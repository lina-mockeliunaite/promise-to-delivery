"""Revamp (15 Oct): the deal stage is worked out from the documents; gaps are placed where their promise was first
made; the brief is owner-confirmed and read from a profile. Reads only: nothing here may change a finding."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
import deal_stage
import ledger
import ledger_v2
import workspace


def doc(key, dtype, date):
    return {"key": key, "type": dtype, "date": date}


class TestPlacement(unittest.TestCase):
    def test_first_call_is_discovery_and_later_calls_evaluation(self):
        placed = deal_stage.place_documents([doc("A", "call_transcript", "2026-09-01"),
                                             doc("B", "call_transcript", "2026-09-05")])
        self.assertEqual(placed, {"A": "discovery", "B": "evaluation"})

    def test_contract_documents_mark_contracting(self):
        placed = deal_stage.place_documents([doc("A", "call_transcript", "2026-09-01"), doc("P", "proposal", "2026-09-10"),
                                             doc("S", "draft_sow", "2026-09-20"), doc("C", "draft_contract", "2026-09-21")])
        self.assertEqual((placed["P"], placed["S"], placed["C"]), ("proposal", "contracting", "contracting"))

    def test_internal_note_and_email_never_move_the_stage(self):
        placed = deal_stage.place_documents([doc("A", "call_transcript", "2026-09-01"),
                                             doc("N", "pricing_services_note", "2026-09-02"),
                                             doc("E", "customer_email", "2026-09-03")])
        self.assertEqual((placed["N"], placed["E"]), ("discovery", "discovery"))

    def test_a_late_call_does_not_move_the_stage_back(self):
        placed = deal_stage.place_documents([doc("P", "proposal", "2026-09-10"), doc("A", "call_transcript", "2026-09-11")])
        self.assertEqual(placed["A"], "proposal")
        self.assertEqual(max(placed.values(), key=deal_stage.STAGE_INDEX.get), "proposal")


class TestOnDemoDeals(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        d = Path(cls.tmp.name)
        cls.patch = mock.patch.object(config, "V2_CACHE_DIR", d / "cache")
        cls.patch.start()
        ledger_v2.build(d / "l.sqlite")
        cls.conn = ledger.connect(d / "l.sqlite")

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        cls.patch.stop()
        cls.tmp.cleanup()

    def test_harbour_bank_is_at_contracting_from_its_documents(self):
        s = deal_stage.deal_stage(self.conn, "harbour_bank")
        self.assertEqual((s["current"], s["basis"]), ("contracting", "documents"))
        states = [x["state"] for x in s["stages"]]
        self.assertEqual(states, ["done", "done", "done", "done", "current", "todo", "todo"])

    def test_every_promise_with_an_open_gap_is_placed_once(self):
        ov = workspace.overview(self.conn, "harbour_bank")
        placed = sum(x["gaps_started"] for x in ov["stage"]["stages"])
        self.assertEqual(placed, len(ov["open_rows"]))
        self.assertIn("Proposal / RFP", ov["stage"]["headline"])

    def test_brief_comes_from_the_profile_and_says_who_confirmed_it(self):
        brief = workspace.overview(self.conn, "harbour_bank")["brief"]
        self.assertTrue(brief["summary"])
        self.assertTrue(brief["confirmed_by"])
        self.assertIn("12,000", " ".join(brief["deliverables"]))

    def test_override_is_shown_as_an_override(self):
        real = deal_stage.load_profile

        def with_override(slug):
            p = dict(real(slug))
            p["stage_override"] = {"stage": "shortlisted", "set_by": "Lina", "reason": "CRM says shortlisted"}
            return p
        with mock.patch.object(deal_stage, "load_profile", with_override):
            s = deal_stage.deal_stage(self.conn, "harbour_bank")
        self.assertEqual((s["current"], s["basis"]), ("shortlisted", "override"))

    def test_stage_and_brief_change_no_finding(self):
        before = json.dumps(workspace.register(self.conn, "harbour_bank"), sort_keys=True, default=str)
        workspace.overview(self.conn, "harbour_bank")
        after = json.dumps(workspace.register(self.conn, "harbour_bank"), sort_keys=True, default=str)
        self.assertEqual(before, after)

    def test_user_deals_never_read_a_profile_file(self):
        self.assertEqual(deal_stage.load_profile("u_0123456789abcdef"), {})


if __name__ == "__main__":
    unittest.main()
