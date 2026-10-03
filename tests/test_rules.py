"""Tests for rules.py on synthetic deals: authorisation with citations, contractual presence through the contract
chain, and the issues each raises. Each rule has a case where it fires and a case where it must not.
The real catalogue is used (it is development data); nothing under data/coral_pay/ is read. No labels are read."""

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import ledger_consolidate
import references as R
import rules
from test_terms import CATALOGUE, VOCAB

SHA = "e" * 64
NOTE_TEXT = """# INTERNAL — Pricing and services note

| Capability | Scope | Catalogue position | Deal approval |
|---|---|---|---|
| CAP-021 On-chain wallet screening integration | Singapore, NUSD on Ethereum, real-time | Generally available | No exception needed |
| CAP-021 On-chain wallet screening integration | Singapore, NUSD on Polygon, real-time | Beta; requires named approval | No named exception approved |
| CAP-023 Payout ledger connector | Singapore | Maximum 25,000 payouts per day | No approval for 40,000/day |
"""
APPROVED_NOTE = """# INTERNAL — Pricing and services note

| CAP-021 On-chain wallet screening integration | Singapore, NUSD on Polygon, real-time | Beta | Named exception approved for this customer; approved by J. Tan (Head of Product) |
| CAP-023 Payout ledger connector | Singapore | Maximum 25,000 payouts per day | Exception approved for 40,000/day, approved by J. Tan (Head of Product), subject to quarterly capacity review |
"""
CONTRACT_TEXT = "**Clause 2. Services.** Provider will perform the services in the Statement of Work dated 5 October 2026."


def ver(id_, key, doc_type, date, text="", included=True):
    return R.Version(id_, key, doc_type, date, text, included)


def deal(customer_side, contract_side=(), note=NOTE_TEXT, contract=CONTRACT_TEXT, sow_extra=""):
    """customer_side / contract_side: (quote, language). Returns (plan, assessments by commitment name)."""
    versions = [ver(1, "P-01", "proposal", "2026-10-01", "\n".join(q for q, _ in customer_side))]
    if note is not None:
        versions.append(ver(2, "N-01", "pricing_services_note", "2026-10-02", note))
    sow_text = "# SOW\n\n" + "\n\n".join(q for q, _ in contract_side) + sow_extra
    versions.append(ver(3, "S-01", "draft_sow", "2026-10-05", sow_text))
    if contract is not None:
        versions.append(ver(4, "K-01", "draft_contract", "2026-10-08", contract))
    statements = []
    for vid, items, prefix in ((1, customer_side, "P-01"), (3, contract_side, "S-01")):
        for n, (quote, language) in enumerate(items, start=1):
            statements.append({"statement_id": len(statements) + 1, "source_version_id": vid,
                               "statement_key": f"{prefix}-S{n:02d}", "quote": quote, "language": language})
    plan = ledger_consolidate.plan_review(statements, VOCAB, SHA, ledger_consolidate.referenced_sections(statements, versions))
    chain = R.contract_chain(versions)
    info = {s["statement_key"]: {"quote": s["quote"], "language": s["language"], "source_version_id": s["source_version_id"]}
            for s in statements}
    result = rules.assess(plan, versions, chain, sys.modules[__name__].CATALOGUE, VOCAB, info)
    return plan, {c["name"]: result[c["commitment_key"]] for c in plan["commitments"]}


def types(a):
    return sorted(i["issue_type"] for i in a.issues)


POLYGON_RT = ("Every NUSD payout on Polygon will be screened in real time before release.", "firm")
POLYGON_BATCH = ("Polygon recipient wallets are screened in hourly batches.", "firm")
ETH_RT = ("NUSD payouts on Ethereum will be screened in real time before release.", "firm")


