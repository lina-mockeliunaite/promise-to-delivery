"""Read model for the deal workspace: what the screens show, built from the ledger. Reads only; no rules, no model.

Plain language on purpose: the screens speak to business readers. Internal hashes, prompts, labels and file paths
never appear in anything this module returns.
"""

import json
import re

import config
import evidence_text
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


_COMMITMENT_KEY = re.compile(r"\bC\d{2,}\b(?: \(([^)]*)\))?")
_STATEMENT_KEY = re.compile(r"\b[A-Z]{1,4}-\d{2}-S\d{2,}\b|\bS\d{3,}\b")


MONTHS_SHORT = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def short_date(iso, year: bool = True) -> str:
    """'28 Sep 2026' (or '28 Sep'); empty or malformed input comes back as it is."""
    try:
        y, m, d = (int(x) for x in str(iso).split("-"))
        return f"{d} {MONTHS_SHORT[m - 1]} {y}" if year else f"{d} {MONTHS_SHORT[m - 1]}"
    except (ValueError, IndexError):
        return str(iso or "")


def document_labels(conn, did: int) -> dict:
    """{source_key: plain-language label} for one deal: the document type ('Pricing and services note'), never a file
    name or key. Two documents of one type in a deal are told apart by date ('Call transcript of 28 Sep 2026'), then
    by a number if the dates match. The version is added where it is known exactly (see version_label)."""
    rows = conn.execute(
        "SELECT s.source_key, v.doc_type, v.doc_date FROM sources s JOIN source_versions v ON v.source_id = s.id"
        " WHERE s.deal_id = ? AND v.version_no = (SELECT MAX(version_no) FROM source_versions WHERE source_id = s.id)"
        " ORDER BY s.id", (did,)).fetchall()
    base = {key: DOC_TYPE_LABELS.get(dt, dt) for key, dt, _ in rows}
    labels = {}
    for key, _, date in rows:
        dup = sum(1 for b in base.values() if b == base[key]) > 1
        labels[key] = f"{base[key]} of {short_date(date)}" if dup else base[key]
    seen = {}
    for key, _, _ in rows:
        seen[labels[key]] = seen.get(labels[key], 0) + 1
    count = {}
    for key, _, _ in rows:
        if seen[labels[key]] > 1:
            count[labels[key]] = count.get(labels[key], 0) + 1
            labels[key] = f"{labels[key]} ({count[labels[key]]})"
    return labels


def version_label(label: str, version) -> str:
    return f"{label}, version {version}"


# Rules and recheck phrasing that reads as system talk, in plain words. Applied by plain() to reason and detail text.
PHRASES = [
    ("Still found by this recheck. ", ""),
    ("Not raised by this recheck, but nothing yet shows its closure criteria are met; it stays open.",
     "Nothing yet shows that what was needed is in place, so it stays open."),
    ("Closed: this recheck no longer finds the issue, and the evidence below meets its closure criteria.",
     "Closed: the issue is no longer found, and the evidence meets what was needed."),
    ("closure criteria not shown by any current evidence", "nothing in the current documents shows it is closed"),
]


def plain(text, names: dict | None = None) -> str:
    """Ledger or rules text with internal keys and system phrasing removed: 'C07 (Name)' becomes 'Name', statement keys
    go, document keys become the document's plain label (no version: the text does not record which). Not applied to verbatim quotes."""
    if not text:
        return text or ""
    def commitment(m):
        name = re.sub(r"\s*\[terms incomplete:[^\]]*\]", "", m.group(1) or "").strip()
        return f"\u201c{name}\u201d" if name else "another commitment"
    out = text
    for phrase, replacement in PHRASES:
        out = out.replace(phrase, replacement)
    out = re.sub(r"\s*\[terms incomplete:[^\]]*\]", "", out)
    out = re.sub(r"Included: (?:(?:" + _STATEMENT_KEY.pattern + r")(?:, )?)+ in ", "Included in ", out)
    out = _STATEMENT_KEY.sub("", out)
    out = _COMMITMENT_KEY.sub(commitment, out)
    for key in sorted(names or {}, key=len, reverse=True):
        out = re.sub(rf"\b{re.escape(key)}\b", names[key], out)
    return re.sub(r"\s{2,}", " ", out).replace(" ,", ",").replace(" .", ".").strip()


