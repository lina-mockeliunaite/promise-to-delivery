"""v2 in the app (Stage 2, 10 Oct 2026): model-proposed, code-verified findings written into the existing ledger.

A v2 review, in order:
1. The current documents of the deal (latest included version of each source).
2. Model findings for exactly those documents: from the file cache (keyed by a fingerprint of documents, catalogue,
   prompt, schema, model and v2 version), from saved frozen output (the demo seed, first review only), or one model call.
   A recheck whose only new documents are internal pricing notes makes no model call: a note cannot create a promise,
   so the previous review's findings are verified again against the new evidence.
3. Code verifies every finding (detect_v2.verify). Rejected findings are kept in v2_detections, never shown.
4. Every existing open issue is checked again by re-verifying the claim stored when it was raised. A claim that still
   holds keeps the issue open; a claim that no longer holds closes it, with the verifier's reason and the documents it
   read as evidence. No model is involved in closing anything. An absolute limit never closes through an exception.
5. Verified findings with no existing issue raise new ones; one that matches a resolved issue re-opens it.
6. Promises are grouped into commitments by their quotes; each commitment's quotes are stored as statements so the
   screens show them with their source, and a commitment whose quotes left the documents reads 'Not in current documents'.

Writes only through the existing ledger tables plus v2_detections. Decisions, accountable people and the handoff hang
off the issues and work unchanged.
"""

import hashlib
import json
import re
from pathlib import Path

import config
import detect_v2
import extraction_cache
import integrity
import ledger_fixes
import ledger_import
import score_v2

HERE = Path(__file__).resolve().parent
SCHEMA_PATH = HERE / "v2_schema.sql"
INTERNAL_ONLY = set(detect_v2.INTERNAL_TYPES)
ISSUE_TYPE = {"approval_required": "approval", "absolute_limit": "approval", "over_limit": "approval",
              "contract_gap": "contract_gap", "conflicting_terms": "conflicting_terms"}
OWNER = {"approval": "Product", "contract_gap": "Commercial", "conflicting_terms": "Commercial"}
CRITERIA_VERSION = 2


class NeedsModel(extraction_cache.ExtractionFailed):
    """The documents changed in a way that needs the model, and there is no client."""


class DetectionFailed(extraction_cache.ExtractionFailed):
    """The model reply could not be used (cut off or unparseable). Nothing was written."""


def ensure_schema(conn) -> None:
    if conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'v2_detections_append_only_d'").fetchone():
        return
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()


# --- Inputs ---------------------------------------------------------------------------------------------------------
def current_docs(conn, did: int) -> list:
    """[{source_id, doc_type, date, text, version_id}] for the latest included version of every source."""
    return [{"source_id": k, "doc_type": t, "date": d or "", "text": x, "version_id": v} for k, t, d, x, v in conn.execute(
        "SELECT s.source_key, v.doc_type, v.doc_date, v.canonical_text, v.id FROM sources s JOIN source_versions v"
        " ON v.source_id = s.id WHERE s.deal_id = ? AND v.included = 1 AND v.version_no ="
        " (SELECT MAX(version_no) FROM source_versions WHERE source_id = s.id AND included = 1)"
        " ORDER BY v.doc_date, s.source_key", (did,))]


def _sha(text) -> str:
    return hashlib.sha256(text.encode("utf-8") if isinstance(text, str) else text).hexdigest()


def input_sha256(docs: list, catalogue_raw: bytes, model: str) -> str:
    fingerprint = {
        "v2_version": detect_v2.V2_VERSION, "model": model, "prompt": _sha(detect_v2.SYSTEM_PROMPT),
        "schema": _sha(json.dumps(detect_v2.OUTPUT_FORMAT, sort_keys=True)),
        "catalogue": _sha(integrity.canonical_catalogue(catalogue_raw)),
        "docs": sorted([d["source_id"], d["doc_type"], d["date"], _sha(d["text"])] for d in docs)}
    return _sha(json.dumps(fingerprint, sort_keys=True))


def _cache_path(sha: str) -> Path:
    return Path(config.V2_CACHE_DIR) / f"{sha}.json"


