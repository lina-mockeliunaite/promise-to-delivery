"""Tests for agent.py and agent_compare.py with a scripted fake client: no model calls, no API key.

The ledger is built in a temporary folder from the frozen practice deal (docs and the pinned run file only). Labels are
read only by the scoring step, through the deal guard, as in score_rules. Each test scripts what an agent might say;
the point is what the code does with it: accept supported verdicts, reject unsupported or uncited ones, stop at the
bounds, and judge the run against the decision rule.
"""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import agent
import agent_compare
import config
import ledger
import ledger_consolidate
import ledger_import

SLUG = "practice_cases"
REAL_DATA, REAL_RESULTS = config.DATA_DIR, config.RESULTS_DIR
NOTE_POLYGON = ("| CAP-021 On-chain wallet screening integration | Singapore, NUSD on Polygon, real-time | "
                "Beta; requires named approval | No named exception approved for Tidewater Pay |")


def tool(name, input_, n):
    return NS(type="tool_use", id=f"t{n}", name=name, input=input_)


def response(blocks):
    return NS(content=blocks, usage=NS(input_tokens=2000, output_tokens=300), stop_reason="tool_use")


class FakeClient:
    def __init__(self, turns):
        self.turns, self.calls = list(turns), 0
        self.messages = self

    def create(self, **kwargs):
        self.calls += 1
        if not self.turns:
            return response([tool("search_catalogue", {"words": ["again"]}, 900 + self.calls)])
        return response(self.turns.pop(0))


def verdict(key, **kw):
    return {"commitment_key": key, "rationale": "scripted", "pricing_note_line": None, **kw}


def good_verdicts(keys):
    """What a careful agent would submit for the escalated practice commitments, keyed by a quote fragment."""
    k = keys
    return [
        verdict(k["instant risk check"], capability_id="CAP-021", network="Polygon", mode="real_time",
                term_evidence=[{"term": "capability", "phrase": "risk check before funds move"},
                               {"term": "network", "phrase": "Polygon wallet"}, {"term": "mode", "phrase": "instant"}],
                catalogue_path="CAP-021/SG/Polygon/NUSD/real_time", pricing_note_line=NOTE_POLYGON,
                authorisation="no_approval_evidence"),
        verdict(k["Tron wallets"], capability_id="CAP-021", network="Tron",
                term_evidence=[{"term": "capability", "phrase": "pre-release checks"},
                               {"term": "network", "phrase": "Tron wallets"}],
                catalogue_path="CAP-021/SG/Tron", authorisation="no_approval_evidence"),
        verdict(k["risk-checked live"], capability_id="CAP-021", network="Ethereum", mode="real_time",
                term_evidence=[{"term": "capability", "phrase": "risk-checked"}, {"term": "network", "phrase": "Ethereum payouts"},
                               {"term": "mode", "phrase": "live before release"}],
                catalogue_path="CAP-021/SG/Ethereum/NUSD/real_time", authorisation="standard_authorised"),
        verdict(k["sanctions checks"], capability_id="CAP-007", quantity={"value": 120000, "unit": "screenings", "period": "day"},
                term_evidence=[{"term": "capability", "phrase": "sanctions checks"},
                               {"term": "quantity", "phrase": "120,000 sanctions checks every day"}],
                catalogue_path="CAP-007/SG", authorisation="no_approval_evidence"),
        verdict(k["30k payouts"], capability_id="CAP-023", quantity={"value": 30000, "unit": "payouts", "period": "day"},
                term_evidence=[{"term": "capability", "phrase": "absorb around 30k payouts a day"},
                               {"term": "quantity", "phrase": "30k payouts a day"}],
                catalogue_path="CAP-023/SG", authorisation="no_approval_evidence"),
        verdict(k["Counterparty data sharing"], capability_id="CAP-024", region="SG",
                term_evidence=[{"term": "capability", "phrase": "Counterparty data sharing with exchanges"},
                               {"term": "region", "phrase": "in Singapore"}],
                catalogue_path="CAP-024/SG", authorisation="no_approval_evidence"),
        verdict(k["audit trail"], capability_id="CAP-014",
                term_evidence=[{"term": "capability", "phrase": "full audit trail on every case"}],
                catalogue_path="CAP-014/SG", authorisation="standard_authorised"),
    ]


class AgentCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        data, results = root / "data", root / "results"
        shutil.copytree(REAL_DATA / SLUG / "docs", data / SLUG / "docs")
        shutil.copyfile(REAL_DATA / "catalogue.json", data / "catalogue.json")
        results.mkdir()
        name = config.LEDGER_IMPORT_RUN_FILES[SLUG]
        shutil.copyfile(REAL_RESULTS / name, results / name)
        self.results = results
        for attr, value in (("DATA_DIR", data), ("RESULTS_DIR", results), ("LEDGER_DEALS", [SLUG])):
            patcher = mock.patch.object(config, attr, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.conn = ledger.open_ledger(root / "ledger.sqlite")
        self.addCleanup(self.conn.close)
        ledger_import.import_all(self.conn)
        ledger_consolidate.consolidate_all(self.conn, assess=True)
        review = self.conn.execute("SELECT MAX(review_id) FROM commitment_assessments").fetchone()[0]
        self.items = agent.escalated_items(self.conn, review)
        self.keys = {frag: next(i["commitment_key"] for i in self.items if any(frag in s["quote"] for s in i["statements"]))
                     for frag in ("instant risk check", "Tron wallets", "risk-checked live", "sanctions checks",
                                  "30k payouts", "Counterparty data sharing", "audit trail")}

    def compare(self, turns_per_run, runs=1):
        clients = [FakeClient(t) for t in turns_per_run]
        real = agent.run_agent
        with mock.patch.object(agent, "run_agent", side_effect=lambda client, *a, **k: real(clients.pop(0), *a, **k)):
            return agent_compare.compare(None, self.conn, runs, data_dir=REAL_DATA, results_dir=REAL_RESULTS)


class TestEscalation(AgentCase):
    def test_only_firm_unknown_commitments_are_escalated_with_their_context(self):
        self.assertEqual(len(self.items), 7)
        tron = next(i for i in self.items if i["commitment_key"] == self.keys["Tron wallets"])
        self.assertIn("instant risk check", tron["statements"][0]["context"])  # the preceding call turn

    def test_the_agent_input_never_contains_labels(self):
        message = agent._user_message(self.items, {"capabilities": []})
        self.assertNotIn("overcommitment", message)
        self.assertNotIn("PC1", message)


class TestValidation(AgentCase):
    def setUp(self):
        super().setUp()
        import json, terms
        self.catalogue = json.loads((config.DATA_DIR / "catalogue.json").read_text(encoding="utf-8"))
        self.vocab = terms.build_vocabulary(self.catalogue)
        review = self.conn.execute("SELECT MAX(review_id) FROM commitment_assessments").fetchone()[0]
        self.notes = agent.review_notes(self.conn, review)
        self.item = {i["commitment_key"]: i for i in self.items}

    def check(self, v):
        return agent.validate(v, self.item[v["commitment_key"]], self.catalogue, self.vocab, self.notes)

    def test_every_careful_verdict_is_accepted(self):
        for v in good_verdicts(self.keys):
            result = self.check(v)
            self.assertTrue(result["accepted"], (v["commitment_key"], result["problems"]))
        tron = self.check(good_verdicts(self.keys)[1])
        self.assertTrue(tron["absolute_limit"])

    def test_a_verdict_its_own_evidence_does_not_support_is_rejected(self):
        v = good_verdicts(self.keys)[0]
        v["authorisation"] = "standard_authorised"
        result = self.check(v)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["expected"], "no_approval_evidence")

    def test_an_invented_phrase_is_rejected(self):
        v = good_verdicts(self.keys)[0]
        v["term_evidence"][2]["phrase"] = "in real time"
        self.assertFalse(self.check(v)["accepted"])

    def test_a_verdict_without_a_catalogue_path_is_uncited(self):
        v = good_verdicts(self.keys)[4]
        v["catalogue_path"] = None
        self.assertTrue(any(p.startswith("uncited") for p in self.check(v)["problems"]))

    def test_a_volume_in_the_wrong_unit_cannot_claim_a_limit_breach(self):
        v = good_verdicts(self.keys)[3]
        v["quantity"]["unit"] = "checks"
        self.assertEqual(self.check(v)["expected"], "standard_authorised")
        self.assertFalse(self.check(v)["accepted"])


