"""Bounded catalogue-search agent: a second opinion on authorisation, only where the rules could not decide.

Design (docs/BRIEF_2026-10-05.md):
- Escalation, not replacement. The rules decide every commitment first. The agent sees only firm commitments the rules
  left as 'unknown / needs review' (wording outside the parser's vocabulary, promises outside the catalogue).
- The agent interprets language; code checks evidence. The agent proposes terms (capability, network, mode, volume ...),
  each backed by a phrase copied from the quotes, plus a catalogue path and, where needed, a pricing-note line. Code
  then recomputes the verdict from those terms with the same rules (rules.catalogue_verdict, rules.note_finding). A
  verdict that its own evidence does not support, or that cites nothing, is rejected and counted as unsupported.
- Bounded: at most AGENT_MAX_TOOL_CALLS_PER_COMMITMENT tool calls per escalated commitment and
  AGENT_MAX_TOOL_CALLS_PER_DEAL per deal, and AGENT_MAX_TURNS model turns. Hitting a bound ends the run as 'capped'.
- Reads only what the rules read: the catalogue, the review's pricing notes and the commitment's own statements with
  their neighbouring paragraph. Never labels, briefs or fingerprint files.
"""

import json
import re
import time

import config
import rules
import terms

AUTHORISATIONS = ("standard_authorised", "exception_approved", "no_approval_evidence", "unknown_needs_review")

SYSTEM_PROMPT = """You check whether a vendor's sales promises are authorised. The vendor is Elva, an AML platform.

You get commitments that a rule-based checker could not decide, usually because the wording is paraphrased. For each
one, find what it promises in the catalogue's own terms and decide its authorisation. Use the tools; do not guess.

Rules you must follow:
- Authorisation comes only from the catalogue and the internal pricing and services note. Never infer approval from
  confident language, or from a promise appearing in a proposal, SOW or contract.
- standard_authorised: the catalogue entry for the exact scope is sellable as standard and the promise is within its
  limits. no_approval_evidence: the scope needs named approval (beta, roadmap, above a limit) and the pricing note
  records none, or the scope is not in the catalogue and the catalogue says unlisted items are not offered.
  exception_approved: the pricing note names an approver for this exact scope. unknown_needs_review: the promise is not
  a catalogue capability, or you cannot tell which scope it means.
- Every term you state must be backed by a phrase copied exactly from the commitment's quotes or context.
- Catalogue paths look like CAP-021/SG/Polygon/NUSD/real_time, CAP-023/SG or, for an unlisted network, CAP-021/SG/Tron.
- State quantities in the catalogue's limit units: a limit named max_payouts_per_day means unit "payouts", period "day".
- If unsure, choose unknown_needs_review. A wrong verdict is worse than an honest unknown.
- Budget: few tool calls. Look up each capability once; submit one verdict per commitment."""

TOOLS = [
    {"name": "search_catalogue",
     "description": "Find catalogue capabilities whose name contains any of the given words. Returns id, name and regions.",
     "input_schema": {"type": "object", "properties": {"words": {"type": "array", "items": {"type": "string"}}},
                      "required": ["words"]}},
    {"name": "get_capability",
     "description": "The full catalogue entry for one capability: regions, networks, assets, modes, status, sellability, limits, roadmap dates.",
     "input_schema": {"type": "object", "properties": {"capability_id": {"type": "string"}}, "required": ["capability_id"]}},
    {"name": "get_pricing_note",
     "description": "The internal pricing and services note(s) for this deal, as lines.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "submit_verdict",
     "description": "Submit the verdict for one commitment. Call once per commitment.",
     "input_schema": {
         "type": "object",
         "properties": {
             "commitment_key": {"type": "string"},
             "capability_id": {"type": ["string", "null"]},
             "network": {"type": ["string", "null"]},
             "asset": {"type": ["string", "null"]},
             "mode": {"type": ["string", "null"], "enum": ["real_time", "batch", None]},
             "region": {"type": ["string", "null"]},
             "quantity": {"type": ["object", "null"], "properties": {
                 "value": {"type": "number"}, "unit": {"type": "string"}, "period": {"type": "string"}}},
             "term_evidence": {"type": "array", "items": {"type": "object", "properties": {
                 "term": {"type": "string"}, "phrase": {"type": "string"}}, "required": ["term", "phrase"]}},
             "catalogue_path": {"type": ["string", "null"]},
             "pricing_note_line": {"type": ["string", "null"]},
             "authorisation": {"type": "string", "enum": list(AUTHORISATIONS)},
             "rationale": {"type": "string"},
         },
         "required": ["commitment_key", "capability_id", "term_evidence", "catalogue_path", "authorisation", "rationale"],
     }},
]


