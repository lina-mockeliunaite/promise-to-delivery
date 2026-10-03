"""Tests for the grouping score.

Pure matching and must-hold logic is tested on small synthetic inputs, including negative controls that make each
must-hold fail. The integration tests score a consolidated temporary ledger (built as in test_ledger_consolidate.py)
against the real development labels, read-only. Nothing here touches workspace/ledger.sqlite, results/ or the real
coral_pay path.
"""

import ast
import contextlib
import copy
import io
import json
import shutil
import sqlite3
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
import ledger_consolidate
import ledger_import
import score_grouping as sg
from test_ledger_consolidate import ConsolidateCase
from test_ledger_import import DEALS, DECOY, REAL_DATA, REAL_RESULTS

fs = frozenset


class TestMatchGroups(unittest.TestCase):
    def test_a_perfect_match(self):
        predicted = {"P1": fs({"a", "b"}), "P2": fs({"c"})}
        labelled = {"L1": fs({"a", "b"}), "L2": fs({"c"})}
        self.assertEqual(sg.match_groups(predicted, labelled), {"P1": "L1", "P2": "L2"})

    def test_matching_is_one_to_one_so_fragments_cannot_all_take_one_label(self):
        predicted = {"P1": fs({"a"}), "P2": fs({"b"}), "P3": fs({"c"})}
        labelled = {"L1": fs({"a", "b", "c"})}
        mapping = sg.match_groups(predicted, labelled)
        self.assertEqual(len(mapping), 1)
        self.assertEqual(set(mapping.values()), {"L1"})

    def test_the_best_overlap_wins(self):
        predicted = {"P1": fs({"a", "b", "c"}), "P2": fs({"c"})}
        labelled = {"L1": fs({"a", "b", "c"})}
        self.assertEqual(sg.match_groups(predicted, labelled), {"P1": "L1"})

    def test_on_equal_overlap_a_complete_group_beats_an_incomplete_one(self):
        predicted = {"P1": fs({"a"}), "P2": fs({"b"})}
        labelled = {"L1": fs({"a", "b"})}
        self.assertEqual(sg.match_groups(predicted, labelled, incomplete=fs({"P1"})), {"P2": "L1"})
        self.assertEqual(sg.match_groups(predicted, labelled, incomplete=fs({"P2"})), {"P1": "L1"})

    def test_then_the_lower_predicted_id_then_the_lower_labelled_id(self):
        self.assertEqual(sg.match_groups({"P1": fs({"a"}), "P2": fs({"b"})}, {"L1": fs({"a", "b"})}), {"P1": "L1"})
        self.assertEqual(sg.match_groups({"P1": fs({"a", "b"})}, {"L1": fs({"a"}), "L2": fs({"b"})}), {"P1": "L1"})

    def test_a_statement_in_two_commitments_pairs_each_group_with_its_own_label(self):
        predicted = {"P1": fs({"s", "x"}), "P2": fs({"s", "y"})}
        labelled = {"L1": fs({"s", "x"}), "L2": fs({"s", "y"})}
        self.assertEqual(sg.match_groups(predicted, labelled), {"P1": "L1", "P2": "L2"})

    def test_groups_that_share_nothing_never_pair_and_empty_inputs_are_fine(self):
        self.assertEqual(sg.match_groups({"P1": fs({"a"})}, {"L1": fs({"b"})}), {})
        self.assertEqual(sg.match_groups({}, {}), {})
        self.assertEqual(sg.match_groups({"P1": fs({"a"})}, {}), {})

    def test_matching_is_deterministic(self):
        predicted = {f"P{i}": fs({f"s{i}", "shared"}) for i in range(1, 6)}
        labelled = {"L1": fs({"shared", "s1"}), "L2": fs({"shared", "s2"})}
        self.assertEqual(sg.match_groups(predicted, labelled), sg.match_groups(dict(reversed(list(predicted.items()))), labelled))


