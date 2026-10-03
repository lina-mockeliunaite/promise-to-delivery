"""Tests for references.py: finding and resolving references in contract-side documents. Synthetic text only,
plus one check on the Harbour Bank documents read through the deal guard. Nothing under data/coral_pay/ is read."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
import references as R

SOW_TEXT = """# DRAFT Statement of Work

Date: 5 October 2026

## 2. Volumes

The payout ledger connector will handle up to 12,000 payouts per day at launch.

## 3. Wallet screening

Provider will screen NUSD payouts on Ethereum and Polygon in accordance with the Specification in Annex A.

## Annex A — Specification

A.1 Ethereum: each wallet is screened in real time before release.

A.2 Polygon: wallets are screened in hourly batches.
"""
CONTRACT_DATED = ("# DRAFT Agreement\n\n**Clause 1. Definitions.** Terms have the meanings in the Statement of Work.\n\n"
                  "**Clause 3. Services.** Provider will perform the services in the Statement of Work dated 5 October 2026,"
                  " including Annex A.\n\n**Clause 3.4. Screening.** As described in SOW section 3.\n")


def v(id_, key, doc_type, date, text, included=True):
    return R.Version(id_, key, doc_type, date, text, included)


SOW = v(2, "S-01", "draft_sow", "2026-10-05", SOW_TEXT)
CONTRACT = v(3, "K-01", "draft_contract", "2026-10-08", CONTRACT_DATED)


class TestDocumentReferences(unittest.TestCase):
    def test_a_dated_reference_resolves_to_the_version_with_that_date(self):
        chain = R.contract_chain([SOW, CONTRACT])
        self.assertEqual(chain.contract_version_ids, [3])
        self.assertIn(2, chain.incorporated)
        dated = next(r for r in chain.resolutions if r.from_locator == "Clause 3" and r.kind == "document")
        self.assertEqual((dated.status, dated.resolved_version_id, dated.cited_date), ("resolved", 2, "2026-10-05"))
        self.assertEqual(chain.incorporated[2], "incorporated by K-01 Clause 3")

    def test_an_undated_reference_inherits_the_contracts_dated_citation(self):
        newer = v(4, "S-01", "draft_sow", "2026-10-20", SOW_TEXT)  # a re-dated SOW must not slip in via clause 1
        chain = R.contract_chain([SOW, newer, CONTRACT])
        clause1 = next(r for r in chain.resolutions if r.from_locator == "Clause 1")
        self.assertEqual((clause1.status, clause1.resolved_version_id), ("resolved", 2))
        self.assertNotIn(4, chain.incorporated)

    def test_a_citation_no_version_matches_is_unresolved(self):
        redated = v(2, "S-01", "draft_sow", "2026-10-20", SOW_TEXT)
        chain = R.contract_chain([redated, CONTRACT])
        dated = next(r for r in chain.resolutions if r.from_locator == "Clause 3" and r.kind == "document")
        self.assertEqual((dated.status, dated.target_source_key, dated.resolved_version_id), ("unresolved", "S-01", None))
        self.assertNotIn(2, chain.incorporated)
        self.assertTrue(chain.gaps())

    def test_no_statement_of_work_at_all_is_missing(self):
        chain = R.contract_chain([CONTRACT])
        self.assertTrue(all(r.status == "missing" for r in chain.resolutions))
        self.assertEqual(list(chain.incorporated), [3])

    def test_without_a_date_the_newest_included_version_is_used(self):
        contract = v(3, "K-01", "draft_contract", "2026-10-08", "**Clause 2.** Services in the Statement of Work.")
        old = v(1, "S-01", "draft_sow", "2026-10-01", "x")
        excluded = v(5, "S-01", "draft_sow", "2026-10-30", "x", included=False)
        chain = R.contract_chain([old, SOW, excluded, contract])
        self.assertEqual(chain.resolutions[0].resolved_version_id, 2)
        self.assertNotIn(5, chain.incorporated)

    def test_a_missing_sow_section_is_unresolved(self):
        contract = v(3, "K-01", "draft_contract", "2026-10-08",
                     "**Clause 3.** Statement of Work dated 5 October 2026.\n**Clause 4.** As in SOW section 9.")
        chain = R.contract_chain([SOW, contract])
        sec = next(r for r in chain.resolutions if r.target_locator == "section 9")
        self.assertEqual(sec.status, "unresolved")

    def test_an_excluded_contract_is_not_a_contract(self):
        chain = R.contract_chain([SOW, v(3, "K-01", "draft_contract", "2026-10-08", CONTRACT_DATED, included=False)])
        self.assertFalse(chain.has_contract)
        self.assertEqual(chain.incorporated, {})


class TestSectionReferences(unittest.TestCase):
    def test_an_annex_heading_resolves_and_the_heading_itself_is_not_a_reference(self):
        chain = R.contract_chain([SOW, CONTRACT])
        annex = [r for r in chain.resolutions if r.cited_label == "Annex A"]
        self.assertTrue(annex and all(r.status == "resolved" and r.resolved_version_id == 2 for r in annex))

    def test_a_missing_schedule_is_missing_with_its_topic(self):
        sow = v(2, "S-01", "draft_sow", "2026-10-05", "# SOW\n\n## 3. Reporting\n\nProvider will deliver the reporting set out in Schedule 2.\n")
        contract = v(3, "K-01", "draft_contract", "2026-10-08", "**Clause 2.** Services in the Statement of Work.")
        chain = R.contract_chain([sow, contract])
        gap = next(r for r in chain.gaps())
        self.assertEqual((gap.cited_label, gap.status, gap.target_source_id if hasattr(gap, "target_source_id") else None),
                         ("Schedule 2", "missing", None))
        self.assertEqual(gap.topic, ["report"])

    def test_section_span_runs_to_the_next_heading_of_the_same_level(self):
        start, end = R.section_span(SOW_TEXT, "Annex", "A")
        self.assertTrue(SOW_TEXT[start:end].startswith("## Annex A"))
        self.assertIn("A.2 Polygon", SOW_TEXT[start:end])
        s3, e3 = R.section_span(SOW_TEXT, "section", "3")
        self.assertNotIn("Annex A —", SOW_TEXT[s3:e3].splitlines()[-1])
        self.assertIsNone(R.section_span(SOW_TEXT, "Schedule", "2"))

    def test_a_pointer_quote_finds_its_section(self):
        quote = "Provider will screen NUSD payouts on Ethereum and Polygon in accordance with the Specification in Annex A."
        target, (start, end) = R.referenced_section(quote, SOW, [SOW, CONTRACT])
        self.assertEqual(target.id, 2)
        self.assertIn("A.1 Ethereum", SOW_TEXT[start:end])
        self.assertIsNone(R.referenced_section("No reference here.", SOW, [SOW]))

    def test_topic_words_ignore_generic_contract_language(self):
        self.assertEqual(R.topic_stems("Provider will deliver the services described in Schedule 2."), set())
        self.assertEqual(R.stem("reporting"), R.stem("reports"))


class TestHarbourBank(unittest.TestCase):
    """The real development documents, read through the deal guard."""

    def test_the_contract_incorporates_the_sow_and_annex_a(self):
        manifest = __import__("json").loads(config.doc_path("harbour_bank", "manifest.json").read_text(encoding="utf-8"))
        versions = [v(i, d["source_id"], d["doc_type"], d["date"], config.doc_path("harbour_bank", d["file"]).read_text(encoding="utf-8"))
                    for i, d in enumerate(manifest["documents"], start=1)]
        chain = R.contract_chain(versions)
        keys = {versions[i - 1].source_key for i in chain.incorporated}
        self.assertEqual(keys, {"HB-06", "HB-07"})
        self.assertEqual(chain.gaps(), [])
        self.assertTrue(any(r.cited_label == "Statement of Work dated 20 October 2026" and r.status == "resolved"
                            for r in chain.resolutions))


if __name__ == "__main__":
    unittest.main()
