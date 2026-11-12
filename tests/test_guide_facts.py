"""The demo bar's guide (11 Nov) states facts: its tour captions and its hint lines. Each one is checked here against the deal's own data, so the
wording can never drift from the findings. Runs on a temporary ledger built from the saved v2 output; nothing is written outside it."""

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

import api
import config
import deal_catalogue
import reset_demo

ROOT = Path(__file__).resolve().parents[1]
DOCS = lambda deal, name: (config.DATA_DIR / deal / "docs" / name).read_text(encoding="utf-8")
_t = {}


def setUpModule():
    tmp = tempfile.TemporaryDirectory()
    _t["tmp"] = tmp
    db = Path(tmp.name) / "ledger.sqlite"
    reset_demo.reset(db)
    _t["client"] = TestClient(api.create_app(dist_dir=Path(tmp.name) / "x", ledger_path=db, public=True), base_url="http://127.0.0.1")


def tearDownModule():
    _t["tmp"].cleanup()


def reg(deal):
    return _t["client"].get(f"/api/deals/{deal}/register").json()


def row(deal, pattern):
    return next(c for c in reg(deal)["commitments"] if re.search(pattern, f"{c['display_name']} {c['name']}", re.I))


def types(c):
    return sorted((i["type"], bool(i["absolute_limit"])) for i in c["issues"] if i["state"] != "Resolved")


def js_text(name):
    return (ROOT / "frontend" / "src" / name).read_text(encoding="utf-8")


class TestNomaHints(unittest.TestCase):
    def test_the_specialist_hint_names_the_sources_the_drawer_lists_and_the_rest_is_in_the_findings(self):
        c = row("noma_journeys", "launch specialist")
        # The drawer's "Source: RFP response, 28 Sep · also in Proposal, 5 Oct" is the statements' found_in, earliest first. The hint says the same
        # sources in the same order: "Promised in the RFP and again in the proposal".
        listed = []
        for st in c["statements"]:
            for f in st["found_in"]:
                if f["doc_type_label"] not in listed:
                    listed.append(f["doc_type_label"])
        self.assertEqual(listed, ["RFP response", "Proposal"])
        hint = re.search(r'"(Promised in the [^"]*)"', js_text("demo.js")).group(1)
        self.assertTrue(hint.startswith("Promised in the RFP and again in the proposal, never approved, not in the contract."), hint)
        words = {"RFP response": "RFP", "Proposal": "proposal"}
        mentioned = [w for w in re.findall(r"\b(RFP|proposal)\b", hint.split(", never")[0])]
        self.assertEqual(mentioned, [words[l] for l in listed])  # the hint's sources equal the drawer's listed sources, in order
        self.assertIn("No named exception approved", DOCS("noma_journeys", "NJ-05_pricing_services_note.md"))  # never approved
        c = row("noma_journeys", "launch specialist")
        self.assertEqual(types(c), [("approval", False), ("contract_gap", False)])  # approval missing; not in the contract
        for name in ("NJ-06_draft_sow.md", "NJ-07_draft_contract.md"):
            self.assertNotIn("launch specialist", DOCS("noma_journeys", name).lower(), name)

    def test_languages_were_promised_as_12_and_the_draft_contract_says_four(self):
        c = row("noma_journeys", "12 languages")
        self.assertEqual(types(c), [("conflicting_terms", False)])
        self.assertIn("four languages", DOCS("noma_journeys", "NJ-07_draft_contract.md"))
        self.assertIn("12 languages", DOCS("noma_journeys", "NJ-04_proposal.md"))
        self.assertIn("four", c["contract"].lower())

    def test_voice_is_not_offered_so_no_document_can_fix_it(self):
        c = row("noma_journeys", "phone")
        self.assertIn(("approval", True), types(c))  # an absolute limit: "Not offered"
        cat = json.loads((config.DATA_DIR / "catalogue_aivuna.json").read_text(encoding="utf-8"))
        self.assertIn("Voice (phone) support is not offered", cat["unlisted_rule"])
        issue = next(i for i in c["issues"] if i["absolute_limit"])
        self.assertEqual(issue["finding"], "Not offered")


