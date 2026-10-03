"""Unit tests for the term parser. Pure functions: no database, no model calls.

The catalogue is read from data/catalogue.json (read-only); a synthetic copy adds a second asset so pairings can
be tested. Labels are never read here.
"""

import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
import terms

CATALOGUE = json.loads((config.DATA_DIR / "catalogue.json").read_text(encoding="utf-8"))
VOCAB = terms.build_vocabulary(CATALOGUE)


def synthetic_catalogue_with_usdc():
    cat = copy.deepcopy(CATALOGUE)
    cap = next(c for c in cat["capabilities"] if c["id"] == "CAP-021")
    cap["regions"]["SG"]["networks"]["Polygon"]["assets"]["USDC"] = copy.deepcopy(
        cap["regions"]["SG"]["networks"]["Polygon"]["assets"]["NUSD"]
    )
    cap["regions"]["SG"]["networks"]["Ethereum"]["assets"]["USDC"] = copy.deepcopy(
        cap["regions"]["SG"]["networks"]["Ethereum"]["assets"]["NUSD"]
    )
    return cat


def parse(quote, vocab=VOCAB):
    return terms.parse_terms(quote, vocab)


def keys(quote, vocab=VOCAB):
    return [t.key for t in parse(quote, vocab).term_sets]


def only(quote, vocab=VOCAB):
    sets = parse(quote, vocab).term_sets
    assert len(sets) == 1, sets
    return sets[0]


class TestNormalisers(unittest.TestCase):
    def test_number_words(self):
        for words, value in (
            ("thirty thousand", 30000), ("twenty-five", 25), ("one hundred and five", 105),
            ("two million", 2_000_000), ("fifteen thousand five hundred", 15500), ("twelve", 12),
        ):
            self.assertEqual(terms.words_to_number(words), value, words)
        self.assertIsNone(terms.words_to_number("thirty widgets"))

    def test_digit_numbers(self):
        for text, value in (("12,000 payouts", 12000), ("40000 payouts", 40000), ("30k payouts", 30000), ("1.5m", 1_500_000)):
            self.assertEqual([v for _, _, v in terms.find_numbers(text)][:1], [value], text)
        self.assertEqual([v for _, _, v in terms.find_numbers("up to thirty thousand payouts")], [30000])

    def test_dates(self):
        for text, value in (
            ("on 31 March 2027", "2027-03-31"), ("on March 31, 2027", "2027-03-31"), ("in March 2027", "2027-03"),
            ("a 1 December go-live", "--12-01"), ("due 2026-12-01", "2026-12-01"), ("on 3rd October", "--10-03"),
        ):
            self.assertEqual([v for _, _, v in terms.find_dates(text)][-1:], [value], text)

    def test_numbers_inside_dates_are_not_quantities(self):
        self.assertIsNone(only("Elva will go live on 1 December 2026.").quantity)
        self.assertIsNone(parse("Planned general availability is 31 March 2027.").term_sets[0].quantity)

    def test_a_bare_number_is_not_a_volume(self):
        self.assertIsNone(only("The work has 3 phases of delivery for the payout ledger connector.").quantity)


class TestVolumeKeys(unittest.TestCase):
    BASE = "The payout ledger connector will handle up to {n} payouts per day at launch."

    def test_digits_and_words_share_a_key(self):
        a, b = keys(self.BASE.format(n="thirty thousand")), keys(self.BASE.format(n="30,000"))
        self.assertEqual(a, b)
        self.assertIsNotNone(a[0])

    def test_differing_terms_never_share_a_key(self):
        base = keys(self.BASE.format(n="30,000"))
        for other in (
            self.BASE.format(n="40,000"),
            "The payout ledger connector will handle at least 30,000 payouts per day at launch.",
            "The payout ledger connector will handle up to 30,000 payouts per month at launch.",
            "The payout ledger connector will handle up to 30,000 transactions per day at launch.",
            "The payout ledger connector will handle up to 30,000 payouts per day by the end of the first year.",
            "The payout ledger connector will handle up to 30,000 payouts per day.",
            "The payout ledger connector for Singapore will handle up to 30,000 payouts per day at launch.",
        ):
            self.assertNotEqual(keys(other), base, other)

    def test_a_volume_needs_unit_and_period(self):
        self.assertEqual(only("The payout ledger connector will handle up to 30,000 per day.").missing, ["unit"])
        self.assertEqual(only("The payout ledger connector will handle up to 30,000 payouts.").missing, ["period"])
        self.assertEqual(only("The payout ledger connector will handle up to 30,000.").missing, ["unit", "period"])
        self.assertIsNone(only("The payout ledger connector will handle up to 30,000.").key)

    def test_quantity_fields(self):
        q = only(self.BASE.format(n="12,000")).quantity
        self.assertEqual(q, {"value": 12000, "bound": "max", "unit": "payouts", "period": "day"})
        self.assertEqual(only(self.BASE.format(n="12,000")).when, ["launch"])


