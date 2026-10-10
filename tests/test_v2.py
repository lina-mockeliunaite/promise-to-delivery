"""v2 detection: the verifier accepts correct findings on every dev deal, rejects wrong ones, and the scorer counts."""

import json
import unittest
from types import SimpleNamespace as NS
from pathlib import Path
import tempfile

import config
import detect_v2
import run_v2
import score_v2
import sealed_run

CAT = json.loads((config.DATA_DIR / "catalogue.json").read_text(encoding="utf-8"))
BLANK = dict(catalogue_path=None, unlisted_value=None, limit_name=None, promised_quantity=None, missing_phrases=[],
             contract_quote=None, note_quote=None, subject=None, promised_value=None, contract_value=None,
             reason="r", commitment="c")


def F(kind, quotes, **kw):
    return {**BLANK, "kind": kind, "promise_quotes": [{"source_id": s, "quote": q} for s, q in quotes], **kw}


def Q(src, quote):
    return {"source_id": src, "quote": quote}


HB05 = "Every NUSD payout on Polygon will be screened in real time through Elva's analytics integration before release, from the 1 December launch."
ORACLE = {
    "harbour_bank": [
        F("approval_required", [("HB-04", HB05)], catalogue_path="CAP-021/SG/Polygon/NUSD/real_time"),
        F("conflicting_terms", [("HB-04", HB05)], subject="Polygon", promised_value="real time", contract_value="hourly",
          contract_quote=Q("HB-06", "A.2 Polygon: recipient wallets are screened through the analytics integration in batches at hourly intervals.")),
        F("over_limit", [("HB-04", "The payout ledger connector will handle up to 40,000 payouts per day by the end of the first year.")],
          catalogue_path="CAP-023/SG", limit_name="max_payouts_per_day", promised_quantity=40000),
        F("contract_gap", [("HB-04", "The payout ledger connector will handle up to 40,000 payouts per day by the end of the first year.")],
          missing_phrases=["40,000 payouts per day"]),
        F("approval_required", [("HB-04", "For payouts to exchange-hosted wallets, VASP counterparty data exchange will be generally available in Singapore by 31 March 2027.")],
          catalogue_path="CAP-024/SG"),
        F("contract_gap", [("HB-04", "For payouts to exchange-hosted wallets, VASP counterparty data exchange will be generally available in Singapore by 31 March 2027.")],
          missing_phrases=["VASP counterparty data exchange"]),
    ],
    "practice_cases": [
        F("approval_required", [("PC-01", "Every payout to a Polygon wallet gets an instant risk check before funds move.")],
          catalogue_path="CAP-021/SG/Polygon/NUSD/real_time"),
        F("absolute_limit", [("PC-01", "Tron wallets will be covered by the same pre-release checks.")], catalogue_path="CAP-021/SG", unlisted_value="Tron"),
        F("contract_gap", [("PC-01", "Tron wallets will be covered by the same pre-release checks.")], missing_phrases=["Tron"]),
        F("over_limit", [("PC-02", "We will comfortably absorb around 30k payouts a day from launch.")],
          catalogue_path="CAP-023/SG", limit_name="max_payouts_per_day", promised_quantity=30000),
        F("over_limit", [("PC-02", "Our service handles up to 120,000 sanctions checks every day.")],
          catalogue_path="CAP-007/SG", limit_name="max_screenings_per_day", promised_quantity=120000),
        F("approval_required", [("PC-02", "Counterparty data sharing with exchanges will be switched on in Singapore by the end of Q1 2027.")],
          catalogue_path="CAP-024/SG"),
    ],
    "hard_cases": [
        F("absolute_limit", [("KR-02", "Elva will screen every NUSD payout on Arbitrum in real time before release.")],
          catalogue_path="CAP-021/SG", unlisted_value="Arbitrum"),
        F("contract_gap", [("KR-02", "Elva will go live for Kestrel Remit on 1 March 2027.")], missing_phrases=["1 March 2027"]),
        F("contract_gap", [("KR-02", "Elva will provide full case audit history for every alert raised on Kestrel Remit payouts.")],
          missing_phrases=["full case audit history"]),
    ],
    "coral_pay": [
        F("contract_gap", [("CP-04", "Elva will deliver two 90-minute operations training sessions for Coral Pay's payout operations team before launch.")],
          missing_phrases=["90-minute operations training sessions"]),
        F("absolute_limit", [("CP-04", "Elva will screen the recipient wallet of every NUSD payout on Solana through its pre-built analytics integration before release.")],
          catalogue_path="CAP-021/AU", unlisted_value="Solana"),
        F("absolute_limit", [("CP-03", "Elva will deploy Coral Pay's production environment on Microsoft Azure in the Australia East region.")],
          catalogue_path="CAP-019/AU", unlisted_value="Microsoft Azure"),
    ],
}