class TestScoreStatements(unittest.TestCase):
    GROUPS = {
        "P1": {"terms_incomplete": False, "missing": []},
        "P2": {"terms_incomplete": True, "missing": ["mode"]},
        "P3": {"terms_incomplete": False, "missing": []},
    }

    def info(self, key="k", kept=1, rule=None):
        return {"ledger_key": key, "kept": kept, "filter_rule": rule}

    def score(self, label_sets, predicted_of, mapping, stmt_info):
        return {r["label_statement"]: r for r in sg.score_statements(label_sets, predicted_of, mapping, stmt_info, self.GROUPS)}

    def test_exact_when_the_matched_groups_equal_the_labelled_commitments(self):
        r = self.score({"S1": {"L1", "L2"}}, {"S1": {"P1", "P3"}}, {"P1": "L1", "P3": "L2"}, {"S1": self.info()})
        self.assertTrue(r["S1"]["exact"])
        self.assertEqual(r["S1"]["reasons"], [])

    def test_an_unmatched_predicted_group_is_a_mismatch_with_its_incomplete_terms_named(self):
        r = self.score({"S1": {"L1"}}, {"S1": {"P2"}}, {}, {"S1": self.info()})["S1"]
        self.assertFalse(r["exact"])
        self.assertTrue(any("terms incomplete: mode" in x and "unmatched predicted group" in x for x in r["reasons"]))
        self.assertTrue(any("labelled L1 has no predicted counterpart" in x for x in r["reasons"]))

    def test_a_group_matched_to_another_label_is_a_mismatch(self):
        r = self.score({"S1": {"L1"}}, {"S1": {"P1"}}, {"P1": "L2"}, {"S1": self.info()})["S1"]
        self.assertFalse(r["exact"])
        self.assertTrue(any("matched to labelled L2, which this statement does not belong to" in x for x in r["reasons"]))

    def test_a_missing_membership_is_a_mismatch(self):
        r = self.score({"S1": {"L1", "L2"}}, {"S1": {"P1"}}, {"P1": "L1", "P3": "L2"}, {"S1": self.info()})["S1"]
        self.assertFalse(r["exact"])
        self.assertTrue(any("labelled L2 is matched to predicted P3, which does not contain this statement" in x for x in r["reasons"]))

    def test_extraction_misses_and_dropped_statements_have_their_own_reasons(self):
        r = self.score({"S1": {"L1"}, "S2": {"L1"}}, {}, {}, {
            "S1": self.info(key=None, kept=None), "S2": self.info(key="x", kept=0, rule="sales_next_call")})
        self.assertIn("extraction miss", r["S1"]["reasons"][0])
        self.assertIn("dropped by the sales filter (sales_next_call)", r["S2"]["reasons"][0])


class TestGroupReport(unittest.TestCase):
    def test_notes_compare_a_group_only_with_its_partner(self):
        predicted = {"P1": fs({"a", "b", "z"}), "P2": fs({"c"})}
        labelled = {"L1": fs({"a", "b", "c"})}
        groups = {"P1": {"name": "one", "terms_incomplete": False, "missing": []},
                  "P2": {"name": "two", "terms_incomplete": True, "missing": ["mode"]}}
        mapping = sg.match_groups(predicted, labelled, fs({"P2"}))
        report = sg.group_report(predicted, labelled, mapping, groups, {"L1": "label one"})
        [l] = report["labelled_commitments"]
        self.assertFalse(l["exact_membership"])
        self.assertIn("lacks c; held by unmatched predicted P2", l["note"])
        self.assertIn("also holds ['z']", l["note"])
        p1, p2 = report["predicted_groups"]
        self.assertEqual(p1["unlabelled_members"], ["z"])
        self.assertIn("unmatched predicted group", p2["note"])

    def test_a_shared_statement_is_not_reported_as_a_merge(self):
        predicted = {"P1": fs({"s", "x"}), "P2": fs({"s", "y"})}
        labelled = {"L1": fs({"s", "x"}), "L2": fs({"s", "y"})}
        groups = {p: {"name": p, "terms_incomplete": False, "missing": []} for p in predicted}
        report = sg.group_report(predicted, labelled, sg.match_groups(predicted, labelled), groups, {})
        self.assertTrue(all(r["exact_membership"] and "note" not in r for r in report["labelled_commitments"]))
        self.assertTrue(all("note" not in r for r in report["predicted_groups"]))


def harbour_fixture():
    statements = {k: {"quote": k, "source_id": "HB", "kept": 0, "filter_rule": "r"}
                  for k in ("HB-01-S02", "HB-01-S04", "HB-02-S02", "HB-03-S02", "HB-04-S06")}
    statements.update({k: {"quote": k, "source_id": "HB", "kept": 1, "filter_rule": None}
                       for k in ("HB-01-S01", "HB-03-S01", "HB-06-S03", "HB-06-S05")})
    predicted = {"P1": fs({"HB-01-S01", "HB-03-S01"}), "P2": fs({"HB-03-S01"}), "P3": fs({"HB-06-S05"}), "P4": fs({"HB-06-S03"})}
    ledger = {
        "statements": statements,
        "groups": {p: {"terms_incomplete": False, "key": f"key-{p}"} for p in predicted},
        "member_term_keys": {p: [f"key-{p}"] * len(m) for p, m in predicted.items()},
    }
    return {
        "ledger": ledger, "predicted": predicted,
        "ledger_key": {"S01": "HB-01-S01", "S04": "HB-03-S01", "S15": "HB-06-S03", "S13": "HB-06-S05"},
        "label_sets": {"S01": {"C01"}, "S04": {"C01", "C02"}, "S15": {"C08"}, "S13": {"C03"}},
        "mapping": {"P1": "C01", "P2": "C02", "P3": "C03", "P4": "C08"},
    }


