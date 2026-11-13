"""Round 6 (13 Nov): the rejected-findings count split by kind, read at display time (rejection_kind.py, workspace.rejection_split, handover()["check_split"]).

"failed": the evidence did not verify. "answered": the evidence verifies and the current documents already answer the point. The kind comes from the verifier's own
predicates, not from its problem text. The total, the stored records, the snapshot and its fingerprint are untouched."""
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

import api
import config
import deal_catalogue
import detect_v2
import handover
import ledger
import ledger_fixes
import ledger_v2
import rejection_kind
import reset_demo
import workspace

SCEN = config.SCENARIOS_DIR


def fresh(test, deal=None, add=()):
    """A scratch ledger rebuilt from the saved reading (no model call), plus any pricing-note versions in `add` (source key, file)."""
    tmp = tempfile.TemporaryDirectory()
    test.addCleanup(tmp.cleanup)
    db = Path(tmp.name) / "l.sqlite"
    reset_demo.reset(db_path=db)
    conn = ledger.connect(db)
    test.addCleanup(conn.close)
    for key, name in add:
        ledger_fixes.add_source_version(conn, deal, key, (SCEN / name).read_text(encoding="utf-8"), name)
    if add:
        deal_catalogue.recheck(conn, deal, None, None)
    return conn


def stored_rejected(conn, slug):
    did = ledger_fixes.deal_id(conn, slug)
    row = conn.execute("SELECT d.rejected_json FROM v2_detections d JOIN reviews r ON r.id = d.review_id WHERE r.deal_id = ? ORDER BY d.review_id DESC LIMIT 1", (did,)).fetchone()
    return did, json.loads(row[0])


DOC = lambda sid, typ, text: {"source_id": sid, "doc_type": typ, "text": text}


class TestClassification(unittest.TestCase):
    CAT = {"capabilities": []}

    def gap(self, **kw):
        return {"kind": "contract_gap", "promise_quotes": [{"source_id": "RFP", "quote": "We will provide a named launch specialist."}], "missing_phrases": ["launch specialist"], **kw}

    def docs(self, contract="The supplier provides the assistant."):
        return [DOC("RFP", "rfp_response", "We will provide a named launch specialist."), DOC("SOW", "draft_sow", contract)]

    def test_a_gap_the_contract_now_answers_is_answered(self):
        self.assertTrue(detect_v2.verify(self.gap(), self.docs("The supplier provides a launch specialist."), self.CAT))  # the verifier rejects it
        self.assertEqual(rejection_kind.classify(self.gap(), self.docs("The supplier provides a launch specialist."), self.CAT), "answered")

    def test_a_gap_that_is_answered_but_whose_quote_fails_is_failed_never_answered(self):
        """The contract does hold the phrase, but the promise quote is not in the source: the evidence failed, so the point is not 'answered'."""
        bad = self.gap(promise_quotes=[{"source_id": "RFP", "quote": "We will provide a dedicated specialist, named."}])
        docs = self.docs("The supplier provides a launch specialist.")
        self.assertTrue(detect_v2.verify(bad, docs, self.CAT))
        self.assertEqual(rejection_kind.classify(bad, docs, self.CAT), "failed")
        # also when the source is internal or unknown
        self.assertEqual(rejection_kind.classify(self.gap(promise_quotes=[{"source_id": "NOTE", "quote": "x"}]), docs + [DOC("NOTE", "pricing_services_note", "x")], self.CAT), "failed")
        self.assertEqual(rejection_kind.classify(self.gap(promise_quotes=[{"source_id": "NOPE", "quote": "x"}]), docs, self.CAT), "failed")
        self.assertEqual(rejection_kind.classify(self.gap(promise_quotes=[]), docs, self.CAT), "failed")

    def test_evidence_that_fails_for_other_reasons_is_failed(self):
        docs = self.docs()  # the contract does NOT hold the phrase: this would verify, so it is not even a rejection; make it fail by phrase not in the promise
        self.assertEqual(rejection_kind.classify(self.gap(missing_phrases=["invented phrase"]), docs, self.CAT), "failed")
        self.assertEqual(rejection_kind.classify(self.gap(missing_phrases=["a phrase of far more than six words long"]), docs, self.CAT), "failed")
        self.assertEqual(rejection_kind.classify(self.gap(missing_phrases=[]), docs, self.CAT), "failed")
        self.assertEqual(rejection_kind.classify({**self.gap(), "kind": "no_such_kind"}, docs, self.CAT), "failed")

    def test_a_conflict_the_contract_now_matches_is_answered_and_a_bad_contract_quote_is_failed(self):
        f = {"kind": "conflicting_terms", "promise_quotes": [{"source_id": "RFP", "quote": "Support in 12 languages."}], "subject": "languages",
             "promised_value": "12", "contract_value": "4", "contract_quote": {"source_id": "SOW", "quote": "Support in 12 languages."}}
        docs = [DOC("RFP", "rfp_response", "Support in 12 languages."), DOC("SOW", "draft_sow", "Support in 12 languages.")]
        self.assertTrue(detect_v2.verify(f, docs, self.CAT))
        self.assertEqual(rejection_kind.classify(f, docs, self.CAT), "answered")
        gone = [DOC("RFP", "rfp_response", "Support in 12 languages."), DOC("SOW", "draft_sow", "Support in 4 languages.")]
        self.assertEqual(rejection_kind.classify(f, gone, self.CAT), "failed")  # the contract quote is not verbatim any more

    def test_split_counts_both_kinds(self):
        docs = self.docs("The supplier provides a launch specialist.")
        bad = self.gap(promise_quotes=[{"source_id": "RFP", "quote": "not in the document at all"}])
        self.assertEqual(rejection_kind.split([self.gap(), bad, bad], docs, self.CAT), {"failed": 2, "answered": 1})
        self.assertEqual(rejection_kind.split([], docs, self.CAT), {"failed": 0, "answered": 0})