def _seed(slug: str):
    name = config.V2_SEED_FILES.get(slug)
    if not name:
        return None
    path = Path(config.RESULTS_DIR) / name
    if not path.is_file():
        return None
    saved = json.loads(path.read_text(encoding="utf-8"))
    if saved.get("v2_version") != detect_v2.V2_VERSION:
        return None
    for d in saved.get("deals", []):
        if d.get("deal") == slug and not d.get("parse_error"):
            return {"findings": d["findings"], "cost_usd": 0.0, "origin": "seed", "seed_file": name}
    return None


def detection(slug: str, docs: list, catalogue: dict, catalogue_raw: bytes, client, allow_seed: bool) -> dict:
    """{'findings', 'origin', 'input_sha256', 'cost_usd'}: cache, then seed (first review only), then one model call."""
    model = config.EXTRACTION_MODEL
    sha = input_sha256(docs, catalogue_raw, model)
    path = _cache_path(sha)
    if path.is_file():
        cached = json.loads(path.read_text(encoding="utf-8"))
        return {"findings": cached["findings"], "origin": "cache", "input_sha256": sha, "cost_usd": 0.0}
    found = _seed(slug) if allow_seed else None
    if found is None:
        if client is None:
            raise NeedsModel("these documents have not been read by the model yet")
        out = detect_v2.call_model(client, docs, catalogue, model)
        if out.get("parse_error") or out.get("stop_reason") != "end_turn":
            raise DetectionFailed(out.get("parse_error") or f"model reply stopped with {out.get('stop_reason')}")
        found = {"findings": out["findings"], "cost_usd": out.get("cost_usd") or 0.0, "origin": "model_call",
                 "usage": out.get("usage")}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"input_sha256": sha, "deal": slug, "v2_version": detect_v2.V2_VERSION, "model": model,
                                **found}, indent=2, ensure_ascii=False), encoding="utf-8")
    return {**found, "input_sha256": sha}


# --- Grouping -------------------------------------------------------------------------------------------------------
def _quotes(finding) -> list:
    return [{"source_id": q["source_id"], "quote": q["quote"]} for q in finding.get("promise_quotes") or []]


def _overlap(a: list, b: list) -> bool:
    return any(x["source_id"] == y["source_id"] and score_v2.quotes_match(x["quote"], y["quote"]) for x in a for y in b)


def group(findings: list) -> list:
    """Clusters of findings about the same promise (any shared quote), in first-seen order."""
    clusters = []
    for f in findings:
        hits = [c for c in clusters if _overlap(_quotes(f), c["quotes"])]
        merged = {"findings": [f], "quotes": _quotes(f)}
        for c in hits:
            merged["findings"] = c["findings"] + merged["findings"]
            merged["quotes"] = c["quotes"] + merged["quotes"]
            clusters.remove(c)
        clusters.append(merged)
    for c in clusters:
        seen, uniq = set(), []
        for q in c["quotes"]:
            k = (q["source_id"], detect_v2._n(q["quote"]))
            if k not in seen:
                seen.add(k)
                uniq.append(q)
        c["quotes"] = uniq
    return clusters


def subject_key(f: dict) -> str:
    kind = f["kind"]
    if kind == "approval_required":
        return f"approval:{f.get('catalogue_path')}"
    if kind == "absolute_limit":
        return f"absolute:{f.get('catalogue_path')}:{detect_v2._n(f.get('unlisted_value') or '')}"
    if kind == "over_limit":
        return f"limit:{f.get('catalogue_path')}:{f.get('limit_name')}"
    if kind == "contract_gap":
        return "contract"
    return "contract_terms"


def _terms_summary(findings: list, catalogue: dict = None) -> tuple:
    """(told, contract) short terms for the overview row."""
    told = contract = None
    for f in findings:
        k = f["kind"]
        if k == "conflicting_terms":
            return f.get("promised_value"), f.get("contract_value")
        if k == "over_limit" and f.get("promised_quantity") and not told:
            told = f"{f['promised_quantity']:,}" + ("/day" if "per_day" in (f.get("limit_name") or "") else "")
        elif k == "absolute_limit" and not told:
            parts = (f.get("catalogue_path") or "").split("/")
            value = f.get("unlisted_value") or ""
            if value and value != (parts[1] if len(parts) > 1 else None):
                told = value
            else:  # the whole region is missing: name the capability and the region
                cap = detect_v2._capability(catalogue or {}, parts[0]) if parts else None
                told = f"{cap['name'] if cap else parts[0]} in {parts[1] if len(parts) > 1 else '?'}"
        elif k == "contract_gap":
            contract = "Not included"
            if not told and f.get("missing_phrases"):
                told = f["missing_phrases"][0]
        elif k == "approval_required" and not told:
            parts = (f.get("catalogue_path") or "").split("/")[2:]
            told = " ".join(p.replace("_", "-") for p in parts if p != "NUSD") or None
    return told, contract


