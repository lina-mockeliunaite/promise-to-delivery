"""Add a document and check it in one call (20 Oct): nothing is stored when the check cannot run, a version set aside after
a late failure never appears on any screen, and a document that needs no model still goes through."""

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import add_check
import api
import config
import extraction_cache
import ledger
import ledger_fixes
import recheck
import reset_demo
import workspace
from fastapi.testclient import TestClient
from tests.test_reset_demo import ResetCase

H = {"X-Requested-With": "deal-workspace"}
SOW = (config.DATA_DIR / "alder_bank" / "docs" / "AB-06_draft_sow.md").read_text(encoding="utf-8")
SCEN = config.DATA_DIR / "scenarios"


class AddCheckCase(ResetCase):
    def setUp(self):
        super().setUp()
        env = mock.patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop("ANTHROPIC_API_KEY", None)  # the server has no API key
        reset_demo.reset(self.db)
        self.client = TestClient(api.create_app(dist_dir=self.dir / "no-dist", ledger_path=self.db), base_url="http://127.0.0.1")

    def post(self, body):
        return self.client.post("/api/deals/alder_bank/documents/add-and-check", json=body, headers=H)

    def docs(self):
        return {d["source_key"]: d for d in self.client.get("/api/deals/alder_bank/documents").json()["documents"]}

    def stored(self, key="AB-06"):
        conn = ledger.connect(self.db)
        try:
            return conn.execute("SELECT v.version_no, v.included FROM source_versions v JOIN sources s ON s.id = v.source_id"
                                " WHERE s.source_key = ? ORDER BY v.version_no", (key,)).fetchall()
        finally:
            conn.close()

    def freshness(self):
        return self.client.get("/api/deals/alder_bank/register").json()["freshness"]["state"]


class TestCheckBeforeWriting(AddCheckCase):
    def test_no_key_and_a_changed_sow_refuses_and_stores_nothing_however_often_it_is_tried(self):
        for n in range(3):
            r = self.post({"source_key": "AB-06", "filename": f"sow{n}.md", "text": SOW + f"\n\nAttempt {n}.\n"})
            self.assertEqual(r.status_code, 409, r.text)
            self.assertIn("Nothing was added.", r.json()["detail"])
            self.assertNotIn("set aside", r.json()["detail"])
        self.assertEqual(self.stored(), [(1, 1)])  # still one version, still in the review
        self.assertEqual(self.docs()["AB-06"]["version"], 1)
        self.assertEqual(self.freshness(), "Up to date")

    def test_no_key_and_a_new_contract_document_adds_no_source(self):
        before = set(self.docs())
        r = self.post({"name": "Annex A", "filename": "annex.md", "doc_type": "draft_sow", "doc_date": "2026-10-18", "text": "Annex A. New terms."})
        self.assertEqual(r.status_code, 409, r.text)
        self.assertEqual(set(self.docs()), before)

    def test_a_pricing_note_needs_no_model_and_goes_through_with_the_check_run(self):
        text = (SCEN / "AB-05_v2_named_exception.md").read_text(encoding="utf-8")
        r = self.post({"source_key": "AB-05", "filename": "AB-05_v2.md", "text": text})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["review"]["model_calls"], 0)
        self.assertEqual(self.docs()["AB-05"]["version"], 2)
        self.assertEqual(self.freshness(), "Up to date")

    def test_a_signed_contract_needs_no_model_either(self):
        text = (SCEN / "AB-09_signed_contract.md").read_text(encoding="utf-8")
        r = self.post({"name": "Signed contract", "filename": "AB-09.md", "doc_type": "signed_contract", "doc_date": "2026-10-20", "text": text})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.client.get("/api/deals/alder_bank/register").json()["stage"]["current"], "signed")

    def test_bad_input_is_a_400_and_stores_nothing(self):
        self.assertEqual(self.post({"source_key": "NOPE", "filename": "x.md", "text": "x"}).status_code, 400)
        self.assertEqual(self.post({"name": "X", "filename": "x.md", "doc_type": "nonsense", "text": "x"}).status_code, 400)
        self.assertEqual(self.stored(), [(1, 1)])


class TestSetAsideAfterALateFailure(AddCheckCase):
    def conn(self):
        conn = ledger.connect(self.db)
        self.addCleanup(conn.close)
        return conn

    def fail_late(self):
        """A key is 'present' (so the pre-check passes) and the review then fails, as when the model call itself errors."""
        return mock.patch.object(recheck, "recheck", side_effect=extraction_cache.ExtractionFailed("the model call failed"))

    def attempt(self, n):
        conn = self.conn()
        with self.fail_late():
            with self.assertRaises(add_check.AddCheckError) as ctx:
                add_check.add_and_check(conn, "alder_bank", filename=f"sow{n}.md", text=SOW + f"\n\nAttempt {n}.\n", source_key="AB-06", client=object())
        return ctx.exception

    def test_the_version_is_set_aside_the_old_one_stays_in_the_review_and_the_message_is_the_agreed_one(self):
        err = self.attempt(1)
        self.assertEqual((str(err), err.status), ("The check didn't run. This version was set aside and isn't part of the review.", 409))
        self.assertNotIn("Nothing was added", str(err))
        self.assertEqual(self.stored(), [(1, 1), (2, 0)])  # v2 is in the stored history only
        self.assertEqual(self.docs()["AB-06"]["version"], 1)  # the screens still show v1
        self.assertTrue(self.docs()["AB-06"]["included"])
        self.assertEqual(self.freshness(), "Up to date")  # the review's documents are exactly as before
        err = self.attempt(2)
        self.assertEqual(self.stored(), [(1, 1), (2, 0), (3, 0)])  # a number is skipped, nothing more
        self.assertEqual(self.docs()["AB-06"]["version"], 1)

    def test_a_set_aside_version_is_in_no_document_list_stage_or_hash(self):
        conn = self.conn()
        import deal_stage
        did = ledger_fixes.deal_id(conn, "alder_bank")
        before = (ledger_fixes.source_set_sha256(conn, did), [(d["source_key"], d["version"]) for d in workspace.documents(conn, "alder_bank") if d["included"]],
                  sum(len(s["documents"]) for s in deal_stage.deal_stage(conn, "alder_bank")["stages"]))
        self.attempt(1)
        conn = self.conn()
        after = (ledger_fixes.source_set_sha256(conn, did), [(d["source_key"], d["version"]) for d in workspace.documents(conn, "alder_bank") if d["included"]],
                 sum(len(s["documents"]) for s in deal_stage.deal_stage(conn, "alder_bank")["stages"]))
        self.assertEqual(after, before)
        self.assertEqual(len(before[1]), 8)  # "Documents checked" still counts eight

    def test_a_new_document_that_fails_late_is_excluded_and_not_listed(self):
        conn = self.conn()
        with self.fail_late():
            with self.assertRaises(add_check.AddCheckError):
                add_check.add_and_check(conn, "alder_bank", name="Annex A", filename="annex.md", text="Annex A.", doc_type="draft_sow",
                                        doc_date="2026-10-18", client=object())
        names = [d["name"] for d in workspace.documents(self.conn(), "alder_bank") if d["included"]]
        self.assertEqual(len(names), 8)
        self.assertFalse(any("Annex" in n for n in names))
