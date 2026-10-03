"""Extraction cache with the full key (DESIGN.md; docs/LEDGER_SCHEMA.md section 6).

A document is a hit only when every field that can change extraction output matches: canonical-text hash, document
type, context (none today), system-prompt, template and schema hashes, model, thinking mode and parameter sent,
MAX_TOKENS and the cache-format version. Anything else re-extracts that document. Only complete extractions are stored
as reusable. Imported run-file rows are never reusable. Extraction itself is the frozen extract.py call, unchanged.
"""

import hashlib
import json

import config
import extract

CACHE_FORMAT_VERSION = "1"
NO_CONTEXT_SHA256 = hashlib.sha256(b"").hexdigest()


class ExtractionFailed(Exception):
    pass


def key_fields(canonical_sha256: str, doc_type: str) -> dict:
    hashes = extract.prompt_hashes()
    thinking = extract.thinking_param(config.THINKING_MODE, config.EXTRACTION_MODEL)
    return {
        "canonical_sha256": canonical_sha256, "doc_type": doc_type, "context_sha256": NO_CONTEXT_SHA256,
        "system_prompt_sha256": hashes["system_prompt_sha256"], "user_template_sha256": hashes["user_template_sha256"],
        "schema_sha256": hashes["schema_sha256"], "model_id": config.EXTRACTION_MODEL,
        "thinking_mode": config.THINKING_MODE,
        "thinking_param_sent": "none" if thinking is None else json.dumps(thinking, sort_keys=True),
        "max_tokens": config.MAX_TOKENS, "cache_format_version": CACHE_FORMAT_VERSION,
    }


def key_sha256(fields: dict) -> str:
    return hashlib.sha256(json.dumps(fields, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def lookup(conn, fields: dict):
    row = conn.execute("SELECT id FROM extraction_cache WHERE key_sha256 = ? AND reusable = 1",
                       (key_sha256(fields),)).fetchone()
    return row[0] if row else None


def get_or_extract(conn, client, version_id: int, canonical_text: str, canonical_sha256: str, doc_type: str,
                   statement_prefix: str):
    """(extraction_id, 'hit' | 'miss_called', cost_usd). A miss calls the model through the frozen extract.py call."""
    fields = key_fields(canonical_sha256, doc_type)
    hit = lookup(conn, fields)
    if hit is not None:
        return hit, "hit", 0.0
    if client is None:
        raise ExtractionFailed(f"source version {version_id} needs extraction and no model client was given")
    attempts, parsed = [], None
    for number in range(1, config.MAX_ATTEMPTS + 1):
        record, parsed = extract.attempt_extraction(client, doc_type, canonical_text, number)
        attempts.append(record)
        if parsed is not None:
            break
    if parsed is None:
        raise ExtractionFailed(f"source version {version_id}: extraction failed after {len(attempts)} attempts")
    keep_speaker = doc_type in config.CALL_DOC_TYPES
    statements = [{"statement_id": f"{statement_prefix}-S{n:02d}", "quote": s.quote,
                   "speaker": s.speaker if keep_speaker else config.WRITTEN_DOC_SPEAKER, "language": s.language}
                  for n, s in enumerate(parsed.statements, start=1)]
    usage = [a["usage"] for a in attempts if a["usage"]]
    costs = [a["cost_usd"] for a in attempts if a["usage"]]
    cost = None if any(c is None for c in costs) else round(sum(costs), 6)
    eid = conn.execute(
        "INSERT INTO extraction_cache (key_sha256, canonical_sha256, doc_type, context_sha256, system_prompt_sha256,"
        " user_template_sha256, schema_sha256, model_id, thinking_mode, thinking_param_sent, max_tokens,"
        " cache_format_version, output_json, usage_json, cost_usd, origin, reusable)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'model_call', 1)",
        (key_sha256(fields), fields["canonical_sha256"], doc_type, fields["context_sha256"],
         fields["system_prompt_sha256"], fields["user_template_sha256"], fields["schema_sha256"], fields["model_id"],
         fields["thinking_mode"], fields["thinking_param_sent"], fields["max_tokens"], fields["cache_format_version"],
         json.dumps(statements, ensure_ascii=False), json.dumps({"attempts": usage}), cost),
    ).lastrowid
    for n, s in enumerate(statements, start=1):
        conn.execute("INSERT INTO statements (extraction_id, ordinal, statement_key, quote, speaker, language)"
                     " VALUES (?, ?, ?, ?, ?, ?)", (eid, n, s["statement_id"], s["quote"], s["speaker"], s["language"]))
    return eid, "miss_called", cost or 0.0