class TestAuthorisation(unittest.TestCase):
    def test_standard_and_within_limits_is_authorised_with_a_catalogue_citation(self):
        _, a = deal([ETH_RT], [ETH_RT])
        x = a["On-chain wallet screening integration: Ethereum, real time"]
        self.assertEqual(x.authorisation, "standard_authorised")
        self.assertIn("CAP-021/SG/Ethereum/NUSD/real_time", x.evidence_refs["catalogue"])
        self.assertEqual(types(x), [])

    def test_beta_with_a_negative_note_row_is_no_approval_evidence_citing_that_row(self):
        _, a = deal([POLYGON_RT], [POLYGON_RT])
        x = a["On-chain wallet screening integration: Polygon, real time"]
        self.assertEqual(x.authorisation, "no_approval_evidence")
        self.assertIn("No named exception approved", x.authorisation_evidence)
        issue = next(i for i in x.issues if i["issue_type"] == "approval")
        self.assertEqual((issue["absolute_limit"], issue["raised"]["outcome"], issue["owner_function"]), (0, "open_action", "Product"))
        self.assertEqual(issue["raised"]["evidence_checked"][0]["source_version_id"], 2)

    def test_an_approved_exception_covering_the_scope_is_exception_approved(self):
        _, a = deal([POLYGON_RT], [POLYGON_RT], note=APPROVED_NOTE)
        x = a["On-chain wallet screening integration: Polygon, real time"]
        self.assertEqual(x.authorisation, "exception_approved")
        self.assertEqual(types(x), [])

    def test_approval_wording_without_a_named_approver_needs_review(self):
        note = "| CAP-021 On-chain wallet screening integration | Singapore, NUSD on Polygon, real-time | Exception approved |"
        _, a = deal([POLYGON_RT], [POLYGON_RT], note=note)
        x = a["On-chain wallet screening integration: Polygon, real time"]
        self.assertEqual(x.authorisation, "unknown_needs_review")
        self.assertIn("names no approver", x.authorisation_evidence)

    def test_an_approval_records_its_approver_and_conditions(self):
        quote = ("The payout ledger connector will handle up to 40,000 payouts per day by the end of the first year.", "firm")
        _, a = deal([quote], [], note=APPROVED_NOTE)
        x = next(v for k, v in a.items() if "40,000" in k)
        self.assertEqual(x.evidence_refs["approval"]["approver"], "J. Tan (Head of Product)")
        self.assertEqual(x.evidence_refs["approval"]["conditions"], ["subject to quarterly capacity review"])
        self.assertIn("must be carried into the contract", x.authorisation_evidence)

    def test_an_unlisted_network_is_absolute_only_under_an_explicit_catalogue_rule(self):
        quote = ("Elva will screen every NUSD payout on Arbitrum in real time before release.", "firm")
        without_rule = {k: v for k, v in CATALOGUE.items() if k not in ("coverage", "unlisted_rule")}
        plan_versions = deal([quote], [])  # with the rule: absolute (see the absolute-limit test)
        self.assertTrue(any(i["absolute_limit"] for v in plan_versions[1].values() for i in v.issues))
        with mock.patch.object(sys.modules[__name__], "CATALOGUE", without_rule):
            _, a = deal([quote], [])
        x = a["On-chain wallet screening integration: Arbitrum, real time"]
        approval = next(i for i in x.issues if i["issue_type"] == "approval")
        self.assertEqual(approval["absolute_limit"], 0)
        self.assertIn("does not declare", x.authorisation_evidence)

    def test_an_unstated_region_is_named_as_unchecked(self):
        quote = ("The payout ledger connector will handle up to 12,000 payouts per day at launch.", "firm")
        _, a = deal([quote], [quote])
        evidence = next(v for k, v in a.items() if "12,000" in k).authorisation_evidence
        self.assertIn("Checked: capability, volume, milestone", evidence)
        self.assertIn("the deal's own region is not checked here", evidence)

    def test_an_approval_for_a_different_scope_does_not_count(self):
        note = "| CAP-021 On-chain wallet screening integration | Singapore, NUSD on Polygon, batch | Exception approved for this customer; approved by J. Tan |"
        _, a = deal([POLYGON_RT], [POLYGON_RT], note=note)
        self.assertEqual(a["On-chain wallet screening integration: Polygon, real time"].authorisation, "no_approval_evidence")

    def test_a_volume_above_the_limit_needs_approval_and_cites_the_row_naming_it(self):
        quote = ("The payout ledger connector will handle up to 40,000 payouts per day by the end of the first year.", "firm")
        _, a = deal([quote], [])
        x = next(v for k, v in a.items() if "40,000" in k)
        self.assertEqual(x.authorisation, "no_approval_evidence")
        self.assertIn("No approval for 40,000/day", x.authorisation_evidence)
        _, approved = deal([quote], [], note=APPROVED_NOTE)
        self.assertEqual(next(v for k, v in approved.items() if "40,000" in k).authorisation, "exception_approved")

    def test_a_volume_within_every_regions_limit_is_standard(self):
        quote = ("The payout ledger connector will handle up to 12,000 payouts per day at launch.", "firm")
        _, a = deal([quote], [quote])
        x = next(v for k, v in a.items() if "12,000" in k)
        self.assertEqual(x.authorisation, "standard_authorised")
        self.assertIn("same for every value the catalogue lists", x.authorisation_evidence)

    def test_an_unlisted_network_is_an_absolute_limit_that_only_a_changed_promise_closes(self):
        _, a = deal([("Elva will screen every NUSD payout on Arbitrum in real time before release.", "firm")], [])
        x = a["On-chain wallet screening integration: Arbitrum, real time"]
        issue = next(i for i in x.issues if i["issue_type"] == "approval")
        self.assertEqual(issue["absolute_limit"], 1)
        self.assertEqual(issue["closure_criteria"]["closes_by"], ["change_or_withdraw_promise"])
        self.assertTrue(issue["closure_criteria"]["absolute_limit_blocks_exception"])

    def test_missing_terms_keep_the_verdict_only_if_every_completion_agrees(self):
        _, a = deal([("We'll have Arbitrum screening live for your launch.", "firm")], [])
        arbitrum = next(v for k, v in a.items() if "Arbitrum" in k)
        self.assertEqual(arbitrum.authorisation, "no_approval_evidence")  # unlisted for every mode
        _, b = deal([("Elva will screen NUSD payouts on Polygon before release.", "firm")], [])
        polygon = next(v for k, v in b.items() if "Polygon" in k)
        self.assertEqual(polygon.authorisation, "unknown_needs_review")  # real time needs approval; batch is standard
        self.assertIn("insufficient_evidence", types(polygon))
        self.assertNotIn("approval", types(polygon))

    def test_a_promise_the_catalogue_does_not_cover_is_unknown_never_inferred(self):
        _, a = deal([("Elva will go live on 1 March 2027.", "firm")], [])
        x = a["Go-live"]
        self.assertEqual(x.authorisation, "unknown_needs_review")
        issue = next(i for i in x.issues if i["subject_key"] == "authorisation")
        self.assertEqual((issue["issue_type"], issue["owner_function"], issue["raised"]["outcome"]),
                         ("insufficient_evidence", "Delivery", "open_evidence"))

    def test_without_a_pricing_note_approval_cannot_be_assessed(self):
        _, a = deal([POLYGON_RT], [POLYGON_RT], note=None)
        self.assertEqual(a["On-chain wallet screening integration: Polygon, real time"].authorisation, "unknown_needs_review")

    def test_exploratory_and_conditional_promises_get_no_authorisation_and_no_issues(self):
        quote = ("If Product approves, Elva could screen NUSD payouts on Polygon in real time.", "conditional")
        _, a = deal([quote], [])
        x = a["On-chain wallet screening integration: Polygon, real time"]
        self.assertIsNone(x.authorisation)
        self.assertEqual((x.contractual_presence, x.issues), ("absent", []))


