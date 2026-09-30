"""Must-hold regression checks for a Harbour Bank extraction run. No API calls.

Usage: python regression.py results/extract_harbour_bank_<timestamp>.json
Scores the run with evaluate.py against the current labels, then runs the checks in CHECKS.
Writes results/regression_<run stem>.json (never overwrites) and prints PASS/FAIL per check.
Exit codes: 0 all checks pass, 1 at least one check fails, 2 refused or cannot start.
"""

import argparse
import json
import sys
from pathlib import Path

import check_quotes
import config
import evaluate

DEAL = "harbour_bank"

# The check definitions. Change a threshold or an id here; the check functions below read only this dict.
CHECKS = {
    "firm_labels_matched": {
        "title": "Every firm label is matched",
    },
    "hedge_pair_output_firm": {
        "title": "S08 and S09 are matched and the output language is firm",
        "label_ids": ["S08", "S09"],
        "output_language": "firm",
    },
    "must_match": {
        "title": "S12, S13 and S14 are matched",
        "label_ids": ["S12", "S13", "S14"],
    },
    "quotes_valid": {
        "title": "Every quote is valid (found word for word in its source)",
    },
    "precision_floor": {
        "title": "Precision is at least 0.60",
        "min_precision": 0.60,
    },
    "excluded_sources": {
        "title": "No statements from HB-05, HB-07 or HB-08",
        "source_ids": ["HB-05", "HB-07", "HB-08"],
    },
}


# --- Checks --------------------------------------------------------------
# Each check takes (ctx, params) and returns the failing rows; no rows means PASS.
# ctx: run, labels, sources, rep (evaluate report), matched (label id -> (score, label, output)).

def _label_row(label: dict, problem: str) -> dict:
    return {"label_id": label["id"], "source_id": label["source_id"], "label_language": label["language"],
            "problem": problem, "quote": label["quote"]}


def check_firm_labels_matched(ctx, params):
    return [_label_row(l, "firm label not matched")
            for l in ctx["labels"] if l["language"] == "firm" and l["id"] not in ctx["matched"]]


def check_hedge_pair_output_firm(ctx, params):
    by_id = {l["id"]: l for l in ctx["labels"]}
    rows = []
    for label_id in params["label_ids"]:
        if label_id not in by_id:
            rows.append({"label_id": label_id, "problem": "label id not found in labels"})
        elif label_id not in ctx["matched"]:
            rows.append(_label_row(by_id[label_id], "not matched"))
        else:
            _, label, out = ctx["matched"][label_id]
            if out["language"] != params["output_language"]:
                rows.append({**_label_row(label, f"output language is {out['language']!r}, need {params['output_language']!r}"),
                             "statement_id": out["statement_id"], "output_language": out["language"]})
    return rows


def check_must_match(ctx, params):
    by_id = {l["id"]: l for l in ctx["labels"]}
    return [_label_row(by_id[i], "not matched") if i in by_id else {"label_id": i, "problem": "label id not found in labels"}
            for i in params["label_ids"] if i not in ctx["matched"]]


def check_quotes_valid(ctx, params):
    report = check_quotes.check_run(ctx["run"], ctx["sources"])
    return [{"statement_id": f["statement_id"], "source_id": f["source_id"], "problem": f["reason"], "quote": f["quote"]}
            for f in report["failures"]]


def check_precision_floor(ctx, params):
    precision = ctx["rep"]["precision"]
    if precision is None:
        return [{"problem": "no statements extracted; precision is undefined"}]
    if precision >= params["min_precision"]:
        return []
    return [{"statement_id": o["statement_id"], "source_id": o["source_id"],
             "problem": f"false positive (precision {precision:.3f} < {params['min_precision']})", "quote": o["quote"]}
            for o in ctx["rep"]["false_positives"]]


def check_excluded_sources(ctx, params):
    return [{"statement_id": s["statement_id"], "source_id": s["source_id"], "problem": "statement from an excluded source",
             "quote": s["quote"]}
            for d in ctx["run"]["documents"] for s in d.get("statements") or []
            if s["source_id"] in params["source_ids"]]


