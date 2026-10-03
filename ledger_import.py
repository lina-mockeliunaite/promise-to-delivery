"""Development import: the frozen run files become ledger rows. No model calls, no API key.

Usage: python ledger_import.py [--rebuild]
Builds workspace/ledger.sqlite from scratch. Refuses if it already exists unless --rebuild is given;
--rebuild builds next to it and swaps it in, so a failed rebuild leaves the old database intact.
Exit codes: 0 built, 2 refused.

Only deals in config.LEDGER_DEALS are imported, each from the run file pinned in
config.LEDGER_IMPORT_RUN_FILES. Source documents are read through config.doc_path (inside docs/ only);
labels are never opened. Imported extraction rows are never reusable: the run file does not record the
content hash the model saw (docs/LEDGER_SCHEMA.md section 6).
"""

import hashlib
import json
import os
import sqlite3
import sys
from pathlib import Path

import config
import ledger

ADAPTER_NAME = "text_markdown"
ADAPTER_VERSION = "1"
LANGUAGES = ("exploratory", "conditional", "firm")
STATUS_COMPLETE = "complete"
STATUS_SKIPPED = "skipped_reference_only"


class LedgerImportError(Exception):
    """Raised when the import refuses: nothing has been written."""


def sha256_hex(data) -> str:
    return hashlib.sha256(data.encode("utf-8") if isinstance(data, str) else data).hexdigest()


def markdown_adapter(raw: bytes) -> dict:
    """Text/Markdown adapter: canonical text is what extract.py read (UTF-8, line endings as \\n).

    location_map is the paragraphs (runs of non-blank lines) as character offsets into the canonical text.
    """
    text = raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    paragraphs, start, end, offset = [], None, 0, 0
    for line in text.splitlines(keepends=True):
        if line.strip():
            if start is None:
                start = offset
            end = offset + len(line.rstrip())
        elif start is not None:
            paragraphs.append({"paragraph": len(paragraphs) + 1, "start": start, "end": end})
            start = None
        offset += len(line)
    if start is not None:
        paragraphs.append({"paragraph": len(paragraphs) + 1, "start": start, "end": end})
    return {
        "canonical_text": text,
        "location_map": json.dumps(paragraphs),
        "adapter_name": ADAPTER_NAME,
        "adapter_version": ADAPTER_VERSION,
    }


# --- Reading and validating (no database) --------------------------------

def _refuse(slug: str, message: str):
    raise LedgerImportError(f"{slug}: {message}")


def _read_json(path: Path, slug: str, what: str):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        _refuse(slug, f"cannot read {what}: {exc}")


