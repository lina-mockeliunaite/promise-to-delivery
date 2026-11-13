"""Why a proposed finding was rejected, split for the screens (13 Nov, Round 6). Display only.

The model's proposals that the verifier rejects fall into two kinds a reader should not see alike:
  "failed"   the evidence did not verify: a quote that is not verbatim, a wrong or internal source, a path or claim that does not hold.
  "answered" the evidence verifies, but the current documents already answer the point (an approval is recorded in the pricing note,
             the contract chain now holds the phrase, the contract now says the promised value, the value is now listed).
The kind is not read from the verifier's problem text. It is derived here, at read time, by asking the verifier's own predicates
(`detect_v2._contains`, `_note_approves`, `resolve`, ...) about the stored finding and the current documents. A finding whose gap
is answered but whose quote fails verification is "failed", never "answered". Nothing is stored, and detect_v2, the ledger and the
config hash are untouched: the stored rejected records and every count in a published or sealed result stay exactly as they were.
"""
import json
import re

import detect_v2

FAILED, ANSWERED = "failed", "answered"


def _promises_hold(finding: dict, by_id: dict):
    """The promise quotes verify against the current customer-facing documents (the verifier's first gate)."""
    promises = finding.get("promise_quotes") or []
    if not promises:
        return False
    for q in promises:
        doc = by_id.get(q.get("source_id"))
        if doc is None or doc["doc_type"] in detect_v2.INTERNAL_TYPES or not detect_v2._contains(doc["text"], q.get("quote") or ""):
            return False
    return True


def classify(finding: dict, docs: list, catalogue: dict) -> str:
    by_id = {d["source_id"]: d for d in docs}
    if not _promises_hold(finding, by_id):
        return FAILED
    chain = [d for d in docs if d["doc_type"] in detect_v2.CONTRACT_TYPES]
    chain_text = "\n".join(d["text"] for d in chain)
    notes = [d for d in docs if d["doc_type"] in detect_v2.INTERNAL_TYPES]
    promise_text = " ".join(q["quote"] for q in finding["promise_quotes"])
    kind = finding.get("kind")
    answered = False
    if kind == "absolute_limit":
        parts = (finding.get("catalogue_path") or "").split("/")
        cap = detect_v2._capability(catalogue, parts[0]) if parts and parts[0] else None
        region = ((cap or {}).get("regions") or {}).get(parts[1]) if cap and len(parts) > 1 else None
        value = (finding.get("unlisted_value") or "").strip()
        answered = bool(region is not None and value and detect_v2._contains(promise_text, value)
                        and detect_v2._contains(json.dumps(region, ensure_ascii=False), value))
    elif kind in ("approval_required", "over_limit"):
        cap, region, leaf = detect_v2.resolve(catalogue, finding.get("catalogue_path"))
        if cap is not None and region is not None:
            scope = finding["catalogue_path"].split("/")[2:]
            patterns = [detect_v2._scope_pattern(p) for p in scope]
            held = True  # every other claim of the finding must still hold
            if kind == "approval_required":
                held = leaf is not None and leaf.get("sellable") == "requires_named_approval" and (
                    not scope or bool(re.search(detect_v2._scope_pattern(scope[0]), promise_text, re.I)))
            else:
                entry = leaf or region
                limit = (entry.get("limits") or {}).get(finding.get("limit_name") or "")
                qty = finding.get("promised_quantity")
                held = (isinstance(limit, (int, float)) and isinstance(qty, int) and qty > limit
                        and (any(f.lower() in promise_text.lower() for f in detect_v2._number_forms(qty))
                             or qty in detect_v2.word_numbers(promise_text)))
            answered = bool(held and detect_v2._note_approves(notes, cap, patterns))
    elif kind == "contract_gap":
        phrases = [p for p in finding.get("missing_phrases") or [] if p and p.strip()]
        outside = not all(by_id[q["source_id"]]["doc_type"] in detect_v2.CONTRACT_TYPES for q in finding["promise_quotes"])
        answered = bool(chain and outside and phrases and all(len(p.split()) <= 6 and detect_v2._contains(promise_text, p) for p in phrases)
                        and any(detect_v2._contains(chain_text, p) for p in phrases))
    elif kind == "conflicting_terms":
        cq = finding.get("contract_quote") or {}
        doc = by_id.get(cq.get("source_id"))
        pv, cv = finding.get("promised_value") or "", finding.get("contract_value") or ""
        subject = finding.get("subject") or ""
        answered = bool(doc is not None and doc["doc_type"] in detect_v2.CONTRACT_TYPES and detect_v2._contains(doc["text"], cq.get("quote") or "")
                        and pv and cv and detect_v2._n(pv) != detect_v2._n(cv) and detect_v2._contains(promise_text, pv)
                        and subject and detect_v2._contains(promise_text, subject) and detect_v2._contains(cq["quote"], subject)
                        and detect_v2._contains(cq["quote"], pv))
    return ANSWERED if answered else FAILED


def split(rejected: list, docs: list, catalogue: dict) -> dict:
    kinds = [classify(f, docs, catalogue) for f in rejected]
    return {"failed": kinds.count(FAILED), "answered": kinds.count(ANSWERED)}