def docs_for(deal):
    if deal in config.ALLOWED_DEALS:
        return detect_v2.deal_documents(deal)
    with sealed_run.unsealed(deal, config.RESULTS_DIR):
        return detect_v2.deal_documents(deal)


def labels_for(deal):
    if deal in config.ALLOWED_DEALS:
        return score_v2.load_labels(deal)
    with sealed_run.unsealed(deal, config.RESULTS_DIR):
        return score_v2.load_labels(deal)


class OracleTest(unittest.TestCase):
    """Correct findings, written from the labels, must pass verification: the verifier is not the bottleneck."""

    def test_each_correct_finding_is_accepted(self):
        for deal, findings in ORACLE.items():
            docs = docs_for(deal)
            for f in findings:
                with self.subTest(deal=deal, kind=f["kind"], q=f["promise_quotes"][0]["quote"][:40]):
                    self.assertEqual(detect_v2.verify(f, docs, CAT), [])

    def test_oracle_scores(self):
        expected_missing = {"harbour_bank": [], "practice_cases": ["PC1 contradiction", "PC1 expectation_gap", "PC10 expectation_gap",
                                                                   "PC7 contradiction", "PC7 expectation_gap", "PC9 expectation_gap"],
                            "hard_cases": ["KC1 expectation_gap", "KC4 overcommitment"], "coral_pay": []}
        for deal, findings in ORACLE.items():
            s = score_v2.score(deal, [dict(f, problems=[]) for f in findings], [], labels_for(deal))
            with self.subTest(deal=deal):
                self.assertEqual(sorted(f"{m['commitment']} {m['issue']}" for m in s["missed"]), expected_missing[deal])
                self.assertEqual(s["false_flags"], 0)


class RejectTest(unittest.TestCase):
    def setUp(self):
        self.docs = detect_v2.deal_documents("harbour_bank")

    def check(self, f, fragment):
        problems = detect_v2.verify(f, self.docs, CAT)
        self.assertTrue(problems, "expected a rejection")
        self.assertIn(fragment, " ".join(problems))

    def test_paraphrased_quote(self):
        self.check(F("approval_required", [("HB-04", "Every NUSD payout on Polygon is screened in real time.")],
                     catalogue_path="CAP-021/SG/Polygon/NUSD/real_time"), "not verbatim")

    def test_internal_document_is_not_a_promise(self):
        self.check(F("contract_gap", [("HB-05", "Maximum 25,000 payouts per day")], missing_phrases=["25,000"]), "internal")

    def test_standard_entry_is_not_an_approval_finding(self):
        self.check(F("approval_required", [("HB-04", "NUSD payouts on Ethereum will be screened in real time through Elva's analytics integration before release.")],
                     catalogue_path="CAP-021/SG/Ethereum/NUSD/real_time"), "standard")

    def test_quantity_within_limit(self):
        self.check(F("over_limit", [("HB-04", "The payout ledger connector will handle up to 12,000 payouts per day at launch.")],
                     catalogue_path="CAP-023/SG", limit_name="max_payouts_per_day", promised_quantity=12000), "within the limit")

    def test_listed_value_is_not_absolute(self):
        self.check(F("absolute_limit", [("HB-04", HB05)], catalogue_path="CAP-021/SG", unlisted_value="Polygon"), "is listed")

    def test_unknown_capability(self):
        self.check(F("approval_required", [("HB-04", HB05)], catalogue_path="CAP-999/SG"), "does not exist")

    def test_phrase_present_in_contract(self):
        self.check(F("contract_gap", [("HB-04", "The payout ledger connector will handle up to 12,000 payouts per day at launch.")],
                     missing_phrases=["12,000 payouts per day"]), "appears in the contract chain")

    def test_long_phrase(self):
        self.check(F("contract_gap", [("HB-04", HB05)], missing_phrases=["Every NUSD payout on Polygon will be screened"]), "longer than six words")

    def test_conflict_without_shared_subject(self):
        self.check(F("conflicting_terms", [("HB-04", HB05)], subject="Polygon", promised_value="real time", contract_value="12,000",
                     contract_quote=Q("HB-06", "The payout ledger connector will handle up to 12,000 payouts per day at launch.")), "subject")

    def test_named_approval_in_pricing_note_rejects(self):
        scen = (config.ROOT / "data" / "scenarios" / "HB-05_v2_named_exception.md").read_text(encoding="utf-8")
        docs = [dict(d, text=scen) if d["source_id"] == "HB-05" else d for d in self.docs]
        f = F("approval_required", [("HB-04", HB05)], catalogue_path="CAP-021/SG/Polygon/NUSD/real_time")
        self.assertIn("records an approval", " ".join(detect_v2.verify(f, docs, CAT)))
        # 'No named exception approved for Harbour Bank' (the original note) is not an approval
        self.assertEqual(detect_v2.verify(f, self.docs, CAT), [])