def read_plan(slug: str) -> dict:
    """Read and validate everything the import needs for one deal. Raises before anything is written."""
    ledger.require_ledger_deal(slug)

    pinned = config.LEDGER_IMPORT_RUN_FILES.get(slug)
    if pinned is None:
        _refuse(slug, "no run file is pinned in LEDGER_IMPORT_RUN_FILES")
    latest = ledger.discover_run_files().get(slug)
    if latest is None:
        _refuse(slug, "no run file found")
    if latest.name != pinned:
        _refuse(slug, f"the latest run file is {latest.name}, not the pinned {pinned}; change the pin on purpose")

    run = _read_json(latest, slug, "run file")
    if run.get("deal") != slug:
        _refuse(slug, f"run file is for deal {run.get('deal')!r}")
    try:
        hashes = run["prompt_hashes"]
        for key in ("system_prompt_sha256", "user_template_sha256", "schema_sha256"):
            hashes[key]
        for key in ("model", "max_tokens", "thinking_mode", "thinking_param_sent"):
            run[key]
    except (KeyError, TypeError) as exc:
        _refuse(slug, f"run file is missing {exc}")

    manifest = _read_json(config.doc_path(slug, "manifest.json"), slug, "manifest")
    if manifest.get("deal") != slug:
        _refuse(slug, f"manifest is for deal {manifest.get('deal')!r}")

    run_docs = {}
    for doc in run.get("documents", []):
        if doc.get("source_id") in run_docs:
            _refuse(slug, f"run file lists {doc.get('source_id')} twice")
        run_docs[doc.get("source_id")] = doc
    manifest_ids = [e.get("source_id") for e in manifest.get("documents", [])]
    if len(set(manifest_ids)) != len(manifest_ids):
        _refuse(slug, "manifest lists a source twice")
    if set(manifest_ids) != set(run_docs):
        _refuse(slug, f"manifest sources {sorted(manifest_ids)} differ from run file sources {sorted(run_docs)}")

    docs = []
    for entry in manifest["documents"]:
        sid = entry["source_id"]
        doc = run_docs[sid]
        for field in ("file", "doc_type", "date"):
            if doc.get(field) != entry.get(field):
                _refuse(slug, f"{sid}: {field} differs between manifest ({entry.get(field)!r}) and run file ({doc.get(field)!r})")
        doc_type, status = entry["doc_type"], doc.get("status")
        if status == STATUS_COMPLETE:
            if doc_type not in config.EXTRACTABLE_DOC_TYPES:
                _refuse(slug, f"{sid}: {doc_type!r} is complete in the run file but not extractable")
        elif status == STATUS_SKIPPED:
            if doc_type not in config.REFERENCE_ONLY_DOC_TYPES:
                _refuse(slug, f"{sid}: {doc_type!r} is skipped but not reference-only")
            if doc.get("statements"):
                _refuse(slug, f"{sid}: a skipped document has statements")
        else:
            _refuse(slug, f"{sid}: status {status!r} cannot be imported (only {STATUS_COMPLETE} or {STATUS_SKIPPED})")

        statements = doc.get("statements") or []
        for n, stmt in enumerate(statements, start=1):
            expected_id = f"{sid}-S{n:02d}"
            if stmt.get("statement_id") != expected_id:
                _refuse(slug, f"{sid}: statement {n} has id {stmt.get('statement_id')!r}, expected {expected_id!r}")
            for field, want in (("source_id", sid), ("doc_type", doc_type), ("date", entry["date"])):
                if stmt.get(field) != want:
                    _refuse(slug, f"{expected_id}: {field} is {stmt.get(field)!r}, expected {want!r}")
            if not isinstance(stmt.get("quote"), str) or not stmt["quote"]:
                _refuse(slug, f"{expected_id}: empty quote")
            if stmt.get("language") not in LANGUAGES:
                _refuse(slug, f"{expected_id}: language {stmt.get('language')!r}")

        try:
            raw = config.doc_path(slug, entry["file"]).read_bytes()
            adapted = markdown_adapter(raw)
        except (OSError, ValueError) as exc:
            _refuse(slug, f"{sid}: cannot read {entry['file']}: {exc}")
        docs.append({"entry": entry, "run_doc": doc, "statements": statements, "raw": raw, **adapted})

    return {"slug": slug, "run_file": latest.name, "run": run, "docs": docs}


# --- Writing --------------------------------------------------------------

def _insert(conn, sql, *args) -> int:
    return conn.execute(sql, args).lastrowid


def _insert_statements(conn, extraction_id: int, statements: list) -> None:
    for n, stmt in enumerate(statements, start=1):
        conn.execute(
            "INSERT INTO statements (extraction_id, ordinal, statement_key, quote, speaker, language)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (extraction_id, n, stmt["statement_id"], stmt["quote"], stmt.get("speaker"), stmt["language"]),
        )


