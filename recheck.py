"""Recheck: re-evaluate every commitment and every issue of a deal after a fix, with the same rules.

Usage (library): recheck(conn, slug, fix_id=None, client=None)
- With an approved fix: a 'recheck_after_fix' review. Without: an 'unchanged_input_rerun'.
- Extraction: an unchanged source version reuses the extraction its previous review used; a new extractable version
  goes through the full-key cache (extraction_cache.py), calling the model only on a miss. An unchanged-input rerun
  therefore makes no model call.
- Consolidation and rules run exactly as in a review (ledger_consolidate.plan_review, rules.assess). Each group keeps
  the identity of the previous commitment it shares the most statements with (by source and quote); a previous
  commitment with no statement left is recorded as 'unsupported' (shown as "Not in current documents"), never deleted.
- Every existing issue gets one 'recheck' closure check. Closure is a decision about evidence: an issue is 'met' only
  when this review no longer finds it AND its own closure condition holds with evidence (approval recorded, the
  contract now includes the promise, the conflicting contract term is gone, the missing evidence now exists, or the
  promise was withdrawn in a newer version of every source that made it). Not being re-raised is never enough, so an
  issue another checker raised stays open until its condition is met. An absolute limit is never closed by an
  allowed exception (also enforced by a database trigger). New issues the recheck finds are raised as usual.
All of it is one transaction: the review is written completely or not at all.
"""

import hashlib
import json
import sqlite3
from pathlib import Path

import config
import extraction_cache
import integrity
import ledger
import ledger_consolidate as lc
import ledger_fixes
import references
import rules


class RecheckError(Exception):
    pass


def _quote_sha(quote: str) -> str:
    return hashlib.sha256(quote.encode("utf-8")).hexdigest()


def _latest_review(conn, did: int):
    """The latest complete assessed review, or None for a deal never reviewed (a user deal's first review)."""
    row = conn.execute("SELECT MAX(a.review_id) FROM commitment_assessments a JOIN reviews r ON r.id = a.review_id"
                       " WHERE r.deal_id = ? AND r.status = 'complete'", (did,)).fetchone()
    return row[0] if row and row[0] is not None else None


def _previous_members(conn, review_id: int) -> dict:
    """{commitment_id: {(source_key, quote_sha256)}} for the previous review's links."""
    out = {}
    for cid, key, quote in conn.execute(
        "SELECT l.commitment_id, so.source_key, s.quote FROM review_statement_commitments l"
        " JOIN statements s ON s.id = l.statement_id JOIN source_versions v ON v.id = l.source_version_id"
        " JOIN sources so ON so.id = v.source_id WHERE l.review_id = ?", (review_id,)):
        out.setdefault(cid, set()).add((key, _quote_sha(quote)))
    return out


def _assign_identities(plan: dict, statements: dict, previous: dict, existing_keys: dict) -> dict:
    """{plan group index: commitment_id or None}. Largest overlap first; each previous commitment used once."""
    candidates = []
    for gi, c in enumerate(plan["commitments"]):
        members = {(statements[sid]["source_key"], _quote_sha(statements[sid]["quote"])) for sid, _ in c["members"]}
        for cid, prev in previous.items():
            overlap = len(members & prev)
            if overlap:
                candidates.append((-overlap, existing_keys[cid], gi, cid))
    assigned, used = {}, set()
    for _, _, gi, cid in sorted(candidates):
        if gi not in assigned and cid not in used:
            assigned[gi] = cid
            used.add(cid)
    return {gi: assigned.get(gi) for gi in range(len(plan["commitments"]))}


