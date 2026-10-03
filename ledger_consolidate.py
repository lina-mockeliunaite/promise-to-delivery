"""Consolidation and write path: filter, parse, group, and write a build-time review's picture to the ledger.

Usage: python ledger_consolidate.py
Consolidates the build-time review of every deal in config.LEDGER_DEALS in the existing workspace/ledger.sqlite.
Exit codes: 0 consolidated, 2 refused (nothing written). No model calls, no API key.

When unsure, keep apart and keep visible. Statements group only on an equal, complete term-set key. A term set with
anything missing never merges with another. Labels never influence how groups are built.
"""

import hashlib
import json
import sqlite3
import sys
from pathlib import Path

import config
import ledger
import ledger_import
import sales_filter
import terms

HERE = Path(__file__).resolve().parent
RULE_FILES = ("terms.py", "sales_filter.py", "ledger_consolidate.py")
LANGUAGE_RANK = {"exploratory": 0, "conditional": 1, "firm": 2}
WHEN_LABELS = {"launch": "at launch", "end_of_first_year": "by end of first year"}
BOUND_LABELS = {"max": "up to ", "min": "at least "}


class ConsolidationError(Exception):
    """Raised when consolidation refuses: nothing has been written."""


def rules_sha256(catalogue_bytes: bytes) -> str:
    """Hash of everything that decides the result: the rule modules and the catalogue."""
    digest = hashlib.sha256()
    for name in RULE_FILES:
        digest.update(name.encode() + b"\0" + (HERE / name).read_bytes() + b"\0")
    digest.update(b"catalogue.json\0" + catalogue_bytes)
    return digest.hexdigest()


# --- Names ------------------------------------------------------------------

def commitment_name(ts, vocab) -> str | None:
    """A readable, deterministic name from a term set, or None if there is nothing to name it by."""
    if ts is None:
        return None
    if ts.promise_type == "go_live":
        return "Go-live"
    cap = vocab.capabilities.get(ts.capability)
    if cap is None:
        return None
    detail = []
    if ts.network:
        detail.append(ts.network)
    if ts.mode:
        detail.append(ts.mode.replace("_", " "))
    if ts.region and "region" in cap.key_dims:
        detail.append(ts.region)
    if ts.quantity:
        q = ts.quantity
        detail.append(f"{BOUND_LABELS.get(q['bound'], '')}{q['value']:,} {q['unit'] or '?'} per {q['period'] or '?'}")
        detail += [WHEN_LABELS.get(w, w) for w in ts.when]
    return cap.name + (": " + ", ".join(detail) if detail else "")


# --- Planning (pure) --------------------------------------------------------

def plan_review(statements: list, vocab: terms.Vocabulary, config_sha256: str) -> dict:
    """Decide the filter outcome and the commitment groups. No database access.

    statements: dicts with statement_id, source_version_id, statement_key, quote, language, in source order.
    Returns {"statements": [...], "commitments": [...]} in the order they should be written.
    """
    outcomes, groups, order = [], {}, []
    for st in statements:
        decision = sales_filter.classify(st["quote"], vocab)
        outcomes.append({
            "statement_id": st["statement_id"], "source_version_id": st["source_version_id"],
            "kept": 1 if decision.kept else 0, "filter_rule": decision.rule,
        })
        if not decision.kept:
            continue
        parsed = terms.parse_terms(st["quote"], vocab)
        sets = list(parsed.term_sets)
        if parsed.ambiguous or not sets:
            sets.append(None)  # an ambiguous association: a group of its own, never merged
        for index, ts in enumerate(sets):
            complete = ts is not None and ts.key is not None
            group_id = ("key", ts.key) if complete else ("incomplete", st["statement_key"], index)
            if group_id not in groups:
                missing = list(ts.missing) if ts is not None else ["association"]
                groups[group_id] = {"complete": complete, "ts": ts, "missing": missing, "members": []}
                order.append(group_id)
            groups[group_id]["members"].append({
                "statement": st, "ts": ts, "dates": parsed.dates, "cadence": parsed.cadence,
            })

    commitments = []
    for n, group_id in enumerate(order, start=1):
        group = groups[group_id]
        members = group["members"]
        language = max((m["statement"]["language"] for m in members), key=LANGUAGE_RANK.__getitem__)
        name = commitment_name(group["ts"], vocab) or "Unclassified promise: " + members[0]["statement"]["quote"][:50].strip()
        if not group["complete"]:
            name += f" [terms incomplete: {', '.join(group['missing'])}; {members[0]['statement']['statement_key']}]"
        by_language = {}
        for m in members:
            by_language.setdefault(m["statement"]["language"], []).append(m["statement"]["statement_key"])
        listing = "; ".join(
            f"{lang}: {', '.join(by_language[lang])}" for lang in sorted(by_language, key=LANGUAGE_RANK.__getitem__, reverse=True)
        )
        commitments.append({
            "commitment_key": f"C{n:02d}",
            "name": name,
            "language": language,
            "support_state": "supported",
            "rationale": f"Firmest of {len(members)} kept statement(s) is {language}. {listing}.",
            "members": [(m["statement"]["statement_id"], m["statement"]["source_version_id"]) for m in members],
            "terms": {
                "config_sha256": config_sha256,
                "key": group["ts"].key if group["complete"] else None,
                "terms_incomplete": not group["complete"],
                "missing": group["missing"],
                "members": [
                    {
                        "statement_key": m["statement"]["statement_key"],
                        "term_set": m["ts"].as_dict() if m["ts"] is not None else None,
                        "dates": m["dates"], "cadence": m["cadence"],
                    }
                    for m in members
                ],
            },
        })
    return {"statements": outcomes, "commitments": commitments}


