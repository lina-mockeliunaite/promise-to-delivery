"""Decision integrity: three-hash bindings, versioned hash definitions, human records that never touch findings, and
ownership that carries forward only for the verified same issue.

Ledgers are built in temporary files from the development deals, with a scripted fake in place of the model. No label
file is read and nothing under data/coral_pay/ is touched.
"""

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
import handoff
import integrity
import ledger_fixes
import recheck
import scenarios
import workspace
from test_recheck import FakeExtractor, NoModel, build_current

SOW = (config.DATA_DIR / "harbour_bank" / "docs" / "HB-06_draft_sow.md").read_text(encoding="utf-8")
SOW_QUOTES = [
    "The payout ledger connector will handle up to 12,000 payouts per day at launch.",
    "Provider will provide NUSD wallet screening for HarbourPay Global payouts on Ethereum and Polygon through Elva's pre-built"
    " connector to Customer's configured blockchain analytics service, in accordance with the Wallet Screening Specification in Annex A.",
    "The parties will hold a weekly project status meeting during implementation.",
    "A.1 Ethereum: each recipient wallet is screened through the analytics integration in real time before the payout is released.",
    "A.2 Polygon: recipient wallets are screened through the analytics integration in batches at hourly intervals.",
    "A Polygon payout is released after the next completed screening batch returns a clear result.",
]


def payload(quotes):
    return {"statements": [{"quote": q, "speaker": "x", "language": "firm"} for q in quotes]}


