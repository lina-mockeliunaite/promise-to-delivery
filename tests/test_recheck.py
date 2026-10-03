"""Tests for fixes and recheck: the five resolution scenarios, the unchanged-input rerun, the cache and the guards.

A scripted fake client stands in for the model (the revised SOW in S2 and S3 needs one extraction). Ledgers are built
in temporary files from the development deals' documents and pinned run files; workspace/ledger.sqlite is never
touched. Nothing under data/coral_pay/ is read.
"""

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
import extraction_cache
import ledger_fixes
import recheck
import scenarios

SOW2 = {"statements": [
    {"quote": "The payout ledger connector will handle up to 12,000 payouts per day at launch.", "speaker": "x", "language": "firm"},
    {"quote": "Provider will provide NUSD wallet screening for HarbourPay Global payouts on Ethereum and Polygon through Elva's"
              " pre-built connector to Customer's configured blockchain analytics service, in accordance with the Wallet"
              " Screening Specification in Annex A.", "speaker": "x", "language": "firm"},
    {"quote": "The parties will hold a weekly project status meeting during implementation.", "speaker": "x", "language": "firm"},
    {"quote": "A.1 Ethereum: each recipient wallet is screened through the analytics integration in real time before the"
              " payout is released.", "speaker": "x", "language": "firm"},
    {"quote": "A.2 Polygon: each recipient wallet is screened through the analytics integration in real time before the"
              " payout is released.", "speaker": "x", "language": "firm"},
]}


class FakeExtractor:
    def __init__(self, payload=SOW2):
        self.calls, self.payload, self.messages = 0, payload, self

    def create(self, **kwargs):
        self.calls += 1
        return NS(content=[NS(type="text", text=json.dumps(self.payload))], stop_reason="end_turn",
                  usage=NS(input_tokens=1000, output_tokens=300, output_tokens_details=None))


class NoModel:
    """Any model call fails the test."""
    messages = property(lambda self: (_ for _ in ()).throw(AssertionError("model called")))


