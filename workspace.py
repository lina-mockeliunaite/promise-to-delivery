"""Read model for the deal workspace: what the screens show, built from the ledger. Reads only; no rules, no model.

Plain language on purpose: the screens speak to business readers. Internal hashes, prompts, labels and file paths
never appear in anything this module returns.
"""

import json
import re

import config
import ledger_fixes

ISSUE_LABELS = {
    ("approval", None): "Needs internal approval",
    ("contract_gap", None): "Missing from the contract",
    ("conflicting_terms", None): "Contract says something different",
    ("insufficient_evidence", "authorisation"): "Approval can't be confirmed",
    ("insufficient_evidence", "contract"): "Contract coverage can't be confirmed",
    ("missing_condition", None): "A condition was dropped",
}
NEXT_STEP = {
    "approval": "Record a named exception with its approver, or change the promise.",
    "approval_absolute": "Not offered: change or withdraw the promise. An exception cannot close this.",
    "contract_gap": "Add the promise to the SOW or contract, or withdraw it.",
    "conflicting_terms": "Align the documents so they say the same thing.",
    "insufficient_evidence": "Add the missing evidence, then review again.",
    "missing_condition": "Restore the condition, or record that it was withdrawn.",
}
DOC_TYPE_LABELS = {
    "call_transcript": "Call transcript", "rfp_response": "RFP response", "proposal": "Proposal",
    "draft_sow": "Draft SOW", "draft_contract": "Draft contract", "pricing_services_note": "Pricing and services note",
    "customer_email": "Customer email", "security_questionnaire": "Security questionnaire",
}
AUTH_LABELS = {
    "standard_authorised": "Standard, authorised", "exception_approved": "Exception approved",
    "no_approval_evidence": "No approval recorded", "unknown_needs_review": "Can't be confirmed",
    "not_assessed": "Not assessed", None: "Not applicable",
}
PRESENCE_LABELS = {"included_in_draft_contract": "In the draft contract", "absent": "Not in the contract",
                   "not_assessed": "Not assessed"}


def display_name(name: str, statements: list) -> str:
    """A readable commitment name: internal markers removed; a promise outside the catalogue named by its own words."""
    clean = re.sub(r"\s*\[terms incomplete:[^\]]*\]", "", name or "").strip()
    if clean.startswith("Unclassified promise:"):
        quote = statements[0]["quote"] if statements else clean.split(":", 1)[1]
        quote = re.sub(r"^\s*[A-Z]\.\d+(\.\d+)*\s+", "", quote).strip().rstrip(".")
        return quote if len(quote) <= 90 else quote[:87].rsplit(" ", 1)[0] + "…"
    return clean


def deal_title(slug: str, display: str) -> str:
    return display if ledger_fixes.USER_SLUG.fullmatch(slug) else display.replace("_", " ").title()


def issue_label(issue_type, subject):
    return ISSUE_LABELS.get((issue_type, subject)) or ISSUE_LABELS.get((issue_type, None)) or issue_type


def documents(conn, slug: str) -> list:
    did = ledger_fixes.deal_id(conn, slug)
    out = []
    for key, name, vid, version_no, doc_type, date, included, filename in conn.execute(
        "SELECT s.source_key, s.display_name, v.id, v.version_no, v.doc_type, v.doc_date, v.included, v.original_filename"
        " FROM sources s JOIN source_versions v ON v.source_id = s.id WHERE s.deal_id = ? AND v.version_no ="
        " (SELECT MAX(version_no) FROM source_versions WHERE source_id = s.id) ORDER BY v.doc_date, s.source_key", (did,)):
        out.append({
            "source_key": key, "name": name, "source_version_id": vid, "version": version_no,
            "doc_type": doc_type, "doc_type_label": DOC_TYPE_LABELS.get(doc_type, doc_type), "date": date,
            "included": bool(included), "filename": filename,
            "role": ("Read for promises" if doc_type in config.EXTRACTABLE_DOC_TYPES
                     else "Approval evidence" if doc_type == "pricing_services_note" else "Reference only"),
        })
    return out


