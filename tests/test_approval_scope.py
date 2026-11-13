"""Approval scope (Round 5, 12 Nov): a named approval closes the approval gap only if its effective start date covers the commitment's start date.

approval_scope.py is a read-time layer (like signed_check.py): the engine, the ledger and the config hash are untouched. Dates are parsed by code from quotes that are already
verified; with either date missing nothing changes. Alder demonstrates it; Noma must not change."""

import datetime
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi.testclient import TestClient

import api
import approval_scope as ap
import config
import ledger
import ledger_fixes
import real_readings
import reset_demo
from test_noma_journeys import FakeClient

H = {"X-Requested-With": "deal-workspace"}
SC = config.SCENARIOS_DIR
D = datetime.date
SENTENCE = "Scam-call alerts will be live from the 1 February 2027 launch: they warn the bank when a customer seems to be on a call with a scammer while making a payment."
NO_DATE_SENTENCE = "Scam-call alerts will be live at launch: they warn the bank when a customer seems to be on a call with a scammer while making a payment."
APPROVAL_NOW = "Named exception approved by Arjun Rao (Head of Product) from 1 May 2027, subject to the beta terms in Annex B"
HELD = "The signed start date is earlier than the approved start date."


class TestDates(unittest.TestCase):
    def test_only_day_month_year_dates_are_read(self):
        for text, want in (("1 May 2027", D(2027, 5, 1)), ("1st May 2027", D(2027, 5, 1)), ("22nd of May", None), ("May 1, 2027", D(2027, 5, 1)), ("May 1 2027", D(2027, 5, 1)),
                           ("2027-05-01", D(2027, 5, 1)), ("1 Sept. 2027", D(2027, 9, 1)), ("3 Feb 2027", D(2027, 2, 3)), ("the 1 February 2027 launch", D(2027, 2, 1))):
            self.assertEqual(ap.explicit_date(text), want, text)

    def test_quarters_months_numeric_forms_and_vague_words_are_no_date(self):
        for text in ("Q2 2027", "H1 2027", "May 2027", "1 May", "mid-2027", "at launch", "end of year one", "01/05/2027", "05/01/2027", "31 February 2027", "in 2027", "1 May 27"):
            self.assertIsNone(ap.explicit_date(text), text)

    def test_two_different_dates_in_one_sentence_is_no_date_but_the_same_date_twice_is_one(self):
        self.assertIsNone(ap.explicit_date("live from 1 February 2027, with go-live 1 December 2026"))
        self.assertEqual(ap.explicit_date("from 1 May 2027 (1 May 2027)"), D(2027, 5, 1))

    def test_the_approval_date_is_the_one_after_from_effective_with_effect_from_or_starting(self):
        for line, want in (("approved by Arjun Rao from 1 May 2027, subject to Annex B", D(2027, 5, 1)),
                           ("approved by Arjun Rao, effective 1 May 2027", D(2027, 5, 1)),
                           ("approved by Arjun Rao, effective from 1 May 2027", D(2027, 5, 1)),
                           ("approved by Arjun Rao with effect from 1 May 2027", D(2027, 5, 1)),
                           ("approved by Arjun Rao starting May 1, 2027", D(2027, 5, 1)),
                           ("approved by Arjun Rao from the 1 May 2027 launch", D(2027, 5, 1)),
                           ("approved by Arjun Rao from 2027-05-01", D(2027, 5, 1))):
            self.assertEqual(ap.effective_date(line), want, line)

    def test_any_other_date_is_ignored_the_issue_date_the_end_date_and_deadlines(self):
        for line in ("approved by Arjun Rao on 16 October 2026 for the 1 February 2027 launch, subject to Annex B",  # the old AB-05 row
                     "approved by Arjun Rao on 16 October 2026", "approved by Arjun Rao, dated 16 October 2026", "approved by Arjun Rao by 1 May 2027",
                     "approved by Arjun Rao until 30 June 2027", "approved by Arjun Rao from Q2 2027", "approved by Arjun Rao from launch", "approved by Arjun Rao from May 2027"):
            self.assertIsNone(ap.effective_date(line), line)
        # a range: only the date after the introducer counts; its end date is ignored (an approval that expires early is not caught: stated limitation)
        self.assertEqual(ap.effective_date("approved by Arjun Rao from 1 May 2027 until 30 June 2027"), D(2027, 5, 1))
        self.assertIsNone(ap.effective_date("approved by Arjun Rao from 1 May 2027, effective 1 June 2027"))  # two introduced dates: ambiguous