def _write_plan(conn, plan: dict) -> None:
    slug, run, run_file = plan["slug"], plan["run"], plan["run_file"]
    deal_id = ledger.create_development_deal(conn, slug, commit=False)

    version_ids, source_set_lines = {}, []
    for d in plan["docs"]:
        entry = d["entry"]
        source_id = _insert(
            conn, "INSERT INTO sources (deal_id, source_key, display_name) VALUES (?, ?, ?)",
            deal_id, entry["source_id"], entry["file"],
        )
        canonical_sha = sha256_hex(d["canonical_text"])
        version_ids[entry["source_id"]] = _insert(
            conn,
            "INSERT INTO source_versions (source_id, version_no, original_sha256, canonical_sha256, adapter_name,"
            " adapter_version, doc_type, doc_date, original_filename, canonical_text, location_map)"
            " VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            source_id, sha256_hex(d["raw"]), canonical_sha, d["adapter_name"], d["adapter_version"],
            entry["doc_type"], entry["date"], entry["file"], d["canonical_text"], d["location_map"],
        )
        source_set_lines.append(f"{entry['source_id']}:1:{canonical_sha}:{entry['doc_type']}:{entry['date']}")

    review_id = _insert(
        conn,
        "INSERT INTO reviews (deal_id, run_kind, checker, source_set_sha256, decision_evidence_sha256, status,"
        " cost_usd, note) VALUES (?, 'review', 'rules', ?, ?, 'running', 0.0, ?)",
        deal_id, sha256_hex("\n".join(sorted(source_set_lines))), sha256_hex(""),
        f"build-time import of {run_file}; no model calls",
    )

    thinking_sent = "none" if run["thinking_param_sent"] is None else json.dumps(run["thinking_param_sent"], sort_keys=True)
    for d in plan["docs"]:
        sid, run_doc = d["entry"]["source_id"], d["run_doc"]
        if run_doc["status"] == STATUS_SKIPPED:
            conn.execute(
                "INSERT INTO review_sources (review_id, source_version_id, extraction_id, cache_outcome)"
                " VALUES (?, ?, NULL, 'not_extracted')",
                (review_id, version_ids[sid]),
            )
            continue
        usage = {k: run_doc.get(k) for k in ("input_tokens", "output_tokens", "thinking_tokens", "attempts")}
        extraction_id = _insert(
            conn,
            "INSERT INTO extraction_cache (doc_type, system_prompt_sha256, user_template_sha256, schema_sha256,"
            " model_id, thinking_mode, thinking_param_sent, max_tokens, output_json, usage_json, cost_usd, origin,"
            " source_run_file, reusable) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'imported_run_file', ?, 0)",
            d["entry"]["doc_type"], run["prompt_hashes"]["system_prompt_sha256"],
            run["prompt_hashes"]["user_template_sha256"], run["prompt_hashes"]["schema_sha256"],
            run["model"], run["thinking_mode"], thinking_sent, run["max_tokens"],
            json.dumps(d["statements"], ensure_ascii=False), json.dumps(usage), run_doc.get("cost_usd"), run_file,
        )
        _insert_statements(conn, extraction_id, d["statements"])
        conn.execute(
            "INSERT INTO review_sources (review_id, source_version_id, extraction_id, cache_outcome)"
            " VALUES (?, ?, ?, 'imported')",
            (review_id, version_ids[sid], extraction_id),
        )

    conn.execute(
        "UPDATE reviews SET status = 'complete', finished_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = ?",
        (review_id,),
    )


def _import_deal(conn: sqlite3.Connection, slug: str) -> None:
    """Validate, then write one deal. Never commits."""
    ledger.require_ledger_deal(slug)
    if conn.execute("SELECT 1 FROM deals WHERE slug = ?", (slug,)).fetchone():
        _refuse(slug, "deal already imported; the import never merges into an existing deal")
    _write_plan(conn, read_plan(slug))


def import_deal(conn: sqlite3.Connection, slug: str) -> None:
    """Import one deal atomically: all its rows are written, or none."""
    try:
        _import_deal(conn, slug)
    except BaseException:
        conn.rollback()
        raise
    conn.commit()


def import_all(conn: sqlite3.Connection) -> None:
    """Import every deal in LEDGER_DEALS in one transaction: all rows are written, or none."""
    try:
        for slug in config.LEDGER_DEALS:
            _import_deal(conn, slug)
    except BaseException:
        conn.rollback()
        raise
    conn.commit()


def table_counts(conn: sqlite3.Connection) -> dict:
    tables = [
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' AND name <> 'schema_meta'"
            " ORDER BY name"
        )
    ]
    return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}


# --- Building the database ------------------------------------------------

def build(db_path=None, rebuild: bool = False) -> dict:
    """Build the ledger from scratch and return its table counts.

    Refuses if the database exists and rebuild is False. The new database is built beside the old one and
    swapped in only on success.
    """
    final = Path(db_path) if db_path is not None else config.LEDGER_DB_PATH
    if final.exists() and not rebuild:
        raise LedgerImportError(f"{final.name} already exists; use --rebuild to replace it")
    final.parent.mkdir(parents=True, exist_ok=True)
    building = final.with_name(final.name + ".building")
    building.unlink(missing_ok=True)  # leftover from an earlier crash: our own temporary file

    conn = None
    try:
        conn = ledger.open_ledger(building)
        import_all(conn)
        counts = table_counts(conn)
        conn.close()
        conn = None
        os.replace(building, final)
    except BaseException:
        if conn is not None:
            conn.close()
        building.unlink(missing_ok=True)
        raise
    return counts


def main(argv: list) -> int:
    rebuild = "--rebuild" in argv
    unknown = [a for a in argv if a != "--rebuild"]
    if unknown:
        print(f"unknown arguments: {unknown}\nusage: python ledger_import.py [--rebuild]", file=sys.stderr)
        return 2
    try:
        counts = build(rebuild=rebuild)
    except (LedgerImportError, ledger.LedgerDealNotAllowed) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    print(f"built {config.LEDGER_DB_PATH}")
    for table, n in counts.items():
        print(f"  {table:32} {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