class TestCompare(AgentCase):
    def careful_run(self):
        return [[tool("get_pricing_note", {}, 1), tool("get_capability", {"capability_id": "CAP-021"}, 2)],
                [tool("submit_verdict", v, 10 + n) for n, v in enumerate(good_verdicts(self.keys))]]

    def test_a_careful_agent_adds_the_five_missed_approval_issues_and_meets_conditions_1_and_2(self):
        report = self.compare([self.careful_run()])
        judged = report["deals"][SLUG]["judged"][0]
        self.assertEqual(sorted(a["label"] for a in judged["added_material"]), ["PC1", "PC10", "PC3", "PC7", "PC9"])
        self.assertEqual((judged["false_flags"], judged["unsupported"], judged["uncited"]), ([], [], []))
        self.assertTrue(report["decision"]["condition_1_adds_material_issue"])
        self.assertTrue(report["decision"]["condition_2_no_unsupported_or_uncited"])
        self.assertEqual(judged["tool_calls"], 9)

    def test_one_overreaching_verdict_fails_condition_2(self):
        run = self.careful_run()
        bad = good_verdicts(self.keys)
        bad[6]["authorisation"] = "no_approval_evidence"  # audit trail is standard: an unsupported flag
        run[1] = [tool("submit_verdict", v, 10 + n) for n, v in enumerate(bad)]
        report = self.compare([run])
        self.assertFalse(report["decision"]["condition_2_no_unsupported_or_uncited"])
        self.assertFalse(report["decision"]["keep_agent"])

    def test_an_agent_that_never_finishes_is_capped_and_fails_condition_3(self):
        report = self.compare([[]])
        judged = report["deals"][SLUG]["judged"][0]
        self.assertTrue(judged["status"].startswith("capped"))
        self.assertLessEqual(judged["tool_calls"], config.AGENT_MAX_TOOL_CALLS_PER_DEAL + 1)
        self.assertFalse(report["decision"]["condition_3_within_bounds"])

    def test_variation_across_runs_is_recorded(self):
        run2 = self.careful_run()
        cautious = good_verdicts(self.keys)
        cautious[0] = verdict(self.keys["instant risk check"], capability_id=None, term_evidence=[],
                              catalogue_path=None, authorisation="unknown_needs_review")
        run2[1] = [tool("submit_verdict", v, 10 + n) for n, v in enumerate(cautious)]
        report = self.compare([self.careful_run(), run2], runs=2)
        varied = {k: v for k, v in report["deals"][SLUG]["variation"].items() if len(v) > 1}
        self.assertEqual(varied, {self.keys["instant risk check"]: ["no_approval_evidence", "unknown_needs_review"]})

    def test_the_report_is_written_once_and_never_overwritten(self):
        report = self.compare([self.careful_run()])
        now = __import__("datetime").datetime(2026, 10, 3, tzinfo=__import__("datetime").timezone.utc)
        agent_compare.write_report(report, results_dir=self.results, now=now)
        with self.assertRaises(FileExistsError):
            agent_compare.write_report(report, results_dir=self.results, now=now)

    def test_the_cli_refuses_without_a_key(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertEqual(agent_compare.main([]), 2)


if __name__ == "__main__":
    unittest.main()
