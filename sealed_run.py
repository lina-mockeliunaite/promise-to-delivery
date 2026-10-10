"""The sealed evaluation: baseline, rules, and rules + agent v2, once each, on a deal no code has read before.

Usage (Lina, after releasing the seal):
    python sealed_run.py coral_pay

Configuration recorded in DECISIONS.md (2026-10-09/10, "Configuration for the 14 Oct sealed run"), moved forward to
10 Oct by Lina's decision. This file only chains existing, already-tested pieces; it changes none of them:
  1. Seal check   every file listed in data/<deal>.sha256 must match; otherwise nothing runs.
  2. Baseline     one model call over all documents and the catalogue (the same task as baseline.py).
  3. Extraction   extract.run_extraction (frozen v1), then evaluate.evaluate against the deal's statement labels.
  4. Rules        consolidation + rules in a TEMPORARY ledger that is deleted afterwards; scored with
                  score_rules.score_deal against the deal's commitment labels. The workspace ledger and the app never
                  see the deal (LEDGER_DEALS, UI_DEALS and the files on disk are unchanged).
  5. Agent v2     one run over the firm commitments the rules leave 'unknown', judged with agent_compare.judge_run and
                  the 4 Oct decision rule (agent_compare.decide), condition 2 on this single run.
Writes results/extract_<deal>_*.json, results/eval_*.json and one results/sealed_<deal>_<time>.json; never overwrites.
Refuses to run twice on the same deal: a crash before the summary is written may be rerun, and is logged as such.
Exit 0 completed, 1 completed with a failed step, 2 refused.
"""

import hashlib
import json
import os
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import agent
import agent_compare
import config
import evaluate
import extract
import ledger_consolidate
import ledger_import
import ledger_fixes
import score_rules
import terms

BASELINE_TASK = """Review this deal's paperwork before signature.
Find customer-facing promises that go beyond Elva's catalogue or approved scope, and firm, specific promises that are missing or changed in the draft agreement without being explicitly withdrawn.
For each problem, give the exact quote, its source ID, and why the supplied evidence makes it a problem."""


class Refused(Exception):
    pass


def verify_seal(deal: str, root: Path = None) -> list:
    """Check every 'sha256  path' line of data/<deal>.sha256. Returns the files checked; raises Refused on any miss."""
    root = Path(root) if root is not None else config.ROOT
    seal = root / "data" / f"{deal}.sha256"
    if not seal.is_file():
        raise Refused(f"no seal file data/{deal}.sha256")
    checked = []
    for line in seal.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        want, rel = line.split(None, 1)
        rel = rel.lstrip("*").strip()
        path = (root / rel).resolve()
        if not path.is_relative_to((root / "data").resolve()) or not path.is_file():
            raise Refused(f"seal lists {rel}, which is missing or outside data/")
        if hashlib.sha256(path.read_bytes()).hexdigest() != want:
            raise Refused(f"seal broken: {rel} does not match its recorded hash")
        checked.append(rel)
    if not checked:
        raise Refused("the seal file lists no files")
    return checked


@contextmanager
def unsealed(deal: str, results_dir: Path):
    """For this process only: allow the deal for reading, and point results at results_dir."""
    with mock.patch.object(config, "ALLOWED_DEALS", config.ALLOWED_DEALS + [deal] if deal not in config.ALLOWED_DEALS else config.ALLOWED_DEALS), \
            mock.patch.object(config, "RESULTS_DIR", Path(results_dir)):
        yield


