"""Demo polish (11 Nov), item 2: the row's "Promised in" and the drawer's source come from one rule. Every stored statement now carries
found_in, the customer-facing checked documents that contain its exact sentence, earliest first; the commitment's first_found is the
earliest of them. Read-time only: the stored quotes and readings are untouched. Runs on a temporary ledger built from the saved v2
output; the real ledger and reading cache are not written."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

import api
import reset_demo

_tmp = {}


def setUpModule():
    tmp = tempfile.TemporaryDirectory()
    _tmp["tmp"] = tmp
    _tmp["db"] = Path(tmp.name) / "ledger.sqlite"
    reset_demo.reset(_tmp["db"])
    _tmp["client"] = TestClient(api.create_app(dist_dir=Path(tmp.name) / "x", ledger_path=_tmp["db"], public=False), base_url="http://127.0.0.1")


def tearDownModule():
    _tmp["tmp"].cleanup()


def commitments(deal):
    return _tmp["client"].get(f"/api/deals/{deal}/register").json()["commitments"]


class TestOneSourceRule(unittest.TestCase):
    def test_the_launch_specialist_is_first_found_in_the_rfp_and_also_in_the_proposal(self):
        c = next(c for c in commitments("noma_journeys") if "launch specialist" in c["name"])
        self.assertEqual(c["first_found"], {"doc_type_label": "RFP response", "date": "2026-09-28"})
        [st] = c["statements"]
        self.assertEqual((st["doc_type_label"], st["date"]), ("Proposal", "2026-10-05"))  # the reading quoted the Proposal; that is stored and unchanged
        self.assertEqual(st["found_in"], [{"doc_type_label": "RFP response", "date": "2026-09-28"},
                                          {"doc_type_label": "Proposal", "date": "2026-10-05"}])

    def test_for_every_commitment_in_both_public_deals_the_row_and_the_drawer_name_the_same_first_source(self):
        for deal in ("noma_journeys", "alder_bank"):
            for c in commitments(deal):
                firsts = [s["found_in"][0] for s in c["statements"] if s.get("found_in")]
                if c["first_found"]:
                    self.assertTrue(firsts, (deal, c["name"]))
                    earliest = min(firsts, key=lambda f: f["date"] or "9999")
                    self.assertEqual(earliest, c["first_found"], (deal, c["name"]))
                for s in c["statements"]:
                    dates = [f["date"] or "9999" for f in s["found_in"]]
                    self.assertEqual(dates, sorted(dates), (deal, c["name"]))  # earliest first

    def test_internal_documents_are_never_a_source(self):
        for deal in ("noma_journeys", "alder_bank"):
            for c in commitments(deal):
                for s in c["statements"]:
                    for f in s["found_in"]:
                        self.assertNotIn("Internal", f["doc_type_label"], (deal, c["name"]))
                        self.assertNotIn("Pricing", f["doc_type_label"], (deal, c["name"]))

    def test_the_order_is_the_same_after_a_reset(self):
        before = [(c["name"], c["first_found"]) for c in commitments("noma_journeys")]
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / "ledger.sqlite"
            reset_demo.reset(db)
            other = TestClient(api.create_app(dist_dir=Path(d) / "x", ledger_path=db, public=False), base_url="http://127.0.0.1")
            after = [(c["name"], c["first_found"]) for c in other.get("/api/deals/noma_journeys/register").json()["commitments"]]
        self.assertEqual(sorted(before, key=str), sorted(after, key=str))


if __name__ == "__main__":
    unittest.main()
