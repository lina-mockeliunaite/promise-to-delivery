"""Does a draft's fix survive into the signed paperwork? (21 Oct; signed_check.py)

Replayed on scratch ledgers with scripted readings (the saved demo runs, in a scratch cache): no model is called and nothing is
written to the repo's reading cache. The signed contract that says four languages exists only in this test file."""

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
import deal_stage
import handover
import ledger
import ledger_fixes
import reset_demo
import signed_check
import workspace
from test_noma_journeys import FakeClient

SCEN = config.DATA_DIR / "scenarios"
NOMA_RUN = config.RESULTS_DIR / "v2_demo_noma_journeys_20261020T091857Z.json"
ALDER_RUN = config.RESULTS_DIR / "v2_demo_alder_bank_20261016T065312Z.json"
NJ9 = (SCEN / "NJ-09_signed_contract.md").read_text(encoding="utf-8")
# A signed contract that went back to four languages: the fix in the draft never reached the signed agreement.
NJ9_FOUR = NJ9.replace("The Assistant will respond to Guest enquiries in 12 languages, listed in Schedule 1.",
                       "The Assistant will respond to Guest enquiries in four languages: English, Mandarin Chinese, Japanese and Korean.")
EXACT_REASON = "The fix in Draft contract, version 2 was not found in the signed contract."


class Replay(unittest.TestCase):
    deal = "noma_journeys"
    run_file = NOMA_RUN

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
        accepted = json.loads(self.run_file.read_text(encoding="utf-8"))["deals"][0]["accepted"]
        self.client = FakeClient([{k: v for k, v in f.items() if k != "problems"} for f in accepted])

    def filed(self, source_key, name):
        ledger_fixes.add_source_version(self.conn, self.deal, source_key, (SCEN / name).read_text(encoding="utf-8"), name)
        deal_catalogue.recheck(self.conn, self.deal, None, self.client)

    def sign(self, text, name="NJ-09_signed_contract.md"):
        ledger_fixes.add_source(self.conn, self.deal, "Signed contract", text, name, "signed_contract", "2026-10-20")

    def ov(self):
        return workspace.overview(self.conn, self.deal)

    def issue(self, word, finding, ov=None):
        c = next(c for c in (ov or self.ov())["commitments"] if word in c["name"].lower())
        return c, next(i for i in c["issues"] if i["finding"] == finding)


