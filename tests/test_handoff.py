"""Handoff record: decision rules, owner confirmations, immutability, exports and key scrubbing.

Ledgers are built in temporary files from the development deals; workspace/ledger.sqlite is never touched. A scripted
fake stands in for the model. No label file is read and nothing under data/coral_pay/ is touched.
"""

import csv
import io
import json
import re
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
import evidence_text
import handoff
import ledger_fixes
import recheck
import scenarios
import workspace
from test_recheck import FakeExtractor, build_current

# Internal keys that must never reach a reader: commitment keys, statement keys, document keys, hashes, paths.
INTERNAL = re.compile(r"\bC\d{2,}\b|-S\d{2}\b|\b(?:HB|D)-\d{2}\b|sha256|\.sqlite|/Users/|state:|\.md\b|\.txt\b|CAP-\d+|\|"
                      r"|Still found by this recheck|this recheck|closure criteria")


class HandoffCase(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(config, "LEDGER_DEALS", ["harbour_bank", "hard_cases"])
        patcher.start()
        self.addCleanup(patcher.stop)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.conn = build_current(Path(tmp.name) / "ledger.sqlite")
        self.addCleanup(self.conn.close)

    def open_ids(self, deal="harbour_bank"):
        reg = workspace.register(self.conn, deal)
        return [i["id"] for c in reg["commitments"] for i in c["issues"] if i["state"] != "Resolved"]

    def save(self, decision="proceed", confirmed=None, deal="harbour_bank", reviewer="Lina"):
        ids = self.open_ids(deal) if confirmed is None else confirmed
        return handoff.save(self.conn, deal, decision, reviewer, "A note", ids)

    def clean_user_deal(self):
        deal = ledger_fixes.create_user_deal(self.conn, "Clean deal")
        text = "We might look at full case audit history later.\n"
        ledger_fixes.add_source(self.conn, deal, "Call", text, "c.md", "call_transcript", "2026-11-01")
        payload = {"statements": [{"quote": text.strip(), "speaker": "x", "language": "exploratory"}]}
        recheck.recheck(self.conn, deal, None, FakeExtractor(payload))
        return deal


class TestScrubbing(unittest.TestCase):
    def test_commitment_keys_statement_keys_and_document_keys_become_plain_text(self):
        names = {"HB-05": "Pricing note"}
        out = workspace.plain("Conflicting terms with C07 (On-chain screening: Polygon, batch): differs. HB-05 says no. See HB-01-S02.", names)
        self.assertEqual(out, "Conflicting terms with “On-chain screening: Polygon, batch”: differs. Pricing note says no. See.")
        self.assertEqual(workspace.plain("Same as C12 here"), "Same as another commitment here")
        self.assertEqual(workspace.plain(None), "")

    def test_ordinary_text_is_left_alone(self):
        text = "SOC 2 Type II, C-level sponsor, 12,000 payouts per day, clause A.1, CAP-021 beta"
        self.assertEqual(workspace.plain(text), text)


class TestPlainLanguage(unittest.TestCase):
    def test_system_phrasing_is_replaced_with_plain_words(self):
        self.assertEqual(workspace.plain("Still found by this recheck. Firm promise needs named approval."),
                         "Firm promise needs named approval.")
        self.assertEqual(workspace.plain("Closed: this recheck no longer finds the issue, and the evidence below meets its closure criteria."),
                         "Closed: the issue is no longer found, and the evidence meets what was needed.")
        self.assertNotIn("recheck", workspace.plain("Not raised by this recheck, but nothing yet shows its closure criteria are met; it stays open."))
        self.assertNotIn("closure criteria", workspace.plain("closure criteria not shown by any current evidence"))

    def test_statement_lists_in_inclusion_text_are_dropped_cleanly(self):
        out = workspace.plain("Included: HB-06-S02, HB-06-S05, HB-06-S06 in HB-06 (incorporated by HB-07 Clause 3).",
                              {"HB-06": "Draft SOW", "HB-07": "Draft contract"})
        self.assertEqual(out, "Included in Draft SOW (incorporated by Draft contract Clause 3).")


class TestEvidenceChoice(unittest.TestCase):
    S = [{"quote": "maybe", "language": "exploratory"}, {"quote": "if approved", "language": "conditional"},
         {"quote": "will, in RFP", "language": "firm"}, {"quote": "will, in proposal", "language": "firm"}]

    def test_trigger_statements_are_the_firm_ones_and_the_main_statement_is_the_strongest_latest_one(self):
        self.assertEqual([s["quote"] for s in handoff.trigger_statements(self.S)], ["will, in RFP", "will, in proposal"])
        self.assertEqual([s["quote"] for s in handoff.main_statement(self.S)], ["will, in proposal"])
        self.assertEqual([s["quote"] for s in handoff.main_statement(self.S[:2])], ["if approved"])
        self.assertEqual([s["quote"] for s in handoff.main_statement(self.S[:1])], ["maybe"])
        self.assertEqual(handoff.main_statement([]), [])
        self.assertEqual([s["quote"] for s in handoff.trigger_statements(self.S[:2])], ["if approved"])  # no firm: main one


POLYGON_APPROVAL = ("Catalogue: On-chain wallet screening integration on Polygon (NUSD, real-time) in Singapore is in beta, "
                    "needs named approval, general availability planned 31 March 2027. "
                    "Pricing note: no named exception approved for Harbour Bank.")


class TestApprovalText(unittest.TestCase):
    def text(self, auth, refs=None, terms_json=None, language="firm"):
        return evidence_text.approval_text(auth, language, refs or {}, terms_json)

    def test_pricing_note_rows_are_read_by_cell_not_pasted(self):
        row = "| CAP-021 On-chain wallet screening integration | Singapore, NUSD on Polygon | Beta | No named exception approved for Harbour Bank |"
        self.assertEqual(evidence_text.pricing_note_cell(row), "no named exception approved for Harbour Bank")
        self.assertEqual(evidence_text.pricing_note_cell("No named exceptions approved for Harbour Bank."),
                         "no named exceptions approved for Harbour Bank")
        self.assertEqual(evidence_text.pricing_note_cell("| x | SOW scope is fixed |"), "SOW scope is fixed")

    def test_each_authorisation_case_reads_as_plain_sentences(self):
        poly = {"catalogue": ["CAP-021/SG/Polygon/NUSD/real_time"],
                "source_versions": [{"role": "approval_evidence", "line": "| CAP-021 x | y | z | No named exception approved |"}]}
        self.assertEqual(self.text("no_approval_evidence", poly),
                         "Catalogue: On-chain wallet screening integration on Polygon (NUSD, real-time) in Singapore is in beta, "
                         "needs named approval, general availability planned 31 March 2027. Pricing note: no named exception approved.")
        approved = {"catalogue": poly["catalogue"], "approval": {"approver": "Daniel Koh (Product)", "conditions": ["subject to a 10,000 cap"]},
                    "source_versions": poly["source_versions"]}
        out = self.text("exception_approved", approved)
        self.assertIn("Pricing note: named exception approved by Daniel Koh (Product).", out)
        self.assertIn("Conditions: subject to a 10,000 cap. Each must be carried into the contract.", out)
        self.assertEqual(self.text("standard_authorised", {"catalogue": ["CAP-021/SG/Ethereum/NUSD/real_time"]}),
                         "Catalogue: On-chain wallet screening integration on Ethereum (NUSD, real-time) in Singapore is generally available and standard.")
        self.assertEqual(self.text(None, language="conditional"), "Approval isn't assessed for a conditional promise.")
        self.assertEqual(self.text("not_assessed"), "")
        self.assertIn("Catalogue: no entry for this promise.", self.text("unknown_needs_review", {"source_versions": [
            {"role": "approval_evidence_searched"}]}))
        self.assertIn("approval wording found, but no approver is named",
                      self.text("unknown_needs_review", {**poly, "source_versions": [{"role": "approval_evidence", "line": "approved"}]}))
        self.assertIn("No pricing and services note", self.text("unknown_needs_review", {"catalogue": poly["catalogue"]}))
        self.assertIn("names no approval for this scope", self.text("no_approval_evidence", {**poly, "source_versions": [
            {"role": "approval_evidence", "line": None}]}))

    def test_a_limit_the_promise_exceeds_is_stated_per_region(self):
        ts = {"capability": "CAP-023", "quantity": {"value": 40000, "unit": "payouts", "period": "day", "bound": "max"}}
        out = self.text("no_approval_evidence", {"catalogue": ["CAP-023/AU", "CAP-023/SG"], "source_versions": []},
                        {"members": [{"term_set": ts}]})
        self.assertIn("Payout ledger connector in Australia: 40,000 payouts per day is above the standard limit of 20,000.", out)
        self.assertIn("Payout ledger connector in Singapore: 40,000 payouts per day is above the standard limit of 25,000.", out)
        self.assertIn("each listed option was checked", out)


class TestProgressionAndContractLine(unittest.TestCase):
    def st(self, language, label, date):
        return {"language": language, "doc_type_label": label, "date": date}

    def test_progression_line(self):
        s = [self.st("exploratory", "Call transcript", "2026-09-28"), self.st("conditional", "Call transcript", "2026-10-02"),
             self.st("firm", "RFP response", "2026-10-06")]
        self.assertEqual(workspace.progression(s), "Started as exploratory (Call transcript, 28 Sep) \u2192 conditional "
                                                   "(Call transcript, 2 Oct) \u2192 firm (RFP response, 6 Oct)")
        self.assertEqual(workspace.progression(s[:1]), "")
        self.assertEqual(workspace.progression([]), "")
        twice = [self.st("firm", "Draft SOW", "2026-10-20")] * 3
        self.assertEqual(workspace.progression(twice), "Stated as firm throughout (Draft SOW, 20 Oct)")
        cross = [self.st("firm", "Proposal", "2026-12-30"), self.st("firm", "Draft SOW", "2027-01-05")]
        self.assertIn("30 Dec 2026", workspace.progression(cross))

    def test_short_date(self):
        self.assertEqual(workspace.short_date("2026-09-28"), "28 Sep 2026")
        self.assertEqual(workspace.short_date("2026-10-02", year=False), "2 Oct")
        self.assertEqual((workspace.short_date(""), workspace.short_date("n/a")), ("", "n/a"))


class TestDecisionRules(HandoffCase):
    def test_ready_is_refused_while_any_issue_is_open_and_allowed_when_none_are(self):
        with self.assertRaisesRegex(handoff.HandoffError, "can't be ready"):
            self.save("ready", confirmed=[])
        deal = self.clean_user_deal()
        self.assertEqual(self.save("ready", deal=deal, confirmed=[])["version"], 1)

    def test_proceed_is_refused_if_any_open_issue_is_unconfirmed(self):
        ids = self.open_ids()
        self.assertGreater(len(ids), 1)
        for confirmed in ([], ids[:-1], ids[1:]):
            with self.assertRaisesRegex(handoff.HandoffError, "Confirm the owner of every open issue"):
                self.save("proceed", confirmed=confirmed)
        self.assertEqual(self.save("proceed", confirmed=ids)["version"], 1)

    def test_not_ready_needs_no_confirmation_and_unconfirmed_owners_show_as_default(self):
        self.save("not_ready", confirmed=[])
        issues = handoff.get_version(self.conn, "harbour_bank")["handoff"]["issues"]
        self.assertTrue(all(i["owner_basis"] == "default" for i in issues))

    def test_confirmed_owners_are_labelled_with_the_reviewer_in_the_snapshot_and_every_export(self):
        ids = self.open_ids()
        self.save("not_ready", confirmed=ids[:2], reviewer="Dana")
        found = handoff.get_version(self.conn, "harbour_bank")
        issues = found["handoff"]["issues"]
        self.assertEqual(sum(i["owner_basis"] == "confirmed by Dana" for i in issues), 2)
        self.assertTrue(any(i["owner_basis"] == "default" for i in issues))
        self.assertIn("(confirmed by Dana)", handoff.render_csv(found["handoff"]))
        self.assertIn("(default)", handoff.render_csv(found["handoff"]))
        page = handoff.render_html(found["handoff"], 1)
        self.assertIn("(confirmed by Dana)", page)
        self.assertIn("(default)", page)

    def test_confirmations_must_belong_to_the_deal_and_a_reviewer_is_required(self):
        with self.assertRaisesRegex(handoff.HandoffError, "does not match an issue"):
            self.save("not_ready", confirmed=[999999])
        with self.assertRaisesRegex(handoff.HandoffError, "reviewer"):
            self.save("not_ready", confirmed=[], reviewer="  ")
        with self.assertRaisesRegex(handoff.HandoffError, "Choose a decision"):
            self.save("maybe", confirmed=[])

    def test_the_decision_and_confirmations_change_no_issue_and_no_register_state(self):
        before_issues = self.conn.execute("SELECT * FROM issues ORDER BY id").fetchall()
        before_checks = self.conn.execute("SELECT * FROM closure_checks ORDER BY id").fetchall()
        before_reg = json.dumps(workspace.register(self.conn, "harbour_bank"), sort_keys=True)
        self.save("proceed")
        self.assertEqual(self.conn.execute("SELECT * FROM issues ORDER BY id").fetchall(), before_issues)
        self.assertEqual(self.conn.execute("SELECT * FROM closure_checks ORDER BY id").fetchall(), before_checks)
        self.assertEqual(json.dumps(workspace.register(self.conn, "harbour_bank"), sort_keys=True), before_reg)


class TestFreshnessGate(HandoffCase):
    def test_save_is_refused_when_the_review_is_out_of_date(self):
        ledger_fixes.set_included(self.conn, "harbour_bank", "HB-04", False)
        with self.assertRaises(handoff.HandoffError) as caught:
            self.save("not_ready", confirmed=[])
        self.assertEqual(str(caught.exception), "Rerun the review before saving the handoff")
        self.assertEqual(caught.exception.status, 409)
        self.assertEqual(handoff.list_versions(self.conn, "harbour_bank"), [])

    def test_save_is_refused_when_the_deal_has_not_been_reviewed(self):
        deal = ledger_fixes.create_user_deal(self.conn, "Fresh")
        with self.assertRaisesRegex(handoff.HandoffError, "Run the review"):
            handoff.save(self.conn, deal, "not_ready", "Lina", "", [])

    def test_a_stale_review_id_is_refused(self):
        with self.assertRaisesRegex(handoff.HandoffError, "review has changed"):
            handoff.save(self.conn, "harbour_bank", "not_ready", "Lina", "", [], review_id=987654)


class TestImmutability(HandoffCase):
    def test_a_saved_version_cannot_be_updated_or_deleted_and_a_new_save_is_a_new_version(self):
        self.save("not_ready", confirmed=[])
        first = self.conn.execute("SELECT snapshot_json FROM handoff_versions WHERE version_no = 1").fetchone()[0]
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("UPDATE handoff_versions SET decision = 'ready' WHERE version_no = 1")
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("UPDATE handoff_versions SET snapshot_json = '{}' WHERE version_no = 1")
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("DELETE FROM handoff_versions WHERE version_no = 1")
        self.assertEqual(self.save("proceed")["version"], 2)
        self.assertEqual(self.conn.execute("SELECT snapshot_json FROM handoff_versions WHERE version_no = 1").fetchone()[0], first)
        self.assertEqual([v["version"] for v in handoff.list_versions(self.conn, "harbour_bank")], [2, 1])

    def test_the_view_flags_changes_after_saving_but_the_saved_content_stays(self):
        self.save("proceed")
        saved = json.dumps(handoff.get_version(self.conn, "harbour_bank")["handoff"], sort_keys=True)
        self.assertFalse(handoff.get_version(self.conn, "harbour_bank")["changed_since_saved"])
        ledger_fixes.set_included(self.conn, "harbour_bank", "HB-04", False)
        after = handoff.get_version(self.conn, "harbour_bank")
        self.assertTrue(after["changed_since_saved"])
        self.assertEqual(json.dumps(after["handoff"], sort_keys=True), saved)

    def test_ensure_schema_is_idempotent_and_leaves_the_ledger_version_alone(self):
        handoff.ensure_schema(self.conn)
        handoff.ensure_schema(self.conn)
        self.assertEqual(self.conn.execute("SELECT value FROM schema_meta WHERE key = 'schema_version'").fetchone()[0], "1")


class TestExports(HandoffCase):
    def snapshot(self):
        self.save("proceed")
        return handoff.get_version(self.conn, "harbour_bank")["handoff"]

    def test_csv_has_one_row_per_issue_plus_one_per_clean_commitment_with_open_items_first(self):
        snap = self.snapshot()
        reg = workspace.register(self.conn, "harbour_bank")
        rows = list(csv.reader(io.StringIO(handoff.render_csv(snap).lstrip("﻿"))))
        self.assertEqual(rows[0], ["Commitment", "What needs attention", "Status", "Owner", "Note", "Evidence quote",
                                   "Source document", "Source version"])
        body = rows[1:]
        n_issues = sum(len(c["issues"]) for c in reg["commitments"])
        clean = [c for c in reg["commitments"] if not c["issues"]]
        self.assertEqual((n_issues, len(clean)), (8, 4))
        self.assertEqual(len(body), n_issues + len(clean))
        statuses = [r[2] for r in body]
        open_n = sum(s in ("Needs action", "Needs evidence") for s in statuses)
        self.assertEqual(open_n, 8)
        self.assertTrue(all(s in ("Needs action", "Needs evidence") for s in statuses[:open_n]))
        for c in clean:
            row = next(r for r in body if r[0] == c["name"])
            self.assertEqual((row[1], row[3], row[2]), ("", "", c["status"]))
            self.assertTrue(row[5] and row[6] and row[7])  # quote, source and version are still shown
        polygon = [r for r in body[:open_n] if "Polygon, real time" in r[0]]
        self.assertTrue(any(r[1].startswith("Missing from the contract") for r in polygon))
        self.assertTrue(any(r[1].startswith("Contract says something different") for r in polygon))

    def test_an_issue_shows_only_the_statements_that_triggered_it(self):
        snap = self.snapshot()
        reg = workspace.register(self.conn, "harbour_bank")
        polygon = next(c for c in reg["commitments"] if "Polygon, real time" in c["name"])
        firm = [s["quote"] for s in polygon["statements"] if s["language"] == "firm"]
        self.assertLess(len(firm), len(polygon["statements"]))  # the commitment has softer statements too
        rows = [i for i in snap["issues"] if i["commitment"] == polygon["name"]]
        self.assertEqual(len(rows), 3)
        for i in rows:
            self.assertEqual([e["quote"] for e in i["evidence"]], firm)
        csv_text = handoff.render_csv(snap)
        self.assertNotIn("We're exploring whether", csv_text)  # the exploratory call statement
        self.assertNotIn("If Product grants named approval", csv_text)  # the conditional one
        self.assertIn(firm[0], csv_text)
        self.assertNotIn("We're exploring whether", handoff.render_html(snap, 1))

    def test_clean_commitments_show_one_main_statement(self):
        snap = self.snapshot()
        clean = [c for c in snap["commitments"] if c["issue_count"] == 0]
        self.assertEqual(len(clean), 4)  # three firm, one conditional ("Not checked")
        reg = {c["name"]: c for c in workspace.register(self.conn, "harbour_bank")["commitments"]}
        for c in clean:
            self.assertEqual(len(c["evidence"]), 1)
            self.assertEqual(c["evidence"][0]["quote"], handoff.main_statement(reg[c["promise"]]["statements"])[0]["quote"])
        rows = list(csv.reader(io.StringIO(handoff.render_csv(snap).lstrip("\ufeff"))))
        for r in rows[1:]:
            if r[1] == "":
                self.assertNotIn("\n", r[5])
                self.assertNotIn("\n", r[6])

    def test_documents_are_named_by_type_never_by_file_name_or_key(self):
        snap = self.snapshot()
        docs = workspace.documents(self.conn, "harbour_bank")
        self.assertEqual(sorted(d["name"] for d in docs), sorted([
            "Call transcript of 28 Sep 2026", "Call transcript of 2 Oct 2026", "RFP response", "Proposal",
            "Pricing and services note", "Draft SOW", "Draft contract", "Customer email"]))
        self.assertTrue(all("filename" not in d for d in docs))
        self.assertEqual(sorted(s["document"] for s in snap["sources"]), sorted(d["name"] for d in docs))
        rows = list(csv.reader(io.StringIO(handoff.render_csv(snap).lstrip("\ufeff"))))
        names = {d["name"] for d in docs}
        for r in rows[1:]:
            self.assertTrue(set(r[6].split("\n")) <= names, r[6])
            self.assertTrue(all(v.isdigit() for v in r[7].split("\n")), r[7])
        page = handoff.render_html(snap, 1)
        self.assertRegex(page, r"(Proposal|RFP response), version 1")
        self.assertNotIn("Pricing note HB", page)

    def test_two_documents_of_one_type_on_the_same_day_are_told_apart(self):
        deal = ledger_fixes.create_user_deal(self.conn, "Twin docs")
        for _ in range(2):
            ledger_fixes.add_source(self.conn, deal, "x", "A promise.\n", "same.md", "proposal", "2026-11-01")
        self.assertEqual(sorted(workspace.document_labels(self.conn, ledger_fixes.deal_id(self.conn, deal)).values()),
                         ["Proposal of 1 Nov 2026 (1)", "Proposal of 1 Nov 2026 (2)"])

    def test_approval_evidence_is_plain_sentences_on_screen_and_in_both_exports(self):
        snap = self.snapshot()
        reg = workspace.register(self.conn, "harbour_bank")
        polygon = next(c for c in reg["commitments"] if "Polygon, real time" in c["name"])
        self.assertEqual(polygon["authorisation_evidence"], POLYGON_APPROVAL)
        approval = next(i for i in polygon["issues"] if i["type"] == "approval")
        self.assertEqual(approval["reason"], "Firm promise needs named approval, and none is recorded. " + POLYGON_APPROVAL)
        csv_text, page = handoff.render_csv(snap), handoff.render_html(snap, 1)
        self.assertIn(POLYGON_APPROVAL, csv_text)
        self.assertIn(POLYGON_APPROVAL.replace("'", "&#x27;"), page)
        for text in (csv_text, page, json.dumps(reg)):
            self.assertNotIn("CAP-", text)
            self.assertNotIn("requires named approval", text)
            self.assertNotIn("planned GA", text)

    def test_the_contract_line_names_the_conflicting_term_and_the_gap_reason_has_no_duplicated_type(self):
        snap = self.snapshot()
        reg = {c["name"]: c for c in workspace.register(self.conn, "harbour_bank")["commitments"]}
        polygon = next(c for n, c in reg.items() if "Polygon, real time" in n)
        self.assertEqual(polygon["presence"], "Not in the contract: the contract says batch instead.")
        other = next(c for n, c in reg.items() if n.startswith("VASP"))
        self.assertEqual(other["presence"], "Not in the contract")  # no conflict: the plain label stays
        self.assertEqual(next(c for c in snap["commitments"] if "Polygon, real time" in c["promise"])["contract"],
                         "The contract says batch instead")
        gaps = [i for c in reg.values() for i in c["issues"] if i["type"] == "contract_gap"]
        self.assertEqual(len(gaps), 3)
        for i in gaps:
            self.assertEqual(i["reason"], "Not in the draft contract or the SOW it incorporates (clause 3).")
        self.assertNotIn("(draft contract)", json.dumps(reg))
        self.assertEqual(polygon["presence_detail"], "Not in the draft contract or the SOW it incorporates (clause 3).")

    def test_the_commitment_card_data_carries_a_progression_only_when_there_is_more_than_one_statement(self):
        reg = {c["name"]: c for c in workspace.register(self.conn, "harbour_bank")["commitments"]}
        polygon = next(c for n, c in reg.items() if "Polygon, real time" in n)
        self.assertEqual(polygon["progression"], "Started as exploratory (Call transcript, 28 Sep) \u2192 conditional "
                                                 "(Call transcript, 2 Oct) \u2192 firm (RFP response, 6 Oct; Proposal, 10 Oct)")
        for c in reg.values():
            self.assertEqual(bool(c["progression"]), len(c["statements"]) > 1, c["name"])

    def test_the_in_the_contract_column_is_one_clean_phrase_per_row(self):
        snap = self.snapshot()
        phrases = {c["promise"]: c["contract"] for c in snap["commitments"]}
        self.assertEqual(phrases["On-chain wallet screening integration: Polygon, real time"],
                         "The contract says batch instead")
        self.assertEqual(phrases["VASP counterparty data exchange"],
                         "Not in the draft contract or the SOW it incorporates (clause 3)")
        included = [p for n, p in phrases.items() if p.startswith("In ")]
        self.assertEqual(len(included), 4)
        self.assertTrue(all(p == "In the SOW the contract incorporates (clause 3)" for p in included), included)
        for phrase in phrases.values():
            self.assertNotIn(".:", phrase)
            self.assertFalse(phrase.endswith("."), phrase)
            self.assertNotRegex(phrase, r"(?i)(.{12,}).*\1")  # nothing said twice inside one phrase
            self.assertNotIn("Included", phrase)
        self.assertNotIn("contract_detail", json.dumps(snap))
        self.assertEqual(handoff.contract_phrase("Not assessed", "Not assessed: no draft contract among the selected sources."),
                         "Not assessed: no draft contract among the selected sources")
        self.assertEqual(handoff.contract_phrase("In the draft contract", ""), "In the draft contract")

    def test_reviewed_sources_drop_the_type_column_and_the_summary_states_what_resolved_means_once(self):
        page = handoff.render_html(self.snapshot(), 1)
        sources = page[page.index("Reviewed sources"):]
        self.assertNotIn("<th>Type</th>", sources)
        self.assertIn("<th>Document</th><th>Version</th><th>Date</th><th>Used</th>", sources)
        self.assertEqual(page.count("Resolved means"), 1)

    def test_promises_that_are_not_firm_say_not_checked_instead_of_no_issues_raised(self):
        reg = workspace.register(self.conn, "harbour_bank")
        by = {c["name"]: c for c in reg["commitments"]}
        golive = by["Go-live"]
        self.assertEqual((golive["language"], golive["status"]), ("conditional", "Not checked: conditional promise"))
        self.assertEqual(golive["check_note"], "Only firm promises are checked against approval and the contract.")
        firm_clean = [c for c in reg["commitments"] if c["language"] == "firm" and not c["issues"]]
        self.assertEqual(len(firm_clean), 3)
        self.assertTrue(all(c["status"] == "No issues raised" and c["check_note"] == "" for c in firm_clean))
        self.assertEqual(reg["counts"].get("No issues raised"), 3)
        self.assertEqual(reg["counts"].get("Not checked: conditional promise"), 1)
        snap = self.snapshot()
        row = next(c for c in snap["commitments"] if c["promise"] == "Go-live")
        self.assertEqual((row["status"], row["check_note"]), ("Not checked: conditional promise", workspace.CHECK_NOTE))
        csv_rows = list(csv.reader(io.StringIO(handoff.render_csv(snap).lstrip("\ufeff"))))
        golive_row = next(r for r in csv_rows if r[0] == "Go-live")
        self.assertEqual((golive_row[2], golive_row[4]), ("Not checked: conditional promise", workspace.CHECK_NOTE))
        clean_firm_row = next(r for r in csv_rows if r[2] == "No issues raised")
        self.assertEqual(clean_firm_row[4], "")
        page = handoff.render_html(snap, 1)
        self.assertIn("Not checked: conditional promise", page)
        self.assertIn(workspace.CHECK_NOTE, page)
        self.assertNotIn(workspace.CHECK_NOTE, handoff.render_html({**snap, "commitments": [
            c for c in snap["commitments"] if not c["check_note"]]}, 1))  # no footnote when nothing was skipped

    def test_display_status_names_the_language(self):
        self.assertEqual(workspace.display_status("No issues raised", "exploratory"), "Not checked: exploratory promise")
        self.assertEqual(workspace.display_status("No issues raised", "conditional"), "Not checked: conditional promise")
        self.assertEqual(workspace.display_status("No issues raised", "firm"), "No issues raised")
        self.assertEqual(workspace.display_status("Needs action", "firm"), "Needs action")
        self.assertEqual(workspace.display_status("Not in current documents", "conditional"), "Not in current documents")

    def test_dates_in_the_summary_read_as_28_sep_2026_not_iso(self):
        page = handoff.render_html(self.snapshot(), 1)
        self.assertRegex(page, r"\b\d{1,2} [A-Z][a-z]{2} 20\d\d\b")
        self.assertNotRegex(page, r"\b20\d\d-\d{2}-\d{2}\b")
        self.assertIn("28 Sep 2026", page)

    def test_no_internal_keys_ids_hashes_or_paths_reach_any_screen_or_export(self):
        snap = self.snapshot()
        found = handoff.get_version(self.conn, "harbour_bank")
        reg = workspace.register(self.conn, "harbour_bank")
        for name, text in {"snapshot": json.dumps(found), "csv": handoff.render_csv(snap), "html": handoff.render_html(snap, 1),
                           "register": json.dumps(reg)}.items():
            self.assertEqual(INTERNAL.findall(text), [], name)
        self.assertNotIn('"key"', json.dumps(reg))
        self.assertNotIn('"subject"', json.dumps(reg))

    def test_summary_lists_open_items_before_all_commitments_and_escapes_everything(self):
        snap = self.snapshot()
        snap["deal"] = "<script>alert(1)</script>"
        snap["issues"][0]["note"] = '"><img src=x onerror=alert(1)>'
        page = handoff.render_html(snap, 1)
        self.assertNotIn("<script>", page)
        self.assertNotIn("<img", page)
        self.assertLess(page.index("Open items"), page.index("All commitments"))
        for heading in ("Approved exceptions", "Fix and decision history", "Reviewed sources"):
            self.assertIn(heading, page)
        self.assertIn("Demonstrated on fictional deals with a complete capability catalogue.", page)

    def test_csv_cells_that_look_like_formulas_are_neutralised(self):
        snap = self.snapshot()
        snap["issues"][0]["note"] = "=HYPERLINK(\"http://x\")"
        snap["issues"][0]["commitment"] = "@cmd"
        rows = list(csv.reader(io.StringIO(handoff.render_csv(snap).lstrip("﻿"))))
        self.assertEqual(rows[1][0], "'@cmd")
        self.assertEqual(rows[1][4], "'=HYPERLINK(\"http://x\")")

    def test_export_filename_carries_no_path(self):
        self.assertEqual(handoff.export_filename({"deal": "../../etc/Harbour Bank"}, 3, "csv"), "handoff-etc-Harbour-Bank-v3.csv")


if __name__ == "__main__":
    unittest.main()
