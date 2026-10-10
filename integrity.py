"""Decision integrity: which evidence a decision was made against, and whether it is still current.

Three rules (docs/BRIEF_2026-10-06_integrity.md):
1. No human record changes a finding. Accepted risks, impact assessments and accountable people live in their own
   append-only tables (integrity_schema.sql); nothing here writes to issues or closure_checks, and none of it feeds
   decision_evidence_sha256.
2. Every decision is bound to three hashes of the review it concerns: source set, decision evidence and config
   (catalogue and rules). If any differs, the decision reads "Needs re-confirmation"; it is never rewritten.
3. Ownership follows an issue only when it is verifiably the same issue with the same terms and no closure since.

Hash definitions are versioned. Definition 1 is what reviews recorded before this change: reviews.config_sha256 from
ledger_consolidate.rules_sha256 (five rule files and the raw catalogue bytes). Definition 2 adds recheck.py, which
decides closure and identity, and hashes the catalogue as canonical JSON, so re-indenting it is not a change. A record
is compared only against a hash computed under its own definition; a record under an older definition says so and
never reads as "Documents changed". The source-set and decision-evidence hashes did not change definition.
"""

import hashlib
import json
import sqlite3
from pathlib import Path

import config
import ledger_consolidate as lc
import ledger_fixes
import ledger_import

HERE = Path(__file__).resolve().parent
SCHEMA_PATH = HERE / "integrity_schema.sql"
HASH_DEFINITION = 3
CONFIG_FILES = lc.RULE_FILES + ("recheck.py",)
CONFIG_FILES_3 = CONFIG_FILES + ("detect_v2.py", "ledger_v2.py")  # 3 (10 Oct): the v2 detector and verifier decide findings

DOCUMENTS = "Documents changed"
EVIDENCE = "Approval or fix evidence changed"
RULES = "Catalogue or rules changed"
OLDER_DEFINITION = "Needs re-confirmation: checking rules updated"
NO_CONFIG = "Not comparable: rerun the review"
STALE = {DOCUMENTS, EVIDENCE, RULES}  # these make the review itself out of date; the other two only limit decisions
REVIEW_STALE = "Review out of date: rerun before a signing decision."
CONFIRM_OWNER = "Confirm owner still applies"
EXTRACTION_NOTE = "Some documents were read under earlier extraction settings."
TABLES = ("review_bindings", "decision_bindings", "accepted_risks", "impact_assessments", "accountability")


class IntegrityError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def ensure_schema(conn) -> None:
    """Create the integrity tables and their triggers if this database does not have them yet."""
    have = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE name LIKE '%_append_only_%' OR type = 'table'")}
    if set(TABLES) <= have and "accountability_append_only_d" in have:
        return
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()


def _has(conn, table: str) -> bool:
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)).fetchone() is not None


# --- Hash definitions ------------------------------------------------------------------------------------------------
def catalogue_bytes() -> bytes:
    return (config.DATA_DIR / "catalogue.json").read_bytes()


