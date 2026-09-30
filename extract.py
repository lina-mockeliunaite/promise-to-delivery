"""Extraction v1: one model call per extractable document in a deal's manifest.

Usage: python extract.py harbour_bank
The model returns only quote, speaker and language. The code attaches source_id,
doc_type, date and statement_id, and saves every run to results/.
Exit codes: 0 all extractable documents complete, 1 an incomplete or flagged document, 2 refused/cannot start.
"""

import argparse
import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timezone

import anthropic
from pydantic import ValidationError

import config
from schema import DocExtraction, StoredStatement

log = logging.getLogger("extract")

SYSTEM_PROMPT = """You read one document from a vendor's sales record and list every commitment that the vendor, Elva, makes to the customer.

What to extract
- Only statements by Elva. Ignore statements by the customer, the customer's own obligations, questions, background, and descriptions that promise nothing.
- A commitment is a statement in which Elva says it will do, deliver, provide, support or guarantee something, or states that a capability, date, volume, service or responsibility applies to this customer's deal.
- A sentence that states its own terms is a statement even if it also points elsewhere for detail. A sentence that only points elsewhere (for example "see the annex") and states no terms itself is not a statement.
- Do not judge whether Elva is authorised to make the promise, or whether it is true. Only record what the document says.
- If the document contains no such statements, return an empty list.

Fields
- quote: the single sentence that carries the commitment, copied exactly, character for character, from the document. Do not paraphrase, shorten, merge sentences, fix typos or change punctuation. Leave out speaker labels and neighbouring sentences. Do not return the same sentence twice.
- speaker: in a call transcript, the name of the Elva speaker as the transcript labels them. In any other document, "Elva".
- language: how firmly the sentence is worded.
  - exploratory: A possible customer-facing capability or outcome under consideration, without a decision to provide it ("we could support", "we may offer", "we're exploring whether we could provide"). A bare plan to investigate or confirm coverage is a next step, so exclude it.
  - conditional: a customer-relevant commitment or roadmap target qualified by an explicit condition, dependency or planning language about delivery or availability ("if", "subject to", "planned", "targeted", "expected"); a future date alone does not make an otherwise firm promise conditional.
  - firm: stated without qualification as something that will happen, is available, or is delivered.

List statements in the order they appear."""

USER_TEMPLATE = "Document type: {doc_type}\n\n<document>\n{text}\n</document>"

