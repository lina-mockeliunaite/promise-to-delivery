"""Workspace API: the register, documents, fixes, review and freshness, against a temporary ledger.

The ledger is built from the development deals in a temporary file. Only harbour_bank (config.UI_DEALS) and user deals
are reachable; hard_cases is in the ledger but not in the UI, and sealed_decoy is never in either. A scripted fake stands
in for the model. No label file is read by the API.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi.testclient import TestClient

import api
import config
import scenarios
from test_recheck import FakeExtractor, build_current

H = {"X-Requested-With": "deal-workspace"}


class WorkspaceCase(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(config, "LEDGER_DEALS", ["harbour_bank", "hard_cases"])
        patcher.start()
        self.addCleanup(patcher.stop)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.db = root / "ledger.sqlite"
        build_current(self.db).close()
        self.client = TestClient(api.create_app(dist_dir=root / "no-dist", ledger_path=self.db),
                                 base_url="http://127.0.0.1", follow_redirects=False)

    def post(self, path, body):
        return self.client.post(path, json=body, headers=H)

    def register(self, deal="harbour_bank"):
        r = self.client.get(f"/api/deals/{deal}/register")
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def commitment(self, fragment, deal="harbour_bank"):
        return next(c for c in self.register(deal)["commitments"] if fragment in c["name"])


class TestReading(WorkspaceCase):
    def test_the_register_shows_the_harbour_bank_findings_in_plain_language(self):
        reg = self.register()
        self.assertEqual(reg["freshness"]["state"], "Up to date")
        self.assertEqual(reg["counts"], {"Needs action": 3, "Needs evidence": 1, "No issues raised": 3,
                                         "Not checked: conditional promise": 1})
        polygon = self.commitment("Polygon, real time")
        self.assertEqual(polygon["attention"], ["Needs internal approval", "Missing from the contract",
                                                "Contract says something different"])
        self.assertTrue(all(i["next_step"] for i in polygon["issues"]))
        self.assertTrue(any("Every NUSD payout on Polygon" in s["quote"] for s in polygon["statements"]))
        self.assertNotIn("sha256", json.dumps(reg))

    def test_only_ui_deals_and_existing_user_deals_are_reachable(self):
        for deal in ("hard_cases", "sealed_decoy", "u_0123456789abcdef", "..", "harbour_bank%2F..%2Fsealed_decoy"):
            for path in (f"/api/deals/{deal}/register", f"/api/deals/{deal}/documents"):
                self.assertIn(self.client.get(path).status_code, (404, 422), path)
            self.assertIn(self.post(f"/api/deals/{deal}/review", {}).status_code, (404, 422), deal)
        names = [d["deal"] for d in self.client.get("/api/workspace/deals").json()["deals"]]
        self.assertEqual(names, ["harbour_bank"])

    def test_writes_need_the_header_and_a_json_body(self):
        self.assertEqual(self.client.post("/api/deals/harbour_bank/review", json={}).status_code, 403)
        r = self.client.post("/api/deals/harbour_bank/review", data="x", headers={**H, "Content-Type": "text/plain"})
        self.assertEqual(r.status_code, 403)


class TestFixFlow(WorkspaceCase):
    def test_upload_fix_and_review_closes_only_the_approval_issue(self):
        text = config.scenario_path("HB-05_v2_named_exception.md").read_text(encoding="utf-8")
        r = self.post("/api/deals/harbour_bank/documents", {"source_key": "HB-05", "filename": "HB-05_v2.md", "text": text})
        self.assertEqual(r.status_code, 200, r.text)
        vid = r.json()["source_version_id"]
        self.assertEqual(self.register()["freshness"]["state"], "Review out of date")
        polygon = self.commitment("Polygon, real time")
        approval = next(i for i in polygon["issues"] if i["type"] == "approval")
        r = self.post("/api/deals/harbour_bank/fixes", {
            "route": "allowed_exception", "owner": "Product", "rationale": "Named exception recorded.",
            "issue_ids": [approval["id"]], "evidence": [{"source_version_id": vid, "locator": "CAP-021 Polygon row"}],
            "approved_by": "Daniel Koh"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.commitment("Polygon, real time")["status"], "Needs action")  # a fix alone closes nothing
        r = self.post("/api/deals/harbour_bank/review", {"fix_id": r.json()["fix_id"]})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["review"]["model_calls"], 0)
        polygon = self.commitment("Polygon, real time")
        states = {i["type"]: i["state"] for i in polygon["issues"]}
        self.assertEqual(states, {"approval": "Resolved", "contract_gap": "Needs action", "conflicting_terms": "Needs action"})
        self.assertEqual(self.register()["freshness"]["state"], "Up to date")

    def test_owner_and_note_changes_do_not_mark_the_review_out_of_date_or_change_state(self):
        issue = self.commitment("Polygon, real time")["issues"][0]
        r = self.post("/api/deals/harbour_bank/issues", {"issue_id": issue["id"], "owner": "Delivery", "note": "Call Product"})
        self.assertEqual(r.status_code, 200, r.text)
        after = next(i for i in self.commitment("Polygon, real time")["issues"] if i["id"] == issue["id"])
        self.assertEqual((after["owner"], after["note"], after["state"]), ("Delivery", "Call Product", issue["state"]))
        self.assertEqual(self.register()["freshness"]["state"], "Up to date")

    def test_excluding_a_document_marks_the_review_out_of_date(self):
        r = self.post("/api/deals/harbour_bank/documents/include", {"source_key": "HB-04", "included": False})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.register()["freshness"]["state"], "Review out of date")

    def fixes_in_ledger(self):
        import ledger
        conn = ledger.connect(self.db)
        try:
            return conn.execute("SELECT COUNT(*), COUNT(fix_key) FROM fixes").fetchone()[0]
        finally:
            conn.close()

    def test_a_refused_sign_off_leaves_no_draft_fix_behind(self):
        issue = self.commitment("Polygon, real time")["issues"][0]
        body = {"route": "allowed_exception", "owner": "Product", "rationale": "Named exception.",
                "issue_ids": [issue["id"]], "evidence": [{"source_version_id": 5, "locator": "whole document"}]}
        for bad in ({"approved_by": ""}, {"approved_by": "   "}, {}):
            r = self.post("/api/deals/harbour_bank/fixes", {**body, **bad})
            self.assertEqual(r.status_code, 400, r.text)
            self.assertEqual(r.json()["detail"], "a fix needs the name of who signs it off")
            self.assertEqual(self.fixes_in_ledger(), 0)
        # a route that needs evidence, sent without any: the ledger refuses at approval; still no draft
        r = self.post("/api/deals/harbour_bank/fixes", {**body, "evidence": [], "approved_by": "Dana"})
        self.assertEqual(r.status_code, 400, r.text)
        self.assertEqual(self.fixes_in_ledger(), 0)
        # and the next real fix is the first one: nothing was skipped
        r = self.post("/api/deals/harbour_bank/fixes", {"route": "change_or_withdraw_promise", "owner": "Product",
                      "rationale": "Withdraw it.", "issue_ids": [issue["id"]], "evidence": [], "approved_by": "Dana"})
        self.assertEqual(r.status_code, 200, r.text)
        import ledger
        conn = ledger.connect(self.db)
        try:
            self.assertEqual(conn.execute("SELECT fix_key, status FROM fixes").fetchall(), [("F1", "approved")])
        finally:
            conn.close()

    def test_a_fix_cannot_claim_an_issue_from_another_deal_and_bad_input_is_a_400(self):
        r = self.post("/api/deals/harbour_bank/fixes", {"route": "allowed_exception", "owner": "Product", "rationale": "x",
                                                        "issue_ids": [999999], "evidence": [], "approved_by": "x"})
        self.assertEqual(r.status_code, 400)
        r = self.post("/api/deals/harbour_bank/issues", {"issue_id": 999999, "note": "x"})
        self.assertEqual(r.status_code, 404)


class TestUserDeal(WorkspaceCase):
    def test_create_upload_and_review_a_user_deal(self):
        r = self.post("/api/user-deals", {"name": "Acme renewal"})
        self.assertEqual(r.status_code, 200, r.text)
        deal = r.json()["deal"]
        self.assertRegex(deal, r"^u_[0-9a-f]{16}$")
        proposal = "# Proposal\n\nElva will provide full case audit history for every alert.\n"
        r = self.post(f"/api/deals/{deal}/documents", {"name": "Proposal", "filename": "proposal.md", "doc_type": "proposal",
                                                       "doc_date": "2026-11-01", "text": proposal})
        self.assertEqual(r.status_code, 200, r.text)
        with mock.patch.dict(os.environ, {}, clear=True):
            r = self.post(f"/api/deals/{deal}/review", {})
        self.assertEqual(r.status_code, 409)  # needs the model, and the server has no key
        payload = {"statements": [{"quote": "Elva will provide full case audit history for every alert.",
                                   "speaker": "x", "language": "firm"}]}
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-only"}), \
                mock.patch("anthropic.Anthropic", return_value=FakeExtractor(payload)):
            r = self.post(f"/api/deals/{deal}/review", {})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["review"]["run_kind"], "review")
        reg = self.register(deal)
        audit = next(c for c in reg["commitments"] if "Case audit history" in c["name"])
        self.assertEqual(audit["authorisation"], "Standard, authorised")
        self.assertIn("Contract coverage can't be confirmed", audit["attention"])  # no contract uploaded
        self.assertIn("unvalidated", reg["scope_note"])

    def test_a_user_deal_rejects_an_unknown_document_type_and_an_empty_name(self):
        self.assertEqual(self.post("/api/user-deals", {"name": " "}).status_code, 400)
        deal = self.post("/api/user-deals", {"name": "X"}).json()["deal"]
        r = self.post(f"/api/deals/{deal}/documents", {"name": "a", "doc_type": "board_minutes", "doc_date": "2026-11-01",
                                                       "text": "x"})
        self.assertEqual(r.status_code, 400)


if __name__ == "__main__":
    unittest.main()
