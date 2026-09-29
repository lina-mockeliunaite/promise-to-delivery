"""Offline tests for check_quotes and the deal guard. No network, no deal files."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import check_quotes
import config
from schema import DocExtraction, Statement

SOURCES = {
    "X-01": "Intro line.\nWe will deliver the\n  export by Friday.  Also, we will deliver the export by Friday.",
    "X-02": "A different sentence lives only here.",
}


def run_with(*stmts):
    """stmts are (statement_id, source_id, quote)."""
    return {
        "deal": "harbour_bank",
        "documents": [{
            "source_id": "X-01", "status": "complete",
            "statements": [
                {"statement_id": i, "source_id": s, "quote": q, "speaker": "Elva", "language": "firm"}
                for i, s, q in stmts
            ],
        }],
    }


class QuoteCheck(unittest.TestCase):
    def test_pass_exact_and_across_line_breaks(self):
        report = check_quotes.check_run(
            run_with(("S1", "X-01", "Intro line."), ("S2", "X-01", "We will deliver the export by Friday.")),
            SOURCES,
        )
        self.assertEqual(report["failed"], 0)
        self.assertEqual(report["checked"], 2)

    def test_fail_altered_word(self):
        report = check_quotes.check_run(run_with(("S1", "X-01", "We will deliver the export by Monday.")), SOURCES)
        self.assertEqual(report["failed"], 1)
        self.assertEqual(report["failures"][0]["reason"], "not_found_in_source")

    def test_fail_reports_other_source(self):
        report = check_quotes.check_run(run_with(("S1", "X-01", "A different sentence lives only here.")), SOURCES)
        self.assertEqual(report["failures"][0]["found_in_other_sources"], ["X-02"])

    def test_fail_unknown_source_id(self):
        report = check_quotes.check_run(run_with(("S1", "X-99", "Intro line.")), SOURCES)
        self.assertEqual(report["failures"][0]["reason"], "source_id_not_in_manifest")

    def test_case_and_punctuation_are_not_normalised(self):
        report = check_quotes.check_run(run_with(("S1", "X-01", "intro line.")), SOURCES)
        self.assertEqual(report["failed"], 1)

    def test_repeated_quote_is_noted_not_failed(self):
        report = check_quotes.check_run(run_with(("S1", "X-01", "deliver the export by Friday.")), SOURCES)
        self.assertEqual(report["failed"], 0)
        self.assertEqual(report["ambiguous"][0]["matches"], 2)

    def test_incomplete_document_is_reported(self):
        run = {"deal": "harbour_bank", "documents": [{"source_id": "X-02", "status": "incomplete", "statements": []}]}
        report = check_quotes.check_run(run, SOURCES)
        self.assertEqual(report["documents_not_complete"], [{"source_id": "X-02", "status": "incomplete"}])


class DealGuard(unittest.TestCase):
    def test_fake_deal_is_refused(self):
        with self.assertRaises(config.DealNotAllowed):
            config.require_allowed_deal("fake_deal")
        with self.assertRaises(config.DealNotAllowed):
            config.deal_dir("fake_deal")

    def test_path_tricks_are_refused(self):
        for name in ("../fake_deal", "harbour_bank/../fake_deal", "Harbour_Bank", ""):
            with self.assertRaises(config.DealNotAllowed):
                config.deal_dir(name)

    def test_check_quotes_refuses_before_reading_any_deal_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_file = Path(tmp) / "run.json"
            run_file.write_text(json.dumps({"deal": "fake_deal", "documents": []}))
            with mock.patch("pathlib.Path.read_text", autospec=True, side_effect=Path.read_text) as spy:
                code = check_quotes.main(["check_quotes.py", str(run_file)])
            self.assertEqual(code, 2)
            read_paths = [str(call.args[0]) for call in spy.call_args_list]
            self.assertEqual(read_paths, [str(run_file)])  # only the run file; nothing under data/

    def test_allowed_deal_passes_guard(self):
        self.assertEqual(config.deal_dir("harbour_bank"), config.DATA_DIR / "harbour_bank")


class Schema(unittest.TestCase):
    def test_valid_and_empty(self):
        self.assertEqual(DocExtraction.model_validate({"statements": []}).statements, [])
        s = Statement.model_validate({"quote": "q", "speaker": "Elva", "language": "firm"})
        self.assertEqual(s.language, "firm")

    def test_rejects_bad_language_blank_quote_and_extra_field(self):
        good = {"quote": "q", "speaker": "Elva", "language": "firm"}
        for bad in ({**good, "language": "certain"}, {**good, "quote": "  "}, {**good, "source_id": "X"}):
            with self.assertRaises(Exception):
                Statement.model_validate(bad)


if __name__ == "__main__":
    unittest.main()
