"""Make the model readings the Alder documents need, show them for checking, and store them only when you say so. (Round 5, 12-13 Nov; Round 5c, 13 Nov.)

Round 5c: the revised statement of work's heading and the signed appendix's bold lead are renamed ("## 5. Fraud warnings during payment"), so the signed check's closing wording is the full
sentence and not a heading fragment. Those two files are staged in data/staged_alder/scenarios/ until the reading is accepted; while that folder exists every mode reads the scenario files from it
(the script says so), so the key is the one the app will compute after they go live. AB-06 is part of the K1 key, so K1 needs one new reading; K0 (the base documents) is unchanged and is
reused from results/v2_cache with no model call.

The detection cache is keyed by every current document's text and by the catalogue, so two
Alder states need one fresh reading each:
  K0  the base documents AB-01 .. AB-08 (Reset, the first load, the hourly reset)
  K1  the base documents with AB-05 and AB-06 added as the demo's sample files (AB-05 alone, and AB-09, are internal or signed paperwork: no model)
Nothing is changed in the prompt or the engine: this runs the app's own code (the same review, the same add-and-check route, the same cache-key guard) on a scratch ledger,
with a scratch cache, against the live Alder documents (data/alder_bank/docs, data/scenarios) and the Alder catalogue (data/catalogue_alder.json, through Alder's profile). Your ledger and
results/v2_cache are not touched until --accept. (It was first run against staged copies of these files; they went live on 13 Nov, after --accept. Run it again, with --fresh, only if a document or the
catalogue changes: the keys change with them. The accepted readings are in results/v2_cache.)

  python fill_alder_readings.py --selftest        no key, no model call: the whole story is run on canned readings, to check the documents, the catalogue and this script
  ANTHROPIC_API_KEY=... python fill_alder_readings.py      the real run: two model calls (about $0.11 each), then the report; candidates are kept in scratch_alder_candidates/
  python fill_alder_readings.py --accept          no key, no call: re-checks the kept candidates offline and, only if the report is READY, copies the two files to results/v2_cache
  (--fresh with the real run deletes kept candidates first.)

The key is read only from ANTHROPIC_API_KEY, in presence-only form: it is never printed, logged or written. The report ends with READY (safe to --accept) or NOT SAFE with the reasons.
READY means: every proposed finding is one of the four expected (scam-call alerts: approval_required and contract_gap; hosting: absolute_limit and conflicting_terms), nothing about
volume or scoring thresholds or anything else was proposed, no proposed missing phrase already appears in a base contract-chain document, no real company name appears in a reading, the contract gap closes when the revised statement of work is added, the approval
gap stays open (starts later, by the promise, then the contract, then the signed document), the signed contract confirms the contract fix, and the locked record has one gap needing
attention (scam-call alerts) and one addressed by note (hosting)."""

import argparse
import contextlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import config  # noqa: E402

DEAL = "alder_bank"
DOCS_DIR = config.DATA_DIR / "alder_bank" / "docs"
SCEN_LIVE = config.DATA_DIR / "scenarios"
SCEN_STAGED = ROOT / "data" / "staged_alder" / "scenarios"
CANDIDATES = ROOT / "scratch_alder_candidates"
REAL_CACHE = ROOT / "results" / "v2_cache"
H = {"X-Requested-With": "deal-workspace"}
ALLOWED = {("scam-call alerts", "approval_required"), ("scam-call alerts", "contract_gap"), ("hosting", "absolute_limit"), ("hosting", "conflicting_terms")}
FORBIDDEN_NAMES = ("biocatch",)
SCAM, HOSTING = "scam-call alerts", "hosting"
TITLES = {SCAM: "Scam-call alerts live at launch", HOSTING: "Hosting on Microsoft Azure"}


class NotReady(Exception):
    pass


def scen_dir() -> Path:
    """Where the sample files are read from: the staged copies while they exist (Round 5c), else the live ones."""
    return SCEN_STAGED if SCEN_STAGED.is_dir() else SCEN_LIVE


