"""Closing lines and closed commitments (20 Oct): what changed vs what was checked with it, and the contract wording a closed gap
now finds. No model is called: a scripted client returns the saved run-1 findings, in a scratch cache, so nothing scripted can ever
reach the repo's real reading cache (results/v2_cache)."""

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
import detect_v2
import handover
import ledger
import ledger_fixes
import reset_demo
import workspace
from test_noma_journeys import FakeClient

SCEN = config.DATA_DIR / "scenarios"
RUN1 = config.RESULTS_DIR / "v2_demo_noma_journeys_20261020T091857Z.json"


def doc(text, label="Draft contract", type_="draft_contract", key="NJ-07"):
    return {"text": text, "label": label, "key": key, "type": type_}


class TestMatchingContractWording(unittest.TestCase):
    CONTRACT = ("# DRAFT Master Services Agreement\\n\\n**Clause 3. Services.** Provider will perform the services.\\n\\n"
                "**Clause 4. Languages.** The Assistant will respond to Guest enquiries in 12 languages, listed in Schedule 1. "
                "Other terms apply.\\n").replace("\\n", "\n")

    def test_a_closed_conflict_finds_the_sentence_with_the_promised_value_without_the_clause_heading(self):
        got = workspace.matching_contract_wording({"kind": "conflicting_terms", "promised_value": "12 languages"}, [doc(self.CONTRACT)])
        self.assertEqual(got, {"target": "12 languages", "document": "Draft contract",
                               "quote": "The Assistant will respond to Guest enquiries in 12 languages, listed in Schedule 1."})
        self.assertIn(got["quote"], self.CONTRACT)  # verbatim, so the document view can highlight it

    def test_a_closed_gap_finds_a_sentence_with_one_of_the_searched_phrases(self):
        sow = doc("## 2. Coaching\n\nProvider will provide BioCatch coaching detection at launch.\n", "Draft SOW", "draft_sow", "AB-06")
        got = workspace.matching_contract_wording({"kind": "contract_gap", "missing_phrases": ["nothing like this", "BioCatch"]}, [sow])
        self.assertEqual((got["target"], got["document"]), ("BioCatch", "Draft SOW"))

    def test_nothing_found_or_another_kind_gives_none(self):
        self.assertIsNone(workspace.matching_contract_wording({"kind": "conflicting_terms", "promised_value": "99 languages"}, [doc(self.CONTRACT)]))
        self.assertIsNone(workspace.matching_contract_wording({"kind": "approval_required"}, [doc(self.CONTRACT)]))
        self.assertIsNone(workspace.matching_contract_wording({"kind": "contract_gap", "missing_phrases": []}, [doc(self.CONTRACT)]))
        self.assertIsNone(workspace.matching_contract_wording({}, []))


class TestTheNomaRehearsalReplayed(unittest.TestCase):
    """The demo order on a scratch ledger: pricing note, then the revised contract."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.cache = mock.patch.object(config, "V2_CACHE_DIR", Path(cls.tmp.name) / "cache")
        cls.cache.start()
        db = Path(cls.tmp.name) / "l.sqlite"
        reset_demo.reset(db_path=db)
        cls.conn = ledger.connect(db)
        run = json.loads(RUN1.read_text(encoding="utf-8"))["deals"][0]
        client = FakeClient([{k: v for k, v in f.items() if k != "problems"} for f in run["accepted"]])
        for key, name in (("NJ-05", "NJ-05_v2_named_exception.md"), ("NJ-07", "NJ-07_v2_languages_aligned.md")):
            ledger_fixes.add_source_version(cls.conn, "noma_journeys", key, (SCEN / name).read_text(encoding="utf-8"), name)
            deal_catalogue.recheck(cls.conn, "noma_journeys", None, client)
        cls.ov = workspace.overview(cls.conn, "noma_journeys")

    @classmethod
    def tearDownClass(cls):
        cls.cache.stop()
        cls.conn.close()
        cls.tmp.cleanup()

    def commitment(self, word):
        return next(c for c in self.ov["commitments"] if word in c["name"].lower())

    def closed(self, word):
        return next(i for i in self.commitment(word)["issues"] if i["state"] == "Resolved")["resolved_by"]

    def test_the_changed_document_closed_it_and_the_unchanged_one_was_only_checked_with(self):
        r = self.closed("12 languages")
        self.assertEqual((r["changed"], r["unchanged"]), (["Draft contract, version 2"], ["Draft SOW, version 1"]))
        self.assertEqual(r["text"].split(" · ")[:2], ["Resolved by Draft contract, version 2", "Draft SOW, version 1 unchanged"])
        self.assertEqual({d["label"] for d in r["documents"]}, {"Draft contract, version 2", "Draft SOW, version 1"})  # the full list is kept

    def test_when_one_document_is_all_there_is_nothing_is_marked_unchanged(self):
        r = self.closed("launch specialist")
        self.assertEqual((r["changed"], r["unchanged"]), (["Pricing and services note, version 2"], []))
        self.assertNotIn("unchanged", r["text"])

    def test_the_closed_languages_commitment_has_the_wording_now_found(self):
        self.assertEqual(self.commitment("12 languages")["contract_now"],
                         {"target": "12 languages", "document": "Draft contract",
                          "quote": "The Assistant will respond to Guest enquiries in 12 languages, listed in Schedule 1."})
        self.assertIsNone(self.commitment("phone calls")["contract_now"])  # nothing closed there
        self.assertIsNone(self.commitment("launch specialist")["contract_now"])  # its closed gap was an approval, not wording

    def test_new_snapshots_store_what_a_closed_commitment_was_told_and_what_the_contract_says_now(self):
        snap = handover.build_snapshot(self.conn, "noma_journeys", "Priya Nair")
        item = next(i for i in snap["closed_items"] if "12 languages" in i["promise"])
        self.assertTrue(item["quotes"])
        self.assertEqual(item["contract_now"]["target"], "12 languages")
        self.assertEqual(item["first_found"], {"doc_type_label": "RFP response", "date": "2026-09-28"})
        self.assertTrue(all(i["promise"] for i in snap["closed_items"]))
        self.assertIn("Draft SOW, version 1 unchanged", next(r for r in snap["resolved"] if "12 languages" in r["promise"])["resolved_by"])

    def test_the_phone_commitment_still_carries_its_open_gaps(self):
        kinds = {i["finding"] for i in self.commitment("phone calls")["issues"] if i["state"] != "Resolved"}
        self.assertLessEqual({"Not offered", "Contract says something different"}, kinds)


if __name__ == "__main__":
    unittest.main()
