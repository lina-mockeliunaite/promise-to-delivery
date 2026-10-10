"""Layout redesign (built 9 Oct; docs/BRIEF_2026-10-06_layout.md): the overview read model, the fix inside the finding,
per-finding decisions, the deal note and the accountable person. Temporary ledgers only; a scripted fake stands in for
the model. Covers the brief's check table."""

import json
import os
import sqlite3
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
import ledger
import scenarios
import workspace
from test_recheck import SOW2, FakeExtractor, build_current

H = {"X-Requested-With": "deal-workspace"}
DEAL = "/api/deals/harbour_bank"


def scenario_text(name):
    return config.scenario_path(name).read_text(encoding="utf-8")


class LayoutCase(unittest.TestCase):
    build = staticmethod(build_current)

    def setUp(self):
        patcher = mock.patch.object(config, "LEDGER_DEALS", ["harbour_bank", "hard_cases"])
        patcher.start()
        self.addCleanup(patcher.stop)
        env = mock.patch.dict(os.environ)
        env.start()
        os.environ.pop("ANTHROPIC_API_KEY", None)
        self.addCleanup(env.stop)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.db = Path(tmp.name) / "ledger.sqlite"
        self.build(self.db).close()
        self.client = TestClient(api.create_app(dist_dir=Path(tmp.name) / "no-dist", ledger_path=self.db),
                                 base_url="http://127.0.0.1", follow_redirects=False)

    def post(self, path, body):
        return self.client.post(DEAL + path, json=body, headers=H)

    def overview(self):
        r = self.client.get(DEAL + "/register")
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def commitment(self, fragment):
        return next(c for c in self.overview()["commitments"] if fragment in c["name"])

    def finding(self, fragment, itype):
        return next(i for i in self.commitment(fragment)["issues"] if i["type"] == itype)

    def count_versions(self):
        conn = ledger.connect(self.db)
        try:
            return conn.execute("SELECT COUNT(*) FROM source_versions").fetchone()[0], conn.execute("SELECT COUNT(*) FROM fixes").fetchone()[0]
        finally:
            conn.close()

    def check(self, issue_id, **body):
        return self.post("/findings/check", {"issue_id": issue_id, **body})

    def pricing_note_v2(self, issue_id, who="Daniel Koh"):
        return self.check(issue_id, source_key="HB-05", confirmed_doc_type="pricing_services_note",
                          filename="HB-05_v2_named_exception.md", text=scenario_text("HB-05_v2_named_exception.md"),
                          signed_off_by=who)


class TestOverview(LayoutCase):
    def test_rows_counts_and_short_terms(self):
        o = self.overview()
        self.assertEqual(o["freshness_label"], "Up to date")
        self.assertTrue(o["can_decide"])
        self.assertEqual(o["finding_counts"], {"unresolved": 8, "awaiting_decision": 8, "needs_reconfirmation": 0, "must_fix_flags": 0})
        rows = [next(c for c in o["commitments"] if c["id"] == i) for i in o["open_rows"]]
        self.assertEqual([c["open_count"] for c in rows], sorted((c["open_count"] for c in rows), reverse=True))
        polygon = rows[0]
        self.assertIn("Polygon, real time", polygon["name"])
        self.assertEqual((polygon["told"], polygon["contract"]), ("real-time", "batch"))
        self.assertEqual(polygon["findings"], ["No approval recorded", "Missing from contract", "Contract says something different"])
        self.assertTrue(polygon["unassigned"])
        self.assertIn("Draft SOW v1", o["versions_line"])
        self.assertEqual(o["resolved_findings"], [])
        self.assertNotIn("sha256", json.dumps(o))

    def test_told_shows_the_promise_s_own_terms_and_unclassified_promises_get_a_readable_name(self):
        by_name = {c["name"]: c for c in self.overview()["commitments"]}
        self.assertEqual(by_name["Payout ledger connector: up to 40,000 payouts per day, by end of first year"]["told"], "40,000 payouts/day")
        self.assertEqual(by_name["VASP counterparty data exchange"]["told"], "by 31 Mar 2027")
        self.assertEqual(by_name["Go-live"]["told"], "1 Dec go-live (conditional)")
        weekly = by_name["Weekly project status meeting during implementation"]
        self.assertEqual(weekly["told"], "weekly")
        self.assertTrue(any(s["quote"].startswith("The parties will hold") for s in weekly["statements"]))  # quote untouched

    def test_register_keys_used_by_the_handoff_are_unchanged(self):
        o = self.overview()
        for key in ("deal", "name", "freshness", "counts", "commitments", "scope_note", "resolved_means"):
            self.assertIn(key, o)