CHECK_FUNCTIONS = {
    "firm_labels_matched": check_firm_labels_matched,
    "hedge_pair_output_firm": check_hedge_pair_output_firm,
    "must_match": check_must_match,
    "quotes_valid": check_quotes_valid,
    "precision_floor": check_precision_floor,
    "excluded_sources": check_excluded_sources,
}
assert list(CHECK_FUNCTIONS) == list(CHECKS)   # one function per check, same order


# --- Scoring and running -------------------------------------------------

def matched_pairs(run: dict, labels: list[dict]) -> dict:
    """label id -> (score, label, output), from the same one-to-one assignment evaluate.py uses."""
    eligible = [s for d in run["documents"] if d.get("status") == "complete" for s in d.get("statements") or []]
    result = evaluate.assign(labels, eligible, config.MATCH_THRESHOLD, config.NEAR_MISS_FLOOR)
    return {l["id"]: (score, l, o) for score, l, o in result["matches"]}


def run_checks(run: dict, labels: list[dict], sources: dict[str, str]) -> tuple[dict, list[dict]]:
    """Score the run, then run every check. Returns (evaluate report, one result per check)."""
    rep = evaluate.evaluate(run, labels, config.MATCH_THRESHOLD, config.NEAR_MISS_FLOOR)
    matched = matched_pairs(run, labels)
    if len(matched) != rep["counts"]["tp"]:
        raise RuntimeError("regression and evaluate disagree on the matched pairs")
    ctx = {"run": run, "labels": labels, "sources": sources, "rep": rep, "matched": matched}
    results = []
    for name, params in CHECKS.items():
        rows = CHECK_FUNCTIONS[name](ctx, params)
        results.append({"name": name, "title": params["title"], "passed": not rows, "failing_rows": rows})
    return rep, results


def print_results(rep: dict, results: list[dict]) -> None:
    c = rep["counts"]
    print(f"TP {c['tp']}  FP {c['fp']}  FN {c['fn']}  precision {evaluate.fmt(rep['precision'])}  "
          f"recall {evaluate.fmt(rep['recall'])}  recall (firm) {evaluate.fmt(rep['recall_firm'])}\n")
    for n, r in enumerate(results, start=1):
        print(f"{'PASS' if r['passed'] else 'FAIL'}  {n}. {r['title']}")
        for row in r["failing_rows"]:
            print("    - " + "; ".join(f"{k}: {v}" for k, v in row.items()))


def output_path(run_path: Path) -> Path:
    return config.RESULTS_DIR / f"regression_{run_path.stem}.json"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run_file")
    args = ap.parse_args(argv)

    try:
        run_path = evaluate.validate_run_path(args.run_file)
        run = json.loads(run_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"Could not read input: {exc}")
        return 2
    if run.get("deal") != DEAL:  # refuse before any label or document is read
        print(f"Refused: regression.py only runs on {DEAL!r}, not {run.get('deal')!r}.")
        return 2
    config.require_allowed_deal(DEAL)

    out_path = output_path(run_path)
    if out_path.exists():
        print(f"Refusing to overwrite {out_path}", file=sys.stderr)
        return 2

    labels, labels_sha = evaluate.load_labels(DEAL)
    rep, results = run_checks(run, labels, check_quotes.load_sources(DEAL))
    print_results(rep, results)

    failed = [r["name"] for r in results if not r["passed"]]
    record = {
        "run_file": run_path.name,
        "deal": DEAL,
        "model": run.get("model"),
        "thinking_mode": run.get("thinking_mode"),
        "labels_sha256": labels_sha,
        "prompt_hashes": run.get("prompt_hashes"),  # as recorded in the run file
        "threshold": rep["threshold"],
        "metrics": {k: rep[k] for k in ("counts", "precision", "recall", "recall_firm", "language_accuracy")},
        "all_passed": not failed,
        "failed_checks": failed,
        "checks": results,
    }
    with open(out_path, "x", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2, ensure_ascii=False)
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed. Wrote {out_path}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
