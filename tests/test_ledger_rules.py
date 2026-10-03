"""Integration tests: the rules run inside the consolidating review on the development deals, in one transaction.

Built as in test_ledger_consolidate.py: byte-identical copies in a temporary folder, a temporary database and a decoy
sealed deal with a canary. Labels are not read here (score_rules.py compares with labels). Expected values are the
must-holds of docs/BRIEF_2026-10-04.md, written from the documents and the catalogue.
"""

import json
import sqlite3
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
import ledger
import ledger_consolidate
import test_ledger_consolidate as tlc
from test_ledger_consolidate import ConsolidateCase
from test_ledger_import import CANARY, assert_no_canary

# commitment name fragment -> (authorisation, contractual presence, sorted issue types)
EXPECTED = {
    "harbour_bank": {
        "Polygon, real time": ("no_approval_evidence", "absent", ["approval", "conflicting_terms", "contract_gap"]),
        "Go-live": (None, "absent", []),
        "Ethereum, real time": ("standard_authorised", "included_in_draft_contract", []),
        "12,000 payouts": ("standard_authorised", "included_in_draft_contract", []),
        "40,000 payouts": ("no_approval_evidence", "absent", ["approval", "contract_gap"]),
        "VASP counterparty": ("no_approval_evidence", "absent", ["approval", "contract_gap"]),
        "Polygon, batch": ("standard_authorised", "included_in_draft_contract", []),
        "weekly project status": ("unknown_needs_review", "included_in_draft_contract", ["insufficient_evidence"]),
    },
    "hard_cases": {
        "Arbitrum [terms incomplete": ("no_approval_evidence", "absent", ["approval", "insufficient_evidence"]),
        "Polygon, real time": (None, "absent", []),
        "Go-live": ("unknown_needs_review", "absent", ["contract_gap", "insufficient_evidence"]),
        "30,000 payouts": ("no_approval_evidence", "included_in_draft_contract", ["approval"]),
        "Arbitrum, real time": ("no_approval_evidence", "absent", ["approval", "contract_gap"]),
        "VASP counterparty": (None, "absent", []),
        "Case audit history": ("standard_authorised", "absent", ["contract_gap"]),
        "Ethereum, real time": ("standard_authorised", "included_in_draft_contract", []),
    },
}
RULE_TABLES = ("issues", "closure_checks", "reference_resolutions", "commitment_links")


class RulesCase(ConsolidateCase):
    def rows(self, slug):
        out = {}
        for cid, name, auth, presence in self.conn.execute(
            "SELECT c.id, a.name, a.authorisation, a.contractual_presence FROM commitments c"
            " JOIN commitment_assessments a ON a.commitment_id = c.id JOIN deals d ON d.id = c.deal_id WHERE d.slug = ?",
            (slug,),
        ):
            found = sorted(r[0] for r in self.conn.execute("SELECT issue_type FROM issues WHERE commitment_id = ?", (cid,)))
            out[name] = (auth, presence, found)
        return out

    def rule_counts(self):
        return {t: self.conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in RULE_TABLES}