def hard_fixture():
    quote = "up to thirty thousand payouts"
    statements = {k: {"quote": quote, "source_id": "KR", "kept": 1, "filter_rule": None} for k in ("KR-02-S02", "KR-03-S01")}
    predicted = {"P1": fs({"KR-02-S02", "KR-03-S01"})}
    return {
        "ledger": {"statements": statements, "groups": {"P1": {"terms_incomplete": False, "key": "k"}},
                   "member_term_keys": {"P1": ["k", "k"]}},
        "predicted": predicted, "ledger_key": {"K04": "KR-02-S02", "K08": "KR-03-S01"},
        "label_sets": {"K04": {"KC4"}, "K08": {"KC4"}}, "mapping": {"P1": "KC4"},
        "run_quotes": {"KR-02-S02": quote, "KR-03-S01": quote},
    }


def check(slug, fx, run_quotes=None):
    results = sg.must_holds(slug, fx["ledger"], fx["ledger_key"], fx["label_sets"], fx["predicted"], fx["mapping"],
                            run_quotes if run_quotes is not None else fx.get("run_quotes", {}))
    return {r["must_hold"]: r["passed"] for r in results}


class TestMustHolds(unittest.TestCase):
    def failing(self, slug, fx, **kwargs):
        return sorted(name for name, passed in check(slug, fx, **kwargs).items() if not passed)

    def test_the_baselines_pass_every_must_hold(self):
        self.assertEqual(self.failing("harbour_bank", harbour_fixture()), [])
        self.assertEqual(self.failing("hard_cases", hard_fixture()), [])

    def test_a_labelled_statement_dropped_fails(self):
        fx = harbour_fixture()
        fx["ledger"]["statements"]["HB-06-S03"]["kept"] = 0
        failing = self.failing("harbour_bank", fx)
        self.assertIn("no labelled statement is dropped by the filter", failing)
        self.assertIn("S15 (weekly project status meeting) is kept and linked", failing)
        self.assertIn("exactly the five sales-process statements are dropped", failing)

    def test_a_wrong_number_of_dropped_statements_fails(self):
        fx = harbour_fixture()
        fx["ledger"]["statements"]["HB-01-S01"]["kept"] = 0
        self.assertIn("exactly the five sales-process statements are dropped", self.failing("harbour_bank", fx))

    def test_merging_c01_and_c03_fails(self):
        fx = harbour_fixture()
        fx["predicted"]["P1"] = fx["predicted"]["P1"] | fx["predicted"]["P3"]
        self.assertIn("C01 (real-time Polygon) and C03 (hourly-batch Polygon) are never merged", self.failing("harbour_bank", fx))

    def test_s04_missing_a_group_fails(self):
        fx = harbour_fixture()
        fx["predicted"]["P2"] = fs({"HB-06-S05"})
        self.assertIn("S04 is linked to both the C01 and C02 groups", self.failing("harbour_bank", fx))

    def test_two_keys_in_one_complete_group_fails(self):
        fx = harbour_fixture()
        fx["ledger"]["member_term_keys"]["P1"] = ["key-P1", "other-key"]
        self.assertIn("differing terms are never collapsed into one commitment (every complete group has one key)",
                      self.failing("harbour_bank", fx))

    def test_one_key_shared_by_two_complete_groups_fails(self):
        fx = harbour_fixture()
        fx["ledger"]["groups"]["P2"]["key"] = "key-P1"
        fx["ledger"]["member_term_keys"]["P2"] = ["key-P1"]
        self.assertIn("differing terms are never collapsed into one commitment (every complete group has one key)",
                      self.failing("harbour_bank", fx))

    def test_k04_and_k08_in_different_groups_fails(self):
        fx = hard_fixture()
        fx["predicted"] = {"P1": fs({"KR-02-S02"}), "P2": fs({"KR-03-S01"})}
        self.assertIn("K04 (\"thirty thousand\") and K08 (\"30,000\") share one commitment", self.failing("hard_cases", fx))

    def test_a_changed_quote_or_an_unreadable_run_file_fails_the_verbatim_check(self):
        fx = hard_fixture()
        fx["ledger"]["statements"]["KR-02-S02"]["quote"] += " "
        self.assertIn("K04 and K08 quotes are stored verbatim", self.failing("hard_cases", fx))
        self.assertIn("K04 and K08 quotes are stored verbatim", self.failing("hard_cases", hard_fixture(), run_quotes={}))