class Flow(unittest.TestCase):
    def setUp(self):
        p = mock.patch.dict(os.environ, {**{k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}, "ANTHROPIC_API_KEY": "test"}, clear=True)
        p.start()
        self.addCleanup(p.stop)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        # A scratch cache holding Alder's base reading, and a fake model that serves the accepted K1 reading for the variants a test builds (a changed approval note changes the cache key).
        # Nothing is written to results/v2_cache, and no real model is called.
        cache = real_readings.patch_cache(self.dir / "cache")
        cache.start()
        self.addCleanup(cache.stop)
        fake = mock.patch("anthropic.Anthropic", return_value=FakeClient(real_readings.k1_findings()))
        fake.start()
        self.addCleanup(fake.stop)

    def alder(self, ab05=None, ab06=None, ab09=None, steps=3, sub="a"):
        db = self.dir / f"{sub}.sqlite"
        reset_demo.reset(db)
        client = TestClient(api.create_app(dist_dir=self.dir / "x", ledger_path=db, public=False), base_url="http://127.0.0.1")
        read = lambda f: (SC / f).read_text(encoding="utf-8")
        docs = [("AB-05", "AB-05_v2_named_exception.md", ab05 or read("AB-05_v2_named_exception.md")), ("AB-06", "AB-06_v2_scam_alerts_added.md", ab06 or read("AB-06_v2_scam_alerts_added.md"))][:steps]
        for key, f, text in docs:
            r = client.post("/api/deals/alder_bank/documents/add-and-check", json={"source_key": key, "filename": f, "text": text}, headers=H)
            self.assertEqual(r.status_code, 200, r.text)
        if steps >= 3:
            r = client.post("/api/deals/alder_bank/documents/add-and-check", json={"name": "Signed contract", "filename": "s.md", "doc_type": "signed_contract",
                                                                                  "doc_date": "2026-10-20", "text": ab09 or read("AB-09_signed_contract.md")}, headers=H)
            self.assertEqual(r.status_code, 200, r.text)
        return db, client

    def coaching(self, client):
        reg = client.get("/api/deals/alder_bank/register").json()
        c = next(x for x in reg["commitments"] if "Scam-call alerts" in x["name"])
        return c, {i["type"]: i for i in c["issues"]}

    def scratch_ab05(self, row):
        text = (SC / "AB-05_v2_named_exception.md").read_text(encoding="utf-8")
        self.assertIn(APPROVAL_NOW, text)
        return text.replace(APPROVAL_NOW, row)


