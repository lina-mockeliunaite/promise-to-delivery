"""Add a document and check it in one call (20 Oct).

The add-document form used to make two calls: store the version, then review. When the review failed (no API key, say) the
version was already stored, and every retry stored another one (v1 to v4 after three failed tries).

Now, in one call and in this order:

1. Before writing anything: if the new or changed document needs the model and the server cannot call it, refuse.
   Nothing is written. (The older fix flow in finding_check.py does the same.)
2. Store the version, then run the review.
3. If the review fails after the version was stored (a rare case: the model call itself failed), the version is set aside:
   excluded, and the version it replaced is included again. Versions are immutable and never deleted, so this is exclusion,
   not rollback: the version stays in the stored history, a version number is skipped, and nothing on any screen shows it.

Why exclusion and not a transaction: the review code runs `executescript` before it works, and sqlite commits a pending
transaction first, so a stored version cannot be held back inside it. Changing that would mean editing ledger_v2.py, which is
part of the config hash (every review would go stale). So ledger_v2.py is left untouched.
"""

import re

import config
import extraction_cache
import finding_check
import ledger_fixes
import ledger_import
import deal_catalogue
import ledger_v2
import recheck

NO_KEY = ("This review needs the model to read the new or changed document, and the server has no API key. "
          "Restart the server with the key set in its terminal, then try again. Nothing was added.")
SET_ASIDE = "The check didn't run. This version was set aside and isn't part of the review."


class AddCheckError(Exception):
    def __init__(self, message: str, status: int = 409):
        super().__init__(message)
        self.status = status


def _latest(conn, did: int) -> list:
    """[(source_key, display name, doc_type)] for the latest included version of each source, as the review sees them."""
    return conn.execute(
        "SELECT s.source_key, s.display_name, v.doc_type FROM sources s JOIN source_versions v ON v.source_id = s.id"
        " WHERE s.deal_id = ? AND v.included = 1 AND v.version_no = (SELECT MAX(version_no) FROM source_versions"
        " WHERE source_id = s.id AND included = 1) ORDER BY s.id", (did,)).fetchall()


def refusal_hint(conn, slug: str, did: int, source_key, doc_type: str) -> str:
    """One sentence added to the "needs the model" refusal (21 Oct) when the likely cause is a filing slip. A document added as "A new
    document" is dated the day it is added and sits beside the original, so the review's input differs from the one a stored reading was
    made for, and the model is needed where a correct filing would not need it. Two cases: this file itself would be a new document next
    to one of its own type; or an earlier "new document" already sits beside an original of its type. "" when neither."""
    import workspace
    labels = workspace.document_labels(conn, did)
    docs = _latest(conn, did)
    same = [(k, labels.get(k, n)) for k, n, t in docs if t == doc_type]
    if not source_key and len(same) == 1:
        return (f"This file would be added as a new document dated today, next to {same[0][1]}. If it revises {same[0][1]}, choose "
                f"“A new version of: {same[0][1]}” instead, and the stored reading may apply.")
    by_type = {}
    for k, n, t in docs:
        by_type.setdefault(t, []).append((k, labels.get(k, n)))
    for t, items in by_type.items():
        added = [name for k, name in items if re.fullmatch(r"D-\d+", k)]  # added with "A new document" (the form generates these keys)
        original = [name for k, name in items if not re.fullmatch(r"D-\d+", k)]
        if added and original and t in config.REFERENCE_ONLY_DOC_TYPES + config.EXTRACTABLE_DOC_TYPES:
            return (f"{added[0]} was added earlier as a new document, dated the day it was added, next to {original[0]}. A new version of "
                    f"{original[0]} would replace it instead. Reset the demo and add it as “A new version of: {original[0]}”.")
    return ""


def _needs_model(conn, slug, did, source_key, doc_type, text, adapted, doc_date=None) -> bool:
    if ledger_v2.is_v2(conn, did):
        canonical = adapted["canonical_text"] if adapted else ledger_import.markdown_adapter(text.encode("utf-8"))["canonical_text"]
        return deal_catalogue.needs_model(conn, slug, source_key, doc_type, canonical, doc_date or None)
    if doc_type in config.EXTRACTABLE_DOC_TYPES:
        fields = extraction_cache.key_fields(finding_check._canonical_sha(text, adapted), doc_type)
        return extraction_cache.lookup(conn, fields) is None
    return False


def add_and_check(conn, slug: str, *, filename: str, text: str = "", raw=None, adapted=None, source_key=None, name=None,
                  doc_type=None, doc_date=None, client=None) -> dict:
    """{'version_id', 'result'}: the stored version and the review's result. Raises AddCheckError (nothing written, or the
    version set aside) and ledger_fixes.FixError (bad input, nothing written)."""
    did = ledger_fixes.deal_id(conn, slug)
    source_id = None
    if source_key:
        row = conn.execute("SELECT id FROM sources WHERE deal_id = ? AND source_key = ?", (did, str(source_key))).fetchone()
        if row is None:
            raise ledger_fixes.FixError(f"{slug}: no source {source_key}")
        source_id = row[0]
        prev_type = conn.execute("SELECT doc_type FROM source_versions WHERE source_id = ? ORDER BY version_no DESC LIMIT 1",
                                 (source_id,)).fetchone()[0]
        doc_type = doc_type or prev_type
    if doc_type not in config.EXTRACTABLE_DOC_TYPES + config.REFERENCE_ONLY_DOC_TYPES:
        raise ledger_fixes.FixError(f"unknown document type {doc_type!r}")

    # 1. Check before writing: no key and the model is needed means nothing is stored.
    if client is None and _needs_model(conn, slug, did, str(source_key) if source_key else None, doc_type, text, adapted, doc_date):
        hint = refusal_hint(conn, slug, did, str(source_key) if source_key else None, doc_type)
        raise AddCheckError(f"{NO_KEY} {hint}".strip())

    # 2. Store, remembering which versions were in the review so a set-aside can restore them.
    was_included = [r[0] for r in conn.execute("SELECT id FROM source_versions WHERE source_id = ? AND included = 1",
                                               (source_id,))] if source_id else []
    if source_key:
        version_id = ledger_fixes.add_source_version(conn, slug, str(source_key), text, filename, doc_type, doc_date or None,
                                                     raw=raw, adapted=adapted)
    else:
        version_id = ledger_fixes.add_source(conn, slug, (name or filename or "").strip(), text, filename, doc_type,
                                             doc_date or "", raw=raw, adapted=adapted)
    try:
        result = deal_catalogue.recheck(conn, slug, None, client)
    except Exception:
        conn.rollback()
        conn.execute("UPDATE source_versions SET included = 0 WHERE id = ?", (version_id,))
        for vid in was_included:
            conn.execute("UPDATE source_versions SET included = 1 WHERE id = ?", (vid,))
        conn.commit()
        raise AddCheckError(SET_ASIDE) from None
    return {"version_id": version_id, "result": result}
