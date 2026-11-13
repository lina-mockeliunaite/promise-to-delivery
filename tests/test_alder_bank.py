"""Alder Bank demo deal (16 Oct): the documents support every intended finding in data/alder_bank/BRIEF.md, and the
two fix documents close exactly what they should. Deterministic: hand-written findings through the frozen v2 verifier,
no model call. This checks the scenario is built right; whether the model finds the gaps is the separate demo run.
"""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config
import real_readings
import detect_v2
import run_v2
import sealed_run

SCEN = config.DATA_DIR / "scenarios"
PROMISE = ("AB-03", "Scam-call alerts warn the bank when a customer seems to be on a call with a scammer while making a payment, live from the 1 February 2027 launch.")
AZ = ("AB-03", "Elva will host Alder's dedicated environment on Microsoft Azure in the Australia East region.")


def finding(kind, quotes, **kw):
    base = dict(kind=kind, commitment="c", promise_quotes=[{"source_id": s, "quote": q} for s, q in quotes],
                catalogue_path=None, unlisted_value=None, limit_name=None, promised_quantity=None, missing_phrases=[],
                contract_quote=None, note_quote=None, subject=None, promised_value=None, contract_value=None, reason="r")
    base.update(kw)
    return base


# 13 Nov (Round 5): Alder is a two-row story: scam-call alerts (an approval and a contract gap) and Azure hosting (not offered, and conflicting). Nothing about volume or scoring thresholds.
APPROVAL = finding("approval_required", [PROMISE], catalogue_path="CAP-027/AU")
SCAM_GAP = finding("contract_gap", [PROMISE], missing_phrases=["scam-call alerts", "on a call with a scammer"])
AZURE = finding("absolute_limit", [AZ], catalogue_path="CAP-019/AU", unlisted_value="Microsoft Azure")
HOSTING = finding("conflicting_terms", [AZ], subject="dedicated environment", promised_value="Microsoft Azure",
                  contract_value="Amazon Web Services",
                  contract_quote={"source_id": "AB-06", "quote": "Provider will host the Customer's dedicated environment "
                                  "on Amazon Web Services in the Sydney region."})