# --- Closure --------------------------------------------------------------------------------------------------------
def closing_reason(problem: str, labels: dict) -> str:
    """The verifier's reason a stored claim no longer holds, as a sentence for the reader."""
    m = re.match(r"the pricing note records an approval: (.*)", problem)
    if m:
        cells = [c.strip() for c in m.group(1).strip().strip("|").split("|") if c.strip()]
        approval = next((c for c in reversed(cells) if "approved by" in c.lower()), cells[-1] if cells else m.group(1))
        return f"Closed: the pricing note now records an approval with a named approver: “{approval}”."
    m = re.match(r"'(.+)' appears in the contract chain", problem)
    if m:
        return f"Closed: the contract documents now include “{m.group(1)}”."
    m = re.match(r"quote not verbatim in (\S+)", problem)
    if m:
        return f"Closed: the promise is no longer in the current version of {labels.get(m.group(1), m.group(1))}."
    m = re.match(r"contract quote not verbatim in (\S+)", problem)
    if m:
        return f"Closed: the contract clause behind this conflict is no longer in {labels.get(m.group(1), m.group(1))}."
    m = re.match(r"'(.+)' also appears in the contract quote", problem)
    if m:
        return f"Closed: the contract now says “{m.group(1)}”, as promised."
    return "Closed: the original finding no longer holds against the current documents (" + problem + ")."


def _evidence(claim: dict, docs: list, problem: str = "") -> list:
    """The current documents behind a closure: the pricing notes when an approval is now recorded, the contract chain
    when the contract changed, the promise's own sources when the promise changed; for anything else, all three."""
    keys = {q["source_id"] for q in claim.get("promise_quotes") or []}
    if problem.startswith("the pricing note records an approval"):
        chosen = [d for d in docs if d["doc_type"] in detect_v2.INTERNAL_TYPES]
    elif "contract" in problem:
        chosen = [d for d in docs if d["doc_type"] in detect_v2.CONTRACT_TYPES]
    elif problem.startswith("quote not verbatim"):
        chosen = [d for d in docs if d["source_id"] in keys]
    else:
        chosen = [d for d in docs if d["source_id"] in keys or d["doc_type"] in detect_v2.INTERNAL_TYPES + detect_v2.CONTRACT_TYPES]
    return [{"source_version_id": d["version_id"]} for d in (chosen or docs)]


def _reason_open(f: dict, still: bool) -> str:
    lead = "Still holds on the current documents. " if still else ""
    return lead + (f.get("reason") or "").strip()


def _checked_line(f: dict) -> str:
    """What the code confirmed, in one line, kept as the check's 'unmet' entry."""
    k = f["kind"]
    if k == "approval_required":
        return f"Catalogue {f['catalogue_path']} needs a named approval; no approval with a named approver is recorded."
    if k == "absolute_limit":
        v = f.get("unlisted_value")
        return f"Not in the catalogue for {f['catalogue_path']}" + (f": {v}." if v else ".") + " It cannot be sold under an exception."
    if k == "over_limit":
        return f"Promised {f['promised_quantity']:,}; catalogue limit {f['limit_name']} for {f['catalogue_path']} is lower; no approval recorded."
    if k == "contract_gap":
        return "Not found anywhere in the contract or SOW: " + "; ".join(f"“{p}”" for p in f.get("missing_phrases") or []) + "."
    return f"Promised “{f.get('promised_value')}”; the contract says “{f.get('contract_value')}”."


def needs_model(conn, slug: str, source_key, doc_type: str, canonical_text: str, catalogue_path=None) -> bool:
    """True if adding this document (or this new version of source_key) would need a model call that no cache answers."""
    if doc_type in INTERNAL_ONLY:
        return False
    did = ledger_fixes.deal_id(conn, slug)
    docs = [d for d in current_docs(conn, did) if d["source_id"] != source_key]
    docs.append({"source_id": source_key or "new", "doc_type": doc_type, "date": "", "text": canonical_text, "version_id": None})
    raw = Path(catalogue_path or config.DATA_DIR / "catalogue.json").read_bytes()
    return not _cache_path(input_sha256(docs, raw, config.EXTRACTION_MODEL)).is_file()


