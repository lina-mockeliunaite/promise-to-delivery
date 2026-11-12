"""Alder: why coaching reopens after the signed contract, and the signed document's two dates (11 Nov).

Part A, as a regression test: from the state where the revised SOW (AB-05, AB-06) has closed the coaching contract gap, the signed contract is added twice, once as
shipped (it names the 9 October SOW) and once as a scratch copy that names the 16 October SOW. Both reopen, with the same closing sentence looked up in the same
draft SOW, because the check searches the signed text itself and does not read which SOW the contract names. The scratch copy lives in a temporary folder;
data/scenarios/ is only read.

Part B: the signed document's filing date feeds no reading-cache key and no review hash (signed paperwork is left out of both), so showing the signature date
changes only what is displayed and stored as the document's date.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

import api
import config
import ledger
import ledger_fixes
import ledger_v2
import reset_demo
import signed_check
import workspace

H = {"X-Requested-With": "deal-workspace"}
SC = config.SCENARIOS_DIR
REASON = "The signed contract doesn't contain the wording that closed this gap, so the fix can't be confirmed."


class AlderCase(unittest.TestCase):
    def setUp(self):
        for name in ("ANTHROPIC_API_KEY",):
            p = mock.patch.dict(os.environ, {k: v for k, v in os.environ.items() if k != name}, clear=True)
            p.start()
            self.addCleanup(p.stop)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def alder_with_revised_sow(self, sub=""):
        db = self.dir / f"ledger{sub}.sqlite"
        reset_demo.reset(db)
        client = TestClient(api.create_app(dist_dir=self.dir / "x", ledger_path=db, public=False), base_url="http://127.0.0.1")
        for f, key in (("AB-05_v2_named_exception.md", "AB-05"), ("AB-06_v2_coaching_added.md", "AB-06")):
            r = client.post("/api/deals/alder_bank/documents/add-and-check", json={"source_key": key, "filename": f, "text": (SC / f).read_text(encoding="utf-8")}, headers=H)
            self.assertEqual(r.status_code, 200, r.text)
        return db, client

    def add_signed(self, client, text, doc_date="2026-10-20"):
        r = client.post("/api/deals/alder_bank/documents/add-and-check", json={"name": "Signed contract", "filename": "signed.md", "doc_type": "signed_contract",
                                                                              "doc_date": doc_date, "text": text}, headers=H)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["review"]["model_calls"], 0)

    def evaluate(self, db):
        conn = ledger.connect(db)
        self.addCleanup(conn.close)
        did = ledger_fixes.deal_id(conn, "alder_bank")
        return conn, did, signed_check.evaluate(conn, did, "alder_bank")


class TestWhyCoachingReopens(AlderCase):
    def test_the_gap_is_closed_before_the_signed_contract(self):
        db, client = self.alder_with_revised_sow()
        coaching = next(c for c in client.get("/api/deals/alder_bank/register").json()["commitments"] if "BioCatch" in c["name"])
        self.assertEqual({i["finding"]: i["state"] for i in coaching["issues"]}, {"No approval recorded": "Resolved", "Missing from contract": "Resolved"})

    def test_both_signed_texts_reopen_with_the_same_closing_sentence_looked_up_in_the_draft_sow(self):
        shipped = (SC / "AB-09_signed_contract.md").read_text(encoding="utf-8")
        copy = shipped.replace("Statement of Work dated 9 October 2026", "Statement of Work dated 16 October 2026")
        self.assertNotEqual(shipped, copy)
        self.assertEqual(len([1 for a, b in zip(shipped.splitlines(), copy.splitlines()) if a != b]), 1)  # the one line naming the SOW date
        seen = []
        for n, text in enumerate((shipped, copy)):
            db, client = self.alder_with_revised_sow(str(n))
            self.add_signed(client, text)
            conn, did, res = self.evaluate(db)
            self.assertEqual([v["status"] for v in res.values()], ["not_found"], n)
            [v] = res.values()
            self.assertEqual(v["closed_by"], "Draft SOW, version 2")
            self.assertEqual(v["reason"], REASON)
            self.assertIn("coached by a scammer", v["sentence"])
            signed = signed_check.signed_documents(conn, did, "alder_bank")
            self.assertEqual(len(signed), 1)
            self.assertFalse(signed_check.contains(signed[0]["text"], v["sentence"]))  # the sentence is not in the signed text
            self.assertNotIn("biocatch", signed[0]["text"].lower())
            seen.append((v["sentence"], v["closed_by"], v["status"]))
            reg = client.get("/api/deals/alder_bank/register").json()
            coaching = next(c for c in reg["commitments"] if "BioCatch" in c["name"])
            gap = next(i for i in coaching["issues"] if i["finding"] == "Missing from contract")
            self.assertEqual(gap["signed_check"]["reason"], REASON)
            self.assertIn("Draft SOW, version 2", gap["signed_check"]["earlier"])  # the closing document, named beneath
        self.assertEqual(seen[0], seen[1])  # the SOW date the contract names changes nothing

    def test_the_reason_is_the_generic_sentence_for_every_deal(self):
        self.assertIn("doesn't contain the wording that closed this gap, so the fix can't be confirmed", Path(signed_check.__file__).read_text(encoding="utf-8"))


class TestSignedCheckOutputFields(AlderCase):
    """Evidence fields added to the signed check's output (11 Nov): the signed clause, which document it is in, and which signed document was searched."""

    def test_a_confirmed_verdict_carries_the_signed_clause_and_its_document(self):
        db = self.dir / "noma.sqlite"
        reset_demo.reset(db)
        client = TestClient(api.create_app(dist_dir=self.dir / "x", ledger_path=db, public=False), base_url="http://127.0.0.1")
        for f, key in (("NJ-05_v2_named_exception.md", "NJ-05"), ("NJ-07_v2_languages_aligned.md", "NJ-07")):
            self.assertEqual(client.post("/api/deals/noma_journeys/documents/add-and-check", json={"source_key": key, "filename": f, "text": (SC / f).read_text(encoding="utf-8")}, headers=H).status_code, 200)
        self.add_signed_to(client, "noma_journeys", (SC / "NJ-09_signed_contract.md").read_text(encoding="utf-8"))
        conn = ledger.connect(db)
        self.addCleanup(conn.close)
        res = signed_check.evaluate(conn, ledger_fixes.deal_id(conn, "noma_journeys"), "noma_journeys")
        [v] = res.values()
        self.assertEqual(v["status"], "confirmed")
        self.assertEqual(v["signed_sentence"], "The Assistant will respond to Guest enquiries in 12 languages, listed in Schedule 1.")
        self.assertIn(v["signed_sentence"], (SC / "NJ-09_signed_contract.md").read_text(encoding="utf-8"))  # the signed text's own wording
        key = next(d["source_key"] for d in client.get("/api/deals/noma_journeys/documents").json()["documents"] if d["doc_type"] == "signed_contract")
        self.assertEqual((v["signed_key"], v["signed"], v["date"]), (key, "Signed contract", "2026-10-20"))  # the key the app gave the new document
        self.assertIsInstance(v["signed_version_id"], int)
        gap = next(i for c in client.get("/api/deals/noma_journeys/register").json()["commitments"] for i in c["issues"] if i.get("signed_check"))
        self.assertEqual(gap["signed_check"]["signed_sentence"], v["signed_sentence"])  # the register carries it to the screens

    def add_signed_to(self, client, deal, text):
        r = client.post(f"/api/deals/{deal}/documents/add-and-check", json={"name": "Signed contract", "filename": "s.md", "doc_type": "signed_contract", "doc_date": "2026-10-20", "text": text}, headers=H)
        self.assertEqual(r.status_code, 200, r.text)

    def test_a_not_found_verdict_names_the_signed_document_that_was_searched(self):
        db, client = self.alder_with_revised_sow()
        self.add_signed_to(client, "alder_bank", (SC / "AB-09_signed_contract.md").read_text(encoding="utf-8"))
        conn, did, res = self.evaluate(db)
        [v] = res.values()
        key = next(d["source_key"] for d in client.get("/api/deals/alder_bank/documents").json()["documents"] if d["doc_type"] == "signed_contract")
        self.assertEqual((v["status"], v["signed_label"], v["signed_date"], v["signed_key"]), ("not_found", "Signed contract", "2026-10-20", key))
        self.assertEqual(v["closed_by"], "Draft SOW, version 2")

    def test_locate_returns_the_signed_wording_and_falls_back_to_the_sentence(self):
        text = "**Clause 4. Languages.** The Assistant will respond in 12 languages, listed in Schedule 1.\n\nMore."
        self.assertEqual(signed_check.locate(text, "The Assistant will respond in 12 languages, listed in Schedule 1."), "The Assistant will respond in 12 languages, listed in Schedule 1.")
        self.assertEqual(signed_check.locate(text, "Something else entirely."), "Something else entirely.")
        self.assertEqual(signed_check.locate("", "x y"), "x y")

    def test_the_saved_handover_record_keeps_only_its_old_fields(self):
        src = (Path(signed_check.__file__).parent / "handover.py").read_text(encoding="utf-8")
        self.assertIn('for k in ("status", "text", "reason", "earlier") if k in sc', src)  # the snapshot copies four fields: new fields never enter the saved record