def run_baseline(client, deal: str) -> dict:
    manifest = json.loads(config.doc_path(deal, "manifest.json").read_text(encoding="utf-8"))
    parts = [f"=== {d['source_id']} ({d['doc_type']}, {d['date']}) ===\n" + config.doc_path(deal, d["file"]).read_text(encoding="utf-8")
             for d in manifest["documents"]]
    catalogue = (config.DATA_DIR / "catalogue.json").read_text(encoding="utf-8")
    response = client.messages.create(model=config.EXTRACTION_MODEL, max_tokens=config.MAX_TOKENS, messages=[
        {"role": "user", "content": f"{BASELINE_TASK}\n\nCATALOGUE:\n{catalogue}\n\nDOCUMENTS:\n" + "\n\n".join(parts)}])
    answer = "".join(b.text for b in response.content if getattr(b, "type", None) == "text")
    return {"answer": answer, "stop_reason": response.stop_reason,
            "cost_usd": extract.cost_usd(response.usage.input_tokens, response.usage.output_tokens),
            "usage": {"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens},
            "scoring": "manual: compare each problem the baseline names with the commitment labels"}


def run_rules_and_agent(client, deal: str, run_file: str) -> dict:
    """Consolidation + rules in a throwaway ledger, scored; then one agent v2 run over the 'unknown' commitments."""
    catalogue = json.loads((config.DATA_DIR / "catalogue.json").read_text(encoding="utf-8"))
    vocab = terms.build_vocabulary(catalogue)
    with tempfile.TemporaryDirectory() as tmp, \
            mock.patch.object(config, "LEDGER_DEALS", [deal]), \
            mock.patch.object(config, "LEDGER_IMPORT_RUN_FILES", {deal: run_file}):
        db = Path(tmp) / "sealed.sqlite"
        ledger_import.build(db)
        import ledger
        conn = ledger.connect(db)
        try:
            ledger_consolidate.consolidate_all(conn, assess=True)
            scored = score_rules.score_deal(deal, conn, results_dir=config.RESULTS_DIR)
            items = agent.escalated_items(conn, scored["review_id"])
            raw = agent.run_agent(client, items, catalogue, vocab, agent.review_notes(conn, scored["review_id"])) if items else None
        finally:
            conn.close()
    judged = agent_compare.judge_run(raw, scored["commitments"], {}) if raw else None
    decision = agent_compare.decide({deal: {"escalated": [i["commitment_key"] for i in items], "judged": [judged] if judged else []}})
    return {"rules": scored, "agent": {"agent_version": agent.AGENT_VERSION, "escalated": [i["commitment_key"] for i in items],
                                        "run": raw, "judged": judged, "decision": decision}}


def sealed_run(client, deal: str, results_dir=None, root=None, allow_development: bool = False) -> dict:
    results_dir = Path(results_dir) if results_dir is not None else config.RESULTS_DIR
    if not allow_development and (deal in config.LEDGER_DEALS or deal in config.UI_DEALS):
        raise Refused(f"{deal} is a development deal; the sealed run is for a sealed deal")
    if any(results_dir.glob(f"sealed_{deal}_*.json")):
        raise Refused(f"a sealed run of {deal} already exists in {results_dir.name}/; it runs once per configuration")
    seal = verify_seal(deal, root)
    out = {"deal": deal, "seal_files_verified": len(seal), "configuration": {
        "extraction_model": config.EXTRACTION_MODEL, "max_tokens": config.MAX_TOKENS, "thinking_mode": config.THINKING_MODE,
        "prompt_hashes": extract.prompt_hashes(), "agent_version": agent.AGENT_VERSION, "agent_model": config.AGENT_MODEL,
        "agent_bounds": {"cost_usd": config.AGENT_BOUND_COST_USD, "latency_s": config.AGENT_BOUND_LATENCY_S,
                         "tool_calls_per_commitment": config.AGENT_MAX_TOOL_CALLS_PER_COMMITMENT,
                         "tool_calls_per_deal": config.AGENT_MAX_TOOL_CALLS_PER_DEAL, "turns": config.AGENT_MAX_TURNS},
        "rules_config_sha256": ledger_consolidate.rules_sha256((config.DATA_DIR / "catalogue.json").read_bytes())},
        "steps": {}}
    with unsealed(deal, results_dir):
        out["steps"]["baseline"] = _guard(lambda: run_baseline(client, deal))
        def extraction():
            run = extract.run_extraction(client, deal)
            path = Path(extract.save_run(run))
            labels, sha = evaluate.load_labels(deal)
            rep = evaluate.evaluate(run, labels, config.MATCH_THRESHOLD, config.NEAR_MISS_FLOOR)
            eval_path = evaluate.output_path(path, config.MATCH_THRESHOLD, sha)
            with open(eval_path, "x", encoding="utf-8") as f:
                json.dump(rep, f, indent=2, ensure_ascii=False)
            return {"run_file": path.name, "eval_file": eval_path.name, "status_counts": run["status_counts"],
                    "cost_usd": run["totals"].get("cost_usd"),
                    "metrics": {k: rep[k] for k in ("counts", "precision", "recall", "recall_firm", "language_accuracy")}}
        out["steps"]["extraction"] = _guard(extraction)
        if out["steps"]["extraction"]["ok"]:
            out["steps"]["rules_and_agent"] = _guard(lambda: run_rules_and_agent(client, deal, out["steps"]["extraction"]["result"]["run_file"]))
    costs = [out["steps"].get("baseline", {}).get("result", {}).get("cost_usd"),
             out["steps"].get("extraction", {}).get("result", {}).get("cost_usd"),
             ((out["steps"].get("rules_and_agent", {}).get("result") or {}).get("agent", {}).get("run") or {}).get("cost_usd")]
    out["total_cost_usd"] = round(sum(c for c in costs if c), 6)
    out["completed"] = all(s["ok"] for s in out["steps"].values()) and "rules_and_agent" in out["steps"]
    now = datetime.now(timezone.utc)
    out["timestamp_utc"] = now.isoformat(timespec="seconds")
    path = results_dir / f"sealed_{deal}_{now.strftime('%Y%m%dT%H%M%SZ')}.json"
    with open(path, "x", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False, default=agent_compare._jsonable)
    out["written"] = str(path)
    return out


def _guard(step) -> dict:
    """Run one step; a failure is recorded, not hidden, and later steps that do not depend on it still run."""
    try:
        return {"ok": True, "result": step()}
    except Exception as exc:  # recorded verbatim in the summary; never retried silently
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def render(out: dict) -> str:
    lines = [f"Sealed run: {out['deal']} · seal verified ({out['seal_files_verified']} files) · total ${out['total_cost_usd']}"]
    for name, s in out["steps"].items():
        if not s["ok"]:
            lines.append(f"{name}: FAILED — {s['error']}")
            continue
        r = s["result"]
        if name == "baseline":
            lines.append(f"baseline: {len(r['answer'])} characters, stop {r['stop_reason']}, ${r['cost_usd']} (score by hand)")
        elif name == "extraction":
            m = r["metrics"]
            lines.append(f"extraction: {r['status_counts']}; recall {m['recall']}, firm recall {m['recall_firm']}, precision "
                         f"{m['precision']}, language {m['language_accuracy']} ({m['counts']}), ${r['cost_usd']}")
        else:
            m = r["rules"]["metrics"]
            lines.append(f"rules: authorisation {m['authorisation']['exact']}/{m['authorisation']['of']}, presence "
                         f"{m['presence']['exact']}/{m['presence']['of']}, issue sets {m['issue_sets']['exact']}/{m['issue_sets']['of']}, "
                         f"issues TP {m['issues']['true_positive']} FP {m['issues']['false_positive']} FN {m['issues']['false_negative']}, "
                         f"false flags on clean {m['false_flags_on_clean_commitments']}")
            a = r["agent"]
            lines.append(f"agent v{a['agent_version']}: escalated {a['escalated']}; {a['decision']['conclusion']}")
    lines.append(f"completed: {out['completed']} · written {out.get('written')}")
    return "\n".join(lines)


def main(argv: list) -> int:
    if len(argv) != 1:
        print("usage: python sealed_run.py <sealed deal>", file=sys.stderr)
        return 2
    if not os.environ.get("ANTHROPIC_API_KEY"):  # presence only; never read or printed
        print("ANTHROPIC_API_KEY is not set.", file=sys.stderr)
        return 2
    import anthropic
    try:
        out = sealed_run(anthropic.Anthropic(), argv[0])
    except Refused as exc:
        print(f"Refused: {exc}", file=sys.stderr)
        return 2
    print(render(out))
    return 0 if out["completed"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