class TestAlderHints(unittest.TestCase):
    def test_coaching_detection_needs_a_named_approval_for_a_beta_connector_and_the_sow_does_not_mention_it(self):
        c = row("alder_bank", "coaching")
        self.assertEqual(types(c), [("approval", False), ("contract_gap", False)])
        cap = next(x for x in json.loads((config.DATA_DIR / "catalogue.json").read_text(encoding="utf-8"))["capabilities"] if x["id"] == "CAP-027")
        self.assertEqual((cap["regions"]["AU"]["status"], cap["regions"]["AU"]["sellable"]), ("beta", "requires_named_approval"))
        sow = DOCS("alder_bank", "AB-06_draft_sow.md").lower()
        self.assertNotIn("coaching", sow); self.assertNotIn("biocatch", sow)

    def test_the_second_coaching_step_follows_the_approval_with_the_contract_gap_still_open(self):
        sow2 = (config.SCENARIOS_DIR / "AB-06_v2_coaching_added.md").read_text(encoding="utf-8").lower()
        self.assertIn("coaching", sow2)  # the revised SOW is what closes the gap the hint names
        approval = (config.SCENARIOS_DIR / "AB-05_v2_named_exception.md").read_text(encoding="utf-8")
        self.assertIn("Named exception approved", approval)

    def test_the_signed_step_names_the_later_date_the_shipped_signed_contract_sets_and_does_not_describe_the_check_as_comparing_dates(self):
        signed = (config.SCENARIOS_DIR / "AB-09_signed_contract.md").read_text(encoding="utf-8")
        self.assertIn("will be enabled from 1 May 2027", signed)  # the date the hint and the summary name
        self.assertEqual(signed.lower().count("biocatch"), 1)
        for text in (js_text("demo.js"), (config.ROOT / "public_demo.py").read_text(encoding="utf-8")):
            self.assertNotRegex(text.lower(), r"compar\w* (the )?(dates?|terms)")

    def test_azure_is_not_a_supported_cloud_the_sow_says_aws_sydney_and_the_note_is_the_fix(self):
        c = row("alder_bank", "hosting")
        self.assertIn(("approval", True), types(c))
        cap = next(x for x in json.loads((config.DATA_DIR / "catalogue.json").read_text(encoding="utf-8"))["capabilities"] if x["id"] == "CAP-019")
        self.assertEqual(cap["regions"]["AU"]["limits"]["supported_clouds"], ["AWS", "GCP"])
        self.assertIn("Amazon Web Services in the Sydney region", DOCS("alder_bank", "AB-06_draft_sow.md"))
        self.assertIn("Elva", deal_catalogue.vendor_name("alder_bank"))  # "Elva doesn't offer Azure hosting"
        self.assertIn("AWS Sydney", js_text("demo.js"))  # the sample note the visitor records


class TestTourCaptionFacts(unittest.TestCase):
    def test_what_each_caption_states_is_in_the_deal(self):
        facts = {"noma_journeys": ("Aivuna", "told our leadership", "NJ-01_discovery_call.md"), "alder_bank": ("Elva", "told our board", "AB-01_discovery_call.md")}
        for deal, (vendor, told, call) in facts.items():
            r = reg(deal)
            self.assertEqual(deal_catalogue.vendor_name(deal), vendor, deal)
            self.assertIn(told, DOCS(deal, call), deal)  # "the go-live <customer> has promised its leadership / its board"
            self.assertEqual(r["brief"]["go_live"], "2027-02-01", deal)  # "1 February"
            self.assertEqual(r["stage"]["current"], "contracting", deal)  # "We're at Contracting"
            self.assertEqual(r["stage"]["current_label"], "Contracting", deal)
            self.assertEqual(len(r["open_rows"]), 3, deal)  # "Three need attention"
            self.assertIn(vendor, js_text("demo.js")); self.assertIn("its leadership" if deal == "noma_journeys" else "its board", js_text("demo.js"))

    def test_the_hint_lines_in_the_front_end_are_the_ones_checked_here(self):
        demo = js_text("demo.js")
        for fragment in ("Promised in the RFP and again in the proposal, never approved, not in the contract.", "Told 12 languages; the draft contract says four.",
                         "Aivuna doesn't offer voice, so no document can fix this.", "which is in beta and needs a named approval; the SOW doesn't mention it.",
                         "Elva doesn't offer Azure hosting, so no document can fix this. The customer agreed AWS Sydney on a call: record it as a note."):
            self.assertIn(fragment, demo)


if __name__ == "__main__":
    unittest.main()
