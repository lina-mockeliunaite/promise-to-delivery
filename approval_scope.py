"""Does a named approval start in time for the promise it was filed against? (12 Nov, Round 5)

A pricing-note approval closes the approval gap when it names the approver (detect_v2.verify). That says nothing about *when* the approval starts. This
layer adds one deterministic check, computed when a page is read, in the way signed_check.py is: the ledger is not changed (the gap stays recorded as
Resolved), nothing in the config hash is touched (detect_v2.py, ledger_v2.py and the rules are not edited, so no review goes stale and no reading-cache
key moves), and no model is called.

When both dates are explicit and the approval's effective date is later than the commitment's start date, the approval gap is shown as Needs attention
again, with the reason: "The signed start date is earlier than the approved start date." (or "The contract start date…", "The promised start date…",
by the source the start date comes from). With either date missing, nothing changes. Nothing here decides anything else.

Dates, parsed from quotes that are already verified (the approval line the verifier matched; the commitment's own quotes and wording):
- Approval effective date: an explicit day-month-year date introduced by "from", "effective (from)", "with effect from" or "starting", in the approval
  line. Any other date in the line (the issue date, "on 16 October 2026") is ignored. The document's own date is the issue date and stays separate.
- Commitment start date: the explicit date in the sentence of the firmest source that states the commitment: the signed contract or SOW, then the draft
  contract or SOW, then the customer's promise. The sentence is located with the commitment's own searched phrases (the same lookup the contract-gap
  display uses); the promise comes from the approval finding's verified promise quotes. The firmest located source decides: if its sentence has no explicit
  date there is no start date, and a weaker source is not consulted. A sentence (or a set of promise quotes) with two different dates counts as no date.
- Only day-month-year dates are read ("1 May 2027", "1st May 2027", "May 1, 2027", "2027-05-01"). Quarters, half-years, a month with no day, a day with
  no year, "mid-2027", "at launch" and numeric day/month forms ("01/05/2027", ambiguous) are no date.
- An approval's end date ("until 30 June 2027") is ignored: an approval that expires early is not caught.

Only the approval already filed against the commitment is compared: the approval finding's catalogue entry and scope pick the note line (the verifier's own
rule); there is no matching by feature name.
"""

import datetime
import json
import re

import detect_v2
import signed_check
import workspace