def staged(kind: str, name: str) -> str:
    """The text of an Alder document ("docs": the base documents; "scenarios": the three sample files, staged or live)."""
    return ((DOCS_DIR if kind == "docs" else scen_dir()) / name).read_text(encoding="utf-8")


def closing_sentence() -> str:
    """The one sentence the revised statement of work and the signed appendix share, read from the sample files."""
    line = next(l.strip() for l in staged("scenarios", "AB-06_v2_coaching_added.md").splitlines() if "will be live from the 1 February 2027 launch" in l)
    if staged("scenarios", "AB-09_signed_contract.md").count(line) != 1:
        raise NotReady("the signed appendix does not carry the revised statement of work's sentence exactly once")
    return line


def subject_of(f: dict) -> str:
    """Which of the two stories a proposed finding belongs to, from its catalogue entry and its promise quotes; anything else is 'other' (an extra)."""
    text = " ".join(q["quote"] for q in f.get("promise_quotes") or []).lower()
    path = f.get("catalogue_path") or ""
    if path.startswith("CAP-027") or "scam-call" in text:
        return SCAM
    if path.startswith("CAP-019") or "azure" in text or "host" in text:
        return HOSTING
    return "other"


def extras(findings: list) -> list:
    """Lines for every proposed finding that is not one of the four expected (volume, scoring thresholds, anything else, or a duplicate)."""
    out, seen = [], set()
    for f in findings:
        pair = (subject_of(f), f["kind"])
        if pair not in ALLOWED:
            out.append(f"EXTRA: {f['kind']} · {f['commitment'][:70]!r} · {f.get('catalogue_path')}")
        elif pair in seen:
            out.append(f"EXTRA (duplicate): {f['kind']} · {f['commitment'][:70]!r}")
        seen.add(pair)
    return out


def chain_phrase_hits(findings: list, chain: list) -> list:
    """Lines for every missing phrase of a proposed contract_gap that already appears in a base contract-chain document (chain: [(source id, text)]). Such a gap would not open: the
    verifier closes a contract gap when any of its phrases is in the draft contract or SOW (so a promise whose phrase the base contract already holds is no gap at all)."""
    import detect_v2
    out = []
    for f in findings:
        if f.get("kind") != "contract_gap":
            continue
        for ph in f.get("missing_phrases") or []:
            for sid, text in chain:
                if detect_v2._contains(text, ph):
                    out.append(f"the {subject_of(f)} contract gap's phrase {ph!r} already appears in base contract-chain document {sid}: the gap would not open")
    return out


def missing(findings: list) -> list:
    have = {(subject_of(f), f["kind"]) for f in findings}
    return [f"MISSING: {s} · {k}" for s, k in sorted(ALLOWED - have)]


# ---- canned readings, for --selftest only (built from the staged texts, so every quote is word for word) -------------------------------------------------------------------------
def canned(k1: bool) -> list:
    line = lambda doc, needle: next(l.strip() for l in staged("docs", doc).splitlines() if needle in l)
    rfp, prop = line("AB-03_rfp_response.md", "Scam-call alerts warn"), line("AB-04_proposal.md", "Scam-call alerts will warn")
    azure = line("AB-03_rfp_response.md", "Microsoft Azure")
    aws = line("AB-06_draft_sow.md", "Amazon Web Services")
    base = dict(catalogue_path=None, unlisted_value=None, limit_name=None, promised_quantity=None, missing_phrases=[], contract_quote=None, note_quote=None, subject=None,
                promised_value=None, contract_value=None, reason="canned reading for the self-test")
    note = None if k1 else {"source_id": "AB-05", "quote": "No named exception approved for Alder Bank"}
    return [
        {**base, "kind": "approval_required", "commitment": "Scam-call alerts live from the 1 February 2027 launch", "catalogue_path": "CAP-027/AU", "note_quote": note,
         "promise_quotes": [{"source_id": "AB-03", "quote": rfp}, {"source_id": "AB-04", "quote": prop}]},
        {**base, "kind": "contract_gap", "commitment": "Scam-call alerts live from the 1 February 2027 launch", "missing_phrases": ["scam-call alerts", "on a call with a scammer"],
         "promise_quotes": [{"source_id": "AB-03", "quote": rfp}, {"source_id": "AB-04", "quote": prop}]},
        {**base, "kind": "absolute_limit", "commitment": "Hosting on Microsoft Azure", "catalogue_path": "CAP-019/AU", "unlisted_value": "Microsoft Azure",
         "promise_quotes": [{"source_id": "AB-03", "quote": azure}]},
        {**base, "kind": "conflicting_terms", "commitment": "Hosting on Microsoft Azure", "subject": "dedicated environment", "promised_value": "Microsoft Azure",
         "contract_value": "Amazon Web Services", "contract_quote": {"source_id": "AB-06", "quote": aws}, "promise_quotes": [{"source_id": "AB-03", "quote": azure}]},
    ]


