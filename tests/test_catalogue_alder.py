"""Alder's catalogue is a demo fixture (Round 5, 12 Nov): a copy of Elva's published file with three fields changed, so no real company is named anywhere in Alder's documents,
the catalogue pop-up or the model's input. Elva's data/catalogue.json is untouched: Atlas Remit's sealed inputs and every Elva deal's hash stay as they were."""

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import catalogue_store
import config
import deal_catalogue
import ledger

SHARED = config.DATA_DIR / "catalogue.json"
ALDER = config.DATA_DIR / "catalogue_alder.json"
SHARED_SHA256 = "2d2d96a0bb93dea22e100f31c65af4152285447ce44a615da2133247747ebe25"  # data/catalogue.json as it was before Round 5; it must never change here
SENTENCE = " BioCatch is named as an illustrative provider only: the Elva connector and its status are fictional, and no partnership is implied."


class TestAlderCatalogue(unittest.TestCase):
    def setUp(self):
        self.shared = json.loads(SHARED.read_text(encoding="utf-8"))
        self.alder = json.loads(ALDER.read_text(encoding="utf-8"))

    def test_the_shared_catalogue_is_untouched(self):
        self.assertEqual(hashlib.sha256(SHARED.read_bytes()).hexdigest(), SHARED_SHA256)

    def test_exactly_three_fields_differ_and_nothing_else(self):
        cap = lambda c: next(x for x in c["capabilities"] if x["id"] == "CAP-027")
        self.assertEqual((cap(self.alder)["name"], cap(self.alder)["prebuilt_integrations"]), ("Scam-call alerts", []))
        self.assertEqual(self.shared["schema_note"].replace(SENTENCE, ""), self.alder["schema_note"])  # the only change to the note: the sentence naming the real provider
        # with those three fields made equal, the two files are the same
        s, a = json.loads(json.dumps(self.shared)), json.loads(json.dumps(self.alder))
        for c in (s, a):
            cap(c)["name"], cap(c)["prebuilt_integrations"], c["schema_note"] = "x", [], "x"
        self.assertEqual(s, a)
        self.assertEqual(cap(self.alder)["regions"], cap(self.shared)["regions"])  # CAP-027 is still beta and requires a named approval, in SG and AU

    def test_the_alder_file_names_no_real_company_and_the_shared_one_still_does(self):
        self.assertNotIn("biocatch", ALDER.read_text(encoding="utf-8").lower())
        self.assertIn("BioCatch", SHARED.read_text(encoding="utf-8"))  # why a copy was needed

    def test_the_vendor_is_registered_as_a_published_file_named_elva(self):
        self.assertEqual(catalogue_store.VENDORS["elva_alder"], {"name": "Elva", "file": "catalogue_alder.json"})
        self.assertEqual(catalogue_store.published_path("elva_alder"), ALDER)
        with tempfile.TemporaryDirectory() as tmp:
            conn = ledger.open_ledger(Path(tmp) / "l.sqlite")
            try:
                view = catalogue_store.view(conn, "elva_alder")
            finally:
                conn.close()
        self.assertEqual((view["vendor_name"], view["can_add"]), ("Elva", False))  # nothing can be added to it in the app
        self.assertEqual(next(c for c in view["capabilities"] if c["id"] == "CAP-027")["integrations"], [])

    def test_only_alder_is_routed_to_it_and_the_other_deals_are_routed_as_before(self):
        for slug, vendor in (("harbour_bank", "elva"), ("coral_pay", "elva"), ("atlas_remit", "elva"), ("noma_journeys", "aivuna"), ("alder_bank", "elva_alder")):
            self.assertEqual(deal_catalogue.vendor_of(slug), vendor, slug)
        self.assertEqual(deal_catalogue.vendor_name("alder_bank"), "Elva")


if __name__ == "__main__":
    unittest.main()
