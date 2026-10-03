"""Grouping score: how well the stored commitment groups match the labelled commitments.

Usage: python score_grouping.py
Reads workspace/ledger.sqlite (read-only) and the development labels, prints a report, and writes it to
results/grouping_score_<UTC timestamp>.json, never overwriting. It scores what is stored in the ledger: it imports
nothing from the parser, the filter or the consolidation module.
Exit codes: 0 scored and every must-hold passed, 1 scored but a must-hold failed, 2 refused (no ledger, not
consolidated, output file exists). No model calls, no API key.

Predicted groups are matched one-to-one to labelled commitments (greedy by overlap), so fragmented groups cannot all
map to one label: only one fragment gets the label, the others count as mismatches. On equal overlap a complete-key
group is preferred to an incomplete one, then the lower id. Labels never influence how groups are built; they only
score them.

Two metrics are reported per deal: labelled statements whose commitment set matches exactly (x of 15, x of 9), and
labelled commitments whose matched group has exactly the labelled members (x of 8, x of 7).
"""

import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import config
import evaluate

DEALS = ("harbour_bank", "hard_cases")  # deals with grouping must-holds; scoring covers every LEDGER_DEALS deal
TIE_BREAK = "equal overlap: complete-key group before incomplete, then lower predicted id, then lower labelled id"


class ScoreRefused(Exception):
    """Raised when scoring cannot proceed: nothing is written."""


# --- Matching (pure) -----------------------------------------------------------

def jaccard(a: frozenset, b: frozenset) -> float:
    return len(a & b) / len(a | b) if (a | b) else 0.0


def match_groups(predicted: dict, labelled: dict, incomplete=frozenset()) -> dict:
    """One-to-one {predicted id: labelled id}. Only groups that share a statement can pair.

    predicted / labelled: {id: frozenset of statement keys}. incomplete: ids of predicted groups whose terms are
    incomplete. Greedy by descending Jaccard overlap; on equal overlap a complete-key group goes first, then the
    lower predicted id, then the lower labelled id, so the result is deterministic.
    """
    candidates = sorted(
        (-jaccard(p_members, l_members), p_id in incomplete, p_id, l_id)
        for p_id, p_members in predicted.items()
        for l_id, l_members in labelled.items()
        if p_members & l_members
    )
    mapping, used = {}, set()
    for _, _, p_id, l_id in candidates:
        if p_id in mapping or l_id in used:
            continue
        mapping[p_id] = l_id
        used.add(l_id)
    return mapping


def score_statements(label_sets: dict, predicted_of: dict, mapping: dict, stmt_info: dict, groups: dict) -> list:
    """One result per labelled statement: exact or not, with every reason.

    label_sets: {label statement id: set of labelled commitment ids}
    predicted_of: {label statement id: set of predicted group ids containing its ledger statement}
    stmt_info: {label statement id: {"ledger_key": str|None, "kept": int|None, "filter_rule": str|None}}
    groups: {predicted id: {"terms_incomplete", "missing", ...}}
    """
    inverse = {l: p for p, l in mapping.items()}
    results = []
    for sid in sorted(label_sets):
        labelled_ids, predicted_ids, info = label_sets[sid], predicted_of.get(sid, set()), stmt_info[sid]
        reasons = []
        if info["ledger_key"] is None:
            reasons.append("no matching statement in the ledger (an extraction miss)")
        elif info["kept"] == 0:
            reasons.append(f"dropped by the sales filter ({info['filter_rule']})")
        else:
            mapped = {mapping[p] for p in predicted_ids if p in mapping}
            for l in sorted(labelled_ids - mapped):
                partner = inverse.get(l)
                if partner is None:
                    reasons.append(f"labelled {l} has no predicted counterpart (unmatched labelled commitment)")
                else:
                    reasons.append(f"labelled {l} is matched to predicted {partner}, which does not contain this statement")
            for p in sorted(predicted_ids):
                g = groups[p]
                tag = f" (terms incomplete: {', '.join(g['missing'])})" if g["terms_incomplete"] else ""
                if p not in mapping:
                    reasons.append(f"predicted {p}{tag} has no labelled counterpart (unmatched predicted group)")
                elif mapping[p] not in labelled_ids:
                    reasons.append(f"predicted {p}{tag} is matched to labelled {mapping[p]}, which this statement does not belong to")
        results.append({
            "label_statement": sid, "ledger_statement": info["ledger_key"],
            "labelled_commitments": sorted(labelled_ids), "predicted_groups": sorted(predicted_ids),
            "mapped_to": sorted({mapping[p] for p in predicted_ids if p in mapping}),
            "exact": not reasons, "reasons": reasons,
        })
    return results


