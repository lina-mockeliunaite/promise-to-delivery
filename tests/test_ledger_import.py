"""Offline tests for the development import.

Expected values are read from the real frozen run files and the real development docs (read-only). The
import itself runs on byte-identical copies in a temporary folder, into a temporary database, so nothing
here touches the real data/ folder beyond those reads, the real sealed_decoy path or workspace/ledger.sqlite.
"""

import contextlib
import io
import json
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
import ledger
import ledger_import

REAL_DATA = config.DATA_DIR
REAL_RESULTS = config.RESULTS_DIR
CANARY = "CANARY_TEXT_c0ral_9c2e"
DECOY = "sealed_decoy"
DEALS = ("harbour_bank", "hard_cases")

EXPECTED = {  # per deal: sources, source_versions, extractions, review_sources, statements, outcomes
    "harbour_bank": dict(sources=8, extractions=6, statements=20, imported=6, not_extracted=2),
    "hard_cases": dict(sources=5, extractions=4, statements=10, imported=4, not_extracted=1),
}
EXPECTED_TOTALS = {
    "closure_checks": 0, "commitment_assessments": 0, "commitment_links": 0, "commitments": 0,
    "deals": 2, "extraction_cache": 10, "fix_evidence": 0, "fix_issues": 0, "fixes": 0, "issues": 0,
    "reference_resolutions": 0, "review_sources": 13, "review_statement_commitments": 0,
    "review_statements": 0, "reviews": 2, "source_versions": 13, "sources": 13, "statements": 30,
}


def normalise(text):
    return " ".join(text.split())


def real_run(slug):
    return json.loads((REAL_RESULTS / config.LEDGER_IMPORT_RUN_FILES[slug]).read_text(encoding="utf-8"))


def assert_no_canary(case, conn, db_path):
    conn.commit()
    dump = "\n".join(conn.iterdump())
    case.assertNotIn(CANARY, dump)
    case.assertNotIn(DECOY, dump)
    raw = Path(db_path).read_bytes()
    case.assertNotIn(CANARY.encode(), raw)
    case.assertNotIn(DECOY.encode(), raw)


