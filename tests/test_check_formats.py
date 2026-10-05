"""check_formats.py (Lina's real-model check) with a scripted fake client: the comparison, the refusals and the file guard.
No model call, no network. Reads the pinned Harbour Bank run file for the Markdown baseline; never the labels."""

import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "fixtures"))

import check_formats
import config
import make_formats as mf
from test_recheck import FakeExtractor


def payload(statements):
    return {"statements": [{"quote": q, "speaker": "Elva", "language": lang} for q, lang in statements]}


class TestCheck(unittest.TestCase):
    def setUp(self):
        self.baseline = check_formats.baseline_hb04()

    def run_with(self, statements, user_files=()):
        client = FakeExtractor(payload(statements))
        return check_formats.run_check(client, list(user_files)), client

    def test_the_baseline_is_the_markdown_hb04_run(self):
        self.assertEqual(len(self.baseline), 6)
        self.assertGreaterEqual(sum(1 for _, lang in self.baseline if lang == "firm"), 3)

    def test_same_statements_from_every_variant_agree_and_cost_is_summed(self):
        report, client = self.run_with(self.baseline)
        self.assertEqual(client.calls, 2)  # the generated PDF and Word versions, once each
        self.assertTrue(report["all_agree"])
        for r in report["results"]:
            self.assertEqual((r["extraction"], r["quotes_missing"], r["firm"]["missing"], r["firm"]["extra"]), ("ok", [], [], []))
        pdf, docx = report["results"]
        self.assertTrue(all(page for page in pdf["pages"].values()))  # every quote resolves to a page
        self.assertEqual(docx["pages"], {})
        self.assertGreater(report["total_cost_usd"], 0)

    def test_a_missing_firm_statement_an_extra_one_and_an_invented_quote_are_flagged(self):
        firm = next(s for s in self.baseline if s[1] == "firm")
        invented = ("Elva will guarantee zero false positives.", "firm")
        report, _ = self.run_with([s for s in self.baseline if s != firm] + [invented])
        self.assertFalse(report["all_agree"])
        r = report["results"][0]
        self.assertEqual(r["quotes_missing"], [invented[0]])      # not in the text the adapter produced
        self.assertEqual(len(r["firm"]["extra"]), 1)
        self.assertEqual(len(r["firm"]["missing"]), 1)

    def test_a_quote_that_differs_only_in_line_breaks_still_counts_as_found_and_the_same(self):
        broken = [(q.replace(" the ", "\nthe ", 1), lang) for q, lang in self.baseline]
        report, _ = self.run_with(broken)
        self.assertTrue(report["all_agree"])

    def test_a_variant_the_adapter_refuses_is_reported_not_extracted(self):
        client = FakeExtractor(payload(self.baseline))
        out = check_formats.check_variant(client, "scan", "scan.pdf", mf.image_only_pdf(), self.baseline)
        self.assertIn("No page in this PDF has readable text", out["refused"])
        self.assertEqual(client.calls, 0)

    def test_your_own_pdf_is_extracted_too(self):
        report, client = self.run_with(self.baseline, [("your PDF (Export.pdf)", "Export.pdf", mf.hb04_pdf(lines_per_page=20))])
        self.assertEqual(client.calls, 3)
        self.assertEqual(report["results"][2]["variant"], "your PDF (Export.pdf)")
        self.assertTrue(report["all_agree"])

    def test_the_report_prints_without_a_key_or_a_path(self):
        report, _ = self.run_with(self.baseline)
        out = io.StringIO()
        with redirect_stdout(out):
            check_formats.print_report(report)
        text = out.getvalue()
        self.assertIn("firm statements agree and every quote is valid", text)
        self.assertNotIn("/Users/", text)


class TestCommandLine(unittest.TestCase):
    def test_files_inside_the_data_folder_missing_files_and_unknown_options_are_refused(self):
        for args in (["--pdf", str(config.DATA_DIR / "harbour_bank" / "docs" / "HB-04_proposal.md")], ["--pdf", "/nonexistent/x.pdf"],
                     ["--bogus"], ["--pdf"]):
            err = io.StringIO()
            with redirect_stderr(err), mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}), \
                    mock.patch("anthropic.Anthropic", side_effect=AssertionError("client created")):
                self.assertEqual(check_formats.main(args), 2, args)
            self.assertTrue(err.getvalue())

    def test_an_oversize_file_is_refused_before_any_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            big = Path(tmp) / "big.pdf"
            big.write_bytes(b"%PDF-" + b"0" * (check_formats.adapters.MAX_UPLOAD_BYTES + 1))
            with self.assertRaisesRegex(ValueError, "larger than 10 MB"):
                check_formats.read_user_file(str(big))

    def test_without_a_key_it_stops_and_never_prints_one(self):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, {}, clear=True), redirect_stdout(out), redirect_stderr(err), \
                mock.patch("anthropic.Anthropic", side_effect=AssertionError("client created")):
            self.assertEqual(check_formats.main([]), 2)
        self.assertIn("ANTHROPIC_API_KEY is not set.", err.getvalue())

    def test_a_key_is_never_printed_and_the_result_file_names_no_path(self):
        baseline = check_formats.baseline_hb04()  # read from the real results folder before the write is redirected
        client = FakeExtractor(payload(baseline))
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(config, "RESULTS_DIR", Path(tmp)), \
                mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-sentinel-xyz"}), \
                mock.patch("anthropic.Anthropic", return_value=client), \
                mock.patch.object(check_formats, "baseline_hb04", return_value=baseline), redirect_stdout(out):
            code = check_formats.main([])
            written = list(Path(tmp).glob("formats_check_*.json"))
            self.assertEqual((code, len(written)), (0, 1))
            text = written[0].read_text(encoding="utf-8")
            self.assertNotIn("sk-ant-sentinel", text + out.getvalue())
            self.assertNotIn("/Users/", text)


if __name__ == "__main__":
    unittest.main()