class TestNeverUpToDateWhenADecisionCannotBeSaved(LayoutCase):
    build = staticmethod(scenarios.build_fresh)  # imported reviews: no recorded config, no decision possible

    def test_label(self):
        o = self.overview()
        self.assertEqual(o["freshness"]["state"], "Up to date")  # the ledger's own state is unchanged
        self.assertEqual(o["freshness_label"], workspace.DECISION_NOT_CURRENT)
        self.assertFalse(o["can_decide"])


class TestFixInsideTheFinding(LayoutCase):
    def test_named_exception_closes_only_the_approval_finding(self):
        approval = self.finding("Polygon, real time", "approval")
        r = self.pricing_note_v2(approval["id"])
        self.assertEqual(r.status_code, 200, r.text)
        out = r.json()["check"]
        self.assertEqual(out["this_finding"], "Resolved")
        self.assertEqual(out["closed"], ["No approval recorded"])
        self.assertEqual(out["still_open"], ["Missing from contract", "Contract says something different"])
        self.assertEqual(out["model_calls"], 0)
        self.assertEqual(out["document"], "Pricing and services note, version 2")
        o = self.overview()
        self.assertEqual(o["freshness_label"], "Up to date")
        resolved = next(i for i in self.commitment("Polygon, real time")["issues"] if i["type"] == "approval")
        self.assertTrue(resolved["resolved_by"]["text"].startswith("Resolved by Pricing and services note, version 2"))
        self.assertIn("signed off by Daniel Koh", resolved["resolved_by"]["text"])
        self.assertIn("No approval recorded", [f["finding"] for f in o["resolved_findings"]])

    def test_aligned_sow_closes_both_contract_findings_and_says_so(self):
        gap = self.finding("Polygon, real time", "contract_gap")
        fake = FakeExtractor(SOW2)
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-only"}), mock.patch("anthropic.Anthropic", return_value=fake):
            r = self.check(gap["id"], source_key="HB-06", confirmed_doc_type="draft_sow", filename="HB-06_v2_annex_aligned.md",
                           text=scenario_text("HB-06_v2_annex_aligned.md"), signed_off_by="Dana Lee")
        self.assertEqual(r.status_code, 200, r.text)
        out = r.json()["check"]
        self.assertEqual(sorted(out["closed"]), ["Contract says something different", "Missing from contract"])
        self.assertEqual(out["still_open"], ["No approval recorded"])
        self.assertEqual(fake.calls, 1)

    def test_the_fix_addresses_only_the_clicked_finding_and_other_closures_are_reported_as_effects(self):
        gap = self.finding("Polygon, real time", "contract_gap")
        fake = FakeExtractor(SOW2)
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-only"}), mock.patch("anthropic.Anthropic", return_value=fake):
            r = self.check(gap["id"], source_key="HB-06", confirmed_doc_type="draft_sow", filename="HB-06_v2_annex_aligned.md",
                           text=scenario_text("HB-06_v2_annex_aligned.md"), signed_off_by="Dana Lee")
        self.assertEqual(r.status_code, 200, r.text)
        conn = ledger.connect(self.db)
        try:
            addressed = [row[0] for row in conn.execute("SELECT issue_id FROM fix_issues WHERE fix_id = ?", (r.json()["check"]["fix_id"],))]
        finally:
            conn.close()
        self.assertEqual(addressed, [gap["id"]])
        self.assertIn("Contract says something different", r.json()["check"]["closed"])  # closed by the recheck, as an effect

    def test_a_type_that_does_not_match_the_replaced_document_is_refused_and_nothing_is_saved(self):
        approval = self.finding("Polygon, real time", "approval")
        before = self.count_versions()
        r = self.check(approval["id"], source_key="HB-06", confirmed_doc_type="pricing_services_note",
                       filename="HB-05_v2_named_exception.md", text=scenario_text("HB-05_v2_named_exception.md"), signed_off_by="Dana")
        self.assertEqual(r.status_code, 400, r.text)
        self.assertIn("would replace the Draft SOW", r.json()["detail"])
        self.assertEqual(self.count_versions(), before)
        self.assertEqual(self.finding("Polygon, real time", "approval")["state"], "Needs action")

    def test_the_type_must_be_confirmed_and_someone_must_sign_off(self):
        approval = self.finding("Polygon, real time", "approval")
        before = self.count_versions()
        base = {"source_key": "HB-05", "filename": "x.md", "text": scenario_text("HB-05_v2_named_exception.md")}
        self.assertEqual(self.check(approval["id"], **base, signed_off_by="Dana").status_code, 400)
        self.assertEqual(self.check(approval["id"], **base, confirmed_doc_type="pricing_services_note", signed_off_by=" ").status_code, 400)
        self.assertEqual(self.count_versions(), before)

    def test_a_document_that_needs_the_model_is_refused_up_front_without_a_key(self):
        gap = self.finding("Polygon, real time", "contract_gap")
        before = self.count_versions()
        r = self.check(gap["id"], source_key="HB-06", confirmed_doc_type="draft_sow", filename="HB-06_v2.md",
                       text=scenario_text("HB-06_v2_annex_aligned.md"), signed_off_by="Dana")
        self.assertEqual(r.status_code, 409, r.text)
        self.assertIn("Nothing was saved", r.json()["detail"])
        self.assertEqual(self.count_versions(), before)

    def test_a_finding_from_another_deal_is_not_found(self):
        r = self.check(999999, source_key="HB-05", confirmed_doc_type="pricing_services_note", filename="x.md",
                       text="x", signed_off_by="Dana")
        self.assertEqual(r.status_code, 404)