class TestTwoRunMatrix(Flow):
    """The signed start date is fixed at 1 February 2027 (AB-06 and AB-09 carry one identical sentence); only the approval's effective date changes."""

    def test_a_the_approval_from_1_may_confirms_the_signed_wording_and_the_approval_gap_stays_open_with_both_clauses(self):
        self.assertIn(SENTENCE, (SC / "AB-06_v2_scam_alerts_added.md").read_text(encoding="utf-8"))
        self.assertIn(SENTENCE, (SC / "AB-09_signed_contract.md").read_text(encoding="utf-8"))
        db, client = self.alder(sub="a")
        c, by = self.coaching(client)
        self.assertEqual(by["contract_gap"]["signed_check"]["status"], "confirmed")  # the signed wording is confirmed
        self.assertEqual(by["contract_gap"]["state"], "Resolved")
        gap = by["approval"]
        self.assertEqual((gap["state"], gap["finding"], gap["reason"]), ("Needs action", "Approval starts later", HELD))
        s = gap["approval_scope"]
        self.assertEqual((s["status"], s["start"]["source"], s["start"]["date"], s["approval"]["date"]), ("not_covered", "signed", "2027-02-01", "2027-05-01"))
        self.assertEqual(s["start"]["sentence"], SENTENCE)  # both clauses are there to show, with their documents
        self.assertIn("from 1 May 2027", s["approval"]["line"])
        self.assertEqual((s["start"]["label"], s["approval"]["doc_date"]), ("Signed contract", "2026-10-16"))  # the document's own (issue) date is separate from the effective date
        self.assertEqual(c["open_count"], 1)
        self.assertIn(c["id"], client.get("/api/deals/alder_bank/register").json()["open_rows"])

    def test_b_the_approval_from_1_february_covers_the_launch_and_the_gap_closes(self):
        db, client = self.alder(ab05=self.scratch_ab05("Named exception approved by Arjun Rao (Head of Product) from 1 February 2027, subject to the beta terms in Annex B"), sub="b")
        c, by = self.coaching(client)
        self.assertEqual(by["contract_gap"]["signed_check"]["status"], "confirmed")  # the same signed wording
        self.assertEqual((by["approval"]["state"], by["approval"]["finding"]), ("Resolved", "No approval recorded"))  # the approval covers the launch: closed as today
        self.assertEqual(by["approval"]["approval_scope"]["status"], "covered")
        self.assertEqual(c["open_count"], 0)

    def test_the_reason_names_the_source_of_the_start_date_promise_then_contract_then_signed(self):
        db, client = self.alder(steps=1, sub="p")
        _, by = self.coaching(client)
        self.assertEqual((by["approval"]["reason"], by["approval"]["approval_scope"]["start"]["source"]), ("The promised start date is earlier than the approved start date.", "promise"))
        db, client = self.alder(steps=2, sub="c")
        _, by = self.coaching(client)
        self.assertEqual((by["approval"]["reason"], by["approval"]["approval_scope"]["start"]["source"]), ("The contract start date is earlier than the approved start date.", "contract"))
        db, client = self.alder(steps=3, sub="s")
        _, by = self.coaching(client)
        self.assertEqual((by["approval"]["reason"], by["approval"]["approval_scope"]["start"]["source"]), (HELD, "signed"))

    def test_a_note_can_address_the_gap_it_holds_open(self):
        db, client = self.alder(sub="n")
        _, by = self.coaching(client)
        r = client.post("/api/deals/alder_bank/resolve-note", json={"issue_ids": [by["approval"]["id"]], "resolved_by": "Sam", "reason": "Product will bring the approval forward."}, headers=H)
        self.assertEqual(r.status_code, 200, r.text)


class TestAsToday(Flow):
    def test_an_approval_with_no_effective_date_behaves_as_today_and_says_no_start_dates_to_compare(self):
        old_row = "Named exception approved by Arjun Rao (Head of Product) on 16 October 2026 for the 1 February 2027 launch, subject to the beta terms in Annex B"
        db, client = self.alder(ab05=self.scratch_ab05(old_row), steps=2, sub="o")
        _, by = self.coaching(client)
        self.assertEqual((by["approval"]["state"], by["approval"]["finding"]), ("Resolved", "No approval recorded"))
        s = by["approval"]["approval_scope"]
        self.assertEqual((s["status"], s["approval"]["date"], s["start"]["date"], s["note"]), ("no_dates", None, "2027-02-01", ap.NO_DATES_NOTE))  # one date found: the note

    def test_an_approval_with_only_an_issue_date_has_no_effective_date(self):
        row = "Named exception approved by Arjun Rao (Head of Product) on 16 October 2026, subject to the beta terms in Annex B"
        db, client = self.alder(ab05=self.scratch_ab05(row), steps=2, sub="i")
        _, by = self.coaching(client)
        self.assertEqual(by["approval"]["state"], "Resolved")
        self.assertIsNone(by["approval"]["approval_scope"]["approval"]["date"])

    def test_the_note_is_said_only_when_one_date_was_found_not_when_neither_was(self):
        row = "Named exception approved by Arjun Rao (Head of Product), subject to the beta terms in Annex B"
        signed = (SC / "AB-09_signed_contract.md").read_text(encoding="utf-8").replace(SENTENCE, NO_DATE_SENTENCE)
        db, client = self.alder(ab05=self.scratch_ab05(row), ab09=signed, sub="z")
        _, by = self.coaching(client)
        s = by["approval"]["approval_scope"]
        self.assertEqual((s["status"], s["approval"]["date"], s["start"]["date"], s["note"]), ("no_dates", None, None, None))  # neither: silence

    def test_the_firmest_located_source_decides_a_sentence_with_no_date_does_not_fall_through_to_the_draft_or_the_promise(self):
        signed = (SC / "AB-09_signed_contract.md").read_text(encoding="utf-8").replace(SENTENCE, NO_DATE_SENTENCE)
        db, client = self.alder(ab09=signed, sub="f")
        _, by = self.coaching(client)
        s = by["approval"]["approval_scope"]
        # the signed sentence is located and has no explicit date: no start date, and the draft SOW's and the promise's 1 February are not consulted
        self.assertEqual((s["status"], s["start"]["source"], s["start"]["date"], by["approval"]["state"]), ("no_dates", "signed", None, "Resolved"))
        self.assertEqual(s["note"], ap.NO_DATES_NOTE)  # the approval's 1 May was found: one date

    def test_an_approval_filed_against_a_different_commitment_is_unaffected(self):
        text = (SC / "AB-05_v2_named_exception.md").read_text(encoding="utf-8")
        row = "Named exception approved by Arjun Rao (Head of Product) on 16 October 2026, subject to the beta terms in Annex B"
        other = text.replace(APPROVAL_NOW, row).replace("| No exception needed |\n| CAP-019", "| Named exception approved by Dana Lee (Head of Delivery) from 1 June 2027 |\n| CAP-019")
        self.assertNotEqual(other, text.replace(APPROVAL_NOW, row))
        db, client = self.alder(ab05=other, steps=2, sub="d")
        _, by = self.coaching(client)
        self.assertEqual(by["approval"]["state"], "Resolved")  # the CAP-011 line from 1 June 2027 is not this commitment's approval
        self.assertIsNone(by["approval"]["approval_scope"]["approval"]["date"])


