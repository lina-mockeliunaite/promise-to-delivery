"""Smoke test for agent v2 with the real model (Lina's decision, 9 Oct: option C in docs/DECISION_MEMO_agent_v2.md).

Usage: python agent_smoke.py
Needs ANTHROPIC_API_KEY (one real-model run per deal, about $0.02 in total).

Purpose, and its limit: does agent v2 run end to end with the real model — tool calls, submitted verdicts, validation,
cost and latency inside the bounds — before its one run on the sealed deal? It is NOT an evaluation and NOT an input to
the rules-vs-agent decision rule (DECISIONS 4 Oct, unchanged):
- only Harbour Bank and the hard cases (already seen; one escalated commitment each). The practice set is refused: it
  judged v1, and running v2 there would be tuning to the test (DECISIONS 3 Oct).
- no labels are read and nothing is scored.
- built in a temporary ledger (the same build as reset_demo), so the workspace ledger is never read or written.
Writes results/agent_smoke_<UTC timestamp>.json, never overwriting. Exit 0 ran, 1 a run failed or was capped, 2 refused.
"""

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import agent
import config
import ledger_fixes
import recheck
import scenarios
import terms

SMOKE_DEALS = ("harbour_bank", "hard_cases")
PURPOSE = "Smoke test only: does agent v2 run with the real model. Not scored, not an input to the decision rule."


def smoke(client, deals=SMOKE_DEALS, workdir=None) -> dict:
    refused = [d for d in deals if d not in SMOKE_DEALS]
    if refused:
        raise ValueError(f"refused: {refused} — the smoke test runs on {list(SMOKE_DEALS)} only")
    catalogue = json.loads((config.DATA_DIR / "catalogue.json").read_text(encoding="utf-8"))
    vocab = terms.build_vocabulary(catalogue)
    with tempfile.TemporaryDirectory(dir=workdir) as tmp:
        conn = scenarios.build_fresh(Path(tmp) / "smoke.sqlite")
        try:
            out = {}
            for slug in deals:
                recheck.recheck(conn, slug, None, None)  # current hash definition, no model call
                review_id = ledger_fixes.freshness(conn, ledger_fixes.deal_id(conn, slug))["review_id"]
                items = agent.escalated_items(conn, review_id)
                run = agent.run_agent(client, items, catalogue, vocab, agent.review_notes(conn, review_id))
                out[slug] = {
                    "escalated": run["escalated"], "status": run["status"], "turns": run["turns"],
                    "tool_calls": run["tool_calls"], "seconds": run.get("seconds"), "cost_usd": run.get("cost_usd"),
                    "verdicts": {k: {"accepted": v["validation"]["accepted"], "problems": v["validation"]["problems"],
                                     "authorisation": v["submitted"].get("authorisation")} for k, v in run["verdicts"].items()},
                    "missing_verdicts": sorted(set(run["escalated"]) - set(run["verdicts"])),
                }
        finally:
            conn.close()
    ok = all(d["status"] in ("complete", "nothing_to_escalate") and not d["missing_verdicts"] for d in out.values())
    return {"purpose": PURPOSE, "agent_version": agent.AGENT_VERSION, "model": config.AGENT_MODEL,
            "bounds": {"cost_usd": config.AGENT_BOUND_COST_USD, "latency_s": config.AGENT_BOUND_LATENCY_S},
            "deals": out, "ran_end_to_end": ok}


def render(report: dict) -> str:
    lines = [report["purpose"], f"agent v{report['agent_version']}, {report['model']}"]
    for slug, d in report["deals"].items():
        lines.append(f"{slug}: {d['status']}; escalated {d['escalated']}; {d['tool_calls']} tool calls, {d['turns']} turns, "
                     f"{d['seconds']} s, ${d['cost_usd']}")
        for key, v in d["verdicts"].items():
            lines.append(f"  {key}: {'accepted' if v['accepted'] else 'rejected'} ({v['authorisation']})"
                         + (f" — {'; '.join(v['problems'])}" if v["problems"] else ""))
        if d["missing_verdicts"]:
            lines.append(f"  no verdict submitted for: {d['missing_verdicts']}")
    lines.append(f"Ran end to end: {report['ran_end_to_end']}")
    return "\n".join(lines)


def main(argv: list) -> int:
    if argv:
        print("usage: python agent_smoke.py", file=sys.stderr)
        return 2
    if not os.environ.get("ANTHROPIC_API_KEY"):  # presence only; never read or printed
        print("ANTHROPIC_API_KEY is not set.", file=sys.stderr)
        return 2
    import anthropic
    report = smoke(anthropic.Anthropic())
    now = datetime.now(timezone.utc)
    path = config.RESULTS_DIR / f"agent_smoke_{now.strftime('%Y%m%dT%H%M%SZ')}.json"
    with open(path, "x", encoding="utf-8") as f:
        json.dump({"timestamp_utc": now.isoformat(timespec="seconds"), **report}, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(render(report))
    print(f"\nwritten {path}")
    return 0 if report["ran_end_to_end"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