def register(conn, slug: str) -> dict:
    did = ledger_fixes.deal_id(conn, slug)
    name = conn.execute("SELECT display_name FROM deals WHERE id = ?", (did,)).fetchone()[0]
    fresh = ledger_fixes.freshness(conn, did)
    commitments = []
    rows = conn.execute(
        "SELECT c.id, c.commitment_key, c.note, s.status, a.id, a.review_id, a.name, a.language, a.authorisation,"
        " a.authorisation_evidence, a.contractual_presence, a.presence_detail, a.support_state"
        " FROM commitments c JOIN commitment_status s ON s.commitment_id = c.id"
        " JOIN commitment_assessments a ON a.id = s.assessment_id WHERE c.deal_id = ? ORDER BY c.id", (did,)).fetchall()
    for cid, key, note, status, aid, review_id, cname, language, auth, auth_ev, presence, pdetail, support in rows:
        if support == "unsupported":
            prev = conn.execute("SELECT name FROM commitment_assessments WHERE commitment_id = ? AND support_state = 'supported'"
                                " ORDER BY id DESC LIMIT 1", (cid,)).fetchone()
            cname = prev[0] if prev else cname
        statements = [
            {"source_key": sk, "source_name": sn, "doc_type_label": DOC_TYPE_LABELS.get(dt, dt), "version": vn,
             "quote": q, "language": lang}
            for sk, sn, dt, vn, q, lang in conn.execute(
                "SELECT so.source_key, so.display_name, v.doc_type, v.version_no, st.quote, st.language"
                " FROM review_statement_commitments l JOIN statements st ON st.id = l.statement_id"
                " JOIN source_versions v ON v.id = l.source_version_id JOIN sources so ON so.id = v.source_id"
                " WHERE l.commitment_id = ? AND l.review_id = (SELECT MAX(review_id) FROM review_statement_commitments"
                " WHERE commitment_id = ?) ORDER BY v.doc_date, st.ordinal", (cid, cid))]
        issues = []
        for iid, itype, subject, owner, inote, absolute, raised_by in conn.execute(
                "SELECT id, issue_type, subject_key, owner_function, note, absolute_limit, raised_by FROM issues"
                " WHERE commitment_id = ? ORDER BY id", (cid,)):
            state, outcome = conn.execute("SELECT state, latest_outcome FROM issue_current_state WHERE issue_id = ?",
                                          (iid,)).fetchone()
            check = conn.execute("SELECT reason, unmet, evidence_checked, check_kind FROM closure_checks WHERE issue_id = ?"
                                 " ORDER BY id DESC LIMIT 1", (iid,)).fetchone()
            step = NEXT_STEP["approval_absolute"] if itype == "approval" and absolute else NEXT_STEP.get(itype, "")
            issues.append({
                "id": iid, "type": itype, "subject": subject, "label": issue_label(itype, subject), "state": state,
                "owner": owner, "note": inote, "next_step": step if state != "Resolved" else "",
                "absolute_limit": bool(absolute), "raised_by": raised_by,
                "reason": check[0] if check else "", "unmet": json.loads(check[1]) if check and check[1] else [],
                "evidence_versions": [e.get("source_version_id") for e in json.loads(check[2])] if check else [],
                "last_check": check[3] if check else None,
            })
        open_issues = [i for i in issues if i["state"] != "Resolved"]
        commitments.append({
            "id": cid, "key": key, "name": display_name(cname, statements), "note": note, "status": status, "language": language,
            "authorisation": AUTH_LABELS.get(auth, auth), "authorisation_evidence": auth_ev or "",
            "presence": PRESENCE_LABELS.get(presence, presence), "presence_detail": pdetail or "",
            "supported": support == "supported",
            "attention": [i["label"] for i in open_issues], "owners": sorted({i["owner"] for i in open_issues}),
            "issues": issues, "statements": statements,
        })
    order = {"Needs action": 0, "Needs evidence": 1, "Not in current documents": 2, "Resolved": 3, "No issues raised": 4}
    commitments.sort(key=lambda c: (order.get(c["status"], 5), c["key"]))
    counts = {}
    for c in commitments:
        counts[c["status"]] = counts.get(c["status"], 0) + 1
    return {"deal": slug, "name": deal_title(slug, name), "freshness": fresh, "counts": counts, "commitments": commitments,
            "scope_note": ("Demonstrated on fictional deals with a complete capability catalogue."
                           if not ledger_fixes.USER_SLUG.fullmatch(slug)
                           else "Uploaded documents: accuracy unvalidated; approval needs internal evidence."),
            "resolved_means": "Resolved means the documented gap is closed, not that the work is ready."}


def deal_list(conn) -> list:
    out = []
    for slug, kind, name in conn.execute("SELECT slug, kind, display_name FROM deals ORDER BY kind, id"):
        if kind == "development" and slug not in config.UI_DEALS:
            continue
        did = ledger_fixes.deal_id(conn, slug)
        open_n = conn.execute("SELECT COUNT(*) FROM issue_current_state s JOIN commitments c ON c.id = s.commitment_id"
                              " WHERE c.deal_id = ? AND s.state <> 'Resolved'", (did,)).fetchone()[0]
        out.append({"deal": slug, "name": deal_title(slug, name), "kind": kind,
                    "freshness": ledger_fixes.freshness(conn, did), "open_issues": open_n})
    return out
