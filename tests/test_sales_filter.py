"""Unit tests for the sales-housekeeping filter. Pure functions; labels are never read here."""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
import sales_filter
import terms

VOCAB = terms.build_vocabulary(json.loads((config.DATA_DIR / "catalogue.json").read_text(encoding="utf-8")))
REAL_RESULTS = config.RESULTS_DIR


def run_statements(slug):
    run = json.loads((REAL_RESULTS / config.LEDGER_IMPORT_RUN_FILES[slug]).read_text(encoding="utf-8"))
    return {s["statement_id"]: s["quote"] for d in run["documents"] for s in d["statements"]}


def decide(quote):
    return sales_filter.classify(quote, VOCAB)


class TestRules(unittest.TestCase):
    def test_each_rule_drops_a_sales_statement_with_no_material_term(self):
        for rule, quote in (
            ("sales_next_call", "I'll bring our team to the next call."),
            ("sales_rfp_or_proposal_response", "We'll respond to your RFP within the window and follow with a proposal."),
            ("sales_draft_sow_to_follow", "A draft Statement of Work will follow."),
            ("sales_walkthrough", "Priya can walk your architects through the options after this call."),
            ("sales_security_pack", "We'll send our security pack by Friday."),
            ("sales_methodology", "Elva follows a phased methodology: discovery, configuration and testing."),
        ):
            d = decide(quote)
            self.assertFalse(d.kept, quote)
            self.assertEqual(d.rule, rule, quote)
            self.assertIn(rule, d.matched_rules)

    def test_a_sales_phrase_with_a_material_term_is_kept(self):
        for quote in (
            "We'll walk your architects through real-time Polygon screening after this call.",   # network / mode / capability
            "We'll send our security pack on 3 October 2026.",                                   # a date
            "We'll respond to your RFP for the payout ledger connector within the window.",     # a capability
            "We'll walk you through the plan before we go live.",                                # go_live
            "We'll hold the next call with up to 5,000 payouts per day in scope.",              # a quantity
        ):
            d = decide(quote)
            self.assertTrue(d.kept, quote)
            self.assertIsNone(d.rule)
            self.assertTrue(d.matched_rules, quote)
            self.assertTrue(d.material_terms, quote)

    def test_absence_of_terms_alone_never_drops_a_statement(self):
        for quote in (
            "The parties will hold a weekly project status meeting during implementation.",
            "We'll have a very responsive team.",
            "Screening will be available.",
        ):
            d = decide(quote)
            self.assertTrue(d.kept, quote)
            self.assertEqual(d.matched_rules, (), quote)

    def test_classify_is_deterministic(self):
        quote = "We'll send our security pack by Friday."
        self.assertEqual(decide(quote), decide(quote))


class TestFrozenRuns(unittest.TestCase):
    """The imported run files: which statements the filter drops, and that the weekly status meeting is kept."""

    def dropped(self, slug):
        return {k: decide(q).rule for k, q in run_statements(slug).items() if not decide(q).kept}

    def test_harbour_bank_drops_exactly_the_five_sales_process_statements(self):
        self.assertEqual(self.dropped("harbour_bank"), {
            "HB-01-S02": "sales_next_call",
            "HB-01-S04": "sales_rfp_or_proposal_response",
            "HB-02-S02": "sales_walkthrough",
            "HB-03-S02": "sales_methodology",
            "HB-04-S06": "sales_draft_sow_to_follow",
        })

    def test_the_weekly_project_status_meeting_is_kept(self):
        quote = run_statements("harbour_bank")["HB-06-S03"]
        self.assertIn("weekly project status meeting", quote)
        d = decide(quote)
        self.assertTrue(d.kept)
        self.assertEqual(d.matched_rules, ())

    def test_hard_cases_drops_only_the_security_pack_statement(self):
        self.assertEqual(self.dropped("hard_cases"), {"KR-01-S02": "sales_security_pack"})


if __name__ == "__main__":
    unittest.main()
