"""Real-model check of the PDF and Word adapters (Lina runs this, with her key; about $0.01 per document).

    .venv/bin/python check_formats.py [--pdf FILE]... [--docx FILE]...

Extracts the Harbour Bank proposal (HB-04) once from each variant and compares the statements with the Markdown HB-04
statements in the pinned Harbour Bank run file: are the firm statements the same, and does every quote appear in the
text the adapter produced (with its page, for PDFs)? The variants are always the generated PDF and Word versions of
HB-04 (tests/fixtures/make_formats.py). --pdf and --docx add a file you exported yourself (from Word or Pages), which
is the realistic case; the comparison is only meaningful if that file has HB-04's content.

Reads ANTHROPIC_API_KEY from the environment and never prints it. Reads the run file, never the labels, never anything
under data/ except HB-04 through config.doc_path (via the fixtures) and refuses files inside the data folder. Writes
results/formats_check_<UTC timestamp>.json; record the cost and the verdict in DECISIONS.md.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import adapters
import check_quotes
import config
import extract

sys.path.insert(0, str(Path(__file__).resolve().parent / "tests" / "fixtures"))
import make_formats  # noqa: E402  (development fixtures: HB-04 as PDF and DOCX)


def baseline_hb04() -> list:
    """[(quote, language)] of HB-04 in the pinned Harbour Bank run file (the Markdown extraction)."""
    path = config.RESULTS_DIR / config.LEDGER_IMPORT_RUN_FILES["harbour_bank"]
    run = json.loads(path.read_text(encoding="utf-8"))
    doc = next(d for d in run["documents"] if d.get("source_id") == "HB-04")
    return [(s["quote"], s["language"]) for s in doc["statements"]]


def read_user_file(path_text: str) -> tuple:
    """(file name, bytes) of a file the user exported. Refuses anything inside the data folder or over 10 MB."""
    path = Path(path_text).expanduser().resolve()
    if path.is_relative_to(config.DATA_DIR.resolve()):
        raise ValueError("refused: give a file outside the data folder")
    if not path.is_file():
        raise ValueError(f"refused: {path.name} is not a file")
    if path.stat().st_size > adapters.MAX_UPLOAD_BYTES:
        raise ValueError(f"refused: {path.name} is larger than 10 MB")
    return path.name, path.read_bytes()


def compare_firm(baseline: list, variant: list) -> dict:
    """Firm statements of the variant against the baseline: same quote, same by containment, missing, extra."""
    norm = check_quotes.normalise
    base = [norm(q) for q, lang in baseline if lang == "firm"]
    got = [norm(q) for q, lang in variant if lang == "firm"]
    exact = [q for q in base if q in got]
    near = [q for q in base if q not in got and any(q in g or g in q for g in got)]
    missing = [q for q in base if q not in exact and q not in near]
    near_got = [g for g in got if g not in base and any(b in g or g in b for b in base)]
    extra = [g for g in got if g not in base and g not in near_got]
    return {"same": len(exact), "same_by_containment": len(near), "missing": missing, "extra": extra,
            "agrees": not missing and not extra}


def check_variant(client, label: str, filename: str, raw: bytes, baseline: list) -> dict:
    out = {"variant": label, "format": None, "problems": [], "refused": None, "extraction": None, "cost_usd": None,
           "statements": [], "quotes_found": None, "quotes_missing": [], "pages": {}, "firm": None}
    try:
        adapted = adapters.adapt(filename, raw)
    except adapters.AdapterError as exc:
        out["refused"] = str(exc)
        return out
    out.update(format=adapted["format"], problems=adapted["problems"])
    record, parsed = extract.attempt_extraction(client, "proposal", adapted["canonical_text"], 1)
    out["cost_usd"] = record.get("cost_usd")
    if parsed is None:
        out["extraction"] = f"failed ({record.get('error_kind')})"
        return out
    out["extraction"] = "ok"
    out["statements"] = [(s.quote, s.language) for s in parsed.statements]
    missing = [q for q, _ in out["statements"] if not adapters.quote_in_text(adapted["canonical_text"], q)]
    out["quotes_found"] = len(out["statements"]) - len(missing)
    out["quotes_missing"] = missing
    if adapted["adapter_name"] == adapters.PDF_ADAPTER_NAME:
        out["pages"] = {q: adapters.locate_page(adapted["canonical_text"], adapted["location_map"], q)
                        for q, _ in out["statements"]}
    out["firm"] = compare_firm(baseline, out["statements"])
    return out


def run_check(client, user_files: list) -> dict:
    baseline = baseline_hb04()
    variants = [("generated PDF of HB-04", "hb04.pdf", make_formats.hb04_pdf()),
                ("generated Word version of HB-04", "hb04.docx", make_formats.hb04_docx())] + user_files
    results = [check_variant(client, label, name, raw, baseline) for label, name, raw in variants]
    cost = sum(r["cost_usd"] or 0 for r in results)
    ok = all(r["extraction"] == "ok" and not r["quotes_missing"] and r["firm"]["agrees"] for r in results)
    return {"baseline_statements": len(baseline), "baseline_firm": sum(1 for _, lang in baseline if lang == "firm"),
            "results": results, "total_cost_usd": round(cost, 6), "all_agree": ok}


def print_report(report: dict) -> None:
    print(f"Baseline: Markdown HB-04 has {report['baseline_statements']} statements, {report['baseline_firm']} firm.")
    for r in report["results"]:
        print(f"\n{r['variant']} ({r['format'] or 'not read'})")
        if r["refused"]:
            print(f"  Refused by the adapter: {r['refused']}")
            continue
        for p in r["problems"]:
            print(f"  Adapter note: {p}")
        print(f"  Extraction: {r['extraction']}; {len(r['statements'])} statements; cost ${r['cost_usd'] or 0:.4f}")
        if r["extraction"] != "ok":
            continue
        print(f"  Quotes found in the adapter's text: {r['quotes_found']} of {len(r['statements'])}")
        for q in r["quotes_missing"]:
            print(f"    NOT FOUND: {q[:100]}")
        f = r["firm"]
        print(f"  Firm statements vs Markdown: {f['same']} same, {f['same_by_containment']} same by containment, "
              f"{len(f['missing'])} missing, {len(f['extra'])} extra")
        for q in f["missing"]:
            print(f"    MISSING: {q[:100]}")
        for q in f["extra"]:
            print(f"    EXTRA:   {q[:100]}")
        if r["pages"]:
            print("  Pages: " + ", ".join(f"{p}" for p in sorted({v for v in r["pages"].values() if v})))
    print(f"\nTotal cost ${report['total_cost_usd']:.4f}. Verdict: "
          f"{'firm statements agree and every quote is valid' if report['all_agree'] else 'differences found; read above'}.")


def main(argv: list) -> int:
    files, args, i = [], list(argv), 0
    while i < len(args):
        if args[i] in ("--pdf", "--docx") and i + 1 < len(args):
            try:
                name, raw = read_user_file(args[i + 1])
            except ValueError as exc:
                print(exc, file=sys.stderr)
                return 2
            files.append((f"your {'PDF' if args[i] == '--pdf' else 'Word file'} ({name})", name, raw))
            i += 2
        else:
            print("usage: python check_formats.py [--pdf FILE]... [--docx FILE]...", file=sys.stderr)
            return 2
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set.", file=sys.stderr)
        return 2
    import anthropic
    report = run_check(anthropic.Anthropic(), files)
    print_report(report)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = config.RESULTS_DIR / f"formats_check_{stamp}.json"
    out.write_text(json.dumps({"timestamp_utc": stamp, "model": config.EXTRACTION_MODEL, **report}, indent=2, ensure_ascii=False),
                   encoding="utf-8")
    print(f"Saved {out.name}. Record the cost and verdict in DECISIONS.md.")
    return 0 if report["all_agree"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