def canonical_catalogue(raw: bytes) -> bytes:
    try:
        return json.dumps(json.loads(raw.decode("utf-8")), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    except ValueError:
        return raw


def config_sha256(definition: int, raw: bytes | None = None) -> str:
    """The catalogue-and-rules hash under a definition (1 or 2). raw: the catalogue bytes, default the data one."""
    raw = catalogue_bytes() if raw is None else raw
    if definition == 1:
        return lc.rules_sha256(raw)
    if definition not in (2, 3):
        raise ValueError(f"unknown hash definition {definition}")
    digest = hashlib.sha256()
    digest.update(f"hash_definition:{definition}".encode() + b"\0")
    for name in (CONFIG_FILES if definition == 2 else CONFIG_FILES_3):
        digest.update(name.encode() + b"\0" + (HERE / name).read_bytes() + b"\0")
    digest.update(b"catalogue.json\0" + canonical_catalogue(raw))
    return digest.hexdigest()


def config_reasons(definition: int, stored, raw: bytes | None = None) -> list:
    """Why a record's config hash cannot be called current, in plain words. [] means it is."""
    if stored is None:
        return [NO_CONFIG]
    if definition == HASH_DEFINITION:
        return [] if config_sha256(definition, raw) == stored else [RULES]
    reasons = [RULES] if config_sha256(definition, raw) != stored else []  # definition 1 still tells a real change
    return reasons + [OLDER_DEFINITION]


def compare(conn, did: int, source_set, evidence, definition: int, stored_config, raw: bytes | None = None) -> dict:
    """{'current': bool, 'reasons': [...]} for a record bound to these hashes, against the deal as it stands now."""
    reasons = []
    if ledger_fixes.source_set_sha256(conn, did) != source_set:
        reasons.append(DOCUMENTS)
    if ledger_fixes.decision_evidence_sha256(conn, did) != evidence:
        reasons.append(EVIDENCE)
    reasons += config_reasons(definition, stored_config, raw)
    return {"current": not reasons, "reasons": reasons}


# --- Reviews ---------------------------------------------------------------------------------------------------------
def review_config(conn, review_id: int) -> tuple:
    """(definition, config hash or None) recorded for a review. Reviews before this change are definition 1."""
    if _has(conn, "review_bindings"):
        row = conn.execute("SELECT hash_definition, config_sha256 FROM review_bindings WHERE review_id = ?", (review_id,)).fetchone()
        if row:
            return row[0], row[1]
    row = conn.execute("SELECT config_sha256 FROM reviews WHERE id = ?", (review_id,)).fetchone()
    return 1, row[0] if row else None


def review_reasons(conn, did: int, review_id: int, source_set, evidence) -> list:
    definition, stored = review_config(conn, review_id)
    return compare(conn, did, source_set, evidence, definition, stored)["reasons"]


def extraction_keys(conn, review_id: int) -> dict:
    """{source_version_id: extraction cache key hash or None (imported)} for the sources a review used."""
    return {str(v): k for v, k in conn.execute(
        "SELECT rs.source_version_id, e.key_sha256 FROM review_sources rs JOIN extraction_cache e ON e.id = rs.extraction_id"
        " WHERE rs.review_id = ?", (review_id,))}


def write_review_binding(conn, review_id: int, config_sha: str, inputs_changed) -> None:
    conn.execute("INSERT INTO review_bindings (review_id, hash_definition, config_sha256, extraction_keys, inputs_changed)"
                 " VALUES (?, ?, ?, ?, ?)", (review_id, HASH_DEFINITION, config_sha, json.dumps(extraction_keys(conn, review_id), sort_keys=True),
                                             None if inputs_changed is None else int(inputs_changed)))


def extraction_note(conn, review_id: int) -> list:
    """One plain line when a document in this review was read under extraction settings other than today's.
    Recorded and shown, never a reason to mark anything out of date: the documents themselves did not change."""
    if not _has(conn, "review_bindings"):
        return []
    row = conn.execute("SELECT extraction_keys FROM review_bindings WHERE review_id = ?", (review_id,)).fetchone()
    if row is None:
        return []
    import extraction_cache  # imported here: it needs the model SDK, and freshness must stay cheap to import
    for vid, key in json.loads(row[0]).items():
        if key is None:
            continue
        sha, doc_type = conn.execute("SELECT canonical_sha256, doc_type FROM source_versions WHERE id = ?", (int(vid),)).fetchone()
        if extraction_cache.key_sha256(extraction_cache.key_fields(sha, doc_type)) != key:
            return [EXTRACTION_NOTE]
    return []


def is_current(conn, did: int) -> tuple:
    """(True, '') when a signing or handoff decision may be made now, else (False, the plain refusal)."""
    fresh = ledger_fixes.freshness(conn, did)
    if fresh["state"] != "Up to date" or fresh.get("reasons"):
        return False, REVIEW_STALE
    return True, ""


def require_current(conn, did: int) -> dict:
    ok, message = is_current(conn, did)
    if not ok:
        raise IntegrityError(message, 409)
    return ledger_fixes.freshness(conn, did)


def current_binding(conn, did: int) -> dict:
    """The three hashes of the review the deal stands on, refused unless that review is current under definition 2."""
    fresh = require_current(conn, did)
    source_set, evidence = conn.execute("SELECT source_set_sha256, decision_evidence_sha256 FROM reviews WHERE id = ?",
                                        (fresh["review_id"],)).fetchone()
    definition, stored = review_config(conn, fresh["review_id"])
    return {"hash_definition": definition, "source_set_sha256": source_set, "decision_evidence_sha256": evidence,
            "config_sha256": stored}


def write_decision_binding(conn, kind: str, decision_id: int, binding: dict) -> None:
    conn.execute("INSERT INTO decision_bindings (decision_kind, decision_id, hash_definition, source_set_sha256,"
                 " decision_evidence_sha256, config_sha256) VALUES (?, ?, ?, ?, ?, ?)",
                 (kind, decision_id, binding["hash_definition"], binding["source_set_sha256"],
                  binding["decision_evidence_sha256"], binding["config_sha256"]))


def decision_status(conn, did: int, kind: str, decision_id: int, derived=None) -> dict:
    """{'current': bool, 'reasons': [...], 'label'}. derived: (source_set, evidence, review_id) for a record that
    predates bindings (a handoff saved before this change), read as definition 1 from its review."""
    row = conn.execute("SELECT hash_definition, source_set_sha256, decision_evidence_sha256, config_sha256 FROM decision_bindings"
                       " WHERE decision_kind = ? AND decision_id = ?", (kind, decision_id)).fetchone() if _has(conn, "decision_bindings") else None
    if row is None and derived is not None:
        definition, stored = review_config(conn, derived[2])
        row = (definition, derived[0], derived[1], stored)
    if row is None:
        return {"current": False, "reasons": [NO_CONFIG], "label": "Needs re-confirmation"}
    out = compare(conn, did, row[1], row[2], row[0], row[3])
    out["label"] = "Current" if out["current"] else "Needs re-confirmation"
    return out


# --- Issue context and human records ---------------------------------------------------------------------------------
def _digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _commitment_facts(conn, commitment_id: int) -> dict:
    """What a commitment says now: its term sets and the hashes of the quotes behind it, from its latest assessment."""
    row = conn.execute("SELECT review_id, terms FROM commitment_assessments WHERE commitment_id = ? AND support_state = 'supported'"
                       " ORDER BY id DESC LIMIT 1", (commitment_id,)).fetchone()
    if row is None:
        return {"supported": False}
    terms = json.loads(row[1]) if row[1] else {}
    quotes = sorted(hashlib.sha256(q.encode("utf-8")).hexdigest() for (q,) in conn.execute(
        "SELECT s.quote FROM review_statement_commitments l JOIN statements s ON s.id = l.statement_id"
        " WHERE l.review_id = ? AND l.commitment_id = ?", (row[0], commitment_id)))
    return {"supported": True, "key": terms.get("key"), "term_sets": [m.get("term_set") for m in terms.get("members", [])],
            "quotes": quotes}


def issue_context(conn, issue_id: int) -> tuple:
    """(context hash, latest closure check id) for an issue: identity, the terms and quotes of its commitment and of the
    commitment on the other side of a conflict, and the evidence its latest closure check looked at."""
    cid, itype, subject = conn.execute("SELECT i.commitment_id, i.issue_type, i.subject_key FROM issues i WHERE i.id = ?",
                                       (issue_id,)).fetchone()
    deal = conn.execute("SELECT deal_id FROM commitments WHERE id = ?", (cid,)).fetchone()[0]
    other = None
    if subject.startswith("conflict:"):
        found = conn.execute("SELECT id FROM commitments WHERE deal_id = ? AND commitment_key = ?", (deal, subject.split(":", 1)[1])).fetchone()
        other = _commitment_facts(conn, found[0]) if found else {"supported": False}
    check = conn.execute("SELECT id, evidence_checked FROM closure_checks WHERE issue_id = ? ORDER BY id DESC LIMIT 1", (issue_id,)).fetchone()
    versions = sorted({e.get("source_version_id") for e in json.loads(check[1] or "[]")}) if check else []
    return _digest({"type": itype, "subject": subject, "commitment": _commitment_facts(conn, cid), "other": other,
                    "evidence_versions": versions}), (check[0] if check else None)


def _issue_in_deal(conn, did: int, issue_id) -> None:
    if not conn.execute("SELECT 1 FROM issues i JOIN commitments c ON c.id = i.commitment_id WHERE i.id = ? AND c.deal_id = ?",
                        (issue_id, did)).fetchone():
        raise IntegrityError("That issue is not in this deal.", 404)


def _name(value, what: str) -> str:
    value = (value or "").strip()
    if not value or len(value) > 120:
        raise IntegrityError(f"Add {what} (up to 120 characters).")
    return value


def _record(conn, did: int, kind: str, table: str, columns: str, values: tuple, issue_id: int) -> int:
    """One human record with its decision binding, in one transaction. Never touches issues or closure_checks."""
    ensure_schema(conn)
    binding = current_binding(conn, did)
    _issue_in_deal(conn, did, issue_id)
    try:
        rid = conn.execute(f"INSERT INTO {table} ({columns}) VALUES ({', '.join('?' * len(values))})", values).lastrowid
        write_decision_binding(conn, kind, rid, binding)
    except BaseException:
        conn.rollback()
        raise
    conn.commit()
    return rid


def record_accepted_risk(conn, slug: str, issue_id: int, accepted_by, rationale) -> int:
    did = ledger_fixes.deal_id(conn, slug)
    _issue_in_deal(conn, did, issue_id)
    who, why = _name(accepted_by, "who accepts the risk"), (rationale or "").strip()
    if not why or len(why) > 2000:
        raise IntegrityError("Add the reason the risk is accepted (up to 2,000 characters).")
    ctx, _ = issue_context(conn, issue_id)
    return _record(conn, did, "accepted_risk", "accepted_risks", "deal_id, issue_id, accepted_by, rationale, issue_context",
                   (did, issue_id, who, why, ctx), issue_id)


def record_impact(conn, slug: str, issue_id: int, impact, assessed_by, note=None) -> int:
    did = ledger_fixes.deal_id(conn, slug)
    if impact not in ("material", "no_material_impact", "unknown"):
        raise IntegrityError("Choose an impact: material, no material impact or unknown.")
    _issue_in_deal(conn, did, issue_id)
    who = _name(assessed_by, "who assessed the impact")
    ctx, _ = issue_context(conn, issue_id)
    return _record(conn, did, "impact_assessment", "impact_assessments", "deal_id, issue_id, impact, assessed_by, note, issue_context",
                   (did, issue_id, impact, who, (note or "").strip()[:2000] or None, ctx), issue_id)


def set_accountability(conn, slug: str, issue_id: int, person, deadline, set_by, confirm: bool = False) -> int:
    """Name the accountable person for an issue, stamped with the issue's evidence context now. confirm=True records
    that a named person checked that an earlier owner still applies."""
    did = ledger_fixes.deal_id(conn, slug)
    _issue_in_deal(conn, did, issue_id)
    who, by = _name(person, "the accountable person"), _name(set_by, "who is setting this")
    ctx, check_id = issue_context(conn, issue_id)
    return _record(conn, did, "accountability", "accountability", "deal_id, issue_id, person, deadline, set_by, kind, issue_context, evidence_check_id",
                   (did, issue_id, who, deadline or None, by, "confirmed" if confirm else "set", ctx, check_id), issue_id)


def accountability_status(conn, issue_id: int) -> dict:
    """{'status': 'none' | 'current' | 'confirm', ...}. Carries forward only for the same issue with unchanged terms and
    quotes that no closure check has closed since it was set; otherwise a named person must confirm."""
    if not _has(conn, "accountability"):
        return {"status": "none"}
    row = conn.execute("SELECT person, deadline, issue_context, evidence_check_id FROM accountability WHERE issue_id = ?"
                       " ORDER BY id DESC LIMIT 1", (issue_id,)).fetchone()
    if row is None:
        return {"status": "none"}
    ctx, _ = issue_context(conn, issue_id)
    closed = conn.execute("SELECT 1 FROM closure_checks WHERE issue_id = ? AND outcome = 'met' AND id > ?",
                          (issue_id, row[3] or 0)).fetchone()
    base = {"person": row[0], "deadline": row[1]}
    if ctx != row[2] or closed:
        return {"status": "confirm", "message": CONFIRM_OWNER, **base}
    return {"status": "current", **base}


def _record_status(conn, did: int, kind: str, table: str, issue_id: int, reassess: bool) -> dict:
    if not _has(conn, table):
        return {"status": "none"}
    row = conn.execute(f"SELECT id, issue_context FROM {table} WHERE issue_id = ? ORDER BY id DESC LIMIT 1", (issue_id,)).fetchone()
    if row is None:
        return {"status": "none"}
    st = decision_status(conn, did, kind, row[0])
    if reassess and issue_context(conn, issue_id)[0] != row[1]:
        return {"status": "Needs reassessment", "record_id": row[0], "reasons": st["reasons"]}
    return {"status": st["label"], "record_id": row[0], "reasons": st["reasons"]}


def accepted_risk_status(conn, slug: str, issue_id: int) -> dict:
    return _record_status(conn, ledger_fixes.deal_id(conn, slug), "accepted_risk", "accepted_risks", issue_id, False)


def impact_status(conn, slug: str, issue_id: int) -> dict:
    return _record_status(conn, ledger_fixes.deal_id(conn, slug), "impact_assessment", "impact_assessments", issue_id, True)


def decision_summary(conn, slug: str) -> dict:
    """Open issues with their human records. Declines to list anything as current while the review is out of date."""
    did = ledger_fixes.deal_id(conn, slug)
    ok, message = is_current(conn, did)
    if not ok:
        return {"current": False, "message": message, "items": []}
    items = []
    for iid, itype, subject in conn.execute(
            "SELECT i.id, i.issue_type, i.subject_key FROM issues i JOIN commitments c ON c.id = i.commitment_id"
            " JOIN issue_current_state v ON v.issue_id = i.id WHERE c.deal_id = ? AND v.state <> 'Resolved' ORDER BY i.id", (did,)):
        items.append({"issue_id": iid, "accepted_risk": accepted_risk_status(conn, slug, iid), "impact": impact_status(conn, slug, iid),
                      "accountability": accountability_status(conn, iid)})
    return {"current": True, "message": "", "items": items}
