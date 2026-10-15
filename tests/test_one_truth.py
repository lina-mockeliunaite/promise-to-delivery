"""One source of truth (15 Oct): the overview, the register and the handoff never disagree about a promise's contract
position or approval, and the deal brief says when the document it was confirmed against has changed."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import deal_stage
import handoff
import workspace
from tests.test_ledger_v2 import SCEN, FakeClient, V2Case

GAP_FREE = ("No contract gap found",)


def snapshot(conn, slug):
    open_ids = [i["id"] for c in workspace.overview(conn, slug)["commitments"] for i in c["issues"] if i["state"] != "Resolved"]
    return handoff.build_snapshot(conn, slug, "proceed", "Lina", "", open_ids, "2026-10-15", "2026-10-15")


class TestOneTruth(V2Case):
    def assert_views_agree(self, slug):
        ov = workspace.overview(self.conn, slug)
        snap = snapshot(self.conn, slug)
        by_name = {c["promise"]: c for c in snap["commitments"]}
        for c in ov["commitments"]:
            open_types = {i["type"] for i in c["issues"] if i["state"] != "Resolved"}
            exported = by_name[c["name"]]["contract"]
            if open_types & {"contract_gap", "conflicting_terms"}:
                self.assertNotIn(c["presence"], GAP_FREE, c["name"])
                self.assertNotIn(exported, GAP_FREE, c["name"])
                if c["id"] in ov["open_rows"]:
                    self.assertNotEqual(c["contract"], "No gap found", c["name"])
            if "approval" in open_types:
                self.assertEqual(c["authorisation"], "No approval recorded", c["name"])

    def test_all_views_agree_on_the_seeded_deals(self):
        for slug in ("harbour_bank", "coral_pay", "atlas_remit"):
            self.assert_views_agree(slug)

    def test_after_both_fixes_the_views_still_agree_and_the_exception_is_listed(self):
        iid, _ = self.find("harbour_bank", "Polygon", "No approval recorded")
        self.attach("harbour_bank", iid, SCEN / "HB-05_v2_named_exception.md", "pricing_services_note", source_key="HB-05")
        iid, _ = self.find("harbour_bank", "Polygon", "Contract says something different")
        self.attach("harbour_bank", iid, SCEN / "HB-06_v2_annex_aligned.md", "draft_sow", source_key="HB-06",
                    client=FakeClient([]))
        self.assert_views_agree("harbour_bank")
        ov = workspace.overview(self.conn, "harbour_bank")
        polygon = next(c for c in ov["commitments"] if "Polygon" in c["name"])
        self.assertEqual(polygon["authorisation"], "Exception approved")
        snap = snapshot(self.conn, "harbour_bank")
        self.assertTrue(any("Polygon" in x["commitment"] for x in snap["exceptions"]))
        self.assertIn("Daniel Koh", next(x["evidence"] for x in snap["exceptions"] if "Polygon" in x["commitment"]))

    def test_the_brief_asks_for_reconfirmation_once_its_sow_changes(self):
        self.assertFalse(deal_stage.deal_brief(self.conn, "harbour_bank")["needs_reconfirmation"])
        iid, _ = self.find("harbour_bank", "Polygon", "Contract says something different")
        self.attach("harbour_bank", iid, SCEN / "HB-06_v2_annex_aligned.md", "draft_sow", source_key="HB-06",
                    client=FakeClient([]))
        brief = deal_stage.deal_brief(self.conn, "harbour_bank")
        self.assertTrue(brief["needs_reconfirmation"])
        self.assertIn("version 2", brief["reconfirm_note"])
        self.assertNotIn("HB-06", brief["reconfirm_note"])


if __name__ == "__main__":
    unittest.main()
