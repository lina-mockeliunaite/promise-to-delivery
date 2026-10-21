"""The add-and-check guard and the review use one cache key (21 Oct).

The guard (deal_catalogue.needs_model) used to build the incoming document with an empty date and the placeholder source id "new", so
with no API key it refused a step whose reading was cached. It now builds the document list the review will see and uses the same key
function. These tests check the two keys agree, then replay the Noma and Alder demo flows through the add-and-check route itself,
first with a scripted client (filling a scratch cache) and then offline, with no key: every cached step succeeds with no model call.
Everything uses a scratch cache; nothing scripted can reach results/v2_cache."""

import json
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
import config
import deal_catalogue
import ledger
import ledger_fixes
import ledger_import
import reset_demo
from test_noma_journeys import FakeClient

SCEN = config.DATA_DIR / "scenarios"
H = {"X-Requested-With": "deal-workspace"}
NOMA = [f for f in json.loads((config.RESULTS_DIR / "v2_demo_noma_journeys_20261020T091857Z.json").read_text())["deals"][0]["accepted"]]
ALDER = [f for f in json.loads((config.RESULTS_DIR / "v2_demo_alder_bank_20261016T065312Z.json").read_text())["deals"][0]["accepted"]]
clean = lambda findings: [{k: v for k, v in f.items() if k != "problems"} for f in findings]


def scratch_ledger(tmp, name="l.sqlite"):
    db = Path(tmp) / name
    reset_demo.reset(db_path=db)
    return db


