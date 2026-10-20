"""Positioning pass (20 Oct): the owner-confirmed scope line and the check-coverage count, both read-only.

Run against a ledger rebuilt from the saved v2 output (no model call). The scope line is shown only for a deal whose profile
has one; the count is how many proposed findings the code rejected in the latest v2 review, and it is stored in new
handover snapshots (additive) but never changes a finding, a count or a verdict."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import handover
import ledger
import ledger_fixes
import reset_demo
import workspace


class TestPositioningFields(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        db = Path(cls.tmp.name) / "ledger.sqlite"
        reset_demo.reset(db_path=db)
        cls.conn = ledger.connect(db)

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        cls.tmp.cleanup()

    def test_the_scope_line_is_the_owner_confirmed_one_and_absent_elsewhere(self):
        rows = {r["deal"]: r for r in handover.deal_rows(self.conn, workspace.deal_list(self.conn))}
        self.assertEqual(rows["alder_bank"]["scope"], "Scam protection for outbound instant payments")
        for slug in rows:
            if slug != "alder_bank":
                self.assertIsNone(rows[slug]["scope"], slug)

    def test_the_coverage_count_is_the_stored_rejected_findings(self):
        self.assertEqual(workspace.overview(self.conn, "alder_bank")["check_coverage"], {"rejected": 1})
        self.assertEqual(workspace.overview(self.conn, "harbour_bank")["check_coverage"], {"rejected": 0})

    def test_the_count_changes_no_finding_count_or_verdict(self):
        before = workspace.overview(self.conn, "alder_bank")
        self.assertEqual(before["counts"], workspace.register(self.conn, "alder_bank")["counts"])
        self.assertEqual(before["freshness"], workspace.register(self.conn, "alder_bank")["freshness"])

    def test_a_deal_without_a_v2_review_has_no_count(self):
        did = ledger_fixes.deal_id(self.conn, "alder_bank")
        self.assertIsNone(workspace.rejected_count(self.conn, 10**6))
        self.assertEqual(workspace.rejected_count(self.conn, did), 1)

    def test_new_snapshots_store_the_count_and_older_ones_simply_lack_it(self):
        snap = handover.build_snapshot(self.conn, "alder_bank", "Priya Nair")
        self.assertEqual(snap["check_coverage"], {"rejected": 1})
        json.dumps(snap)  # still plain stored JSON
        old = {k: v for k, v in snap.items() if k != "check_coverage"}
        self.assertNotIn("check_coverage", old)


if __name__ == "__main__":
    unittest.main()