class FakeClient:
    """Stands in for anthropic.Anthropic in --selftest: the first reading is K0, the second K1."""

    def __init__(self):
        self.calls = 0
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **_kw):
        self.calls += 1
        text = json.dumps({"findings": canned(self.calls > 1)})
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)], stop_reason="end_turn", usage=SimpleNamespace(input_tokens=1, output_tokens=1))


# ---- the pipeline: the app's own code, on a scratch ledger and a scratch cache ---------------------------------------------------------------------------------------------------
def pipeline(cache_dir: Path, client, reuse_k0: bool = True) -> dict:
    """client: None (offline: cache hits only), a FakeClient, or a real anthropic client. Returns the report data; never writes outside the scratch ledger and `cache_dir`."""
    import anthropic
    from fastapi.testclient import TestClient

    import api
    import approval_scope  # noqa: F401  (imported so the read-time layer is loaded as in the app)
    import deal_catalogue
    import detect_v2
    import ledger
    import ledger_fixes
    import ledger_import
    import ledger_v2

    rep = {"states": [], "readings": {}, "problems": [], "titles": {}}
    problem = rep["problems"].append
    cache_dir.mkdir(parents=True, exist_ok=True)
    with contextlib.ExitStack() as es, tempfile.TemporaryDirectory() as tmp:
        es.enter_context(mock.patch.object(config, "V2_CACHE_DIR", cache_dir))
        es.enter_context(mock.patch.object(config, "V2_SEED_FILES", {k: v for k, v in config.V2_SEED_FILES.items() if k != DEAL}))  # a stale seed must never serve the new documents
        env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
        if isinstance(client, FakeClient):
            env["ANTHROPIC_API_KEY"] = "selftest"
            es.enter_context(mock.patch("anthropic.Anthropic", return_value=client))
        elif client is not None:
            env["ANTHROPIC_API_KEY"] = os.environ["ANTHROPIC_API_KEY"]  # passed through to the app's own client factory; never printed
        es.enter_context(mock.patch.dict(os.environ, env, clear=True))

        db = Path(tmp) / "alder.sqlite"
        conn = ledger.open_ledger(db)
        did = ledger_v2.import_deal(conn, DEAL)
        conn.commit()
        cat_path = deal_catalogue.path_for(DEAL)
        catalogue = json.loads(Path(cat_path).read_text(encoding="utf-8"))
        if reuse_k0:  # the base documents are unchanged: their accepted reading is reused, so the only new model call is K1's
            k0 = ledger_v2.input_sha256(ledger_v2.current_docs(conn, did), Path(cat_path).read_bytes(), config.EXTRACTION_MODEL)
            if (REAL_CACHE / f"{k0}.json").is_file() and not (cache_dir / f"{k0}.json").is_file():
                shutil.copyfile(REAL_CACHE / f"{k0}.json", cache_dir / f"{k0}.json")
                rep["k0_reused"] = k0
        try:
            ledger_v2.review(conn, DEAL, client, None, str(cat_path))
        except ledger_v2.NeedsModel as exc:
            raise NotReady(f"no reading for the base documents in {cache_dir.name}/ and no model client ({exc}): run the real step first") from None
        conn.close()
        web = TestClient(api.create_app(dist_dir=Path(tmp) / "x", ledger_path=db, public=False), base_url="http://127.0.0.1")

        def key_and_findings():
            c = ledger.connect(db)
            try:
                key = c.execute("SELECT d.input_sha256 FROM v2_detections d JOIN reviews r ON r.id = d.review_id WHERE r.deal_id = ? ORDER BY d.review_id DESC LIMIT 1", (did,)).fetchone()[0]
            finally:
                c.close()
            path = cache_dir / f"{key}.json"
            return key, (json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None)

        def state(label):
            c_ = ledger.connect(db)
            try:
                ckeys = dict(c_.execute("SELECT id, commitment_key FROM commitments WHERE deal_id = ?", (did,)).fetchall())
            finally:
                c_.close()
            reg = web.get(f"/api/deals/{DEAL}/register").json()
            rows = []
            for c in reg["commitments"]:
                subject = next((SCAM if (i.get("catalogue_path") or "").startswith("CAP-027") else HOSTING if (i.get("catalogue_path") or "").startswith("CAP-019") else None
                                for i in c["issues"] if i.get("catalogue_path")), "?")
                rows.append({"subject": subject, "key": c["ref"], "ckey": ckeys.get(c["id"]), "name": c["name"], "status": {"open": "Needs attention", "noted": "Addressed by note", "resolved": "Closed"}.get(c["group"], c["group"]), "open": c["open_count"], "noted": c["noted_count"],
                             "issues": [{"finding": i["finding"], "state": i["state"], "reason": i["reason"], "path": i.get("catalogue_path"),
                                         "signed": (i.get("signed_check") or {}).get("status"), "scope": (i.get("approval_scope") or {}).get("status"),
                                         "closing": (i.get("signed_check") or {}).get("sentence"), "signed_clause": (i.get("signed_check") or {}).get("signed_sentence")} for i in c["issues"]]})
            st = {"label": label, "rows": rows, "rejected": reg["check_coverage"]["rejected"], "open_rows": len(reg["open_rows"]), "noted_rows": len(reg["noted_rows"])}
            rep["states"].append(st)
            return st

        def verdicts(label, findings):
            c = ledger.connect(db)
            try:
                docs = ledger_v2.current_docs(c, did)
            finally:
                c.close()
            return [{"kind": f["kind"], "commitment": f["commitment"], "path": f.get("catalogue_path"), "subject": subject_of(f), "phrases": f.get("missing_phrases"),
                     "quotes": [(q["source_id"], q["quote"][:80]) for q in f["promise_quotes"]], "problems": detect_v2.verify({k: v for k, v in f.items() if k != "problems"}, docs, catalogue)}
                    for f in findings]

        k0, r0 = key_and_findings()
        c = ledger.connect(db)
        try:
            base_chain = [(d["source_id"], d["text"]) for d in ledger_v2.current_docs(c, did) if d["doc_type"] in detect_v2.CONTRACT_TYPES]
        finally:
            c.close()
        s0 = state("start: the base documents")
        if r0 is None:
            raise NotReady("the base-document reading was not stored under the key the app computes")
        rep["readings"]["K0"] = {"key": k0, "findings": r0["findings"], "cost": r0.get("cost_usd"), "verdicts": verdicts("K0", r0["findings"])}

        post = lambda body: web.post(f"/api/deals/{DEAL}/documents/add-and-check", json=body, headers=H)
        ab05, ab06, ab09 = staged("scenarios", "AB-05_v2_named_exception.md"), staged("scenarios", "AB-06_v2_coaching_added.md"), staged("scenarios", "AB-09_signed_contract.md")
        r = post({"source_key": "AB-05", "filename": "AB-05_v2_named_exception.md", "text": ab05})
        if r.status_code != 200:
            raise NotReady(f"adding AB-05 failed: {r.status_code} {r.text[:200]}")
        s1 = state("step 2: approval added (AB-05)")
        c = ledger.connect(db)
        try:
            guard = deal_catalogue.cache_key(c, DEAL, "AB-06", "draft_sow", ledger_import.markdown_adapter(ab06.encode("utf-8"))["canonical_text"], None)
        finally:
            c.close()
        r = post({"source_key": "AB-06", "filename": "AB-06_v2_coaching_added.md", "text": ab06})
        if r.status_code != 200:
            raise NotReady(f"adding AB-06 failed: {r.status_code} {r.text[:200]}")
        k1, r1 = key_and_findings()
        s2 = state("step 3: revised statement of work added (AB-06)")
        if r1 is None:
            raise NotReady("the K1 reading was not stored under the key the review used")
        rep["readings"]["K1"] = {"key": k1, "findings": r1["findings"], "cost": r1.get("cost_usd"), "verdicts": verdicts("K1", r1["findings"])}
        if guard != k1:
            problem(f"the app's cache-key guard computed {guard[:12]}... but the review stored the reading under {k1[:12]}...: the demo would not find it")
        rep["guard"] = guard
        r = post({"name": "Signed contract", "filename": "AB-09_signed_contract.md", "doc_type": "signed_contract", "doc_date": "2026-10-20", "text": ab09})
        if r.status_code != 200:
            raise NotReady(f"adding AB-09 failed: {r.status_code} {r.text[:200]}")
        s3 = state("step 4: signed contract added (AB-09)")
        host = next(row for row in s3["rows"] if row["subject"] == HOSTING)
        ids = [i["id"] for c_ in web.get(f"/api/deals/{DEAL}/register").json()["commitments"] if "ref" in c_ and c_["ref"] == host["key"] for i in c_["issues"] if i["state"] != "Resolved"]
        web.post(f"/api/deals/{DEAL}/resolve-note", json={"issue_ids": ids, "resolved_by": "Self-test", "reason": "Customer agreed AWS Sydney on the 14 Oct call."}, headers=H)
        s4 = state("step 5: hosting settled by a note")
        for role in ("sales", "delivery"):
            web.post(f"/api/deals/{DEAL}/handover/notes", json={"role": role, "note": f"{role} note", "entered_by": "Self-test"}, headers=H)
        done = web.post(f"/api/deals/{DEAL}/handover/complete", json={"completed_by": "Self-test"}, headers=H)
        snap = (done.json().get("snapshot") if done.status_code == 200 else None) or {}
        rep["locked"] = {"open": [i["promise"] for i in snap.get("open_items", [])], "noted": [i["promise"] for i in snap.get("resolved_by_note", [])],
                         "closed_only": [i["promise"] for i in snap.get("closed_items", [])], "status": done.status_code}
        for row in s3["rows"]:
            if row["subject"] in TITLES:
                rep["titles"][row["ckey"]] = TITLES[row["subject"]]

        # ---- the checks ------------------------------------------------------------------------------------------------------------------------------------------------------
        for name, reading in rep["readings"].items():
            for line in extras(reading["findings"]) + (missing(reading["findings"]) if name == "K0" else []):
                problem(f"{name}: {line}")
            if any(w in json.dumps(reading["findings"]).lower() for w in FORBIDDEN_NAMES):
                problem(f"{name}: a real company name appears in the reading")
        for line in chain_phrase_hits(rep["readings"]["K0"]["findings"], base_chain):
            problem(f"K0: {line}")
        k0v = {(v["subject"], v["kind"]): v for v in rep["readings"]["K0"]["verdicts"]}
        for pair in sorted(ALLOWED):
            if pair in k0v and k0v[pair]["problems"]:
                problem(f"K0: {pair[0]} · {pair[1]} would be rejected by the verifier on the base documents: {k0v[pair]['problems'][0]}")

        def row(st, subject):
            return next((x for x in st["rows"] if x["subject"] == subject), None)

        def issue(st, subject, finding):
            return next((i for i in (row(st, subject) or {"issues": []})["issues"] if i["finding"] == finding), None)

        a0, c0 = issue(s0, SCAM, "No approval recorded"), issue(s0, SCAM, "Missing from contract")
        if not (a0 and c0 and a0["state"] != "Resolved" and c0["state"] != "Resolved"):
            problem("start: the scam-call alerts row should open with the approval gap and the contract gap")
        if len([x for x in s0["rows"]]) != 2 or not (row(s0, HOSTING) and row(s0, SCAM)):
            problem(f"start: expected exactly two rows (scam-call alerts, hosting); found {[x['subject'] for x in s0['rows']]}")
        hs = issue(s0, HOSTING, "Not offered")
        if not hs or hs["state"] == "Resolved":
            problem("start: hosting should open as 'Not offered'")
        a1 = issue(s1, SCAM, "Approval starts later")
        if not (a1 and a1["state"] == "Needs action" and a1["reason"].startswith("The promised start date")):
            problem("step 2: the approval should be found but held open, by the promised start date")
        c2, a2 = issue(s2, SCAM, "Missing from contract"), issue(s2, SCAM, "Approval starts later")
        if not (c2 and c2["state"] == "Resolved"):
            problem("step 3: the contract gap should close when the revised statement of work is added (does the proposed missing phrase appear in its sentence?)")
        if not (a2 and a2["reason"].startswith("The contract start date")):
            problem("step 3: the approval gap should stay open, by the contract start date")
        c3, a3 = issue(s3, SCAM, "Missing from contract"), issue(s3, SCAM, "Approval starts later")
        if not (c3 and c3["state"] == "Resolved" and c3["signed"] == "confirmed"):
            problem("step 4: the signed contract should confirm the contract fix")
        if not (a3 and a3["reason"].startswith("The signed start date")):
            problem("step 4: the approval gap should stay open, by the signed start date")
        whole = closing_sentence()  # Round 5c: the closing wording the checker uses, and the signed clause the drawer shows, are the full sentence, not a heading fragment
        if c3 and (c3["closing"] != whole or c3["signed_clause"] != whole):
            problem(f"step 4: the signed check's closing wording is {c3['closing']!r} and the signed clause is {c3['signed_clause']!r}, not the full sentence: a heading probably holds a searched phrase")
        h4 = row(s4, HOSTING)
        if not (h4 and h4["open"] == 0 and h4["noted"] > 0):
            problem("step 5: the hosting row should be addressed by note")
        lk = rep["locked"]
        if not (lk["status"] == 200 and len(lk["open"]) == 1 and len(lk["noted"]) == 1):
            problem(f"locked record: expected 1 needing attention and 1 addressed by note; got {len(lk['open'])} and {len(lk['noted'])}")
    return rep