class TestScorerIsIndependentOfTheRules(unittest.TestCase):
    def test_it_imports_nothing_from_the_parser_filter_or_consolidation(self):
        tree = ast.parse((Path(__file__).resolve().parents[1] / "score_grouping.py").read_text(encoding="utf-8"))
        imported = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        imported |= {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
        self.assertEqual(imported & {"terms", "sales_filter", "ledger_consolidate", "ledger_import", "ledger"}, set())


class ScoreCase(ConsolidateCase):
    """A consolidated temporary ledger, scored against the real development labels (read-only)."""

    def setUp(self):
        super().setUp()
        ledger_consolidate.consolidate_all(self.conn)
        self.conn.commit()

    def report(self):
        reader = sg.open_read_only(self.db_path)
        self.addCleanup(reader.close)
        return sg.build_report(reader, data_dir=REAL_DATA, results_dir=REAL_RESULTS)


class TestScoreTheStoredLedger(ScoreCase):
    def test_both_metrics_per_deal(self):
        report = self.report()["deals"]
        self.assertEqual(report["harbour_bank"]["metrics"], {"statements": {"exact": 15, "of": 15}, "commitments": {"exact": 8, "of": 8}})
        self.assertEqual(report["hard_cases"]["metrics"], {"statements": {"exact": 8, "of": 9}, "commitments": {"exact": 6, "of": 7}})

    def test_every_mismatch_is_listed_with_its_reasons(self):
        report = self.report()["deals"]
        miss = {slug: [s for s in d["statements"] if not s["exact"]] for slug, d in report.items()}
        self.assertEqual([s["label_statement"] for s in miss["harbour_bank"]], [])  # S11 fixed 3 Oct (Annex A)
        self.assertEqual([s["label_statement"] for s in miss["hard_cases"]], ["K01"])
        k01 = miss["hard_cases"][0]
        self.assertTrue(any("terms incomplete: mode" in r and "unmatched predicted group" in r for r in k01["reasons"]))

    def test_the_complete_fragment_takes_the_label_on_a_tie(self):
        hard = self.report()["deals"]["hard_cases"]
        self.assertEqual(hard["mapping"]["C05"], "KC1")  # Arbitrum real time (complete), not KR-01-S01's incomplete group
        self.assertEqual(hard["unmatched_predicted_groups"], ["C01"])
        self.assertEqual(hard["unmatched_labelled_commitments"], [])

    def test_every_group_on_harbour_bank_is_matched(self):
        harbour = self.report()["deals"]["harbour_bank"]
        self.assertEqual(harbour["unmatched_predicted_groups"], [])
        self.assertEqual(harbour["unmatched_labelled_commitments"], [])
        self.assertEqual(harbour["predicted_groups"], 8)

    def test_every_must_hold_passes(self):
        report = self.report()
        self.assertTrue(sg.all_passed(report))
        names = {slug: [c["must_hold"] for c in d["must_hold"]] for slug, d in report["deals"].items()}
        self.assertEqual(len(names["harbour_bank"]), 6)
        self.assertEqual(len(names["hard_cases"]), 4)

    def test_it_scores_what_is_stored_not_what_the_rules_would_produce(self):
        """Break a stored group's members in a copy of the database: the score follows the database."""
        copy_path = self.root / "tampered.sqlite"
        shutil.copyfile(self.db_path, copy_path)
        conn = sqlite3.connect(copy_path)
        conn.execute("DROP TRIGGER rsc_append_only_d")
        conn.execute("DELETE FROM review_statement_commitments WHERE statement_id IN"
                     " (SELECT id FROM statements WHERE statement_key = 'HB-04-S01')")
        conn.commit()
        conn.close()
        reader = sg.open_read_only(copy_path)
        self.addCleanup(reader.close)
        report = sg.build_report(reader, data_dir=REAL_DATA, results_dir=REAL_RESULTS)["deals"]["harbour_bank"]
        self.assertLess(report["metrics"]["statements"]["exact"], 15)

    def test_labels_are_read_through_the_deal_guard(self):
        with self.assertRaises(config.DealNotAllowed):
            sg.read_labels(DECOY, data_dir=self.data)

    def test_scoring_leaves_the_ledger_byte_identical_and_cannot_write_to_it(self):
        before = self.db_path.read_bytes()
        self.report()
        self.assertEqual(self.db_path.read_bytes(), before)
        reader = sg.open_read_only(self.db_path)
        self.addCleanup(reader.close)
        with self.assertRaises(sqlite3.OperationalError):
            reader.execute("DELETE FROM deals")

    def test_a_ledger_that_is_not_consolidated_is_refused(self):
        other = self.root / "bare.sqlite"
        ledger_import.build(other)
        reader = sg.open_read_only(other)
        self.addCleanup(reader.close)
        with self.assertRaises(sg.ScoreRefused):
            sg.build_report(reader, data_dir=REAL_DATA, results_dir=REAL_RESULTS)


class TestOutputFile(ScoreCase):
    NOW = datetime(2026, 10, 3, 12, 0, 0, tzinfo=timezone.utc)

    def test_the_report_is_written_with_both_metrics_and_provenance(self):
        report = self.report()
        path = sg.write_report(report, results_dir=self.results, now=self.NOW)
        self.assertEqual(path.name, "grouping_score_20261003T120000Z.json")
        body = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(body["timestamp_utc"], "2026-10-03T12:00:00+00:00")
        self.assertIn("complete-key group before incomplete", body["tie_break"])
        for slug in DEALS:
            deal = body["deals"][slug]
            self.assertEqual(set(deal["metrics"]), {"statements", "commitments"})
            self.assertEqual(set(deal["labels_sha256"]), {"statements", "commitments"})
            self.assertEqual(len(deal["rules_sha256"]), 1)
            self.assertTrue(deal["must_hold"] and deal["statements"] and deal["groups"])

    def test_a_second_report_never_overwrites_the_first(self):
        report = self.report()
        first = sg.write_report(report, results_dir=self.results, now=self.NOW)
        before = first.read_bytes()
        with self.assertRaises(sg.ScoreRefused):
            sg.write_report(report, results_dir=self.results, now=self.NOW)
        self.assertEqual(first.read_bytes(), before)
        later = sg.write_report(report, results_dir=self.results, now=datetime(2026, 10, 3, 12, 0, 1, tzinfo=timezone.utc))
        self.assertNotEqual(later, first)
        self.assertEqual(first.read_bytes(), before)


class TestCli(ScoreCase):
    def setUp(self):
        super().setUp()
        self.conn.close()
        for slug in DEALS:  # the CLI reads labels through config.DATA_DIR, which these tests point at a temp folder
            shutil.copytree(REAL_DATA / slug / "labels", self.data / slug / "labels")
        patcher = mock.patch.object(config, "LEDGER_DB_PATH", self.db_path)
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_main(self, argv=()):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = sg.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def written(self):
        return sorted(p.name for p in self.results.glob("grouping_score_*.json"))

    def test_it_scores_prints_both_metrics_and_writes_one_file(self):
        code, out, _ = self.run_main()
        self.assertEqual(code, 0)
        self.assertIn("statements 15 of 15 exact; commitments 8 of 8 exact", out)
        self.assertIn("statements 8 of 9 exact; commitments 6 of 7 exact", out)
        self.assertIn("MISMATCH K01", out)
        self.assertEqual(len(self.written()), 1)

    def test_a_failed_must_hold_exits_1_and_still_writes_the_report(self):
        failing = [{"must_hold": "forced", "passed": False, "detail": "x"}]
        with mock.patch.object(sg, "must_holds", return_value=failing):
            code, out, _ = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("[FAIL] forced", out)
        self.assertEqual(len(self.written()), 1)

    def test_a_missing_or_unconsolidated_ledger_is_refused_without_writing(self):
        with mock.patch.object(config, "LEDGER_DB_PATH", self.root / "nowhere.sqlite"):
            self.assertEqual(self.run_main()[0], 2)
        bare = self.root / "bare.sqlite"
        ledger_import.build(bare)
        with mock.patch.object(config, "LEDGER_DB_PATH", bare):
            code, _, err = self.run_main()
        self.assertEqual(code, 2)
        self.assertIn("no consolidated review", err)
        self.assertEqual(self.written(), [])

    def test_arguments_are_refused(self):
        self.assertEqual(self.run_main(["--bogus"])[0], 2)


if __name__ == "__main__":
    unittest.main()