class ImportCase(unittest.TestCase):
    """Temporary data and results folders holding copies of the two development deals and a decoy."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.data, self.results = self.root / "data", self.root / "results"
        self.results.mkdir()
        for slug in DEALS:  # docs only; labels are never copied or read
            shutil.copytree(REAL_DATA / slug / "docs", self.data / slug / "docs")
            name = config.LEDGER_IMPORT_RUN_FILES[slug]
            shutil.copyfile(REAL_RESULTS / name, self.results / name)
        (self.data / DECOY / "docs").mkdir(parents=True)
        (self.data / DECOY / "docs" / "canary.txt").write_text(CANARY)
        (self.data / DECOY / "docs" / "manifest.json").write_text(json.dumps({"deal": DECOY, "documents": []}))
        self.decoy_run = self.results / f"extract_{DECOY}_20260930T000000Z.json"
        self.decoy_run.write_text(json.dumps({"deal": DECOY, "documents": [], "note": CANARY}))

        # These tests are about the two original development deals; other ledger deals have their own tests.
        for name, value in (("DATA_DIR", self.data), ("RESULTS_DIR", self.results), ("LEDGER_DEALS", list(DEALS))):
            patcher = mock.patch.object(config, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

        self.db_path = self.root / "workspace" / "ledger.sqlite"
        self.conn = ledger.open_ledger(self.db_path)
        self.addCleanup(self.conn.close)

    def counts(self):
        return ledger_import.table_counts(self.conn)

    def dump(self):
        return "\n".join(self.conn.iterdump())


class TestImportContents(ImportCase):
    def setUp(self):
        super().setUp()
        ledger_import.import_all(self.conn)

    def deal_id(self, slug):
        return self.conn.execute("SELECT id FROM deals WHERE slug = ?", (slug,)).fetchone()[0]

    def test_row_counts_per_table(self):
        self.assertEqual(self.counts(), EXPECTED_TOTALS)

    def test_row_counts_per_deal(self):
        q = self.conn.execute
        for slug, want in EXPECTED.items():
            deal = self.deal_id(slug)
            self.assertEqual(q("SELECT COUNT(*) FROM sources WHERE deal_id = ?", (deal,)).fetchone()[0], want["sources"], slug)
            self.assertEqual(
                q("SELECT COUNT(*) FROM source_versions v JOIN sources s ON s.id = v.source_id WHERE s.deal_id = ?", (deal,)).fetchone()[0],
                want["sources"], slug,
            )
            self.assertEqual(q("SELECT COUNT(*) FROM reviews WHERE deal_id = ?", (deal,)).fetchone()[0], 1, slug)
            outcomes = dict(q(
                "SELECT cache_outcome, COUNT(*) FROM review_sources rs JOIN reviews r ON r.id = rs.review_id"
                " WHERE r.deal_id = ? GROUP BY cache_outcome", (deal,),
            ))
            self.assertEqual(outcomes, {"imported": want["imported"], "not_extracted": want["not_extracted"]}, slug)
            self.assertEqual(
                q("SELECT COUNT(DISTINCT rs.extraction_id) FROM review_sources rs JOIN reviews r ON r.id = rs.review_id"
                  " WHERE r.deal_id = ?", (deal,)).fetchone()[0],
                want["extractions"], slug,
            )
            self.assertEqual(
                q("SELECT COUNT(*) FROM statements s JOIN review_sources rs ON rs.extraction_id = s.extraction_id"
                  " JOIN reviews r ON r.id = rs.review_id WHERE r.deal_id = ?", (deal,)).fetchone()[0],
                want["statements"], slug,
            )

    def stored_statements(self, slug):
        return {
            row[0]: row for row in self.conn.execute(
                "SELECT s.statement_key, s.quote, s.speaker, s.language, s.ordinal FROM statements s"
                " JOIN review_sources rs ON rs.extraction_id = s.extraction_id"
                " JOIN reviews r ON r.id = rs.review_id WHERE r.deal_id = ?", (self.deal_id(slug),),
            )
        }

    def test_every_stored_quote_is_byte_identical_to_the_run_file(self):
        for slug in DEALS:
            stored = self.stored_statements(slug)
            expected = [s for doc in real_run(slug)["documents"] for s in doc["statements"]]
            self.assertEqual(len(stored), len(expected), slug)
            for stmt in expected:
                row = stored[stmt["statement_id"]]
                self.assertEqual(row[1].encode("utf-8"), stmt["quote"].encode("utf-8"), stmt["statement_id"])
                self.assertEqual(row[2], stmt["speaker"], stmt["statement_id"])
                self.assertEqual(row[3], stmt["language"], stmt["statement_id"])

    def test_extraction_output_json_is_the_run_files_statements(self):
        for slug in DEALS:
            for doc in real_run(slug)["documents"]:
                if doc["status"] != "complete":
                    continue
                stored = self.conn.execute(
                    "SELECT e.output_json FROM extraction_cache e JOIN review_sources rs ON rs.extraction_id = e.id"
                    " JOIN source_versions v ON v.id = rs.source_version_id JOIN sources s ON s.id = v.source_id"
                    " WHERE s.deal_id = ? AND s.source_key = ?", (self.deal_id(slug), doc["source_id"]),
                ).fetchone()[0]
                self.assertEqual(json.loads(stored), doc["statements"], doc["source_id"])

    def test_source_versions_hold_the_documents_with_independent_hashes(self):
        import hashlib
        for slug in DEALS:
            for doc in real_run(slug)["documents"]:
                raw = (REAL_DATA / slug / "docs" / doc["file"]).read_bytes()
                text = raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
                row = self.conn.execute(
                    "SELECT v.original_sha256, v.canonical_sha256, v.canonical_text, v.doc_type, v.doc_date,"
                    " v.original_filename, v.version_no, v.included, v.adapter_name, v.adapter_version"
                    " FROM source_versions v JOIN sources s ON s.id = v.source_id WHERE s.deal_id = ? AND s.source_key = ?",
                    (self.deal_id(slug), doc["source_id"]),
                ).fetchone()
                self.assertEqual(row[0], hashlib.sha256(raw).hexdigest(), doc["source_id"])
                self.assertEqual(row[1], hashlib.sha256(text.encode("utf-8")).hexdigest(), doc["source_id"])
                self.assertEqual(row[2], text, doc["source_id"])
                self.assertEqual(row[3:8], (doc["doc_type"], doc["date"], doc["file"], 1, 1), doc["source_id"])
                self.assertEqual(row[8:], ("text_markdown", "1"), doc["source_id"])

    def test_every_quote_is_found_in_its_canonical_text(self):
        failures = []
        for slug in DEALS:
            texts = {
                key: normalise(text) for key, text in self.conn.execute(
                    "SELECT s.source_key, v.canonical_text FROM source_versions v JOIN sources s ON s.id = v.source_id"
                    " WHERE s.deal_id = ?", (self.deal_id(slug),),
                )
            }
            for key, quote in self.conn.execute(
                "SELECT s.statement_key, s.quote FROM statements s JOIN review_sources rs ON rs.extraction_id = s.extraction_id"
                " JOIN reviews r ON r.id = rs.review_id WHERE r.deal_id = ?", (self.deal_id(slug),),
            ):
                if normalise(quote) not in texts[key.rsplit("-S", 1)[0]]:
                    failures.append(f"{slug}:{key}")
        self.assertEqual(failures, [], "quotes not found in their canonical text")

    def test_location_map_paragraphs_point_into_the_text(self):
        for text, location in self.conn.execute("SELECT canonical_text, location_map FROM source_versions"):
            paragraphs = json.loads(location)
            self.assertTrue(paragraphs)
            previous_end = 0
            for n, p in enumerate(paragraphs, start=1):
                self.assertEqual(p["paragraph"], n)
                self.assertGreaterEqual(p["start"], previous_end)
                self.assertGreater(p["end"], p["start"])
                self.assertEqual(text[p["start"]:p["end"]].strip(), text[p["start"]:p["end"]])
                self.assertNotIn("\n\n", text[p["start"]:p["end"]])
                previous_end = p["end"]
            self.assertEqual(text[paragraphs[0]["start"]:].lstrip(), text[paragraphs[0]["start"]:])

    def test_imported_extractions_are_never_reusable(self):
        rows = self.conn.execute(
            "SELECT origin, reusable, key_sha256, canonical_sha256, context_sha256, cache_format_version,"
            " thinking_param_sent, source_run_file FROM extraction_cache"
        ).fetchall()
        self.assertEqual(len(rows), 10)
        for origin, reusable, key, canonical, context, fmt, sent, run_file in rows:
            self.assertEqual((origin, reusable, key, canonical, context, fmt, sent),
                             ("imported_run_file", 0, None, None, None, None, "none"))
            self.assertIn(run_file, config.LEDGER_IMPORT_RUN_FILES.values())

    def test_each_deal_has_one_complete_build_time_review(self):
        import hashlib
        for slug in DEALS:
            review = self.conn.execute(
                "SELECT run_kind, checker, status, finished_at, cost_usd, note, source_set_sha256, decision_evidence_sha256,"
                " config_sha256 FROM reviews WHERE deal_id = ?", (self.deal_id(slug),),
            ).fetchone()
            self.assertEqual(review[:3], ("review", "rules", "complete"))
            self.assertIsNotNone(review[3])
            self.assertEqual(review[4], 0.0)
            self.assertIn(config.LEDGER_IMPORT_RUN_FILES[slug], review[5])
            self.assertEqual(review[7], hashlib.sha256(b"").hexdigest())
            self.assertIsNone(review[8])
            lines = sorted(
                f"{key}:1:{canonical}:{doc_type}:{date}" for key, canonical, doc_type, date in self.conn.execute(
                    "SELECT s.source_key, v.canonical_sha256, v.doc_type, v.doc_date FROM source_versions v"
                    " JOIN sources s ON s.id = v.source_id WHERE s.deal_id = ?", (self.deal_id(slug),),
                )
            )
            self.assertEqual(review[6], hashlib.sha256("\n".join(lines).encode()).hexdigest())

    def test_running_the_import_again_refuses_and_changes_nothing(self):
        before = self.dump()
        with self.assertRaises(ledger_import.LedgerImportError):
            ledger_import.import_all(self.conn)
        for slug in DEALS:
            with self.assertRaises(ledger_import.LedgerImportError):
                ledger_import.import_deal(self.conn, slug)
        self.assertEqual(self.dump(), before)
        self.assertEqual(self.counts(), EXPECTED_TOTALS)


class TestImportSeal(ImportCase):
    def test_the_decoy_cannot_be_imported_even_if_allowed_deals_is_widened(self):
        with self.assertRaises(ledger.LedgerDealNotAllowed):
            ledger_import.import_deal(self.conn, DECOY)
        with mock.patch.object(config, "ALLOWED_DEALS", config.ALLOWED_DEALS + [DECOY]):
            with self.assertRaises(ledger.LedgerDealNotAllowed):
                ledger_import.import_deal(self.conn, DECOY)
            ledger_import.import_all(self.conn)
        self.assertEqual(self.counts(), EXPECTED_TOTALS)
        assert_no_canary(self, self.conn, self.db_path)

    def test_import_all_never_reads_the_decoy_run_file(self):
        opened = []
        original = Path.read_text

        def spy(path, *args, **kwargs):
            opened.append(Path(path).name)
            return original(path, *args, **kwargs)

        with mock.patch.object(Path, "read_text", spy):
            ledger_import.import_all(self.conn)
        self.assertNotIn(self.decoy_run.name, opened)
        self.assertEqual({n for n in opened if n.startswith("extract_")}, {config.LEDGER_IMPORT_RUN_FILES[d] for d in config.LEDGER_DEALS})
        assert_no_canary(self, self.conn, self.db_path)

    def test_negative_control_the_canary_check_detects_a_leak(self):
        ledger_import.import_all(self.conn)
        self.conn.execute(
            "INSERT INTO deals (slug, kind, display_name) VALUES ('leaked', 'development', ?)",
            (self.decoy_run.read_text(),),
        )
        with self.assertRaises(AssertionError):
            assert_no_canary(self, self.conn, self.db_path)

    def test_a_newer_run_file_refuses_instead_of_replacing_the_pinned_one(self):
        newer = self.results / "extract_harbour_bank_20261001T000000Z.json"
        shutil.copyfile(self.results / config.LEDGER_IMPORT_RUN_FILES["harbour_bank"], newer)
        with self.assertRaises(ledger_import.LedgerImportError):
            ledger_import.import_deal(self.conn, "harbour_bank")
        self.assertEqual(self.counts()["deals"], 0)
        # Lookalike names are never candidates, so they do not trigger the refusal.
        newer.unlink()
        (self.results / "extract_harbour_bank_20261001T000000Z_copy.json").write_text("{}")
        ledger_import.import_deal(self.conn, "harbour_bank")
        self.assertEqual(self.counts()["deals"], 1)


class TestValidationAndAtomicity(ImportCase):
    """A synthetic deal 'fake' with one call (two statements) and one reference-only note."""

    SLUG = "fake"

    def setUp(self):
        super().setUp()
        docs = self.data / self.SLUG / "docs"
        docs.mkdir(parents=True)
        (docs / "F-01_call.md").write_text("Intro line.\n\nWe will deliver X by May.\nAnd Y too.\n", encoding="utf-8")
        (docs / "F-02_note.md").write_text("A pricing note.\n", encoding="utf-8")
        self.manifest = {"deal": self.SLUG, "documents": [
            {"source_id": "F-01", "file": "F-01_call.md", "doc_type": "call_transcript", "date": "2026-11-01"},
            {"source_id": "F-02", "file": "F-02_note.md", "doc_type": "pricing_services_note", "date": "2026-11-02"},
        ]}
        stmts = [
            {"quote": "We will deliver X by May.", "speaker": "A", "language": "firm", "statement_id": "F-01-S01",
             "source_id": "F-01", "doc_type": "call_transcript", "date": "2026-11-01"},
            {"quote": "And Y too.", "speaker": "A", "language": "conditional", "statement_id": "F-01-S02",
             "source_id": "F-01", "doc_type": "call_transcript", "date": "2026-11-01"},
        ]
        self.run = {
            "deal": self.SLUG, "model": "m", "max_tokens": 1, "thinking_mode": "model_default",
            "thinking_param_sent": None,
            "prompt_hashes": {"system_prompt_sha256": "s", "user_template_sha256": "u", "schema_sha256": "h"},
            "documents": [
                {**self.manifest["documents"][0], "status": "complete", "error": None, "attempts": 1,
                 "statements": stmts, "input_tokens": 1, "output_tokens": 1, "thinking_tokens": 0, "cost_usd": 0.001},
                {**self.manifest["documents"][1], "status": "skipped_reference_only", "error": None, "attempts": 0,
                 "statements": []},
            ],
        }
        self.run_name = "extract_fake_20260930T000000Z.json"
        for name, value in (
            ("LEDGER_DEALS", config.LEDGER_DEALS + [self.SLUG]),
            ("ALLOWED_DEALS", config.ALLOWED_DEALS + [self.SLUG]),
            ("LEDGER_IMPORT_RUN_FILES", {**config.LEDGER_IMPORT_RUN_FILES, self.SLUG: self.run_name}),
        ):
            patcher = mock.patch.object(config, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.write()

    def write(self):
        (self.data / self.SLUG / "docs" / "manifest.json").write_text(json.dumps(self.manifest))
        (self.results / self.run_name).write_text(json.dumps(self.run))

    def assert_refused(self, mutate):
        mutate()
        self.write()
        with self.assertRaises(ledger_import.LedgerImportError):
            ledger_import.import_deal(self.conn, self.SLUG)
        self.assertEqual(self.counts()["deals"], 0)
        self.assertEqual(sum(self.counts().values()), 0)

    def test_the_synthetic_deal_imports(self):
        ledger_import.import_deal(self.conn, self.SLUG)
        counts = self.counts()
        self.assertEqual((counts["sources"], counts["extraction_cache"], counts["statements"], counts["review_sources"]), (2, 1, 2, 2))

    def test_manifest_and_run_file_must_agree(self):
        self.assert_refused(lambda: self.manifest["documents"][0].update(date="2026-11-09"))

    def test_a_source_missing_from_the_run_file_refuses(self):
        self.assert_refused(lambda: self.run["documents"].pop())

    def test_a_wrong_statement_id_refuses(self):
        self.assert_refused(lambda: self.run["documents"][0]["statements"][1].update(statement_id="F-01-S03"))

    def test_an_incomplete_document_refuses(self):
        self.assert_refused(lambda: self.run["documents"][0].update(status="incomplete"))

    def test_a_skipped_document_with_statements_refuses(self):
        self.assert_refused(lambda: self.run["documents"][1].update(statements=[self.run["documents"][0]["statements"][0]]))

    def test_an_unknown_doc_type_refuses(self):
        def mutate():
            self.manifest["documents"][1]["doc_type"] = "mystery"
            self.run["documents"][1]["doc_type"] = "mystery"
        self.assert_refused(mutate)

    def test_a_run_file_for_another_deal_refuses(self):
        self.assert_refused(lambda: self.run.update(deal="harbour_bank"))

    def test_a_missing_document_file_refuses(self):
        self.assert_refused(lambda: (self.data / self.SLUG / "docs" / "F-02_note.md").unlink())

    def test_a_failure_mid_write_rolls_everything_back(self):
        with mock.patch.object(ledger_import, "_insert_statements", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                ledger_import.import_deal(self.conn, self.SLUG)
        self.assertEqual(sum(self.counts().values()), 0)

    def test_import_all_is_all_or_nothing_across_deals(self):
        pins = {k: v for k, v in config.LEDGER_IMPORT_RUN_FILES.items() if k != "hard_cases"}
        with mock.patch.object(config, "LEDGER_IMPORT_RUN_FILES", pins):
            with self.assertRaises(ledger_import.LedgerImportError):
                ledger_import.import_all(self.conn)  # harbour_bank would import; hard_cases has no pin
        self.assertEqual(sum(self.counts().values()), 0)


class TestBuild(ImportCase):
    def setUp(self):
        super().setUp()
        self.conn.close()
        self.target = self.root / "build" / "ledger.sqlite"
        self.building = self.target.with_name(self.target.name + ".building")

    def test_a_fresh_build_creates_the_database_with_the_expected_counts(self):
        counts = ledger_import.build(self.target)
        self.assertEqual(counts, EXPECTED_TOTALS)
        self.assertTrue(self.target.exists())
        self.assertFalse(self.building.exists())
        conn = ledger.open_ledger(self.target)
        self.addCleanup(conn.close)
        self.assertEqual(ledger_import.table_counts(conn), EXPECTED_TOTALS)

    def test_building_again_refuses_and_leaves_the_file_unchanged(self):
        ledger_import.build(self.target)
        before = self.target.read_bytes()
        with self.assertRaises(ledger_import.LedgerImportError):
            ledger_import.build(self.target)
        self.assertEqual(self.target.read_bytes(), before)
        self.assertFalse(self.building.exists())

    def test_rebuild_replaces_the_database(self):
        ledger_import.build(self.target)
        self.assertEqual(ledger_import.build(self.target, rebuild=True), EXPECTED_TOTALS)
        self.assertFalse(self.building.exists())

    def test_a_failed_rebuild_keeps_the_old_database(self):
        ledger_import.build(self.target)
        before = self.target.read_bytes()
        with mock.patch.object(ledger_import, "import_all", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                ledger_import.build(self.target, rebuild=True)
        self.assertEqual(self.target.read_bytes(), before)
        self.assertFalse(self.building.exists())

    def test_a_failed_first_build_leaves_no_files(self):
        with mock.patch.object(ledger_import, "import_all", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                ledger_import.build(self.target)
        self.assertFalse(self.target.exists())
        self.assertFalse(self.building.exists())

    def test_the_cli_builds_then_refuses_then_rebuilds(self):
        with mock.patch.object(config, "LEDGER_DB_PATH", self.target):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(ledger_import.main([]), 0)
            self.assertIn("statements", out.getvalue())
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(ledger_import.main([]), 2)
                self.assertEqual(ledger_import.main(["--bogus"]), 2)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(ledger_import.main(["--rebuild"]), 0)

    def test_the_cli_refuses_the_decoy_if_it_were_in_the_pins(self):
        # The guard, not the pin, decides: a pinned decoy is still refused because it is not in LEDGER_DEALS.
        pins = {**config.LEDGER_IMPORT_RUN_FILES, DECOY: self.decoy_run.name}
        with mock.patch.object(config, "LEDGER_IMPORT_RUN_FILES", pins):
            conn = ledger.open_ledger(self.root / "x.sqlite")
            self.addCleanup(conn.close)
            with self.assertRaises(ledger.LedgerDealNotAllowed):
                ledger_import.import_deal(conn, DECOY)


if __name__ == "__main__":
    unittest.main()