def show(rep: dict) -> None:
    line = "-" * 118
    for name in ("K0", "K1"):
        rd = rep["readings"].get(name)
        if not rd:
            continue
        what = "the base documents" if name == "K0" else "the base documents + AB-05 + AB-06 (the demo's sample files)"
        reused = rep.get("k0_reused") == rd["key"]
        print(f"\n{line}\nREADING {name}: {what}\n  cache key {rd['key']}   cost ${rd['cost']}{'   (reused from results/v2_cache: no model call)' if reused else ''}\n{line}")
        for v in rd["verdicts"]:
            verdict = "accepted" if not v["problems"] else "rejected: " + v["problems"][0][:110]
            print(f"  {v['kind']:18s} {v['subject']:17s} entry={v['path']}\n    commitment: {v['commitment'][:100]}\n    phrases: {v['phrases']}  quotes from: {sorted({q[0] for q in v['quotes']})}\n    verifier: {verdict}")
        if name == "K1":
            print("  (a gap that is already closed is re-proposed and rejected here; that is expected and only adds to the 'rejected' count below, which the screens show as 'already answered')")
    print(f"\n{line}\nSTORY, step by step (rows, statuses, reasons)\n{line}")
    for st in rep["states"]:
        print(f"  {st['label']}   [{st['open_rows']} need attention, {st['noted_rows']} addressed by note; proposed findings the verifier rejected (screens: failed / already answered): {st['rejected']}]")
        for r in st["rows"]:
            print(f"    - {r['subject']:17s} {r['status']}")
            for i in r["issues"]:
                extra = f" · signed check: {i['signed']}" if i["signed"] else ""
                print(f"        {i['finding']:32s} {i['state']:13s} {i['reason'][:78]}{extra}")
    lk = rep["locked"]
    print(f"\nLOCKED RECORD: needing attention {[p[:50] for p in lk['open']]}; addressed by note {[p[:50] for p in lk['noted']]}; closed only {[p[:50] for p in lk['closed_only']]}")
    print(f"\nSIGNED CHECK: closing wording and signed clause are the full sentence: {closing_sentence()!r}" if not any("closing wording" in p for p in rep["problems"]) else "\nSIGNED CHECK: not the full sentence (see below)")
    here = scen_dir()
    print(f"\nSCENARIO FILES READ FROM: {here.relative_to(ROOT) if here.is_relative_to(ROOT) else here}")
    print(f"\nAPP KEY CHECK: the cache-key guard and the stored reading agree: {rep['guard'][:12] == rep['readings']['K1']['key'][:12]}")
    print("\nPROFILE TITLES (the commitment keys, for data/profiles/alder_bank.json):\n" + json.dumps(rep["titles"], indent=2))
    print(f"\n{line}")