class TestAlderScenario(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cat = json.loads((config.DATA_DIR / "catalogue_alder.json").read_text(encoding="utf-8"))  # Alder's own copy of Elva's catalogue
        cls.docs = detect_v2.deal_documents("alder_bank")

    def swap(self, docs, sid, name):
        return [dict(d, text=(SCEN / name).read_text(encoding="utf-8")) if d["source_id"] == sid else d for d in docs]

    def test_every_intended_finding_verifies_on_the_original_documents(self):
        for name, f in [("approval", APPROVAL), ("scam-call alerts contract gap", SCAM_GAP), ("Azure not offered", AZURE), ("hosting conflict", HOSTING)]:
            self.assertEqual(detect_v2.verify(f, self.docs, self.cat), [], name)

    def test_nothing_about_volume_or_scoring_thresholds_can_be_found(self):
        text = " ".join(d["text"] for d in self.docs)
        self.assertNotIn("750,000", text)
        self.assertNotIn("AUD 1,000", text)
        vol = finding("over_limit", [("AB-04", "Real-time scoring will handle up to 750,000 payments per day by the end of the first year.")], catalogue_path="CAP-003/AU",
                      limit_name="max_transactions_per_day", promised_quantity=750000)
        self.assertEqual(detect_v2.verify(vol, self.docs, self.cat), ["quote not verbatim in AB-04"])  # the promise is not in the documents

    def test_the_named_exception_closes_only_the_approval(self):
        after = self.swap(self.docs, "AB-05", "AB-05_v2_named_exception.md")
        self.assertNotEqual(detect_v2.verify(APPROVAL, after, self.cat), [])
        for f in (SCAM_GAP, AZURE, HOSTING):
            self.assertEqual(detect_v2.verify(f, after, self.cat), [])

    def test_the_revised_statement_of_work_closes_the_scam_call_contract_gap_and_nothing_else(self):
        after = self.swap(self.swap(self.docs, "AB-05", "AB-05_v2_named_exception.md"), "AB-06", "AB-06_v2_coaching_added.md")
        self.assertNotEqual(detect_v2.verify(SCAM_GAP, after, self.cat), [])
        for f in (AZURE, HOSTING):  # what is left for the note
            self.assertEqual(detect_v2.verify(f, after, self.cat), [])

    def test_the_demo_run_refuses_any_other_deal(self):
        with self.assertRaises(sealed_run.Refused):
            run_v2.demo(object(), "harbour_bank")

    def test_the_shared_catalogue_is_untouched_so_existing_demo_deals_keep_their_saved_output(self):
        shared = json.loads((config.DATA_DIR / "catalogue.json").read_text(encoding="utf-8"))
        self.assertEqual(shared["as_of"], "2026-09-30")
        self.assertEqual(len(shared["capabilities"]), 25)
        self.assertEqual((self.cat["as_of"], len(self.cat["capabilities"])), ("2026-09-30", 25))  # Alder's copy has the same capabilities


class TestAlderClosureReason(unittest.TestCase):
    """In the app: adding the approval note closes the coaching approval, says why in plain words, and credits only the
    pricing note (16 Oct: the first wording blamed a vanished quote and listed five documents)."""

    def test_the_named_exception_closes_the_approval_with_the_approver_as_the_reason(self):
        import tempfile
        from unittest import mock
        import ledger
        import ledger_fixes
        import ledger_v2
        import reset_demo
        import workspace
        with tempfile.TemporaryDirectory() as tmp, real_readings.patch_cache(Path(tmp) / "cache"):
            reset_demo.build(Path(tmp) / "l.sqlite")
            conn = ledger.connect(Path(tmp) / "l.sqlite")
            try:
                ledger_fixes.add_source_version(conn, "alder_bank", "AB-05", (SCEN / "AB-05_v2_named_exception.md").read_text(),
                                                "AB-05_v2_named_exception.md")
                self.assertEqual(ledger_v2.review(conn, "alder_bank")["model_calls"], 0)
                # The engine is unchanged: the ledger records the closure and says why, crediting the approver (Round 5 added a read-time layer, approval_scope.py).
                did = ledger_fixes.deal_id(conn, "alder_bank")
                ledger_closed = conn.execute("SELECT c.name, k.reason FROM issues i JOIN issue_current_state s ON s.issue_id = i.id JOIN commitments m ON m.id = i.commitment_id"
                                             " JOIN commitment_assessments c ON c.commitment_id = m.id JOIN closure_checks k ON k.issue_id = i.id"
                                             " WHERE m.deal_id = ? AND s.state = 'Resolved' AND k.id = (SELECT MAX(id) FROM closure_checks WHERE issue_id = i.id)"
                                             " GROUP BY i.id", (did,)).fetchall()
                self.assertEqual(len(ledger_closed), 1)
                self.assertIn("Scam-call alerts", ledger_closed[0][0])
                self.assertIn("named approver", ledger_closed[0][1])
                self.assertIn("Arjun Rao", ledger_closed[0][1])
                # The screens: the approval now says it starts 1 May 2027, after the promised 1 February, so the gap stays open (Round 5).
                reg = workspace.overview(conn, "alder_bank")
                self.assertEqual([i for c in reg["commitments"] for i in c["issues"] if i["state"] == "Resolved"], [])
                coaching = next(c for c in reg["commitments"] if "Scam-call alerts" in c["name"])
                issue = next(i for i in coaching["issues"] if i["type"] == "approval")
                self.assertEqual((issue["finding"], issue["state"]), ("Approval starts later", "Needs action"))
                self.assertEqual(issue["reason"], "The promised start date is earlier than the approved start date.")
                credited = workspace.resolved_by(conn, did, issue["id"], workspace.document_labels(conn, did))  # the ledger's own record of what closed it
                self.assertEqual(credited["text"].split(" · ")[0], "Resolved by Internal approvals note, version 2")
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()
