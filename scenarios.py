"""Run the five resolution scenarios (data/scenarios/scenarios.json) and check them against their expected states.

Usage: python scenarios.py
Each scenario starts from a freshly built ledger (a temporary file, never workspace/ledger.sqlite), applies its steps
(a new source version, a fix, approval, recheck) and compares the resulting commitment and issue states with the
expected ones. A control first runs an unchanged-input rerun with no model client: it must make no model call and
change no state. Scenarios that revise an extractable document (the SOW) need one model call each, so this needs
ANTHROPIC_API_KEY. Writes results/scenarios_<UTC timestamp>.json. Exit 0 all pass, 1 any fail, 2 refused.
"""

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import config
import ledger
import ledger_consolidate
import ledger_fixes
import ledger_import
import recheck


def build_fresh(db_path: Path):
    conn = ledger.open_ledger(db_path)
    ledger_import.import_all(conn)
    ledger_consolidate.consolidate_all(conn, assess=True)
    return conn


def _find(names, fragment):
    found = [n for n in names if fragment in n]
    if len(found) != 1:
        raise ValueError(f"{fragment!r} matches {found}")
    return found[0]


def _issue_ids(conn, slug, wanted):
    did = ledger_fixes.deal_id(conn, slug)
    rows = conn.execute(
        "SELECT i.id, i.issue_type, (SELECT name FROM commitment_assessments a WHERE a.commitment_id = c.id"
        " AND a.support_state = 'supported' ORDER BY a.id DESC LIMIT 1) FROM issues i JOIN commitments c"
        " ON c.id = i.commitment_id WHERE c.deal_id = ?", (did,)).fetchall()
    ids = []
    for w in wanted:
        match = [iid for iid, t, name in rows if t == w["type"] and name and w["commitment"] in name]
        if len(match) != 1:
            raise ValueError(f"{w} matches issues {match}")
        ids.append(match[0])
    return ids


def _included_version(conn, slug, source_key):
    did = ledger_fixes.deal_id(conn, slug)
    return conn.execute("SELECT v.id FROM source_versions v JOIN sources s ON s.id = v.source_id WHERE s.deal_id = ?"
                        " AND s.source_key = ? AND v.included = 1", (did, source_key)).fetchone()[0]


def compare_expected(states: dict, expect: dict) -> list:
    problems = []
    for fragment, want in expect.items():
        try:
            name = _find(states, fragment)
        except ValueError as exc:
            problems.append(str(exc))
            continue
        status, issues = states[name]
        if status != want["status"]:
            problems.append(f"{fragment}: status {status}, expected {want['status']}")
        for pattern, state in want["issues"].items():
            keys = [k for k in issues if (k.startswith(pattern[:-1]) if pattern.endswith("*") else k == pattern)]
            if len(keys) != 1:
                problems.append(f"{fragment}: issue {pattern} matched {keys}")
            elif issues[keys[0]] != state:
                problems.append(f"{fragment}: {keys[0]} is {issues[keys[0]]}, expected {state}")
    return problems


def run_scenario(scenario: dict, client, workdir: Path) -> dict:
    conn = build_fresh(workdir / f"{scenario['id']}.sqlite")
    slug, rechecks = scenario["deal"], []
    try:
        for step in scenario["steps"]:
            version_id = None
            if "new_version" in step:
                nv = step["new_version"]
                text = config.scenario_path(nv["file"]).read_text(encoding="utf-8")
                version_id = ledger_fixes.add_source_version(conn, slug, nv["source"], text, nv["file"])
            f = step["fix"]
            evidence_version = version_id if f["evidence"] == "new_version" else _included_version(conn, slug, f["evidence"]["source"])
            fix_id = ledger_fixes.create_fix(conn, slug, f["route"], f["owner"], f["rationale"],
                                             _issue_ids(conn, slug, f["issues"]), [(evidence_version, "whole document", None)])
            ledger_fixes.approve_fix(conn, fix_id, f["approved_by"])
            rechecks.append(recheck.recheck(conn, slug, fix_id, client))
        states = recheck.status_by_name(conn, slug)
        problems = compare_expected(states, scenario["expect"])
        return {"id": scenario["id"], "name": scenario["name"], "passed": not problems, "problems": problems,
                "rechecks": rechecks, "states": {k: {"status": v[0], "issues": v[1]} for k, v in states.items()}}
    finally:
        conn.close()


def control_unchanged_rerun(workdir: Path) -> dict:
    """An unchanged-input rerun: no model client at all, and every state stays as it was."""
    conn = build_fresh(workdir / "control.sqlite")
    try:
        out = {}
        for slug in config.LEDGER_DEALS:
            before = recheck.status_by_name(conn, slug)
            result = recheck.recheck(conn, slug, None, client=None)
            after = recheck.status_by_name(conn, slug)
            out[slug] = {"model_calls": result["model_calls"], "unchanged": before == after, "checks": result["checks"]}
        return {"passed": all(v["model_calls"] == 0 and v["unchanged"] for v in out.values()), "deals": out}
    finally:
        conn.close()


def run_all(client) -> dict:
    spec = json.loads(config.scenario_path("scenarios.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        control = control_unchanged_rerun(work)
        results = [run_scenario(s, client, work) for s in spec["scenarios"]]
    return {"control_unchanged_input_rerun": control, "scenarios": results,
            "passed": sum(r["passed"] for r in results), "of": len(results),
            "cost_usd": round(sum(r2["cost_usd"] for r in results for r2 in r["rechecks"]), 6)}


def main(argv: list) -> int:
    if argv:
        print("usage: python scenarios.py", file=sys.stderr)
        return 2
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set (scenarios S2 and S3 extract a revised SOW).", file=sys.stderr)
        return 2
    import anthropic
    report = run_all(anthropic.Anthropic())
    now = datetime.now(timezone.utc)
    path = config.RESULTS_DIR / f"scenarios_{now.strftime('%Y%m%dT%H%M%SZ')}.json"
    with open(path, "x", encoding="utf-8") as f:
        json.dump({"timestamp_utc": now.isoformat(timespec="seconds"), **report}, f, indent=2, ensure_ascii=False)
    print(f"control (unchanged-input rerun, no model client): {'PASS' if report['control_unchanged_input_rerun']['passed'] else 'FAIL'}")
    for r in report["scenarios"]:
        print(f"{r['id']} {'PASS' if r['passed'] else 'FAIL'}  {r['name']}")
        for p in r["problems"]:
            print(f"    {p}")
    print(f"\n{report['passed']} of {report['of']} scenarios as expected; model cost ${report['cost_usd']}")
    print(f"written {path}")
    return 0 if report["passed"] == report["of"] and report["control_unchanged_input_rerun"]["passed"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
