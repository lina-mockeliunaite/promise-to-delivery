"""Run v2 (model detects, code verifies) on the development deals, or once on the sealed v2 test deal.

Usage:
    python run_v2.py dev                      one model call per development deal; ~$0.1 a deal
    python run_v2.py replay results/v2_dev_<time>.json   re-verify and re-score saved model output; no model call
    python run_v2.py sealed atlas_remit       the one sealed run; refuses if it has run before or the seal is broken

Dev deals: harbour_bank, practice_cases, hard_cases, coral_pay (released 10 Oct; development data from then on).
Results go to results/ and are never overwritten.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import config
import detect_v2
import score_v2
import sealed_run

DEV_DEALS = ["harbour_bank", "practice_cases", "hard_cases", "coral_pay"]
SEALED_V2 = "atlas_remit"


def _catalogue() -> dict:
    return json.loads((config.DATA_DIR / "catalogue.json").read_text(encoding="utf-8"))


def run_deal(client, deal: str, catalogue: dict) -> dict:
    docs = detect_v2.deal_documents(deal)
    out = detect_v2.review(client, docs, catalogue)
    out["score"] = score_v2.score(deal, out["accepted"], out["rejected"])
    return {"deal": deal, **out}


def reverify(saved: dict, catalogue: dict) -> dict:
    """Re-run verification and scoring on saved model findings: free, for iterating on the verifier."""
    deals = []
    for d in saved["deals"]:
        with sealed_run.unsealed(d["deal"], config.RESULTS_DIR) if d["deal"] not in config.ALLOWED_DEALS else _null():
            docs = detect_v2.deal_documents(d["deal"])
            accepted, rejected = [], []
            for f in d["findings"]:
                f = {k: v for k, v in f.items() if k != "problems"}
                problems = detect_v2.verify(f, docs, catalogue)
                (rejected if problems else accepted).append({**f, "problems": problems})
            deals.append({**d, "accepted": accepted, "rejected": rejected,
                          "score": score_v2.score(d["deal"], accepted, rejected)})
    return {**saved, "replayed_from": saved.get("file"), "deals": deals}


class _null:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _save(prefix: str, out: dict) -> Path:
    config.RESULTS_DIR.mkdir(exist_ok=True)
    path = config.RESULTS_DIR / f"{prefix}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    if path.exists():
        raise FileExistsError(path)
    out["file"] = path.name
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def dev(client) -> dict:
    catalogue = _catalogue()
    deals = []
    for deal in DEV_DEALS:
        ctx = sealed_run.unsealed(deal, config.RESULTS_DIR) if deal not in config.ALLOWED_DEALS else _null()
        with ctx:
            deals.append(run_deal(client, deal, catalogue))
    return {"kind": "v2_dev", "v2_version": detect_v2.V2_VERSION, "model": config.EXTRACTION_MODEL, "deals": deals}


def sealed(client, deal: str, root: Path = None) -> dict:
    if deal in DEV_DEALS or deal in config.ALLOWED_DEALS:
        raise sealed_run.Refused(f"{deal} is a development deal")
    if any(config.RESULTS_DIR.glob(f"sealed_v2_{deal}_*.json")):
        raise sealed_run.Refused(f"the v2 sealed run of {deal} already exists; it runs once")
    seal = sealed_run.verify_seal(deal, root)
    with sealed_run.unsealed(deal, config.RESULTS_DIR):
        result = run_deal(client, deal, _catalogue())
        try:  # the same one-call baseline as the Coral Pay run, for comparison; scored by hand afterwards
            baseline = sealed_run.run_baseline(client, deal)
        except Exception as exc:  # recorded, never retried
            baseline = {"error": f"{type(exc).__name__}: {str(exc)[:300]}"}
    return {"kind": "v2_sealed", "v2_version": detect_v2.V2_VERSION, "model": config.EXTRACTION_MODEL,
            "seal_files_verified": len(seal), "deals": [result], "baseline": baseline}


def render(out: dict) -> str:
    lines = [f"{out['kind']} · v2_version {out['v2_version']} · {out.get('file', '')}",
             f"{'deal':16} {'found':>9} {'false':>6} {'dup':>4} {'rejected(true)':>15} {'cost':>8}"]
    total = 0.0
    for d in out["deals"]:
        s = d["score"]
        cost = d.get("cost_usd") or 0.0
        total += cost
        lines.append(f"{d['deal']:16} {s['found']:>4}/{s['targets']:<4} {s['false_flags']:>6} {s['duplicates']:>4} "
                     f"{s['rejected']:>9}({len(s['rejected_true'])}) {cost:>8.4f}"
                     + (f"  PARSE ERROR {d['parse_error']}" if d.get("parse_error") else "")
                     + (f"  stop={d['stop_reason']}" if d.get("stop_reason") not in (None, "end_turn") else ""))
        for m in s["missed"]:
            lines.append(f"    missed  {m['commitment']} {m['issue']}: {m['name']}")
        for r in s["rows"]:
            if r["verdict"] == "false_flag":
                lines.append(f"    false   {r['kind']}: {r['commitment']} (quotes match {r['matched'] or 'no labelled statement'})")
        for r in s["rejected_true"]:
            lines.append(f"    rejected but true  {r['kind']} {r['matched']}: {'; '.join(r['problems'])}")
    b = out.get("baseline")
    if b:
        total += b.get("cost_usd") or 0.0
        lines.append(f"baseline (one call, scored by hand): {b.get('error') or str(len(b.get('answer', ''))) + ' characters'}"
                     f", ${b.get('cost_usd') or 0:.4f}")
    lines.append(f"total cost ${total:.4f}")
    return "\n".join(lines)


def main(argv: list) -> int:
    if not argv or argv[0] not in ("dev", "replay", "sealed"):
        print(__doc__, file=sys.stderr)
        return 2
    if argv[0] == "replay":
        saved = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
        out = reverify(saved, _catalogue())
        path = _save("v2_replay", out)
        print(render(out))
        print(f"saved {path.name}")
        return 0
    import anthropic
    client = anthropic.Anthropic()
    if argv[0] == "dev":
        out = dev(client)
        path = _save("v2_dev", out)
    else:
        if len(argv) != 2:
            print("usage: python run_v2.py sealed <deal>", file=sys.stderr)
            return 2
        try:
            out = sealed(client, argv[1])
        except sealed_run.Refused as exc:
            print(f"Refused: {exc}", file=sys.stderr)
            return 1
        path = _save(f"sealed_v2_{argv[1]}", out)
    print(render(out))
    print(f"saved {path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
