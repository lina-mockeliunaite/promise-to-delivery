"""Fix inside the finding (layout redesign, built 9 Oct; docs/BRIEF_2026-10-06_layout.md, Level 2 item 3).

One server call for the flow the reviewer could not follow on 6 Oct: attach a document to a finding, confirm its type,
sign it off, and recheck. In order, in one place:

1. The document type is confirmed by the person (required; never defaulted here). If the file replaces an existing
   document, that document's type must match the confirmed one, so a SOW cannot silently become approval evidence.
2. If the new version needs the model and the server has no key, refuse before writing anything.
3. Save the document version and an approved fix that cites it, addressing only the finding the person attached it to
   (Lina, 9 Oct: the fix history should say what the person did). recheck.py still re-evaluates every issue, so a
   document can close other findings too; those are reported as cross-finding effects, not claimed by the fix.
4. Recheck with the same rules (recheck.py, unchanged). The document is evidence; only the recheck closes anything.
5. Report what changed: on this commitment (closed, still open, new) and anywhere else in the deal.

Writes nothing to issues or closure_checks itself; the recheck does, exactly as for any other fix.
"""

import config
import extraction_cache
import ledger_fixes
import ledger_import
import recheck
import workspace

ROUTE_FOR_TYPE = {"pricing_services_note": "allowed_exception", "draft_sow": "align_documents", "draft_contract": "align_documents"}
NEEDS_KEY = ("This document has to be read by the model before it can be checked, and the server has no API key. "
             "Restart the server with the key set in its terminal, then try again. Nothing was saved.")


class CheckError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def route_for(doc_type: str) -> str:
    """Which of the three fix routes a document of this type stands for."""
    return ROUTE_FOR_TYPE.get(doc_type, "change_or_withdraw_promise")


def _states(conn, did: int) -> dict:
    """{issue_id: (state, commitment_id, issue_type, subject_key, absolute_limit)} for every issue of the deal."""
    return {r[0]: r[1:] for r in conn.execute(
        "SELECT i.id, s.state, i.commitment_id, i.issue_type, i.subject_key, i.absolute_limit FROM issues i"
        " JOIN commitments c ON c.id = i.commitment_id JOIN issue_current_state s ON s.issue_id = i.id"
        " WHERE c.deal_id = ? ORDER BY i.id", (did,))}


def _canonical_sha(text: str, adapted) -> str:
    canonical = adapted["canonical_text"] if adapted else ledger_import.markdown_adapter(text.encode("utf-8"))["canonical_text"]
    return ledger_import.sha256_hex(canonical)


