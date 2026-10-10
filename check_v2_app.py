"""Real-model check of v2 in the app (10 Oct 2026). About $0.10-0.15; needs ANTHROPIC_API_KEY.

    python check_v2_app.py

On a throwaway ledger (workspace/ledger.sqlite is never touched), Harbour Bank:
  1. Seeded first review: 6 open findings, no model call.
  2. Attach the named-exception pricing note to the Polygon approval finding: it closes; no model call (a pricing note
     cannot create a promise); the Polygon conflict stays open.
  3. Attach the aligned SOW (Polygon real time in Annex A) to the Polygon conflict: one real model call reads the new
     document set; the conflict closes by re-verifying its stored claim; no finding that was open before is closed by
     model variance, and anything newly raised is printed for a person to judge.
  4. Rerun with nothing changed: no model call, nothing changes.
Model output is cached in results/v2_cache/, so the same steps in the demo afterwards need no model call.
"""

import sys
import tempfile
from pathlib import Path

import config
import finding_check
import ledger
import ledger_v2
import recheck
import workspace

SCEN = config.ROOT / "data" / "scenarios"


def _issues(conn):
    return {(c["name"], i["finding"]): (i["state"], i["id"]) for c in workspace.overview(conn, "harbour_bank")["commitments"]
            for i in c["issues"]}


def _find(conn, word, finding):
    return next(v[1] for k, v in _issues(conn).items() if word in k[0] and k[1] == finding)


def run(client, db_path) -> list:
    results = []

    def check(name, ok, detail=""):
        results.append((name, bool(ok), detail))

    built = ledger_v2.build(db_path, client=None)
    conn = ledger.connect(db_path)
    try:
        hb = built["harbour_bank"]
        open_before = {k for k, v in _issues(conn).items() if v[0] != "Resolved"}
        check("1 seeded review: 6 open, no model call", hb["model_calls"] == 0 and len(open_before) == 6, f"{len(open_before)} open")

        iid = _find(conn, "Polygon", "No approval recorded")
        out = finding_check.check(conn, "harbour_bank", iid, confirmed_doc_type="pricing_services_note", filename="HB-05_v2.md",
                                  text=(SCEN / "HB-05_v2_named_exception.md").read_text(encoding="utf-8"), source_key="HB-05",
                                  signed_off_by="Daniel Koh", client=client)
        conflict = _find(conn, "Polygon", "Contract says something different")
        check("2 named exception closes the approval, no model call", out["this_finding"] == "Resolved" and out["model_calls"] == 0,
              f"{out['this_finding']}, calls {out['model_calls']}")
        check("2 the Polygon conflict stays open", _issues(conn)[next(k for k in _issues(conn) if _issues(conn)[k][1] == conflict)][0] != "Resolved")

        before = {k for k, v in _issues(conn).items() if v[0] != "Resolved"}
        out = finding_check.check(conn, "harbour_bank", conflict, confirmed_doc_type="draft_sow", filename="HB-06_v2.md",
                                  text=(SCEN / "HB-06_v2_annex_aligned.md").read_text(encoding="utf-8"), source_key="HB-06",
                                  signed_off_by="Dana Lee", client=client)
        after = _issues(conn)
        closed = sorted(k for k in before if after[k][0] == "Resolved")
        check("3 aligned SOW: one model call, the conflict closes", out["model_calls"] == 1 and out["this_finding"] == "Resolved",
              f"{out['this_finding']}, calls {out['model_calls']}")
        check("3 nothing else closed", closed == [k for k in before if after[k][1] == conflict], f"closed: {closed}")
        new = sorted(k for k, v in after.items() if v[0] != "Resolved" and k not in before)
        check("3 newly raised findings (judge by eye; none expected)", True, f"{new or 'none'}")

        r = recheck.recheck(conn, "harbour_bank", None, client)
        check("4 unchanged rerun: no model call, nothing changes", r["model_calls"] == 0 and _issues(conn) == after,
              f"calls {r['model_calls']}")
    finally:
        conn.close()
    return results


def main(argv) -> int:
    import anthropic
    client = anthropic.Anthropic()
    with tempfile.TemporaryDirectory() as tmp:
        results = run(client, Path(tmp) / "check.sqlite")
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""))
    failed = sum(1 for _, ok, _ in results if not ok)
    print(f"{len(results) - failed}/{len(results)} pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
