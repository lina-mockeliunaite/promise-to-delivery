"""sealed_run.py, dry-run end to end on the practice set with a scripted model (no key, no spend), before any sealed
deal is opened. The practice set has its own seal file (data/practice_cases.sha256), so the seal check is exercised
for real. Nothing under data/coral_pay/ is read: every test names practice_cases or a temporary copy."""

import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
import extract
import sealed_run

PINNED = config.RESULTS_DIR / config.LEDGER_IMPORT_RUN_FILES["practice_cases"]


def reply(text, usage=(1000, 200)):
    return NS(content=[NS(type="text", text=text)], stop_reason="end_turn",
              usage=NS(input_tokens=usage[0], output_tokens=usage[1], output_tokens_details=None))


class ScriptedModel:
    """Extraction: returns the pinned practice-run statements of whichever document it is shown. Baseline: a short
    answer. Agent: 'unknown' for every escalated commitment."""

    def __init__(self):
        self.messages, self.calls = self, {"extraction": 0, "baseline": 0, "agent": 0}
        run = json.loads(PINNED.read_text(encoding="utf-8"))
        self.docs = [[{k: s[k] for k in ("quote", "speaker", "language")} for s in d["statements"]] for d in run["documents"]]

    def create(self, **kw):
        if "tools" in kw:
            self.calls["agent"] += 1
            keys = re.findall(r'"commitment_key": "([^"]+)"', kw["messages"][0]["content"])
            blocks = [NS(type="tool_use", id=f"a{self.calls['agent']}{n}", name="submit_verdict",
                         input={"commitment_key": k, "authorisation": "unknown_needs_review", "rationale": "scripted",
                                "pricing_note_line": None}) for n, k in enumerate(keys)]
            return NS(content=blocks, stop_reason="tool_use", usage=NS(input_tokens=1500, output_tokens=200))
        if kw.get("system") == extract.SYSTEM_PROMPT:
            self.calls["extraction"] += 1
            text = kw["messages"][0]["content"]
            for stmts in self.docs:
                if stmts and all(s["quote"] in text for s in stmts):
                    return reply(json.dumps({"statements": stmts}))
            return reply(json.dumps({"statements": []}))
        self.calls["baseline"] += 1
        return reply("1. A scripted baseline answer.")


class SealedRunCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.results = Path(tmp.name) / "results"
        self.results.mkdir()
        db = mock.patch.object(config, "LEDGER_DB_PATH", Path(tmp.name) / "workspace-must-not-exist.sqlite")
        db.start()
        self.addCleanup(db.stop)
        self.db = config.LEDGER_DB_PATH

    def run_dry(self, model=None):
        return sealed_run.sealed_run(model or ScriptedModel(), "practice_cases", results_dir=self.results, allow_development=True)


class TestDryRun(SealedRunCase):
    def test_end_to_end_on_the_practice_set(self):
        model = ScriptedModel()
        out = self.run_dry(model)
        self.assertTrue(out["completed"], json.dumps({k: v.get("error") for k, v in out["steps"].items()}))
        self.assertGreaterEqual(out["seal_files_verified"], 5)
        self.assertEqual(model.calls["baseline"], 1)
        self.assertGreater(model.calls["extraction"], 0)
        ext = out["steps"]["extraction"]["result"]
        self.assertEqual(ext["metrics"]["recall"], 1.0)  # the scripted model returns the pinned statements
        rules = out["steps"]["rules_and_agent"]["result"]["rules"]
        self.assertEqual(rules["metrics"]["issues"]["false_negative"] >= 0, True)
        agent = out["steps"]["rules_and_agent"]["result"]["agent"]
        self.assertTrue(agent["escalated"])  # the practice set's paraphrases reach the agent
        self.assertIn("rules power the demo", agent["decision"]["conclusion"])
        written = sorted(p.name for p in self.results.iterdir())
        self.assertTrue(any(n.startswith("sealed_practice_cases_") for n in written))
        self.assertTrue(any(n.startswith("extract_practice_cases_") for n in written))
        self.assertTrue(any(n.startswith("eval_extract_practice_cases_") for n in written))
        self.assertFalse(self.db.exists())  # the workspace ledger is never created or touched
        self.assertNotIn("practice_cases_", " ".join(p.name for p in config.RESULTS_DIR.iterdir() if "sealed_" in p.name))
        print("\n" + sealed_run.render(out))

    def test_it_runs_once_per_deal(self):
        self.run_dry()
        with self.assertRaises(sealed_run.Refused):
            self.run_dry()

    def test_a_development_deal_is_refused_without_the_dry_run_flag(self):
        with self.assertRaises(sealed_run.Refused):
            sealed_run.sealed_run(ScriptedModel(), "practice_cases", results_dir=self.results)

    def test_config_is_restored_afterwards(self):
        before = (list(config.ALLOWED_DEALS), list(config.LEDGER_DEALS), dict(config.LEDGER_IMPORT_RUN_FILES), config.RESULTS_DIR)
        self.run_dry()
        self.assertEqual(before, (list(config.ALLOWED_DEALS), list(config.LEDGER_DEALS), dict(config.LEDGER_IMPORT_RUN_FILES), config.RESULTS_DIR))

    def test_a_failed_step_is_recorded_and_the_rest_still_reported(self):
        class Broken(ScriptedModel):
            def create(self, **kw):
                if kw.get("system") != extract.SYSTEM_PROMPT and "tools" not in kw:
                    raise RuntimeError("baseline call failed")
                return super().create(**kw)
        out = self.run_dry(Broken())
        self.assertFalse(out["steps"]["baseline"]["ok"])
        self.assertIn("baseline call failed", out["steps"]["baseline"]["error"])
        self.assertTrue(out["steps"]["extraction"]["ok"])
        self.assertFalse(out["completed"])


class TestSeal(unittest.TestCase):
    def test_a_changed_file_breaks_the_seal_and_nothing_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(config.DATA_DIR / "practice_cases", root / "data" / "practice_cases")
            shutil.copy(config.DATA_DIR / "practice_cases.sha256", root / "data" / "practice_cases.sha256")
            self.assertGreaterEqual(len(sealed_run.verify_seal("practice_cases", root)), 5)
            doc = next((root / "data" / "practice_cases" / "docs").glob("PC-01*"))
            doc.write_text(doc.read_text(encoding="utf-8") + "\nedited", encoding="utf-8")
            with self.assertRaises(sealed_run.Refused):
                sealed_run.verify_seal("practice_cases", root)

    def test_no_seal_file_means_no_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(sealed_run.Refused):
                sealed_run.verify_seal("practice_cases", Path(tmp))


if __name__ == "__main__":
    unittest.main()