class TestTheGuardAndTheReviewAgree(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        cache = mock.patch.object(config, "V2_CACHE_DIR", Path(tmp.name) / "cache")
        cache.start()
        self.addCleanup(cache.stop)
        self.conn = ledger.connect(scratch_ledger(tmp.name))
        self.addCleanup(self.conn.close)
        self.client = FakeClient(clean(NOMA))
        self.did = ledger_fixes.deal_id(self.conn, "noma_journeys")

    def canonical(self, text):
        return ledger_import.markdown_adapter(text.encode("utf-8"))["canonical_text"]

    def review_key(self):
        return self.conn.execute("SELECT d.input_sha256 FROM v2_detections d JOIN reviews r ON r.id = d.review_id"
                                 " WHERE r.deal_id = ? ORDER BY d.review_id DESC LIMIT 1", (self.did,)).fetchone()[0]

    def agree(self, source_key, doc_type, text, doc_date=None, name="x.md"):
        guard = deal_catalogue.cache_key(self.conn, "noma_journeys", source_key, doc_type, self.canonical(text), doc_date)
        self.assertTrue(deal_catalogue.needs_model(self.conn, "noma_journeys", source_key, doc_type, self.canonical(text), doc_date))
        if source_key:
            ledger_fixes.add_source_version(self.conn, "noma_journeys", source_key, text, name, doc_type, doc_date)
        else:
            ledger_fixes.add_source(self.conn, "noma_journeys", name, text, name, doc_type, doc_date or "")
        deal_catalogue.recheck(self.conn, "noma_journeys", None, self.client)
        self.assertEqual(guard, self.review_key())  # the key the guard computed is the key the review used
        if source_key:  # asking again about the same new version is a cache hit (asking again about "a new document" is a different document)
            self.assertFalse(deal_catalogue.needs_model(self.conn, "noma_journeys", source_key, doc_type, self.canonical(text), doc_date))

    def test_a_new_version_inherits_the_previous_versions_date_in_both(self):
        self.agree("NJ-07", "draft_contract", (SCEN / "NJ-07_v2_languages_aligned.md").read_text(encoding="utf-8"))

    def test_a_new_version_with_its_own_date_in_both(self):
        self.agree("NJ-07", "draft_contract", (SCEN / "NJ-07_v2_languages_aligned.md").read_text(encoding="utf-8"), "2026-10-19")

    def test_a_new_document_gets_the_same_source_id_in_both(self):
        self.agree(None, "proposal", "# Proposal addendum\n\nAivuna will add one more thing.\n", "2026-10-19", "addendum.md")

    def test_internal_and_signed_paperwork_never_need_the_model(self):
        for doc_type in ("pricing_services_note", "signed_contract", "signed_sow"):
            self.assertFalse(deal_catalogue.needs_model(self.conn, "noma_journeys", None, doc_type, "x", "2026-10-20"), doc_type)

    def test_the_shared_rules_are_the_ones_the_storing_code_uses(self):
        self.assertEqual(ledger_fixes.version_doc_date(self.conn, self.did, "NJ-07", None), "2026-10-14")
        self.assertEqual(ledger_fixes.version_doc_date(self.conn, self.did, "NJ-07", "2026-10-19"), "2026-10-19")
        self.assertEqual(ledger_fixes.next_source_key(self.conn, self.did), "D-09")


def flow(deal, steps, findings, key_set, cache_dir, tmp):
    """The demo flow through the add-and-check route itself. Returns (responses, model calls, locked snapshot counts)."""
    fake = FakeClient(findings)
    env = {"ANTHROPIC_API_KEY": "test"} if key_set else {}
    with mock.patch.dict(os.environ, env), mock.patch.object(config, "V2_CACHE_DIR", cache_dir), \
            mock.patch("anthropic.Anthropic", return_value=fake):
        if not key_set:
            os.environ.pop("ANTHROPIC_API_KEY", None)
        db = scratch_ledger(tmp, f"{deal}_{'key' if key_set else 'nokey'}.sqlite")
        client = TestClient(api.create_app(dist_dir=Path(tmp) / "no-dist", ledger_path=db), base_url="http://127.0.0.1")
        out = []
        for kind, payload in steps:
            if kind == "doc":
                r = client.post(f"/api/deals/{deal}/documents/add-and-check", json=payload, headers=H)
            elif kind == "note_all":  # one note settles every open gap on the commitment named, as the screen does
                reg = client.get(f"/api/deals/{deal}/register").json()
                ids = [i["id"] for c in reg["commitments"] if payload["word"] in c["name"].lower() for i in c["issues"] if i["state"] != "Resolved"]
                r = client.post(f"/api/deals/{deal}/resolve-note", json={"issue_ids": ids, "resolved_by": "Priya Nair", "reason": payload["reason"]}, headers=H)
            elif kind == "handover_note":
                r = client.post(f"/api/deals/{deal}/handover/notes", json=payload, headers=H)
            else:
                r = client.post(f"/api/deals/{deal}/handover/complete", json=payload, headers=H)
            out.append((kind, r.status_code, r.text[:160] if r.status_code != 200 else "", fake.calls))
        snap = client.get(f"/api/deals/{deal}/handover").json()["snapshot"]
        counts = (len(snap["open_items"]), len(snap["resolved_by_note"]), len(snap["closed_items"]))
        return out, fake.calls, counts, snap


def noma_steps():
    read = lambda n: (SCEN / n).read_text(encoding="utf-8")
    return [("doc", {"source_key": "NJ-05", "filename": "NJ-05_v2_named_exception.md", "text": read("NJ-05_v2_named_exception.md")}),
            ("doc", {"source_key": "NJ-07", "filename": "NJ-07_v2_languages_aligned.md", "text": read("NJ-07_v2_languages_aligned.md")}),
            ("note_all", {"word": "phone calls", "reason": "Noma agreed on 19 Oct to launch on chat and email; voice is not offered."}),
            ("doc", {"name": "Signed contract", "filename": "NJ-09_signed_contract.md", "doc_type": "signed_contract", "doc_date": "2026-10-20", "text": read("NJ-09_signed_contract.md")}),
            ("handover_note", {"role": "sales", "note": "Signed with the launch specialist still missing from the contract.", "entered_by": "Liam Hart"}),
            ("handover_note", {"role": "delivery", "note": "Accepted.", "entered_by": "Sam Lee"}),
            ("complete", {"completed_by": "Priya Nair"})]


def alder_steps():
    read = lambda n: (SCEN / n).read_text(encoding="utf-8")
    return [("doc", {"source_key": "AB-05", "filename": "AB-05_v2_named_exception.md", "text": read("AB-05_v2_named_exception.md")}),
            ("doc", {"source_key": "AB-06", "filename": "AB-06_v2_coaching_added.md", "text": read("AB-06_v2_coaching_added.md")}),
            ("note_all", {"word": "azure", "reason": "Customer agreed AWS Sydney on the 14 Oct call."}),
            ("doc", {"name": "Signed contract", "filename": "AB-09_signed_contract.md", "doc_type": "signed_contract", "doc_date": "2026-10-20", "text": read("AB-09_signed_contract.md")}),
            ("handover_note", {"role": "sales", "note": "Signed; see open items.", "entered_by": "Tom Fraser"}),
            ("handover_note", {"role": "delivery", "note": "Accepted.", "entered_by": "Sam Lee"}),
            ("complete", {"completed_by": "Priya Nair"})]


class TestTheOfflineReplayThroughTheRoute(unittest.TestCase):
    def replay(self, deal, steps, findings, expected_calls, expected_counts):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "cache"
            online, calls_online, counts_online, _ = flow(deal, steps, findings, True, cache, tmp)
            self.assertTrue(all(step[1] == 200 for step in online), online)
            self.assertEqual(calls_online, expected_calls)  # only the step that changes a read document needs the model
            offline, calls_offline, counts_offline, snap = flow(deal, steps, findings, False, cache, tmp)
            self.assertTrue(all(step[1] == 200 for step in offline), offline)  # every cached step succeeds with no key
            self.assertEqual(calls_offline, 0)  # and no model call
            self.assertEqual(counts_offline, counts_online)
            self.assertEqual(counts_offline, expected_counts)
            return snap

    def test_the_noma_flow_offline(self):
        # one model call when the cache is filled (the revised contract); the signed contract confirms the languages fix, so
        # the locked record has the specialist and the phone gaps: 1 needing attention, 1 addressed by note; 1 closed (languages)
        snap = self.replay("noma_journeys", noma_steps(), clean(NOMA), 1, (1, 1, 2))
        languages = next(i for i in snap["closed_items"] if "12 languages" in i["promise"])
        self.assertEqual(languages["signed"][0]["text"], "Confirmed in the signed contract (Signed contract, 20 Oct)")

    def test_the_alder_flow_offline_ends_with_the_coaching_fix_reopened(self):
        # the revised SOW needs the model once; the signed contract incorporates the 9 October SOW, so the coaching fix is not in it
        snap = self.replay("alder_bank", alder_steps(), clean(ALDER), 1, (2, 1, 1))
        coaching = next(i for i in snap["open_items"] if "coach" in i["promise"].lower())
        reopened = next(f for f in coaching["findings"] if f["finding"] == "Missing from contract")
        self.assertEqual(reopened["signed_check"]["reason"], "The fix in Draft SOW, version 2 was not found in the signed contract.")

    def test_a_changed_document_with_no_key_and_no_cache_is_still_refused_and_nothing_is_added(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(config, "V2_CACHE_DIR", Path(tmp) / "cache"), \
                mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            db = scratch_ledger(tmp)
            client = TestClient(api.create_app(dist_dir=Path(tmp) / "no-dist", ledger_path=db), base_url="http://127.0.0.1")
            conn = ledger.connect(db)
            before = conn.execute("SELECT COUNT(*) FROM source_versions").fetchone()[0]
            conn.close()
            r = client.post("/api/deals/noma_journeys/documents/add-and-check", json={
                "source_key": "NJ-07", "filename": "NJ-07_v2.md", "text": (SCEN / "NJ-07_v2_languages_aligned.md").read_text(encoding="utf-8")}, headers=H)
            self.assertEqual(r.status_code, 409)
            self.assertIn("Nothing was added.", r.json()["detail"])
            conn = ledger.connect(db)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM source_versions").fetchone()[0], before)
            conn.close()


if __name__ == "__main__":
    unittest.main()
