"""Tests for score_rules.py: scores a temporary ledger, built and assessed as in test_ledger_rules.py, against the
real development labels (read through the deal guard). Never touches workspace/ledger.sqlite."""

import contextlib
import io
import shutil
import sqlite3
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
import ledger_consolidate
import score_grouping as sg
import score_rules
from test_ledger_consolidate import ConsolidateCase
from test_ledger_import import DECOY, REAL_DATA, REAL_RESULTS


class ScoreRulesCase(ConsolidateCase):
    def setUp(self):
        super().setUp()
        ledger_consolidate.consolidate_all(self.conn, assess=True)
        self.conn.commit()

    def report(self, path=None):
        reader = sg.open_read_only(path or self.db_path)
        self.addCleanup(reader.close)
        return score_rules.build_report(reader, data_dir=REAL_DATA, results_dir=REAL_RESULTS)


class TestScoreRules(ScoreRulesCase):
    def test_development_scores(self):
        deals = self.report()["deals"]
        hb, hc = deals["harbour_bank"]["metrics"], deals["hard_cases"]["metrics"]
        self.assertEqual((hb["authorisation"], hb["presence"], hb["issue_sets"]),
                         ({"exact": 8, "of": 8}, {"exact": 8, "of": 8}, {"exact": 8, "of": 8}))
        self.assertEqual(hb["issues"], {"true_positive": 8, "false_positive": 0, "false_negative": 0})
        self.assertEqual(hb["false_flags_on_clean_commitments"], 0)
        self.assertEqual(hb["commitments_with_issues_reaching_review"], {"found": 4, "of": 4})
        self.assertEqual(hc["issues"], {"true_positive": 6, "false_positive": 0, "false_negative": 0})
        self.assertEqual(hc["absolute_limit"], {"exact": 7, "of": 7})

    def test_the_unmatched_arbitrum_fragment_is_reported_not_hidden(self):
        extra = self.report()["deals"]["hard_cases"]["issues_on_unmatched_predicted_groups"]
        self.assertEqual(len(extra), 1)
        self.assertIn(["approval", "authorisation", 1], extra[0]["issues"])

    def test_it_scores_what_is_stored(self):
        """Negative control: tamper with a stored verdict in a copy; the score must drop."""
        copy_path = self.root / "tampered.sqlite"
        shutil.copyfile(self.db_path, copy_path)
        conn = sqlite3.connect(copy_path)
        conn.execute("DROP TRIGGER issues_no_delete")
        conn.execute("DROP TRIGGER closure_checks_append_only_d")
        conn.execute("DELETE FROM closure_checks WHERE issue_id IN (SELECT id FROM issues WHERE issue_type = 'conflicting_terms')")
        conn.execute("DELETE FROM issues WHERE issue_type = 'conflicting_terms'")
        conn.commit()
        conn.close()
        hb = self.report(copy_path)["deals"]["harbour_bank"]["metrics"]
        self.assertEqual(hb["issues"]["false_negative"], 1)

    def test_labels_are_read_through_the_deal_guard(self):
        with self.assertRaises(config.DealNotAllowed):
            sg.read_labels(DECOY, data_dir=self.data)

    def test_the_cli_writes_one_file_and_never_overwrites(self):
        with mock.patch.object(config, "LEDGER_DB_PATH", self.db_path), \
                mock.patch.object(config, "DATA_DIR", REAL_DATA), mock.patch.object(config, "RESULTS_DIR", REAL_RESULTS):
            with mock.patch.object(score_rules, "write_report", lambda report: self.root / "x.json"):
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    code = score_rules.main([])
        self.assertEqual(code, 0)
        self.assertIn("harbour_bank: authorisation 8 of 8", out.getvalue())
        now = __import__("datetime").datetime(2026, 10, 3, tzinfo=__import__("datetime").timezone.utc)
        score_rules.write_report({"deals": {}}, results_dir=self.root, now=now)
        with self.assertRaises(score_rules.ScoreRefused):
            score_rules.write_report({"deals": {}}, results_dir=self.root, now=now)

    def test_an_unassessed_ledger_is_refused(self):
        other = ConsolidateCase("run")
        other.setUp()
        self.addCleanup(other.doCleanups)
        ledger_consolidate.consolidate_all(other.conn)  # consolidation only, no rules
        other.conn.commit()
        reader = sg.open_read_only(other.db_path)
        self.addCleanup(reader.close)
        with self.assertRaises(score_rules.ScoreRefused):
            score_rules.build_report(reader, data_dir=REAL_DATA, results_dir=REAL_RESULTS)


if __name__ == "__main__":
    unittest.main()