class IntegrityCase(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(config, "LEDGER_DEALS", ["harbour_bank", "hard_cases"])
        patcher.start()
        self.addCleanup(patcher.stop)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.conn = build_current(Path(tmp.name) / "ledger.sqlite")
        self.addCleanup(self.conn.close)
        self.did = ledger_fixes.deal_id(self.conn, "harbour_bank")

    def issue(self, commitment_key, issue_type):
        return self.conn.execute(
            "SELECT i.id FROM issues i JOIN commitments c ON c.id = i.commitment_id WHERE c.deal_id = ? AND c.commitment_key = ?"
            " AND i.issue_type = ? ORDER BY i.id", (self.did, commitment_key, issue_type)).fetchone()[0]

    def hashes(self):
        return ledger_fixes.source_set_sha256(self.conn, self.did), ledger_fixes.decision_evidence_sha256(self.conn, self.did)

    def findings(self):
        """Everything a human record must leave alone."""
        return (self.conn.execute("SELECT * FROM issues ORDER BY id").fetchall(),
                self.conn.execute("SELECT * FROM closure_checks ORDER BY id").fetchall(),
                json.dumps(workspace.register(self.conn, "harbour_bank")["counts"], sort_keys=True))

    def open_ids(self):
        reg = workspace.register(self.conn, "harbour_bank")
        return [i["id"] for c in reg["commitments"] for i in c["issues"] if i["state"] != "Resolved"]

    def save(self, decision="proceed"):
        return handoff.save(self.conn, "harbour_bank", decision, "Lina", "", self.open_ids() if decision == "proceed" else [])

    def rerun(self, client=None):
        return recheck.recheck(self.conn, "harbour_bank", None, client or NoModel())

    def revise_sow(self, text, quotes):
        ledger_fixes.add_source_version(self.conn, "harbour_bank", "HB-06", text, "HB-06_v2.md")
        return self.rerun(FakeExtractor(payload(quotes)))

    def freshness(self):
        return ledger_fixes.freshness(self.conn, self.did)


class TestHashDefinitions(IntegrityCase):
    def test_definition_two_adds_recheck_py_and_a_canonical_catalogue(self):
        raw = (config.DATA_DIR / "catalogue.json").read_bytes()
        reindented = json.dumps(json.loads(raw), indent=3).encode()
        self.assertNotEqual(integrity.config_sha256(1, raw), integrity.config_sha256(2, raw))
        self.assertNotEqual(integrity.config_sha256(1, raw), integrity.config_sha256(1, reindented))  # definition 1 sees whitespace
        self.assertEqual(integrity.config_sha256(2, raw), integrity.config_sha256(2, reindented))
        self.assertIn("recheck.py", integrity.CONFIG_FILES)
        with mock.patch.object(integrity, "CONFIG_FILES", integrity.lc.RULE_FILES):
            without = integrity.config_sha256(2, raw)
        self.assertNotEqual(without, integrity.config_sha256(2, raw))

    def test_an_older_definition_never_reads_as_documents_changed(self):
        stored1 = integrity.config_sha256(1)
        src, ev = self.hashes()
        out = integrity.compare(self.conn, self.did, src, ev, 1, stored1)
        self.assertEqual(out["reasons"], [integrity.OLDER_DEFINITION])
        self.assertEqual(integrity.compare(self.conn, self.did, src, ev, 1, None)["reasons"], [integrity.NO_CONFIG])
        self.assertEqual(integrity.compare(self.conn, self.did, src, ev, 1, "0" * 64)["reasons"],
                         [integrity.RULES, integrity.OLDER_DEFINITION])
        self.assertEqual(integrity.compare(self.conn, self.did, src, ev, 2, integrity.config_sha256(2))["reasons"], [integrity.OLDER_DEFINITION])
        self.assertEqual(integrity.compare(self.conn, self.did, src, ev, 3, integrity.config_sha256(3))["reasons"], [])

    def test_the_ledger_schema_version_is_unchanged_and_ensure_schema_is_idempotent(self):
        integrity.ensure_schema(self.conn)
        integrity.ensure_schema(self.conn)
        self.assertEqual(self.conn.execute("SELECT value FROM schema_meta WHERE key = 'schema_version'").fetchone()[0], "2")

    def test_an_existing_database_without_the_tables_keeps_its_data_and_reads_as_definition_one(self):
        for table in reversed(integrity.TABLES):
            for (trigger,) in self.conn.execute("SELECT name FROM sqlite_master WHERE type = 'trigger' AND tbl_name = ?", (table,)).fetchall():
                self.conn.execute(f"DROP TRIGGER {trigger}")
            self.conn.execute(f"DROP TABLE {table}")
        before = self.findings()
        fresh = self.freshness()
        self.assertEqual((fresh["state"], fresh["reasons"]), ("Up to date", [integrity.OLDER_DEFINITION]))
        integrity.ensure_schema(self.conn)
        self.assertEqual(self.findings(), before)


class TestReviewsAndHandoffs(IntegrityCase):
    def test_a_review_records_its_definition_and_a_handoff_binds_all_three_hashes(self):
        review_id = self.freshness()["review_id"]
        self.assertEqual(integrity.review_config(self.conn, review_id), (3, integrity.config_sha256(3)))
        self.save()
        hid = self.conn.execute("SELECT id FROM handoff_versions").fetchone()[0]
        row = self.conn.execute("SELECT hash_definition, source_set_sha256, decision_evidence_sha256, config_sha256 FROM decision_bindings"
                                " WHERE decision_kind = 'handoff' AND decision_id = ?", (hid,)).fetchone()
        self.assertEqual(row, (3, *self.hashes(), integrity.config_sha256(3)))
        self.assertFalse(handoff.get_version(self.conn, "harbour_bank")["changed_since_saved"])
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("UPDATE decision_bindings SET config_sha256 = ?", ("0" * 64,))
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("DELETE FROM review_bindings")

    def test_a_catalogue_change_marks_the_review_and_the_saved_decision_and_nothing_appears_current(self):
        self.save()
        changed = json.loads((config.DATA_DIR / "catalogue.json").read_text(encoding="utf-8"))
        changed["_edited"] = "test"
        with mock.patch.object(integrity, "catalogue_bytes", lambda: json.dumps(changed).encode()):
            fresh = self.freshness()
            self.assertEqual((fresh["state"], fresh["reasons"]), ("Review out of date", [integrity.RULES]))
            view = handoff.get_version(self.conn, "harbour_bank")
            self.assertTrue(view["changed_since_saved"])
            self.assertEqual(view["reasons"], [integrity.RULES])
            self.assertFalse(integrity.decision_summary(self.conn, "harbour_bank")["current"])
            with self.assertRaisesRegex(handoff.HandoffError, "Rerun the review"):
                self.save("not_ready")

    def test_re_indenting_the_catalogue_is_not_a_change(self):
        self.save()
        raw = json.loads((config.DATA_DIR / "catalogue.json").read_text(encoding="utf-8"))
        with mock.patch.object(integrity, "catalogue_bytes", lambda: json.dumps(raw, indent=7).encode()):
            self.assertEqual(self.freshness()["state"], "Up to date")
            self.assertFalse(handoff.get_version(self.conn, "harbour_bank")["changed_since_saved"])

    def test_a_new_document_version_marks_the_decision_with_documents_changed(self):
        self.save()
        note = (config.DATA_DIR / "harbour_bank" / "docs" / "HB-05_pricing_services_note.md").read_text(encoding="utf-8")
        ledger_fixes.add_source_version(self.conn, "harbour_bank", "HB-05", note + "\n", "HB-05_v2.md")
        view = handoff.get_version(self.conn, "harbour_bank")
        self.assertEqual((view["changed_since_saved"], view["reasons"]), (True, [integrity.DOCUMENTS]))

    def test_a_handoff_saved_before_bindings_reads_as_checking_rules_updated_and_is_not_rewritten(self):
        with mock.patch.object(integrity, "write_review_binding", lambda *a, **k: None):
            self.rerun()  # a review as the old code wrote it: definition 1
        handoff.ensure_schema(self.conn)
        review = self.freshness()["review_id"]
        src, ev = self.hashes()
        self.conn.execute(
            "INSERT INTO handoff_versions (deal_id, version_no, review_id, source_set_sha256, decision_evidence_sha256, decision,"
            " reviewer, decided_on, snapshot_json) VALUES (?, 1, ?, ?, ?, 'not_ready', 'Lina', '2026-10-05', '{}')", (self.did, review, src, ev))
        self.conn.commit()
        view = handoff.get_version(self.conn, "harbour_bank")
        self.assertEqual(view["handoff"], {})
        self.assertTrue(view["changed_since_saved"])
        self.assertEqual(view["reasons"], [integrity.OLDER_DEFINITION])
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM decision_bindings").fetchone()[0], 0)

    def test_an_imported_review_is_not_comparable_and_no_decision_can_be_saved_on_it(self):
        conn = scenarios.build_fresh(Path(tempfile.mkdtemp()) / "l.sqlite")
        self.addCleanup(conn.close)
        did = ledger_fixes.deal_id(conn, "harbour_bank")
        fresh = ledger_fixes.freshness(conn, did)
        self.assertEqual((fresh["state"], fresh["reasons"]), ("Up to date", [integrity.NO_CONFIG]))
        with self.assertRaisesRegex(handoff.HandoffError, "Rerun the review"):
            handoff.save(conn, "harbour_bank", "not_ready", "Lina", "", [])
        self.assertFalse(integrity.decision_summary(conn, "harbour_bank")["current"])
        recheck.recheck(conn, "harbour_bank", None, NoModel())  # the rerun makes no model call and moves it to definition 2
        self.assertEqual(ledger_fixes.freshness(conn, did)["reasons"], [])

    def test_a_review_made_under_definition_one_cannot_back_a_decision_until_rerun(self):
        with mock.patch.object(integrity, "write_review_binding", lambda *a, **k: None):
            self.rerun()
        fresh = self.freshness()
        self.assertEqual((fresh["state"], fresh["reasons"]), ("Up to date", [integrity.OLDER_DEFINITION]))
        with self.assertRaisesRegex(handoff.HandoffError, "Rerun the review"):
            self.save("not_ready")
        self.assertEqual(integrity.decision_summary(self.conn, "harbour_bank")["message"], integrity.REVIEW_STALE)
        self.rerun()
        self.assertEqual(self.freshness()["reasons"], [])
        self.assertEqual(self.save("not_ready")["version"], 1)

    def test_extraction_settings_are_recorded_and_shown_never_a_reason(self):
        self.revise_sow(SOW.replace("hourly", "every hour"), SOW_QUOTES)
        self.assertEqual(self.freshness()["notes"], [])
        with mock.patch.object(config, "MAX_TOKENS", config.MAX_TOKENS + 1):
            fresh = self.freshness()
        self.assertEqual((fresh["state"], fresh["reasons"], fresh["notes"]), ("Up to date", [], [integrity.EXTRACTION_NOTE]))
        keys = json.loads(self.conn.execute("SELECT extraction_keys FROM review_bindings WHERE review_id = ?", (fresh["review_id"],)).fetchone()[0])
        self.assertTrue(any(v is None for v in keys.values()) and any(v is not None for v in keys.values()))  # imported and extracted

    def test_a_recheck_reuses_an_extraction_made_under_a_different_config_and_the_binding_records_it(self):
        self.revise_sow(SOW.replace("hourly", "every hour"), SOW_QUOTES)
        with mock.patch.object(config, "MAX_TOKENS", config.MAX_TOKENS + 1):
            result = self.rerun()  # NoModel: any model call fails the test
        self.assertEqual(result["model_calls"], 0)


class TestRerunLabels(IntegrityCase):
    def test_inputs_changed_not_run_kind_says_whether_a_rerun_saw_new_inputs(self):
        same = self.rerun()
        self.assertEqual((same["run_kind"], same["inputs_changed"]), ("unchanged_input_rerun", False))
        changed = self.revise_sow(SOW.replace("hourly", "every hour"), SOW_QUOTES)
        self.assertEqual((changed["run_kind"], changed["inputs_changed"]), ("unchanged_input_rerun", True))  # run_kind is as before
        rows = dict(self.conn.execute("SELECT review_id, inputs_changed FROM review_bindings").fetchall())
        self.assertEqual((rows[same["review_id"]], rows[changed["review_id"]]), (0, 1))
        note = self.conn.execute("SELECT note FROM reviews WHERE id = ?", (changed["review_id"],)).fetchone()[0]
        self.assertTrue(note.endswith("; documents changed"), note)
        self.assertEqual(self.conn.execute("SELECT note FROM reviews WHERE id = ?", (same["review_id"],)).fetchone()[0].count(";"), 0)

    def test_a_first_review_has_no_inputs_changed_value(self):
        deal = ledger_fixes.create_user_deal(self.conn, "Clean deal")
        text = "We might look at full case audit history later.\n"
        ledger_fixes.add_source(self.conn, deal, "Call", text, "c.md", "call_transcript", "2026-11-01")
        result = recheck.recheck(self.conn, deal, None, FakeExtractor({"statements": [{"quote": text.strip(), "speaker": "x", "language": "exploratory"}]}))
        self.assertEqual((result["run_kind"], result["inputs_changed"]), ("review", False))
        value = self.conn.execute("SELECT inputs_changed FROM review_bindings WHERE review_id = ?", (result["review_id"],)).fetchone()[0]
        self.assertIsNone(value)


class TestHumanRecordsNeverTouchFindings(IntegrityCase):
    def test_owner_and_note_edits_change_neither_hash_nor_freshness_nor_a_saved_handoff(self):
        self.save()
        before = self.hashes()
        self.conn.execute("UPDATE issues SET owner_function = 'Delivery', note = 'call Product' WHERE id = ?", (self.issue("C01", "conflicting_terms"),))
        self.conn.commit()
        self.assertEqual(self.hashes(), before)
        self.assertEqual(self.freshness()["state"], "Up to date")
        self.assertFalse(handoff.get_version(self.conn, "harbour_bank")["changed_since_saved"])

    def test_accepting_a_risk_keeps_the_finding_open_and_the_review_current(self):
        findings, hashes = self.findings(), self.hashes()
        iid = self.issue("C01", "conflicting_terms")
        integrity.record_accepted_risk(self.conn, "harbour_bank", iid, "Daniel Koh", "Customer accepts the hourly interval for the beta.")
        self.assertEqual(self.findings(), findings)
        self.assertEqual(self.hashes(), hashes)
        self.assertEqual(self.freshness()["reasons"], [])
        self.assertEqual(integrity.accepted_risk_status(self.conn, "harbour_bank", iid)["status"], "Current")
        self.assertIn(iid, self.open_ids())

    def test_recording_an_impact_even_no_material_impact_or_a_person_changes_no_finding(self):
        findings, hashes = self.findings(), self.hashes()
        iid = self.issue("C01", "approval")
        integrity.record_impact(self.conn, "harbour_bank", iid, "no_material_impact", "Priya", "Beta only")
        integrity.set_accountability(self.conn, "harbour_bank", iid, "Marcus Webb", "2026-11-15", "Priya")
        self.assertEqual(self.findings(), findings)
        self.assertEqual(self.hashes(), hashes)
        self.assertEqual(self.freshness()["state"], "Up to date")
        self.assertIn(iid, self.open_ids())

    def test_later_decisions_leave_an_earlier_handoff_as_it_was(self):
        self.save()
        saved = self.conn.execute("SELECT * FROM handoff_versions").fetchall()
        iid = self.issue("C01", "approval")
        integrity.record_accepted_risk(self.conn, "harbour_bank", iid, "Daniel Koh", "Accepted for the beta.")
        integrity.record_impact(self.conn, "harbour_bank", iid, "material", "Priya")
        self.assertEqual(self.save("not_ready")["version"], 2)
        self.assertEqual(self.conn.execute("SELECT * FROM handoff_versions WHERE version_no = 1").fetchall(), saved)

    def test_human_records_are_append_only_and_need_a_named_person(self):
        iid = self.issue("C01", "approval")
        rid = integrity.record_accepted_risk(self.conn, "harbour_bank", iid, "Daniel Koh", "Reason")
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("UPDATE accepted_risks SET rationale = 'x' WHERE id = ?", (rid,))
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("DELETE FROM accepted_risks WHERE id = ?", (rid,))
        with self.assertRaisesRegex(integrity.IntegrityError, "who accepts"):
            integrity.record_accepted_risk(self.conn, "harbour_bank", iid, "  ", "Reason")
        with self.assertRaisesRegex(integrity.IntegrityError, "accountable person"):
            integrity.set_accountability(self.conn, "harbour_bank", iid, "", None, "Priya")
        with self.assertRaisesRegex(integrity.IntegrityError, "not in this deal"):
            integrity.record_impact(self.conn, "harbour_bank", 999999, "material", "Priya")

    def test_a_new_contract_version_makes_earlier_records_need_re_confirmation_and_keeps_them_readable(self):
        iid = self.issue("C01", "approval")
        integrity.record_accepted_risk(self.conn, "harbour_bank", iid, "Daniel Koh", "Accepted for the beta.")
        integrity.record_impact(self.conn, "harbour_bank", iid, "no_material_impact", "Priya")
        note = (config.DATA_DIR / "harbour_bank" / "docs" / "HB-05_pricing_services_note.md").read_text(encoding="utf-8")
        ledger_fixes.add_source_version(self.conn, "harbour_bank", "HB-05", note + "\n", "HB-05_v2.md")
        for status in (integrity.accepted_risk_status(self.conn, "harbour_bank", iid), integrity.impact_status(self.conn, "harbour_bank", iid)):
            self.assertEqual((status["status"], status["reasons"]), ("Needs re-confirmation", [integrity.DOCUMENTS]))
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM accepted_risks").fetchone()[0], 1)

    def test_every_decision_path_declines_while_the_review_is_out_of_date(self):
        ledger_fixes.set_included(self.conn, "harbour_bank", "HB-04", False)
        iid = self.issue("C01", "approval")
        summary = integrity.decision_summary(self.conn, "harbour_bank")
        self.assertEqual((summary["current"], summary["message"], summary["items"]), (False, integrity.REVIEW_STALE, []))
        for call in (lambda: integrity.record_accepted_risk(self.conn, "harbour_bank", iid, "Daniel Koh", "x"),
                     lambda: integrity.record_impact(self.conn, "harbour_bank", iid, "material", "Priya"),
                     lambda: integrity.set_accountability(self.conn, "harbour_bank", iid, "Marcus", None, "Priya")):
            with self.assertRaisesRegex(integrity.IntegrityError, "rerun before a signing decision"):
                call()
        for table in ("accepted_risks", "impact_assessments", "accountability", "decision_bindings"):
            self.assertEqual(self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0], 0)

    def test_the_decision_summary_lists_open_issues_with_their_records_when_current(self):
        iid = self.issue("C01", "approval")
        integrity.record_accepted_risk(self.conn, "harbour_bank", iid, "Daniel Koh", "x")
        summary = integrity.decision_summary(self.conn, "harbour_bank")
        self.assertTrue(summary["current"])
        item = next(i for i in summary["items"] if i["issue_id"] == iid)
        self.assertEqual((item["accepted_risk"]["status"], item["impact"]["status"], item["accountability"]["status"]),
                         ("Current", "none", "none"))
        self.assertEqual(len(summary["items"]), len(self.open_ids()))