class AgentCapped(Exception):
    pass


# --- Tools (pure, over the catalogue and the notes) ----------------------------------------------------------

def tool_search_catalogue(catalogue, words):
    words = [w.lower() for w in words if w and len(w) > 2]
    found = []
    for cap in catalogue["capabilities"]:
        name = cap["name"].lower()
        if any(w in name for w in words):
            found.append({"id": cap["id"], "name": cap["name"], "regions": sorted(cap["regions"])})
    return found or {"result": "no capability name contains those words"}


def tool_get_capability(catalogue, capability_id):
    cap = next((c for c in catalogue["capabilities"] if c["id"] == capability_id), None)
    if cap is None:
        return {"error": f"no capability {capability_id}"}
    out = {"catalogue_rule": {k: catalogue[k] for k in ("coverage", "unlisted_rule") if k in catalogue}}
    out.update(cap)
    return out


def tool_get_pricing_note(notes):
    if not notes:
        return {"result": "no pricing and services note among the selected sources"}
    return {n.source_key: [line for line in n.text.splitlines() if line.strip()] for n in notes}


# --- Validation: code recomputes the verdict from the agent's own terms ----------------------------------------

def _norm(text):
    return re.sub(r"\s+", " ", text).strip().lower()


def validate(verdict: dict, item: dict, catalogue: dict, vocab: terms.Vocabulary, notes: list) -> dict:
    """{'accepted': bool, 'problems': [...], 'expected': authorisation, 'absolute_limit': bool, 'catalogue_paths': [...]}"""
    problems = []
    haystack = _norm(" ".join([q["quote"] for q in item["statements"]] + [q.get("context", "") for q in item["statements"]]))
    for ev in verdict.get("term_evidence") or []:
        if _norm(ev.get("phrase", "")) not in haystack or not ev.get("phrase", "").strip():
            problems.append(f"term '{ev.get('term')}' evidence phrase not found verbatim: {ev.get('phrase')!r}")
    stated = [t for t in ("network", "asset", "mode", "region", "quantity") if verdict.get(t)]
    evidenced = {ev.get("term") for ev in verdict.get("term_evidence") or []}
    for t in stated + (["capability"] if verdict.get("capability_id") else []):
        if t not in evidenced:
            problems.append(f"term '{t}' has no evidence phrase")

    cap_id = verdict.get("capability_id")
    if not cap_id:
        expected, absolute, paths = "unknown_needs_review", False, []
    else:
        cap = vocab.capabilities.get(cap_id)
        if cap is None:
            return {"accepted": False, "problems": problems + [f"unknown capability {cap_id}"], "expected": None,
                    "absolute_limit": False, "catalogue_paths": []}
        ts = {"capability": cap_id, **{t: verdict.get(t) for t in ("network", "asset", "mode", "region")}}
        q = verdict.get("quantity")
        if q:
            value = q.get("value")
            ts["quantity"] = {"value": int(value) if isinstance(value, (int, float)) and value == int(value) else value,
                              "unit": q.get("unit"), "period": q.get("period"), "bound": "max"}
        cv = rules.catalogue_verdict(catalogue, ts)
        paths = cv.paths
        if not verdict.get("catalogue_path"):
            problems.append("uncited: no catalogue path")
        elif verdict["catalogue_path"] not in paths:
            problems.append(f"catalogue path {verdict['catalogue_path']!r} is not the path for the stated terms {paths}")
        absolute = cv.kind == "absolute"
        if cv.kind == "standard":
            expected = "standard_authorised"
        elif cv.kind == "absolute":
            expected = "no_approval_evidence"
        elif cv.kind == "varies":
            expected = "unknown_needs_review"
        else:
            finding, row, _ = rules.note_finding(notes, ts, cap.name)
            expected = "unknown_needs_review" if finding == "approval_without_approver" else finding
            if expected in ("no_approval_evidence", "exception_approved") and row and verdict.get("pricing_note_line"):
                if _norm(verdict["pricing_note_line"]) not in _norm(row) and _norm(row) not in _norm(verdict["pricing_note_line"]):
                    problems.append("pricing-note line does not match the line the rules would cite")
    if verdict.get("pricing_note_line"):
        all_lines = _norm(" ".join(n.text for n in notes))
        if _norm(verdict["pricing_note_line"].strip("| ")) not in all_lines:
            problems.append("pricing-note line not found verbatim in any note")
    if verdict.get("authorisation") != expected:
        problems.append(f"authorisation {verdict.get('authorisation')} is not what its own terms and evidence give ({expected})")
    return {"accepted": not problems, "problems": problems, "expected": expected,
            "absolute_limit": absolute and not problems, "catalogue_paths": paths}