# --- Writing ----------------------------------------------------------------

def _load_vocabulary(catalogue_path=None):
    path = Path(catalogue_path) if catalogue_path is not None else config.DATA_DIR / "catalogue.json"
    try:
        raw = path.read_bytes()
        return terms.build_vocabulary(json.loads(raw.decode("utf-8"))), raw
    except (OSError, ValueError) as exc:
        raise ConsolidationError(f"cannot read the catalogue: {exc}") from exc


def _consolidate_review(conn: sqlite3.Connection, review_id: int, vocab, catalogue_bytes: bytes) -> dict:
    """Plan and write one review. Never commits."""
    row = conn.execute(
        "SELECT r.deal_id, d.slug FROM reviews r JOIN deals d ON d.id = r.deal_id WHERE r.id = ?", (review_id,)
    ).fetchone()
    if row is None:
        raise ConsolidationError(f"no review {review_id}")
    deal_id, slug = row
    ledger.require_ledger_deal(slug)
    if conn.execute("SELECT 1 FROM review_statements WHERE review_id = ?", (review_id,)).fetchone() or conn.execute(
        "SELECT 1 FROM commitments WHERE deal_id = ?", (deal_id,)
    ).fetchone():
        raise ConsolidationError(f"{slug}: already consolidated; this never merges into existing commitments")

    statements = [
        {"statement_id": sid, "source_version_id": vid, "statement_key": key, "quote": quote, "language": language}
        for sid, vid, key, quote, language in conn.execute(
            "SELECT s.id, rs.source_version_id, s.statement_key, s.quote, s.language FROM review_sources rs"
            " JOIN statements s ON s.extraction_id = rs.extraction_id WHERE rs.review_id = ?"
            " ORDER BY rs.source_version_id, s.ordinal", (review_id,),
        )
    ]
    plan = plan_review(statements, vocab, rules_sha256(catalogue_bytes))

    for o in plan["statements"]:
        conn.execute(
            "INSERT INTO review_statements (review_id, statement_id, source_version_id, kept, filter_rule)"
            " VALUES (?, ?, ?, ?, ?)",
            (review_id, o["statement_id"], o["source_version_id"], o["kept"], o["filter_rule"]),
        )
    for c in plan["commitments"]:
        commitment_id = conn.execute(
            "INSERT INTO commitments (deal_id, commitment_key, created_review_id) VALUES (?, ?, ?)",
            (deal_id, c["commitment_key"], review_id),
        ).lastrowid
        for statement_id, version_id in c["members"]:
            conn.execute(
                "INSERT INTO review_statement_commitments (review_id, statement_id, source_version_id, commitment_id)"
                " VALUES (?, ?, ?, ?)",
                (review_id, statement_id, version_id, commitment_id),
            )
        conn.execute(
            "INSERT INTO commitment_assessments (review_id, commitment_id, name, language, support_state, rationale, terms)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (review_id, commitment_id, c["name"], c["language"], c["support_state"], c["rationale"],
             json.dumps(c["terms"], sort_keys=True)),
        )
    return plan


def consolidate_review(conn: sqlite3.Connection, review_id: int, catalogue_path=None) -> dict:
    """Consolidate one review atomically: all its rows are written, or none."""
    vocab, raw = _load_vocabulary(catalogue_path)
    try:
        plan = _consolidate_review(conn, review_id, vocab, raw)
    except BaseException:
        conn.rollback()
        raise
    conn.commit()
    return plan


def consolidate_all(conn: sqlite3.Connection, catalogue_path=None) -> dict:
    """Consolidate the build-time review of every LEDGER_DEALS deal in one transaction. Returns {slug: plan}."""
    vocab, raw = _load_vocabulary(catalogue_path)
    plans = {}
    try:
        for slug in config.LEDGER_DEALS:
            reviews = [
                r[0] for r in conn.execute(
                    "SELECT r.id FROM reviews r JOIN deals d ON d.id = r.deal_id"
                    " WHERE d.slug = ? AND r.run_kind = 'review' AND r.checker = 'rules' ORDER BY r.id", (slug,),
                )
            ]
            if len(reviews) != 1:
                raise ConsolidationError(f"{slug}: expected one build-time review, found {len(reviews)}")
            plans[slug] = _consolidate_review(conn, reviews[0], vocab, raw)
    except BaseException:
        conn.rollback()
        raise
    conn.commit()
    return plans


def main(argv: list) -> int:
    if argv:
        print("usage: python ledger_consolidate.py", file=sys.stderr)
        return 2
    path = config.LEDGER_DB_PATH
    if not path.exists():
        print(f"refused: {path} does not exist; build it with ledger_import.py first", file=sys.stderr)
        return 2
    conn = ledger.connect(path)
    try:
        if ledger.schema_version(conn) != ledger.SCHEMA_VERSION or "terms" not in {
            r[1] for r in conn.execute("PRAGMA table_info(commitment_assessments)")
        }:
            print("refused: the database was built from an older schema; run ledger_import.py --rebuild", file=sys.stderr)
            return 2
        try:
            plans = consolidate_all(conn)
        except (ConsolidationError, ledger.LedgerDealNotAllowed) as exc:
            print(f"refused: {exc}", file=sys.stderr)
            return 2
        print(f"consolidated {path}")
        for slug, plan in plans.items():
            kept = sum(o["kept"] for o in plan["statements"])
            print(f"  {slug}: {len(plan['statements'])} statements ({kept} kept), {len(plan['commitments'])} commitments")
        for table, n in ledger_import.table_counts(conn).items():
            print(f"    {table:32} {n}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
