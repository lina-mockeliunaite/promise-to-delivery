"""Noma Journeys demo deal (20 Oct; Aivuna's catalogue): the documents support every intended finding in
data/noma_journeys/BRIEF.md, and the update documents close exactly what they should. Deterministic: hand-written findings
through the frozen v2 verifier, no model call. This checks the scenario is built right; whether the model finds the gaps is
the separate demo run (step 3), and nothing here is an app outcome."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import catalogue_store
import config
import deal_catalogue
import detect_v2
import ledger
import ledger_fixes
import ledger_v2
import workspace

SCEN = config.DATA_DIR / "scenarios"
LANG_PROMISE = ("NJ-04", "Aivuna will support guest conversations in 12 languages from the 1 February 2027 launch, including "
                         "English, Mandarin Chinese, Japanese and Korean.")
LANG_CONTRACT = {"source_id": "NJ-07", "quote": "The Assistant will respond to Guest enquiries in four languages: English, "
                                                "Mandarin Chinese, Japanese and Korean."}
SPECIALIST = ("NJ-03", "A dedicated Aivuna launch specialist will work with Noma Journeys for the first 30 days after launch at no extra charge.")
PHONE = ("NJ-03", "Aivuna's assistant will answer guests' phone calls and respond to chat and email from the 1 February 2027 launch.")


def finding(kind, quotes, **kw):
    base = dict(kind=kind, commitment="c", promise_quotes=[{"source_id": s, "quote": q} for s, q in quotes],
                catalogue_path=None, unlisted_value=None, limit_name=None, promised_quantity=None, missing_phrases=[],
                contract_quote=None, note_quote=None, subject=None, promised_value=None, contract_value=None, reason="r")
    base.update(kw)
    return base


LANGUAGES = finding("conflicting_terms", [LANG_PROMISE], commitment="Support in 12 languages at launch", subject="languages",
                    promised_value="12 languages", contract_value="four languages", contract_quote=LANG_CONTRACT)
APPROVAL = finding("approval_required", [SPECIALIST], commitment="Dedicated launch specialist", catalogue_path="CAP-008/SG",
                   note_quote={"source_id": "NJ-05", "quote": "No named exception approved for Noma Journeys"})
SPEC_GAP = finding("contract_gap", [SPECIALIST], commitment="Dedicated launch specialist",
                   missing_phrases=["launch specialist", "first 30 days"])
VOICE = finding("absolute_limit", [PHONE], commitment="AI answers phone calls at launch", catalogue_path="CAP-003/SG",
                unlisted_value="phone calls")
INTENDED = [("languages conflict", LANGUAGES), ("specialist approval", APPROVAL), ("specialist contract gap", SPEC_GAP),
            ("voice not offered", VOICE)]


class TestNomaScenario(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cat = json.loads((config.DATA_DIR / "catalogue_aivuna.json").read_text(encoding="utf-8"))
        cls.docs = detect_v2.deal_documents("noma_journeys")

    def swap(self, docs, sid, name):
        return [dict(d, text=(SCEN / name).read_text(encoding="utf-8")) if d["source_id"] == sid else d for d in docs]

    def test_every_intended_finding_verifies_on_the_original_documents(self):
        for name, f in INTENDED:
            self.assertEqual(detect_v2.verify(f, self.docs, self.cat), [], name)

    def test_what_the_catalogue_offers_is_not_reported(self):
        offered = finding("absolute_limit", [LANG_PROMISE], catalogue_path="CAP-002/SG", unlisted_value="Mandarin Chinese")
        chat = finding("absolute_limit", [PHONE], catalogue_path="CAP-003/SG", unlisted_value="chat")
        self.assertIn("listed", detect_v2.verify(offered, self.docs, self.cat)[0])
        self.assertIn("listed", detect_v2.verify(chat, self.docs, self.cat)[0])

    def test_the_catalogue_says_voice_is_not_offered_in_the_unlisted_rule_not_in_the_region_entry(self):
        # An explicit voice entry would make the verifier reject the "not offered" finding (the word would be "listed").
        self.assertIn("Voice (phone) support is not offered", self.cat["unlisted_rule"])
        region = json.dumps(next(c for c in self.cat["capabilities"] if c["id"] == "CAP-003")["regions"]["SG"]).lower()
        self.assertNotIn("voice", region)
        self.assertNotIn("phone", region)

    def test_the_catalogue_has_the_shape_of_elvas_and_ten_capabilities(self):
        elva = json.loads((config.DATA_DIR / "catalogue.json").read_text(encoding="utf-8"))
        self.assertEqual(set(self.cat), set(elva) | {"vendor"})
        self.assertEqual(len(self.cat["capabilities"]), 10)
        self.assertEqual(self.cat["coverage"], "complete")
        self.assertEqual(len(next(c for c in self.cat["capabilities"] if c["id"] == "CAP-002")["regions"]["SG"]["limits"]["supported_languages"]), 12)
        view = catalogue_store.view(None, "aivuna")
        self.assertEqual((view["vendor_name"], view["can_add"], len(view["capabilities"])), ("Aivuna", False, 10))
        self.assertIn("Voice (phone) support is not offered", view["unlisted_rule"])

    def test_the_named_exception_closes_only_the_approval(self):
        after = self.swap(self.docs, "NJ-05", "NJ-05_v2_named_exception.md")
        self.assertNotEqual(detect_v2.verify(APPROVAL, after, self.cat), [])
        for f in (LANGUAGES, SPEC_GAP, VOICE):
            self.assertEqual(detect_v2.verify(f, after, self.cat), [])

    def test_the_revised_contract_closes_only_the_languages_conflict_and_the_specialist_stays_missing(self):
        after = self.swap(self.swap(self.docs, "NJ-05", "NJ-05_v2_named_exception.md"), "NJ-07", "NJ-07_v2_languages_aligned.md")
        self.assertNotEqual(detect_v2.verify(LANGUAGES, after, self.cat), [])
        self.assertNotEqual(detect_v2.verify(APPROVAL, after, self.cat), [])
        for f in (SPEC_GAP, VOICE):  # what Delivery inherits: the specialist is in no contract document, voice is not offered
            self.assertEqual(detect_v2.verify(f, after, self.cat), [])

    def test_the_signed_contract_matches_the_final_scope_and_still_omits_the_specialist(self):
        signed = (SCEN / "NJ-09_signed_contract.md").read_text(encoding="utf-8").lower()
        self.assertIn("12 languages", signed)
        self.assertNotIn("launch specialist", signed)
        self.assertNotIn("first 30 days", signed)
        for doc in ("NJ-06_draft_sow.md",):
            self.assertNotIn("launch specialist", (config.doc_path("noma_journeys", doc)).read_text(encoding="utf-8").lower())

    def test_schedule_1_lists_exactly_the_catalogues_twelve_languages_in_its_spelling_and_order(self):
        import re
        want = next(c for c in self.cat["capabilities"] if c["id"] == "CAP-002")["regions"]["SG"]["limits"]["supported_languages"]
        self.assertEqual(len(want), 12)
        for name in ("NJ-07_v2_languages_aligned.md", "NJ-09_signed_contract.md"):
            text = (SCEN / name).read_text(encoding="utf-8")
            line = re.search(r"## Schedule 1 — Languages\n\n(.+)\n", text).group(1).rstrip(".")
            self.assertEqual(re.split(r", | and ", line), want, name)

    def test_the_sow_purpose_and_handoff_clause_say_what_was_agreed_and_no_more_scope(self):
        sow = config.doc_path("noma_journeys", "NJ-06_draft_sow.md").read_text(encoding="utf-8")
        self.assertIn("answers guests' questions about bookings, booking changes and refunds", sow)
        self.assertIn("hand over conversations it cannot resolve to the Customer's human agents, with the full conversation attached", sow)

    def test_no_document_makes_a_performance_promise(self):
        import re
        texts = [d["text"] for d in self.docs] + [p.read_text(encoding="utf-8") for p in SCEN.glob("NJ-*.md")]
        for text in texts:
            self.assertIsNone(re.search(r"\d+\s?%|resolve[sd]? \w+ of tickets|within \d+ (seconds|minutes)", text, re.I))

    def test_the_stated_dates_are_the_versions_own_and_in_order(self):
        from workspace import stated_date
        self.assertEqual(stated_date((SCEN / "NJ-05_v2_named_exception.md").read_text()), "2026-10-18")  # pricing note first
        self.assertEqual(stated_date((SCEN / "NJ-07_v2_languages_aligned.md").read_text()), "2026-10-19")
        self.assertEqual(stated_date((SCEN / "NJ-09_signed_contract.md").read_text()), "2026-10-20")
        manifest = json.loads(config.doc_path("noma_journeys", "manifest.json").read_text())["documents"]
        dates = [d["date"] for d in manifest]
        self.assertEqual(dates, sorted(dates))
        for d in manifest:
            self.assertEqual(stated_date(config.doc_path("noma_journeys", d["file"]).read_text()), d["date"], d["file"])


class FakeClient:
    """A scripted stand-in for the model: returns the hand-written findings. Never a real call."""

    def __init__(self, findings):
        self.calls = 0
        self.messages = NS(create=self._create)
        self.findings = findings

    def _create(self, **kw):
        self.calls += 1
        return NS(content=[NS(type="text", text=json.dumps({"findings": self.findings}))], stop_reason="end_turn",
                  usage=NS(input_tokens=1, output_tokens=1, output_tokens_details=None))


class TestNomaInTheLedger(unittest.TestCase):
    """The whole path in a scratch ledger, on Aivuna's catalogue, with scripted findings: closure only by re-verifying."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        for patch in (mock.patch.object(config, "V2_DEALS", ["noma_journeys", "harbour_bank"]),
                      mock.patch.object(config, "V2_CACHE_DIR", Path(tmp.name) / "cache"),
                      mock.patch.dict(config.V2_SEED_FILES, {}, clear=True)):  # scripted findings only: no saved model output
            patch.start()
            self.addCleanup(patch.stop)
        self.conn = ledger.open_ledger(Path(tmp.name) / "l.sqlite")
        self.addCleanup(self.conn.close)
        for slug in ("noma_journeys", "harbour_bank"):
            ledger_v2.import_deal(self.conn, slug)
        self.conn.commit()
        self.client = FakeClient([f for _, f in INTENDED])
        self.path = str(deal_catalogue.path_for("noma_journeys"))

    def states(self):
        return {(c["name"], i["finding"]): i["state"] for c in workspace.overview(self.conn, "noma_journeys")["commitments"] for i in c["issues"]}

    def test_the_first_review_uses_aivunas_catalogue_and_its_hash(self):
        r = ledger_v2.review(self.conn, "noma_journeys", self.client, None, self.path)
        self.assertEqual((r["accepted"], r["rejected"]), (4, 0))
        did = ledger_fixes.deal_id(self.conn, "noma_journeys")
        import integrity
        aivuna = (config.DATA_DIR / "catalogue_aivuna.json").read_bytes()
        review_id = self.conn.execute("SELECT MAX(id) FROM reviews WHERE deal_id = ?", (did,)).fetchone()[0]
        self.assertEqual(integrity.review_config(self.conn, review_id), (integrity.HASH_DEFINITION, integrity.config_sha256(integrity.HASH_DEFINITION, aivuna)))
        self.assertNotEqual(integrity.config_sha256(3, aivuna), integrity.config_sha256(3, (config.DATA_DIR / "catalogue.json").read_bytes()))
        self.assertEqual(ledger_fixes.freshness(self.conn, did)["state"], "Up to date")
        self.assertEqual(workspace.overview(self.conn, "noma_journeys")["check_coverage"], {"rejected": 0})

    def test_an_elva_catalogue_addition_makes_elva_deals_stale_and_leaves_aivuna_alone(self):
        ledger_v2.review(self.conn, "noma_journeys", self.client, None, self.path)
        # Harbour Bank (Elva) gets its own saved reading, checked against Elva's catalogue (restored when the test ends).
        config.V2_SEED_FILES["harbour_bank"] = "v2_dev_20261010T083854Z.json"
        ledger_v2.review(self.conn, "harbour_bank", None, None, None)
        catalogue_store.add_capability(self.conn, {"name": "Test capability", "regions": ["SG"], "status": "beta",
                                                   "sellable": "requires_named_approval", "added_by": "Tester"})
        hb = ledger_fixes.deal_id(self.conn, "harbour_bank")
        nj = ledger_fixes.deal_id(self.conn, "noma_journeys")
        self.assertEqual(ledger_fixes.freshness(self.conn, hb)["state"], "Review out of date")
        self.assertEqual(ledger_fixes.freshness(self.conn, nj)["state"], "Up to date")

    def test_aivunas_catalogue_cannot_be_added_to(self):
        with self.assertRaises(catalogue_store.CatalogueError) as cm:
            catalogue_store.add_capability(self.conn, {"name": "Voice", "regions": ["SG"], "status": "beta",
                                                       "sellable": "standard", "added_by": "Tester"}, "aivuna")
        self.assertEqual(cm.exception.status, 409)

    def test_the_updates_close_exactly_what_they_should_by_re_verifying_stored_claims(self):
        ledger_v2.review(self.conn, "noma_journeys", self.client, None, self.path)
        before = self.states()
        self.assertTrue(all(v == "Needs action" for v in before.values()))
        ledger_fixes.add_source_version(self.conn, "noma_journeys", "NJ-05", (SCEN / "NJ-05_v2_named_exception.md").read_text(), "NJ-05_v2.md")
        deal_catalogue.recheck(self.conn, "noma_journeys", None, self.client)
        after_note = {k: v for k, v in self.states().items() if v == "Resolved"}
        self.assertEqual([k[1] for k in after_note], ["No approval recorded"])
        ledger_fixes.add_source_version(self.conn, "noma_journeys", "NJ-07", (SCEN / "NJ-07_v2_languages_aligned.md").read_text(), "NJ-07_v2.md")
        deal_catalogue.recheck(self.conn, "noma_journeys", None, self.client)
        resolved = sorted(k[1] for k, v in self.states().items() if v == "Resolved")
        self.assertEqual(resolved, ["Contract says something different", "No approval recorded"])
        open_ = sorted(k[1] for k, v in self.states().items() if v != "Resolved")
        self.assertEqual(open_, ["Missing from contract", "Not offered"])  # the specialist is still missing from the contract; voice is not offered
        docs = {d["source_key"]: d for d in workspace.documents(self.conn, "noma_journeys") if d["included"]}
        self.assertEqual((docs["NJ-05"]["version"], docs["NJ-05"]["version_date"]), (2, "2026-10-18"))
        self.assertEqual((docs["NJ-07"]["version"], docs["NJ-07"]["version_date"]), (2, "2026-10-19"))

    def test_the_signed_contract_marks_the_deal_signed_and_is_not_read_by_the_checks(self):
        ledger_v2.review(self.conn, "noma_journeys", self.client, None, self.path)
        ledger_fixes.add_source(self.conn, "noma_journeys", "Signed contract", (SCEN / "NJ-09_signed_contract.md").read_text(),
                                "NJ-09.md", "signed_contract", "2026-10-20")
        calls = self.client.calls
        deal_catalogue.recheck(self.conn, "noma_journeys", None, self.client)
        self.assertEqual(self.client.calls, calls)  # no model call: signed paperwork is not read
        import deal_stage
        self.assertEqual(deal_stage.deal_stage(self.conn, "noma_journeys")["current"], "signed")
        self.assertEqual(sum(v == "Needs action" for v in self.states().values()), 4)


if __name__ == "__main__":
    unittest.main()
