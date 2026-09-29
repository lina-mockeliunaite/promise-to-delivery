"""Offline tests for extract.py. A scripted stub replaces the API client; no network, no real deal files."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import anthropic

import config
import extract

GOOD = json.dumps({"statements": [
    {"quote": "We will deliver it.", "speaker": "Model Guess", "language": "firm"},
    {"quote": "We could look at it.", "speaker": "Model Guess", "language": "exploratory"},
]})
BAD_LANGUAGE = json.dumps({"statements": [{"quote": "q", "speaker": "s", "language": "certain"}]})


def reply(text, stop="end_turn", inp=1000, out=500, thinking=None):
    details = SimpleNamespace(thinking_tokens=thinking) if thinking is not None else None
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        stop_reason=stop,
        usage=SimpleNamespace(input_tokens=inp, output_tokens=out, output_tokens_details=details),
    )


class StubClient:
    """messages.create returns scripted replies in order; an Exception item is raised."""

    def __init__(self, *script):
        self.script = list(script)
        self.calls = []
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.docs = root / "data" / "test_deal" / "docs"
        self.docs.mkdir(parents=True)
        (root / "data" / "test_deal" / "labels").mkdir()
        for patcher in (
            mock.patch.object(config, "DATA_DIR", root / "data"),
            mock.patch.object(config, "RESULTS_DIR", root / "results"),
            mock.patch.object(config, "ALLOWED_DEALS", ["test_deal"]),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def write_manifest(self, *entries):
        """entries are (source_id, file, doc_type); the file is created unless its name contains '..'."""
        docs = []
        for i, (sid, fname, dtype) in enumerate(entries):
            docs.append({"source_id": sid, "file": fname, "doc_type": dtype, "date": f"2026-10-0{i + 1}"})
            if ".." not in fname:
                (self.docs / fname).write_text(f"text of {sid}", encoding="utf-8")
        (self.docs / "manifest.json").write_text(json.dumps({"deal": "test_deal", "documents": docs}))


class Extraction(Base):
    def test_success_attaches_code_owned_fields_and_fixes_speaker(self):
        self.write_manifest(("T-01", "t1.md", "call_transcript"), ("T-02", "t2.md", "proposal"))
        client = StubClient(reply(GOOD), reply(GOOD))
        run = extract.run_extraction(client, "test_deal")

        call_doc, written_doc = run["documents"]
        self.assertEqual([s["statement_id"] for s in call_doc["statements"]], ["T-01-S01", "T-01-S02"])
        self.assertEqual(call_doc["statements"][0]["source_id"], "T-01")
        self.assertEqual(call_doc["statements"][0]["doc_type"], "call_transcript")
        self.assertEqual(call_doc["statements"][0]["date"], "2026-10-01")
        self.assertEqual(call_doc["statements"][0]["speaker"], "Model Guess")       # calls keep the model's speaker
        self.assertEqual(written_doc["statements"][0]["speaker"], config.WRITTEN_DOC_SPEAKER)  # written docs do not
        self.assertEqual(call_doc["status"], "complete")
        self.assertEqual(len(client.calls), 2)

    def test_empty_statement_list_is_complete(self):
        self.write_manifest(("T-01", "t1.md", "draft_contract"))
        run = extract.run_extraction(StubClient(reply('{"statements": []}')), "test_deal")
        self.assertEqual(run["documents"][0]["status"], "complete")
        self.assertEqual(run["documents"][0]["statements"], [])

    def test_retry_after_validation_failure_logs_both_attempts(self):
        self.write_manifest(("T-01", "t1.md", "proposal"))
        client = StubClient(reply(BAD_LANGUAGE, inp=1000, out=200), reply(GOOD, inp=1000, out=300))
        doc = extract.run_extraction(client, "test_deal")["documents"][0]

        self.assertEqual(doc["status"], "complete")
        self.assertEqual(len(doc["attempts"]), 2)
        first, second = doc["attempts"]
        self.assertFalse(first["ok"])
        self.assertEqual(first["error_kind"], "validation")
        self.assertIn("language", first["error"])
        self.assertIn("certain", first["raw_text"])
        self.assertTrue(second["ok"])
        self.assertEqual((doc["input_tokens"], doc["output_tokens"]), (2000, 500))  # both attempts counted
        self.assertEqual(len(doc["statements"]), 2)

    def test_incomplete_after_two_failures_keeps_both_errors(self):
        self.write_manifest(("T-01", "t1.md", "proposal"), ("T-02", "t2.md", "rfp_response"))
        client = StubClient(reply("not json"), reply(BAD_LANGUAGE), reply(GOOD))
        run = extract.run_extraction(client, "test_deal")

        bad, ok = run["documents"]
        self.assertEqual(bad["status"], "incomplete")
        self.assertEqual(bad["statements"], [])
        self.assertEqual([a["ok"] for a in bad["attempts"]], [False, False])
        self.assertTrue(all(a["error"] for a in bad["attempts"]))
        self.assertEqual(ok["status"], "complete")            # the next document is still processed
        self.assertEqual(run["status_counts"], {"incomplete": 1, "complete": 1})

    def test_truncated_reply_is_a_failed_attempt(self):
        self.write_manifest(("T-01", "t1.md", "proposal"))
        client = StubClient(reply('{"statements": [', stop="max_tokens"), reply(GOOD))
        doc = extract.run_extraction(client, "test_deal")["documents"][0]
        self.assertEqual(doc["attempts"][0]["error_kind"], "truncated")
        self.assertEqual(doc["attempts"][0]["stop_reason"], "max_tokens")
        self.assertEqual(doc["status"], "complete")

    def test_api_error_is_a_failed_attempt_with_no_usage(self):
        self.write_manifest(("T-01", "t1.md", "proposal"))
        err = anthropic.APIConnectionError(request=mock.Mock())
        doc = extract.run_extraction(StubClient(err, reply(GOOD)), "test_deal")["documents"][0]
        self.assertEqual(doc["attempts"][0]["error_kind"], "api_error")
        self.assertIsNone(doc["attempts"][0]["usage"])
        self.assertEqual(doc["status"], "complete")

    def test_unsupported_type_is_flagged_and_reference_only_is_skipped_without_calls(self):
        self.write_manifest(("T-01", "t1.md", "security_questionnaire"),
                            ("T-02", "t2.md", "pricing_services_note"),
                            ("T-03", "t3.md", "customer_email"))
        client = StubClient()
        with self.assertLogs("extract", level="WARNING") as logs:
            run = extract.run_extraction(client, "test_deal")
        statuses = [d["status"] for d in run["documents"]]
        self.assertEqual(statuses, ["flagged_unsupported_type", "skipped_reference_only", "skipped_reference_only"])
        self.assertEqual(client.calls, [])
        self.assertTrue(any("security_questionnaire" in line for line in logs.output))


class RunRecord(Base):
    def test_run_records_settings_and_actual_usage_and_sends_no_thinking_override(self):
        self.write_manifest(("T-01", "t1.md", "proposal"), ("T-02", "t2.md", "draft_sow"))
        client = StubClient(reply(GOOD, inp=1000, out=500, thinking=120), reply(GOOD, inp=2000, out=1000))
        run = extract.run_extraction(client, "test_deal")

        self.assertEqual(run["model"], config.EXTRACTION_MODEL)
        self.assertEqual(run["max_tokens"], config.MAX_TOKENS)
        self.assertEqual(run["thinking_mode"], "model_default")
        for call in client.calls:
            self.assertNotIn("thinking", call)
            self.assertEqual(call["model"], config.EXTRACTION_MODEL)
            self.assertEqual(call["max_tokens"], config.MAX_TOKENS)
            self.assertEqual(call["output_config"]["format"]["type"], "json_schema")

        first, second = run["documents"]
        self.assertEqual(first["attempts"][0]["usage"], {"input_tokens": 1000, "output_tokens": 500, "thinking_tokens": 120})
        self.assertIsNone(second["attempts"][0]["usage"]["thinking_tokens"])   # not reported -> null, not invented
        self.assertEqual(run["totals"]["input_tokens"], 3000)
        self.assertEqual(run["totals"]["output_tokens"], 1500)
        self.assertEqual(run["totals"]["thinking_tokens"], 120)                # only what was reported

    def test_thinking_total_is_null_when_never_reported(self):
        self.write_manifest(("T-01", "t1.md", "proposal"))
        run = extract.run_extraction(StubClient(reply(GOOD)), "test_deal")
        self.assertIsNone(run["totals"]["thinking_tokens"])

    def test_cost_uses_config_prices_and_is_null_without_them(self):
        self.assertAlmostEqual(extract.cost_usd(1000, 500), 0.007)   # 1000*2/1e6 + 500*10/1e6
        with mock.patch.object(config, "PRICE_PER_MTOK", {config.EXTRACTION_MODEL: {"input": None, "output": None}}):
            self.assertIsNone(extract.cost_usd(1000, 500))
            self.write_manifest(("T-01", "t1.md", "proposal"))
            run = extract.run_extraction(StubClient(reply(GOOD)), "test_deal")
            self.assertIsNone(run["totals"]["cost_usd"])

    def test_run_records_full_sha256_of_prompt_template_and_schema(self):
        import hashlib
        self.write_manifest(("T-01", "t1.md", "proposal"))
        client = StubClient(reply(GOOD))
        hashes = extract.run_extraction(client, "test_deal")["prompt_hashes"]

        self.assertEqual(set(hashes), {"system_prompt_sha256", "user_template_sha256", "schema_sha256"})
        for value in hashes.values():
            self.assertRegex(value, r"^[0-9a-f]{64}$")           # full digest, not truncated
        sha = lambda s: hashlib.sha256(s.encode("utf-8")).hexdigest()
        self.assertEqual(hashes["system_prompt_sha256"], sha(extract.SYSTEM_PROMPT))
        self.assertEqual(hashes["user_template_sha256"], sha(extract.USER_TEMPLATE))

        # The schema hash covers the schema that was actually sent to the API.
        sent = client.calls[0]["output_config"]["format"]["schema"]
        canonical = json.dumps(sent, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        self.assertEqual(hashes["schema_sha256"], sha(canonical))
        # The system prompt and user message actually sent match what was hashed.
        self.assertEqual(client.calls[0]["system"], extract.SYSTEM_PROMPT)
        self.assertEqual(client.calls[0]["messages"][0]["content"],
                         extract.USER_TEMPLATE.format(doc_type="proposal", text="text of T-01"))

    def test_hashes_are_stable_and_change_when_the_prompt_changes(self):
        self.write_manifest(("T-01", "t1.md", "proposal"))
        first = extract.run_extraction(StubClient(reply(GOOD)), "test_deal")["prompt_hashes"]
        again = extract.run_extraction(StubClient(reply(GOOD)), "test_deal")["prompt_hashes"]
        self.assertEqual(first, again)

        with mock.patch.object(extract, "SYSTEM_PROMPT", extract.SYSTEM_PROMPT + " "):
            changed = extract.run_extraction(StubClient(reply(GOOD)), "test_deal")["prompt_hashes"]
        self.assertNotEqual(changed["system_prompt_sha256"], first["system_prompt_sha256"])
        self.assertEqual(changed["user_template_sha256"], first["user_template_sha256"])
        self.assertEqual(changed["schema_sha256"], first["schema_sha256"])

        with mock.patch.object(extract, "USER_TEMPLATE", extract.USER_TEMPLATE + "\n"):
            changed = extract.run_extraction(StubClient(reply(GOOD)), "test_deal")["prompt_hashes"]
        self.assertNotEqual(changed["user_template_sha256"], first["user_template_sha256"])

    def test_unimplemented_thinking_mode_is_refused(self):
        self.write_manifest(("T-01", "t1.md", "proposal"))
        with mock.patch.object(config, "THINKING_MODE", "adaptive"):
            with self.assertRaises(ValueError):
                extract.run_extraction(StubClient(), "test_deal")

    def test_save_run_writes_a_new_file_and_never_overwrites(self):
        self.write_manifest(("T-01", "t1.md", "proposal"))
        run = extract.run_extraction(StubClient(reply(GOOD)), "test_deal")
        path = extract.save_run(run)
        saved = json.loads(Path(path).read_text())
        self.assertEqual(saved["model"], config.EXTRACTION_MODEL)
        self.assertEqual(saved["thinking_mode"], "model_default")
        with self.assertRaises(FileExistsError):
            extract.save_run(run)


class Guards(Base):
    def test_fake_deal_is_refused_before_any_read_or_call(self):
        client = StubClient()
        with mock.patch("pathlib.Path.read_text", autospec=True) as read, \
             mock.patch("builtins.open") as opened:
            with self.assertRaises(config.DealNotAllowed):
                extract.run_extraction(client, "fake_deal")
            self.assertEqual(extract.main(["extract.py", "fake_deal"]), 2)
        read.assert_not_called()
        opened.assert_not_called()
        self.assertEqual(client.calls, [])

    def test_missing_api_key_stops_before_reading_deal_files(self):
        with mock.patch.dict(os.environ, {}, clear=False) as env, \
             mock.patch("pathlib.Path.read_text", autospec=True) as read:
            env.pop("ANTHROPIC_API_KEY", None)
            self.assertEqual(extract.main(["extract.py", "test_deal"]), 2)
        read.assert_not_called()

    def test_manifest_filename_outside_docs_is_never_read_or_sent(self):
        secret = self.docs.parent / "labels" / "gold.md"
        secret.write_text("SECRET LABEL TEXT")
        self.write_manifest(("T-01", "../labels/gold.md", "proposal"),
                            ("T-02", "sub/../../labels/gold.md", "proposal"))
        client = StubClient()
        run = extract.run_extraction(client, "test_deal")
        for doc in run["documents"]:
            self.assertEqual(doc["status"], "incomplete")
            self.assertIn("outside the docs folder", doc["error"])
        self.assertEqual(client.calls, [])

    def test_symlink_out_of_docs_is_refused(self):
        secret = self.docs.parent / "labels" / "gold.md"
        secret.write_text("SECRET LABEL TEXT")
        (self.docs / "link.md").symlink_to(secret)
        docs = [{"source_id": "T-01", "file": "link.md", "doc_type": "proposal", "date": "2026-10-01"}]
        (self.docs / "manifest.json").write_text(json.dumps({"documents": docs}))
        client = StubClient()
        doc = extract.run_extraction(client, "test_deal")["documents"][0]
        self.assertEqual(doc["status"], "incomplete")
        self.assertEqual(client.calls, [])


if __name__ == "__main__":
    unittest.main()