def is_v2(conn, did: int) -> bool:
    return conn.execute("SELECT 1 FROM reviews WHERE deal_id = ? AND checker = 'model_v2' LIMIT 1", (did,)).fetchone() is not None


# --- The review -----------------------------------------------------------------------------------------------------
def _previous_review(conn, did: int):
    return conn.execute("SELECT r.id FROM reviews r JOIN v2_detections d ON d.review_id = r.id WHERE r.deal_id = ?"
                        " AND r.status = 'complete' ORDER BY r.id DESC LIMIT 1", (did,)).fetchone()


def _needs_detection(conn, prev_id, docs: list) -> bool:
    if prev_id is None:
        return True
    before = {v for (v,) in conn.execute("SELECT source_version_id FROM review_sources WHERE review_id = ?", (prev_id,))}
    changed = [d for d in docs if d["version_id"] not in before]
    removed = before - {d["version_id"] for d in docs}
    removed_types = {t for (t,) in conn.execute(
        f"SELECT doc_type FROM source_versions WHERE id IN ({','.join('?' * len(removed))})", tuple(removed))} if removed else set()
    return bool(removed_types - INTERNAL_ONLY) or any(d["doc_type"] not in INTERNAL_ONLY for d in changed)


def review(conn, slug: str, client=None, fix_id=None, catalogue_path=None) -> dict:
    """One v2 review of the deal (a first review, an unchanged rerun, or a recheck after a fix). Commits on success."""
    did = ledger_fixes.deal_id(conn, slug)
    integrity.ensure_schema(conn)
    ensure_schema(conn)
    catalogue_raw = Path(catalogue_path or config.DATA_DIR / "catalogue.json").read_bytes()
    catalogue = json.loads(catalogue_raw.decode("utf-8"))
    fix = None
    if fix_id is not None:
        fix = conn.execute("SELECT id, route, status, deal_id FROM fixes WHERE id = ?", (fix_id,)).fetchone()
        if fix is None or fix[3] != did or fix[2] != "approved":
            raise ValueError("a recheck after a fix needs an approved fix of this deal")
    docs = current_docs(conn, did)
    prev = _previous_review(conn, did)
    prev_id = prev[0] if prev else None
    if _needs_detection(conn, prev_id, docs):
        det = detection(slug, docs, catalogue, catalogue_raw, client, allow_seed=prev_id is None)
    else:
        row = conn.execute("SELECT findings_json, input_sha256 FROM v2_detections WHERE review_id = ?", (prev_id,)).fetchone()
        det = {"findings": json.loads(row[0]), "origin": "previous_review", "input_sha256": row[1], "cost_usd": 0.0}
    try:
        result = _write(conn, did, slug, docs, catalogue, catalogue_raw, det, prev_id, fix)
    except BaseException:
        conn.rollback()
        raise
    conn.commit()
    return result


