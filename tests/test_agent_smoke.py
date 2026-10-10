"""agent_smoke.py (9 Oct, option C): runs agent v2 once on Harbour Bank and the hard cases only, in a temporary ledger,
scores nothing, and never uses the workspace ledger. A scripted fake stands in for the model."""

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import agent_smoke
import config


class EchoAgent:
    """Submits 'unknown' for every commitment it is asked about, then stops."""

    def __init__(self):
        self.calls, self.messages = 0, self

    def create(self, **kwargs):
        self.calls += 1
        keys = re.findall(r'"commitment_key": "([^"]+)"', kwargs["messages"][0]["content"])
        blocks = [NS(type="tool_use", id=f"t{self.calls}{n}", name="submit_verdict",
                     input={"commitment_key": k, "authorisation": "unknown_needs_review", "rationale": "scripted",
                            "pricing_note_line": None}) for n, k in enumerate(keys)]
        return NS(content=blocks, usage=NS(input_tokens=1500, output_tokens=200), stop_reason="tool_use")


class TestSmoke(unittest.TestCase):
    def test_runs_on_the_two_seen_deals_only_and_never_touches_the_workspace_ledger(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(config, "LEDGER_DB_PATH", Path(tmp) / "must-not-exist.sqlite"):
            report = agent_smoke.smoke(EchoAgent(), workdir=tmp)
            self.assertFalse((Path(tmp) / "must-not-exist.sqlite").exists())
        self.assertEqual(set(report["deals"]), {"harbour_bank", "hard_cases"})
        self.assertTrue(report["ran_end_to_end"])
        self.assertIn("Not scored", report["purpose"])
        for d in report["deals"].values():
            self.assertEqual(len(d["escalated"]), 1)
            self.assertEqual(d["missing_verdicts"], [])
        # Labels never reach the agent's input: covered by test_agent.TestEscalation (same escalated_items function).

    def test_the_practice_set_is_refused(self):
        with self.assertRaises(ValueError):
            agent_smoke.smoke(EchoAgent(), deals=("practice_cases",))

    def test_main_refuses_without_a_key(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertEqual(agent_smoke.main([]), 2)


if __name__ == "__main__":
    unittest.main()