class TestPresence(unittest.TestCase):
    def test_absent_from_the_contract_chain_is_a_contract_gap(self):
        _, a = deal([("Elva will provide full case audit history for every alert.", "firm")], [])
        x = a["Case audit history"]
        self.assertEqual((x.contractual_presence, types(x)), ("absent", ["contract_gap"]))
        gap = x.issues[0]
        self.assertEqual(gap["closure_criteria"]["target_source_keys"], ["K-01", "S-01"])

    def test_in_a_sow_the_contract_incorporates_is_included(self):
        quote = ("Elva will provide full case audit history for every alert.", "firm")
        _, a = deal([quote], [quote])
        self.assertEqual(a["Case audit history"].contractual_presence, "included_in_draft_contract")

    def test_in_a_sow_the_contract_does_not_incorporate_is_absent(self):
        quote = ("Elva will provide full case audit history for every alert.", "firm")
        _, a = deal([quote], [quote], contract="**Clause 2.** Governing law is Singapore.")
        self.assertEqual(a["Case audit history"].contractual_presence, "absent")

    def test_without_a_contract_presence_is_not_assessed_never_absent(self):
        _, a = deal([("Elva will provide full case audit history for every alert.", "firm")], [], contract=None)
        x = a["Case audit history"]
        self.assertEqual(x.contractual_presence, "not_assessed")
        self.assertEqual([(i["issue_type"], i["subject_key"]) for i in x.issues], [("insufficient_evidence", "contract")])

    def test_an_incomplete_commitment_never_gets_a_confirmed_gap(self):
        _, a = deal([("We'll have Arbitrum screening live for your launch.", "firm")], [])
        x = next(v for k, v in a.items() if "Arbitrum" in k)
        self.assertEqual(sorted((i["issue_type"], i["subject_key"]) for i in x.issues),
                         [("approval", "authorisation"), ("insufficient_evidence", "contract")])
        self.assertIn("terms incomplete", x.presence_detail)

    def test_a_missing_reference_makes_only_an_absence_on_its_topic_uncertain(self):
        extra = "\n\n## 3. Reporting\n\nProvider will deliver the reporting set out in Schedule 2."
        audit = ("Elva will provide full case audit history for every alert.", "firm")
        reports = ("Elva will provide operational and audit reports every month.", "firm")
        _, a = deal([audit, reports], [], sow_extra=extra)
        self.assertEqual(types(a["Case audit history"]), ["contract_gap"])
        x = a["Operational and audit reports"]
        self.assertEqual([(i["issue_type"], i["subject_key"]) for i in x.issues], [("insufficient_evidence", "contract")])
        self.assertIn("Schedule 2", x.presence_detail)


