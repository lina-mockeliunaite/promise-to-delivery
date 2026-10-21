"""Does a draft's fix survive into the signed paperwork? (21 Oct)

A gap closed by a draft contract or SOW is only as good as the agreement that is signed. When a signed contract or signed SOW is in
the deal, this checks every gap that is closed by documents and whose closure relies on contract or SOW wording (a "missing from the
contract" or a "contract says something different" finding closed by a draft). It is deterministic and calls no model:

- what it looks for is the closing wording, the contract sentence that now matches (workspace.matching_contract_wording: the first
  sentence in a current draft that contains the claim's promised value, or one of its searched phrases);
- it matches against the signed document's own text after normalising both sides the same way (see `normalise`): whitespace collapsed,
  lower-case, curly quotes straightened, punctuation ignored, and numbers and their word forms equal ("12" and "twelve", 0 to 100). It stays
  strict on wording: a word added, dropped or changed ("listed in" against "as listed in") is a different sentence and reopens the gap.

Outcomes, per closed gap:
  confirmed      the sentence is in a signed document: "Confirmed in the signed contract (Signed contract, 20 Oct)"
  not_found      it is in no signed document: the closure is no longer supported by the paperwork that counts, so the screens show the
                 commitment as Needs attention with "The fix in <closing document> was not found in the signed contract." The earlier
                 closure stays visible
  not_confirmed  the closure has no lookup sentence to look for (for example a conflict that closed because the old clause vanished):
                 a neutral "Not confirmed against the signed contract"
Approval-only closures (the pricing note) are not affected by signed paperwork and are skipped. With no signed document, nothing.

This is a layer computed when a page is read. The ledger is not changed (the closure stays recorded as Resolved), and no file inside the
config hash is touched, so no review goes stale. A signed document that newly contains wording for an open gap does not close it.

Limits, stated: a gap closed in an SOW is confirmed only if the signed document repeats the wording. A signed contract that incorporates
the revised SOW by reference, without repeating it, would wrongly reopen the gap: it errs toward attention.
"""

import re

import workspace

SIGNED_TYPES = ("signed_contract", "signed_sow")
DRAFT_TYPES = ("draft_contract", "draft_sow")
CHECKED_KINDS = ("contract_gap", "conflicting_terms")


