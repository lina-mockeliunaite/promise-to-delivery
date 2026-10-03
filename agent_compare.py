"""Rules vs agent on the development deals, judged by the decision rule fixed on 3 Oct (DECISIONS 2026-10-03).

Usage: python agent_compare.py [--runs 3]
Needs ANTHROPIC_API_KEY (makes model calls). Reads workspace/ledger.sqlite read-only; never writes the ledger.
For every deal in config.LEDGER_DEALS: the commitments the rules left as 'unknown / needs review' go to the agent,
three fresh runs each; code validates every verdict; the result is scored against the frozen labels and the three
conditions. Writes results/agent_compare_<UTC timestamp>.json, never overwriting. Exit 0 scored, 2 refused.

Condition 1: at least one material issue (approval issue, including an absolute limit) that the rules miss, that the
agent finds in an accepted verdict and the labels support. Condition 2: in all runs, no unsupported finding (an
accepted approval issue the labels do not support, or a rejected verdict that claimed more than 'unknown') and no
uncited verdict. Condition 3: mean extra cost <= bound and mean extra latency <= bound per deal review, no single run
above twice either bound, and no run capped.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import agent
import config
import score_grouping as sg
import score_rules
import terms


def judge_run(run: dict, rows: list, unmatched: dict) -> dict:
    """Score one agent run against the rules baseline and the labels."""
    by_pred = {r["predicted"]: r for r in rows if r["predicted"]}
    added, false_flags, unsupported, uncited, misses = [], [], [], [], []
    final = {}
    for key, v in run["verdicts"].items():
        sub, val = v["submitted"], v["validation"]
        row = by_pred.get(key)
        label_over = bool(row and "approval" in row["issues"]["label"])
        if not val["accepted"]:
            if any(p.startswith("uncited") for p in val["problems"]):
                uncited.append(key)
            if sub.get("authorisation") != "unknown_needs_review":
                unsupported.append({"commitment": key, "label": row["label"] if row else None, "problems": val["problems"]})
            elif val["expected"] not in (None, "unknown_needs_review"):
                misses.append(key)
            final[key] = "unknown_needs_review"
            continue
        final[key] = sub["authorisation"]
        flags = sub["authorisation"] == "no_approval_evidence"
        if flags and label_over and "approval" not in row["issues"]["rules"]:
            added.append({"commitment": key, "label": row["label"], "absolute_limit": val["absolute_limit"],
                          "label_absolute": row["absolute_limit"]["label"]})
        elif flags and not label_over:
            false_flags.append({"commitment": key, "label": row["label"] if row else None})
        if row and sub["authorisation"] != row["authorisation"]["label"]:
            misses.append(key)
    return {"added_material": added, "false_flags": false_flags, "unsupported": unsupported, "uncited": uncited,
            "disagreements_with_labels": sorted(set(misses)), "final_authorisation": final,
            "cost_usd": run.get("cost_usd"), "seconds": run.get("seconds"), "status": run["status"],
            "tool_calls": run["tool_calls"], "turns": run["turns"]}


def decide(deals: dict) -> dict:
    runs = [j for d in deals.values() for j in d["judged"] if d["escalated"]]
    c1 = any(j["added_material"] for j in runs)
    c2 = all(not (j["false_flags"] or j["unsupported"] or j["uncited"]) for j in runs)
    bounds = {}
    c3 = True
    for slug, d in deals.items():
        js = [j for j in d["judged"] if d["escalated"]]
        if not js:
            continue
        costs = [j["cost_usd"] or 0 for j in js]
        secs = [j["seconds"] or 0 for j in js]
        mean_cost, mean_secs = sum(costs) / len(costs), sum(secs) / len(secs)
        ok = (mean_cost <= config.AGENT_BOUND_COST_USD and mean_secs <= config.AGENT_BOUND_LATENCY_S
              and max(costs) <= 2 * config.AGENT_BOUND_COST_USD and max(secs) <= 2 * config.AGENT_BOUND_LATENCY_S
              and all(j["status"] == "complete" for j in js))
        bounds[slug] = {"mean_cost_usd": round(mean_cost, 6), "max_cost_usd": max(costs), "mean_seconds": round(mean_secs, 2),
                        "max_seconds": max(secs), "within_bounds": ok}
        c3 = c3 and ok
    keep = c1 and c2 and c3
    return {"condition_1_adds_material_issue": c1, "condition_2_no_unsupported_or_uncited": c2,
            "condition_3_within_bounds": c3, "bounds_per_deal": bounds, "keep_agent": keep,
            "conclusion": ("Keep the agent as an escalation step: all three conditions hold on the tested cases."
                           if keep else "The rules power the demo: the agent did not meet all three conditions on the tested cases.")}


def variation(runs: list) -> dict:
    keys = sorted({k for r in runs for k in r["final_authorisation"]})
    return {k: sorted({r["final_authorisation"].get(k, "missing") for r in runs}) for k in keys}


def compare(client, conn, runs: int = 3, data_dir=None, results_dir=None) -> dict:
    catalogue = json.loads((config.DATA_DIR / "catalogue.json").read_text(encoding="utf-8"))
    vocab = terms.build_vocabulary(catalogue)
    deals = {}
    for slug in config.LEDGER_DEALS:
        scored = score_rules.score_deal(slug, conn, data_dir, results_dir)
        review_id = scored["review_id"]
        items = agent.escalated_items(conn, review_id)
        notes = agent.review_notes(conn, review_id)
        raw = [agent.run_agent(client, items, catalogue, vocab, notes) for _ in range(runs)] if items else []
        judged = [judge_run(r, scored["commitments"], {}) for r in raw]
        deals[slug] = {"escalated": [i["commitment_key"] for i in items], "rules_metrics": scored["metrics"],
                       "judged": judged, "variation": variation(judged), "runs": raw}
    return {"model": config.AGENT_MODEL, "runs_per_deal": runs,
            "bounds": {"cost_usd": config.AGENT_BOUND_COST_USD, "latency_s": config.AGENT_BOUND_LATENCY_S,
                       "tool_calls_per_commitment": config.AGENT_MAX_TOOL_CALLS_PER_COMMITMENT,
                       "tool_calls_per_deal": config.AGENT_MAX_TOOL_CALLS_PER_DEAL},
            "deals": deals, "decision": decide(deals)}


def render(report: dict) -> str:
    lines = []
    for slug, d in report["deals"].items():
        lines.append(f"{slug}: escalated {len(d['escalated'])} {d['escalated']}")
        for n, j in enumerate(d["judged"], start=1):
            lines.append(f"  run {n}: {j['status']}; {j['tool_calls']} tool calls, {j['turns']} turns, ${j['cost_usd']}, "
                         f"{j['seconds']} s; added {[a['label'] for a in j['added_material']]}; "
                         f"false flags {[f['commitment'] for f in j['false_flags']]}; "
                         f"unsupported {[u['commitment'] for u in j['unsupported']]}; uncited {j['uncited']}")
        varied = {k: v for k, v in d["variation"].items() if len(v) > 1}
        if varied:
            lines.append(f"  varied across runs: {varied}")
    dec = report["decision"]
    lines.append(f"\nCondition 1 (adds a material issue): {dec['condition_1_adds_material_issue']}")
    lines.append(f"Condition 2 (no unsupported or uncited): {dec['condition_2_no_unsupported_or_uncited']}")
    lines.append(f"Condition 3 (within bounds): {dec['condition_3_within_bounds']} {dec['bounds_per_deal']}")
    lines.append(dec["conclusion"])
    return "\n".join(lines)


def _jsonable(obj):
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return str(obj)


def write_report(report: dict, results_dir=None, now=None) -> Path:
    base = Path(results_dir) if results_dir is not None else config.RESULTS_DIR
    now = now or datetime.now(timezone.utc)
    path = base / f"agent_compare_{now.strftime('%Y%m%dT%H%M%SZ')}.json"
    base.mkdir(parents=True, exist_ok=True)
    with open(path, "x", encoding="utf-8") as f:
        json.dump({"timestamp_utc": now.isoformat(timespec="seconds"), **report}, f, indent=2, ensure_ascii=False,
                  default=_jsonable)
        f.write("\n")
    return path


def main(argv: list) -> int:
    parser = argparse.ArgumentParser(description="Rules vs agent on the development deals.")
    parser.add_argument("--runs", type=int, default=3)
    args = parser.parse_args(argv)
    if not os.environ.get("ANTHROPIC_API_KEY"):  # presence only; never read or printed
        print("ANTHROPIC_API_KEY is not set.", file=sys.stderr)
        return 2
    if not config.LEDGER_DB_PATH.exists():
        print("refused: build the ledger first (ledger_import.py --rebuild, ledger_consolidate.py)", file=sys.stderr)
        return 2
    import anthropic
    conn = sg.open_read_only(config.LEDGER_DB_PATH)
    try:
        report = compare(anthropic.Anthropic(), conn, args.runs)
    finally:
        conn.close()
    path = write_report(report)
    print(render(report))
    print(f"\nwritten {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
