"""Offline tests for evaluate. Synthetic strings only: no network, no deal files."""

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
import evaluate

T, F = config.MATCH_THRESHOLD, config.NEAR_MISS_FLOOR

FULL = "Elva will screen up to 25,000 payouts per day from the 1 December launch."
SHORT = "Elva will screen up to 25,000 payouts per day."


def lab(i, src, quote, language="firm"):
    return {"id": i, "source_id": src, "quote": quote, "language": language}


def out(i, src, quote, language="firm"):
    return {"statement_id": i, "source_id": src, "quote": quote, "language": language}


def run_of(*stmts, status="complete"):
    return {"deal": "harbour_bank", "documents": [{"source_id": "X-01", "status": status, "statements": list(stmts)}]}


class Matching(unittest.TestCase):
    def test_identical_quotes_match(self):
        r = evaluate.evaluate(run_of(out("S1", "X-01", FULL)), [lab("L1", "X-01", FULL)], T, F)
        self.assertEqual((r["counts"]["tp"], r["counts"]["fp"], r["counts"]["fn"]), (1, 0, 0))

    def test_different_source_id_never_matches(self):
        r = evaluate.evaluate(run_of(out("S1", "X-02", FULL)), [lab("L1", "X-01", FULL)], 0.0, F)
        self.assertEqual((r["counts"]["tp"], r["counts"]["fp"], r["counts"]["fn"]), (0, 1, 1))
        self.assertEqual(r["near_misses"], [])

    def test_near_miss_not_counted_as_match(self):
        # FULL: elva will screen up to 25 000 payouts per day from the 1 december launch
        #   -> 15 distinct tokens (25,000 splits into 25 and 000; 1 is a token).
        # SHORT: the same minus "from the 1 december launch" -> 10 tokens, all shared.
        # Jaccard = 10 / 15.
        score = evaluate.jaccard(evaluate.words(SHORT), evaluate.words(FULL))
        self.assertEqual(len(evaluate.words(FULL)), 15)
        self.assertEqual(len(evaluate.words(SHORT)), 10)
        self.assertAlmostEqual(score, 10 / 15)
        r = evaluate.evaluate(run_of(out("S1", "X-01", SHORT)), [lab("L1", "X-01", FULL)], T, F)
        self.assertEqual((r["counts"]["tp"], r["counts"]["fp"], r["counts"]["fn"]), (0, 1, 1))
        self.assertEqual(len(r["near_misses"]), 1)
        self.assertAlmostEqual(r["near_misses"][0]["score"], 0.667, places=3)

    def test_near_miss_only_when_both_sides_unmatched(self):
        labels = [lab("L1", "X-01", FULL)]
        r = evaluate.evaluate(run_of(out("S1", "X-01", FULL), out("S2", "X-01", SHORT)), labels, T, F)
        self.assertEqual(r["near_misses"], [])

    def test_two_outputs_one_label_gives_tp_and_fp(self):
        r = evaluate.evaluate(
            run_of(out("S1", "X-01", FULL), out("S2", "X-01", FULL)), [lab("L1", "X-01", FULL)], T, F)
        self.assertEqual((r["counts"]["tp"], r["counts"]["fp"], r["counts"]["fn"]), (1, 1, 0))

    def test_threshold_override_changes_outcome(self):
        args = (run_of(out("S1", "X-01", SHORT)), [lab("L1", "X-01", FULL)])
        self.assertEqual(evaluate.evaluate(*args, 0.6, F)["counts"]["tp"], 1)
        self.assertEqual(evaluate.evaluate(*args, 1.0, F)["counts"]["tp"], 0)

    def test_threshold_one_accepts_same_word_set_in_other_order(self):
        r = evaluate.evaluate(
            run_of(out("S1", "X-01", "payouts per day, per day")), [lab("L1", "X-01", "Day per payouts")], 1.0, F)
        self.assertEqual(r["counts"]["tp"], 1)


class Checks(unittest.TestCase):
    def test_missing_number_flagged_detail_lost(self):
        label = "Elva will screen 25,000 payouts by 1 December."
        output = "Elva will screen payouts by December."
        r = evaluate.evaluate(run_of(out("S1", "X-01", output)), [lab("L1", "X-01", label)], 0.5, F)
        self.assertEqual(r["counts"]["tp"], 1)
        self.assertEqual(r["detail_lost"][0]["missing"], ["000", "1", "25"])

    def test_no_detail_lost_when_numbers_present(self):
        r = evaluate.evaluate(run_of(out("S1", "X-01", FULL)), [lab("L1", "X-01", FULL)], T, F)
        self.assertEqual(r["detail_lost"], [])

    def test_language_confusion_and_hedge_errors(self):
        labels = [lab("L1", "X-01", "alpha beta gamma", "conditional"), lab("L2", "X-01", "delta epsilon zeta", "firm")]
        stmts = [out("S1", "X-01", "alpha beta gamma", "firm"), out("S2", "X-01", "delta epsilon zeta", "firm")]
        r = evaluate.evaluate(run_of(*stmts), labels, T, F)
        self.assertEqual(r["language_confusion"], {"conditional": {"firm": 1}, "firm": {"firm": 1}})
        self.assertAlmostEqual(r["language_accuracy"], 0.5)
        self.assertEqual(len(r["hedge_errors"]), 1)

    def test_non_complete_document_labels_are_fn_and_outputs_cannot_match(self):
        r = evaluate.evaluate(
            run_of(out("S1", "X-01", FULL), status="failed"), [lab("L1", "X-01", FULL)], T, F)
        self.assertEqual((r["counts"]["tp"], r["counts"]["fp"], r["counts"]["fn"]), (0, 1, 1))
        self.assertEqual(r["non_complete_documents"],
                         [{"source_id": "X-01", "status": "failed", "labels_affected": ["L1"]}])