class TestAlderAndNoma(unittest.TestCase):
    def test_alder_by_step_failed_and_answered(self):
        base = fresh(self)
        self.assertEqual(workspace.overview(base, "alder_bank")["check_split"], {"failed": 0, "answered": 0})
        step2 = fresh(self, "alder_bank", [("AB-05", "AB-05_v2_named_exception.md")])
        ov = workspace.overview(step2, "alder_bank")
        self.assertEqual((ov["check_coverage"], ov["check_split"]), ({"rejected": 1}, {"failed": 0, "answered": 1}))
        did, rejected = stored_rejected(step2, "alder_bank")
        # the verifier's own text here is "the pricing-note quote is not verbatim": the kind is not read from it, it is derived from the documents (the approval is recorded)
        self.assertEqual(rejected[0]["problems"][0], ledger_v2.NOTE_QUOTE_GONE)
        # the split never changes the stored records, the total or any count
        self.assertEqual(len(rejected), 1)
        self.assertEqual(ov["check_coverage"]["rejected"], ov["check_split"]["failed"] + ov["check_split"]["answered"])

    def test_noma_after_the_named_exception_note_is_answered_not_failed(self):
        conn = fresh(self, "noma_journeys", [("NJ-05", "NJ-05_v2_named_exception.md")])
        ov = workspace.overview(conn, "noma_journeys")
        self.assertEqual((ov["check_coverage"], ov["check_split"]), ({"rejected": 1}, {"failed": 0, "answered": 1}))
        self.assertEqual(workspace.overview(fresh(self), "noma_journeys")["check_split"], {"failed": 0, "answered": 0})

    def test_a_real_stored_finding_whose_quote_is_broken_counts_as_failed(self):
        conn = fresh(self, "alder_bank", [("AB-05", "AB-05_v2_named_exception.md")])
        did, rejected = stored_rejected(conn, "alder_bank")
        docs, cat = ledger_v2.current_docs(conn, did), deal_catalogue.load(conn, "alder_bank")
        self.assertEqual(rejection_kind.classify(rejected[0], docs, cat), "answered")
        broken = copy.deepcopy(rejected[0])
        broken["promise_quotes"][0]["quote"] = broken["promise_quotes"][0]["quote"] + " (and more words that are not there)"
        self.assertEqual(rejection_kind.classify(broken, docs, cat), "failed")  # the gap is answered, the quote fails: failed

    def test_the_snapshot_and_its_fingerprint_do_not_change_and_the_split_sits_beside_them(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        db = Path(tmp.name) / "l.sqlite"
        reset_demo.reset(db_path=db)
        client = TestClient(api.create_app(dist_dir=Path(tmp.name) / "x", ledger_path=db, public=False), base_url="http://127.0.0.1")
        H = {"X-Requested-With": "deal-workspace"}
        for body in ({"source_key": "AB-05", "filename": "n.md", "text": (SCEN / "AB-05_v2_named_exception.md").read_text(encoding="utf-8")},
                     {"name": "Signed contract", "filename": "s.md", "doc_type": "signed_contract", "doc_date": "2026-10-20", "text": (SCEN / "AB-09_signed_contract.md").read_text(encoding="utf-8")}):
            self.assertEqual(client.post("/api/deals/alder_bank/documents/add-and-check", json=body, headers=H).status_code, 200)
        for role, note in (("sales", "Sales note."), ("delivery", "Accepted.")):
            self.assertEqual(client.post("/api/deals/alder_bank/handover/notes", json={"role": role, "note": note, "entered_by": "Sam"}, headers=H).status_code, 200)
        self.assertEqual(client.post("/api/deals/alder_bank/handover/complete", json={"completed_by": "Sam"}, headers=H).status_code, 200)
        conn = ledger.connect(db)
        self.addCleanup(conn.close)
        did = ledger_fixes.deal_id(conn, "alder_bank")
        stored = conn.execute("SELECT snapshot_json FROM handover_completions WHERE deal_id = ?", (did,)).fetchone()[0]
        hv = handover.handover(conn, "alder_bank")
        self.assertEqual(hv["snapshot"]["check_coverage"], {"rejected": 1})  # the saved total, as before
        self.assertNotIn("check_split", hv["snapshot"])
        self.assertNotIn("check_split", stored)
        self.assertEqual(hv["fingerprint"], hashlib.sha256(stored.encode("utf-8")).hexdigest())
        self.assertEqual(hv["check_split"], {"failed": 0, "answered": 1})
        again = handover.handover(conn, "alder_bank")  # reading it again changes nothing
        self.assertEqual((again["fingerprint"], again["snapshot"]), (hv["fingerprint"], hv["snapshot"]))
        self.assertEqual(conn.execute("SELECT snapshot_json FROM handover_completions WHERE deal_id = ?", (did,)).fetchone()[0], stored)

    def test_the_locked_record_gets_the_signed_check_results_in_its_own_response_and_the_snapshot_is_untouched(self):
        """Round 8c: GET handover carries live_commitments (the signed check's results, read now) beside the snapshot, so the record is drawn from one response. The snapshot, its
        fingerprint and the stored text do not change; the default handover() (which workspace.overview calls) does not carry them, so there is no recursion."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        db = Path(tmp.name) / "l.sqlite"
        reset_demo.reset(db_path=db)
        client = TestClient(api.create_app(dist_dir=Path(tmp.name) / "x", ledger_path=db, public=False), base_url="http://127.0.0.1")
        H = {"X-Requested-With": "deal-workspace"}
        r = client.post("/api/deals/noma_journeys/documents/add-and-check", json={"name": "Signed contract", "filename": "s.md", "doc_type": "signed_contract", "doc_date": "2026-10-20",
                                                                                   "text": (SCEN / "NJ-09_signed_contract.md").read_text(encoding="utf-8")}, headers=H)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIsNone(client.get("/api/deals/noma_journeys/handover").json()["live_commitments"])  # not locked: nothing
        for role in ("sales", "delivery"):
            client.post("/api/deals/noma_journeys/handover/notes", json={"role": role, "note": "n", "entered_by": "Sam"}, headers=H)
        self.assertEqual(client.post("/api/deals/noma_journeys/handover/complete", json={"completed_by": "Sam"}, headers=H).status_code, 200)
        conn = ledger.connect(db)
        self.addCleanup(conn.close)
        did = ledger_fixes.deal_id(conn, "noma_journeys")
        stored = conn.execute("SELECT snapshot_json FROM handover_completions WHERE deal_id = ?", (did,)).fetchone()[0]
        hv = client.get("/api/deals/noma_journeys/handover").json()
        live = {c["name"]: c for c in hv["live_commitments"]}
        self.assertTrue(live)
        self.assertEqual(hv["fingerprint"], hashlib.sha256(stored.encode("utf-8")).hexdigest())
        self.assertNotIn("live_commitments", hv["snapshot"])
        self.assertNotIn("live_commitments", stored)
        self.assertEqual({c["name"] for c in hv["live_commitments"]} >= {i["promise"] for i in hv["snapshot"]["open_items"]}, True)  # every open promise of the record is there
        for c in hv["live_commitments"]:
            for i in c["issues"]:
                self.assertIn("finding", i)
                self.assertIn("state", i)  # the same issue records the live register has, signed_check included when there is one
        self.assertIsNone(handover.handover(conn, "noma_journeys")["live_commitments"])
        self.assertEqual(conn.execute("SELECT snapshot_json FROM handover_completions WHERE deal_id = ?", (did,)).fetchone()[0], stored)

    def test_a_deal_with_no_review_has_no_split_and_an_unlocked_deal_has_no_record_split(self):
        conn = fresh(self)
        self.assertIsNone(workspace.rejection_split(conn, 10**6, "alder_bank"))
        self.assertIsNone(handover.handover(conn, "alder_bank")["check_split"])


if __name__ == "__main__":
    unittest.main()