def check(conn, slug: str, issue_id, *, confirmed_doc_type, filename: str, text: str = "", raw=None, adapted=None,
          source_key=None, name=None, doc_date=None, signed_off_by=None, note=None, client=None) -> dict:
    did = ledger_fixes.deal_id(conn, slug)
    try:
        issue_id = int(issue_id)
    except (TypeError, ValueError):
        raise CheckError("That finding is not in this deal.", 404) from None
    before = _states(conn, did)
    if issue_id not in before:
        raise CheckError("That finding is not in this deal.", 404)
    commitment_id = before[issue_id][1]
    if confirmed_doc_type not in workspace.DOC_TYPE_LABELS:
        raise CheckError("Confirm what kind of document this is before it is checked.")
    signer = (signed_off_by or "").strip()
    if not signer or len(signer) > 120:
        raise CheckError("Add the name of who signs this off (up to 120 characters).")

    if source_key:
        row = conn.execute("SELECT v.doc_type FROM sources s JOIN source_versions v ON v.source_id = s.id WHERE s.deal_id = ?"
                           " AND s.source_key = ? ORDER BY v.version_no DESC LIMIT 1", (did, str(source_key))).fetchone()
        if row is None:
            raise CheckError("The document this file should replace is not in this deal.", 404)
        if row[0] != confirmed_doc_type:
            current = workspace.DOC_TYPE_LABELS.get(row[0], row[0])
            chosen = workspace.DOC_TYPE_LABELS[confirmed_doc_type]
            raise CheckError(f"This file would replace the {current}, but it was confirmed as a {chosen.lower()}. "
                             "Choose the document it replaces again, or add it as a new document. Nothing was saved.")
    import ledger_v2
    v2 = ledger_v2.is_v2(conn, did)
    if v2 and client is None:
        canonical = adapted["canonical_text"] if adapted else ledger_import.markdown_adapter(text.encode("utf-8"))["canonical_text"]
        if ledger_v2.needs_model(conn, slug, str(source_key) if source_key else None, confirmed_doc_type, canonical):
            raise CheckError(NEEDS_KEY, 409)
    elif confirmed_doc_type in config.EXTRACTABLE_DOC_TYPES and client is None:
        fields = extraction_cache.key_fields(_canonical_sha(text, adapted), confirmed_doc_type)
        if extraction_cache.lookup(conn, fields) is None:
            raise CheckError(NEEDS_KEY, 409)

    open_here = [i for i, s in before.items() if s[1] == commitment_id and s[0] != "Resolved"]
    try:
        if source_key:
            vid = ledger_fixes.add_source_version(conn, slug, str(source_key), text, filename, confirmed_doc_type, doc_date or None,
                                                  commit=False, raw=raw, adapted=adapted)
        else:
            vid = ledger_fixes.add_source(conn, slug, (name or filename or "").strip(), text, filename, confirmed_doc_type,
                                          doc_date or "", commit=False, raw=raw, adapted=adapted)
        labels = workspace.document_labels(conn, did)
        key, version = conn.execute("SELECT s.source_key, v.version_no FROM source_versions v JOIN sources s ON s.id = v.source_id"
                                    " WHERE v.id = ?", (vid,)).fetchone()
        doc_label = workspace.version_label(labels[key], version)
        owner = conn.execute("SELECT owner_function FROM issues WHERE id = ?", (issue_id,)).fetchone()[0]
        rationale = (note or "").strip()[:2000] or f"Evidence attached to the finding: {doc_label}."
        fix_id = ledger_fixes.create_fix(conn, slug, route_for(confirmed_doc_type), owner, rationale, [issue_id],
                                         [(vid, "whole document", None)], commit=False)
        ledger_fixes.approve_fix(conn, fix_id, signer, commit=False)
        conn.commit()
    except ledger_fixes.FixError as exc:
        conn.rollback()
        raise CheckError(str(exc)) from None
    except BaseException:
        conn.rollback()
        raise

    try:
        result = recheck.recheck(conn, slug, fix_id, client)
    except extraction_cache.ExtractionFailed:
        raise CheckError("The document was saved, but the check could not run because the model is not available. "
                         "Restart the server with the API key set, then choose Review deal.", 409) from None

    after = _states(conn, did)
    names = {cid: n for cid, n in ((c["id"], c["name"]) for c in workspace.register(conn, slug)["commitments"])}

    def label(iid):
        _, _, itype, subject, absolute = after[iid]
        return workspace.finding_label(itype, subject, absolute)

    closed = [label(i) for i in open_here if after[i][0] == "Resolved"]
    still_open = [label(i) for i, s in after.items() if s[1] == commitment_id and s[0] != "Resolved"]
    new_here = [label(i) for i, s in after.items() if i not in before and s[1] == commitment_id and s[0] != "Resolved"]
    elsewhere = [{"commitment": names.get(after[i][1], ""), "finding": label(i)} for i, s in before.items()
                 if s[1] != commitment_id and s[0] != "Resolved" and after[i][0] == "Resolved"]
    return {
        "issue_id": issue_id, "commitment_id": commitment_id, "document": doc_label, "fix_id": fix_id,
        "this_finding": after[issue_id][0], "closed": closed, "still_open": still_open, "new": new_here,
        "closed_elsewhere": elsewhere, "model_calls": result.get("model_calls", 0),
    }
