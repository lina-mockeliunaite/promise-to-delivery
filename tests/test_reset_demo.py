"""reset_demo.py: backs up the ledger, rebuilds it from the v2 demo deals with saved v2 findings, makes no model call,
and never writes to data/. Everything runs in temporary files; workspace/ledger.sqlite and results/v2_cache are never
touched. (Until 10 Oct this file also proved the reset never read Coral Pay; Coral Pay is now a released demo deal.)
"""

import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
import ledger_consolidate
import ledger_fixes
import reset_demo
import scenarios

_active = False
_events = []
WATCHED = {"open", "os.listdir", "os.scandir", "glob.glob", "os.rename", "os.remove", "os.mkdir"}


def _hook(event, args):
    if _active and event in WATCHED:
        _events.append((event, tuple(str(a) for a in args)))


sys.addaudithook(_hook)  # cannot be removed; it records only while a test turns it on


def data_snapshot():
    """(path, size, mtime) of every file in the development deal folders, the catalogue and the scenarios: stat only."""
    roots = [config.DATA_DIR / slug for slug in dict.fromkeys(config.LEDGER_DEALS + config.V2_DEALS)] + [config.DATA_DIR / "scenarios"]
    files = [config.DATA_DIR / "catalogue.json"]
    for root in roots:
        files += [p for p in root.rglob("*") if p.is_file()] if root.is_dir() else []
    return sorted((str(p), p.stat().st_size, p.stat().st_mtime_ns) for p in files)


class ResetCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.db = self.dir / "ledger.sqlite"
        cache = tempfile.TemporaryDirectory()
        self.addCleanup(cache.cleanup)
        p = mock.patch.object(config, "V2_CACHE_DIR", Path(cache.name))
        p.start()
        self.addCleanup(p.stop)

    def old_ledger_with_a_user_deal(self):
        conn = scenarios.build_fresh(self.db)
        deal = ledger_fixes.create_user_deal(conn, "Created in the app")
        conn.close()
        return deal

    def slugs(self, path):
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            return {r[0] for r in conn.execute("SELECT slug FROM deals")}
        finally:
            conn.close()


