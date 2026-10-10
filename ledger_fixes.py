"""Recording what people do about issues: new source versions and fixes. Pure ledger writes, no rules, no model.

A fix records the route (align the documents, record an allowed exception, change or withdraw the promise), the
owner, the rationale, the issues it addresses and its evidence (specific source versions). Recording a fix closes
nothing: only a recheck (recheck.py) can, by re-evaluating every issue with the same rules. Approved fixes are
immutable (database triggers); a change is a new version.
"""

import json
import re
import secrets
import sqlite3

import adapters
import config
import ledger
import ledger_import

ROUTES = ("align_documents", "allowed_exception", "change_or_withdraw_promise")


class FixError(Exception):
    pass


USER_SLUG = re.compile(r"u_[0-9a-f]{16}")


def deal_id(conn: sqlite3.Connection, slug: str) -> int:
    """The deal's id. A development slug must be in LEDGER_DEALS; a user slug must exist with kind 'user'."""
    if USER_SLUG.fullmatch(slug or ""):
        row = conn.execute("SELECT id FROM deals WHERE slug = ? AND kind = 'user'", (slug,)).fetchone()
    else:
        ledger.require_ledger_deal(slug)
        row = conn.execute("SELECT id FROM deals WHERE slug = ? AND kind = 'development'", (slug,)).fetchone()
    if row is None:
        raise FixError(f"{slug}: not in the ledger")
    return row[0]


def create_user_deal(conn, display_name: str, commit: bool = True) -> str:
    """A user deal with a server-generated slug (u_ + 16 hex). The name is display text only, never a path."""
    name = (display_name or "").strip()
    if not name or len(name) > 120:
        raise FixError("a deal needs a name of 1 to 120 characters")
    slug = "u_" + secrets.token_hex(8)
    conn.execute("INSERT INTO deals (slug, kind, display_name) VALUES (?, 'user', ?)", (slug, name))
    if commit:
        conn.commit()
    return slug


def add_source(conn, slug: str, display_name: str, text: str, filename: str, doc_type: str, doc_date: str,
               commit: bool = True, raw: bytes | None = None, adapted: dict | None = None) -> int:
    """A new source with its first version. Returns the version id.

    Text and Markdown come in as `text`. A document read by an adapter (adapters.adapt: PDF, Word) comes in as the
    original `raw` bytes and its `adapted` result; its problems are stored with the version."""
    did = deal_id(conn, slug)
    if doc_type not in config.EXTRACTABLE_DOC_TYPES + config.REFERENCE_ONLY_DOC_TYPES:
        raise FixError(f"unknown document type {doc_type!r}")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", doc_date or ""):
        raise FixError("a document date is needed as YYYY-MM-DD")
    if adapted is None and (not text or not text.strip()):
        raise FixError("the document is empty")
    n = conn.execute("SELECT COUNT(*) FROM sources WHERE deal_id = ?", (did,)).fetchone()[0]
    key = f"D-{n + 1:02d}"
    if adapted is None:
        raw = text.encode("utf-8")
        adapted = ledger_import.markdown_adapter(raw)
    if adapted.get("problems"):
        adapters.ensure_notes_schema(conn)
    try:
        source_id = conn.execute("INSERT INTO sources (deal_id, source_key, display_name) VALUES (?, ?, ?)",
                                 (did, key, (display_name or filename or key)[:200])).lastrowid
        vid = conn.execute(
            "INSERT INTO source_versions (source_id, version_no, original_sha256, canonical_sha256, adapter_name,"
            " adapter_version, doc_type, doc_date, original_filename, canonical_text, location_map, included)"
            " VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)",
            (source_id, ledger_import.sha256_hex(raw), ledger_import.sha256_hex(adapted["canonical_text"]),
             adapted["adapter_name"], adapted["adapter_version"], doc_type, doc_date, (filename or key)[:200],
             adapted["canonical_text"], adapted["location_map"])).lastrowid
        adapters.save_notes(conn, vid, adapted.get("problems") or [])
    except BaseException:
        conn.rollback()
        raise
    if commit:
        conn.commit()
    return vid