class TestRulesOnDevelopmentDeals(RulesCase):
    def setUp(self):
        super().setUp()
        self.plans = ledger_consolidate.consolidate_all(self.conn, assess=True)

    def test_every_commitment_matches_the_must_holds(self):
        for slug, expected in EXPECTED.items():
            rows = self.rows(slug)
            self.assertEqual(len(rows), len(expected), slug)
            for fragment, want in expected.items():
                matches = [v for k, v in rows.items() if fragment in k]
                self.assertEqual(len(matches), 1, f"{slug}: {fragment!r} matched {len(matches)} commitments")
                self.assertEqual(matches[0], want, f"{slug}: {fragment}")

    def test_absolute_limits_are_marked_only_for_the_unlisted_network(self):
        rows = self.conn.execute(
            "SELECT a.name, i.absolute_limit FROM issues i JOIN commitment_assessments a ON a.commitment_id = i.commitment_id"
            " WHERE i.issue_type = 'approval'").fetchall()
        self.assertEqual(sorted(n for n, flag in rows if flag), sorted(n for n, _ in rows if "Arbitrum" in n))
        self.assertEqual(len([1 for n, flag in rows if flag]), 2)

    def test_every_issue_has_exactly_one_raised_check_from_the_same_review_and_none_is_met(self):
        rows = self.conn.execute(
            "SELECT i.id, i.issue_type, i.raised_review_id, COUNT(cc.id), MIN(cc.check_kind), MIN(cc.review_id),"
            " MIN(cc.outcome), MAX(cc.outcome) FROM issues i LEFT JOIN closure_checks cc ON cc.issue_id = i.id GROUP BY i.id"
        ).fetchall()
        self.assertEqual(len(rows), 16)
        for _, issue_type, raised_review, n, kind, review, low, high in rows:
            self.assertEqual((n, kind, review), (1, "raised", raised_review))
            want = "open_evidence" if issue_type == "insufficient_evidence" else "open_action"
            self.assertEqual((low, high), (want, want))
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM closure_checks WHERE outcome = 'met'").fetchone()[0], 0)

    def test_issue_and_commitment_states_follow_the_raised_checks(self):
        states = dict(self.conn.execute("SELECT state, COUNT(*) FROM issue_current_state GROUP BY state").fetchall())
        self.assertEqual(states, {"Needs action": 13, "Needs evidence": 3})
        harbour = dict(self.conn.execute(
            "SELECT a.name, s.status FROM commitment_status s JOIN commitment_assessments a ON a.id = s.assessment_id"
            " JOIN commitments c ON c.id = s.commitment_id JOIN deals d ON d.id = c.deal_id WHERE d.slug = 'harbour_bank'"
        ).fetchall())
        self.assertEqual(next(v for k, v in harbour.items() if "weekly" in k), "Needs evidence")
        self.assertEqual(next(v for k, v in harbour.items() if "Polygon, real time" in k), "Needs action")
        self.assertEqual(next(v for k, v in harbour.items() if "Polygon, batch" in k), "No issues raised")

    def test_no_assessment_is_left_not_assessed_and_none_is_read_as_absent_without_a_contract(self):
        self.assertEqual(self.conn.execute(
            "SELECT COUNT(*) FROM commitment_assessments WHERE authorisation = 'not_assessed'"
            " OR contractual_presence = 'not_assessed'").fetchone()[0], 0)

    def test_every_authorisation_verdict_cites_its_evidence(self):
        for auth, evidence, refs in self.conn.execute(
                "SELECT authorisation, authorisation_evidence, evidence_refs FROM commitment_assessments"):
            refs = json.loads(refs)
            if auth in ("standard_authorised", "no_approval_evidence", "exception_approved"):
                self.assertTrue(refs["catalogue"], evidence)
            if auth == "unknown_needs_review":
                self.assertTrue(evidence.startswith("Attempted match") or "depends on terms" in evidence)
            self.assertTrue(evidence)

    def test_reference_resolutions_are_recorded_per_review(self):
        rows = self.conn.execute(
            "SELECT d.slug, r.cited_label, r.status FROM reference_resolutions r JOIN reviews v ON v.id = r.review_id"
            " JOIN deals d ON d.id = v.deal_id ORDER BY r.id").fetchall()
        harbour = [(label, status) for slug, label, status in rows if slug == "harbour_bank"]
        self.assertIn(("Statement of Work dated 20 October 2026", "resolved"), harbour)
        self.assertTrue(all(status == "resolved" for _, status in harbour))
        hard = [(label, status) for slug, label, status in rows if slug == "hard_cases"]
        self.assertIn(("Schedule 2", "missing"), hard)

    def test_the_hourly_batch_commitment_is_linked_as_the_contract_side_of_real_time_polygon(self):
        rows = self.conn.execute(
            "SELECT f.name, t.name, l.link_type FROM commitment_links l"
            " JOIN commitment_assessments f ON f.commitment_id = l.from_commitment_id"
            " JOIN commitment_assessments t ON t.commitment_id = l.to_commitment_id").fetchall()
        self.assertEqual(rows, [("On-chain wallet screening integration: Polygon, batch",
                                 "On-chain wallet screening integration: Polygon, real time", "contract_side_of")])

    def test_issues_record_the_rules_hash_and_who_raised_them(self):
        hashes = {r for r in self.conn.execute("SELECT DISTINCT raised_config_sha256 || raised_by FROM issues")}
        expected = ledger_consolidate.rules_sha256((config.DATA_DIR / "catalogue.json").read_bytes())
        self.assertEqual(hashes, {(expected + "rules",)})

    def test_a_second_run_refuses_and_writes_nothing(self):
        before = self.rule_counts()
        with self.assertRaises(ledger_consolidate.ConsolidationError):
            ledger_consolidate.consolidate_all(self.conn, assess=True)
        self.assertEqual(self.rule_counts(), before)

    def test_the_canary_never_reaches_the_database(self):
        assert_no_canary(self, self.conn, self.db_path)


class TestAtomicity(RulesCase):
    def test_an_issue_is_never_written_without_its_raised_check(self):
        """Make the closure-check insert fail: the issues, and everything else in the review, roll back."""
        self.conn.execute("CREATE TRIGGER fail_checks BEFORE INSERT ON closure_checks BEGIN SELECT RAISE(ABORT, 'forced'); END")
        self.conn.commit()
        with self.assertRaises(sqlite3.DatabaseError):
            ledger_consolidate.consolidate_all(self.conn, assess=True)
        self.assertEqual(self.rule_counts(), {t: 0 for t in RULE_TABLES})
        self.assertEqual(sum(self.consolidation_counts().values()), 0)

    def test_negative_control_without_the_failure_the_same_run_writes_issues(self):
        ledger_consolidate.consolidate_all(self.conn, assess=True)
        self.assertGreater(self.rule_counts()["issues"], 0)


class TestRulesSeal(tlc.TestSeal):
    """The decoy sealed deal stays untouched when the rules run; the guard holds with ALLOWED_DEALS widened."""

    def test_the_rules_never_touch_the_decoy(self):
        with mock.patch.object(config, "ALLOWED_DEALS", config.ALLOWED_DEALS + ["coral_pay"]):
            with self.assertRaises(ledger.LedgerDealNotAllowed):
                ledger_consolidate.consolidate_review(self.conn, self.decoy_review, assess=True)
        ledger_consolidate.consolidate_all(self.conn, assess=True)
        for table in RULE_TABLES:
            self.assertNotIn(CANARY, "\n".join(str(r) for r in self.conn.execute(f"SELECT * FROM {table}")))
        self.assertEqual(self.conn.execute(
            "SELECT COUNT(*) FROM reference_resolutions WHERE review_id = ?", (self.decoy_review,)).fetchone()[0], 0)

    def test_negative_control_an_unguarded_run_would_carry_the_canary_into_the_rules_output(self):
        with mock.patch.object(config, "LEDGER_DEALS", config.LEDGER_DEALS + ["coral_pay"]):
            ledger_consolidate.consolidate_review(self.conn, self.decoy_review, assess=True)
        found = "\n".join(str(r) for t in ("commitment_assessments",) for r in self.conn.execute(f"SELECT * FROM {t}"))
        self.assertIn(CANARY, found)


if __name__ == "__main__":
    unittest.main()
