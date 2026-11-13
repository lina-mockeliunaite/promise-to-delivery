"""The Alder documents (Round 5, 12-13 Nov): a two-row story in plain English. Staged until the readings were accepted, live since 13 Nov. These checks pin what the readings were made for:
no real company, no volume promise or scoring threshold, one identical sentence in the revised statement of work and the signed appendix, an approval that starts later than the promise."""

import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config

DOCS = config.DATA_DIR / "alder_bank" / "docs"
SCEN = config.DATA_DIR / "scenarios"
SENTENCE = "Scam-call alerts will be live from the 1 February 2027 launch: they warn the bank when a customer seems to be on a call with a scammer while making a payment."
read = lambda p: Path(p).read_text(encoding="utf-8")
ALDER_FILES = [*sorted(DOCS.glob("AB-*.md")), *[SCEN / n for n in ("AB-05_v2_named_exception.md", "AB-06_v2_coaching_added.md", "AB-09_signed_contract.md")],
               DOCS.parent / "BRIEF.md", config.DATA_DIR / "profiles" / "alder_bank.json", config.DATA_DIR / "catalogue_alder.json"]


class TestAlderDocuments(unittest.TestCase):
    def test_no_real_company_no_volume_promise_no_threshold_and_no_coaching_wording(self):
        for p in ALDER_FILES:
            text = read(p).lower()
            for bad in ("biocatch", "750,000", "aud 1,000", "coach", "planned ga ") + (() if p.name.startswith("catalogue") else ("behavioural",)):  # the catalogue describes CAP-027's signals, in Elva's own words
                self.assertNotIn(bad, text, f"{p.name}: {bad}")

    def test_the_real_time_promise_and_annex_a_agree_so_neither_is_a_finding(self):
        prop = read(DOCS / "AB-04_proposal.md")
        for path in (DOCS / "AB-06_draft_sow.md", SCEN / "AB-06_v2_coaching_added.md"):
            sow = read(path)
            self.assertIn("A.1 All outbound instant payments are scored in real time before the payment is released.", sow)
            self.assertNotIn("below", sow.split("Annex A")[-1].lower())  # no hourly batches
        self.assertIn("All outbound instant payments will be scored in real time before they are released.\n", prop)
        self.assertIn("up to 200,000 payments per day at launch", prop)  # the launch volume stays, in the proposal and the SOW
        self.assertIn("up to 200,000 payments per day at launch", read(DOCS / "AB-06_draft_sow.md"))

    def test_the_proposal_states_real_time_scoring_without_a_date(self):
        sentence = next(l for l in read(DOCS / "AB-04_proposal.md").splitlines() if "scored in real time" in l)
        self.assertNotRegex(sentence, r"launch|\d{4}")  # no date, so no date-based gap; consistent with Annex A.1

    def test_the_promise_the_sow_and_the_signed_appendix_say_live_from_1_february_and_the_approval_says_from_1_may(self):
        self.assertIn("Scam-call alerts warn the bank when a customer seems to be on a call with a scammer while making a payment, live from the 1 February 2027 launch.", read(DOCS / "AB-03_rfp_response.md"))
        sow, signed = read(SCEN / "AB-06_v2_coaching_added.md"), read(SCEN / "AB-09_signed_contract.md")
        self.assertEqual((sow.count(SENTENCE), signed.count(SENTENCE)), (1, 1))  # one identical sentence, built from one string
        self.assertEqual(len(re.findall(r"\d{1,2} [A-Z][a-z]+ \d{4}", SENTENCE)), 1)  # one explicit date in it
        self.assertIn("**1. Launch.** The platform launches on 1 February 2027.", signed)  # the signed appendix still states the go-live date
        approval = read(SCEN / "AB-05_v2_named_exception.md")
        self.assertIn("approved by Arjun Rao (Head of Product) from 1 May 2027", approval)
        self.assertIn("Scam-call alerts are approved for Alder Bank from 1 May 2027.", approval)

    def test_the_base_contract_chain_states_the_start_date_without_the_launch_phrases_so_only_the_scam_call_gap_opens(self):
        sow, contract = read(DOCS / "AB-06_draft_sow.md"), read(DOCS / "AB-07_draft_contract.md")
        self.assertIn("**Clause 2. Commencement.** The Services commence on 1 February 2027.", contract)
        for name, text in (("AB-06", sow), ("AB-07", contract)):
            for phrase in ("1 February 2027 launch", "scam-call", "on a call with a scammer", "call with a scammer"):
                self.assertNotIn(phrase.lower(), text.lower(), f"{name}: {phrase}")
        self.assertIn("No named exception approved for Alder Bank", read(DOCS / "AB-05_pricing_services_note.md"))

    def test_the_approval_rows_carry_the_capability_id_the_verifier_matches_and_the_catalogue_name(self):
        cat = json.loads(read(config.DATA_DIR / "catalogue_alder.json"))
        name = next(c["name"] for c in cat["capabilities"] if c["id"] == "CAP-027")
        self.assertEqual(name, "Scam-call alerts")
        for path in (DOCS / "AB-05_pricing_services_note.md", SCEN / "AB-05_v2_named_exception.md"):
            row = next(l for l in read(path).splitlines() if "CAP-027" in l)
            self.assertIn(f"CAP-027 {name}", row)
            self.assertIn("planned general release 31 December 2027", row)

    def test_azure_hosting_is_kept_exactly(self):
        for name, needle in (("AB-03_rfp_response.md", "Elva will host Alder's dedicated environment on Microsoft Azure in the Australia East region."),
                             ("AB-06_draft_sow.md", "Provider will host the Customer's dedicated environment on Amazon Web Services in the Sydney region."),
                             ("AB-01_discovery_call.md", "We run everything on Microsoft Azure today, so hosting matters to us.")):
            self.assertIn(needle, read(DOCS / name))

    def test_the_profile_points_at_the_alder_catalogue_and_titles_the_two_rows(self):
        prof = json.loads(read(config.DATA_DIR / "profiles" / "alder_bank.json"))
        self.assertEqual(prof["deliverables"][1], "Checks every outbound instant payment for scams before it's released")
        self.assertIn("Up to 200,000 payments a day at launch", prof["deliverables"])
        self.assertEqual(prof["catalogue"], "elva_alder")
        self.assertEqual(sorted(prof["titles"].values()), ["Hosting on Microsoft Azure", "Scam-call alerts live at launch"])

    def test_the_alder_deal_has_no_seed_and_reads_its_first_review_from_the_cache(self):
        self.assertNotIn("alder_bank", config.V2_SEED_FILES)


if __name__ == "__main__":
    unittest.main()