class TestOthersAreUnchanged(unittest.TestCase):
    def test_noma_has_no_dates_to_compare_and_shows_nothing_extra(self):
        import ledger_fixes as lf
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}, clear=True):
            db = Path(tmp) / "n.sqlite"
            reset_demo.reset(db)
            client = TestClient(api.create_app(dist_dir=Path(tmp) / "x", ledger_path=db, public=False), base_url="http://127.0.0.1")
            for f, key in (("NJ-05_v2_named_exception.md", "NJ-05"), ("NJ-07_v2_languages_aligned.md", "NJ-07")):
                self.assertEqual(client.post("/api/deals/noma_journeys/documents/add-and-check", json={"source_key": key, "filename": f, "text": (SC / f).read_text(encoding="utf-8")}, headers=H).status_code, 200)
            self.assertEqual(client.post("/api/deals/noma_journeys/documents/add-and-check", json={"name": "Signed contract", "filename": "s.md", "doc_type": "signed_contract",
                                                                                                  "doc_date": "2026-10-20", "text": (SC / "NJ-09_signed_contract.md").read_text(encoding="utf-8")}, headers=H).status_code, 200)
            reg = client.get("/api/deals/noma_journeys/register").json()
            issues = [i for c in reg["commitments"] for i in c["issues"]]
            self.assertTrue(all(i["finding"] != "Approval starts later" for i in issues))
            scopes = [i["approval_scope"] for i in issues if i["approval_scope"]]
            self.assertTrue(scopes and all(s["status"] == "no_dates" and s["note"] is None for s in scopes))  # a closed approval with no dates: no note, no change
            languages = next(c for c in reg["commitments"] if "12 languages" in c["name"])
            self.assertEqual([(i["state"], i["signed_check"]["status"]) for i in languages["issues"] if i["signed_check"]], [("Resolved", "confirmed")])  # signed language link as before

    def test_the_other_deals_notes_have_no_introduced_dates_so_nothing_there_can_change(self):
        for name in ("alder_bank/docs/AB-05", "atlas_remit/docs/AR-05", "coral_pay/docs/CP-05", "harbour_bank/docs/HB-05", "hard_cases/docs/KR-05", "noma_journeys/docs/NJ-05", "practice_cases/docs/PC-03"):
            f = next((config.DATA_DIR / name.rsplit("/", 1)[0]).glob(name.rsplit("/", 1)[1] + "_*"))
            for line in f.read_text(encoding="utf-8").splitlines():
                if "approv" in line.lower():
                    self.assertIsNone(ap.effective_date(line), (f.name, line))

    def test_no_file_in_the_config_hash_is_edited_by_this_layer(self):
        import integrity
        text = (Path(ap.__file__)).read_text(encoding="utf-8")
        self.assertNotIn("detect_v2.V2_VERSION", text)
        for name in integrity.CONFIG_FILES_3:
            self.assertNotIn(name.replace(".py", ""), {"approval_scope"})  # the layer is a new module, outside the hashed list
        self.assertNotIn("approval_scope.py", integrity.CONFIG_FILES_3)


if __name__ == "__main__":
    unittest.main()
