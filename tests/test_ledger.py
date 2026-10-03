"""Offline ledger tests: the seal, and the database's own enforcement.

Everything runs against a temporary folder holding a decoy sealed deal with a canary string and a
temporary database. Nothing here touches the real data/ folder, the real results/ folder, the real
coral_pay path or workspace/ledger.sqlite.
"""

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
import ledger

CANARY = "CANARY_TEXT_c0ral_9c2e"
DECOY = "coral_pay"
H = "a" * 64


def insert(conn, sql, *args):
    return conn.execute(sql, args).lastrowid


def assert_no_canary(case, conn, db_path):
    """Neither the canary nor the decoy slug may appear in the dump or in the raw database file."""
    conn.commit()
    dump = "\n".join(conn.iterdump())
    case.assertNotIn(CANARY, dump)
    case.assertNotIn(DECOY, dump)
    raw = Path(db_path).read_bytes()
    case.assertNotIn(CANARY.encode(), raw)
    case.assertNotIn(DECOY.encode(), raw)


def seed_deal(conn, slug="harbour_bank"):
    """One deal with a source version, a review, three statements (two kept, one dropped), two commitments."""
    deal = ledger.create_development_deal(conn, slug)
    source = insert(conn, "INSERT INTO sources (deal_id, source_key, display_name) VALUES (?, 'HB-01', 'Call')", deal)
    version = insert(
        conn,
        "INSERT INTO source_versions (source_id, version_no, original_sha256, canonical_sha256, adapter_name,"
        " adapter_version, doc_type, doc_date, original_filename, canonical_text, location_map)"
        " VALUES (?, 1, ?, ?, 'text_markdown', '1', 'call_transcript', '2026-09-28', 'HB-01.md', 'text', '[]')",
        source, H, H,
    )
    review = insert(conn, "INSERT INTO reviews (deal_id, run_kind, checker) VALUES (?, 'review', 'rules')", deal)
    extraction = insert(
        conn, "INSERT INTO extraction_cache (output_json, origin) VALUES ('[]', 'imported_run_file')"
    )
    insert(
        conn,
        "INSERT INTO review_sources (review_id, source_version_id, extraction_id, cache_outcome)"
        " VALUES (?, ?, ?, 'imported')",
        review, version, extraction,
    )
    statements = [
        insert(
            conn,
            "INSERT INTO statements (extraction_id, ordinal, statement_key, quote, language)"
            " VALUES (?, ?, ?, 'quote', 'firm')",
            extraction, n, f"HB-01-S0{n}",
        )
        for n in (1, 2, 3)
    ]
    for stmt, kept, rule in ((statements[0], 1, None), (statements[1], 1, None), (statements[2], 0, "sales_process")):
        insert(
            conn,
            "INSERT INTO review_statements (review_id, statement_id, source_version_id, kept, filter_rule)"
            " VALUES (?, ?, ?, ?, ?)",
            review, stmt, version, kept, rule,
        )
    commitments = [
        insert(
            conn,
            "INSERT INTO commitments (deal_id, commitment_key, created_review_id) VALUES (?, ?, ?)",
            deal, key, review,
        )
        for key in ("C01", "C02")
    ]
    conn.commit()
    return SimpleNamespace(
        deal=deal, source=source, version=version, review=review, extraction=extraction,
        statements=statements, commitments=commitments,
    )


def link(conn, s, statement, commitment):
    conn.execute(
        "INSERT INTO review_statement_commitments (review_id, statement_id, source_version_id, commitment_id)"
        " VALUES (?, ?, ?, ?)",
        (s.review, statement, s.version, commitment),
    )


class LedgerTestCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.data, self.results = root / "data", root / "results"
        self.db_path = root / "workspace" / "ledger.sqlite"

        (self.data / DECOY).mkdir(parents=True)
        (self.data / DECOY / "canary.txt").write_text(CANARY)
        self.results.mkdir()
        self.decoy_run = self.results / f"extract_{DECOY}_20260930T000000Z.json"
        self.decoy_run.write_text(json.dumps({"deal": DECOY, "note": CANARY}))
        for name in (
            "extract_harbour_bank_20260929T100933Z.json",
            "extract_harbour_bank_20260930T061113Z.json",
            "extract_hard_cases_20260930T061133Z.json",
            # Lookalikes with later timestamps: must never be picked.
            "extract_harbour_bank_20261001T000000Z_copy.json",
            "eval_extract_harbour_bank_20261001T000000Z_t0.8.json",
            "regression_extract_harbour_bank_20261001T000000Z.json",
            "extract_harbour_bank_latest.json",
        ):
            (self.results / name).write_text("{}")

        for name, value in (("DATA_DIR", self.data), ("RESULTS_DIR", self.results)):
            patcher = mock.patch.object(config, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

        self.conn = ledger.open_ledger(self.db_path)
        self.addCleanup(self.conn.close)


class TestSeal(LedgerTestCase):
    def test_allowlist_is_a_subset_of_allowed_deals_and_excludes_the_sealed_deal(self):
        self.assertTrue(set(config.LEDGER_DEALS) <= set(config.ALLOWED_DEALS))
        self.assertNotIn(DECOY, config.LEDGER_DEALS)

    def test_import_check_rejects_a_ledger_deal_that_is_not_allowed(self):
        config.check_ledger_deals(["harbour_bank"], ["harbour_bank", "hard_cases"])
        for bad in ([DECOY], ["harbour_bank", "hard_cases_x"]):
            with self.assertRaises(RuntimeError):
                config.check_ledger_deals(bad, ["harbour_bank", "hard_cases"])

    def test_creating_a_ledger_deal_for_the_decoy_raises_and_writes_nothing(self):
        with self.assertRaises(ledger.LedgerDealNotAllowed):
            ledger.create_development_deal(self.conn, DECOY)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM deals").fetchone()[0], 0)
        assert_no_canary(self, self.conn, self.db_path)

    def test_the_guard_holds_even_if_allowed_deals_is_widened(self):
        with mock.patch.object(config, "ALLOWED_DEALS", config.ALLOWED_DEALS + [DECOY]):
            with self.assertRaises(ledger.LedgerDealNotAllowed):
                ledger.create_development_deal(self.conn, DECOY)
            self.assertNotIn(DECOY, ledger.discover_run_files())
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM deals").fetchone()[0], 0)
        assert_no_canary(self, self.conn, self.db_path)

    def test_run_file_discovery_ignores_the_decoy_and_lookalikes(self):
        found = ledger.discover_run_files()
        self.assertEqual(set(found), {"harbour_bank", "hard_cases"})
        self.assertEqual(found["harbour_bank"].name, "extract_harbour_bank_20260930T061113Z.json")
        self.assertEqual(found["hard_cases"].name, "extract_hard_cases_20260930T061133Z.json")
        self.assertNotIn(self.decoy_run, found.values())

    def test_canary_never_appears_in_the_database(self):
        for slug in config.LEDGER_DEALS:
            ledger.create_development_deal(self.conn, slug)
        with self.assertRaises(ledger.LedgerDealNotAllowed):
            ledger.create_development_deal(self.conn, DECOY)
        assert_no_canary(self, self.conn, self.db_path)

    def test_database_lives_in_workspace_outside_data(self):
        self.assertEqual(config.LEDGER_DB_PATH, config.ROOT / "workspace" / "ledger.sqlite")
        self.assertFalse(config.LEDGER_DB_PATH.is_relative_to(config.ROOT / "data"))

    def test_negative_control_the_canary_check_detects_an_unguarded_write(self):
        # Throwaway unguarded code: copies the decoy run file into the database with raw SQL.
        self.conn.execute(
            "INSERT INTO deals (slug, kind, display_name) VALUES (?, 'development', ?)",
            ("leaked", self.decoy_run.read_text()),
        )
        with self.assertRaises(AssertionError):
            assert_no_canary(self, self.conn, self.db_path)

    def test_negative_control_the_guard_is_what_stops_the_decoy(self):
        with mock.patch.object(config, "LEDGER_DEALS", config.LEDGER_DEALS + [DECOY]):
            ledger.create_development_deal(self.conn, DECOY)
            self.assertIn(DECOY, ledger.discover_run_files())
        with self.assertRaises(AssertionError):
            assert_no_canary(self, self.conn, self.db_path)


class TestSchemaShape(LedgerTestCase):
    def test_tables_views_and_version(self):
        tables = {
            r[0] for r in self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        self.assertEqual(len(tables - {"schema_meta"}), 18)
        self.assertIn("review_statement_commitments", tables)
        views = {r[0] for r in self.conn.execute("SELECT name FROM sqlite_master WHERE type = 'view'")}
        self.assertEqual(views, {"issue_current_state", "commitment_status"})
        self.assertEqual(ledger.schema_version(self.conn), 1)
        self.assertEqual(self.conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)

    def test_review_statements_no_longer_holds_a_commitment_column(self):
        cols = [r[1] for r in self.conn.execute("PRAGMA table_info(review_statements)")]
        self.assertNotIn("commitment_id", cols)

    def test_link_table_primary_key_is_the_four_columns(self):
        pk = {r[1] for r in self.conn.execute("PRAGMA table_info(review_statement_commitments)") if r[5]}
        self.assertEqual(pk, {"review_id", "statement_id", "source_version_id", "commitment_id"})

    def test_reopening_does_not_recreate_the_schema(self):
        self.conn.commit()
        other = ledger.open_ledger(self.db_path)
        self.addCleanup(other.close)
        self.assertEqual(ledger.schema_version(other), 1)

    def test_user_slugs_must_be_u_plus_16_hex(self):
        ok = "u_" + "0123456789abcdef"
        self.conn.execute("INSERT INTO deals (slug, kind, display_name) VALUES (?, 'user', 'x')", (ok,))
        for bad in ("u_short", "u_" + "g" * 16, "u_" + "0" * 17, "harbour_bank"):
            with self.assertRaises(sqlite3.IntegrityError, msg=bad):
                self.conn.execute("INSERT INTO deals (slug, kind, display_name) VALUES (?, 'user', 'x')", (bad,))
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("INSERT INTO deals (slug, kind, display_name) VALUES (?, 'development', 'x')", (ok,))


class TestLinkEnforcement(LedgerTestCase):
    def setUp(self):
        super().setUp()
        self.s = seed_deal(self.conn)

    def test_one_statement_can_belong_to_two_commitments(self):
        s = self.s
        link(self.conn, s, s.statements[0], s.commitments[0])
        link(self.conn, s, s.statements[0], s.commitments[1])
        n = self.conn.execute("SELECT COUNT(*) FROM review_statement_commitments").fetchone()[0]
        self.assertEqual(n, 2)

    def test_a_dropped_statement_cannot_be_linked(self):
        with self.assertRaises(sqlite3.IntegrityError):
            link(self.conn, self.s, self.s.statements[2], self.s.commitments[0])

    def test_a_link_needs_an_existing_review_statement(self):
        with self.assertRaises(sqlite3.IntegrityError):
            link(self.conn, self.s, 9999, self.s.commitments[0])

    def test_a_link_needs_an_existing_commitment(self):
        with self.assertRaises(sqlite3.IntegrityError):
            link(self.conn, self.s, self.s.statements[0], 9999)

    def test_a_commitment_from_another_deal_cannot_be_linked(self):
        other = seed_deal(self.conn, "hard_cases")
        with self.assertRaises(sqlite3.IntegrityError):
            link(self.conn, self.s, self.s.statements[0], other.commitments[0])

    def test_a_duplicate_link_is_rejected(self):
        link(self.conn, self.s, self.s.statements[0], self.s.commitments[0])
        with self.assertRaises(sqlite3.IntegrityError):
            link(self.conn, self.s, self.s.statements[0], self.s.commitments[0])

    def test_a_linked_statement_cannot_be_changed_to_dropped(self):
        s = self.s
        link(self.conn, s, s.statements[0], s.commitments[0])
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "UPDATE review_statements SET kept = 0, filter_rule = 'sales_process' WHERE statement_id = ?",
                (s.statements[0],),
            )
        kept = self.conn.execute(
            "SELECT kept FROM review_statements WHERE statement_id = ?", (s.statements[0],)
        ).fetchone()[0]
        self.assertEqual(kept, 1)
        # An unlinked kept statement can still be dropped.
        self.conn.execute(
            "UPDATE review_statements SET kept = 0, filter_rule = 'sales_process' WHERE statement_id = ?",
            (s.statements[1],),
        )

    def test_a_linked_review_statement_cannot_change_identity_or_be_deleted(self):
        s = self.s
        link(self.conn, s, s.statements[0], s.commitments[0])
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("UPDATE review_statements SET statement_id = ? WHERE statement_id = ?",
                              (s.statements[1], s.statements[0]))
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("DELETE FROM review_statements WHERE statement_id = ?", (s.statements[0],))

    def test_links_are_append_only(self):
        s = self.s
        link(self.conn, s, s.statements[0], s.commitments[0])
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("UPDATE review_statement_commitments SET commitment_id = ?", (s.commitments[1],))
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("DELETE FROM review_statement_commitments")

    def test_a_dropped_row_needs_a_filter_rule(self):
        s = self.s
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "UPDATE review_statements SET kept = 0, filter_rule = NULL WHERE statement_id = ?",
                (s.statements[1],),
            )

    def test_a_statement_must_come_from_the_extraction_the_review_used(self):
        s = self.s
        other_extraction = insert(
            self.conn, "INSERT INTO extraction_cache (output_json, origin) VALUES ('[]', 'imported_run_file')"
        )
        stray = insert(
            self.conn,
            "INSERT INTO statements (extraction_id, ordinal, statement_key, quote, language)"
            " VALUES (?, 1, 'X-S01', 'q', 'firm')",
            other_extraction,
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO review_statements (review_id, statement_id, source_version_id, kept) VALUES (?, ?, ?, 1)",
                (s.review, stray, s.version),
            )


