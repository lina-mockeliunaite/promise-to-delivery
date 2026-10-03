"""Score the rules against the development labels: authorisation, contractual presence and issues per labelled
commitment, through the grouping score's one-to-one mapping (score_grouping.py).

Usage: python score_rules.py
Reads workspace/ledger.sqlite read-only after ledger_consolidate.py has run the rules. Writes
results/rules_score_<UTC timestamp>.json, never overwriting. Exit codes: 0 scored, 2 refused.

Labels are read only here, to score; they never shape the rules. Label issue names map to ledger issue types:
overcommitment -> approval, expectation_gap -> contract_gap, contradiction -> conflicting_terms,
needs_review -> insufficient_evidence.
"""

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import config
import score_grouping as sg

LABEL_TO_ISSUE = {"overcommitment": "approval", "expectation_gap": "contract_gap",
                  "contradiction": "conflicting_terms", "needs_review": "insufficient_evidence"}


class ScoreRefused(Exception):
    pass


def read_rules(conn: sqlite3.Connection, review_id: int) -> dict:
    """{commitment_key: {authorisation, presence, issues: [(type, subject, absolute_limit)]}} for one review."""
    out = {}
    for cid, key, auth, presence in conn.execute(
        "SELECT c.id, c.commitment_key, a.authorisation, a.contractual_presence FROM commitments c"
        " JOIN commitment_assessments a ON a.commitment_id = c.id AND a.review_id = ?", (review_id,)):
        issues = conn.execute(
            "SELECT issue_type, subject_key, absolute_limit FROM issues WHERE commitment_id = ? AND raised_review_id = ?"
            " ORDER BY issue_type, subject_key", (cid, review_id)).fetchall()
        out[key] = {"authorisation": auth, "presence": presence, "issues": [list(i) for i in issues]}
    if not out or all(v["presence"] == "not_assessed" and v["authorisation"] == "not_assessed" for v in out.values()):
        raise ScoreRefused("the rules have not run on this review; run ledger_consolidate.py")
    return out


def score_deal(slug: str, conn, data_dir=None, results_dir=None) -> dict:
    ledger = sg.read_ledger_deal(conn, slug)
    labels = sg.read_labels(slug, data_dir)
    grouping = sg.score_deal(slug, ledger, labels, sg.pinned_run_quotes(slug, results_dir))
    mapping = grouping["mapping"]                       # predicted key -> label id
    inverse = {label: pred for pred, label in mapping.items()}
    predicted = read_rules(conn, ledger["review_id"])

    rows, tp, fp, fn = [], 0, 0, 0
    for c in labels["commitments"]:
        want_issues = sorted(LABEL_TO_ISSUE[i] for i in c["issues"])
        pred_key = inverse.get(c["id"])
        p = predicted.get(pred_key) if pred_key else None
        got_issues = sorted({t for t, _, _ in p["issues"]}) if p else []
        got_absolute = bool(p and any(a for _, _, a in p["issues"]))
        tp += len(set(want_issues) & set(got_issues))
        fp += len(set(got_issues) - set(want_issues))
        fn += len(set(want_issues) - set(got_issues))
        rows.append({
            "label": c["id"], "name": c["name"], "predicted": pred_key,
            "authorisation": {"label": c["authorisation"], "rules": p["authorisation"] if p else None,
                              "match": bool(p) and p["authorisation"] == c["authorisation"]},
            "presence": {"label": c["contractual_presence"], "rules": p["presence"] if p else None,
                         "match": bool(p) and p["presence"] == c["contractual_presence"]},
            "issues": {"label": want_issues, "rules": got_issues, "match": bool(p) and want_issues == got_issues},
            "absolute_limit": {"label": c.get("reason") == "absolute_limit", "rules": got_absolute,
                               "match": (c.get("reason") == "absolute_limit") == got_absolute},
        })
    unmatched = {k: v for k, v in predicted.items() if k not in mapping}
    extra_issues = [{"predicted": k, "issues": v["issues"]} for k, v in unmatched.items() if v["issues"]]
    clean = [r for r in rows if not r["issues"]["label"]]
    planted = [r for r in rows if r["issues"]["label"]]
    return {
        "deal": slug, "review_id": ledger["review_id"],
        "grouping": grouping["metrics"],
        "metrics": {
            "authorisation": {"exact": sum(r["authorisation"]["match"] for r in rows), "of": len(rows)},
            "presence": {"exact": sum(r["presence"]["match"] for r in rows), "of": len(rows)},
            "issue_sets": {"exact": sum(r["issues"]["match"] for r in rows), "of": len(rows)},
            "issues": {"true_positive": tp, "false_positive": fp, "false_negative": fn},
            "absolute_limit": {"exact": sum(r["absolute_limit"]["match"] for r in rows), "of": len(rows)},
            "false_flags_on_clean_commitments": sum(1 for r in clean if r["issues"]["rules"]),
            "commitments_with_issues_reaching_review": {"found": sum(1 for r in planted if r["issues"]["rules"]),
                                                        "of": len(planted)},
        },
        "issues_on_unmatched_predicted_groups": extra_issues,
        "commitments": rows,
        "labels_sha256": {"statements": labels["statements_sha256"], "commitments": labels["commitments_sha256"]},
    }