def _write(conn, did, slug, docs, catalogue, catalogue_raw, det, prev_id, fix) -> dict:
    labels = {d["source_id"]: d["source_id"] for d in docs}
    labels.update(dict(conn.execute("SELECT source_key, display_name FROM sources WHERE deal_id = ?", (did,)).fetchall()))
    accepted, rejected = [], []
    for f in det["findings"]:
        f = {k: v for k, v in f.items() if k != "problems"}
        problems = detect_v2.verify(f, docs, catalogue)
        (rejected if problems else accepted).append({**f, "problems": problems} if problems else f)

    source_now, evidence_now = ledger_fixes.source_set_sha256(conn, did), ledger_fixes.decision_evidence_sha256(conn, did)
    inputs_changed = None
    if prev_id is not None:
        before = conn.execute("SELECT source_set_sha256, decision_evidence_sha256 FROM reviews WHERE id = ?", (prev_id,)).fetchone()
        inputs_changed = (before[0], before[1]) != (source_now, evidence_now)
    run_kind = "recheck_after_fix" if fix else ("unchanged_input_rerun" if prev_id else "review")
    config_sha = integrity.config_sha256(integrity.HASH_DEFINITION, catalogue_raw)
    rid = conn.execute(
        "INSERT INTO reviews (deal_id, run_kind, checker, config_sha256, source_set_sha256, decision_evidence_sha256,"
        " triggered_by_fix_id, status, cost_usd, note) VALUES (?, ?, 'model_v2', ?, ?, ?, ?, 'running', ?, ?)",
        (did, run_kind, config_sha, source_now, evidence_now, fix[0] if fix else None, det.get("cost_usd") or 0.0,
         f"v2 review; findings from {det['origin']}")).lastrowid
    conn.execute("INSERT INTO v2_detections (review_id, input_sha256, origin, v2_version, findings_json, accepted_json,"
                 " rejected_json, cost_usd) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                 (rid, det["input_sha256"], det["origin"], detect_v2.V2_VERSION, json.dumps(det["findings"], ensure_ascii=False),
                  json.dumps(accepted, ensure_ascii=False), json.dumps(rejected, ensure_ascii=False), det.get("cost_usd") or 0.0))

    # Commitments: existing ones (with their stored quotes) and this review's clusters.
    existing = []
    for cid, key in conn.execute("SELECT id, commitment_key FROM commitments WHERE deal_id = ? ORDER BY id", (did,)).fetchall():
        row = conn.execute("SELECT name, terms FROM commitment_assessments WHERE commitment_id = ? ORDER BY id DESC LIMIT 1",
                           (cid,)).fetchone()
        terms = json.loads(row[1]) if row and row[1] else {}
        existing.append({"id": cid, "key": key, "name": row[0] if row else key, "quotes": terms.get("quotes", []),
                         "findings": []})
    for cl in group(accepted):
        match = next((e for e in existing if _overlap(cl["quotes"], e["quotes"])), None)
        if match is None:
            first = cl["quotes"][0]
            key = "v2-" + _sha(first["source_id"] + "\n" + detect_v2._n(first["quote"]))[:16]
            n = 2
            while any(e["key"] == key for e in existing):
                key = key.split("~")[0] + f"~{n}"
                n += 1
            name = next((f["commitment"] for f in cl["findings"] if f["kind"] != "contract_gap"), cl["findings"][0]["commitment"])
            cid = conn.execute("INSERT INTO commitments (deal_id, commitment_key, created_review_id) VALUES (?, ?, ?)",
                               (did, key, rid)).lastrowid
            match = {"id": cid, "key": key, "name": name, "quotes": [], "findings": []}
            existing.append(match)
        for q in cl["quotes"]:
            if not any(q["source_id"] == x["source_id"] and detect_v2._n(q["quote"]) == detect_v2._n(x["quote"]) for x in match["quotes"]):
                match["quotes"].append(q)
        match["findings"].extend(cl["findings"])

    # Statements: every quote of every commitment that is word for word in a current document.
    by_key = {d["source_id"]: d for d in docs}
    per_version = {}
    for c in existing:
        c["present"] = [q for q in c["quotes"] if q["source_id"] in by_key and detect_v2._contains(by_key[q["source_id"]]["text"], q["quote"])]
        for q in c["present"]:
            per_version.setdefault(by_key[q["source_id"]]["version_id"], []).append((c["id"], q["quote"]))
    for d in docs:
        items = per_version.get(d["version_id"])
        if not items:
            conn.execute("INSERT INTO review_sources (review_id, source_version_id, extraction_id, cache_outcome)"
                         " VALUES (?, ?, NULL, 'not_extracted')", (rid, d["version_id"]))
            continue
        quotes = list(dict.fromkeys(q for _, q in items))
        eid = conn.execute(
            "INSERT INTO extraction_cache (doc_type, model_id, output_json, cost_usd, origin, source_run_file, reusable)"
            " VALUES (?, ?, ?, 0.0, 'model_call', ?, 0)",
            (d["doc_type"], config.EXTRACTION_MODEL, json.dumps({"v2_review": rid, "quotes": quotes}, ensure_ascii=False),
             f"v2_detections:{rid}")).lastrowid
        conn.execute("INSERT INTO review_sources (review_id, source_version_id, extraction_id, cache_outcome)"
                     " VALUES (?, ?, ?, ?)", (rid, d["version_id"], eid, "hit" if det["origin"] != "model_call" else "miss_called"))
        sids = {}
        for n, q in enumerate(quotes, start=1):
            sids[q] = conn.execute("INSERT INTO statements (extraction_id, ordinal, statement_key, quote, language)"
                                   " VALUES (?, ?, ?, ?, 'firm')", (eid, n, f"v2-{rid}-{n}", q)).lastrowid
            conn.execute("INSERT INTO review_statements (review_id, statement_id, source_version_id, kept) VALUES (?, ?, ?, 1)",
                         (rid, sids[q], d["version_id"]))
        for cid, q in dict.fromkeys(items):
            conn.execute("INSERT OR IGNORE INTO review_statement_commitments (review_id, statement_id, source_version_id,"
                         " commitment_id) VALUES (?, ?, ?, ?)", (rid, sids[q], d["version_id"], cid))

    # Issues: re-verify every existing claim; raise or re-open from this review's findings.
    now = {}
    for c in existing:
        for f in c["findings"]:
            now.setdefault((c["id"], ISSUE_TYPE[f["kind"]], subject_key(f)), f)
    fixed = {r[0] for r in conn.execute("SELECT issue_id FROM fix_issues WHERE fix_id = ?", (fix[0],))} if fix else set()
    counts = {"met": 0, "open_action": 0, "new": 0, "reopened": 0}
    for iid, cid, itype, subject, absolute, criteria_json in conn.execute(
            "SELECT i.id, i.commitment_id, i.issue_type, i.subject_key, i.absolute_limit, i.closure_criteria FROM issues i"
            " JOIN commitments c ON c.id = i.commitment_id WHERE c.deal_id = ? ORDER BY i.id", (did,)).fetchall():
        state = conn.execute("SELECT state FROM issue_current_state WHERE issue_id = ?", (iid,)).fetchone()[0]
        claim = json.loads(criteria_json).get("claim")
        fresh = now.pop((cid, itype, subject), None)
        fix_for = fix[0] if fix and iid in fixed else None
        if state == "Resolved":
            if fresh is None:
                continue
            outcome, ev, unmet, reason, re_raised = ("open_action", [], [_checked_line(fresh)],
                                                     "Raised again by this review. " + _reason_open(fresh, False), 1)
            counts["reopened"] += 1
        else:
            problems = detect_v2.verify(claim, docs, catalogue) if claim else ["no stored claim"]
            blocked = absolute and fix is not None and fix[1] == "allowed_exception" and fix_for is not None
            if problems and not blocked and fresh is None:
                outcome, ev, unmet, re_raised = "met", _evidence(claim, docs, problems[0]), None, 0
                reason = closing_reason(problems[0], labels)
                counts["met"] += 1
            else:
                live = claim if not problems else fresh
                outcome, ev, unmet, re_raised = "open_action", [], [_checked_line(live)], 1 if fresh else 0
                reason = _reason_open(live, True)
                counts["open_action"] += 1
        conn.execute("INSERT INTO closure_checks (issue_id, review_id, check_kind, outcome, evidence_checked, reason, unmet,"
                     " re_raised, fix_id) VALUES (?, ?, 'recheck', ?, ?, ?, ?, ?, ?)",
                     (iid, rid, outcome, json.dumps(ev, sort_keys=True), reason, None if unmet is None else json.dumps(unmet),
                      re_raised, fix_for if outcome == "met" else None))
    for (cid, itype, subject), f in now.items():
        criteria = {"v2": 1, "kind": f["kind"], "claim": f}
        iid = conn.execute(
            "INSERT INTO issues (commitment_id, issue_type, subject_key, owner_function, raised_review_id, raised_by,"
            " raised_config_sha256, closure_criteria, criteria_version, absolute_limit)"
            " VALUES (?, ?, ?, ?, ?, 'model_v2', ?, ?, ?, ?)",
            (cid, itype, subject, OWNER[itype], rid, config_sha, json.dumps(criteria, sort_keys=True, ensure_ascii=False),
             CRITERIA_VERSION, 1 if f["kind"] == "absolute_limit" else 0)).lastrowid
        conn.execute("INSERT INTO closure_checks (issue_id, review_id, check_kind, outcome, evidence_checked, reason, unmet,"
                     " re_raised) VALUES (?, ?, 'raised', 'open_action', '[]', ?, ?, 0)",
                     (iid, rid, _reason_open(f, False), json.dumps([_checked_line(f)])))
        counts["new"] += 1

    # Assessments: one per commitment per review.
    for c in existing:
        open_kinds = {f["kind"] for f in c["findings"]}
        told, contract = _terms_summary(c["findings"], catalogue) if c["findings"] else (None, None)
        prev_terms = conn.execute("SELECT terms FROM commitment_assessments WHERE commitment_id = ? ORDER BY id DESC LIMIT 1",
                                  (c["id"],)).fetchone()
        prev_terms = json.loads(prev_terms[0]) if prev_terms and prev_terms[0] else {}
        terms = {"v2": 1, "key": c["key"], "quotes": c["quotes"],
                 "told": told or prev_terms.get("told"), "contract": contract,
                 "members": [{"term_set": {"kind": f["kind"], "subject": subject_key(f)}} for f in c["findings"]]}
        approval = next((f for f in c["findings"] if ISSUE_TYPE[f["kind"]] == "approval"), None)
        gap = next((f for f in c["findings"] if f["kind"] in ("contract_gap", "conflicting_terms")), None)
        conn.execute(
            "INSERT INTO commitment_assessments (review_id, commitment_id, name, language, authorisation, authorisation_evidence,"
            " evidence_refs, contractual_presence, presence_detail, support_state, rationale, terms)"
            " VALUES (?, ?, ?, 'firm', ?, ?, ?, ?, ?, ?, ?, ?)",
            (rid, c["id"], c["name"], "no_approval_evidence" if approval else "not_assessed",
             _checked_line(approval) if approval else None,
             json.dumps({"catalogue": [approval["catalogue_path"]]} if approval and approval.get("catalogue_path") else {}),
             "absent" if gap else "not_assessed", _checked_line(gap) if gap else None,
             "supported" if c["present"] else "unsupported",
             "; ".join(sorted(open_kinds)) or None, json.dumps(terms, sort_keys=True, ensure_ascii=False)))

    integrity.write_review_binding(conn, rid, config_sha, inputs_changed)
    conn.execute("UPDATE reviews SET status = 'complete', finished_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = ?", (rid,))
    return {"review_id": rid, "run_kind": run_kind, "inputs_changed": bool(inputs_changed), "origin": det["origin"], "model_calls": 1 if det["origin"] == "model_call" else 0,
            "cost_usd": det.get("cost_usd") or 0.0, "accepted": len(accepted), "rejected": len(rejected), "checks": counts}


