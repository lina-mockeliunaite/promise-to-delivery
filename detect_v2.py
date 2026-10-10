"""Version 2 detection (10 Oct 2026): the model finds the problems; code verifies every one.

Why: the sealed v1 run showed hand-written vocabulary does not generalise (the rules found 1 of 3 planted issues;
a single model call found 3 of 3). v2 keeps the model for what it is good at - reading paraphrase and mapping a
promise to the catalogue - and keeps code for what must be checkable. A finding is accepted only if every claim in it
can be confirmed deterministically from the documents and the catalogue:

  approval_required  the cited catalogue path exists and says 'requires_named_approval'; no pricing-note line
                     records an approval with a named approver for that scope.
  absolute_limit     the capability exists, and the cited region is absent from it, or the cited value (a network,
                     cloud, asset, mode...) appears in the promise and nowhere in that region's catalogue entry.
  over_limit         the cited catalogue limit is a number below the promised quantity, which appears in the promise;
                     no pricing-note approval with a named approver covers it.
  contract_gap       every 'missing phrase' appears in the promise and none appears anywhere in the contract chain.
  conflicting_terms  the contract quote is verbatim in the contract chain; the promised value is in the promise and
                     absent from the whole contract chain; the contract value is in the contract quote.
Every quote must appear word for word in the document it names; a promise must come from a customer-facing document.
Rejected findings are kept with their reasons and never shown as findings.

Nothing here touches the v1 pipeline or the ledger. One model call per deal review.
"""

import json
import re
from typing import Literal

import anthropic
from pydantic import BaseModel, ConfigDict

import check_quotes
import config
import extract

V2_VERSION = 2  # 2: conditional and context clarifications; number words in over_limit (10 Oct, after dev run 1)
MAX_TOKENS_V2 = 16000
CONTRACT_TYPES = ("draft_contract", "draft_sow")
INTERNAL_TYPES = ("pricing_services_note",)
MODE_WORDS = {"real_time": r"real[\s-]?time", "batch": r"batch"}
# Deliberately generic: a guard against the model missing a recorded approval, not a parser of note wording.
APPROVED_BY = re.compile(r"\bapproved by\s+[A-Z][a-z]", re.S)
NEGATED = re.compile(r"\b(?:no|not)\b[^|\n]{0,40}\bapproved by\b", re.I)


