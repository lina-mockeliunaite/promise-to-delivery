"""Offline tests for regression. Synthetic labels, runs and sources only: no network, no deal files."""

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import check_quotes
import config
import evaluate
import regression

# (label id, source id, language, quote): distinct word sets so nothing matches across labels.
LABEL_ROWS = [
    ("S01", "HB-01", "exploratory", "alpha bravo charlie delta"),
    ("S04", "HB-03", "firm", "echo foxtrot golf hotel"),
    ("S08", "HB-04", "firm", "india juliet kilo lima"),
    ("S09", "HB-04", "firm", "mike november oscar papa"),
    ("S12", "HB-06", "firm", "quebec romeo sierra tango"),
    ("S13", "HB-06", "firm", "uniform victor whiskey xray"),
    ("S14", "HB-06", "firm", "yankee zulu one two"),
]
LABELS = [{"id": i, "source_id": s, "language": lang, "quote": q} for i, s, lang, q in LABEL_ROWS]
EXTRA = [f"filler{n} padding{n} words{n} here{n}" for n in range(6)]


def stmt(sid, source_id, quote, language="firm"):
    return {"statement_id": sid, "source_id": source_id, "quote": quote, "language": language}


def base_run():
    """One complete document per source; every label has an identical, correctly worded statement."""
    statements = [stmt(f"{l['source_id']}-{l['id']}", l["source_id"], l["quote"], l["language"]) for l in LABELS]
    return {"deal": "harbour_bank", "model": "m", "thinking_mode": "model_default",
            "prompt_hashes": {"system_prompt_sha256": "a" * 64},
            "documents": [{"source_id": "ALL", "status": "complete", "statements": statements}]}


def base_sources():
    text = " . ".join([l["quote"] for l in LABELS] + EXTRA + ["stray words from the excluded source"])
    return {sid: text for sid in ("HB-01", "HB-03", "HB-04", "HB-05", "HB-06", "HB-07", "HB-08")}


def results_for(run, sources=None):
    _, results = regression.run_checks(run, LABELS, sources or base_sources())
    return {r["name"]: r for r in results}


def statements(run):
    return run["documents"][0]["statements"]


class Checks(unittest.TestCase):
    def test_all_pass_on_a_clean_run(self):
        res = results_for(base_run())
        self.assertEqual([n for n, r in res.items() if not r["passed"]], [])

    def test_check_definitions_live_in_one_dict_with_six_checks(self):
        self.assertEqual(len(regression.CHECKS), 6)
        self.assertEqual(regression.CHECKS["precision_floor"]["min_precision"], 0.60)
        self.assertEqual(regression.CHECKS["excluded_sources"]["source_ids"], ["HB-05", "HB-07", "HB-08"])

    def test_missing_firm_label_fails_check_1_and_lists_it(self):
        run = base_run()
        statements(run)[:] = [s for s in statements(run) if not s["statement_id"].endswith("S04")]
        res = results_for(run)
        self.assertFalse(res["firm_labels_matched"]["passed"])
        self.assertEqual([r["label_id"] for r in res["firm_labels_matched"]["failing_rows"]], ["S04"])
        self.assertTrue(res["hedge_pair_output_firm"]["passed"])

    def test_unmatched_exploratory_label_does_not_fail_check_1(self):
        run = base_run()
        statements(run)[:] = [s for s in statements(run) if not s["statement_id"].endswith("S01")]
        self.assertTrue(results_for(run)["firm_labels_matched"]["passed"])

    def test_s08_or_s09_missing_or_not_firm_fails_check_2(self):
        run = base_run()
        for s in statements(run):
            if s["statement_id"].endswith("S08"):
                s["language"] = "conditional"
        statements(run)[:] = [s for s in statements(run) if not s["statement_id"].endswith("S09")]
        rows = results_for(run)["hedge_pair_output_firm"]["failing_rows"]
        self.assertEqual({r["label_id"]: r["problem"] for r in rows},
                         {"S08": "output language is 'conditional', need 'firm'", "S09": "not matched"})

    def test_s12_s13_s14_must_match(self):
        run = base_run()
        statements(run)[:] = [s for s in statements(run) if s["statement_id"][-3:] not in ("S12", "S14")]
        res = results_for(run)["must_match"]
        self.assertFalse(res["passed"])
        self.assertEqual([r["label_id"] for r in res["failing_rows"]], ["S12", "S14"])

    def test_invalid_quote_fails_check_4(self):
        sources = base_sources()
        sources["HB-06"] = sources["HB-06"].replace("uniform victor whiskey xray", "something else")
        res = results_for(base_run(), sources)["quotes_valid"]
        self.assertFalse(res["passed"])
        self.assertEqual([r["problem"] for r in res["failing_rows"]], ["not_found_in_source"])
        self.assertEqual(res["failing_rows"][0]["quote"], "uniform victor whiskey xray")

    def test_precision_below_floor_fails_check_5_and_lists_false_positives(self):
        run = base_run()
        statements(run).extend(stmt(f"X{n}", "HB-01", q) for n, q in enumerate(EXTRA))   # 7 TP, 6 FP: 0.538
        res = results_for(run)["precision_floor"]
        self.assertFalse(res["passed"])
        self.assertEqual(len(res["failing_rows"]), 6)

    def test_precision_just_below_floor_fails_and_just_above_passes(self):
        run = base_run()
        statements(run).extend(stmt(f"X{n}", "HB-01", q) for n, q in enumerate(EXTRA[:5]))   # 7 TP, 5 FP: 0.583 fails
        self.assertFalse(results_for(run)["precision_floor"]["passed"])
        run = base_run()
        statements(run).extend(stmt(f"X{n}", "HB-01", q) for n, q in enumerate(EXTRA[:4]))   # 7 TP, 4 FP: 0.636 passes
        self.assertTrue(results_for(run)["precision_floor"]["passed"])

    def test_statement_from_excluded_source_fails_check_6(self):
        for source in ("HB-05", "HB-07", "HB-08"):
            run = base_run()
            statements(run).append(stmt("Z1", source, "stray words from the excluded source"))
            res = results_for(run)["excluded_sources"]
            self.assertFalse(res["passed"], source)
            self.assertEqual([r["source_id"] for r in res["failing_rows"]], [source])

    def test_excluded_source_statements_in_an_incomplete_document_still_count(self):
        run = base_run()
        run["documents"].append({"source_id": "HB-05", "status": "incomplete",
                                 "statements": [stmt("Z1", "HB-05", "stray words from the excluded source")]})
        self.assertFalse(results_for(run)["excluded_sources"]["passed"])

    def test_no_statements_at_all_fails_precision_check_cleanly(self):
        run = base_run()
        statements(run).clear()
        res = results_for(run)
        self.assertFalse(res["precision_floor"]["passed"])
        self.assertIn("undefined", res["precision_floor"]["failing_rows"][0]["problem"])