# --- Matching (21 Oct) ----------------------------------------------------------------------------------------------------------------
# The check is strict on wording but not on typography or on how a number is written. Both sides go through the same normalisation, then
# the closing sentence must be a run of whole words in the signed text. Nothing is fuzzy: no synonyms, no reordering, no near matches.
_UNITS = {w: n for n, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split())}
_TENS = {w: 10 * n for n, w in enumerate("_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()) if w != "_"}
_QUOTES = str.maketrans({"\u2018": "'", "\u2019": "'", "\u201a": "'", "\u201b": "'", "\u201c": '"', "\u201d": '"', "\u201e": '"'})


def _numbers_as_digits(tokens: list) -> list:
    """Number words from zero to 100 become digits ("twelve" -> "12", "twenty one" -> "21", "one hundred" -> "100")."""
    out, i = [], 0
    while i < len(tokens):
        t = tokens[i]
        nxt = tokens[i + 1] if i + 1 < len(tokens) else None
        if t == "one" and nxt == "hundred":
            out.append("100")
            i += 2
        elif t in _TENS and nxt in _UNITS and 1 <= _UNITS[nxt] <= 9:
            out.append(str(_TENS[t] + _UNITS[nxt]))
            i += 2
        elif t in _TENS:
            out.append(str(_TENS[t]))
            i += 1
        elif t in _UNITS:
            out.append(str(_UNITS[t]))
            i += 1
        else:
            out.append(t)
            i += 1
    return out


def normalise(text) -> str:
    """Lower-case, straight quotes, thousands commas removed, every other punctuation mark treated as a space, whitespace collapsed,
    and number words from zero to 100 written as digits. The same function is applied to the closing sentence and to the signed text."""
    t = str(text or "").translate(_QUOTES).lower()
    t = re.sub(r"(?<=\d),(?=\d{3}\b)", "", t)  # 1,000 and 1000 are the same number
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return " ".join(_numbers_as_digits(t.split()))


def contains(text, sentence) -> bool:
    """True if the normalised sentence is a run of whole words in the normalised text."""
    needle = normalise(sentence)
    return bool(needle) and f" {needle} " in f" {normalise(text)} "


def signed_documents(conn, did: int, slug: str) -> list:
    """The signed paperwork in the deal: [{label, date, type, text}] for each included signed contract or SOW."""
    out = []
    for d in workspace.documents(conn, slug):
        if not d["included"] or d["doc_type"] not in SIGNED_TYPES:
            continue
        (text,) = conn.execute("SELECT canonical_text FROM source_versions WHERE id = ?", (d["source_version_id"],)).fetchone()
        out.append({"label": d["name"], "date": d["version_date"] or d["date"], "type": d["doc_type"], "text": text or ""})
    return out


def _chain(conn, did: int, labels: dict) -> list:
    import ledger_v2
    chain = [{"text": d["text"], "label": labels.get(d["source_id"], d["source_id"]), "key": d["source_id"], "type": d["doc_type"]}
             for d in ledger_v2.current_docs(conn, did) if d["doc_type"] in DRAFT_TYPES]
    chain.sort(key=lambda d: (d["type"] != "draft_contract", d["key"]))
    return chain


def _kind(signed: list) -> str:
    return "signed contract" if any(s["type"] == "signed_contract" for s in signed) else "signed SOW"


def evaluate(conn, did: int, slug: str) -> dict:
    """{issue id: result} for the closed gaps this check applies to. {} when there is no signed paperwork."""
    signed = signed_documents(conn, did, slug)
    if not signed:
        return {}
    import json
    import ledger_v2
    labels = workspace.document_labels(conn, did)
    chain = _chain(conn, did, labels)
    version_types = {v: t for v, t in conn.execute(
        "SELECT v.id, v.doc_type FROM source_versions v JOIN sources s ON s.id = v.source_id WHERE s.deal_id = ?", (did,))}
    kind = _kind(signed)
    results = {}
    for iid, criteria in conn.execute(
            "SELECT i.id, i.closure_criteria FROM issues i JOIN issue_current_state s ON s.issue_id = i.id"
            " JOIN commitments c ON c.id = i.commitment_id WHERE c.deal_id = ? AND s.state = 'Resolved'"
            f" AND i.issue_type IN ({','.join('?' * len(CHECKED_KINDS))}) ORDER BY i.id", (did, *CHECKED_KINDS)):
        closed = workspace.resolved_by(conn, did, iid, labels)
        if closed is None:
            continue
        closing_types = {version_types.get(d["source_version_id"]) for d in closed["documents"]}
        if not closing_types & set(DRAFT_TYPES):
            continue  # not closed by contract or SOW wording
        claim = (json.loads(criteria or "{}") or {}).get("claim") or {}
        earlier = closed["text"]
        by = "; ".join(closed["changed"] or [d["label"] for d in closed["documents"]])
        lookup = workspace.matching_contract_wording(claim, chain)
        base = {"earlier": earlier, "closed_by": by, "kind": kind}
        if lookup is None:
            results[iid] = {**base, "status": "not_confirmed", "text": "Not confirmed against the signed contract"
                            if kind == "signed contract" else "Not confirmed against the signed SOW"}
            continue
        hit = next((s for s in signed if contains(s["text"], lookup["quote"])), None)
        if hit:
            when = workspace.short_date(hit["date"], year=False)
            results[iid] = {**base, "status": "confirmed", "sentence": lookup["quote"], "signed": hit["label"], "date": hit["date"],
                            "text": f"Confirmed in the {_kind([hit])} ({hit['label']}{', ' + when if when else ''})"}
        else:
            results[iid] = {**base, "status": "not_found", "sentence": lookup["quote"],
                            "reason": f"The fix in {by} was not found in the {kind}.",
                            "text": f"Closed earlier by {by}, but not found in the {kind}"}
    return results


def reopened(conn, did: int, slug: str) -> dict:
    """{issue id: commitment id} for the closed gaps that are shown as Needs attention again because the signed paperwork lacks the fix."""
    found = {iid for iid, r in evaluate(conn, did, slug).items() if r["status"] == "not_found"}
    if not found:
        return {}
    marks = ",".join("?" * len(found))
    return dict(conn.execute(f"SELECT id, commitment_id FROM issues WHERE id IN ({marks})", tuple(found)).fetchall())