class TestNoma(Replay):
    def noma_updates(self):
        self.filed("NJ-05", "NJ-05_v2_named_exception.md")
        self.filed("NJ-07", "NJ-07_v2_languages_aligned.md")

    def test_no_signed_document_shows_nothing(self):
        self.noma_updates()
        self.assertEqual(signed_check.evaluate(self.conn, ledger_fixes.deal_id(self.conn, self.deal), self.deal), {})
        for c in self.ov()["commitments"]:
            self.assertTrue(all(i["signed_check"] is None for i in c["issues"]))

    def test_the_signed_contract_confirms_the_languages_fix_by_the_exact_sentence(self):
        self.noma_updates()
        self.sign(NJ9)
        _, languages = self.issue("12 languages", "Contract says something different")
        self.assertEqual(languages["state"], "Resolved")
        sc = languages["signed_check"]
        self.assertEqual(sc["status"], "confirmed")
        self.assertEqual(sc["sentence"], "The Assistant will respond to Guest enquiries in 12 languages, listed in Schedule 1.")
        self.assertEqual(sc["text"], "Confirmed in the signed contract (Signed contract, 20 Oct)")
        # an approval closure (the pricing note) is not affected by signed paperwork: skipped
        _, approval = self.issue("launch specialist", "No approval recorded")
        self.assertEqual((approval["state"], approval["signed_check"]), ("Resolved", None))

    def test_a_signed_contract_that_went_back_to_four_languages_reopens_it_with_the_reason_and_the_history(self):
        self.noma_updates()
        before = {r["deal"]: r for r in handover.deal_rows(self.conn, workspace.deal_list(self.conn))}[self.deal]
        self.sign(NJ9_FOUR)
        ov = self.ov()
        c, languages = self.issue("12 languages", "Contract says something different", ov)
        self.assertEqual(languages["state"], "Needs action")
        self.assertEqual(languages["signed_check"]["status"], "not_found")
        self.assertEqual(languages["signed_check"]["reason"], EXACT_REASON)
        self.assertTrue(languages["signed_check"]["earlier"].startswith("Resolved by Draft contract, version 2"))  # the earlier closure stays visible
        self.assertEqual(c["group"], "open")
        self.assertEqual(c["contract"], "four languages: English, Mandarin Chinese, Japanese and Korean")
        self.assertNotIn(c["id"], [r["commitment_id"] for r in ov["resolved_findings"]])
        # one truth: the page, the deal list and the stage bar all count it
        after = {r["deal"]: r for r in handover.deal_rows(self.conn, workspace.deal_list(self.conn))}[self.deal]
        self.assertEqual(after["open_gaps"], before["open_gaps"] + 1)
        stage = deal_stage.deal_stage(self.conn, self.deal)
        self.assertEqual(sum(s["gaps_started"] for s in stage["stages"]), after["open_gaps"])
        self.assertEqual(len(ov["open_rows"]), after["open_gaps"])
        self.assertEqual(ov["finding_counts"]["unresolved"], sum(1 for k in ov["commitments"] for i in k["issues"] if i["state"] != "Resolved"))

    def test_the_locked_record_stores_the_reopen_and_the_confirmation(self):
        self.noma_updates()
        self.sign(NJ9_FOUR)
        snap = handover.build_snapshot(self.conn, self.deal, "Priya Nair")
        item = next(i for i in snap["open_items"] if "12 languages" in i["promise"])
        finding = next(f for f in item["findings"] if f["finding"] == "Contract says something different")
        self.assertEqual(finding["signed_check"]["reason"], EXACT_REASON)
        self.assertNotIn("12 languages", " ".join(r["promise"] for r in snap["resolved"]))
        # and on the confirming signed contract the closed commitment carries its confirmation
        first = self.conn.execute("SELECT source_key FROM sources WHERE display_name = 'Signed contract'").fetchone()[0]
        ledger_fixes.set_included(self.conn, self.deal, first, False)
        self.sign(NJ9, "NJ-09b.md")
        snap2 = handover.build_snapshot(self.conn, self.deal, "Priya Nair")
        closed = next(i for i in snap2["closed_items"] if "12 languages" in i["promise"])
        self.assertEqual([s["status"] for s in closed["signed"]], ["confirmed"])

    def test_a_reopened_gap_can_be_addressed_by_a_note_and_then_shows_as_noted(self):
        self.noma_updates()
        self.sign(NJ9_FOUR)
        _, languages = self.issue("12 languages", "Contract says something different")
        handover.resolve_by_note(self.conn, self.deal, languages["id"], "Sam Lee", "Noma accepted four languages at launch.")
        c, _ = self.issue("12 languages", "Contract says something different")
        self.assertEqual(c["group"], "noted")

    def test_a_closure_with_no_lookup_sentence_is_not_confirmed_and_stays_closed(self):
        # The wrong filing from the 20 Oct rehearsal: the revised contract as a new version of the SOW closes the phone commitment's
        # "contract differs" finding because the SOW's clause vanished. There is no wording to look for, so: neutral, not reopened.
        self.filed("NJ-06", "NJ-07_v2_languages_aligned.md")
        self.sign(NJ9)
        _, phone = self.issue("phone calls", "Contract says something different")
        self.assertEqual(phone["state"], "Resolved")
        self.assertEqual((phone["signed_check"]["status"], phone["signed_check"]["text"]), ("not_confirmed", "Not confirmed against the signed contract"))


class TestAlder(Replay):
    deal = "alder_bank"
    run_file = ALDER_RUN

    def test_the_signed_contract_that_incorporates_the_9_october_sow_reopens_the_coaching_fix(self):
        self.filed("AB-05", "AB-05_v2_named_exception.md")
        self.filed("AB-06", "AB-06_v2_coaching_added.md")
        _, gap = self.issue("coaching", "Missing from contract")
        self.assertEqual(gap["state"], "Resolved")  # closed by the revised SOW, before any signed paperwork
        self.sign((SCEN / "AB-09_signed_contract.md").read_text(encoding="utf-8"), "AB-09_signed_contract.md")
        ov = self.ov()
        c, gap = self.issue("coaching", "Missing from contract", ov)
        self.assertEqual(gap["state"], "Needs action")
        self.assertEqual(gap["signed_check"]["reason"], "The fix in Draft SOW, version 2 was not found in the signed contract.")
        _, approval = self.issue("coaching", "No approval recorded", ov)
        self.assertEqual((approval["state"], approval["signed_check"]), ("Resolved", None))  # the pricing-note fix is untouched
        # the predicted locked-record verdict: nothing is closed by documents any more
        hosting = next(k for k in ov["commitments"] if "azure" in k["name"].lower())
        for i in hosting["issues"]:  # one note on the commitment settles all its open gaps, as the screen does
            handover.resolve_by_note(self.conn, self.deal, i["id"], "Tom Fraser", "Customer agreed AWS Sydney on the 14 Oct call.")
        snap = handover.build_snapshot(self.conn, self.deal, "Priya Nair")
        self.assertEqual((len(snap["open_items"]), len(snap["resolved_by_note"]), len([r for r in snap["closed_items"] if not any(
            f for f in snap["open_items"] if f["promise"] == r["promise"])])), (2, 1, 0))