def group_report(predicted: dict, labelled: dict, mapping: dict, groups: dict, label_commitment_names: dict) -> dict:
    """Group-level view, comparing each group with its matched partner only.

    A statement that belongs to two commitments shares groups legitimately, so overlap alone is not a merge or a
    split; only members missing from, or extra in, the matched partner are reported.
    """
    inverse = {l: p for p, l in mapping.items()}
    all_labelled = set().union(*labelled.values()) if labelled else set()
    holders = lambda stmt: sorted(p for p, m in predicted.items() if stmt in m)
    labelled_rows, predicted_rows = [], []
    for l_id in sorted(labelled):
        members, partner = labelled[l_id], inverse.get(l_id)
        row = {"labelled": l_id, "name": label_commitment_names.get(l_id), "members": sorted(members),
               "partner": partner, "exact_membership": partner is not None and predicted[partner] == members}
        notes = []
        if partner is None:
            notes.append("unmatched labelled commitment")
        else:
            lacks, extra = sorted(members - predicted[partner]), sorted(predicted[partner] - members)
            for stmt in lacks:
                elsewhere = [h for h in holders(stmt) if h != partner]
                unmatched = [h for h in elsewhere if h not in mapping]
                where = f"; held by unmatched predicted {', '.join(unmatched)}" if unmatched else (
                    f"; held by predicted {', '.join(elsewhere)}" if elsewhere else "; held by no predicted group")
                notes.append(f"predicted {partner} lacks {stmt}{where}")
            if extra:
                notes.append(f"predicted {partner} also holds {extra}")
        if notes:
            row["note"] = "; ".join(notes)
        labelled_rows.append(row)
    for p_id in sorted(predicted):
        g, partner = groups[p_id], mapping.get(p_id)
        row = {"predicted": p_id, "name": g["name"], "members": sorted(predicted[p_id]),
               "terms_incomplete": g["terms_incomplete"], "missing": g["missing"], "partner": partner}
        notes = []
        if partner is None:
            sharing = sorted(l for l, lm in labelled.items() if lm & predicted[p_id])
            via = "; ".join(f"shares {sorted(predicted[p_id] & labelled[l])} with labelled {l} (matched to predicted {inverse.get(l)})"
                            for l in sharing)
            notes.append("unmatched predicted group (counts as a mismatch)"
                         + (f"; {via}" if via else "; shares no statement with any labelled commitment"))
        unlabelled = sorted(predicted[p_id] - all_labelled)
        if unlabelled:
            row["unlabelled_members"] = unlabelled
        if notes:
            row["note"] = "; ".join(notes)
        predicted_rows.append(row)
    return {"labelled_commitments": labelled_rows, "predicted_groups": predicted_rows}


# --- Reading the ledger and the labels -------------------------------------------

