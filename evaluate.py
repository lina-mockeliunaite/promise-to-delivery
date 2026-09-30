"""Score an extraction run against the deal's labelled statements. No API calls.

Usage: python evaluate.py results/extract_<deal>_<timestamp>.json [--threshold 0.8]

Matching: Jaccard overlap of lowercase alphanumeric word sets, same source_id only,
assigned one-to-one greedily from the highest score down.
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import config

HEDGED = ("exploratory", "conditional")


# --- Matching ------------------------------------------------------------

def words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def detail_lost(label_quote: str, output_quote: str) -> list[str]:
    """Label words containing a digit that are missing from the output.

    Caveat: this compares word sets, so a digit token that appears elsewhere in the
    output (for example "1" in another date) can mask a number that is missing.
    """
    out = words(output_quote)
    return sorted(w for w in words(label_quote) if any(c.isdigit() for c in w) and w not in out)


def assign(labels: list[dict], outputs: list[dict], threshold: float, floor: float) -> dict:
    """One-to-one greedy assignment. `outputs` must already exclude ineligible statements."""
    label_words = {l["id"]: words(l["quote"]) for l in labels}
    out_words = {o["statement_id"]: words(o["quote"]) for o in outputs}

    scored = []
    for l in labels:
        for o in outputs:
            if l["source_id"] == o["source_id"]:
                s = jaccard(label_words[l["id"]], out_words[o["statement_id"]])
                scored.append((s, l, o))
    scored.sort(key=lambda t: (-t[0], t[1]["id"], t[2]["statement_id"]))

    used_labels, used_outputs, matches = set(), set(), []
    for s, l, o in scored:
        if s < threshold:
            break
        if l["id"] in used_labels or o["statement_id"] in used_outputs:
            continue
        used_labels.add(l["id"])
        used_outputs.add(o["statement_id"])
        matches.append((s, l, o))

    near_misses = [
        (s, l, o) for s, l, o in scored
        if floor <= s < threshold
        and l["id"] not in used_labels and o["statement_id"] not in used_outputs
    ]
    return {
        "matches": matches,
        "near_misses": near_misses,
        "unmatched_labels": [l for l in labels if l["id"] not in used_labels],
        "unmatched_outputs": [o for o in outputs if o["statement_id"] not in used_outputs],
    }


# --- Evaluation ----------------------------------------------------------

def ratio(num: int, den: int):
    return num / den if den else None


def evaluate(run: dict, labels: list[dict], threshold: float, floor: float) -> dict:
    """Score one run. Statements from documents whose status is not 'complete' cannot
    match any label: they count as false positives, and the labels for those sources
    stay false negatives."""
    eligible, ineligible, non_complete = [], [], []
    for doc in run["documents"]:
        stmts = doc.get("statements") or []
        if doc.get("status") == "complete":
            eligible.extend(stmts)
        else:
            ineligible.extend(stmts)
            non_complete.append({
                "source_id": doc.get("source_id"),
                "status": doc.get("status"),
                "labels_affected": sorted(l["id"] for l in labels if l["source_id"] == doc.get("source_id")),
            })

    res = assign(labels, eligible, threshold, floor)
    matches = res["matches"]

    tp = len(matches)
    fp_list = res["unmatched_outputs"] + ineligible
    fn_list = res["unmatched_labels"]
    firm = [l for l in labels if l["language"] == "firm"]
    firm_tp = sum(1 for _, l, _ in matches if l["language"] == "firm")

    confusion: dict[str, dict[str, int]] = {}
    agree = 0
    hedge_errors, mismatches, lost = [], [], []
    for s, l, o in matches:
        confusion.setdefault(l["language"], {}).setdefault(o["language"], 0)
        confusion[l["language"]][o["language"]] += 1
        agree += l["language"] == o["language"]
        if l["language"] != o["language"]:
            mismatches.append(_pair(s, l, o))
        if l["language"] in HEDGED and o["language"] == "firm":
            hedge_errors.append(_pair(s, l, o))
        missing = detail_lost(l["quote"], o["quote"])
        if missing:
            lost.append({**_pair(s, l, o), "missing": missing})

    return {
        "threshold": threshold,
        "near_miss_floor": floor,
        "counts": {"tp": tp, "fp": len(fp_list), "fn": len(fn_list),
                   "labels": len(labels), "outputs": len(eligible) + len(ineligible)},
        "precision": ratio(tp, tp + len(fp_list)),
        "recall": ratio(tp, tp + len(fn_list)),
        "recall_firm": ratio(firm_tp, len(firm)),
        "language_accuracy": ratio(agree, tp),
        "language_confusion": confusion,
        "language_mismatches": mismatches,
        "hedge_errors": hedge_errors,
        "non_complete_documents": non_complete,
        "false_positives": [_out(o) for o in fp_list],
        "false_negatives": [_lab(l) for l in fn_list],
        "near_misses": [_pair(s, l, o) for s, l, o in res["near_misses"]],
        "detail_lost": lost,
    }


def _lab(l: dict) -> dict:
    return {"label_id": l["id"], "source_id": l["source_id"], "language": l["language"], "quote": l["quote"]}


def _out(o: dict) -> dict:
    return {"statement_id": o["statement_id"], "source_id": o["source_id"],
            "language": o["language"], "quote": o["quote"]}


def _pair(score: float, l: dict, o: dict) -> dict:
    return {"score": round(score, 3), "source_id": l["source_id"],
            "label_id": l["id"], "label_language": l["language"], "label_quote": l["quote"],
            "statement_id": o["statement_id"], "output_language": o["language"], "output_quote": o["quote"]}


# --- I/O -----------------------------------------------------------------

def validate_run_path(path_arg: str) -> Path:
    """Resolve the path and require results/extract_*.json inside RESULTS_DIR."""
    path = Path(path_arg).resolve()
    results = config.RESULTS_DIR.resolve()
    if path.parent != results or not re.fullmatch(r"extract_.+\.json", path.name):
        raise ValueError(f"{path_arg!r} is not a results/extract_*.json file")
    return path


def load_labels(deal: str) -> tuple[list[dict], str]:
    """Return the labels and the SHA-256 of the exact bytes they were parsed from."""
    path = config.deal_dir(deal) / "labels" / "statements.json"
    raw = path.read_bytes()
    return json.loads(raw.decode("utf-8"))["statements"], hashlib.sha256(raw).hexdigest()


def output_path(run_path: Path, threshold: float, labels_sha: str) -> Path:
    return config.RESULTS_DIR / f"eval_{run_path.stem}_t{threshold:g}_L{labels_sha[:8]}.json"


def fmt(x) -> str:
    return "n/a" if x is None else f"{x:.3f}"


def print_report(rep: dict) -> None:
    c = rep["counts"]
    print(f"Labels sha256: {rep['labels_sha256'][:8]}")
    print(f"Threshold {rep['threshold']:g} (near-miss floor {rep['near_miss_floor']:g})")
    print(f"Labels {c['labels']}, outputs {c['outputs']}")
    print(f"TP {c['tp']}  FP {c['fp']}  FN {c['fn']}")
    print(f"Precision {fmt(rep['precision'])}  Recall {fmt(rep['recall'])}  "
          f"Recall (firm labels) {fmt(rep['recall_firm'])}")
    print(f"Language accuracy on matched pairs: {fmt(rep['language_accuracy'])}")
    print("Confusion (label -> extracted):")
    for lab, row in sorted(rep["language_confusion"].items()):
        print(f"  {lab}: " + ", ".join(f"{k}={v}" for k, v in sorted(row.items())))
    print(f"Hedge discipline: {len(rep['hedge_errors'])} exploratory/conditional label(s) extracted as firm")

    print("\nDocuments not complete (their labels count as FN):")
    for d in rep["non_complete_documents"] or []:
        print(f"  {d['source_id']}: {d['status']}; labels {d['labels_affected'] or 'none'}")
    if not rep["non_complete_documents"]:
        print("  none")

    def section(title, items, show):
        print(f"\n{title} ({len(items)}):")
        for it in items:
            print(show(it))

    section("False positives", rep["false_positives"],
            lambda o: f"  [{o['source_id']}] {o['statement_id']} ({o['language']}): {o['quote']}")
    section("False negatives", rep["false_negatives"],
            lambda l: f"  [{l['source_id']}] {l['label_id']} ({l['language']}): {l['quote']}")
    pair = lambda p: (f"  [{p['source_id']}] score {p['score']} {p['label_id']} vs {p['statement_id']}\n"
                      f"    label:  {p['label_quote']}\n    output: {p['output_quote']}")
    section("Near-misses", rep["near_misses"], pair)
    section("Language mismatches on matched pairs", rep["language_mismatches"],
            lambda p: f"  [{p['source_id']}] {p['label_id']}: {p['label_language']} -> {p['output_language']}: {p['label_quote']}")
    section("Hedge errors", rep["hedge_errors"], pair)
    section("Detail lost", rep["detail_lost"],
            lambda p: pair(p) + f"\n    missing: {', '.join(p['missing'])}")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run_file")
    ap.add_argument("--threshold", type=float, default=config.MATCH_THRESHOLD)
    args = ap.parse_args(argv)

    run_path = validate_run_path(args.run_file)
    run = json.loads(run_path.read_text(encoding="utf-8"))
    deal = config.require_allowed_deal(run["deal"])
    labels, labels_sha = load_labels(deal)

    out_path = output_path(run_path, args.threshold, labels_sha)
    if out_path.exists():
        print(f"Refusing to overwrite {out_path}", file=sys.stderr)
        return 1

    rep = evaluate(run, labels, args.threshold, config.NEAR_MISS_FLOOR)
    rep = {"run_file": run_path.name, "deal": deal, "labels_sha256": labels_sha, **rep}

    print_report(rep)
    with open(out_path, "x", encoding="utf-8") as f:
        json.dump(rep, f, indent=2, ensure_ascii=False)
    print(f"\nWrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