# --- The loop ---------------------------------------------------------------------------------------------------

def _user_message(items, catalogue):
    index = [f"{c['id']} {c['name']} (regions: {', '.join(sorted(c['regions']))})" for c in catalogue["capabilities"]]
    body = {"commitments": [{"commitment_key": i["commitment_key"], "language": i["language"],
                             "statements": [{"source": s["source_key"], "doc_type": s["doc_type"], "quote": s["quote"],
                                             "context": s.get("context", "")} for s in i["statements"]]}
                            for i in items]}
    return ("Catalogue index (use get_capability for details):\n" + "\n".join(index)
            + "\n\nCommitments to decide:\n" + json.dumps(body, indent=1, ensure_ascii=False))


def run_agent(client, items: list, catalogue: dict, vocab: terms.Vocabulary, notes: list, model=None) -> dict:
    """One fresh agent run over the escalated commitments of one deal. Returns verdicts, validation, usage, timing."""
    model = model or config.AGENT_MODEL
    cap_calls = min(config.AGENT_MAX_TOOL_CALLS_PER_DEAL, config.AGENT_MAX_TOOL_CALLS_PER_COMMITMENT * max(len(items), 1))
    record = {"model": model, "escalated": [i["commitment_key"] for i in items], "tool_calls": 0, "turns": 0,
              "tool_call_cap": cap_calls, "status": "complete", "usage": {"input_tokens": 0, "output_tokens": 0},
              "verdicts": {}, "duplicate_submissions": [], "log": []}
    if not items:
        record.update(status="nothing_to_escalate", seconds=0.0, cost_usd=0.0)
        return record
    keys = {i["commitment_key"] for i in items}
    by_key = {i["commitment_key"]: i for i in items}
    messages = [{"role": "user", "content": _user_message(items, catalogue)}]
    start = time.monotonic()
    try:
        while set(record["verdicts"]) != keys:
            if record["turns"] >= config.AGENT_MAX_TURNS:
                raise AgentCapped(f"turn limit {config.AGENT_MAX_TURNS}")
            record["turns"] += 1
            response = client.messages.create(model=model, max_tokens=config.AGENT_MAX_TOKENS, system=SYSTEM_PROMPT,
                                              tools=TOOLS, messages=messages)
            record["usage"]["input_tokens"] += response.usage.input_tokens
            record["usage"]["output_tokens"] += response.usage.output_tokens
            messages.append({"role": "assistant", "content": response.content})
            uses = [b for b in response.content if getattr(b, "type", None) == "tool_use"]
            if not uses:
                record["log"].append({"turn": record["turns"], "stop_reason": response.stop_reason, "note": "no tool call"})
                messages.append({"role": "user", "content": "Submit a verdict for every remaining commitment: "
                                 + ", ".join(sorted(keys - set(record["verdicts"])))})
                continue
            results = []
            for use in uses:
                record["tool_calls"] += 1
                if record["tool_calls"] > cap_calls:
                    raise AgentCapped(f"tool-call limit {cap_calls}")
                args = use.input or {}
                if use.name == "search_catalogue":
                    out = tool_search_catalogue(catalogue, args.get("words") or [])
                elif use.name == "get_capability":
                    out = tool_get_capability(catalogue, args.get("capability_id"))
                elif use.name == "get_pricing_note":
                    out = tool_get_pricing_note(notes)
                elif use.name == "submit_verdict":
                    key = args.get("commitment_key")
                    if key not in keys:
                        out = {"error": f"{key!r} is not one of the commitments to decide"}
                    elif key in record["verdicts"]:
                        record["duplicate_submissions"].append(key)
                        out = {"error": f"{key} already has a verdict; only the first counts"}
                    else:
                        record["verdicts"][key] = {"submitted": args,
                                                   "validation": validate(args, by_key[key], catalogue, vocab, notes)}
                        out = {"result": "recorded"}
                else:
                    out = {"error": f"unknown tool {use.name}"}
                record["log"].append({"turn": record["turns"], "tool": use.name, "input": args})
                results.append({"type": "tool_result", "tool_use_id": use.id, "content": json.dumps(out, ensure_ascii=False)})
            messages.append({"role": "user", "content": results})
    except AgentCapped as exc:
        record["status"] = f"capped: {exc}"
    record["seconds"] = round(time.monotonic() - start, 2)
    prices = config.PRICE_PER_MTOK.get(model) or {}
    u = record["usage"]
    record["cost_usd"] = (round((u["input_tokens"] * prices["input"] + u["output_tokens"] * prices["output"]) / 1e6, 6)
                          if prices else None)
    return record