class TestDecisions(LayoutCase):
    def test_okay_to_proceed_never_changes_the_finding_and_needs_reconfirmation_after_new_evidence(self):
        gap = self.finding("VASP", "contract_gap")
        r = self.post("/decisions", {"kind": "okay_to_proceed", "issue_id": gap["id"], "by": "Mei Tan", "reason": "Phase 2 item."})
        self.assertEqual(r.status_code, 200, r.text)
        o = self.overview()
        self.assertEqual(o["finding_counts"]["unresolved"], 8)          # a decision never reduces the unresolved count
        self.assertEqual(o["finding_counts"]["awaiting_decision"], 7)   # ...but it is no longer awaiting one
        after = self.finding("VASP", "contract_gap")
        self.assertEqual(after["state"], gap["state"])
        self.assertEqual(after["decision"]["status"], "okay")
        self.assertEqual(o["freshness_label"], "Up to date")
        # any new evidence: deal-wide re-confirmation
        approval = self.finding("Polygon, real time", "approval")
        self.assertEqual(self.pricing_note_v2(approval["id"]).status_code, 200)
        o = self.overview()
        self.assertEqual(self.finding("VASP", "contract_gap")["decision"]["status"], "reconfirm")
        self.assertEqual(o["finding_counts"]["needs_reconfirmation"], 1)
        self.assertEqual(o["finding_counts"]["unresolved"], 7)          # only the evidence closed something

    def test_must_fix_stays_visible_after_the_finding_resolves_until_a_named_person_clears_it(self):
        approval = self.finding("Polygon, real time", "approval")
        r = self.post("/decisions", {"kind": "must_fix", "issue_id": approval["id"], "by": "Mei Tan", "reason": "Launch-critical."})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.post("/decisions", {"kind": "must_fix", "issue_id": approval["id"], "by": "Mei", "reason": "x"}).status_code, 409)
        self.assertEqual(self.finding("Polygon, real time", "approval")["state"], "Needs action")
        self.assertEqual(self.pricing_note_v2(approval["id"]).status_code, 200)
        resolved = self.finding("Polygon, real time", "approval")
        self.assertEqual(resolved["state"], "Resolved")
        flag = resolved["decision"]["must_fix"]
        self.assertIsNotNone(flag)
        self.assertEqual(self.overview()["finding_counts"]["must_fix_flags"], 1)
        self.assertEqual(self.post("/decisions/clear", {"flag_id": flag["flag_id"], "by": "", "reason": "x"}).status_code, 400)
        r = self.post("/decisions/clear", {"flag_id": flag["flag_id"], "by": "Mei Tan", "reason": "Exception approved."})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIsNone(self.finding("Polygon, real time", "approval")["decision"]["must_fix"])
        self.assertEqual(self.post("/decisions/clear", {"flag_id": flag["flag_id"], "by": "Mei", "reason": "x"}).status_code, 409)

    def test_must_fix_shows_once_on_the_row_not_again_in_the_decision_line(self):
        approval = self.finding("Polygon, real time", "approval")
        self.assertEqual(self.post("/decisions", {"kind": "must_fix", "issue_id": approval["id"], "by": "Mei", "reason": "x"}).status_code, 200)
        row = self.commitment("Polygon, real time")
        self.assertTrue(row["must_fix"])
        self.assertNotIn("must fix", row["decision_line"].lower())
        self.assertEqual(row["decision_line"], "2 awaiting decision")

    def test_unknown_kind_and_missing_reason_are_refused(self):
        gap = self.finding("VASP", "contract_gap")
        self.assertEqual(self.post("/decisions", {"kind": "resolve", "issue_id": gap["id"], "by": "A", "reason": "B"}).status_code, 400)
        self.assertEqual(self.post("/decisions", {"kind": "okay_to_proceed", "issue_id": gap["id"], "by": "A", "reason": ""}).status_code, 400)


