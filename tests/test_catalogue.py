"""Product catalogue pop-up and additions (16 Oct).

Without additions the catalogue the checks use is the published file byte for byte, so hashes, cache keys and saved
model output are unchanged. An addition is append-only, gets the next CAP id, shows in the catalogue view, and marks
every deal "Review out of date"; checking again on unchanged documents makes no model call and changes no finding.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi.testclient import TestClient

import api
import catalogue_store
import integrity
import ledger_fixes
import ledger_v2
import workspace
from test_ledger_v2 import V2Case

H = {"X-Requested-With": "deal-workspace"}
NEW = {"name": "Payee name check", "regions": ["AU"], "status": "beta", "sellable": "requires_named_approval",
       "roadmap_date": "2027-06-30", "limit_name": "max_checks_per_day", "limit_value": 400000,
       "integrations": [], "added_by": "Arjun Rao (Product)"}


def states(conn, slug):
    return sorted((c["name"], i["finding"], i["state"]) for c in workspace.overview(conn, slug)["commitments"] for i in c["issues"])


class TestCatalogue(V2Case):
    def setUp(self):
        super().setUp()
        self.client = TestClient(api.create_app(dist_dir=self.dir / "no-dist", ledger_path=self.dir / "l.sqlite"),
                                 base_url="http://127.0.0.1", follow_redirects=False)

    def test_without_additions_the_checks_use_the_published_file_byte_for_byte(self):
        self.assertEqual(integrity.catalogue_bytes(self.conn), catalogue_store.published_bytes())
        self.assertEqual(catalogue_store.effective_bytes(None), catalogue_store.published_bytes())

    def test_the_view_flattens_every_capability_by_region_and_variant(self):
        v = self.client.get("/api/catalogue").json()
        cap = next(c for c in v["capabilities"] if c["id"] == "CAP-021")
        polygon = next(r for r in cap["rows"] if r["variant"] == "Polygon · NUSD · real time")
        self.assertEqual(polygon["path"], "CAP-021/SG/Polygon/NUSD/real_time")
        self.assertEqual(polygon["sellable_label"], "Needs a named approval")
        monitoring = next(c for c in v["capabilities"] if c["id"] == "CAP-003")
        self.assertIn("Max 500,000 transactions per day", next(r for r in monitoring["rows"] if r["region"] == "AU")["limits"])
        self.assertEqual(v["additions"], 0)

    def test_an_addition_gets_the_next_id_is_shown_with_who_added_it_and_cannot_be_changed(self):
        r = self.client.post("/api/catalogue/capabilities", json=NEW, headers=H)
        self.assertEqual(r.status_code, 200, r.text)
        cap = r.json()["capability"]
        self.assertEqual(cap["id"], "CAP-028")
        self.assertEqual(cap["added"]["by"], "Arjun Rao (Product)")
        self.assertEqual(cap["rows"][0]["limits"], ["Max 400,000 checks per day"])
        self.assertEqual(self.client.post("/api/catalogue/capabilities", json=NEW, headers=H).status_code, 409)  # same name
        with self.assertRaises(Exception):
            self.conn.execute("UPDATE catalogue_additions SET added_by = 'x'")
        with self.assertRaises(Exception):
            self.conn.execute("DELETE FROM catalogue_additions")

    def test_bad_additions_are_refused_in_plain_words(self):
        for change in ({"name": ""}, {"regions": []}, {"regions": ["Australia"]}, {"status": "ga"}, {"sellable": "maybe"},
                       {"limit_name": "Max", "limit_value": 5}, {"limit_value": "lots"}, {"added_by": ""}):
            r = self.client.post("/api/catalogue/capabilities", json={**NEW, **change}, headers=H)
            self.assertEqual(r.status_code, 400, change)
        self.assertEqual(self.client.post("/api/catalogue/capabilities", json=NEW).status_code, 403)  # no write header

    def test_an_addition_marks_deals_out_of_date_and_a_free_recheck_brings_them_back_with_the_same_findings(self):
        did = ledger_fixes.deal_id(self.conn, "harbour_bank")
        before = states(self.conn, "harbour_bank")
        self.assertEqual(ledger_fixes.freshness(self.conn, did)["state"], "Up to date")
        self.client.post("/api/catalogue/capabilities", json=NEW, headers=H)
        self.assertEqual(ledger_fixes.freshness(self.conn, did)["state"], "Review out of date")
        result = ledger_v2.review(self.conn, "harbour_bank", client=None)
        self.assertEqual(result["model_calls"], 0)
        self.assertEqual(ledger_fixes.freshness(self.conn, did)["state"], "Up to date")
        self.assertEqual(states(self.conn, "harbour_bank"), before)

    def test_findings_carry_the_catalogue_entry_they_cite(self):
        paths = {i["catalogue_path"] for c in workspace.overview(self.conn, "harbour_bank")["commitments"] for i in c["issues"]}
        self.assertIn("CAP-021/SG/Polygon/NUSD/real_time", paths)


if __name__ == "__main__":
    unittest.main()