class TestConflicts(unittest.TestCase):
    def test_one_differing_mode_against_the_contract_side_is_a_conflict_with_a_link(self):
        _, a = deal([POLYGON_RT], [POLYGON_BATCH])
        x = a["On-chain wallet screening integration: Polygon, real time"]
        self.assertEqual(types(x), ["approval", "conflicting_terms", "contract_gap"])
        conflict = next(i for i in x.issues if i["issue_type"] == "conflicting_terms")
        self.assertEqual(conflict["closure_criteria"]["differing_term"], "mode")
        self.assertEqual(len(x.links), 1)
        self.assertEqual(x.links[0][2], "contract_side_of")
        self.assertEqual(types(a["On-chain wallet screening integration: Polygon, batch"]), [])

    def test_different_networks_are_not_a_conflict(self):
        _, a = deal([POLYGON_RT], [ETH_RT])
        self.assertNotIn("conflicting_terms", types(a["On-chain wallet screening integration: Polygon, real time"]))

    def test_volumes_conflict_only_for_the_same_milestone(self):
        launch12 = ("The payout ledger connector will handle up to 12,000 payouts per day at launch.", "firm")
        year40 = ("The payout ledger connector will handle up to 40,000 payouts per day by the end of the first year.", "firm")
        launch20 = ("The payout ledger connector will handle up to 20,000 payouts per day at launch.", "firm")
        _, a = deal([year40], [launch12])
        self.assertNotIn("conflicting_terms", types(next(v for k, v in a.items() if "40,000" in k)))
        _, b = deal([launch20], [launch12])
        self.assertIn("conflicting_terms", types(next(v for k, v in b.items() if "20,000" in k)))


class TestRaisedChecks(unittest.TestCase):
    def test_every_issue_carries_an_open_raised_check_with_unmet_items(self):
        _, a = deal([POLYGON_RT, ("Elva will go live on 1 March 2027.", "firm")], [POLYGON_BATCH])
        issues = [i for x in a.values() for i in x.issues]
        self.assertTrue(issues)
        for i in issues:
            self.assertIn(i["raised"]["outcome"], ("open_action", "open_evidence"))
            self.assertTrue(i["raised"]["unmet"] and i["raised"]["reason"])
            self.assertEqual(i["closure_criteria"]["version"], rules.CRITERIA_VERSION)
            self.assertEqual(i["raised"]["outcome"] == "open_evidence", i["issue_type"] == "insufficient_evidence")

    def test_the_same_inputs_give_the_same_findings(self):
        first = deal([POLYGON_RT], [POLYGON_BATCH])[1]
        second = deal([POLYGON_RT], [POLYGON_BATCH])[1]
        self.assertEqual({k: (v.authorisation, v.issues, v.links) for k, v in first.items()},
                         {k: (v.authorisation, v.issues, v.links) for k, v in second.items()})


if __name__ == "__main__":
    unittest.main()