class TestSignedDates(AlderCase):
    def test_the_signed_agreement_states_two_dates(self):
        text = (SC / "AB-09_signed_contract.md").read_text(encoding="utf-8")
        self.assertEqual(workspace.stated_date(text), "2026-10-12")
        self.assertEqual(workspace.signature_date(text), "2026-10-20")
        noma = (SC / "NJ-09_signed_contract.md").read_text(encoding="utf-8")
        self.assertEqual((workspace.stated_date(noma), workspace.signature_date(noma)), ("2026-10-20", "2026-10-20"))  # the same: nothing extra to show
        self.assertIsNone(workspace.signature_date("# A draft\n\nDate: 12 October 2026\n"))  # no signature block

    def test_the_documents_list_carries_both_dates_for_signed_paperwork_only(self):
        db, client = self.alder_with_revised_sow()
        self.add_signed(client, (SC / "AB-09_signed_contract.md").read_text(encoding="utf-8"))
        docs = client.get("/api/deals/alder_bank/documents").json()["documents"]
        signed = next(d for d in docs if d["doc_type"] == "signed_contract")
        self.assertEqual((signed["date"], signed["version_date"], signed["agreement_date"], signed["signed_on"]), ("2026-10-20", "2026-10-20", "2026-10-12", "2026-10-20"))
        draft = next(d for d in docs if d["doc_type"] == "draft_sow")
        self.assertEqual((draft["agreement_date"], draft["signed_on"]), (None, None))

    def test_the_signed_documents_filing_date_feeds_no_cache_key_and_no_review_hash(self):
        text = (SC / "AB-09_signed_contract.md").read_text(encoding="utf-8")
        results = []
        for n, date in enumerate(("2026-10-12", "2026-10-20")):
            db, client = self.alder_with_revised_sow(f"d{n}")
            self.add_signed(client, text, date)
            conn = ledger.connect(db)
            self.addCleanup(conn.close)
            did = ledger_fixes.deal_id(conn, "alder_bank")
            docs = ledger_v2.current_docs(conn, did)
            key = ledger_v2.input_sha256(docs, Path(config.DATA_DIR / "catalogue.json").read_bytes(), config.EXTRACTION_MODEL)
            results.append((ledger_fixes.source_set_sha256(conn, did), key, [d["source_id"] for d in docs]))
        self.assertEqual(results[0], results[1])  # the reading-cache key and the review's source-set hash do not move with the signed date
        self.assertNotIn("AB-09", results[0][2])  # signed paperwork is not among the documents the checks read


if __name__ == "__main__":
    unittest.main()