MONTHS = {m: n for n, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"], 1)}
MONTHS.update({"jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12})
_MONTH = "(?:" + "|".join(sorted(MONTHS, key=len, reverse=True)) + r")\.?"
_DATE = re.compile(
    rf"(?<![\w/-])(?:(?P<d1>\d{{1,2}})(?:st|nd|rd|th)?\s+(?P<m1>{_MONTH})\s+(?P<y1>\d{{4}})"
    rf"|(?P<m2>{_MONTH})\s+(?P<d2>\d{{1,2}})(?:st|nd|rd|th)?,?\s+(?P<y2>\d{{4}})"
    r"|(?P<y3>\d{4})-(?P<mo3>\d{2})-(?P<d3>\d{2}))(?![\w/-])", re.I)
_INTRO = re.compile(r"\b(?:with\s+effect\s+from|effective(?:\s+from)?|starting|from)\s+(?:the\s+)?", re.I)

COVERED, NOT_COVERED, NO_DATES = "covered", "not_covered", "no_dates"
REASON = {"signed": "The signed start date is earlier than the approved start date.",
          "contract": "The contract start date is earlier than the approved start date.",
          "promise": "The promised start date is earlier than the approved start date."}
NO_DATES_NOTE = "No start dates to compare."
LABEL_OPEN = "Approval starts later"  # the finding's name while the gap is held open by approval scope


def _to_date(m):
    try:
        if m.group("y3"):
            return datetime.date(int(m.group("y3")), int(m.group("mo3")), int(m.group("d3")))
        d, mo, y = (m.group("d1"), m.group("m1"), m.group("y1")) if m.group("d1") else (m.group("d2"), m.group("m2"), m.group("y2"))
        return datetime.date(int(y), MONTHS[mo.lower().rstrip(".")], int(d))
    except (ValueError, KeyError):
        return None


def dates_in(text) -> list:
    """Every explicit day-month-year date in the text, in order, as datetime.date; an impossible date (31 February) is skipped."""
    return [d for d in (_to_date(m) for m in _DATE.finditer(str(text or ""))) if d]


def explicit_date(text):
    """The one explicit date a sentence states, or None: no date, or two different dates (ambiguous), is no date."""
    found = set(dates_in(text))
    return next(iter(found)) if len(found) == 1 else None


def effective_date(line):
    """The approval's effective date: the date directly after "from", "effective (from)", "with effect from" or "starting"; any other date is ignored. Two
    different introduced dates, or none, is None."""
    text = str(line or "")
    found = set()
    for m in _INTRO.finditer(text):
        d = _DATE.match(text, m.end())
        if d and _to_date(d):
            found.add(_to_date(d))
    return next(iter(found)) if len(found) == 1 else None


def short_date(d) -> str:
    return f"{d.day} {d.strftime('%b')}" if d else ""


def _claim(criteria) -> dict:
    return (json.loads(criteria or "{}") or {}).get("claim") or {}


def _approval_line(conn, claim, docs):
    """(line, document) of the pricing-note line the verifier itself matches for this approval claim, or (None, None)."""
    import integrity
    catalogue = json.loads(integrity.catalogue_bytes(conn).decode("utf-8"))
    cap, region, _leaf = detect_v2.resolve(catalogue, claim.get("catalogue_path"))
    if cap is None or region is None:
        return None, None
    notes = [d for d in docs if d["doc_type"] in detect_v2.INTERNAL_TYPES]
    scope = [detect_v2._scope_pattern(p) for p in (claim.get("catalogue_path") or "").split("/")[2:]]
    line = detect_v2._note_approves(notes, cap, scope)
    if not line:
        return None, None
    return line, next((d for d in notes if line in [x.strip() for x in d["text"].splitlines()]), None)


def _start_from_signed(contract_claim, signed):
    near = signed_check.related_clause(contract_claim, signed) if contract_claim else None
    if not near:
        return None
    return {"source": "signed", "sentence": near["sentence"], "label": near["label"], "key": near["key"], "version_id": near["version_id"],
            "date": explicit_date(near["sentence"]), "in": near["in"]}


def _start_from_draft(contract_claim, chain):
    """The draft contract or SOW sentence that states the commitment, found like the signed one: the sentence holding the most of the commitment's searched phrases, headings skipped
    (a heading such as "## 5. Scam-call alerts" names the feature and states no date), the first sentence on a tie, the contract before the SOW."""
    near = signed_check.related_clause(contract_claim, chain) if contract_claim else None
    if not near:
        return None
    doc = next((d for d in chain if d["version_id"] == near["version_id"]), {})
    return {"source": "contract", "sentence": near["sentence"], "label": near["label"], "key": near["key"], "version_id": near["version_id"],
            "date": explicit_date(near["sentence"]), "in": "draft SOW" if doc.get("type") == "draft_sow" else "draft contract"}


def _start_from_promise(claim, by_key, labels):
    quotes = [q for q in claim.get("promise_quotes") or [] if q.get("quote")]
    if not quotes:
        return None
    distinct = {d for q in quotes for d in dates_in(q["quote"])}
    date = next(iter(distinct)) if len(distinct) == 1 else None
    pick = next((q for q in quotes if date in dates_in(q["quote"])), quotes[0]) if date else quotes[0]
    doc = by_key.get(pick["source_id"]) or {}
    return {"source": "promise", "sentence": pick["quote"], "label": labels.get(pick["source_id"], pick["source_id"]), "key": pick["source_id"],
            "version_id": doc.get("version_id"), "date": date, "in": "promise"}


def evaluate(conn, did: int, slug: str) -> dict:
    """{issue id: result} for the approval gaps a pricing-note approval closed. Each result: status (covered / not_covered / no_dates), the approval
    ({date, line, label, key, version_id, doc_date}), the start ({date, sentence, label, key, version_id, source, in}), the reason when not covered, and a
    note ("No start dates to compare.") when exactly one of the two dates was found. {} when no approval gap was closed by a note. Dates are ISO strings."""
    import ledger_v2
    rows = conn.execute(
        "SELECT i.id, i.commitment_id, i.closure_criteria FROM issues i JOIN issue_current_state s ON s.issue_id = i.id JOIN commitments c ON c.id = i.commitment_id"
        " WHERE c.deal_id = ? AND s.state = 'Resolved' AND i.issue_type = 'approval' ORDER BY i.id", (did,)).fetchall()
    if not rows:
        return {}
    docs = ledger_v2.current_docs(conn, did)
    labels = workspace.document_labels(conn, did)
    by_key = {d["source_id"]: d for d in docs}
    chain = [{"text": d["text"], "label": labels.get(d["source_id"], d["source_id"]), "key": d["source_id"], "type": d["doc_type"], "version_id": d["version_id"]}
             for d in docs if d["doc_type"] in ("draft_contract", "draft_sow")]
    chain.sort(key=lambda d: (d["type"] != "draft_contract", d["key"]))
    signed = signed_check.signed_documents(conn, did, slug)
    issued = {d["source_version_id"]: d["version_date"] or d["date"] for d in workspace.documents(conn, slug)}  # a document's own (issue) date, as the screens show it
    out = {}
    for iid, cid, criteria in rows:
        claim = _claim(criteria)
        if claim.get("kind") not in ("approval_required", "over_limit"):
            continue
        line, note = _approval_line(conn, claim, docs)
        if not line:
            continue  # nothing recorded now: the ledger's own state stands
        approval_date = effective_date(line)
        # The commitment's own contract-side finding gives the searched phrases that locate its wording in the signed and draft text.
        contract_claim = next((c for c in (_claim(x) for (x,) in conn.execute(
            "SELECT closure_criteria FROM issues WHERE commitment_id = ? AND issue_type IN ('contract_gap', 'conflicting_terms') ORDER BY id", (cid,)))
            if c.get("kind") in ("contract_gap", "conflicting_terms")), None)
        start = _start_from_signed(contract_claim, signed) or _start_from_draft(contract_claim, chain) or _start_from_promise(claim, by_key, labels)
        start_date = start["date"] if start else None
        res = {"catalogue_path": claim.get("catalogue_path"), "approval": {"date": approval_date.isoformat() if approval_date else None, "line": line,
                            "label": labels.get(note["source_id"], note["source_id"]) if note else None,
                            "key": note["source_id"] if note else None, "version_id": note["version_id"] if note else None,
                            "doc_date": issued.get(note["version_id"]) if note else None},
               "start": {**start, "date": start_date.isoformat() if start_date else None} if start else None}
        if approval_date and start_date:
            if approval_date > start_date:
                res.update(status=NOT_COVERED, reason=REASON[start["source"]])
            else:
                res.update(status=COVERED)
        else:
            res.update(status=NO_DATES, note=NO_DATES_NOTE if (approval_date or start_date) else None)
        out[iid] = res
    return out


def reopened(conn, did: int, slug: str) -> dict:
    """{issue id: commitment id} for the approval gaps held open because the approval starts later than the commitment."""
    held = {iid for iid, r in evaluate(conn, did, slug).items() if r["status"] == NOT_COVERED}
    if not held:
        return {}
    marks = ",".join("?" * len(held))
    return dict(conn.execute(f"SELECT id, commitment_id FROM issues WHERE id IN ({marks})", tuple(held)).fetchall())


def for_record(conn, did: int, slug: str, snapshot: dict) -> dict:
    """The approval-scope detail of each gap a locked record lists as held open by it (finding "Approval starts later"), found at display time: {"<promise>|<finding>":
    result}. Read-only and not part of the saved snapshot, so its fingerprint cannot move; a record locked before this check has no such finding and gets {}."""
    wanted = [(item["promise"], f) for item in [*(snapshot.get("open_items") or []), *(snapshot.get("resolved_by_note") or [])]
              for f in item.get("findings") or [] if f.get("finding") == LABEL_OPEN]
    if not wanted:
        return {}
    held = [r for r in evaluate(conn, did, slug).values() if r["status"] == NOT_COVERED]
    out = {}
    for promise, f in wanted:
        hit = next((r for r in held if r["catalogue_path"] == f.get("catalogue_path")), None)
        if hit:
            out[f"{promise}|{f['finding']}"] = hit
    return out
