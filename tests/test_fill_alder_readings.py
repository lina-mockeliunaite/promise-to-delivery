"""fill_alder_readings.py (Round 5, 12 Nov): the script that makes the two readings the new Alder documents need. Its --selftest runs the whole story on canned readings, with no key and no
network, against the staged documents and the Alder catalogue; these tests also pin what makes a report "safe to accept" and that nothing is written outside a scratch area."""

import hashlib
import io
import os
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
import fill_alder_readings as fill


def cache_fingerprint():
    d = Path(config.V2_CACHE_DIR)
    return sorted((p.name, hashlib.sha256(p.read_bytes()).hexdigest()) for p in d.glob("*.json"))


class TestFindings(unittest.TestCase):
    def f(self, kind, commitment, quote, path=None):
        return {"kind": kind, "commitment": commitment, "promise_quotes": [{"source_id": "AB-04", "quote": quote}], "catalogue_path": path}

    def test_the_four_expected_findings_are_allowed_and_complete(self):
        four = [self.f("approval_required", "x", "Scam-call alerts will warn the bank", "CAP-027/AU"), self.f("contract_gap", "x", "Scam-call alerts will warn the bank"),
                self.f("absolute_limit", "h", "Elva will host Alder's environment on Microsoft Azure", "CAP-019/AU"), self.f("conflicting_terms", "h", "Elva will host Alder's environment on Microsoft Azure")]
        self.assertEqual((fill.extras(four), fill.missing(four)), ([], []))
        self.assertEqual(len(fill.missing(four[:3])), 1)

    def test_volume_and_threshold_findings_and_duplicates_are_extras(self):
        vol = self.f("over_limit", "Real-time scoring will handle up to 750,000 payments per day", "Real-time scoring will handle up to 750,000 payments per day", "CAP-003/AU")
        thr = self.f("conflicting_terms", "All outbound instant payments scored in real time", "All outbound instant payments will be scored in real time")
        dup = self.f("contract_gap", "x", "Scam-call alerts will warn the bank")
        out = fill.extras([vol, thr, dup, dup])
        self.assertEqual(len(out), 3)
        self.assertTrue(all(line.startswith("EXTRA") for line in out))
        self.assertIn("duplicate", out[2])

    def test_the_subject_follows_the_catalogue_entry_or_the_quote(self):
        self.assertEqual(fill.subject_of(self.f("approval_required", "x", "anything", "CAP-027/AU")), "scam-call alerts")
        self.assertEqual(fill.subject_of(self.f("contract_gap", "x", "Scam-call alerts will warn the bank")), "scam-call alerts")
        self.assertEqual(fill.subject_of(self.f("absolute_limit", "x", "hosted on Microsoft Azure", "CAP-019/AU")), "hosting")
        self.assertEqual(fill.subject_of(self.f("over_limit", "x", "750,000 payments", "CAP-003/AU")), "other")


class TestBaseContractPhrases(unittest.TestCase):
    CHAIN = [("AB-06", "Provider will score outbound instant payments. Real-time scoring will handle up to 200,000 payments per day at launch."), ("AB-07", "The Services commence on 1 February 2027. Provider will perform the services.")]

    def gap(self, phrases, quote="Scam-call alerts will warn the bank"):
        return {"kind": "contract_gap", "commitment": "x", "promise_quotes": [{"source_id": "AB-04", "quote": quote}], "missing_phrases": phrases, "catalogue_path": None}

    def test_a_phrase_the_base_contract_chain_already_holds_is_reported(self):
        hits = fill.chain_phrase_hits([self.gap(["scam-call alerts", "1 February 2027"])], self.CHAIN)
        self.assertEqual(len(hits), 1)
        self.assertIn("'1 February 2027' already appears in base contract-chain document AB-07", hits[0])
        self.assertIn("scam-call alerts contract gap", hits[0])

    def test_phrases_the_chain_lacks_and_other_kinds_are_not_reported(self):
        self.assertEqual(fill.chain_phrase_hits([self.gap(["scam-call alerts", "on a call with a scammer", "1 February 2027 launch"])], self.CHAIN), [])
        other = {**self.gap(["1 February 2027"]), "kind": "conflicting_terms"}
        self.assertEqual(fill.chain_phrase_hits([other], self.CHAIN), [])

    def test_the_pipeline_turns_a_hit_into_a_not_safe_report(self):
        text = Path(fill.__file__).read_text(encoding="utf-8")
        self.assertIn("for line in chain_phrase_hits(rep[\"readings\"][\"K0\"][\"findings\"], base_chain):", text)
        self.assertIn('problem(f"K0: {line}")', text)