class TestDocumentText(LayoutCase):
    def test_a_resolved_finding_can_open_its_evidence_and_only_this_deal_s_versions(self):
        approval = self.finding("Polygon, real time", "approval")
        self.assertEqual(self.pricing_note_v2(approval["id"]).status_code, 200)
        doc = self.finding("Polygon, real time", "approval")["resolved_by"]["documents"][0]
        r = self.client.get(DEAL + f"/documents/text?version={doc['source_version_id']}")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["name"], "Pricing and services note, version 2")
        self.assertIn("Harbour Bank", r.json()["text"])
        conn = ledger.connect(self.db)
        try:
            other = conn.execute("SELECT v.id FROM source_versions v JOIN sources s ON s.id = v.source_id JOIN deals d"
                                 " ON d.id = s.deal_id WHERE d.slug = 'hard_cases' LIMIT 1").fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(self.client.get(DEAL + f"/documents/text?version={other}").status_code, 404)
        self.assertEqual(self.client.get(f"/api/deals/hard_cases/documents/text?version={other}").status_code, 404)


class TestDealNoteAndAccountable(LayoutCase):
    def test_deal_note_is_typed_append_only_and_never_marks_the_review_out_of_date(self):
        r = self.post("/note", {"note": "Stablecoin payouts for SMEs; launch 1 Dec.", "entered_by": "Lina", "deadline": "2026-11-20"})
        self.assertEqual(r.status_code, 200, r.text)
        o = self.overview()
        self.assertEqual(o["deal_note"]["entered_by"], "Lina")
        self.assertEqual(o["deal_note"]["deadline"], "2026-11-20")
        self.assertEqual(o["freshness_label"], "Up to date")
        self.assertEqual(self.post("/note", {"note": "x", "entered_by": "Lina", "deadline": "20 Nov"}).status_code, 400)
        self.assertEqual(self.post("/note", {"note": "", "entered_by": "Lina"}).status_code, 400)
        conn = sqlite3.connect(self.db)
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("UPDATE deal_notes SET note = 'changed'")
        finally:
            conn.close()

    def test_accountable_person_shows_on_the_row(self):
        gap = self.finding("VASP", "contract_gap")
        r = self.post("/accountable", {"issue_id": gap["id"], "person": "Priya Nair", "set_by": "Lina"})
        self.assertEqual(r.status_code, 200, r.text)
        vasp = self.commitment("VASP")
        self.assertEqual(vasp["accountable"], "Priya Nair")
        self.assertTrue(vasp["unassigned"])  # the approval finding still has nobody
        self.assertEqual(next(i for i in vasp["issues"] if i["id"] == gap["id"])["accountable"]["status"], "current")
        self.assertEqual(vasp["confirm_owner"], [])

    def test_an_owner_named_before_the_evidence_changed_shows_as_needing_confirmation_not_as_unassigned(self):
        approval = self.finding("VASP", "approval")  # assessed against the pricing note
        self.assertEqual(self.post("/accountable", {"issue_id": approval["id"], "person": "Priya Nair", "set_by": "Lina"}).status_code, 200)
        polygon_approval = self.finding("Polygon, real time", "approval")
        self.assertEqual(self.pricing_note_v2(polygon_approval["id"]).status_code, 200)  # new pricing note version
        vasp = self.commitment("VASP")
        self.assertIsNone(vasp["accountable"])
        self.assertEqual(vasp["confirm_owner"], ["Priya Nair"])


if __name__ == "__main__":
    unittest.main()