def set_included(conn, slug: str, source_key: str, included: bool, commit: bool = True) -> None:
    """Include or exclude a source's latest version. Excluding never closes an issue; the review goes out of date."""
    did = deal_id(conn, slug)
    row = conn.execute("SELECT v.id FROM source_versions v JOIN sources s ON s.id = v.source_id WHERE s.deal_id = ?"
                       " AND s.source_key = ? ORDER BY v.version_no DESC LIMIT 1", (did, source_key)).fetchone()
    if row is None:
        raise FixError(f"no source {source_key}")
    conn.execute("UPDATE source_versions SET included = ? WHERE id = ?", (1 if included else 0, row[0]))
    if commit:
        conn.commit()


def freshness(conn, did: int) -> dict:
    """'Not reviewed', 'Review out of date' or 'Up to date'.

    Out of date when the documents, the approval evidence or the catalogue and rules differ from what the latest review
    was made against (integrity.py: the three hashes, compared under the review's own hash definition). `reasons` lists
    every plain-word reason, including two that do not make the review out of date but stop a decision being made on
    it: it was made under an older hash definition, or its config was never recorded. `notes` carries the extraction
    line, which is shown and never a reason."""
    import integrity  # imported here: integrity imports this module
    row = conn.execute(
        "SELECT r.id, r.source_set_sha256, r.decision_evidence_sha256, r.finished_at, r.run_kind FROM reviews r"
        " WHERE r.deal_id = ? AND r.status = 'complete' AND EXISTS (SELECT 1 FROM commitment_assessments a"
        " WHERE a.review_id = r.id) ORDER BY r.id DESC LIMIT 1", (did,)).fetchone()
    if row is None:
        return {"state": "Not reviewed", "review_id": None, "finished_at": None, "run_kind": None, "reasons": [], "notes": []}
    reasons = integrity.review_reasons(conn, did, row[0], row[1], row[2])
    state = "Review out of date" if any(r in integrity.STALE for r in reasons) else "Up to date"
    return {"state": state, "review_id": row[0], "finished_at": row[3], "run_kind": row[4], "reasons": reasons,
            "notes": integrity.extraction_note(conn, row[0])}


def add_source_version(conn, slug: str, source_key: str, text: str, filename: str, doc_type=None, doc_date=None,
                       commit: bool = True, raw: bytes | None = None, adapted: dict | None = None) -> int:
    """A new version of an existing source, included in place of the previous one. Returns the new version id.

    Document type and date default to the previous version's: a revised SOW keeps its date unless the user says
    otherwise (a re-dated SOW no longer matches the contract's citation, by design).
    """
    did = deal_id(conn, slug)
    row = conn.execute("SELECT id FROM sources WHERE deal_id = ? AND source_key = ?", (did, source_key)).fetchone()
    if row is None:
        raise FixError(f"{slug}: no source {source_key}")
    source_id = row[0]
    prev = conn.execute(
        "SELECT version_no, doc_type, doc_date FROM source_versions WHERE source_id = ? ORDER BY version_no DESC LIMIT 1",
        (source_id,)).fetchone()
    doc_type = doc_type or prev[1]
    if doc_type not in config.EXTRACTABLE_DOC_TYPES + config.REFERENCE_ONLY_DOC_TYPES:
        raise FixError(f"unknown document type {doc_type!r}")
    if adapted is None:
        raw = text.encode("utf-8")
        adapted = ledger_import.markdown_adapter(raw)
    elif adapted.get("problems"):
        adapters.ensure_notes_schema(conn)
    try:
        conn.execute("UPDATE source_versions SET included = 0 WHERE source_id = ?", (source_id,))
        version_id = conn.execute(
            "INSERT INTO source_versions (source_id, version_no, original_sha256, canonical_sha256, adapter_name,"
            " adapter_version, doc_type, doc_date, original_filename, canonical_text, location_map, included)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)",
            (source_id, prev[0] + 1, ledger_import.sha256_hex(raw), ledger_import.sha256_hex(adapted["canonical_text"]),
             adapted["adapter_name"], adapted["adapter_version"], doc_type, doc_date or prev[2], filename,
             adapted["canonical_text"], adapted["location_map"]),
        ).lastrowid
        adapters.save_notes(conn, version_id, adapted.get("problems") or [])
    except BaseException:
        conn.rollback()
        raise
    if commit:
        conn.commit()
    return version_id