class Arithmetic(unittest.TestCase):
    def test_precision_recall_hand_computed(self):
        # Labels: L1 firm, L2 firm, L3 conditional. Outputs: S1 = L1, S2 = L3, S3 = spurious.
        # TP=2 (L1, L3), FP=1 (S3), FN=1 (L2).
        # precision = 2/3, recall = 2/3, firm recall = 1/2 (L1 found, L2 missed).
        labels = [lab("L1", "X-01", "alpha beta gamma"), lab("L2", "X-01", "delta epsilon zeta"),
                  lab("L3", "X-01", "eta theta iota", "conditional")]
        stmts = [out("S1", "X-01", "alpha beta gamma"), out("S2", "X-01", "eta theta iota", "conditional"),
                 out("S3", "X-01", "kappa lambda mu")]
        r = evaluate.evaluate(run_of(*stmts), labels, T, F)
        self.assertEqual((r["counts"]["tp"], r["counts"]["fp"], r["counts"]["fn"]), (2, 1, 1))
        self.assertAlmostEqual(r["precision"], 2 / 3)
        self.assertAlmostEqual(r["recall"], 2 / 3)
        self.assertAlmostEqual(r["recall_firm"], 1 / 2)
        self.assertEqual(r["language_accuracy"], 1.0)


class InputsAndOutput(unittest.TestCase):
    def test_run_path_must_be_results_extract_json(self):
        good = config.RESULTS_DIR / "extract_x_1.json"
        self.assertEqual(evaluate.validate_run_path(str(good)), good.resolve())
        for bad in ("data/coral_pay/labels/statements.json", "results/eval_x.json",
                    "results/../data/x/extract_a.json", "results/sub/extract_a.json", "results/extract_a.txt"):
            with self.assertRaises(ValueError, msg=bad):
                evaluate.validate_run_path(bad)

    def test_disallowed_deal_refused(self):
        with self.assertRaises(config.DealNotAllowed):
            evaluate.load_labels("coral_pay")

    def test_output_name_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            results = Path(d)
            (results / "extract_harbour_bank_1.json").write_text('{"deal": "harbour_bank", "documents": []}')
            with mock.patch.object(config, "RESULTS_DIR", results), \
                 mock.patch.object(evaluate, "load_labels", return_value=([lab("L1", "X-01", FULL)], "abcdef0123456789" * 4)):
                run_file = str(results / "extract_harbour_bank_1.json")
                with mock.patch("sys.stdout"):
                    self.assertEqual(evaluate.main([run_file, "--threshold", "0.6"]), 0)
                    self.assertTrue((results / "eval_extract_harbour_bank_1_t0.6_Labcdef01.json").exists())
                    self.assertEqual(evaluate.main([run_file, "--threshold", "0.6"]), 1)

    def test_different_label_files_give_different_filenames(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            results = root / "results"
            (root / "deal" / "labels").mkdir(parents=True)
            results.mkdir()
            run_file = results / "extract_harbour_bank_1.json"
            run_file.write_text('{"deal": "harbour_bank", "documents": []}')
            labels_file = root / "deal" / "labels" / "statements.json"
            hashes = []
            with mock.patch.object(config, "RESULTS_DIR", results), \
                 mock.patch.object(config, "deal_dir", return_value=root / "deal"), \
                 mock.patch("sys.stdout"):
                for quote in ("first labels", "second labels"):
                    labels_file.write_text(json.dumps({"statements": [lab("L1", "X-01", quote)]}))
                    hashes.append(hashlib.sha256(labels_file.read_bytes()).hexdigest())
                    self.assertEqual(evaluate.main([str(run_file)]), 0)
            names = sorted(p.name for p in results.glob("eval_*.json"))
            self.assertEqual(len(names), 2)
            self.assertEqual(sorted(n.split("_L")[-1] for n in names),
                             sorted(h[:8] + ".json" for h in hashes))
            for h in hashes:
                rep = json.loads((results / f"eval_extract_harbour_bank_1_t0.8_L{h[:8]}.json").read_text())
                self.assertEqual(rep["labels_sha256"], h)


if __name__ == "__main__":
    unittest.main()