def _closing_evidence(issue, a, unsupported_now, assessments_by_cid, presence_by_key, closing_versions):
    """Evidence rows that show the issue's closure condition holds now, or None."""
    itype, subject = issue["issue_type"], issue["subject_key"]
    if unsupported_now:
        return closing_versions or None
    refs = a.evidence_refs if a else {}
    contract = [{"source_version_id": r["source_version_id"], "locator": "whole document", "role": "contract"}
                for r in refs.get("source_versions", []) if r.get("role") == "contract"]
    approval = [{"source_version_id": r["source_version_id"], "locator": r.get("line") or "whole note",
                 "role": "approval_evidence"} for r in refs.get("source_versions", []) if r.get("role") == "approval_evidence"]
    if itype == "approval":
        return approval if a.authorisation in ("standard_authorised", "exception_approved") and approval else None
    if itype == "contract_gap":
        return contract if a.contractual_presence == "included_in_draft_contract" and contract else None
    if itype == "conflicting_terms":
        other = subject.split(":", 1)[1] if ":" in subject else None
        other_contract_side = presence_by_key.get(other) == "included_in_draft_contract"
        return contract if a.contractual_presence == "included_in_draft_contract" and contract and not other_contract_side else None
    if itype == "insufficient_evidence" and subject == "authorisation":
        decided = a.authorisation not in ("unknown_needs_review", "not_assessed", None)
        rows = approval or [{"source_version_id": r["source_version_id"], "locator": "whole document", "role": r.get("role")}
                            for r in refs.get("source_versions", [])]
        return rows if decided and rows else None
    if itype == "insufficient_evidence" and subject == "contract":
        return contract if a.contractual_presence == "included_in_draft_contract" and contract else None
    return None


def recheck(conn: sqlite3.Connection, slug: str, fix_id=None, client=None, catalogue_path=None) -> dict:
    did = ledger_fixes.deal_id(conn, slug)
    vocab, catalogue_bytes = lc._load_vocabulary(catalogue_path)
    catalogue = json.loads(catalogue_bytes.decode("utf-8"))
    config_sha = lc.rules_sha256(catalogue_bytes)
    config_sha2 = integrity.config_sha256(integrity.HASH_DEFINITION, catalogue_bytes)
    integrity.ensure_schema(conn)  # before any write: it commits
    prev_review = _latest_review(conn, did)
    fix = None
    if fix_id is not None:
        fix = conn.execute("SELECT id, route, status, deal_id FROM fixes WHERE id = ?", (fix_id,)).fetchone()
        if fix is None or fix[3] != did or fix[2] != "approved":
            raise RecheckError("a recheck after a fix needs an approved fix of this deal")
    try:
        result = _recheck(conn, did, slug, prev_review, fix, client, vocab, catalogue, config_sha, config_sha2)
    except BaseException:
        conn.rollback()
        raise
    conn.commit()
    return result