def create_fix(conn, slug: str, route: str, owner: str, rationale: str, issue_ids: list, evidence: list,
               commit: bool = True) -> int:
    """A draft fix. evidence: [(source_version_id, locator, note)]. Returns the fix id."""
    did = deal_id(conn, slug)
    if route not in ROUTES:
        raise FixError(f"unknown route {route!r}")
    if not rationale or not rationale.strip():
        raise FixError("a fix needs a rationale")
    n = conn.execute("SELECT COUNT(DISTINCT fix_key) FROM fixes WHERE deal_id = ?", (did,)).fetchone()[0]
    try:
        fix_id = conn.execute(
            "INSERT INTO fixes (deal_id, fix_key, version_no, route, owner_function, rationale)"
            " VALUES (?, ?, 1, ?, ?, ?)", (did, f"F{n + 1}", route, owner, rationale)).lastrowid
        for issue_id in issue_ids:
            ok = conn.execute("SELECT 1 FROM issues i JOIN commitments c ON c.id = i.commitment_id"
                              " WHERE i.id = ? AND c.deal_id = ?", (issue_id, did)).fetchone()
            if not ok:
                raise FixError(f"issue {issue_id} is not in {slug}")
            conn.execute("INSERT INTO fix_issues (fix_id, issue_id) VALUES (?, ?)", (fix_id, issue_id))
        for version_id, locator, note in evidence:
            ok = conn.execute("SELECT 1 FROM source_versions v JOIN sources s ON s.id = v.source_id"
                              " WHERE v.id = ? AND s.deal_id = ?", (version_id, did)).fetchone()
            if not ok:
                raise FixError(f"source version {version_id} is not in {slug}")
            conn.execute("INSERT INTO fix_evidence (fix_id, source_version_id, locator, note) VALUES (?, ?, ?, ?)",
                         (fix_id, version_id, locator, note))
    except BaseException:
        conn.rollback()
        raise
    if commit:
        conn.commit()
    return fix_id


def approve_fix(conn, fix_id: int, approved_by: str, commit: bool = True) -> None:
    if not approved_by or not approved_by.strip():
        raise FixError("a fix needs the name of who signs it off")
    try:
        conn.execute("UPDATE fixes SET status = 'approved', approved_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now'),"
                     " approved_by = ? WHERE id = ?", (approved_by, fix_id))
    except BaseException:
        conn.rollback()
        raise
    if commit:
        conn.commit()


def decision_evidence_sha256(conn, did: int) -> str:
    """Hash of every evidence row of every approved fix (docs/LEDGER_SCHEMA.md 3.5). Owners and notes excluded."""
    lines = [f"{k}:{v}:{sv}" for k, v, sv in conn.execute(
        "SELECT f.fix_key, f.version_no, e.source_version_id FROM fixes f JOIN fix_evidence e ON e.fix_id = f.id"
        " WHERE f.deal_id = ? AND f.status = 'approved'", (did,))]
    return ledger_import.sha256_hex("\n".join(sorted(lines)))


def source_set_sha256(conn, did: int) -> str:
    lines = [f"{k}:{n}:{h}:{t}:{d}" for k, n, h, t, d in conn.execute(
        "SELECT s.source_key, v.version_no, v.canonical_sha256, v.doc_type, v.doc_date FROM source_versions v"
        " JOIN sources s ON s.id = v.source_id WHERE s.deal_id = ? AND v.included = 1", (did,))]
    return ledger_import.sha256_hex("\n".join(sorted(lines)))


def evidence_json(rows) -> str:
    return json.dumps(rows, sort_keys=True)