# Exactly what is sent as output_config["format"]; the run file hashes this same object.
OUTPUT_FORMAT = {"type": "json_schema", "schema": anthropic.transform_schema(DocExtraction)}


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def prompt_hashes() -> dict:
    """Full SHA-256 of the exact system prompt, the static user-message template and the canonical schema.

    Canonical schema = the JSON sent to the API, keys sorted, no extra whitespace.
    A wording or schema change shows up as a different hash between runs.
    """
    canonical_schema = json.dumps(OUTPUT_FORMAT["schema"], sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return {
        "system_prompt_sha256": _sha256(SYSTEM_PROMPT),
        "user_template_sha256": _sha256(USER_TEMPLATE),
        "schema_sha256": _sha256(canonical_schema),
    }


# --- Cost and usage ------------------------------------------------------

def cost_usd(input_tokens: int, output_tokens: int, model: str | None = None) -> float | None:
    """Cost from config prices; None if the model's prices are not set."""
    prices = config.PRICE_PER_MTOK.get(model or config.EXTRACTION_MODEL) or {}
    if prices.get("input") is None or prices.get("output") is None:
        return None
    return round((input_tokens * prices["input"] + output_tokens * prices["output"]) / 1_000_000, 6)


def usage_record(usage) -> dict:
    """Token counts exactly as the response reports them. thinking_tokens is null if the response gives none."""
    details = getattr(usage, "output_tokens_details", None)
    thinking = getattr(details, "thinking_tokens", None) if details is not None else None
    return {
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "thinking_tokens": thinking,
    }


def _short(text: str, limit: int = 2000) -> str:
    return text if len(text) <= limit else text[:limit] + f"... [{len(text) - limit} more characters]"


# --- Run settings --------------------------------------------------------

THINKING_MODES = ("model_default", "off")


def thinking_param(mode: str, model: str) -> dict | None:
    """The `thinking` request parameter for a mode, or None to send none.

    model_default sends no parameter. off sends {"type": "disabled"}, which only some models accept;
    the rest would answer 400, so refuse before any call.
    """
    if mode == "model_default":
        return None
    if mode == "off":
        if model not in config.THINKING_DISABLED_ACCEPTED:
            raise ValueError(f"--thinking off is not supported for model {model!r}; "
                             f"models known to accept thinking 'disabled': {config.THINKING_DISABLED_ACCEPTED}")
        return {"type": "disabled"}
    raise ValueError(f"THINKING_MODE {mode!r} is not implemented; only {list(THINKING_MODES)}")


# --- One model call ------------------------------------------------------

def attempt_extraction(client, doc_type: str, text: str, number: int,
                       model: str | None = None, thinking_mode: str | None = None) -> tuple[dict, DocExtraction | None]:
    """One call. Returns (attempt record for the run log, parsed result or None)."""
    model = model or config.EXTRACTION_MODEL
    thinking = thinking_param(thinking_mode or config.THINKING_MODE, model)
    record = {"attempt": number, "ok": False, "error_kind": None, "error": None,
              "stop_reason": None, "usage": None, "cost_usd": None}
    try:
        # No `thinking` argument in "model_default" mode; {"type": "disabled"} in "off" mode.
        extra = {} if thinking is None else {"thinking": thinking}
        response = client.messages.create(
            model=model,
            max_tokens=config.MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": USER_TEMPLATE.format(doc_type=doc_type, text=text)}],
            output_config={"format": OUTPUT_FORMAT},
            **extra,
        )
    except anthropic.APIError as exc:  # the SDK has already retried transient network errors itself
        record.update(error_kind="api_error", error=_short(f"{type(exc).__name__}: {exc}"))
        return record, None

    record["stop_reason"] = response.stop_reason
    record["usage"] = usage_record(response.usage)
    record["cost_usd"] = cost_usd(response.usage.input_tokens, response.usage.output_tokens, model)
    reply = "".join(block.text for block in response.content if block.type == "text")

    if response.stop_reason == "max_tokens":
        record.update(error_kind="truncated", error=f"reply hit max_tokens={config.MAX_TOKENS}", raw_text=_short(reply, 4000))
        return record, None
    if response.stop_reason == "refusal":
        record.update(error_kind="refusal", error="model refused", raw_text=_short(reply, 4000))
        return record, None
    try:
        parsed = DocExtraction.model_validate_json(reply)
    except ValidationError as exc:
        record.update(error_kind="validation", error=_short(str(exc)), raw_text=_short(reply, 4000))
        return record, None

    record["ok"] = True
    return record, parsed


# --- One document --------------------------------------------------------

def _tokens_and_cost(attempts: list[dict]) -> dict:
    used = [a["usage"] for a in attempts if a["usage"]]
    thinking = [u["thinking_tokens"] for u in used if u["thinking_tokens"] is not None]
    costs = [a["cost_usd"] for a in attempts if a["usage"]]
    return {
        "input_tokens": sum(u["input_tokens"] for u in used),
        "output_tokens": sum(u["output_tokens"] for u in used),
        "thinking_tokens": sum(thinking) if thinking else None,
        "cost_usd": None if any(c is None for c in costs) else round(sum(costs), 6),
    }


def stored_statements(entry: dict, parsed: DocExtraction) -> list[dict]:
    """Attach code-owned fields. The model's speaker is kept only for calls."""
    keep_model_speaker = entry["doc_type"] in config.CALL_DOC_TYPES
    rows = []
    for n, stmt in enumerate(parsed.statements, start=1):
        rows.append(StoredStatement(
            quote=stmt.quote,
            speaker=stmt.speaker if keep_model_speaker else config.WRITTEN_DOC_SPEAKER,
            language=stmt.language,
            statement_id=f"{entry['source_id']}-S{n:02d}",
            source_id=entry["source_id"],
            doc_type=entry["doc_type"],
            date=entry["date"],
        ).model_dump())
    return rows


def extract_document(client, deal: str, entry: dict, model: str | None = None, thinking_mode: str | None = None) -> dict:
    doc = {"source_id": entry["source_id"], "file": entry["file"], "doc_type": entry["doc_type"],
           "date": entry["date"], "status": None, "error": None, "attempts": [], "statements": []}

    if entry["doc_type"] in config.REFERENCE_ONLY_DOC_TYPES:
        doc["status"] = "skipped_reference_only"
        log.info("%s: %s is reference-only; not extracted", entry["source_id"], entry["doc_type"])
        return doc
    if entry["doc_type"] not in config.EXTRACTABLE_DOC_TYPES:
        doc["status"] = "flagged_unsupported_type"
        log.warning("%s: doc_type %r is in neither EXTRACTABLE nor REFERENCE_ONLY; flagged, not extracted",
                    entry["source_id"], entry["doc_type"])
        return doc

    try:
        text = config.doc_path(deal, entry["file"]).read_text(encoding="utf-8")
    except (OSError, ValueError) as exc:
        doc.update(status="incomplete", error=f"could not read document: {exc}")
        log.warning("%s: %s", entry["source_id"], doc["error"])
        return doc

    parsed = None
    for number in range(1, config.MAX_ATTEMPTS + 1):
        attempt, parsed = attempt_extraction(client, entry["doc_type"], text, number, model, thinking_mode)
        doc["attempts"].append(attempt)
        if parsed is not None:
            break
        log.warning("%s: attempt %d/%d failed (%s): %s", entry["source_id"], number, config.MAX_ATTEMPTS,
                    attempt["error_kind"], attempt["error"])

    if parsed is None:
        doc["status"] = "incomplete"
        log.error("%s: marked incomplete after %d attempts", entry["source_id"], config.MAX_ATTEMPTS)
    else:
        doc["status"] = "complete"
        doc["statements"] = stored_statements(entry, parsed)
    doc.update(_tokens_and_cost(doc["attempts"]))
    return doc


# --- One run -------------------------------------------------------------

def run_extraction(client, deal: str, model: str | None = None, thinking_mode: str | None = None) -> dict:
    config.deal_dir(deal)  # guard: raises DealNotAllowed for any deal not in ALLOWED_DEALS, before any deal file is read
    model = model or config.EXTRACTION_MODEL
    thinking_mode = thinking_mode or config.THINKING_MODE
    thinking = thinking_param(thinking_mode, model)  # raises ValueError before any file read or call

    manifest = json.loads(config.doc_path(deal, "manifest.json").read_text(encoding="utf-8"))
    documents = [extract_document(client, deal, entry, model, thinking_mode) for entry in manifest["documents"]]

    counts: dict[str, int] = {}
    for d in documents:
        counts[d["status"]] = counts.get(d["status"], 0) + 1
    called = [d for d in documents if d["attempts"]]
    return {
        "deal": deal,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": model,
        "max_tokens": config.MAX_TOKENS,
        "thinking_mode": thinking_mode,
        "thinking_param_sent": thinking,  # the literal `thinking` request parameter; null = none sent
        "prompt_hashes": prompt_hashes(),
        "price_per_mtok_usd": config.PRICE_PER_MTOK.get(model),
        "status_counts": counts,
        "totals": _tokens_and_cost([a for d in called for a in d["attempts"]]),
        "documents": documents,
    }


def save_run(run: dict) -> str:
    """Write a new file in results/. Never overwrites an earlier run."""
    stamp = datetime.fromisoformat(run["timestamp_utc"]).strftime("%Y%m%dT%H%M%SZ")
    path = config.RESULTS_DIR / f"extract_{run['deal']}_{stamp}.json"
    config.RESULTS_DIR.mkdir(exist_ok=True)
    with open(path, "x", encoding="utf-8") as fh:
        json.dump(run, fh, indent=2, ensure_ascii=False)
    return str(path)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Extract Elva commitments from a deal's documents.")
    parser.add_argument("deal")
    parser.add_argument("--model", default=config.EXTRACTION_MODEL,
                        help="model ID (default: config.EXTRACTION_MODEL)")
    parser.add_argument("--thinking", choices=THINKING_MODES, default=config.THINKING_MODE,
                        help="model_default sends no thinking parameter; off sends thinking={'type': 'disabled'}")
    args = parser.parse_args(argv[1:])
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    try:
        config.deal_dir(args.deal)  # refuse before anything else happens
    except config.DealNotAllowed as exc:
        print(f"Refused: {exc}")
        return 2
    try:
        thinking_param(args.thinking, args.model)
    except ValueError as exc:
        print(f"Refused: {exc}")
        return 2
    if not os.environ.get("ANTHROPIC_API_KEY"):  # presence only; the value is never read or printed
        print("ANTHROPIC_API_KEY is not set.")
        return 2

    run = run_extraction(anthropic.Anthropic(), args.deal, args.model, args.thinking)
    path = save_run(run)

    for d in run["documents"]:
        print(f"{d['source_id']}  {d['doc_type']:<22} {d['status']:<26} {len(d['statements'])} statements")
    t = run["totals"]
    print(f"\nTokens in/out: {t['input_tokens']}/{t['output_tokens']}  (thinking reported: {t['thinking_tokens']})  cost: {t['cost_usd']} USD")
    if args.model not in config.PRICE_PER_MTOK:
        print(f"No price configured for {args.model}; cost is null.")
    if args.thinking == "off" and t["thinking_tokens"]:
        print(f"WARNING: thinking was disabled but {t['thinking_tokens']} thinking tokens were reported.")
    print(f"Saved {path}")
    bad = {"incomplete", "flagged_unsupported_type"}
    return 1 if bad & set(run["status_counts"]) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