def build_report(conn, data_dir=None, results_dir=None) -> dict:
    return {"deals": {slug: score_deal(slug, conn, data_dir, results_dir) for slug in config.LEDGER_DEALS}}


def render(report: dict) -> str:
    lines = []
    for slug, d in report["deals"].items():
        m = d["metrics"]
        lines.append(f"{slug}: authorisation {m['authorisation']['exact']} of {m['authorisation']['of']}; "
                     f"presence {m['presence']['exact']} of {m['presence']['of']}; "
                     f"issue sets {m['issue_sets']['exact']} of {m['issue_sets']['of']}; "
                     f"issues TP {m['issues']['true_positive']} FP {m['issues']['false_positive']} "
                     f"FN {m['issues']['false_negative']}; false flags on clean {m['false_flags_on_clean_commitments']}")
        for r in d["commitments"]:
            bad = [f for f in ("authorisation", "presence", "issues", "absolute_limit") if not r[f]["match"]]
            if bad:
                lines.append(f"  MISMATCH {r['label']} ({r['predicted']}): " + "; ".join(
                    f"{f} label={r[f]['label']} rules={r[f]['rules']}" for f in bad))
        for extra in d["issues_on_unmatched_predicted_groups"]:
            lines.append(f"  issues on unmatched group {extra['predicted']}: {extra['issues']}")
    return "\n".join(lines)


def write_report(report: dict, results_dir=None, now=None) -> Path:
    base = Path(results_dir) if results_dir is not None else config.RESULTS_DIR
    now = now or datetime.now(timezone.utc)
    path = base / f"rules_score_{now.strftime('%Y%m%dT%H%M%SZ')}.json"
    base.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "x", encoding="utf-8") as f:
            json.dump({"timestamp_utc": now.isoformat(timespec="seconds"), **report}, f, indent=2, ensure_ascii=False)
            f.write("\n")
    except FileExistsError:
        raise ScoreRefused(f"Refusing to overwrite {path}") from None
    return path


def main(argv: list) -> int:
    if argv:
        print("usage: python score_rules.py", file=sys.stderr)
        return 2
    path = config.LEDGER_DB_PATH
    if not path.exists():
        print(f"refused: {path} does not exist; build it with ledger_import.py and ledger_consolidate.py", file=sys.stderr)
        return 2
    conn = sg.open_read_only(path)
    try:
        report = build_report(conn)
        written = write_report(report)
    except (ScoreRefused, sg.ScoreRefused) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    finally:
        conn.close()
    print(render(report))
    print(f"\nwritten {written}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