class TestReset(ResetCase):
    def test_it_backs_up_the_old_ledger_and_builds_a_fresh_one(self):
        user_deal = self.old_ledger_with_a_user_deal()
        now = datetime(2026, 10, 5, 11, 2, 3, tzinfo=timezone.utc)
        done = reset_demo.reset(self.db, now=now)
        backup = self.dir / "ledger.backup-20261005T110203Z.sqlite"
        self.assertEqual(done["backup"], backup)
        self.assertIn(user_deal, self.slugs(backup))            # what the app had is kept
        self.assertNotIn(user_deal, self.slugs(self.db))        # the new ledger is fresh
        self.assertEqual(self.slugs(self.db), set(config.V2_DEALS))
        harbour = next(d for d in done["deals"] if d["deal"] == "harbour_bank")
        self.assertEqual((harbour["freshness"], harbour["open_issues"]), ("Up to date", 6))
        self.assertEqual(done["commitments"]["harbour_bank"], 3)
        self.assertEqual(done["model_calls"], 0)
        self.assertEqual(sorted(p.name for p in self.dir.iterdir()), [backup.name, "ledger.sqlite"])  # no temp files left

    def test_the_demo_starts_on_the_current_hash_definition_so_a_handoff_can_be_saved(self):
        import handoff
        import integrity
        import ledger
        import ledger_fixes
        done = reset_demo.reset(self.db)
        self.assertEqual(done["model_calls"], 0)
        conn = ledger.connect(self.db)
        self.addCleanup(conn.close)
        for slug in config.V2_DEALS:
            fresh = ledger_fixes.freshness(conn, ledger_fixes.deal_id(conn, slug))
            self.assertEqual((fresh["state"], fresh["reasons"]), ("Up to date", []), slug)
            self.assertEqual(integrity.review_config(conn, fresh["review_id"])[0], integrity.HASH_DEFINITION)
            self.assertEqual(conn.execute("SELECT checker FROM reviews WHERE id = ?", (fresh["review_id"],)).fetchone()[0], "model_v2")
        self.assertEqual(handoff.save(conn, "harbour_bank", "not_ready", "Lina", "", [])["version"], 1)

    def test_with_no_existing_ledger_there_is_nothing_to_back_up(self):
        done = reset_demo.reset(self.db)
        self.assertIsNone(done["backup"])
        self.assertTrue(self.db.exists())
        self.assertEqual([p.name for p in self.dir.iterdir()], ["ledger.sqlite"])

    def test_a_failed_build_leaves_the_old_ledger_untouched_and_no_backup_or_temp_file(self):
        self.old_ledger_with_a_user_deal()
        before = self.db.read_bytes()
        import ledger_v2
        with mock.patch.object(ledger_v2, "review", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                reset_demo.reset(self.db)
        self.assertEqual(self.db.read_bytes(), before)
        self.assertEqual([p.name for p in self.dir.iterdir()], ["ledger.sqlite"])

    def test_two_resets_in_one_second_do_not_overwrite_a_backup(self):
        self.old_ledger_with_a_user_deal()
        now = datetime(2026, 10, 5, 11, 2, 3, tzinfo=timezone.utc)
        reset_demo.reset(self.db, now=now)
        with self.assertRaisesRegex(reset_demo.ResetError, "already exists"):
            reset_demo.reset(self.db, now=now)
        self.assertEqual(len(list(self.dir.glob("ledger.backup-*.sqlite"))), 1)

    def test_it_refuses_to_write_a_ledger_inside_the_data_folder(self):
        with self.assertRaisesRegex(reset_demo.ResetError, "data folder"):
            reset_demo.reset(config.DATA_DIR / "ledger.sqlite")
        self.assertFalse((config.DATA_DIR / "ledger.sqlite").exists())
        self.assertFalse((config.DATA_DIR / "ledger.sqlite.resetting").exists())


class TestTitlesSurviveReset(ResetCase):
    """19 Oct: plain titles are keyed by commitment key, so the keys must be the same after every reset."""

    def test_alder_keeps_the_same_three_commitment_keys_and_titles_after_reset(self):
        import deal_stage
        import handover
        import ledger
        import workspace
        titles = deal_stage.load_profile("alder_bank")["titles"]
        self.assertEqual(len(titles), 3)
        for _ in range(2):  # a second reset must not move the keys either
            reset_demo.reset(self.db)
            conn = ledger.connect(self.db)
            self.addCleanup(conn.close)
            did = ledger_fixes.deal_id(conn, "alder_bank")
            keys = {k for (k,) in conn.execute("SELECT commitment_key FROM commitments WHERE deal_id = ?", (did,))}
            self.assertEqual(keys, set(titles))
            shown = {c["name"]: c["display_name"] for c in workspace.overview(conn, "alder_bank")["commitments"]}
            self.assertEqual(sorted(shown.values()), sorted(titles.values()))
            self.assertEqual(handover._display_names(conn, did, "alder_bank"), {n: t for n, t in shown.items()})

    def test_every_register_commitment_carries_a_stable_opaque_ref_for_the_address_bar(self):
        import json
        import ledger
        import re
        import workspace
        reset_demo.reset(self.db)
        conn = ledger.connect(self.db)
        self.addCleanup(conn.close)
        reg = workspace.overview(conn, "alder_bank")
        refs = {c["name"]: c["ref"] for c in reg["commitments"]}
        self.assertEqual(len(refs), 3)
        self.assertEqual(len(set(refs.values())), 3)
        self.assertTrue(all(re.fullmatch(r"[0-9a-f]{12}", r) for r in refs.values()))
        self.assertTrue(all("key" not in c for c in reg["commitments"]))  # the internal commitment key itself never reaches a reader
        self.assertNotIn("v2-", json.dumps(reg))
        reset_demo.reset(self.db)  # a second reset gives the same refs, so a shared link still opens the same commitment
        conn2 = ledger.connect(self.db)
        self.addCleanup(conn2.close)
        self.assertEqual({c["name"]: c["ref"] for c in workspace.overview(conn2, "alder_bank")["commitments"]}, refs)

    def test_other_deals_have_no_titles(self):
        import ledger
        import workspace
        reset_demo.reset(self.db)
        conn = ledger.connect(self.db)
        self.addCleanup(conn.close)
        self.assertEqual(workspace.commitment_titles("harbour_bank"), {})
        self.assertTrue(all(c["display_name"] is None for c in workspace.overview(conn, "harbour_bank")["commitments"]))


class TestDocumentStages(ResetCase):
    """19 Oct: each document returned by the documents API carries the stage the stage bar places it at."""

    def test_alder_documents_carry_the_stage_the_stage_bar_uses(self):
        import ledger
        import workspace
        reset_demo.reset(self.db)
        conn = ledger.connect(self.db)
        self.addCleanup(conn.close)
        stages = {d["source_key"]: d["stage"] for d in workspace.documents(conn, "alder_bank")}
        self.assertEqual(stages, {"AB-01": "discovery", "AB-02": "evaluation", "AB-03": "proposal", "AB-04": "proposal",
                                  "AB-05": "proposal", "AB-06": "contracting", "AB-07": "contracting", "AB-08": "contracting"})
        bar = {s["key"]: len(s["documents"]) for s in workspace.overview(conn, "alder_bank")["stage"]["stages"]}
        for key in bar:  # the sidebar and the stage bar's own counts agree, including a stage with none (shortlisted)
            self.assertEqual(sum(1 for v in stages.values() if v == key), bar[key], key)

    def test_a_document_taken_out_has_no_stage_and_nothing_else_changes(self):
        import ledger
        import ledger_fixes
        import workspace
        reset_demo.reset(self.db)
        conn = ledger.connect(self.db)
        self.addCleanup(conn.close)
        before = {d["source_key"]: d["stage"] for d in workspace.documents(conn, "alder_bank")}
        did = ledger_fixes.deal_id(conn, "alder_bank")
        conn.execute("UPDATE source_versions SET included = 0 WHERE source_id = (SELECT id FROM sources WHERE deal_id = ?"
                     " AND source_key = 'AB-08')", (did,))
        after = {d["source_key"]: d["stage"] for d in workspace.documents(conn, "alder_bank")}
        self.assertIsNone(after["AB-08"])
        self.assertEqual({k: v for k, v in after.items() if k != "AB-08"}, {k: v for k, v in before.items() if k != "AB-08"})


class _NoModel:
    """A client that fails the test the moment anything tries to call the model."""

    def __getattr__(self, name):
        raise AssertionError(f"the model was called ({name})")


class TestSignedPaperwork(ResetCase):
    """19 Oct: the deal is Signed only by a signed contract or SOW in the documents; the checks never read it."""

    def conn(self):
        import ledger
        reset_demo.reset(self.db)
        conn = ledger.connect(self.db)
        self.addCleanup(conn.close)
        return conn

    def findings(self, conn):
        import workspace
        # A rerun words an open finding's reason with a lead ("Still holds on the current documents.") the first review lacks.
        lead = "Still holds on the current documents. "
        return [(c["name"], sorted((i["type"], i["state"], i["reason"].removeprefix(lead)) for i in c["issues"]))
                for c in workspace.overview(conn, "alder_bank")["commitments"]]

    def test_the_reset_leaves_alder_unsigned_at_contracting(self):
        import workspace
        conn = self.conn()
        stage = workspace.overview(conn, "alder_bank")["stage"]
        self.assertEqual((stage["current"], stage["basis"]), ("contracting", "documents"))
        self.assertNotIn("AB-09", {d["source_key"] for d in workspace.documents(conn, "alder_bank")})

    def test_uploading_the_signed_contract_signs_the_deal_and_check_again_makes_no_model_call(self):
        import ledger_fixes
        import ledger_v2
        import workspace
        conn = self.conn()
        before = self.findings(conn)
        text = (config.DATA_DIR / "scenarios" / "AB-09_signed_contract.md").read_text(encoding="utf-8")
        did = ledger_fixes.deal_id(conn, "alder_bank")
        self.assertFalse(ledger_v2.needs_model(conn, "alder_bank", "AB-09", "signed_contract", text))
        ledger_fixes.add_source(conn, "alder_bank", "Signed contract", text, "AB-09_signed_contract.md", "signed_contract", "2026-10-20")
        self.assertEqual(workspace.overview(conn, "alder_bank")["stage"]["current"], "signed")
        self.assertEqual(ledger_fixes.freshness(conn, did)["state"], "Up to date")  # documents the checks don't read: not stale
        self.assertNotIn("signed_contract", {d["doc_type"] for d in ledger_v2.current_docs(conn, did)})  # the checks never read it
        result = ledger_v2.review(conn, "alder_bank", client=_NoModel())
        self.assertEqual(result["model_calls"], 0)
        self.assertEqual(ledger_fixes.freshness(conn, did)["state"], "Up to date")
        self.assertEqual(self.findings(conn), before)  # not one finding changed

    def test_a_note_survives_the_signed_contract_and_the_review_stays_current(self):
        import handover
        import ledger_fixes
        import workspace
        import workspace_records
        conn = self.conn()
        did = ledger_fixes.deal_id(conn, "alder_bank")
        before = ledger_fixes.source_set_sha256(conn, did)
        reg = workspace.overview(conn, "alder_bank")
        first, second = reg["open_rows"][0], reg["open_rows"][1]
        ids = lambda cid: [i["id"] for c in reg["commitments"] if c["id"] == cid for i in c["issues"] if i["state"] != "Resolved"]
        for iid in ids(first):
            handover.resolve_by_note(conn, "alder_bank", iid, "Sam (Delivery)", "The customer agreed on the 14 Oct call.")
        decided = ids(second)[0]
        workspace_records.okay_to_proceed(conn, "alder_bank", decided, "Sam (Delivery)", "Delivery will raise it at kick-off.")
        conn.commit()
        self.assertIn(first, workspace.overview(conn, "alder_bank")["noted_rows"])
        text = (config.DATA_DIR / "scenarios" / "AB-09_signed_contract.md").read_text(encoding="utf-8")
        ledger_fixes.add_source(conn, "alder_bank", "Signed contract", text, "AB-09_signed_contract.md", "signed_contract", "2026-10-20")
        self.assertEqual(ledger_fixes.source_set_sha256(conn, did), before)  # signed paperwork is not in the hash
        after = workspace.overview(conn, "alder_bank")
        self.assertEqual(after["stage"]["current"], "signed")
        self.assertEqual(after["freshness"]["state"], "Up to date")
        self.assertIn(first, after["noted_rows"])  # still "Addressed by note", not reopened
        note = next(i["note_resolution"] for c in after["commitments"] if c["id"] == first for i in c["issues"] if i["note_resolution"])
        self.assertTrue(note["current"])
        item = next(i for c in after["commitments"] if c["id"] == second for i in c["issues"] if i["id"] == decided)
        self.assertEqual(item["decision"]["status"], "okay")  # the kept-open note is still current too

    def test_a_signed_sow_signs_the_deal_too_and_both_types_are_reference_only(self):
        import ledger_fixes
        import workspace
        conn = self.conn()
        for kind in ("signed_contract", "signed_sow"):
            self.assertIn(kind, config.REFERENCE_ONLY_DOC_TYPES)
            self.assertNotIn(kind, config.EXTRACTABLE_DOC_TYPES)
        ledger_fixes.add_source(conn, "alder_bank", "Signed SOW", "Signed by both parties.", "sow.md", "signed_sow", "2026-10-20")
        self.assertEqual(workspace.overview(conn, "alder_bank")["stage"]["current"], "signed")
        placed = {d["source_key"]: d["stage"] for d in workspace.documents(conn, "alder_bank")}
        self.assertEqual(list(placed.values()).count("signed"), 1)


class TestHandoverOwner(ResetCase):
    def test_the_handover_view_names_the_deal_owner_for_the_locked_record(self):
        import handover
        import ledger
        import ledger_fixes
        reset_demo.reset(self.db)
        conn = ledger.connect(self.db)
        self.addCleanup(conn.close)
        view = handover.handover(conn, "alder_bank")
        self.assertEqual(view["owner"], "Tom Fraser")  # from the Alder profile, read now; the snapshot is untouched
        self.assertFalse(view["complete"])


class TestBoundaries(ResetCase):
    def test_it_never_writes_to_data(self):
        global _active
        self.old_ledger_with_a_user_deal()
        before = data_snapshot()
        _events.clear()
        _active = True
        try:
            reset_demo.reset(self.db)
        finally:
            _active = False
        self.assertEqual(data_snapshot(), before)  # no file in the development data changed, appeared or vanished
        data_root = str(config.DATA_DIR.resolve())
        writes = [e for e in _events if e[0] == "open" and data_root in e[1][0].replace(str(config.DATA_DIR), data_root)
                  and len(e[1]) > 1 and any(m in e[1][1] for m in "wax+")]
        self.assertEqual(writes, [])
        self.assertTrue(any(e[0] == "open" and "harbour_bank" in e[1][0] for e in _events))  # it did read the dev deal

    def test_the_app_shows_exactly_the_v2_deals(self):
        self.assertEqual(config.UI_DEALS, config.V2_DEALS)

    def test_it_makes_no_model_call_and_needs_no_api_key(self):
        import anthropic
        with mock.patch.dict(os.environ, {}, clear=True), \
                mock.patch.object(anthropic, "Anthropic", side_effect=AssertionError("model client created")):
            done = reset_demo.reset(self.db)
        self.assertEqual(done["model_calls"], 0)

    def test_the_command_line_takes_no_arguments_and_prints_what_it_did(self):
        import io
        from contextlib import redirect_stdout, redirect_stderr
        self.assertEqual(reset_demo.main(["--oops"]), 2)
        out = io.StringIO()
        with mock.patch.object(config, "LEDGER_DB_PATH", self.db), redirect_stdout(out), redirect_stderr(io.StringIO()):
            self.assertEqual(reset_demo.main([]), 0)
        text = out.getvalue()
        self.assertIn("Demo reset.", text)
        self.assertIn("nothing to back up", text)
        self.assertIn("harbour_bank, 3 commitments, 6 open issues, review up to date", text)
        self.assertIn("model calls: 0", text)


if __name__ == "__main__":
    unittest.main()