# --- Building the app's ledger --------------------------------------------------------------------------------------
def import_deal(conn, slug: str) -> int:
    """Create a v2 deal with version 1 of each of its documents, as ledger_import does. No review yet."""
    if slug not in config.V2_DEALS:
        raise ValueError(f"{slug} is not a v2 deal")
    manifest = json.loads(config.doc_path(slug, "manifest.json").read_text(encoding="utf-8"))
    did = conn.execute("INSERT INTO deals (slug, kind, display_name) VALUES (?, 'development', ?)", (slug, slug)).lastrowid
    for entry in manifest["documents"]:
        raw = config.doc_path(slug, entry["file"]).read_bytes()
        d = ledger_import.markdown_adapter(raw)
        sid = conn.execute("INSERT INTO sources (deal_id, source_key, display_name) VALUES (?, ?, ?)",
                           (did, entry["source_id"], entry["file"])).lastrowid
        conn.execute("INSERT INTO source_versions (source_id, version_no, original_sha256, canonical_sha256, adapter_name,"
                     " adapter_version, doc_type, doc_date, original_filename, canonical_text, location_map)"
                     " VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     (sid, ledger_import.sha256_hex(raw), ledger_import.sha256_hex(d["canonical_text"]), d["adapter_name"],
                      d["adapter_version"], entry["doc_type"], entry["date"], entry["file"], d["canonical_text"], d["location_map"]))
    return did


def build(db_path, client=None) -> dict:
    """A fresh ledger holding every V2_DEALS deal, each with a first v2 review (seeded: no model call if seeds exist)."""
    import ledger
    conn = ledger.open_ledger(db_path)
    try:
        out = {}
        for slug in config.V2_DEALS:
            import_deal(conn, slug)
            conn.commit()
            out[slug] = review(conn, slug, client)
        return out
    finally:
        conn.close()