def read_ledger_deal(conn: sqlite3.Connection, slug: str) -> dict:
    """What the ledger stores for one deal's consolidated review. Nothing here uses the parser or consolidation code."""
    review = conn.execute(
        "SELECT r.id FROM reviews r JOIN deals d ON d.id = r.deal_id WHERE d.slug = ? AND EXISTS"
        " (SELECT 1 FROM review_statements rs WHERE rs.review_id = r.id) ORDER BY r.id DESC", (slug,)).fetchone()
    if review is None:
        raise ScoreRefused(f"{slug}: no consolidated review in the ledger; run ledger_consolidate.py first")
    review_id = review[0]
    statements = {}
    for key, quote, source_key, kept, rule in conn.execute(
        "SELECT s.statement_key, s.quote, so.source_key, rs.kept, rs.filter_rule FROM review_statements rs"
        " JOIN statements s ON s.id = rs.statement_id JOIN source_versions v ON v.id = rs.source_version_id"
        " JOIN sources so ON so.id = v.source_id WHERE rs.review_id = ? ORDER BY s.id", (review_id,)):
        statements[key] = {"quote": quote, "source_id": source_key, "kept": kept, "filter_rule": rule}
    groups, members, member_term_keys = {}, {}, {}
    for cid, ckey, name, terms_json in conn.execute(
        "SELECT c.id, c.commitment_key, a.name, a.terms FROM commitments c JOIN commitment_assessments a"
        " ON a.commitment_id = c.id AND a.review_id = ? ORDER BY c.id", (review_id,)):
        t = json.loads(terms_json) if terms_json else {}
        groups[ckey] = {"name": name, "terms_incomplete": bool(t.get("terms_incomplete")), "missing": t.get("missing", []),
                        "key": t.get("key"), "rules_sha256": t.get("config_sha256")}
        member_term_keys[ckey] = [(m.get("term_set") or {}).get("key") for m in t.get("members", [])]
        members[ckey] = frozenset(r[0] for r in conn.execute(
            "SELECT s.statement_key FROM review_statement_commitments l JOIN statements s ON s.id = l.statement_id"
            " WHERE l.commitment_id = ? AND l.review_id = ?", (cid, review_id)))
    return {"review_id": review_id, "statements": statements, "groups": groups, "members": members,
            "member_term_keys": member_term_keys}


def read_labels(slug: str, data_dir=None) -> dict:
    """The development labels for one deal. Only deals in ALLOWED_DEALS can be read, as everywhere else."""
    config.require_allowed_deal(slug)
    base = (Path(data_dir) if data_dir is not None else config.DATA_DIR) / slug / "labels"
    statements_raw = (base / "statements.json").read_bytes()
    commitments_raw = (base / "commitments.json").read_bytes()
    return {
        "statements": json.loads(statements_raw.decode("utf-8"))["statements"],
        "commitments": json.loads(commitments_raw.decode("utf-8"))["commitments"],
        "statements_sha256": hashlib.sha256(statements_raw).hexdigest(),
        "commitments_sha256": hashlib.sha256(commitments_raw).hexdigest(),
    }


def pinned_run_quotes(slug: str, results_dir=None) -> dict:
    """{statement id: quote} from the pinned frozen run file, the source the import read. {} if unreadable."""
    base = Path(results_dir) if results_dir is not None else config.RESULTS_DIR
    try:
        run = json.loads((base / config.LEDGER_IMPORT_RUN_FILES[slug]).read_text(encoding="utf-8"))
    except (OSError, ValueError, KeyError):
        return {}
    return {s["statement_id"]: s["quote"] for d in run["documents"] for s in d["statements"]}


# --- Scoring a deal ----------------------------------------------------------------

def score_deal(slug: str, ledger: dict, labels: dict, run_quotes: dict) -> dict:
    outputs = [{"statement_id": k, "source_id": v["source_id"], "quote": v["quote"]} for k, v in ledger["statements"].items()]
    assigned = evaluate.assign(labels["statements"], outputs, config.MATCH_THRESHOLD, config.NEAR_MISS_FLOOR)
    ledger_key = {l["id"]: o["statement_id"] for _, l, o in assigned["matches"]}

    label_sets = {l["id"]: set(l["commitment_ids"]) for l in labels["statements"]}
    labelled = {c["id"]: frozenset(ledger_key[s] for s, cs in label_sets.items() if c["id"] in cs and s in ledger_key)
                for c in labels["commitments"]}
    predicted = ledger["members"]
    incomplete = frozenset(g for g, v in ledger["groups"].items() if v["terms_incomplete"])
    mapping = match_groups(predicted, labelled, incomplete)

    stmt_info = {}
    for sid in label_sets:
        key = ledger_key.get(sid)
        stmt = ledger["statements"].get(key) if key else None
        stmt_info[sid] = {"ledger_key": key, "kept": stmt["kept"] if stmt else None,
                          "filter_rule": stmt["filter_rule"] if stmt else None}
    predicted_of = {sid: {p for p, m in predicted.items() if ledger_key.get(sid) in m} for sid in label_sets}

    statements = score_statements(label_sets, predicted_of, mapping, stmt_info, ledger["groups"])
    groups = group_report(predicted, labelled, mapping, ledger["groups"], {c["id"]: c["name"] for c in labels["commitments"]})
    exact_statements = sum(1 for s in statements if s["exact"])
    exact_commitments = sum(1 for r in groups["labelled_commitments"] if r["exact_membership"])
    return {
        "deal": slug, "review_id": ledger["review_id"],
        "metrics": {
            "statements": {"exact": exact_statements, "of": len(statements)},
            "commitments": {"exact": exact_commitments, "of": len(labelled)},
        },
        "predicted_groups": len(predicted),
        "unmatched_predicted_groups": sorted(set(predicted) - set(mapping)),
        "unmatched_labelled_commitments": sorted(set(labelled) - set(mapping.values())),
        "mapping": dict(sorted(mapping.items())),
        "statements": statements, "groups": groups,
        "must_hold": must_holds(slug, ledger, ledger_key, label_sets, predicted, mapping, run_quotes),
    }