class RecheckCase(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(config, "LEDGER_DEALS", ["harbour_bank", "hard_cases"])
        patcher.start()
        self.addCleanup(patcher.stop)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.work = Path(tmp.name)
        self.conn = scenarios.build_fresh(self.work / "ledger.sqlite")
        self.addCleanup(self.conn.close)

    def states(self, slug="harbour_bank"):
        return recheck.status_by_name(self.conn, slug)

    def polygon_rt(self, slug="harbour_bank"):
        return next(v for k, v in self.states(slug).items() if "Polygon, real time" in k)

    def fix(self, issues, version_id, route="allowed_exception", slug="harbour_bank"):
        fid = ledger_fixes.create_fix(self.conn, slug, route, "Product", "test", scenarios._issue_ids(self.conn, slug, issues),
                                      [(version_id, "whole document", None)])
        ledger_fixes.approve_fix(self.conn, fid, "Tester")
        return fid

    def add(self, source, file, slug="harbour_bank"):
        return ledger_fixes.add_source_version(self.conn, slug, source, config.scenario_path(file).read_text(encoding="utf-8"), file)


class TestScenarios(unittest.TestCase):
    def test_all_five_scenarios_and_the_control_behave_as_expected(self):
        fake = FakeExtractor()
        with mock.patch.object(config, "LEDGER_DEALS", ["harbour_bank", "hard_cases"]):
            report = scenarios.run_all(fake)
        self.assertTrue(report["control_unchanged_input_rerun"]["passed"])
        self.assertEqual((report["passed"], report["of"]), (5, 5), [r["problems"] for r in report["scenarios"]])
        self.assertEqual(fake.calls, 2)  # the revised SOW, once each in S2 and S3 (separate fresh ledgers)


class TestRecheckRules(RecheckCase):
    def test_recording_a_fix_closes_nothing_until_a_recheck(self):
        vid = self.add("HB-05", "HB-05_v2_named_exception.md")
        self.fix([{"commitment": "Polygon, real time", "type": "approval"}], vid)
        self.assertEqual(self.polygon_rt()[1]["approval/authorisation"], "Needs action")
        recheck.recheck(self.conn, "harbour_bank", self.conn.execute("SELECT MAX(id) FROM fixes").fetchone()[0], NoModel())
        self.assertEqual(self.polygon_rt()[1]["approval/authorisation"], "Resolved")

    def test_an_unchanged_input_rerun_makes_no_model_call_and_changes_no_state(self):
        before = self.states()
        result = recheck.recheck(self.conn, "harbour_bank", None, NoModel())
        self.assertEqual((result["run_kind"], result["model_calls"]), ("unchanged_input_rerun", 0))
        self.assertEqual(self.states(), before)

    def test_only_the_changed_document_is_extracted_and_an_identical_version_hits_the_cache(self):
        fake = FakeExtractor()
        vid = self.add("HB-06", "HB-06_v2_annex_aligned.md")
        fid = self.fix([{"commitment": "Polygon, real time", "type": "contract_gap"}], vid, "align_documents")
        first = recheck.recheck(self.conn, "harbour_bank", fid, fake)
        self.assertEqual((first["model_calls"], fake.calls), (1, 1))
        outcomes = dict(self.conn.execute("SELECT cache_outcome, COUNT(*) FROM review_sources WHERE review_id = ?"
                                          " GROUP BY cache_outcome", (first["review_id"],)).fetchall())
        self.assertEqual(outcomes, {"imported": 5, "miss_called": 1, "not_extracted": 2})
        self.add("HB-06", "HB-06_v2_annex_aligned.md")  # same text again, as version 3
        second = recheck.recheck(self.conn, "harbour_bank", None, NoModel())
        self.assertEqual(second["model_calls"], 0)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM review_sources WHERE review_id = ? AND cache_outcome = 'hit'",
                                           (second["review_id"],)).fetchone()[0], 1)

    def test_a_cache_key_change_re_extracts(self):
        fields = extraction_cache.key_fields("a" * 64, "draft_sow")
        other = dict(fields, max_tokens=fields["max_tokens"] + 1)
        self.assertNotEqual(extraction_cache.key_sha256(fields), extraction_cache.key_sha256(other))
        self.assertNotEqual(extraction_cache.key_sha256(fields),
                            extraction_cache.key_sha256(dict(fields, doc_type="proposal")))

    def test_excluding_the_approval_source_reopens_a_resolved_issue(self):
        vid = self.add("HB-05", "HB-05_v2_named_exception.md")
        fid = self.fix([{"commitment": "Polygon, real time", "type": "approval"}], vid)
        recheck.recheck(self.conn, "harbour_bank", fid, NoModel())
        self.assertEqual(self.polygon_rt()[1]["approval/authorisation"], "Resolved")
        self.conn.execute("UPDATE source_versions SET included = 0 WHERE id = ?", (vid,))
        self.conn.commit()
        self.assertEqual(self.polygon_rt()[1]["approval/authorisation"], "Needs evidence")  # before any recheck

    def test_an_absolute_limit_is_never_closed_by_an_allowed_exception(self):
        vid = self.add("KR-05", "KR-05_v2_attempted_exception.md", slug="hard_cases")
        fid = self.fix([{"commitment": "Arbitrum, real time", "type": "approval"}], vid, slug="hard_cases")
        recheck.recheck(self.conn, "hard_cases", fid, NoModel())
        issues = next(v for k, v in self.states("hard_cases").items() if "Arbitrum, real time" in k)[1]
        self.assertEqual(issues["approval/authorisation"], "Needs action")
        iid = scenarios._issue_ids(self.conn, "hard_cases", [{"commitment": "Arbitrum, real time", "type": "approval"}])[0]
        review = self.conn.execute("SELECT MAX(id) FROM reviews").fetchone()[0]
        with self.assertRaises(sqlite3.IntegrityError):  # the database refuses it too
            self.conn.execute("INSERT INTO closure_checks (issue_id, review_id, check_kind, outcome, evidence_checked, reason,"
                              " fix_id) VALUES (?, ?, 'recheck', 'met', ?, 'forced', ?)",
                              (iid, review + 0, json.dumps([{"source_version_id": vid}]), fid))

    def test_an_issue_the_rules_no_longer_raise_stays_open_without_closing_evidence(self):
        """Simulates an issue another checker raised: the rules never raise it, so only evidence can close it."""
        cid = self.conn.execute("SELECT commitment_id FROM commitment_assessments WHERE name LIKE '%Ethereum, real time%'"
                                " ORDER BY id DESC LIMIT 1").fetchone()[0]
        review = self.conn.execute("SELECT MAX(review_id) FROM commitment_assessments").fetchone()[0]
        iid = self.conn.execute(
            "INSERT INTO issues (commitment_id, issue_type, subject_key, owner_function, raised_review_id, raised_by,"
            " closure_criteria, criteria_version) VALUES (?, 'approval', 'agent:extra', 'Product', ?, 'agent', '{}', 1)",
            (cid, review)).lastrowid
        self.conn.execute("INSERT INTO closure_checks (issue_id, review_id, check_kind, outcome, evidence_checked, reason,"
                          " unmet) VALUES (?, ?, 'raised', 'open_action', '[]', 'agent', '[]')", (iid, review))
        self.conn.commit()
        recheck.recheck(self.conn, "harbour_bank", None, NoModel())
        latest = self.conn.execute("SELECT outcome, re_raised FROM closure_checks WHERE issue_id = ? ORDER BY id DESC LIMIT 1",
                                   (iid,)).fetchone()
        self.assertEqual(latest, ("open_action", 0))

    def test_a_recheck_needs_an_approved_fix_and_a_failed_extraction_writes_nothing(self):
        vid = self.add("HB-06", "HB-06_v2_annex_aligned.md")
        fid = ledger_fixes.create_fix(self.conn, "harbour_bank", "align_documents", "Commercial", "draft only",
                                      scenarios._issue_ids(self.conn, "harbour_bank",
                                                           [{"commitment": "Polygon, real time", "type": "contract_gap"}]),
                                      [(vid, "whole document", None)])
        with self.assertRaises(recheck.RecheckError):
            recheck.recheck(self.conn, "harbour_bank", fid, FakeExtractor())
        ledger_fixes.approve_fix(self.conn, fid, "Tester")
        reviews = self.conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
        with self.assertRaises(extraction_cache.ExtractionFailed):
            recheck.recheck(self.conn, "harbour_bank", fid, None)  # the revised SOW needs a model and none is given
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0], reviews)

    def test_approved_fixes_are_immutable(self):
        vid = self.add("HB-05", "HB-05_v2_named_exception.md")
        fid = self.fix([{"commitment": "Polygon, real time", "type": "approval"}], vid)
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("UPDATE fixes SET rationale = 'changed' WHERE id = ?", (fid,))

    def test_a_ledger_deal_guard_applies_to_fixes(self):
        with self.assertRaises(Exception):
            ledger_fixes.add_source_version(self.conn, "coral_pay", "CP-01", "x", "x.md")


if __name__ == "__main__":
    unittest.main()