# --- Inputs from the ledger -------------------------------------------------------------------------------------

def _paragraph_context(text: str, quote: str) -> str:
    """The paragraph before the quote's paragraph (for a call, the previous turn). Empty if none."""
    paras = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    for i, p in enumerate(paras):
        if quote in p:
            return paras[i - 1].strip() if i > 0 else ""
    return ""


def escalated_items(conn, review_id: int) -> list:
    """Firm commitments whose latest rules assessment in this review is 'unknown_needs_review'."""
    items = []
    rows = conn.execute(
        "SELECT c.id, c.commitment_key, a.language FROM commitments c JOIN commitment_assessments a"
        " ON a.commitment_id = c.id AND a.review_id = ? WHERE a.language = 'firm'"
        " AND a.authorisation = 'unknown_needs_review' ORDER BY c.id", (review_id,)).fetchall()
    for cid, key, language in rows:
        statements = []
        for skey, quote, source_key, doc_type, text in conn.execute(
            "SELECT s.statement_key, s.quote, so.source_key, v.doc_type, v.canonical_text"
            " FROM review_statement_commitments l JOIN statements s ON s.id = l.statement_id"
            " JOIN source_versions v ON v.id = l.source_version_id JOIN sources so ON so.id = v.source_id"
            " WHERE l.review_id = ? AND l.commitment_id = ? ORDER BY s.id", (review_id, cid)):
            statements.append({"statement_key": skey, "quote": quote, "source_key": source_key, "doc_type": doc_type,
                               "context": _paragraph_context(text, quote)})
        items.append({"commitment_key": key, "language": language, "statements": statements})
    return items


def review_notes(conn, review_id: int) -> list:
    import references
    return [references.Version(i, k, t, d, x, bool(inc)) for i, k, t, d, x, inc in conn.execute(
        "SELECT v.id, so.source_key, v.doc_type, v.doc_date, v.canonical_text, v.included FROM review_sources rs"
        " JOIN source_versions v ON v.id = rs.source_version_id JOIN sources so ON so.id = v.source_id"
        " WHERE rs.review_id = ? AND v.doc_type = 'pricing_services_note' AND v.included = 1"
        " ORDER BY v.doc_date DESC, v.id DESC", (review_id,))]