def must_holds(slug, ledger, ledger_key, label_sets, predicted, mapping, run_quotes) -> list:
    """Pass/fail on each must-hold from the brief that applies to this deal."""
    checks = []

    def add(name, passed, detail):
        checks.append({"must_hold": name, "passed": bool(passed), "detail": detail})

    labelled_keys = {ledger_key[s] for s in label_sets if s in ledger_key}
    dropped = {k: v["filter_rule"] for k, v in ledger["statements"].items() if not v["kept"]}
    dropped_labelled = sorted(k for k in dropped if k in labelled_keys)
    add("no labelled statement is dropped by the filter", not dropped_labelled,
        f"dropped: {sorted(dropped)}; labelled among them: {dropped_labelled}")

    complete = [(g, v) for g, v in ledger["groups"].items() if not v["terms_incomplete"]]
    mixed = [g for g, v in complete if any(k != v["key"] for k in ledger["member_term_keys"].get(g, []))]
    add("differing terms are never collapsed into one commitment (every complete group has one key)",
        not mixed and len({v["key"] for _, v in complete}) == len(complete),
        f"complete groups {len(complete)}, groups with mixed keys {mixed}")

    if slug == "harbour_bank":
        add("exactly the five sales-process statements are dropped", len(dropped) == 5 and not dropped_labelled,
            f"dropped {len(dropped)}: {sorted(dropped)}")
        s15 = ledger_key.get("S15")
        add("S15 (weekly project status meeting) is kept and linked",
            s15 is not None and ledger["statements"][s15]["kept"] == 1 and any(s15 in m for m in predicted.values()),
            f"S15 = {s15}")
        s04 = ledger_key.get("S04")
        groups_of_s04 = sorted(p for p, m in predicted.items() if s04 in m)
        mapped = sorted(mapping[p] for p in groups_of_s04 if p in mapping)
        add("S04 is linked to both the C01 and C02 groups", {"C01", "C02"} <= set(mapped),
            f"S04 = {s04}; its groups {groups_of_s04} map to labelled {mapped}")
        c1 = {ledger_key[s] for s, cs in label_sets.items() if s in ledger_key and cs == {"C01"}}
        c3 = {ledger_key[s] for s, cs in label_sets.items() if s in ledger_key and cs == {"C03"}}
        merged = sorted(p for p, m in predicted.items() if m & c1 and m & c3)
        add("C01 (real-time Polygon) and C03 (hourly-batch Polygon) are never merged", not merged,
            f"groups holding statements exclusive to both: {merged}")
    if slug == "hard_cases":
        k04, k08 = ledger_key.get("K04"), ledger_key.get("K08")
        shared = sorted(p for p, m in predicted.items() if k04 and k08 and k04 in m and k08 in m)
        k04_groups = {p for p, m in predicted.items() if k04 in m}
        add("K04 (\"thirty thousand\") and K08 (\"30,000\") share one commitment", bool(shared) and len(k04_groups) == 1,
            f"K04 = {k04}, K08 = {k08}; shared groups {shared}")
        quotes_ok = bool(run_quotes) and all(
            k and ledger["statements"][k]["quote"].encode("utf-8") == run_quotes.get(k, "").encode("utf-8") for k in (k04, k08))
        add("K04 and K08 quotes are stored verbatim", quotes_ok,
            f"byte-identical to the pinned run file: {k04}, {k08}" if run_quotes else "the pinned run file could not be read")
    return checks