class TestOwnershipCarryForward(IntegrityCase):
    def person(self, iid):
        return integrity.accountability_status(self.conn, iid)

    def test_case_a_unchanged_terms_carry_forward(self):
        iid = self.issue("C01", "conflicting_terms")
        integrity.set_accountability(self.conn, "harbour_bank", iid, "Marcus Webb", "2026-11-15", "Priya")
        self.rerun()
        self.assertEqual(self.person(iid)["status"], "current")
        self.assertEqual(self.person(iid)["person"], "Marcus Webb")

    def test_case_b_changed_terms_in_the_conflict_ask_for_confirmation(self):
        iid = self.issue("C01", "conflicting_terms")
        integrity.set_accountability(self.conn, "harbour_bank", iid, "Marcus Webb", None, "Priya")
        quotes = list(SOW_QUOTES)
        quotes[4] = quotes[4].replace("at hourly intervals", "at 15-minute intervals")
        self.revise_sow(SOW.replace("at hourly intervals", "at 15-minute intervals"), quotes)
        self.assertEqual(self.issue("C01", "conflicting_terms"), iid)  # the same row, which is why this matters
        self.assertEqual(self.person(iid), {"status": "confirm", "message": integrity.CONFIRM_OWNER, "person": "Marcus Webb", "deadline": None})

    def test_confirming_by_a_named_person_makes_it_current_again(self):
        iid = self.issue("C01", "conflicting_terms")
        integrity.set_accountability(self.conn, "harbour_bank", iid, "Marcus Webb", None, "Priya")
        quotes = list(SOW_QUOTES)
        quotes[4] = quotes[4].replace("at hourly intervals", "at 15-minute intervals")
        self.revise_sow(SOW.replace("at hourly intervals", "at 15-minute intervals"), quotes)
        integrity.set_accountability(self.conn, "harbour_bank", iid, "Marcus Webb", None, "Priya", confirm=True)
        self.assertEqual(self.person(iid)["status"], "current")
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM accountability").fetchone()[0], 2)  # the first is preserved

    def test_case_d_an_issue_that_closed_and_reappeared_asks_for_confirmation(self):
        iid = self.issue("C01", "approval")
        integrity.set_accountability(self.conn, "harbour_bank", iid, "Marcus Webb", None, "Priya")
        path = config.scenario_path("HB-05_v2_named_exception.md")
        vid = ledger_fixes.add_source_version(self.conn, "harbour_bank", "HB-05", path.read_text(encoding="utf-8"), path.name)
        fid = ledger_fixes.create_fix(self.conn, "harbour_bank", "allowed_exception", "Product", "t", [iid], [(vid, "whole document", None)])
        ledger_fixes.approve_fix(self.conn, fid, "Tester")
        recheck.recheck(self.conn, "harbour_bank", fid, NoModel())
        self.assertEqual(recheck.status_by_name(self.conn, "harbour_bank")["On-chain wallet screening integration: Polygon, real time"][1]["approval/authorisation"], "Resolved")
        original = (config.DATA_DIR / "harbour_bank" / "docs" / "HB-05_pricing_services_note.md").read_text(encoding="utf-8")
        ledger_fixes.add_source_version(self.conn, "harbour_bank", "HB-05", original, "HB-05_v3.md")
        self.rerun()
        self.assertEqual(self.person(iid)["status"], "confirm")

    def test_cases_e_and_f_a_regrouped_commitment_asks_and_a_new_issue_has_no_owner(self):
        iid = self.issue("C01", "conflicting_terms")
        integrity.set_accountability(self.conn, "harbour_bank", iid, "Marcus Webb", None, "Priya")
        text, quotes = SOW, list(SOW_QUOTES)
        quotes[1] = "Provider will provide NUSD wallet screening for HarbourPay Global payouts on Ethereum and Polygon."
        quotes[4] = quotes[4].replace("at hourly intervals", "at 15-minute intervals")
        quotes[5] = quotes[5].replace("next", "following")
        text = text.replace(SOW_QUOTES[1], quotes[1]).replace(SOW_QUOTES[4], quotes[4]).replace(SOW_QUOTES[5], quotes[5])
        self.revise_sow(text, quotes)
        self.assertEqual(self.person(iid)["status"], "confirm")  # the old row now points at an unsupported commitment
        new_conflicts = self.conn.execute(
            "SELECT i.id FROM issues i JOIN commitments c ON c.id = i.commitment_id WHERE c.deal_id = ? AND i.issue_type = 'conflicting_terms' AND i.id <> ?",
            (self.did, iid)).fetchall()
        self.assertTrue(new_conflicts)
        for (nid,) in new_conflicts:
            self.assertEqual(self.person(nid), {"status": "none"})

    def test_carrying_ownership_forward_never_makes_an_accepted_risk_or_an_assessment_current(self):
        iid = self.issue("C01", "conflicting_terms")
        integrity.set_accountability(self.conn, "harbour_bank", iid, "Marcus Webb", None, "Priya")
        integrity.record_accepted_risk(self.conn, "harbour_bank", iid, "Daniel Koh", "x")
        integrity.record_impact(self.conn, "harbour_bank", iid, "no_material_impact", "Priya")
        quotes = list(SOW_QUOTES)
        quotes[4] = quotes[4].replace("at hourly intervals", "at 15-minute intervals")
        self.revise_sow(SOW.replace("at hourly intervals", "at 15-minute intervals"), quotes)
        integrity.set_accountability(self.conn, "harbour_bank", iid, "Marcus Webb", None, "Priya", confirm=True)
        self.assertEqual(self.person(iid)["status"], "current")
        self.assertEqual(integrity.accepted_risk_status(self.conn, "harbour_bank", iid)["status"], "Needs re-confirmation")
        self.assertEqual(integrity.impact_status(self.conn, "harbour_bank", iid)["status"], "Needs reassessment")


class TestImpactReassessment(IntegrityCase):
    def test_changing_an_issues_evidence_after_assessment_needs_reassessment_and_closes_nothing(self):
        iid = self.issue("C01", "conflicting_terms")
        rid = integrity.record_impact(self.conn, "harbour_bank", iid, "no_material_impact", "Priya", "Beta only")
        original = self.conn.execute("SELECT * FROM impact_assessments WHERE id = ?", (rid,)).fetchone()
        quotes = list(SOW_QUOTES)
        quotes[4] = quotes[4].replace("at hourly intervals", "at 15-minute intervals")
        self.revise_sow(SOW.replace("at hourly intervals", "at 15-minute intervals"), quotes)
        self.assertEqual(integrity.impact_status(self.conn, "harbour_bank", iid)["status"], "Needs reassessment")
        self.assertEqual(self.conn.execute("SELECT * FROM impact_assessments WHERE id = ?", (rid,)).fetchone(), original)
        self.assertIn(iid, self.open_ids())


if __name__ == "__main__":
    unittest.main()
