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

import config
import extraction_cache
import finding_check
import ledger_fixes
import ledger_import
import ledger_v2
import recheck

NO_KEY = ("This review needs the model to read the new or changed document, and the server has no API key. "
          "Restart the server with the key set in its terminal, then try again. Nothing was added.")
SET_ASIDE = "The check didn't run. This version was set aside and isn't part of the review."


class AddCheckError(Exception):
    def __init__(self, message: str, status: int = 409):
        super().__init__(message)
        self.status = status


def _needs_model(conn, slug, did, source_key, doc_type, text, adapted) -> bool:
    if ledger_v2.is_v2(conn, did):
        canonical = adapted["canonical_text"] if adapted else ledger_import.markdown_adapter(text.encode("utf-8"))["canonical_text"]
        return ledger_v2.needs_model(conn, slug, source_key, doc_type, canonical)
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
    if client is None and _needs_model(conn, slug, did, str(source_key) if source_key else None, doc_type, text, adapted):
        raise AddCheckError(NO_KEY)

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
        result = recheck.recheck(conn, slug, None, client)
    except Exception:
        conn.rollback()
        conn.execute("UPDATE source_versions SET included = 0 WHERE id = ?", (version_id,))
        for vid in was_included:
            conn.execute("UPDATE source_versions SET included = 1 WHERE id = ?", (vid,))
        conn.commit()
        raise AddCheckError(SET_ASIDE) from None
    return {"version_id": version_id, "result": result}