class TestScreeningKeys(unittest.TestCase):
    def test_mode_is_part_of_the_key(self):
        real_time = keys("Every payout on Polygon will be screened in real time.")
        batch = keys("Polygon payouts are screened in hourly batches.")
        self.assertNotEqual(real_time, batch)
        self.assertTrue(real_time[0] and batch[0])

    def test_asset_and_region_do_not_split_a_promise_the_catalogue_cannot_vary(self):
        a = keys("Every NUSD payout on Polygon will be screened in real time before release.")
        b = keys("Polygon wallets are screened in real time, in Singapore.")
        self.assertEqual(a, b)
        self.assertIsNotNone(a[0])

    def test_missing_network_or_mode_is_incomplete_and_has_no_key(self):
        no_mode = only("Wallets on Polygon are screened.")
        self.assertEqual((no_mode.capability, no_mode.missing, no_mode.key), ("CAP-021", ["mode"], None))
        no_network = only("Wallets will be screened in real time.")
        self.assertEqual((no_network.missing, no_network.key), (["network"], None))
        both = only("Wallets will be screened.")
        self.assertEqual(both.missing, ["network", "mode"])

    def test_two_networks_one_asset_give_one_set_each(self):
        sets = parse("NUSD wallets on Ethereum and Polygon are screened in real time.").term_sets
        self.assertEqual([t.network for t in sets], ["Ethereum", "Polygon"])
        self.assertEqual(len({t.key for t in sets}), 2)
        self.assertTrue(all(t.asset == "NUSD" and t.mode == "real_time" for t in sets))

    def test_modes_shared_by_two_networks_missing_mode_stays_incomplete(self):
        sets = parse("NUSD wallet screening on Ethereum and Polygon, in accordance with the annex.").term_sets
        self.assertEqual([(t.network, t.missing) for t in sets], [("Ethereum", ["mode"]), ("Polygon", ["mode"])])
        self.assertEqual([t.key for t in sets], [None, None])

    def test_explicit_pairings_do_not_form_a_cartesian_product(self):
        vocab = terms.build_vocabulary(synthetic_catalogue_with_usdc())
        sets = parse("NUSD on Ethereum and USDC on Polygon wallets are screened in real time.", vocab).term_sets
        self.assertEqual(sorted((t.network, t.asset) for t in sets), [("Ethereum", "NUSD"), ("Polygon", "USDC")])
        mode_pairs = parse("Wallets are screened in real time on Ethereum and in hourly batches on Polygon.", vocab).term_sets
        self.assertEqual(sorted((t.network, t.mode) for t in mode_pairs), [("Ethereum", "real_time"), ("Polygon", "batch")])

    def test_an_ambiguous_association_is_incomplete_with_no_term_sets(self):
        vocab = terms.build_vocabulary(synthetic_catalogue_with_usdc())
        result = parse("NUSD and USDC wallets on Ethereum and Polygon are screened in real time.", vocab)
        self.assertTrue(result.ambiguous)
        self.assertEqual(result.missing, ["association"])
        self.assertEqual(result.term_sets, [])
        self.assertTrue(result.terms_incomplete)

    def test_the_catalogue_flags_its_own_networks(self):
        self.assertTrue(only("Wallets on Ethereum are screened in real time.").network_in_catalogue)


class TestUnlistedNetworks(unittest.TestCase):
    def test_an_unlisted_network_is_recorded_with_in_catalogue_false(self):
        ts = only("We'll have Arbitrum screening live for your launch.")
        self.assertEqual((ts.capability, ts.network, ts.network_in_catalogue), ("CAP-021", "Arbitrum", False))
        self.assertEqual(ts.missing, ["mode"])

    def test_an_unlisted_network_can_be_complete_and_has_its_own_key(self):
        ts = only("Elva will screen every NUSD payout on Arbitrum in real time before release.")
        self.assertEqual((ts.network, ts.network_in_catalogue, ts.missing), ("Arbitrum", False, []))
        self.assertNotEqual(ts.key, only("Elva will screen every NUSD payout on Polygon in real time before release.").key)

    def test_the_generic_list_is_proper_nouns_matched_case_sensitively(self):
        self.assertEqual(only("Wallets on Optimism are screened in real time.").network, "Optimism")
        self.assertIsNone(only("Wallets are screened in real time, with optimism.").network)
        self.assertNotIn("Ethereum", VOCAB.generic_networks)  # catalogue names are not repeated
        self.assertIn("Arbitrum", VOCAB.generic_networks)

    def test_several_unlisted_networks_expand_like_listed_ones(self):
        sets = parse("Wallets on Arbitrum and Solana are screened in real time.").term_sets
        self.assertEqual([(t.network, t.network_in_catalogue) for t in sets], [("Arbitrum", False), ("Solana", False)])