class FakeClient:
    def __init__(self, findings):
        self.messages = NS(create=self.create)
        self.findings, self.calls = findings, []

    def create(self, **kw):
        self.calls.append(kw)
        text = json.dumps({"findings": self.findings})
        return NS(content=[NS(type="text", text=text)], stop_reason="end_turn",
                  usage=NS(input_tokens=1000, output_tokens=200, output_tokens_details=None))


class ReviewTest(unittest.TestCase):
    def test_review_splits_and_scores(self):
        bad = F("approval_required", [("HB-04", "made up")], catalogue_path="CAP-021/SG/Polygon/NUSD/real_time")
        client = FakeClient(ORACLE["harbour_bank"] + [bad])
        out = run_v2.run_deal(client, "harbour_bank", CAT)
        self.assertEqual(len(out["accepted"]), 6)
        self.assertEqual(len(out["rejected"]), 1)
        self.assertEqual(out["score"]["found"], out["score"]["targets"])
        self.assertEqual(client.calls[0]["output_config"]["format"]["type"], "json_schema")
        self.assertIn("CATALOGUE", client.calls[0]["messages"][0]["content"])

    def test_unparseable_reply_is_recorded_not_guessed(self):
        client = FakeClient([])
        client.create = lambda **kw: NS(content=[NS(type="text", text="{oops")], stop_reason="max_tokens",
                                        usage=NS(input_tokens=1, output_tokens=1, output_tokens_details=None))
        client.messages = NS(create=client.create)
        out = detect_v2.review(client, detect_v2.deal_documents("harbour_bank"), CAT)
        self.assertEqual(out["accepted"], [])
        self.assertIn("parse_error", out)

    def test_replay_reverifies_without_a_model_call(self):
        saved = {"kind": "v2_dev", "v2_version": 1, "deals": [{"deal": "harbour_bank", "findings": ORACLE["harbour_bank"], "cost_usd": 0.0}]}
        out = run_v2.reverify(saved, CAT)
        self.assertEqual(out["deals"][0]["score"]["found"], 7)
        self.assertIn("harbour_bank", run_v2.render(out))


class SealedV2Test(unittest.TestCase):
    def test_refuses_development_deals(self):
        for deal in ("harbour_bank", "coral_pay"):
            with self.assertRaises(sealed_run.Refused):
                run_v2.sealed(FakeClient([]), deal)

    def test_refuses_a_second_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "sealed_v2_some_deal_20261010T000000Z.json").write_text("{}")
            from unittest import mock
            with mock.patch.object(config, "RESULTS_DIR", Path(tmp)):
                with self.assertRaises(sealed_run.Refused):
                    run_v2.sealed(FakeClient([]), "some_deal")

    def test_refuses_without_a_seal(self):
        with tempfile.TemporaryDirectory() as tmp:
            from unittest import mock
            with mock.patch.object(config, "RESULTS_DIR", Path(tmp)):
                with self.assertRaises(sealed_run.Refused):
                    run_v2.sealed(FakeClient([]), "no_such_deal", root=Path(tmp))


if __name__ == "__main__":
    unittest.main()


class NumberWordsTest(unittest.TestCase):
    def test_words(self):
        self.assertIn(30000, detect_v2.word_numbers("handle up to thirty thousand payouts"))
        self.assertIn(120000, detect_v2.word_numbers("one hundred and twenty thousand checks"))
        self.assertIn(25000, detect_v2.word_numbers("twenty-five thousand a day"))
        self.assertNotIn(30000, detect_v2.word_numbers("thirty payouts and a thousand reasons"))

    def test_over_limit_in_words_is_accepted(self):
        docs = detect_v2.deal_documents("hard_cases")
        f = F("over_limit", [("KR-02", "The payout ledger connector will handle up to thirty thousand payouts per day at launch.")],
              catalogue_path="CAP-023/SG", limit_name="max_payouts_per_day", promised_quantity=30000)
        self.assertEqual(detect_v2.verify(f, docs, CAT), [])


class SealedV2EndToEndTest(unittest.TestCase):
    """The sealed v2 path on a practice deal posing as sealed: seal check, v2 review, baseline, render."""

    def test_runs_v2_and_baseline_once(self):
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            client = FakeClient(ORACLE["practice_cases"])
            with mock.patch.object(config, "RESULTS_DIR", Path(tmp)), \
                    mock.patch.object(config, "ALLOWED_DEALS", [d for d in config.ALLOWED_DEALS if d != "practice_cases"]), \
                    mock.patch.object(run_v2, "DEV_DEALS", []):
                out = run_v2.sealed(client, "practice_cases")
            self.assertEqual(out["seal_files_verified"], 8)
            self.assertEqual(len(client.calls), 2)  # v2 review + baseline
            self.assertIn("answer", out["baseline"])
            self.assertIn("baseline (one call", run_v2.render(out))
