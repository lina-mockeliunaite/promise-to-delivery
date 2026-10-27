"""The Noma filing flow, replayed on a scratch ledger (20 Oct): the right filing gives the designed outcome; the wrong filing from the
rehearsal (the revised contract filed as a new version of the SOW, the revised pricing note as a new "Proposal") gives a different,
wrong one. That is why the add form questions such a filing (frontend/tests/noma_flow.test.mjs checks the questions themselves).
No model is called: a scripted client returns the saved run-1 findings, in a scratch cache."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
import deal_catalogue
import ledger
import ledger_fixes
import reset_demo
import workspace
from test_noma_journeys import FakeClient

SCEN = config.DATA_DIR / "scenarios"
RUN1 = config.RESULTS_DIR / "v2_demo_noma_journeys_20261020T091857Z.json"
CONTRACT_V2 = (SCEN / "NJ-07_v2_languages_aligned.md").read_text(encoding="utf-8")
PRICING_V2 = (SCEN / "NJ-05_v2_named_exception.md").read_text(encoding="utf-8")


class Replay(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        cache = mock.patch.object(config, "V2_CACHE_DIR", Path(tmp.name) / "cache")
        cache.start()
        self.addCleanup(cache.stop)
        db = Path(tmp.name) / "l.sqlite"
        reset_demo.reset(db_path=db)
        self.conn = ledger.connect(db)
        self.addCleanup(self.conn.close)
        run = json.loads(RUN1.read_text(encoding="utf-8"))["deals"][0]
        self.client = FakeClient([{k: v for k, v in f.items() if k != "problems"} for f in run["accepted"]])

    def recheck(self):
        deal_catalogue.recheck(self.conn, "noma_journeys", None, self.client)

    def states(self):
        out = {}
        for c in workspace.overview(self.conn, "noma_journeys")["commitments"]:
            for i in c["issues"]:
                out[(c["display_name"].split()[0] + " " + c["display_name"].split()[1], i["finding"])] = i["state"]
        return out

    def filed(self, source_key, text, name):
        ledger_fixes.add_source_version(self.conn, "noma_journeys", source_key, text, name)
        self.recheck()


class TestTheRightFiling(Replay):
    def test_each_document_goes_to_the_document_it_revises_and_the_design_holds(self):
        self.filed("NJ-05", PRICING_V2, "NJ-05_v2_named_exception.md")  # the pricing note, as a new version of the pricing note
        self.filed("NJ-07", CONTRACT_V2, "NJ-07_v2_languages_aligned.md")  # the contract, as a new version of the Draft contract
        s = self.states()
        self.assertEqual(s[("Support in", "Contract says something different")], "Resolved")  # the languages gap: closed by the contract
        self.assertEqual(s[("Dedicated launch", "No approval recorded")], "Resolved")  # the approval: closed by the pricing note
        self.assertEqual(s[("Dedicated launch", "Missing from contract")], "Needs action")  # what Delivery inherits
        self.assertEqual(s[("AI answers", "Contract says something different")], "Needs action")  # the SOW still says chat and email
        self.assertEqual(s[("AI answers", "Not offered")], "Needs action")


class TestTheWrongFilingFromTheRehearsal(Replay):
    def test_the_contract_filed_as_the_sow_closes_the_wrong_finding_and_leaves_the_right_one_open(self):
        self.filed("NJ-06", CONTRACT_V2, "NJ-07_v2_languages_aligned.md")  # the revised contract as a new version of the Draft SOW
        s = self.states()
        # The SOW's wording is gone, so the phone commitment's "contract differs" finding closes: wrongly.
        self.assertEqual(s[("AI answers", "Contract says something different")], "Resolved")
        # The Draft contract still says four languages, so the languages gap that the file was meant to close stays open.
        self.assertEqual(s[("Support in", "Contract says something different")], "Needs action")

    def test_the_pricing_note_filed_as_a_proposal_does_not_close_the_approval_gap(self):
        ledger_fixes.add_source(self.conn, "noma_journeys", "NJ-05_v2_named_exception.md", PRICING_V2, "NJ-05_v2_named_exception.md",
                                "proposal", "2026-10-18")
        self.recheck()
        self.assertEqual(self.states()[("Dedicated launch", "No approval recorded")], "Needs action")


class TestTheRefusalNamesTheLikelyCause(unittest.TestCase):
    """21 Oct: the mistaken filing from the rehearsal. The pricing note, filed as a new document, needs no model, so it goes in silently and
    sits beside the original, dated today. The revised contract is then refused (its reading was made without that duplicate). The refusal
    now says why, and nothing is added."""

    def run_flow(self, mistaken_steps):
        import os
        import api
        import test_cached_guard as g
        from fastapi.testclient import TestClient
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "cache"
            g.flow("noma_journeys", g.noma_steps()[:2], g.clean(g.NOMA), True, cache, tmp)  # the designed flow fills the scratch cache
            with mock.patch.dict(os.environ, {}, clear=False), mock.patch.object(config, "V2_CACHE_DIR", cache):
                os.environ.pop("ANTHROPIC_API_KEY", None)
                db = g.scratch_ledger(tmp, "mistaken.sqlite")
                client = TestClient(api.create_app(dist_dir=Path(tmp) / "no-dist", ledger_path=db), base_url="http://127.0.0.1")
                out = []
                for payload in mistaken_steps:
                    before = ledger.connect(db).execute("SELECT COUNT(*) FROM source_versions").fetchone()[0]
                    r = client.post("/api/deals/noma_journeys/documents/add-and-check", json=payload, headers=g.H)
                    after = ledger.connect(db).execute("SELECT COUNT(*) FROM source_versions").fetchone()[0]
                    out.append((r.status_code, r.json().get("detail", ""), after - before))
                return out

    def test_the_pricing_note_as_a_new_document_then_the_contract_as_a_new_version(self):
        mistaken = [
            {"name": "NJ-05_v2_named_exception.md", "filename": "NJ-05_v2_named_exception.md", "doc_type": "pricing_services_note",
             "doc_date": "2026-10-21", "text": PRICING_V2},
            {"source_key": "NJ-07", "filename": "NJ-07_v2_languages_aligned.md", "text": CONTRACT_V2}]
        pricing, contract = self.run_flow(mistaken)
        self.assertEqual((pricing[0], pricing[2]), (200, 1))  # no model needed, so it goes in, beside the original
        self.assertEqual((contract[0], contract[2]), (409, 0))  # refused, nothing added
        self.assertIn("Nothing was added.", contract[1])
        self.assertIn("was added earlier as a new document, dated the day it was added, next to Internal approvals note", contract[1])
        self.assertIn("A new version of: Internal approvals note", contract[1])

    def test_the_contract_itself_as_a_new_document_says_it_would_sit_next_to_the_draft_contract(self):
        mistaken = [{"name": "NJ-07_v2_languages_aligned.md", "filename": "NJ-07_v2_languages_aligned.md", "doc_type": "draft_contract",
                     "doc_date": "2026-10-21", "text": CONTRACT_V2}]
        (contract,) = self.run_flow(mistaken)
        self.assertEqual((contract[0], contract[2]), (409, 0))
        self.assertIn("This file would be added as a new document dated today, next to Draft contract.", contract[1])
        self.assertIn("choose “A new version of: Draft contract”", contract[1])

    def test_the_designed_flow_gets_no_hint_because_it_is_not_refused(self):
        designed = [{"source_key": "NJ-05", "filename": "NJ-05_v2_named_exception.md", "text": PRICING_V2},
                    {"source_key": "NJ-07", "filename": "NJ-07_v2_languages_aligned.md", "text": CONTRACT_V2}]
        results = self.run_flow(designed)
        self.assertEqual([r[0] for r in results], [200, 200])


if __name__ == "__main__":
    unittest.main()
