"""Each deal resolves explicitly to its own vendor's catalogue (20 Oct). The four existing deals keep Elva's catalogue and so
keep their hashes and freshness; an Aivuna deal never sees Elva's catalogue or Elva's in-app additions, and nothing can start a
check without going through the resolver."""

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi.testclient import TestClient

import api
import catalogue_store
import config
import deal_catalogue
import deal_stage
import integrity
import ledger
import ledger_fixes
import ledger_v2
import reset_demo
from test_noma_journeys import INTENDED, FakeClient

H = {"X-Requested-With": "deal-workspace"}
ROOT = Path(__file__).resolve().parents[1]
# The canonical SHA-256 of data/catalogue.json. If this changes, every Elva deal's config hash changes with it: update it
# deliberately, never to make a test pass.
ELVA_CATALOGUE_SHA = "029e293c253eb1e5d2cdb013a8bef24b62cf2e1363dc896e0ab36a84aded3a42"


FOUR = ["alder_bank", "harbour_bank", "coral_pay", "atlas_remit"]  # the deals that existed before the second vendor


class TestResolver(unittest.TestCase):
    def test_the_four_existing_deals_and_user_deals_use_elvas_catalogue(self):
        for slug in FOUR + ["u_0123456789abcdef"]:
            self.assertEqual(deal_catalogue.vendor_of(slug), "elva", slug)
            self.assertIsNone(deal_catalogue.path_for(slug), slug)  # no catalogue_path: the unchanged default resolution

    def test_noma_journeys_uses_aivunas(self):
        self.assertEqual((deal_catalogue.vendor_of("noma_journeys"), deal_catalogue.vendor_name("noma_journeys")), ("aivuna", "Aivuna"))
        self.assertEqual(deal_catalogue.path_for("noma_journeys"), config.DATA_DIR / "catalogue_aivuna.json")

    def test_an_unknown_vendor_fails_loudly_instead_of_falling_back_to_elva(self):
        with mock.patch.object(deal_stage, "load_profile", lambda slug: {"catalogue": "acme"}):
            with self.assertRaises(catalogue_store.CatalogueError):
                deal_catalogue.vendor_of("alder_bank")

    def test_elvas_published_catalogue_is_byte_for_byte_what_the_hashes_were_built_on(self):
        import hashlib
        self.assertEqual(hashlib.sha256(integrity.canonical_catalogue((config.DATA_DIR / "catalogue.json").read_bytes())).hexdigest(),
                         ELVA_CATALOGUE_SHA)