class Quote(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: str
    quote: str


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["approval_required", "absolute_limit", "over_limit", "contract_gap", "conflicting_terms"]
    commitment: str
    promise_quotes: list[Quote]
    catalogue_path: str | None
    unlisted_value: str | None
    limit_name: str | None
    promised_quantity: int | None
    missing_phrases: list[str]
    contract_quote: Quote | None
    note_quote: Quote | None
    subject: str | None
    promised_value: str | None
    contract_value: str | None
    reason: str


class Review(BaseModel):
    model_config = ConfigDict(extra="forbid")
    findings: list[Finding]


OUTPUT_FORMAT = {"type": "json_schema", "schema": anthropic.transform_schema(Review)}

SYSTEM_PROMPT = """You review a B2B software deal's paperwork for the vendor, Elva, before the deal is handed to Delivery. You report problems only, and every claim you make will be checked mechanically against the documents and the catalogue, so cite exactly.

Work through every FIRM promise Elva makes to the customer in a customer-facing document (calls, RFP responses, questionnaires, proposals, emails, and the SOW/contract themselves). Ignore exploratory or conditional statements, sales-process steps (next calls, sending documents), the customer's own obligations, and boilerplate.
- A statement qualified by a condition that has not been met ("subject to Product approval", "provided that...", "if...") is conditional even when it says "will". Do not report it.
- A sentence that describes the customer's plan or the purpose of a document ("this proposal sets out our support for your launch on <date>") is context, not a commitment by Elva. A date is a promise only where Elva itself commits to deliver by it. The pricing and services note is internal: it is evidence of approvals, never a promise.

For each firm promise, check three things and report a finding for each problem:
1. Catalogue. Map the promise to the catalogue capability and its full path (capability/region/network/asset/mode as the catalogue nests them; the region is the deal's region).
   - absolute_limit: the region, network, asset, mode, cloud or other variant promised is not in the catalogue for that capability. Anything absent is not offered and cannot be sold even with an exception. catalogue_path = "CAP-xxx/REGION"; unlisted_value = the missing value exactly as worded in the promise (or the region code if the whole region is missing).
   - approval_required: the catalogue entry says sellable "requires_named_approval" and the pricing note records no named approval WITH a named approver for that exact scope. catalogue_path = the full leaf path.
   - over_limit: the promise exceeds a numeric catalogue limit and the pricing note records no approved exception with an approver. catalogue_path = path of the entry holding the limit; limit_name = the limit's key; promised_quantity = the promised number as an integer.
2. Contract. The contract chain is the draft contract plus the SOW and annexes it incorporates.
   - contract_gap: a firm promise made outside the contract chain is absent from the contract chain and nothing withdraws it. missing_phrases = 1-3 short phrases (at most 6 words each) copied from the promise that capture its specific content (each must appear in the promise and must NOT appear anywhere in the contract chain).
   - conflicting_terms: the contract chain covers the same thing on different terms (mode, volume, date, cloud...). contract_quote = the contract-side sentence; subject = one short word or name for what both sides describe (e.g. "Polygon"), present in both the promise and the contract quote; promised_value = the term as promised (must not appear anywhere in the contract chain); contract_value = the term as the contract states it.
3. A promise can have several findings (e.g. not approved AND missing from the contract AND conflicting).

Rules for every finding:
- promise_quotes: one or more sentences copied WORD FOR WORD from the named document (source_id as given), from customer-facing documents only. Prefer the firmest statement.
- note_quote: for approval_required and over_limit, the pricing-note line (word for word) that addresses this scope, or null if the note does not mention it.
- Set fields that do not apply to null (or [] for missing_phrases).
- Do not report a promise that is standard and present in the contract. Do not report problems you cannot cite.
- reason: one or two plain sentences a sales leader would understand."""


def deal_documents(deal: str) -> list:
    """[{source_id, doc_type, date, text}] for a deal folder, in manifest order. Guarded by ALLOWED_DEALS."""
    manifest = json.loads(config.doc_path(deal, "manifest.json").read_text(encoding="utf-8"))
    return [{"source_id": d["source_id"], "doc_type": d["doc_type"], "date": d["date"],
             "text": config.doc_path(deal, d["file"]).read_text(encoding="utf-8")} for d in manifest["documents"]]


def user_message(docs: list, catalogue: dict) -> str:
    parts = [f"=== {d['source_id']} | {d['doc_type']} | {d['date']}{' | INTERNAL' if d['doc_type'] in INTERNAL_TYPES else ''} ===\n{d['text']}"
             for d in docs]
    return "CATALOGUE (complete authority):\n" + json.dumps(catalogue, ensure_ascii=False) + "\n\nDOCUMENTS:\n" + "\n\n".join(parts)


def call_model(client, docs: list, catalogue: dict, model=None) -> dict:
    model = model or config.EXTRACTION_MODEL
    response = client.messages.create(model=model, max_tokens=MAX_TOKENS_V2, system=SYSTEM_PROMPT,
                                      messages=[{"role": "user", "content": user_message(docs, catalogue)}],
                                      output_config={"format": OUTPUT_FORMAT})
    text = "".join(b.text for b in response.content if getattr(b, "type", None) == "text")
    usage = {"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens}
    out = {"model": model, "stop_reason": response.stop_reason, "usage": usage,
           "cost_usd": extract.cost_usd(usage["input_tokens"], usage["output_tokens"], model)}
    try:
        out["findings"] = [f.model_dump() for f in Review.model_validate_json(text).findings]
    except Exception as exc:  # recorded, never guessed
        out.update(findings=[], parse_error=f"{type(exc).__name__}: {str(exc)[:300]}", raw_text=text[:4000])
    return out


# --- Verification ------------------------------------------------------------------------------------------------
def _n(text) -> str:
    return check_quotes.normalise(text or "").lower()


def _contains(haystack: str, needle: str) -> bool:
    needle = _n(needle)
    return bool(needle) and needle in _n(haystack)


def _capability(catalogue: dict, cap_id: str):
    return next((c for c in catalogue.get("capabilities", []) if c.get("id") == cap_id), None)


def resolve(catalogue: dict, path: str):
    """(capability, region entry or None, leaf entry or None) for 'CAP-021/SG/Polygon/NUSD/real_time'."""
    parts = [p for p in (path or "").split("/") if p]
    cap = _capability(catalogue, parts[0]) if parts else None
    if cap is None or len(parts) < 2:
        return cap, None, None
    node = (cap.get("regions") or {}).get(parts[1])
    region = node
    for part in parts[2:]:
        if not isinstance(node, dict):
            return cap, region, None
        for key in ("networks", "assets", "modes"):
            if key in node:
                node = node[key].get(part)
                break
        else:
            return cap, region, None
    leaf = node if isinstance(node, dict) and "sellable" in node else None
    return cap, region, leaf


_UNITS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen "
                                     "fourteen fifteen sixteen seventeen eighteen nineteen".split())}