def deal_title(slug: str, display: str) -> str:
    return display if ledger_fixes.USER_SLUG.fullmatch(slug) else display.replace("_", " ").title()


def issue_label(issue_type, subject):
    return ISSUE_LABELS.get((issue_type, subject)) or ISSUE_LABELS.get((issue_type, None)) or issue_type


def documents(conn, slug: str) -> list:
    did = ledger_fixes.deal_id(conn, slug)
    labels = document_labels(conn, did)
    out = []
    for key, vid, version_no, doc_type, date, included in conn.execute(
        "SELECT s.source_key, v.id, v.version_no, v.doc_type, v.doc_date, v.included"
        " FROM sources s JOIN source_versions v ON v.source_id = s.id WHERE s.deal_id = ? AND v.version_no ="
        " (SELECT MAX(version_no) FROM source_versions WHERE source_id = s.id) ORDER BY v.doc_date, s.source_key", (did,)):
        out.append({
            "source_key": key, "name": labels[key], "source_version_id": vid, "version": version_no,
            "doc_type": doc_type, "doc_type_label": DOC_TYPE_LABELS.get(doc_type, doc_type), "date": date,
            "included": bool(included),
            "role": ("Read for promises" if doc_type in config.EXTRACTABLE_DOC_TYPES
                     else "Approval evidence" if doc_type == "pricing_services_note" else "Reference only"),
        })
    return out


CHECK_NOTE = "Only firm promises are checked against approval and the contract."


def display_status(status: str, language: str) -> str:
    """A promise that is not firm is never checked, so 'No issues raised' would overstate: say it was not checked."""
    if status == "No issues raised" and language in ("conditional", "exploratory"):
        return f"Not checked: {language} promise"
    return status


GAP_PREFIX = "Firm promise absent from the contract terms, and nothing withdraws it. "
INCORPORATED_NAMES = {"draft_sow": "SOW", "draft_contract": "draft contract"}


def progression(statements: list) -> str:
    """One line on how a promise firmed up, from its statements in document order; empty for a single statement."""
    if len(statements) < 2:
        return ""
    years = {s["date"][:4] for s in statements if s.get("date")}
    segments = []
    for s in statements:
        cite = f"{s['doc_type_label']}, {short_date(s['date'], year=len(years) > 1)}"
        if segments and segments[-1][0] == s["language"]:
            if cite not in segments[-1][1]:
                segments[-1][1].append(cite)
        else:
            segments.append((s["language"], [cite]))
    if len(segments) == 1:
        return f"Stated as {segments[0][0]} throughout ({'; '.join(segments[0][1])})"
    parts = [f"{lang} ({'; '.join(cites)})" for lang, cites in segments]
    return "Started as " + " \u2192 ".join(parts)


def presence_sentence(conn, a: dict):
    """Where a promise sits in (or is missing from) the contract, in one sentence, from the review's own sources and the
    document references it resolved. None when the case is not a plain one (the rules' text then stays, cleaned by plain())."""
    if a["presence"] not in ("absent", "included_in_draft_contract") or "Uncertain:" in (a["presence_detail"] or ""):
        return None
    contracts = [r[0] for r in conn.execute(
        "SELECT v.id FROM review_sources rs JOIN source_versions v ON v.id = rs.source_version_id"
        " WHERE rs.review_id = ? AND v.doc_type = 'draft_contract' ORDER BY v.id", (a["review_id"],))]
    if not contracts:
        return None
    incorporated = {}  # version id -> (name, where)
    for target, doc_type in conn.execute(
            "SELECT DISTINCT r.resolved_version_id, v.doc_type FROM reference_resolutions r"
            " JOIN source_versions v ON v.id = r.resolved_version_id WHERE r.review_id = ? AND r.status = 'resolved'"
            " AND r.from_version_id IN (SELECT value FROM json_each(?)) AND r.resolved_version_id NOT IN"
            " (SELECT value FROM json_each(?)) ORDER BY r.resolved_version_id", (a["review_id"], json.dumps(contracts), json.dumps(contracts))):
        row = conn.execute(
            "SELECT from_locator FROM reference_resolutions WHERE review_id = ? AND resolved_version_id = ? AND status = 'resolved'"
            " AND from_version_id IN (SELECT value FROM json_each(?)) ORDER BY id LIMIT 1",
            (a["review_id"], target, json.dumps(contracts))).fetchone()
        where = row[0].strip() if row and row[0] and row[0] in (a["presence_detail"] or "") else ""
        incorporated[target] = (INCORPORATED_NAMES.get(doc_type, DOC_TYPE_LABELS.get(doc_type, doc_type).lower()), where)

    def at(where):
        return f" ({where[:1].lower() + where[1:]})" if where else ""
    if a["presence"] == "absent":
        if not incorporated:
            return "Not in the draft contract."
        if len(incorporated) == 1:
            name, where = next(iter(incorporated.values()))
            return f"Not in the draft contract or the {name} it incorporates{at(where)}."
        return "Not in the draft contract or in what it incorporates: " + "; ".join(
            f"{n}{at(w)}" for n, w in incorporated.values()) + "."
    # included: name where the commitment's own statements sit
    holders = [r[0] for r in conn.execute(
        "SELECT DISTINCT source_version_id FROM review_statement_commitments WHERE review_id = ? AND commitment_id = ?"
        " ORDER BY source_version_id", (a["review_id"], a["commitment_id"]))]
    places = []
    for vid in holders:
        if vid in contracts:
            places.append("the draft contract")
        elif vid in incorporated:
            name, where = incorporated[vid]
            places.append(f"the {name} the contract incorporates{at(where)}")
    if not places:  # statements in other documents (calls, proposal) are not contract-side; only the chain counts
        return None
    return "In " + " and ".join(dict.fromkeys(places)) + "."


