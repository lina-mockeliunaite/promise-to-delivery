"""Check that every extracted quote appears word for word in its source document.

Usage: python check_quotes.py results/extract_<deal>_<timestamp>.json
Reports failures; never edits the run file or the documents.
Exit codes: 0 all quotes found, 1 at least one failure, 2 refused or unreadable input.
"""

import json
import sys
from pathlib import Path

import config


def normalise(text: str) -> str:
    """Collapse whitespace runs (including line breaks). Nothing else is changed."""
    return " ".join(text.split())


def check_run(run: dict, sources: dict[str, str]) -> dict:
    """Compare each statement's quote with its own source text.

    sources maps source_id -> document text. Pure function, no file access.
    """
    normalised = {source_id: normalise(text) for source_id, text in sources.items()}
    failures = []
    ambiguous = []
    checked = 0

    for doc in run.get("documents", []):
        for stmt in doc.get("statements", []):
            checked += 1
            quote = normalise(stmt["quote"])
            source_id = stmt["source_id"]
            base = {"statement_id": stmt["statement_id"], "source_id": source_id, "quote": stmt["quote"]}

            if source_id not in normalised:
                failures.append({**base, "reason": "source_id_not_in_manifest", "found_in_other_sources": []})
                continue
            if not quote:
                failures.append({**base, "reason": "empty_quote", "found_in_other_sources": []})
                continue

            count = normalised[source_id].count(quote)
            if count == 0:
                elsewhere = [s for s, text in normalised.items() if s != source_id and quote in text]
                failures.append({**base, "reason": "not_found_in_source", "found_in_other_sources": elsewhere})
            elif count > 1:
                ambiguous.append({**base, "matches": count})

    return {
        "checked": checked,
        "failed": len(failures),
        "failures": failures,
        "ambiguous": ambiguous,
        "documents_not_complete": [
            {"source_id": d.get("source_id"), "status": d.get("status")}
            for d in run.get("documents", [])
            if d.get("status") != "complete"
        ],
    }


def load_sources(deal: str) -> dict[str, str]:
    """Read the manifest and the documents it lists. Never touches labels or other files."""
    manifest = json.loads(config.doc_path(deal, "manifest.json").read_text(encoding="utf-8"))
    sources = {}
    for entry in manifest["documents"]:
        sources[entry["source_id"]] = config.doc_path(deal, entry["file"]).read_text(encoding="utf-8")
    return sources


def print_report(report: dict) -> None:
    print(f"Checked {report['checked']} quotes: {report['checked'] - report['failed']} found, {report['failed']} failed.")
    for f in report["failures"]:
        print(f"\nFAIL {f['statement_id']} ({f['source_id']}): {f['reason']}")
        print(f"  quote: {f['quote']!r}")
        if f["found_in_other_sources"]:
            print(f"  appears instead in: {', '.join(f['found_in_other_sources'])}")
    for a in report["ambiguous"]:
        print(f"\nNOTE {a['statement_id']} ({a['source_id']}): quote matches {a['matches']} places in its source")
    for d in report["documents_not_complete"]:
        print(f"\nNOTE document {d['source_id']} has status {d['status']!r}; no quotes were checked for it")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    try:
        run = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
        # Guard runs before any file under data/ is read.
        sources = load_sources(run["deal"])
    except config.DealNotAllowed as exc:
        print(f"Refused: {exc}")
        return 2
    except (OSError, KeyError, ValueError) as exc:
        print(f"Could not read input: {exc}")
        return 2

    report = check_run(run, sources)
    print_report(report)
    return 1 if report["failed"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