def verdict(rep: dict) -> int:
    if rep["problems"]:
        print("NOT SAFE to --accept:\n  " + "\n  ".join(rep["problems"]))
        return 1
    print("READY: safe to --accept (nothing extra, the story holds in every step, the keys match what the app computes).")
    return 0


def selftest() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        fake = FakeClient()
        rep = pipeline(Path(tmp) / "cache", fake, reuse_k0=False)
    show(rep)
    code = verdict(rep)
    if code == 0 and fake.calls == 2:
        print("self-test ok: the Alder documents, the Alder catalogue and this script produce the story on canned readings (no key, no network). Two canned calls were made.")
        return 0
    print(f"self-test FAILED (model calls {fake.calls})")
    return 1


def accept(rep: dict) -> int:
    if verdict(rep):
        return 1
    REAL_CACHE.mkdir(parents=True, exist_ok=True)
    for name in ("K0", "K1"):
        key = rep["readings"][name]["key"]
        src, dst = CANDIDATES / f"{key}.json", REAL_CACHE / f"{key}.json"
        if dst.exists() and dst.read_bytes() != src.read_bytes():
            print(f"refused: {dst.name} already exists with different content; nothing further written")
            return 1
        shutil.copyfile(src, dst)
        print(f"written results/v2_cache/{dst.name}  ({name})")
    return 0


def main(argv) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--accept", action="store_true")
    ap.add_argument("--fresh", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if a.accept:
        try:
            rep = pipeline(CANDIDATES, None)
        except NotReady as exc:
            print("cannot --accept:", exc)
            return 1
        show(rep)
        return accept(rep)
    if not os.environ.get("ANTHROPIC_API_KEY"):  # presence only; the value is never read here
        print("ANTHROPIC_API_KEY is not set in this terminal: nothing was done. Set it for this one command (or run --selftest).")
        return 2
    if a.fresh and CANDIDATES.exists():
        shutil.rmtree(CANDIDATES)
    import anthropic
    try:
        rep = pipeline(CANDIDATES, anthropic.Anthropic())
    except NotReady as exc:
        print("stopped:", exc)
        return 1
    show(rep)
    code = verdict(rep)
    print(f"\ncandidates kept in {CANDIDATES.name}/ (nothing was written to results/v2_cache). " + ("Next: python fill_alder_readings.py --accept" if code == 0 else "Do not --accept; send me this report."))
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