class TestRulesAndViews(LedgerTestCase):
    def setUp(self):
        super().setUp()
        self.s = seed_deal(self.conn)

    def add_issue(self, commitment, issue_type="approval", absolute_limit=0):
        return insert(
            self.conn,
            "INSERT INTO issues (commitment_id, issue_type, subject_key, owner_function, raised_review_id, raised_by,"
            " closure_criteria, criteria_version, absolute_limit) VALUES (?, ?, 'k', 'Product', ?, 'rules', '{}', 1, ?)",
            commitment, issue_type, self.s.review, absolute_limit,
        )

    def add_review(self):
        return insert(
            self.conn,
            "INSERT INTO reviews (deal_id, run_kind, checker) VALUES (?, 'recheck_after_fix', 'rules')",
            self.s.deal,
        )

    def add_check(self, issue, review, kind, outcome, evidence="[]", fix=None):
        return insert(
            self.conn,
            "INSERT INTO closure_checks (issue_id, review_id, check_kind, outcome, evidence_checked, reason, unmet, fix_id)"
            " VALUES (?, ?, ?, ?, ?, 'because', ?, ?)",
            issue, review, kind, outcome, evidence, None if outcome == "met" else "[]", fix,
        )

    def assess(self, commitment, review, support="supported"):
        return insert(
            self.conn,
            "INSERT INTO commitment_assessments (review_id, commitment_id, name, language, support_state)"
            " VALUES (?, ?, 'n', 'firm', ?)",
            review, commitment, support,
        )

    def status(self, commitment):
        return self.conn.execute(
            "SELECT status FROM commitment_status WHERE commitment_id = ?", (commitment,)
        ).fetchone()[0]

    def issue_state(self, issue):
        return self.conn.execute("SELECT state FROM issue_current_state WHERE issue_id = ?", (issue,)).fetchone()[0]

    def test_assessment_defaults_do_not_invent_a_value(self):
        s = self.s
        self.assess(s.commitments[0], s.review)
        row = self.conn.execute("SELECT authorisation, contractual_presence FROM commitment_assessments").fetchone()
        self.assertEqual(row, ("not_assessed", "not_assessed"))
        self.conn.execute(  # NULL still means not applicable
            "INSERT INTO commitment_assessments (review_id, commitment_id, name, language, authorisation, support_state)"
            " VALUES (?, ?, 'n', 'exploratory', NULL, 'supported')",
            (s.review, s.commitments[1]),
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO commitment_assessments (review_id, commitment_id, name, language, support_state,"
                " contractual_presence) VALUES (?, ?, 'n', 'firm', 'supported', NULL)",
                (s.review, s.commitments[0]),
            )

    def test_commitment_status_and_issue_state_follow_the_latest_check(self):
        s = self.s
        a = s.commitments[0]
        self.assess(a, s.review)
        self.assertEqual(self.status(a), "No issues raised")

        issue = self.add_issue(a)
        self.add_check(issue, s.review, "raised", "open_action")
        self.assertEqual(self.issue_state(issue), "Needs action")
        self.assertEqual(self.status(a), "Needs action")

        recheck = self.add_review()
        evidence = json.dumps([{"source_version_id": s.version, "locator": "p1", "role": "approval"}])
        self.add_check(issue, recheck, "recheck", "met", evidence)
        self.assertEqual(self.issue_state(issue), "Resolved")
        self.assertEqual(self.status(a), "Resolved")

        # Removing the evidence source never closes anything.
        self.conn.execute("UPDATE source_versions SET included = 0")
        self.assertEqual(self.issue_state(issue), "Needs evidence")
        self.assertEqual(self.status(a), "Needs evidence")

    def test_an_unsupported_commitment_is_not_in_current_documents(self):
        s = self.s
        self.assess(s.commitments[0], s.review, "unsupported")
        self.assertEqual(self.status(s.commitments[0]), "Not in current documents")

    def test_open_issues_win_over_unsupported(self):
        s = self.s
        a, b = s.commitments
        self.assess(a, s.review, "unsupported")
        self.assess(b, s.review, "unsupported")
        action = self.add_issue(a)
        self.add_check(action, s.review, "raised", "open_action")
        evidence = self.add_issue(b)
        self.add_check(evidence, s.review, "raised", "open_evidence")
        self.assertEqual(self.status(a), "Needs action")
        self.assertEqual(self.status(b), "Needs evidence")

        # Once every issue is resolved, an unsupported commitment reads Not in current documents.
        recheck = self.add_review()
        met = json.dumps([{"source_version_id": s.version}])
        self.add_check(action, recheck, "recheck", "met", met)
        self.assertEqual(self.status(a), "Not in current documents")

    def test_removing_a_source_never_hides_an_open_issue(self):
        s = self.s
        a = s.commitments[0]
        self.assess(a, s.review, "unsupported")
        issue = self.add_issue(a)
        self.add_check(issue, s.review, "raised", "open_action")
        self.conn.execute("UPDATE source_versions SET included = 0")
        self.assertEqual(self.status(a), "Needs action")

    def test_an_issue_with_no_check_is_open(self):
        s = self.s
        a = s.commitments[0]
        self.assess(a, s.review)
        issue = self.add_issue(a)
        self.assertEqual(self.issue_state(issue), "Needs action")
        self.assertEqual(self.status(a), "Needs action")

    def test_met_is_refused_on_raised_rows_and_with_empty_evidence(self):
        s = self.s
        issue = self.add_issue(s.commitments[0])
        evidence = json.dumps([{"source_version_id": s.version}])
        with self.assertRaises(sqlite3.IntegrityError):
            self.add_check(issue, s.review, "raised", "met", evidence)
        with self.assertRaises(sqlite3.IntegrityError):
            self.add_check(issue, self.add_review(), "recheck", "met", "[]")

    def test_closure_checks_and_statements_are_immutable(self):
        s = self.s
        issue = self.add_issue(s.commitments[0])
        self.add_check(issue, s.review, "raised", "open_action")
        for sql in ("UPDATE closure_checks SET reason = 'x'", "DELETE FROM closure_checks",
                    "UPDATE statements SET quote = 'x'", "DELETE FROM statements"):
            with self.assertRaises(sqlite3.IntegrityError, msg=sql):
                self.conn.execute(sql)

    def test_issues_and_commitments_change_only_owner_and_note_and_are_never_deleted(self):
        issue = self.add_issue(self.s.commitments[0])
        self.conn.execute("UPDATE issues SET owner_function = 'Commercial', note = 'n' WHERE id = ?", (issue,))
        self.conn.execute("UPDATE commitments SET note = 'n'")
        for sql in ("UPDATE issues SET closure_criteria = '{\"loosened\": 1}'", "DELETE FROM issues",
                    "UPDATE commitments SET commitment_key = 'Z'", "DELETE FROM commitments"):
            with self.assertRaises(sqlite3.IntegrityError, msg=sql):
                self.conn.execute(sql)

    def test_source_versions_are_immutable_except_included(self):
        self.conn.execute("UPDATE source_versions SET included = 0")
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("UPDATE source_versions SET canonical_text = 'changed'")
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("DELETE FROM source_versions")

    def test_a_finished_review_is_frozen(self):
        self.conn.execute("UPDATE reviews SET status = 'complete', finished_at = '2026-10-03T10:00:00Z'")
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("UPDATE reviews SET note = 'late edit'")

    def test_fix_approval_needs_issue_and_evidence_then_freezes(self):
        s = self.s
        issue = self.add_issue(s.commitments[0])
        with self.assertRaises(sqlite3.IntegrityError):  # created as draft only
            self.conn.execute(
                "INSERT INTO fixes (deal_id, fix_key, version_no, route, owner_function, rationale, status, approved_at,"
                " approved_by) VALUES (?, 'F0', 1, 'align_documents', 'Commercial', 'r', 'approved', 't', 'me')",
                (s.deal,),
            )
        fix = insert(
            self.conn,
            "INSERT INTO fixes (deal_id, fix_key, version_no, route, owner_function, rationale)"
            " VALUES (?, 'F1', 1, 'align_documents', 'Commercial', 'r')",
            s.deal,
        )
        approve = "UPDATE fixes SET status = 'approved', approved_at = '2026-10-03T10:00:00Z', approved_by = 'Lina' WHERE id = ?"
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(approve, (fix,))  # no issue
        self.conn.execute("INSERT INTO fix_issues (fix_id, issue_id) VALUES (?, ?)", (fix, issue))
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(approve, (fix,))  # no evidence
        self.conn.execute("INSERT INTO fix_evidence (fix_id, source_version_id) VALUES (?, ?)", (fix, s.version))
        self.conn.execute(approve, (fix,))
        for sql, args in (
            ("UPDATE fixes SET rationale = 'x' WHERE id = ?", (fix,)),
            ("DELETE FROM fixes WHERE id = ?", (fix,)),
            ("DELETE FROM fix_issues WHERE fix_id = ?", (fix,)),
            ("INSERT INTO fix_evidence (fix_id, source_version_id) VALUES (?, " + str(s.version) + ")", (fix,)),
        ):
            with self.assertRaises(sqlite3.IntegrityError, msg=sql):
                self.conn.execute(sql, args)

    def test_an_absolute_limit_is_not_closed_by_an_allowed_exception(self):
        s = self.s
        issue = self.add_issue(s.commitments[0], absolute_limit=1)
        fix = insert(
            self.conn,
            "INSERT INTO fixes (deal_id, fix_key, version_no, route, owner_function, rationale)"
            " VALUES (?, 'F1', 1, 'allowed_exception', 'Product', 'r')",
            s.deal,
        )
        evidence = json.dumps([{"source_version_id": s.version}])
        with self.assertRaises(sqlite3.IntegrityError):
            self.add_check(issue, self.add_review(), "recheck", "met", evidence, fix=fix)


if __name__ == "__main__":
    unittest.main()