class TestMatching(unittest.TestCase):
    """Strict on wording, forgiving only of typography and of how a number is written (21 Oct)."""
    S = "The Assistant will respond to Guest enquiries in 12 languages, listed in Schedule 1."

    def test_a_number_and_its_word_form_are_the_same(self):
        self.assertTrue(signed_check.contains("The Assistant will respond to Guest enquiries in twelve languages, listed in Schedule 1.", self.S))
        self.assertTrue(signed_check.contains("The Assistant will respond to Guest enquiries in TWELVE languages, listed in Schedule one.", self.S))
        for digits, words in (("21", "twenty-one"), ("21", "twenty one"), ("100", "one hundred"), ("40", "forty"), ("19", "nineteen"),
                              ("1", "one"), ("99", "ninety-nine"), ("0", "zero")):
            self.assertTrue(signed_check.contains(f"x {words} y", f"x {digits} y"), (digits, words))
            self.assertTrue(signed_check.contains(f"x {digits} y", f"x {words} y"), (digits, words))
        self.assertTrue(signed_check.contains("fee of 1000 euros", "fee of 1,000 euros"))

    def test_different_numbers_and_partial_numbers_do_not_match(self):
        self.assertFalse(signed_check.contains("in four languages, listed in Schedule 1.", self.S))
        self.assertFalse(signed_check.contains("in 112 languages, listed in Schedule 1.", "in 12 languages, listed in Schedule 1."))  # whole words only
        self.assertFalse(signed_check.contains("in twenty languages", "in 21 languages"))

    def test_curly_quotes_and_apostrophes_are_straightened(self):
        self.assertTrue(signed_check.contains("The Customer\u2019s guests will be answered in \u201c12 languages\u201d.",
                                              "The Customer's guests will be answered in \"12 languages\"."))
        self.assertTrue(signed_check.contains("The Customer's guests", "The Customer\u2019s guests"))

    def test_punctuation_and_spacing_differences_are_ignored(self):
        self.assertTrue(signed_check.contains("The Assistant will respond to Guest enquiries in 12 languages -- listed in Schedule 1", self.S))
        self.assertTrue(signed_check.contains("The Assistant will respond to Guest enquiries in 12  languages;\nlisted in Schedule 1!", self.S))
        self.assertTrue(signed_check.contains("**Clause 4. Languages.** The Assistant will respond to Guest enquiries in 12 languages listed in Schedule 1", self.S))

    def test_a_word_added_dropped_or_changed_is_a_different_sentence(self):
        self.assertFalse(signed_check.contains("The Assistant will respond to Guest enquiries in 12 languages, as listed in Schedule 1.", self.S))
        self.assertFalse(signed_check.contains("The Assistant will respond to Guest enquiries in 12 languages listed in Schedule 2.", self.S))
        self.assertFalse(signed_check.contains("The Assistant will answer Guest enquiries in 12 languages, listed in Schedule 1.", self.S))
        self.assertFalse(signed_check.contains("The Assistant will respond to enquiries in 12 languages, listed in Schedule 1.", self.S))
        self.assertFalse(signed_check.contains("", self.S))
        self.assertFalse(signed_check.contains("anything", ""))

    def test_the_normalisation_itself(self):
        self.assertEqual(signed_check.normalise("Twenty-One  Guests\u2019 \u201cfees\u201d: 1,000!"), "21 guests fees 1000")
        self.assertEqual(signed_check.normalise(None), "")


class TestTheSignedContractWordedDifferently(Replay):
    """On the Noma flow: a signed contract with the same clause written another way is still confirmed; a reworded clause reopens."""

    def after_updates(self):
        for key, name in (("NJ-05", "NJ-05_v2_named_exception.md"), ("NJ-07", "NJ-07_v2_languages_aligned.md")):
            self.filed(key, name)

    def languages(self):
        return self.issue("12 languages", "Contract says something different")[1]

    def test_twelve_in_words_with_curly_punctuation_is_still_confirmed(self):
        self.after_updates()
        self.sign(NJ9.replace("in 12 languages, listed in Schedule 1.", "in twelve languages \u2013 listed in Schedule 1."))
        self.assertEqual(self.languages()["signed_check"]["status"], "confirmed")

    def test_as_listed_in_is_a_different_sentence_and_reopens_it(self):
        self.after_updates()
        self.sign(NJ9.replace("in 12 languages, listed in Schedule 1.", "in 12 languages, as listed in Schedule 1."))
        issue = self.languages()
        self.assertEqual((issue["state"], issue["signed_check"]["status"]), ("Needs action", "not_found"))
        self.assertEqual(issue["signed_check"]["reason"], EXACT_REASON)


class TestTheFourElvaDeals(unittest.TestCase):
    def test_without_signed_paperwork_nothing_changes_anywhere(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(config, "V2_CACHE_DIR", Path(tmp) / "cache"):
            reset_demo.reset(db_path=Path(tmp) / "l.sqlite")
            conn = ledger.connect(Path(tmp) / "l.sqlite")
            try:
                for slug in ("alder_bank", "harbour_bank", "coral_pay", "atlas_remit", "noma_journeys"):
                    self.assertEqual(signed_check.evaluate(conn, ledger_fixes.deal_id(conn, slug), slug), {}, slug)
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()