def conflict_term(conn, did: int, criteria: dict):
    """What the contract side says on the one term that differs, e.g. 'batch' or '12,000 payouts per day'; None if unknown."""
    key, term = criteria.get("conflicting_commitment"), criteria.get("differing_term")
    row = conn.execute(
        "SELECT a.terms FROM commitment_assessments a JOIN commitments c ON c.id = a.commitment_id"
        " WHERE c.deal_id = ? AND c.commitment_key = ? ORDER BY a.id DESC LIMIT 1", (did, key)).fetchone()
    ts = evidence_text.representative_terms(json.loads(row[0])) if row and row[0] else None
    if not ts:
        return None
    if term == "mode" and ts.get("mode"):
        return evidence_text.MODE_WORDS.get(ts["mode"], ts["mode"])
    q = ts.get("quantity")
    if term == "quantity" and q:
        return f"{q['value']:,} {q['unit']} per {q['period']}"
    return None


def register(conn, slug: str) -> dict:
    did = ledger_fixes.deal_id(conn, slug)
    name = conn.execute("SELECT display_name FROM deals WHERE id = ?", (did,)).fetchone()[0]
    fresh = ledger_fixes.freshness(conn, did)
    names = document_labels(conn, did)
    commitments, sort_keys = [], {}
    rows = conn.execute(
        "SELECT c.id, c.commitment_key, c.note, s.status, a.id, a.review_id, a.name, a.language, a.authorisation,"
        " a.authorisation_evidence, a.contractual_presence, a.presence_detail, a.support_state, a.evidence_refs, a.terms"
        " FROM commitments c JOIN commitment_status s ON s.commitment_id = c.id"
        " JOIN commitment_assessments a ON a.id = s.assessment_id WHERE c.deal_id = ? ORDER BY c.id", (did,)).fetchall()
    for cid, key, note, status, aid, review_id, cname, language, auth, auth_ev, presence, pdetail, support, refs_json, terms_json in rows:
        if support == "unsupported":
            prev = conn.execute("SELECT name FROM commitment_assessments WHERE commitment_id = ? AND support_state = 'supported'"
                                " ORDER BY id DESC LIMIT 1", (cid,)).fetchone()
            cname = prev[0] if prev else cname
        statements = [
            {"source_name": names[sk], "doc_type_label": DOC_TYPE_LABELS.get(dt, dt), "version": vn,
             "quote": q, "language": lang, "date": dd}
            for sk, dt, vn, q, lang, dd in conn.execute(
                "SELECT so.source_key, v.doc_type, v.version_no, st.quote, st.language, v.doc_date"
                " FROM review_statement_commitments l JOIN statements st ON st.id = l.statement_id"
                " JOIN source_versions v ON v.id = l.source_version_id JOIN sources so ON so.id = v.source_id"
                " WHERE l.commitment_id = ? AND l.review_id = (SELECT MAX(review_id) FROM review_statement_commitments"
                " WHERE commitment_id = ?) ORDER BY v.doc_date, st.ordinal", (cid, cid))]
        repl = []  # (raw rules text, plain sentence) over every assessment of this commitment, newest first
        shown_auth = shown_presence = None
        for k, (arow_auth, arow_lang, arow_refs, arow_terms, arow_ev, arow_pres, arow_detail, arow_review) in enumerate(conn.execute(
                "SELECT authorisation, language, evidence_refs, terms, authorisation_evidence, contractual_presence,"
                " presence_detail, review_id FROM commitment_assessments WHERE commitment_id = ? ORDER BY id DESC", (cid,))):
            refs_a = json.loads(arow_refs) if arow_refs else {}
            auth_plain = evidence_text.approval_text(arow_auth, arow_lang, refs_a, json.loads(arow_terms) if arow_terms else None)
            pres_plain = presence_sentence(conn, {"presence": arow_pres, "presence_detail": arow_detail, "refs": refs_a,
                                                  "review_id": arow_review, "commitment_id": cid})
            if k == 0:
                shown_auth, shown_presence = auth_plain, pres_plain
            if arow_ev and auth_plain:
                repl.append((arow_ev, auth_plain))
            if arow_detail and pres_plain:
                repl.append((GAP_PREFIX + arow_detail, pres_plain))
                repl.append((arow_detail, pres_plain))

        def explain(text):
            for raw, new in repl:
                if raw and raw in text:
                    text = text.replace(raw, new)
            return plain(text, names)

        issues = []
        conflicts = []
        for iid, itype, subject, owner, inote, absolute, raised_by, criteria in conn.execute(
                "SELECT id, issue_type, subject_key, owner_function, note, absolute_limit, raised_by, closure_criteria FROM issues"
                " WHERE commitment_id = ? ORDER BY id", (cid,)):
            state, outcome = conn.execute("SELECT state, latest_outcome FROM issue_current_state WHERE issue_id = ?",
                                          (iid,)).fetchone()
            check = conn.execute("SELECT reason, unmet, evidence_checked, check_kind FROM closure_checks WHERE issue_id = ?"
                                 " ORDER BY id DESC LIMIT 1", (iid,)).fetchone()
            step = NEXT_STEP["approval_absolute"] if itype == "approval" and absolute else NEXT_STEP.get(itype, "")
            issues.append({
                "id": iid, "type": itype, "label": issue_label(itype, subject), "state": state,
                "owner": owner, "note": plain(inote, names), "next_step": step if state != "Resolved" else "",
                "absolute_limit": bool(absolute), "raised_by": raised_by,
                "reason": explain(check[0]) if check else "",
                "unmet": [plain(u, names) for u in json.loads(check[1])] if check and check[1] else [],
                "evidence_versions": [e.get("source_version_id") for e in json.loads(check[2])] if check else [],
                "last_check": check[3] if check else None,
            })
            if itype == "conflicting_terms" and state != "Resolved":
                conflicts.append(json.loads(criteria))
        open_issues = [i for i in issues if i["state"] != "Resolved"]
        presence_label = PRESENCE_LABELS.get(presence, presence)
        for criteria_ in conflicts:
            term = conflict_term(conn, did, criteria_)
            if term:
                presence_label = f"Not in the contract: the contract says {term} instead."
                break
        shown_status = display_status(status, language)
        commitments.append({
            "id": cid, "name": display_name(cname, statements), "note": note, "status": shown_status, "language": language,
            "check_note": CHECK_NOTE if shown_status != status else "",
            "authorisation": AUTH_LABELS.get(auth, auth), "authorisation_evidence": shown_auth or plain(auth_ev, names),
            "presence": presence_label, "presence_detail": shown_presence or plain(pdetail, names),
            "progression": progression(statements),
            "supported": support == "supported",
            "attention": [i["label"] for i in open_issues], "owners": sorted({i["owner"] for i in open_issues}),
            "issues": issues, "statements": statements,
        })
        sort_keys[cid] = key
    order = {"Needs action": 0, "Needs evidence": 1, "Not in current documents": 2, "Resolved": 3, "No issues raised": 4}
    commitments.sort(key=lambda c: (order.get(c["status"], 5), sort_keys[c["id"]]))
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