class TestRound5c(unittest.TestCase):
    """Round 5c: a numbered heading that holds the gap's searched phrase turns the signed check's closing wording into a fragment. The self-test fails that case, and passes the renamed headings."""

    def temp_scenarios(self, heading_old_style: bool):
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        d = Path(tmp.name)
        for name in ("AB-05_v2_named_exception.md", "AB-06_v2_coaching_added.md", "AB-09_signed_contract.md"):
            text = fill.staged("scenarios", name)
            if heading_old_style:
                text = text.replace("## 5. Fraud warnings during payment", "## 5. Scam-call alerts").replace("**2. Fraud warnings during payment.**", "**2. Scam-call alerts.**")
            (d / name).write_text(text, encoding="utf-8")
        return d

    def test_an_old_style_heading_is_reported_as_not_safe_with_the_fragment(self):
        d = self.temp_scenarios(True)
        with mock.patch.object(fill, "scen_dir", lambda: d):
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = fill.selftest()
        self.assertEqual(code, 1)
        out = buf.getvalue()
        self.assertIn("NOT SAFE", out)
        self.assertIn("closing wording is 'Scam-call alerts'", out)
        self.assertIn("a heading probably holds a searched phrase", out)

    def test_the_renamed_headings_give_the_full_sentence(self):
        d = self.temp_scenarios(False)
        with mock.patch.object(fill, "scen_dir", lambda: d):
            sentence = fill.closing_sentence()
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = fill.selftest()
        self.assertEqual(code, 0, buf.getvalue()[-800:])
        self.assertEqual(sentence, "Scam-call alerts will be live from the 1 February 2027 launch: they warn the bank when a customer seems to be on a call with a scammer while making a payment.")
        self.assertIn(f"the full sentence: {sentence!r}", buf.getvalue())

    def test_the_two_files_must_share_the_sentence_exactly_once(self):
        d = self.temp_scenarios(False)
        (d / "AB-09_signed_contract.md").write_text(fill.staged("scenarios", "AB-09_signed_contract.md").replace("they warn the bank", "they alert the bank"), encoding="utf-8")
        with mock.patch.object(fill, "scen_dir", lambda: d):
            with self.assertRaises(fill.NotReady):
                fill.closing_sentence()

    def test_the_base_reading_is_reused_so_only_the_new_state_needs_a_model(self):
        with __import__("tempfile").TemporaryDirectory() as tmp:
            with self.assertRaises(fill.NotReady) as cm:
                fill.pipeline(Path(tmp) / "cache", None)  # offline: K0 is copied from results/v2_cache; K1 is not there, so adding AB-06 is refused
        self.assertIn("adding AB-06 failed", str(cm.exception))
        self.assertNotIn("no reading for the base documents", str(cm.exception))


class TestTheScript(unittest.TestCase):
    def test_the_selftest_runs_the_whole_story_on_canned_readings_and_writes_nothing_to_the_real_cache(self):
        before = cache_fingerprint()
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = fill.selftest()
        out = buf.getvalue()
        self.assertEqual(code, 0, out[-1500:])
        self.assertIn("READY: safe to --accept", out)
        self.assertIn("The contract start date is earlier than the approved start date.", out)  # step 3
        self.assertIn("The signed start date is earlier than the approved start date.", out)  # step 4
        self.assertIn("addressed by note ['Hosting on Microsoft Azure']", out)
        self.assertEqual(cache_fingerprint(), before)  # results/v2_cache untouched
        self.assertNotIn("selftest", [v for k, v in os.environ.items() if k == "ANTHROPIC_API_KEY"])  # the stand-in key does not leak out of the run

    def test_not_ready_reports_are_refused_and_nothing_is_written(self):
        rep = {"problems": ["K1: EXTRA: over_limit"], "readings": {}}
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(fill.accept(rep), 1)
        self.assertIn("NOT SAFE to --accept", buf.getvalue())

    def test_accept_without_kept_candidates_stops_and_the_real_run_without_a_key_does_nothing(self):
        with mock.patch.object(fill, "CANDIDATES", Path(config.ROOT) / "scratch_alder_candidates_does_not_exist"):
            buf = io.StringIO()
            with redirect_stdout(buf):
                self.assertEqual(fill.main(["--accept"]), 1)
            self.assertIn("cannot --accept", buf.getvalue())
        env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
        with mock.patch.dict(os.environ, env, clear=True):
            buf = io.StringIO()
            with redirect_stdout(buf):
                self.assertEqual(fill.main([]), 2)
            self.assertIn("nothing was done", buf.getvalue())

    def test_the_script_never_prints_or_writes_the_key(self):
        text = Path(fill.__file__).read_text(encoding="utf-8")
        self.assertNotIn("sk-", text)
        self.assertEqual(text.count('os.environ["ANTHROPIC_API_KEY"]'), 1)  # the one pass-through to the app's own client factory
        self.assertNotRegex(text, r"print\([^)]*ANTHROPIC_API_KEY\]")
        self.assertFalse((Path(config.ROOT) / "scratch_alder_candidates").exists() and any((Path(config.ROOT) / "scratch_alder_candidates").glob("*.env")))


if __name__ == "__main__":
    unittest.main()