class Main(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.results = Path(self.tmp.name)
        patches = [
            mock.patch.object(config, "RESULTS_DIR", self.results),
            mock.patch.object(evaluate, "load_labels", return_value=(LABELS, "ab" * 32)),
            mock.patch.object(check_quotes, "load_sources", return_value=base_sources()),
            mock.patch("sys.stdout"),
        ]
        self.load_labels = patches[1].start()
        for p in (patches[0], patches[2], patches[3]):
            p.start()
        for p in patches:
            self.addCleanup(p.stop)

    def write_run(self, run, name="extract_harbour_bank_1.json"):
        path = self.results / name
        path.write_text(json.dumps(run))
        return str(path)

    def test_clean_run_exits_0_and_writes_record_with_hashes(self):
        code = regression.main([self.write_run(base_run())])
        self.assertEqual(code, 0)
        record = json.loads((self.results / "regression_extract_harbour_bank_1.json").read_text())
        self.assertEqual(record["labels_sha256"], "ab" * 32)
        self.assertEqual(record["prompt_hashes"], {"system_prompt_sha256": "a" * 64})
        self.assertTrue(record["all_passed"])
        self.assertEqual(len(record["checks"]), 6)

    def test_failing_check_exits_1_and_is_recorded(self):
        run = base_run()
        statements(run).append(stmt("Z1", "HB-05", "stray words from the excluded source"))
        code = regression.main([self.write_run(run)])
        self.assertEqual(code, 1)
        record = json.loads((self.results / "regression_extract_harbour_bank_1.json").read_text())
        self.assertEqual(record["failed_checks"], ["excluded_sources"])

    def test_other_deals_are_refused_before_labels_are_read(self):
        for deal in ("hard_cases", "coral_pay", None):
            run = copy.deepcopy(base_run())
            run["deal"] = deal
            self.assertEqual(regression.main([self.write_run(run, f"extract_{deal}_1.json")]), 2, deal)
        self.load_labels.assert_not_called()
        self.assertEqual(list(self.results.glob("regression_*")), [])

    def test_path_outside_results_extract_files_is_refused(self):
        self.assertEqual(regression.main(["data/coral_pay/labels/statements.json"]), 2)
        self.assertEqual(regression.main([str(self.results / "eval_x.json")]), 2)
        self.load_labels.assert_not_called()

    def test_existing_output_is_never_overwritten(self):
        path = self.write_run(base_run())
        self.assertEqual(regression.main([path]), 0)
        out = self.results / "regression_extract_harbour_bank_1.json"
        before = out.read_text()
        self.assertEqual(regression.main([path]), 2)
        self.assertEqual(out.read_text(), before)


if __name__ == "__main__":
    unittest.main()