# --- Report and output ------------------------------------------------------------

def render(report: dict) -> str:
    lines = []
    for slug, d in report["deals"].items():
        m = d["metrics"]
        lines.append(f"== {slug}: statements {m['statements']['exact']} of {m['statements']['of']} exact; "
                     f"commitments {m['commitments']['exact']} of {m['commitments']['of']} exact; "
                     f"{d['predicted_groups']} predicted groups")
        for s in d["statements"]:
            if not s["exact"]:
                lines.append(f"  MISMATCH {s['label_statement']} ({s['ledger_statement']}): labelled {s['labelled_commitments']}, "
                             f"predicted {s['predicted_groups']}")
                lines += [f"      - {r}" for r in s["reasons"]]
        for g in d["groups"]["labelled_commitments"]:
            if g.get("note"):
                lines.append(f"  GROUP labelled {g['labelled']} ({g['name']}): {g['note']}")
        for g in d["groups"]["predicted_groups"]:
            if g.get("note") or g.get("unlabelled_members"):
                extra = f"unlabelled members {g['unlabelled_members']}" if g.get("unlabelled_members") else ""
                lines.append(f"  GROUP predicted {g['predicted']} ({g['name']}): {g.get('note', '')} {extra}".rstrip())
        for c in d["must_hold"]:
            lines.append(f"  [{'PASS' if c['passed'] else 'FAIL'}] {c['must_hold']} -- {c['detail']}")
    return "\n".join(lines)


def build_report(conn: sqlite3.Connection, data_dir=None, results_dir=None) -> dict:
    deals = {}
    for slug in config.LEDGER_DEALS:
        ledger = read_ledger_deal(conn, slug)
        labels = read_labels(slug, data_dir)
        deal = score_deal(slug, ledger, labels, pinned_run_quotes(slug, results_dir))
        deal["labels_sha256"] = {"statements": labels["statements_sha256"], "commitments": labels["commitments_sha256"]}
        deal["rules_sha256"] = sorted({g["rules_sha256"] for g in ledger["groups"].values() if g["rules_sha256"]})
        deals[slug] = deal
    return {"tie_break": TIE_BREAK, "deals": deals}


def all_passed(report: dict) -> bool:
    return all(c["passed"] for d in report["deals"].values() for c in d["must_hold"])


def write_report(report: dict, results_dir=None, now: datetime | None = None) -> Path:
    """Write the report to results/grouping_score_<UTC timestamp>.json. Refuses to overwrite an existing file."""
    base = Path(results_dir) if results_dir is not None else config.RESULTS_DIR
    now = now or datetime.now(timezone.utc)
    path = base / f"grouping_score_{now.strftime('%Y%m%dT%H%M%SZ')}.json"
    body = {"timestamp_utc": now.isoformat(timespec="seconds"), **report}
    base.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "x", encoding="utf-8") as f:
            json.dump(body, f, indent=2, ensure_ascii=False)
            f.write("\n")
    except FileExistsError:
        raise ScoreRefused(f"Refusing to overwrite {path}") from None
    return path


def open_read_only(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)


def main(argv: list) -> int:
    if argv:
        print("usage: python score_grouping.py", file=sys.stderr)
        return 2
    path = config.LEDGER_DB_PATH
    if not path.exists():
        print(f"refused: {path} does not exist; build it with ledger_import.py and ledger_consolidate.py", file=sys.stderr)
        return 2
    conn = open_read_only(path)
    try:
        report = build_report(conn)
        written = write_report(report)
    except ScoreRefused as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    finally:
        conn.close()
    print(render(report))
    print(f"\nwritten {written}")
    return 0 if all_passed(report) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
