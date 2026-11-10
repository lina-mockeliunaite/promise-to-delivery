"""POST /api/demo/reset (10 Nov): the in-app "Reset demo". It reuses reset_demo.reset on the app's ledger path and
changes none of its build logic. Everything runs on a temporary ledger and a temporary reading cache; the real
workspace/ledger.sqlite is never opened.
"""

import hashlib
import os
import sqlite3
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
import reset_demo
from test_handover import HandoverCase
from test_api_workspace import H

RESET = "/api/demo/reset"
FIXED = datetime(2026, 11, 10, 9, 0, 0, tzinfo=timezone.utc)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class ResetApiCase(HandoverCase):
    def setUp(self):
        super().setUp()
        cache = tempfile.TemporaryDirectory()
        self.addCleanup(cache.cleanup)
        p = mock.patch.object(config, "V2_CACHE_DIR", Path(cache.name))
        p.start()
        self.addCleanup(p.stop)

    def notes_on_harbour(self):
        notes = self.client.get("/api/deals/harbour_bank/register").json()["handover"]["notes"]
        return {k: v for k, v in notes.items() if v}

    def leftovers(self):
        return sorted(p.name for p in self.db.parent.iterdir() if p.name.endswith(".resetting"))


class TestReset(ResetApiCase):
    def test_a_changed_ledger_is_restored_and_the_report_is_complete(self):
        self.both_notes()
        self.assertTrue(self.notes_on_harbour())
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ANTHROPIC_API_KEY", None)  # no key needed
            r = self.client.post(RESET, json={}, headers=H)
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertEqual(body["deals_restored"], 5)
        self.assertEqual(body["deals"], list(config.V2_DEALS))
        self.assertEqual(body["model_calls"], 0)
        self.assertRegex(body["backup"], r"^ledger\.backup-\d{8}T\d{6}Z\.sqlite$")
        self.assertTrue((self.db.parent / body["backup"]).exists())
        self.assertFalse(self.notes_on_harbour())  # the note is gone from the live ledger
        backup = sqlite3.connect(self.db.parent / body["backup"])
        try:
            self.assertGreater(backup.execute("SELECT COUNT(*) FROM handover_notes").fetchone()[0], 0)  # and kept in the backup
        finally:
            backup.close()
        self.assertEqual(self.leftovers(), [])

    def test_it_works_on_a_deal_whose_handover_is_locked(self):
        self.both_notes()
        self.sign()
        self.assertEqual(self.post("/api/deals/harbour_bank/handover/complete", {"completed_by": "Sam"}).status_code, 200)
        self.assertEqual(self.post("/api/deals/harbour_bank/note", {"note": "x", "entered_by": "y"}).status_code, 409)  # locked
        r = self.client.post(RESET, json={}, headers=H)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.post("/api/deals/harbour_bank/note", {"note": "after reset", "entered_by": "y"}).status_code, 200)

    def test_it_is_refused_without_the_write_guard_headers(self):
        self.both_notes()
        before = sha(self.db)
        self.assertEqual(self.client.post(RESET, json={}).status_code, 403)
        self.assertEqual(self.client.post(RESET, data="x", headers={**H, "Content-Type": "text/plain"}).status_code, 403)
        self.assertEqual(sha(self.db), before)

    def test_it_reads_no_api_key_and_makes_no_model_call(self):
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-sentinel-not-a-key"}):
            with mock.patch.object(reset_demo, "reset", wraps=reset_demo.reset) as spy:
                r = self.client.post(RESET, json={}, headers=H)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertNotIn("sk-sentinel", r.text)
        self.assertEqual(r.json()["model_calls"], 0)
        spy.assert_called_once_with(self.db)


