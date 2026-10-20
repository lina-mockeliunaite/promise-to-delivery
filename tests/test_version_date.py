"""Each version shows its own date (20 Oct): the date set on it, else the date the document states, else the day it was added.
A new version inherits the previous version's recorded date, so the recorded date alone would show the original's."""

import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import workspace


class TestStatedDate(unittest.TestCase):
    def test_reads_the_documents_own_date_line(self):
        self.assertEqual(workspace.stated_date("# DRAFT SOW\n\nDate: 16 October 2026\n\nBody"), "2026-10-16")
        self.assertEqual(workspace.stated_date("Title\nDate: 2026-10-06\n"), "2026-10-06")
        self.assertEqual(workspace.stated_date("Date: 9 October 2026"), "2026-10-09")

    def test_no_date_or_an_unreadable_one_is_none(self):
        self.assertIsNone(workspace.stated_date("No date here"))
        self.assertIsNone(workspace.stated_date("Date: sometime in autumn"))
        self.assertIsNone(workspace.stated_date("Date: 5 Octobre 2026"))
        self.assertIsNone(workspace.stated_date(""))
        self.assertIsNone(workspace.stated_date("\n" * 40 + "Date: 16 October 2026"))  # only the opening lines count


class TestVersionDate(unittest.TestCase):
    def test_version_one_keeps_its_recorded_date(self):
        self.assertEqual(workspace.version_date(1, "2026-10-09", None, "Date: 1 January 2026", "2026-10-20T01:00:00Z"), "2026-10-09")

    def test_a_later_version_shows_the_date_it_states(self):
        self.assertEqual(workspace.version_date(2, "2026-10-09", "2026-10-09", "Date: 16 October 2026", "2026-10-20T01:00:00Z"), "2026-10-16")

    def test_without_a_stated_date_it_shows_the_day_it_was_added(self):
        self.assertEqual(workspace.version_date(2, "2026-10-09", "2026-10-09", "no date line", "2026-10-20T01:00:00Z"), "2026-10-20")

    def test_a_date_someone_set_on_the_version_wins(self):
        self.assertEqual(workspace.version_date(2, "2026-10-15", "2026-10-09", "Date: 16 October 2026", "2026-10-20T01:00:00Z"), "2026-10-15")


class TestDocumentsCarryIt(unittest.TestCase):
    def test_documents_list_the_version_date_and_leave_the_recorded_date_alone(self):
        import ledger
        import ledger_fixes
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            conn = ledger.open_ledger(Path(tmp) / "l.sqlite")
            did = conn.execute("INSERT INTO deals (slug, kind, display_name) VALUES ('harbour_bank', 'development', 'harbour_bank')").lastrowid
            conn.commit()
            ledger_fixes.add_source(conn, "harbour_bank", "Draft SOW", "# SOW\n\nDate: 9 October 2026\n", "sow.md", "draft_sow", "2026-10-09")
            key = conn.execute("SELECT source_key FROM sources WHERE deal_id = ?", (did,)).fetchone()[0]
            ledger_fixes.add_source_version(conn, "harbour_bank", key, "# SOW\n\nDate: 16 October 2026\n", "sow2.md")
            doc = [d for d in workspace.documents(conn, "harbour_bank") if d["included"]][0]
            self.assertEqual((doc["version"], doc["date"], doc["version_date"]), (2, "2026-10-09", "2026-10-16"))
            conn.close()


if __name__ == "__main__":
    unittest.main()
