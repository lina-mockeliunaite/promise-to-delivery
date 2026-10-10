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
