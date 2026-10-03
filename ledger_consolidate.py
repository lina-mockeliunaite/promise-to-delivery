"""Consolidation and write path: filter, parse, group, and write a build-time review's picture to the ledger.

Usage: python ledger_consolidate.py
Consolidates the build-time review of every deal in config.LEDGER_DEALS in the existing workspace/ledger.sqlite, then
runs the rules (rules.py) in the same review and transaction: assessments, issues with their raised closure checks,
reference resolutions and links.
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
import references
import rules
import sales_filter
import terms

HERE = Path(__file__).resolve().parent
RULE_FILES = ("terms.py", "sales_filter.py", "ledger_consolidate.py", "references.py", "rules.py")
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


# --- Filling terms from a referenced section (pure) ----------------------------

FILLABLE_DIMS = ("network", "asset", "mode", "region")


def fill_from_reference(ts, reference: dict, vocab: terms.Vocabulary):
    """A copy of an incomplete term set with its missing terms taken from a referenced section, or ts unchanged.

    reference: {"label", "source_key", "quotes": [(statement_key, quote), ...]} for the statements inside the section
    the pointer cites. A missing term is filled only if every complete term set in the section that matches the
    pointer's capability and every key term the pointer does state agrees on one value. No agreement, no fill.
    Capability, quantity and ambiguous associations are never filled. The quote itself is never changed.
    """
    if ts is None or ts.key is not None or not ts.missing or any(m not in FILLABLE_DIMS for m in ts.missing):
        return ts
    cap = vocab.capabilities.get(ts.capability)
    if cap is None:
        return ts
    candidates = []
    for key, quote in reference["quotes"]:
        for other in terms.parse_terms(quote, vocab).term_sets:
            if other.key is None or other.capability != ts.capability:
                continue
            if all(getattr(ts, d) is None or getattr(ts, d) == getattr(other, d) for d in cap.key_dims):
                candidates.append((key, other))
    if not candidates:
        return ts
    filled, values = {}, {}
    for d in ts.missing:
        found = {getattr(o, d) for _, o in candidates}
        if len(found) != 1 or None in found:
            return ts
        values[d] = found.pop()
        filled[d] = {"value": values[d], "from": sorted({k for k, _ in candidates}),
                     "via": f"{reference['label']} ({reference['source_key']})"}
    new = terms.TermSet(**{**ts.__dict__, **values, "missing": [], "filled": filled, "key": None})
    if "network" in values:
        new.network_in_catalogue = values["network"] in vocab.networks
    new.key = terms._key(new, cap)
    return new


# --- Planning (pure) --------------------------------------------------------

def plan_review(statements: list, vocab: terms.Vocabulary, config_sha256: str, referenced: dict | None = None) -> dict:
    """Decide the filter outcome and the commitment groups. No database access.

    statements: dicts with statement_id, source_version_id, statement_key, quote, language, in source order.
    referenced: optional {statement_key: reference} for pointer statements whose quote cites a section
    (see fill_from_reference). Built from the documents, never from labels.
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
        if referenced and st["statement_key"] in referenced:
            sets = [fill_from_reference(ts, referenced[st["statement_key"]], vocab) for ts in sets]
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


def _review_versions(conn: sqlite3.Connection, review_id: int) -> list:
    return [
        references.Version(vid, key, doc_type, doc_date, text, bool(included))
        for vid, key, doc_type, doc_date, text, included in conn.execute(
            "SELECT v.id, so.source_key, v.doc_type, v.doc_date, v.canonical_text, v.included FROM review_sources rs"
            " JOIN source_versions v ON v.id = rs.source_version_id JOIN sources so ON so.id = v.source_id"
            " WHERE rs.review_id = ? ORDER BY v.id", (review_id,))
    ]


def referenced_sections(statements: list, versions: list) -> dict:
    """{statement_key: reference} for statements whose quote cites a section that exists in the selected documents.

    The reference holds the statements found inside that section (by quote position in the canonical text).
    """
    by_id = {v.id: v for v in versions}
    out = {}
    for st in statements:
        m = references.SECTION_REF.search(st["quote"])
        if not m or st["source_version_id"] not in by_id:
            continue
        found = references.referenced_section(st["quote"], by_id[st["source_version_id"]], versions)
        if not found:
            continue
        target, (start, end) = found
        quotes = []
        for other in statements:
            if other is st or other["source_version_id"] != target.id:
                continue
            pos = target.text.find(other["quote"])
            if pos != -1 and start <= pos < end:
                quotes.append((other["statement_key"], other["quote"]))
        if quotes:
            out[st["statement_key"]] = {"label": f"{m.group(1)} {m.group(2)}", "source_key": target.source_key,
                                        "quotes": quotes}
    return out