class TestFailure(ResetApiCase):
    def test_a_backup_name_collision_is_a_409_and_the_old_ledger_is_untouched(self):
        fixed = mock.Mock(wraps=datetime)
        fixed.now.return_value = FIXED
        with mock.patch.object(reset_demo, "datetime", fixed):
            self.assertEqual(self.client.post(RESET, json={}, headers=H).status_code, 200)
            self.both_notes()
            before = sha(self.db)
            r = self.client.post(RESET, json={}, headers=H)
        self.assertEqual(r.status_code, 409)
        self.assertIn("already exists", r.json()["detail"])
        self.assertEqual(sha(self.db), before)
        self.assertTrue(self.notes_on_harbour())
        self.assertEqual(self.leftovers(), [])

    def test_an_unexpected_failure_is_a_plain_500_and_the_old_ledger_is_untouched(self):
        self.both_notes()
        before = sha(self.db)
        with mock.patch.object(reset_demo, "build", side_effect=RuntimeError("secret internals")):
            r = self.client.post(RESET, json={}, headers=H)
        self.assertEqual(r.status_code, 500)
        self.assertNotIn("secret internals", r.text)
        self.assertIn("left as it was", r.json()["detail"])
        self.assertEqual(sha(self.db), before)
        self.assertEqual(self.leftovers(), [])

    def test_a_failed_reset_does_not_block_the_next_one(self):
        with mock.patch.object(reset_demo, "reset", side_effect=RuntimeError("boom")):
            self.assertEqual(self.client.post(RESET, json={}, headers=H).status_code, 500)
        with mock.patch.object(reset_demo, "reset", side_effect=reset_demo.ResetError("name taken")):
            self.assertEqual(self.client.post(RESET, json={}, headers=H).status_code, 409)
        r = self.client.post(RESET, json={}, headers=H)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["deals_restored"], 5)

    def test_a_second_reset_while_one_runs_is_a_409_and_the_first_still_finishes(self):
        started, release = threading.Event(), threading.Event()
        real = reset_demo.reset

        def slow(*a, **k):
            started.set()
            release.wait(10)
            return real(*a, **k)

        results = []
        with mock.patch.object(reset_demo, "reset", slow):
            t = threading.Thread(target=lambda: results.append(self.client.post(RESET, json={}, headers=H)))
            t.start()
            self.assertTrue(started.wait(10))
            second = self.client.post(RESET, json={}, headers=H)
            release.set()
            t.join(30)
        self.assertEqual(second.status_code, 409)
        self.assertIn("already running", second.json()["detail"])
        self.assertEqual(results[0].status_code, 200, results[0].text)


class TestTheSwapIsSafeWhileTheServerRuns(ResetApiCase):
    def test_a_connection_open_during_the_reset_keeps_its_snapshot_and_the_next_one_sees_the_new_ledger(self):
        self.both_notes()
        old = sqlite3.connect(self.db)
        try:
            self.assertGreater(old.execute("SELECT COUNT(*) FROM handover_notes").fetchone()[0], 0)
            inode_before = os.stat(self.db).st_ino
            self.assertEqual(self.client.post(RESET, json={}, headers=H).status_code, 200)
            self.assertNotEqual(os.stat(self.db).st_ino, inode_before)  # a new file replaced it (os.replace), not an in-place rewrite
            self.assertGreater(old.execute("SELECT COUNT(*) FROM handover_notes").fetchone()[0], 0)  # the old handle still reads old data
        finally:
            old.close()
        fresh = sqlite3.connect(self.db)
        try:
            table = fresh.execute("SELECT 1 FROM sqlite_master WHERE name = 'handover_notes'").fetchone()
            self.assertTrue(not table or fresh.execute("SELECT COUNT(*) FROM handover_notes").fetchone()[0] == 0)  # created lazily
        finally:
            fresh.close()
        self.assertEqual(self.leftovers(), [])

    def test_the_new_ledger_is_built_in_a_temporary_file_and_swapped_in_with_one_replace(self):
        calls = []
        real = os.replace
        with mock.patch.object(reset_demo.os, "replace", lambda a, b: (calls.append((Path(a).name, Path(b).name)), real(a, b))[1]):
            self.assertEqual(self.client.post(RESET, json={}, headers=H).status_code, 200)
        self.assertEqual(calls, [("ledger.sqlite.resetting", "ledger.sqlite")])


if __name__ == "__main__":
    unittest.main()