_TENS = {w: 10 * i for i, w in enumerate("_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()) if w != "_"}
_SCALES = {"hundred": 100, "thousand": 1000, "million": 1_000_000}


def word_numbers(text: str) -> set:
    """Numbers written in English words ('thirty thousand', 'one hundred and twenty thousand'), as integers."""
    found, total, current, active = set(), 0, 0, False
    for tok in re.findall(r"[a-z]+", text.lower().replace("-", " ")):
        if tok in _UNITS or tok in _TENS:
            current += _UNITS.get(tok, 0) + _TENS.get(tok, 0)
            active = True
        elif tok in _SCALES and active:
            if tok == "hundred":
                current *= 100
            else:
                total += current * _SCALES[tok]
                current = 0
        elif tok == "and" and active:
            continue
        else:
            if active:
                found.add(total + current)
            total, current, active = 0, 0, False
    if active:
        found.add(total + current)
    return found


def _number_forms(n: int) -> list:
    forms = [f"{n:,}", str(n)]
    if n % 1000 == 0:
        forms += [f"{n // 1000}k", f"{n // 1000} k", f"{n // 1000} thousand"]
    return forms


def _note_approves(notes: list, cap: dict, scope_patterns: list) -> str | None:
    """A pricing-note line recording an approval by a named person for this capability and scope, or None."""
    for note in notes:
        for line in note["text"].splitlines():
            if not (cap["id"] in line or cap["name"].lower() in line.lower()):
                continue
            if not all(re.search(p, line, re.I) for p in scope_patterns):
                continue
            if APPROVED_BY.search(line) and not NEGATED.search(line):
                return line.strip()
    return None


def _scope_pattern(part: str) -> str:
    return MODE_WORDS.get(part, re.escape(part))


def verify(finding: dict, docs: list, catalogue: dict) -> list:
    """Problems with a finding; [] means every claim in it checks out."""
    by_id = {d["source_id"]: d for d in docs}
    chain = [d for d in docs if d["doc_type"] in CONTRACT_TYPES]
    chain_text = "\n".join(d["text"] for d in chain)
    notes = [d for d in docs if d["doc_type"] in INTERNAL_TYPES]
    problems = []
    promises = finding.get("promise_quotes") or []
    if not promises:
        return ["no promise quote"]
    for q in promises:
        doc = by_id.get(q["source_id"])
        if doc is None:
            problems.append(f"unknown source {q['source_id']}")
        elif doc["doc_type"] in INTERNAL_TYPES:
            problems.append(f"{q['source_id']} is internal, not a promise to the customer")
        elif not _contains(doc["text"], q["quote"]):
            problems.append(f"quote not verbatim in {q['source_id']}")
    if problems:
        return problems
    promise_text = " ".join(q["quote"] for q in promises)
    kind = finding["kind"]

    if kind == "absolute_limit":
        parts = (finding.get("catalogue_path") or "").split("/")
        cap = _capability(catalogue, parts[0]) if parts and parts[0] else None
        if cap is None or len(parts) < 2:
            return ["absolute_limit needs an existing capability and a region (CAP-xxx/REGION)"]
        region = (cap.get("regions") or {}).get(parts[1])
        if region is None:
            return []  # the whole region is not offered for this capability
        value = (finding.get("unlisted_value") or "").strip()
        if not value:
            return ["absolute_limit within an offered region needs the unlisted value"]
        if not _contains(promise_text, value):
            return [f"'{value}' does not appear in the promise"]
        if _contains(json.dumps(region, ensure_ascii=False), value):
            return [f"'{value}' is listed in {cap['id']}/{parts[1]}; not an absolute limit"]
        return []

    if kind in ("approval_required", "over_limit"):
        cap, region, leaf = resolve(catalogue, finding.get("catalogue_path"))
        if cap is None or region is None:
            return [f"catalogue path {finding.get('catalogue_path')!r} does not exist"]
        parts = finding["catalogue_path"].split("/")
        scope = parts[2:]
        scope_patterns = [_scope_pattern(p) for p in scope]
        if kind == "approval_required":
            if leaf is None:
                return [f"catalogue path {finding['catalogue_path']!r} is not a sellable entry"]
            if leaf.get("sellable") != "requires_named_approval":
                return [f"{finding['catalogue_path']} is sellable '{leaf.get('sellable')}', not 'requires_named_approval'"]
            # The network (if any) must be named in the promise. Asset and mode are the model's reading of
            # paraphrase ("instant risk check" = real time); they are not checked against wording.
            if scope and not re.search(_scope_pattern(scope[0]), promise_text, re.I):
                return [f"the promise does not name '{scope[0]}'"]
        else:
            entry = leaf or region
            limit = (entry.get("limits") or {}).get(finding.get("limit_name") or "")
            qty = finding.get("promised_quantity")
            if not isinstance(limit, (int, float)) or not isinstance(qty, int):
                return ["over_limit needs a numeric catalogue limit and a promised quantity"]
            if qty <= limit:
                return [f"{qty:,} is within the limit {limit:,}"]
            if not any(f.lower() in promise_text.lower() for f in _number_forms(qty)) and qty not in word_numbers(promise_text):
                return [f"{qty:,} does not appear in the promise"]
        nq = finding.get("note_quote")
        if nq and (nq.get("source_id") not in {d["source_id"] for d in notes}
                   or not _contains(by_id[nq["source_id"]]["text"], nq["quote"])):
            return ["the pricing-note quote is not verbatim in a pricing note"]
        approved = _note_approves(notes, cap, scope_patterns)
        if approved:
            return [f"the pricing note records an approval: {approved}"]
        return []

    if kind == "contract_gap":
        if not chain:
            return ["no contract documents to compare against"]
        if all(by_id[q["source_id"]]["doc_type"] in CONTRACT_TYPES for q in promises):
            return ["a contract gap needs a promise made outside the contract chain"]
        phrases = [p for p in finding.get("missing_phrases") or [] if p and p.strip()]
        if not phrases:
            return ["contract_gap needs at least one missing phrase"]
        for p in phrases:
            if len(p.split()) > 6:
                return [f"'{p}' is longer than six words; a long phrase is absent from any contract by wording alone"]
            if not _contains(promise_text, p):
                return [f"'{p}' does not appear in the promise"]
            if _contains(chain_text, p):
                return [f"'{p}' appears in the contract chain"]
        return []

    if kind == "conflicting_terms":
        cq = finding.get("contract_quote")
        if not cq or cq.get("source_id") not in by_id or by_id[cq["source_id"]]["doc_type"] not in CONTRACT_TYPES:
            return ["conflicting_terms needs a quote from the contract chain"]
        if not _contains(by_id[cq["source_id"]]["text"], cq["quote"]):
            return [f"contract quote not verbatim in {cq['source_id']}"]
        pv, cv = finding.get("promised_value") or "", finding.get("contract_value") or ""
        if not pv or not cv or _n(pv) == _n(cv):
            return ["conflicting_terms needs two different values"]
        if not _contains(promise_text, pv):
            return [f"'{pv}' does not appear in the promise"]
        subject = finding.get("subject") or ""
        if not subject or not _contains(promise_text, subject) or not _contains(cq["quote"], subject):
            return ["conflicting_terms needs a subject named in both the promise and the contract quote"]
        if not _contains(cq["quote"], cv):
            return [f"'{cv}' does not appear in the contract quote"]
        if _contains(cq["quote"], pv):
            return [f"'{pv}' also appears in the contract quote"]
        return []
    return [f"unknown kind {kind}"]


def review(client, docs: list, catalogue: dict) -> dict:
    """One v2 review: model call, then verification of every finding."""
    out = call_model(client, docs, catalogue)
    accepted, rejected = [], []
    for f in out["findings"]:
        problems = verify(f, docs, catalogue)
        (rejected if problems else accepted).append({**f, "problems": problems})
    out.update(v2_version=V2_VERSION, accepted=accepted, rejected=rejected)
    return out
