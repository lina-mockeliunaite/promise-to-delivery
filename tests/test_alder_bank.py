"""Alder Bank demo deal (16 Oct): the documents support every intended finding in data/alder_bank/BRIEF.md, and the
two fix documents close exactly what they should. Deterministic: hand-written findings through the frozen v2 verifier,
no model call. This checks the scenario is built right; whether the model finds the gaps is the separate demo run.
"""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
import detect_v2
import run_v2
import sealed_run

SCEN = config.DATA_DIR / "scenarios"
BIO = ("AB-03", "Through its connector to BioCatch, Elva will use behavioural signals from Alder's mobile and internet "
                "banking to flag customers who appear to be coached by a scammer, live from the 1 February 2027 launch.")
RT = ("AB-04", "All outbound instant payments will be scored in real time before they are released, from the 1 February 2027 launch.")
VOL = ("AB-04", "Real-time scoring will handle up to 750,000 payments per day by the end of the first year.")
AZ = ("AB-03", "Elva will host Alder's dedicated environment on Microsoft Azure in the Australia East region.")


def finding(kind, quotes, **kw):
    base = dict(kind=kind, commitment="c", promise_quotes=[{"source_id": s, "quote": q} for s, q in quotes],
                catalogue_path=None, unlisted_value=None, limit_name=None, promised_quantity=None, missing_phrases=[],
                contract_quote=None, note_quote=None, subject=None, promised_value=None, contract_value=None, reason="r")
    base.update(kw)
    return base


APPROVAL = finding("approval_required", [BIO], catalogue_path="CAP-027/AU")
REALTIME = finding("conflicting_terms", [RT], subject="outbound instant payments", promised_value="real time",
                   contract_value="batches at hourly intervals",
                   contract_quote={"source_id": "AB-06", "quote": "A.2 Outbound instant payments below AUD 1,000 are "
                                   "scored in batches at hourly intervals after release."})
OVER = finding("over_limit", [VOL], catalogue_path="CAP-003/AU", limit_name="max_transactions_per_day", promised_quantity=750000)
VOL_GAP = finding("contract_gap", [VOL], missing_phrases=["750,000 payments per day", "end of the first year"])
BIO_GAP = finding("contract_gap", [BIO], missing_phrases=["BioCatch", "coached by a scammer"])
AZURE = finding("absolute_limit", [AZ], catalogue_path="CAP-019/AU", unlisted_value="Microsoft Azure")
HOSTING = finding("conflicting_terms", [AZ], subject="dedicated environment", promised_value="Microsoft Azure",
                  contract_value="Amazon Web Services",
                  contract_quote={"source_id": "AB-06", "quote": "Provider will host the Customer's dedicated environment "
                                  "on Amazon Web Services in the Sydney region."})


class TestAlderScenario(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cat = json.loads((config.DATA_DIR / "catalogue.json").read_text(encoding="utf-8"))
        cls.docs = detect_v2.deal_documents("alder_bank")

    def swap(self, docs, sid, name):
        return [dict(d, text=(SCEN / name).read_text(encoding="utf-8")) if d["source_id"] == sid else d for d in docs]

    def test_every_intended_finding_verifies_on_the_original_documents(self):
        for name, f in [("approval", APPROVAL), ("coaching contract gap", BIO_GAP), ("real-time conflict", REALTIME), ("over limit", OVER),
                        ("volume gap", VOL_GAP), ("Azure not offered", AZURE), ("hosting conflict", HOSTING)]:
            self.assertEqual(detect_v2.verify(f, self.docs, self.cat), [], name)

    def test_the_named_exception_closes_only_the_approval(self):
        after = self.swap(self.docs, "AB-05", "AB-05_v2_named_exception.md")
        self.assertNotEqual(detect_v2.verify(APPROVAL, after, self.cat), [])
        for f in (BIO_GAP, REALTIME, OVER, VOL_GAP, AZURE, HOSTING):
            self.assertEqual(detect_v2.verify(f, after, self.cat), [])

    def test_the_coaching_sow_closes_the_coaching_contract_gap_and_nothing_else(self):
        after = self.swap(self.swap(self.docs, "AB-05", "AB-05_v2_named_exception.md"), "AB-06", "AB-06_v2_coaching_added.md")
        self.assertNotEqual(detect_v2.verify(BIO_GAP, after, self.cat), [])
        for f in (OVER, VOL_GAP, AZURE, HOSTING):  # what Delivery inherits
            self.assertEqual(detect_v2.verify(f, after, self.cat), [])

    def test_the_demo_run_refuses_any_other_deal(self):
        with self.assertRaises(sealed_run.Refused):
            run_v2.demo(object(), "harbour_bank")

    def test_the_shared_catalogue_is_untouched_so_existing_demo_deals_keep_their_saved_output(self):
        self.assertEqual(self.cat["as_of"], "2026-09-30")
        self.assertEqual(len(self.cat["capabilities"]), 25)


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
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(config, "V2_CACHE_DIR", Path(tmp) / "cache"):
            reset_demo.build(Path(tmp) / "l.sqlite")
            conn = ledger.connect(Path(tmp) / "l.sqlite")
            try:
                ledger_fixes.add_source_version(conn, "alder_bank", "AB-05", (SCEN / "AB-05_v2_named_exception.md").read_text(),
                                                "AB-05_v2_named_exception.md")
                self.assertEqual(ledger_v2.review(conn, "alder_bank")["model_calls"], 0)
                closed = [(c["name"], i) for c in workspace.overview(conn, "alder_bank")["commitments"] for i in c["issues"]
                          if i["state"] == "Resolved"]
                self.assertEqual(len(closed), 1)
                name, issue = closed[0]
                self.assertIn("BioCatch", name)
                self.assertEqual(issue["finding"], "No approval recorded")
                self.assertIn("named approver", issue["reason"])
                self.assertIn("Arjun Rao", issue["reason"])
                self.assertEqual(issue["resolved_by"]["text"].split(" · ")[0], "Resolved by Pricing and services note, version 2")
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()