def _write_rules(conn, review_id, deal_id, plan, assessments, chain, versions, ids, config_sha256) -> None:
    """Issues with their raised closure checks, links and reference resolutions. Same transaction as the rest."""
    source_ids = dict(conn.execute("SELECT source_key, id FROM sources WHERE deal_id = ?", (deal_id,)).fetchall())
    for r in chain.resolutions:
        conn.execute(
            "INSERT INTO reference_resolutions (review_id, from_version_id, from_locator, target_source_id, target_locator,"
            " cited_label, cited_date, resolved_version_id, status, reason) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (review_id, r.from_version_id, r.from_locator, source_ids.get(r.target_source_key) if r.target_source_key else None,
             r.target_locator, r.cited_label, r.cited_date, r.resolved_version_id, r.status, r.reason),
        )
    for c in plan["commitments"]:
        a = assessments[c["commitment_key"]]
        for issue in a.issues:
            issue_id = conn.execute(
                "INSERT INTO issues (commitment_id, issue_type, subject_key, owner_function, raised_review_id, raised_by,"
                " raised_config_sha256, closure_criteria, criteria_version, absolute_limit)"
                " VALUES (?, ?, ?, ?, ?, 'rules', ?, ?, ?, ?)",
                (ids[c["commitment_key"]], issue["issue_type"], issue["subject_key"], issue["owner_function"], review_id,
                 config_sha256, json.dumps(issue["closure_criteria"], sort_keys=True), rules.CRITERIA_VERSION,
                 issue["absolute_limit"]),
            ).lastrowid
            raised = issue["raised"]
            conn.execute(
                "INSERT INTO closure_checks (issue_id, review_id, check_kind, outcome, evidence_checked, reason, unmet,"
                " re_raised) VALUES (?, ?, 'raised', ?, ?, ?, ?, 1)",
                (issue_id, review_id, raised["outcome"], json.dumps(raised["evidence_checked"], sort_keys=True),
                 raised["reason"], json.dumps(raised["unmet"])),
            )
        for from_key, to_key, link_type, basis in a.links:
            conn.execute(
                "INSERT INTO commitment_links (review_id, from_commitment_id, to_commitment_id, link_type, basis)"
                " VALUES (?, ?, ?, ?, ?)", (review_id, ids[from_key], ids[to_key], link_type, basis),
            )


def _consolidate_review(conn: sqlite3.Connection, review_id: int, vocab, catalogue_bytes: bytes, assess: bool = False) -> dict:
    """Plan and write one review. Never commits. With assess=True the rules run in the same review and transaction."""
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
    versions = _review_versions(conn, review_id)
    config_sha256 = rules_sha256(catalogue_bytes)
    plan = plan_review(statements, vocab, config_sha256, referenced_sections(statements, versions))
    assessments, chain = {}, None
    if assess:
        chain = references.contract_chain(versions)
        info = {st["statement_key"]: {"quote": st["quote"], "language": st["language"],
                                      "source_version_id": st["source_version_id"]} for st in statements}
        assessments = rules.assess(plan, versions, chain, json.loads(catalogue_bytes.decode("utf-8")), vocab, info)

    for o in plan["statements"]:
        conn.execute(
            "INSERT INTO review_statements (review_id, statement_id, source_version_id, kept, filter_rule)"
            " VALUES (?, ?, ?, ?, ?)",
            (review_id, o["statement_id"], o["source_version_id"], o["kept"], o["filter_rule"]),
        )
    ids = {}
    for c in plan["commitments"]:
        commitment_id = conn.execute(
            "INSERT INTO commitments (deal_id, commitment_key, created_review_id) VALUES (?, ?, ?)",
            (deal_id, c["commitment_key"], review_id),
        ).lastrowid
        ids[c["commitment_key"]] = commitment_id
        for statement_id, version_id in c["members"]:
            conn.execute(
                "INSERT INTO review_statement_commitments (review_id, statement_id, source_version_id, commitment_id)"
                " VALUES (?, ?, ?, ?)",
                (review_id, statement_id, version_id, commitment_id),
            )
        if not assess:
            conn.execute(
                "INSERT INTO commitment_assessments (review_id, commitment_id, name, language, support_state, rationale, terms)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (review_id, commitment_id, c["name"], c["language"], c["support_state"], c["rationale"],
                 json.dumps(c["terms"], sort_keys=True)),
            )
            continue
        a = assessments[c["commitment_key"]]
        conn.execute(
            "INSERT INTO commitment_assessments (review_id, commitment_id, name, language, authorisation,"
            " authorisation_evidence, evidence_refs, contractual_presence, presence_detail, support_state, rationale, terms)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (review_id, commitment_id, c["name"], c["language"], a.authorisation, a.authorisation_evidence,
             json.dumps(a.evidence_refs, sort_keys=True), a.contractual_presence, a.presence_detail, c["support_state"],
             c["rationale"], json.dumps(c["terms"], sort_keys=True)),
        )
    if assess:
        _write_rules(conn, review_id, deal_id, plan, assessments, chain, versions, ids, config_sha256)
        plan["assessments"] = assessments
    return plan


def consolidate_review(conn: sqlite3.Connection, review_id: int, catalogue_path=None, assess: bool = False) -> dict:
    """Consolidate one review atomically: all its rows are written, or none. assess=True also runs the rules."""
    vocab, raw = _load_vocabulary(catalogue_path)
    try:
        plan = _consolidate_review(conn, review_id, vocab, raw, assess)
    except BaseException:
        conn.rollback()
        raise
    conn.commit()
    return plan


def consolidate_all(conn: sqlite3.Connection, catalogue_path=None, assess: bool = False) -> dict:
    """Consolidate the build-time review of every LEDGER_DEALS deal in one transaction. Returns {slug: plan}.

    assess=True also runs the rules (rules.py) in the same review and the same transaction.
    """
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
            plans[slug] = _consolidate_review(conn, reviews[0], vocab, raw, assess)
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
            plans = consolidate_all(conn, assess=True)
        except (ConsolidationError, ledger.LedgerDealNotAllowed) as exc:
            print(f"refused: {exc}", file=sys.stderr)
            return 2
        print(f"consolidated {path}")
        for slug, plan in plans.items():
            kept = sum(o["kept"] for o in plan["statements"])
            print(f"  {slug}: {len(plan['statements'])} statements ({kept} kept), {len(plan['commitments'])} commitments")
            for c in plan["commitments"]:
                a = plan["assessments"][c["commitment_key"]]
                found = ", ".join(i["issue_type"] for i in a.issues) or "no issues"
                print(f"    {c['commitment_key']} {c['name'][:60]:60} {a.authorisation or 'n/a':22} {a.contractual_presence:27} {found}")
        for table, n in ledger_import.table_counts(conn).items():
            print(f"    {table:32} {n}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