class TestGoLive(unittest.TestCase):
    KEY = terms.GO_LIVE_KEY

    def test_go_live_is_its_own_promise_type_with_a_fixed_key(self):
        ts = only("Elva will go live for Kestrel Remit on 1 March 2027.")
        self.assertEqual((ts.promise_type, ts.capability, ts.go_live_date, ts.missing, ts.key), ("go_live", None, "2027-03-01", [], self.KEY))

    def test_differing_go_live_dates_share_one_key(self):
        a = keys("Elva will go live on 1 March 2027.")
        b = keys("We are targeting a 15 April 2027 go-live.")
        self.assertEqual(a, b)
        self.assertEqual(a, [self.KEY])

    def test_the_go_live_date_is_the_one_nearest_the_phrase(self):
        ts = only("We're targeting a 1 December go-live, provided access is available by 15 November.")
        self.assertEqual(ts.go_live_date, "--12-01")

    def test_go_live_without_a_date_is_still_a_complete_go_live_promise(self):
        ts = only("Elva will go live once the contract is signed.")
        self.assertEqual((ts.go_live_date, ts.missing, ts.key), (None, [], self.KEY))

    def test_a_statement_with_a_capability_and_a_go_live_yields_both_sets(self):
        sets = parse("We will go live with real-time Polygon wallet screening on 1 December 2026.").term_sets
        self.assertEqual([t.promise_type for t in sets], ["capability", "go_live"])
        self.assertEqual(sets[0].network, "Polygon")

    def test_at_go_live_on_a_volume_is_a_milestone_not_a_go_live_promise(self):
        sets = parse("The payout ledger connector will handle up to 5,000 payouts per day at go-live.").term_sets
        self.assertEqual([t.promise_type for t in sets], ["capability"])
        self.assertEqual(sets[0].when, ["launch"])

    def test_launch_alone_is_not_a_go_live_promise(self):
        self.assertEqual(parse("Wallets on Polygon are screened in real time from the 1 December launch.").term_sets[0].promise_type, "capability")

    def test_recurring_service_obligations_stay_incomplete(self):
        result = parse("The parties will hold a weekly project status meeting during implementation.")
        self.assertEqual(result.missing, ["capability"])
        self.assertEqual(result.cadence, ["weekly"])
        self.assertEqual([t.key for t in result.term_sets], [None])


class TestCapabilityRecognition(unittest.TestCase):
    def test_sanctions_screening_is_not_wallet_screening(self):
        ts = only("We will provide sanctions screening for every payout.")
        self.assertEqual(ts.capability, "CAP-007")

    def test_bare_screening_is_no_capability(self):
        ts = only("Screening will be available.")
        self.assertEqual((ts.capability, ts.missing), (None, ["capability"]))

    def test_catalogue_names_are_recognised(self):
        self.assertEqual(only("Elva will provide full case audit history for every alert.").capability, "CAP-014")
        self.assertEqual(only("Elva will deliver VASP counterparty data exchange, subject to approval.").capability, "CAP-024")

    def test_a_volume_beside_two_capabilities_is_an_association_problem(self):
        sets = parse("The payout ledger connector and VASP counterparty data exchange will handle up to 5,000 payouts per day.").term_sets
        self.assertEqual({t.capability for t in sets}, {"CAP-023", "CAP-024"})
        self.assertTrue(all("association" in t.missing and t.key is None for t in sets))

    def test_incomplete_sets_never_have_a_key_and_complete_ones_always_do(self):
        for quote in (
            "Wallets on Polygon are screened.", "Elva will go live on 1 March 2027.", "We hold a weekly meeting.",
            "The payout ledger connector will handle up to 30,000 payouts per day at launch.",
            "Elva will provide full case audit history for every alert.",
        ):
            for ts in parse(quote).term_sets:
                self.assertEqual(ts.key is None, bool(ts.missing), quote)


class TestVocabularyAndPurity(unittest.TestCase):
    def test_a_catalogue_mode_or_region_the_parser_has_no_phrase_for_is_an_error(self):
        cat = copy.deepcopy(CATALOGUE)
        cap = next(c for c in cat["capabilities"] if c["id"] == "CAP-021")
        cap["regions"]["SG"]["networks"]["Ethereum"]["assets"]["NUSD"]["modes"]["streaming"] = {}
        with self.assertRaises(ValueError):
            terms.build_vocabulary(cat)
        cat = copy.deepcopy(CATALOGUE)
        cat["capabilities"][0]["regions"]["NZ"] = copy.deepcopy(cat["capabilities"][0]["regions"]["SG"])
        with self.assertRaises(ValueError):
            terms.build_vocabulary(cat)

    def test_parsing_is_deterministic_and_does_not_mutate_its_inputs(self):
        quote = "NUSD wallets on Ethereum and Polygon are screened in real time before the 1 December launch."
        before = copy.deepcopy(VOCAB.units), list(VOCAB.networks), list(VOCAB.generic_networks)
        first, second = parse(quote), parse(quote)
        self.assertEqual([t.as_dict() for t in first.term_sets], [t.as_dict() for t in second.term_sets])
        self.assertEqual(first.dates, second.dates)
        self.assertEqual(before, (VOCAB.units, VOCAB.networks, VOCAB.generic_networks))
        self.assertEqual(quote, "NUSD wallets on Ethereum and Polygon are screened in real time before the 1 December launch.")


if __name__ == "__main__":
    unittest.main()
