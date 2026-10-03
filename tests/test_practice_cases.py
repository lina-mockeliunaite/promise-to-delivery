"""The frozen practice deal (Tidewater Pay): fingerprints hold, the pinned run file imports, and the rules run on it.

This checks plumbing only. It does not assert any score: the practice set is for the rules-vs-agent comparison, and
its results are recorded against the frozen labels, never tuned to them. Labels are not read here.
"""

import hashlib
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
import ledger
import ledger_consolidate
import ledger_import

SLUG = "practice_cases"
REAL_DATA, REAL_RESULTS = config.DATA_DIR, config.RESULTS_DIR


class TestFrozenFingerprints(unittest.TestCase):
    def test_every_frozen_file_matches_its_fingerprint(self):
        lines = (REAL_DATA / "practice_cases.sha256").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 8)
        for line in lines:
            digest, rel = line.split(maxsplit=1)
            self.assertEqual(hashlib.sha256((config.ROOT / rel.strip()).read_bytes()).hexdigest(), digest, rel)

    def test_the_deal_is_allowlisted_and_pinned(self):
        self.assertIn(SLUG, config.ALLOWED_DEALS)
        self.assertIn(SLUG, config.LEDGER_DEALS)
        self.assertTrue((REAL_RESULTS / config.LEDGER_IMPORT_RUN_FILES[SLUG]).is_file())


class TestImportAndRules(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        data, results = root / "data", root / "results"
        shutil.copytree(REAL_DATA / SLUG / "docs", data / SLUG / "docs")  # docs only: BRIEF and labels never copied
        shutil.copyfile(REAL_DATA / "catalogue.json", data / "catalogue.json")
        results.mkdir()
        name = config.LEDGER_IMPORT_RUN_FILES[SLUG]
        shutil.copyfile(REAL_RESULTS / name, results / name)
        for attr, value in (("DATA_DIR", data), ("RESULTS_DIR", results), ("LEDGER_DEALS", [SLUG])):
            patcher = mock.patch.object(config, attr, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.conn = ledger.open_ledger(root / "ledger.sqlite")
        self.addCleanup(self.conn.close)

    def test_it_imports_and_every_issue_has_its_raised_check(self):
        ledger_import.import_all(self.conn)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM statements").fetchone()[0], 15)
        ledger_consolidate.consolidate_all(self.conn, assess=True)
        n_issues = self.conn.execute("SELECT COUNT(*) FROM issues").fetchone()[0]
        n_checks = self.conn.execute("SELECT COUNT(*) FROM closure_checks WHERE check_kind = 'raised'").fetchone()[0]
        self.assertEqual(n_issues, n_checks)
        dump = "\n".join(self.conn.iterdump())
        self.assertNotIn("PROPOSED BY CLAUDE", dump)
        self.assertNotIn("Confirmed by Lina", dump)  # label text never reaches the ledger


if __name__ == "__main__":
    unittest.main()
