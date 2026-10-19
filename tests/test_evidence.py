"""Evidence-first screens (17 Oct): each gap carries the code-verified parts of its stored claim, read only.

The contract wording behind a conflict, the phrases searched for and not found, the pricing-note line relied on, and the
catalogue limit's number. Quotes are labelled with the plain document name, never a file name or key.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import handover
import workspace
from test_ledger_v2 import V2Case


class TestEvidence(V2Case):
    def issues(self, slug):
        return [i for c in workspace.overview(self.conn, slug)["commitments"] for i in c["issues"]]

    def test_conflicts_carry_the_contract_wording_and_gaps_the_searched_phrases(self):
        issues = self.issues("harbour_bank")
        conflict = next(i for i in issues if i["finding"] == "Contract says something different")
        self.assertTrue(conflict["evidence"]["contract_quote"]["quote"])
        self.assertNotRegex(conflict["evidence"]["contract_quote"]["source"], r"HB-\d|\.md")
        gap = next(i for i in issues if i["finding"] == "Missing from contract")
        self.assertTrue(gap["evidence"]["missing_phrases"])

    def test_over_limit_carries_the_catalogue_number(self):
        over = [i for i in self.issues("harbour_bank") if i["evidence"].get("limit_name")]
        self.assertTrue(over)
        self.assertEqual(over[0]["evidence"]["limit_value"], 25000)

    def test_the_handover_snapshot_carries_quotes_and_evidence(self):
        snap = handover.build_snapshot(self.conn, "harbour_bank", "Sam")
        item = snap["open_items"][0]
        self.assertTrue(item["quotes"] and item["quotes"][0]["quote"])
        self.assertIn("evidence", item["findings"][0])


if __name__ == "__main__":
    unittest.main()