class TestTheFourExistingDealsAreUnchanged(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        db = Path(cls.tmp.name) / "l.sqlite"
        reset_demo.reset(db_path=db)
        cls.conn = ledger.connect(db)

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        cls.tmp.cleanup()

    def test_every_deal_is_up_to_date_on_the_hash_computed_from_elvas_catalogue_alone(self):
        want = integrity.config_sha256(integrity.HASH_DEFINITION, catalogue_store.published_bytes("elva"))
        for slug in FOUR:
            did = ledger_fixes.deal_id(self.conn, slug)
            review = self.conn.execute("SELECT MAX(id) FROM reviews WHERE deal_id = ?", (did,)).fetchone()[0]
            self.assertEqual(integrity.review_config(self.conn, review), (integrity.HASH_DEFINITION, want), slug)
            fresh = ledger_fixes.freshness(self.conn, did)
            self.assertEqual((fresh["state"], fresh["reasons"]), ("Up to date", []), slug)


class TestNothingStartsACheckWithoutTheResolver(unittest.TestCase):
    def test_no_module_calls_the_check_entry_points_directly(self):
        # recheck.recheck / ledger_v2.needs_model / ledger_v2.review / ledger_v2.build take the catalogue as an optional argument,
        # so a caller that forgets it would silently use Elva's. Callers go through deal_catalogue (or pass the path, as reset_demo does).
        allowed = {"deal_catalogue.py", "reset_demo.py", "recheck.py", "ledger_v2.py"}
        pattern = re.compile(r"\b(?:recheck\.recheck|ledger_v2\.(?:needs_model|review|build))\(")
        offenders = []
        for path in ROOT.glob("*.py"):
            if path.name in allowed or path.name.startswith("scratch"):
                continue
            for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if pattern.search(line) and not line.lstrip().startswith("#"):
                    offenders.append(f"{path.name}:{n}: {line.strip()[:90]}")
        self.assertEqual(offenders, [])

    def test_no_test_builds_the_ledger_with_ledger_v2_build(self):
        # ledger_v2.build passes no catalogue, so it would check the Aivuna deal against Elva's. Tests use reset_demo.build.
        offenders = [p.name for p in (ROOT / "tests").glob("test_*.py")
                     if p.name != Path(__file__).name and re.search(r"ledger_v2\.build\(", p.read_text(encoding="utf-8"))]
        self.assertEqual(offenders, [])

    def test_reset_demo_passes_each_deals_catalogue(self):
        src = (ROOT / "reset_demo.py").read_text(encoding="utf-8")
        self.assertIn("deal_catalogue.path_for(slug)", src)
        self.assertNotIn("ledger_v2.build(", src)


class TestTheCataloguePopupApi(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        for patch in (mock.patch.object(config, "V2_DEALS", ["noma_journeys", "harbour_bank"]),
                      mock.patch.object(config, "UI_DEALS", ["noma_journeys", "harbour_bank"]),
                      mock.patch.object(config, "V2_CACHE_DIR", Path(tmp.name) / "cache"),
                      mock.patch.dict(config.V2_SEED_FILES, {}, clear=True)):  # scripted findings only: no saved model output
            patch.start()
            self.addCleanup(patch.stop)
        self.db = Path(tmp.name) / "l.sqlite"
        conn = ledger.open_ledger(self.db)
        for slug in ("noma_journeys", "harbour_bank"):
            ledger_v2.import_deal(conn, slug)
        conn.commit()
        ledger_v2.review(conn, "noma_journeys", FakeClient([f for _, f in INTENDED]), None, str(deal_catalogue.path_for("noma_journeys")))
        ledger_v2.review(conn, "harbour_bank", FakeClient([]), None, None)
        conn.close()
        self.client = TestClient(api.create_app(dist_dir=Path(tmp.name) / "no-dist", ledger_path=self.db), base_url="http://127.0.0.1")

    def test_a_deal_opens_its_own_vendors_catalogue(self):
        aivuna = self.client.get("/api/catalogue", params={"deal": "noma_journeys"}).json()
        self.assertEqual((aivuna["vendor"], aivuna["vendor_name"], aivuna["can_add"], len(aivuna["capabilities"])), ("aivuna", "Aivuna", False, 10))
        elva = self.client.get("/api/catalogue", params={"deal": "harbour_bank"}).json()
        self.assertEqual((elva["vendor"], elva["vendor_name"], elva["can_add"], len(elva["capabilities"])), ("elva", "Elva", True, 25))
        self.assertEqual(self.client.get("/api/catalogue").json()["vendor"], "elva")  # neither given: Elva's, as before

    def test_the_home_switch_asks_for_a_vendor_directly(self):
        self.assertEqual(self.client.get("/api/catalogue", params={"vendor": "aivuna"}).json()["vendor_name"], "Aivuna")
        self.assertEqual(self.client.get("/api/catalogue", params={"vendor": "acme"}).status_code, 404)
        self.assertEqual(self.client.get("/api/catalogue", params={"deal": "../elva"}).status_code, 404)
        self.assertEqual(self.client.get("/api/catalogue", params={"deal": "alder_bank"}).status_code, 404)  # not in this scratch ledger's deals

    def test_a_capability_cannot_be_added_to_aivunas_catalogue(self):
        body = {"name": "Voice support", "regions": ["SG"], "status": "beta", "sellable": "standard", "added_by": "Tester", "vendor": "aivuna"}
        r = self.client.post("/api/catalogue/capabilities", json=body, headers=H)
        self.assertEqual(r.status_code, 409)
        self.assertEqual(self.client.get("/api/catalogue", params={"vendor": "aivuna"}).json()["additions"], 0)

    def test_the_deal_list_carries_each_deals_vendor(self):
        rows = {d["deal"]: d for d in self.client.get("/api/workspace/deals").json()["deals"]}
        self.assertEqual((rows["noma_journeys"]["vendor"], rows["noma_journeys"]["vendor_name"]), ("aivuna", "Aivuna"))
        self.assertEqual(rows["harbour_bank"]["vendor"], "elva")


if __name__ == "__main__":
    unittest.main()