def _recheck(conn, did, slug, prev_review, fix, client, vocab, catalogue, config_sha, config_sha2):
    run_kind = "recheck_after_fix" if fix else ("unchanged_input_rerun" if prev_review else "review")
    # run_kind is kept as it was written (the column only allows four values). Whether the inputs differed from the
    # previous review is recorded separately: count unchanged-input reruns by inputs_changed, never by run_kind.
    source_now, evidence_now = ledger_fixes.source_set_sha256(conn, did), ledger_fixes.decision_evidence_sha256(conn, did)
    inputs_changed, why = None, ""
    if prev_review:
        before = conn.execute("SELECT source_set_sha256, decision_evidence_sha256 FROM reviews WHERE id = ?", (prev_review,)).fetchone()
        inputs_changed = (source_now, evidence_now) != tuple(before)
        why = ("; documents changed" if source_now != before[0] else "") + (
            "; approval or fix evidence changed" if evidence_now != before[1] else "")
    review_id = conn.execute(
        "INSERT INTO reviews (deal_id, run_kind, checker, config_sha256, source_set_sha256, decision_evidence_sha256,"
        " triggered_by_fix_id, status, note) VALUES (?, ?, 'rules', ?, ?, ?, ?, 'running', ?)",
        (did, run_kind, config_sha, source_now, evidence_now, fix[0] if fix else None,
         f"recheck of review {prev_review}{why}" if prev_review else "first review"),
    ).lastrowid

    # --- Sources and extraction ---
    prev_sources = {v: (e, o) for v, e, o in conn.execute(
        "SELECT source_version_id, extraction_id, cache_outcome FROM review_sources WHERE review_id = ?", (prev_review,))
    } if prev_review else {}
    rows = conn.execute(
        "SELECT v.id, so.source_key, v.version_no, v.doc_type, v.doc_date, v.canonical_text, v.canonical_sha256"
        " FROM source_versions v JOIN sources so ON so.id = v.source_id WHERE so.deal_id = ? AND v.included = 1"
        " ORDER BY so.source_key", (did,)).fetchall()
    cost, model_calls = 0.0, 0
    for vid, key, version_no, doc_type, date, text, sha in rows:
        if doc_type not in config.EXTRACTABLE_DOC_TYPES:
            outcome, eid = "not_extracted", None
        elif vid in prev_sources and prev_sources[vid][0] is not None:
            eid, prev_outcome = prev_sources[vid]
            outcome = "imported" if prev_outcome == "imported" else "hit"
        else:
            prefix = key if version_no == 1 else f"{key}v{version_no}"
            eid, outcome, c = extraction_cache.get_or_extract(conn, client, vid, text, sha, doc_type, prefix)
            cost += c
            model_calls += outcome == "miss_called"
        conn.execute("INSERT INTO review_sources (review_id, source_version_id, extraction_id, cache_outcome)"
                     " VALUES (?, ?, ?, ?)", (review_id, vid, eid, outcome))

    statements = [
        {"statement_id": sid, "source_version_id": vid, "statement_key": skey, "quote": quote, "language": language,
         "source_key": source_key}
        for sid, vid, skey, quote, language, source_key in conn.execute(
            "SELECT s.id, rs.source_version_id, s.statement_key, s.quote, s.language, so.source_key FROM review_sources rs"
            " JOIN statements s ON s.extraction_id = rs.extraction_id JOIN source_versions v ON v.id = rs.source_version_id"
            " JOIN sources so ON so.id = v.source_id WHERE rs.review_id = ? ORDER BY so.source_key, s.ordinal",
            (review_id,))
    ]
    by_sid = {s["statement_id"]: s for s in statements}
    versions = lc._review_versions(conn, review_id)

    # --- Consolidation with identities kept ---
    plan = lc.plan_review(statements, vocab, config_sha, lc.referenced_sections(statements, versions))
    existing = dict(conn.execute("SELECT id, commitment_key FROM commitments WHERE deal_id = ?", (did,)).fetchall())
    identity = _assign_identities(plan, by_sid, _previous_members(conn, prev_review) if prev_review else {}, existing)
    next_n = len(existing)
    for o in plan["statements"]:
        conn.execute("INSERT INTO review_statements (review_id, statement_id, source_version_id, kept, filter_rule)"
                     " VALUES (?, ?, ?, ?, ?)", (review_id, o["statement_id"], o["source_version_id"], o["kept"], o["filter_rule"]))
    ids = {}
    for gi, c in enumerate(plan["commitments"]):
        cid = identity[gi]
        if cid is None:
            next_n += 1
            key = f"C{next_n:02d}"
            cid = conn.execute("INSERT INTO commitments (deal_id, commitment_key, created_review_id) VALUES (?, ?, ?)",
                               (did, key, review_id)).lastrowid
            existing[cid] = key
        c["commitment_key"] = existing[cid]
        ids[c["commitment_key"]] = cid

    chain = references.contract_chain(versions)
    info = {s["statement_key"]: {"quote": s["quote"], "language": s["language"], "source_version_id": s["source_version_id"]}
            for s in statements}
    assessments = rules.assess(plan, versions, chain, catalogue, vocab, info)
    presence_by_key = {k: a.contractual_presence for k, a in assessments.items()}

    for c in plan["commitments"]:
        cid, a = ids[c["commitment_key"]], assessments[c["commitment_key"]]
        for sid, vid in c["members"]:
            conn.execute("INSERT INTO review_statement_commitments (review_id, statement_id, source_version_id, commitment_id)"
                         " VALUES (?, ?, ?, ?)", (review_id, sid, vid, cid))
        conn.execute(
            "INSERT INTO commitment_assessments (review_id, commitment_id, name, language, authorisation,"
            " authorisation_evidence, evidence_refs, contractual_presence, presence_detail, support_state, rationale, terms)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'supported', ?, ?)",
            (review_id, cid, c["name"], c["language"], a.authorisation, a.authorisation_evidence,
             json.dumps(a.evidence_refs, sort_keys=True), a.contractual_presence, a.presence_detail, c["rationale"],
             json.dumps(c["terms"], sort_keys=True)))

    # Previous commitments with no statement left: recorded as unsupported, with what replaced their sources.
    unsupported = {}
    current_sources = {key: vid for vid, key, *_ in rows}
    for cid, key in existing.items():
        if cid in ids.values():
            continue
        prev = conn.execute("SELECT name, language FROM commitment_assessments WHERE commitment_id = ?"
                            " ORDER BY id DESC LIMIT 1", (cid,)).fetchone()
        linked = conn.execute(
            "SELECT DISTINCT l.source_version_id, so.source_key FROM review_statement_commitments l JOIN source_versions v"
            " ON v.id = l.source_version_id JOIN sources so ON so.id = v.source_id WHERE l.commitment_id = ?", (cid,)).fetchall()
        linked_versions = {v for v, _ in linked}
        linked_sources = sorted({k for _, k in linked})
        # Withdrawn only if every source that made the promise has a newer, included version without it.
        # A source that was merely excluded never closes anything.
        replaced = all(current_sources.get(k) is not None and current_sources[k] not in linked_versions
                       for k in linked_sources)
        unsupported[cid] = ([{"source_version_id": current_sources[k], "locator": "whole document", "role": "replacing_version"}
                             for k in linked_sources] if replaced and linked_sources else [])
        conn.execute(
            "INSERT INTO commitment_assessments (review_id, commitment_id, name, language, authorisation,"
            " contractual_presence, presence_detail, support_state, rationale)"
            " VALUES (?, ?, ?, ?, 'not_assessed', 'not_assessed', ?, 'unsupported', ?)",
            (review_id, cid, prev[0], prev[1], "No statement in the current documents.",
             "No statement in the current documents supports this commitment."))

    # --- Closure checks on every existing issue, then any new issues ---
    now = {}
    for c in plan["commitments"]:
        for issue in assessments[c["commitment_key"]].issues:
            now[(ids[c["commitment_key"]], issue["issue_type"], issue["subject_key"])] = issue
    fixed = {r[0] for r in conn.execute("SELECT issue_id FROM fix_issues WHERE fix_id = ?", (fix[0],))} if fix else set()
    counts = {"met": 0, "open_action": 0, "open_evidence": 0, "new": 0}
    by_cid = {ids[k]: assessments[k] for k in assessments}
    for iid, cid, itype, subject, absolute in conn.execute(
            "SELECT i.id, i.commitment_id, i.issue_type, i.subject_key, i.absolute_limit FROM issues i"
            " JOIN commitments c ON c.id = i.commitment_id WHERE c.deal_id = ? ORDER BY i.id", (did,)).fetchall():
        key = (cid, itype, subject)
        fix_for = fix[0] if iid in fixed else None
        if key in now:
            n = now.pop(key)
            outcome, evidence, unmet, reason, re_raised = (n["raised"]["outcome"], n["raised"]["evidence_checked"],
                                                           n["raised"]["unmet"], "Still found by this recheck. " + n["raised"]["reason"], 1)
        else:
            ev = _closing_evidence({"issue_type": itype, "subject_key": subject}, by_cid.get(cid), cid in unsupported,
                                   by_cid, presence_by_key, unsupported.get(cid))
            blocked = absolute and fix is not None and fix[1] == "allowed_exception" and fix_for is not None
            if ev and not blocked:
                outcome, evidence, unmet, re_raised = "met", ev, None, 0
                reason = ("Closed: the promise is no longer in the current documents, and newer versions replace every "
                          "source that made it." if cid in unsupported else
                          "Closed: this recheck no longer finds the issue, and the evidence below meets its closure criteria.")
            else:
                outcome = "open_evidence" if itype == "insufficient_evidence" else "open_action"
                evidence, unmet, re_raised = [], ["closure criteria not shown by any current evidence"], 0
                reason = "Not raised by this recheck, but nothing yet shows its closure criteria are met; it stays open."
        conn.execute(
            "INSERT INTO closure_checks (issue_id, review_id, check_kind, outcome, evidence_checked, reason, unmet,"
            " re_raised, fix_id) VALUES (?, ?, 'recheck', ?, ?, ?, ?, ?, ?)",
            (iid, review_id, outcome, json.dumps(evidence, sort_keys=True), reason,
             None if unmet is None else json.dumps(unmet), re_raised, fix_for))
        counts[outcome] += 1
    for (cid, itype, subject), issue in now.items():
        iid = conn.execute(
            "INSERT INTO issues (commitment_id, issue_type, subject_key, owner_function, raised_review_id, raised_by,"
            " raised_config_sha256, closure_criteria, criteria_version, absolute_limit)"
            " VALUES (?, ?, ?, ?, ?, 'rules', ?, ?, ?, ?)",
            (cid, itype, subject, issue["owner_function"], review_id, config_sha,
             json.dumps(issue["closure_criteria"], sort_keys=True), rules.CRITERIA_VERSION, issue["absolute_limit"])).lastrowid
        r = issue["raised"]
        conn.execute("INSERT INTO closure_checks (issue_id, review_id, check_kind, outcome, evidence_checked, reason, unmet,"
                     " re_raised) VALUES (?, ?, 'raised', ?, ?, ?, ?, 1)",
                     (iid, review_id, r["outcome"], json.dumps(r["evidence_checked"], sort_keys=True), r["reason"],
                      json.dumps(r["unmet"])))
        counts["new"] += 1

    for c in plan["commitments"]:
        for from_key, to_key, link_type, basis in assessments[c["commitment_key"]].links:
            conn.execute("INSERT INTO commitment_links (review_id, from_commitment_id, to_commitment_id, link_type, basis)"
                         " VALUES (?, ?, ?, ?, ?)", (review_id, ids[from_key], ids[to_key], link_type, basis))
    source_ids = dict(conn.execute("SELECT source_key, id FROM sources WHERE deal_id = ?", (did,)).fetchall())
    for r in chain.resolutions:
        conn.execute(
            "INSERT INTO reference_resolutions (review_id, from_version_id, from_locator, target_source_id, target_locator,"
            " cited_label, cited_date, resolved_version_id, status, reason) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (review_id, r.from_version_id, r.from_locator, source_ids.get(r.target_source_key) if r.target_source_key else None,
             r.target_locator, r.cited_label, r.cited_date, r.resolved_version_id, r.status, r.reason))
    integrity.write_review_binding(conn, review_id, config_sha2, inputs_changed)
    conn.execute("UPDATE reviews SET status = 'complete', cost_usd = ?, finished_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')"
                 " WHERE id = ?", (round(cost, 6), review_id))
    return {"review_id": review_id, "run_kind": run_kind, "inputs_changed": bool(inputs_changed), "model_calls": model_calls, "cost_usd": round(cost, 6),
            "checks": counts, "unsupported": sorted(existing[c] for c in unsupported)}


def status_by_name(conn, slug: str) -> dict:
    """{commitment name: (status, {issue_type/subject: state})} from the latest assessment of each commitment."""
    did = ledger_fixes.deal_id(conn, slug)
    out = {}
    for cid, status in conn.execute("SELECT s.commitment_id, s.status FROM commitment_status s JOIN commitments c"
                                    " ON c.id = s.commitment_id WHERE c.deal_id = ?", (did,)):
        name = conn.execute("SELECT name FROM commitment_assessments WHERE commitment_id = ? AND support_state = 'supported'"
                            " ORDER BY id DESC LIMIT 1", (cid,)).fetchone()
        name = name[0] if name else conn.execute("SELECT name FROM commitment_assessments WHERE commitment_id = ?"
                                                 " ORDER BY id DESC LIMIT 1", (cid,)).fetchone()[0]
        issues = {f"{t}/{s}": st for t, s, st in conn.execute(
            "SELECT i.issue_type, i.subject_key, v.state FROM issues i JOIN issue_current_state v ON v.issue_id = i.id"
            " WHERE i.commitment_id = ?", (cid,))}
        out[name] = (status, issues)
    return out
