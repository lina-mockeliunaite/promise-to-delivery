"""Offline seal tests for the read-only API.

The app is pointed at a temporary data folder holding a fake harbour_bank and a decoy coral_pay with a
canary file. Nothing here touches the real data/ folder or the real coral_pay path.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

import api
import config

CANARY = "CANARY_TEXT_c0ral_9c2e"
LABEL_MARKER = "LABEL_MARKER_7f3a"
EVAL_MARKER = "EVAL_MARKER_41bd"
HIDDEN_MARKER = "HIDDEN_FIELD_MARKER_88e0"
HARD_CASES_MARKER = "HARD_CASES_MARKER_5d17"

MANIFEST = {
    "deal": "harbour_bank",
    "labels_path": f"../labels/{LABEL_MARKER}.json",
    "documents": [
        {"source_id": "HB-01", "file": "HB-01_call.md", "doc_type": "call_transcript", "date": "2026-09-28"},
        {"source_id": "HB-05", "file": "HB-05_note.md", "doc_type": "pricing_services_note", "date": "2026-10-14"},
        {"source_id": "HB-09", "file": "HB-09_other.md", "doc_type": "mystery_type", "date": "2026-10-30"},
    ],
}


def result_file(timestamp, quote):
    return {
        "deal": "harbour_bank",
        "timestamp_utc": timestamp,
        "model": "test-model",
        "status_counts": {"complete": 1},
        "prompt_hashes": {"system_prompt_sha256": HIDDEN_MARKER},
        "documents": [
            {
                "source_id": "HB-01",
                "status": "complete",
                "error": HIDDEN_MARKER,
                "attempts": [{"error": HIDDEN_MARKER}],
                "statements": [
                    {
                        "statement_id": "HB-01-S01",
                        "source_id": "HB-01",
                        "quote": quote,
                        "language": "firm",
                        "speaker": "Test Speaker",
                        "raw_model_output": HIDDEN_MARKER,
                    }
                ],
            }
        ],
    }


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        data, results, dist = root / "data", root / "results", root / "dist"

        (data / "harbour_bank" / "docs").mkdir(parents=True)
        (data / "harbour_bank" / "docs" / "manifest.json").write_text(json.dumps(MANIFEST))
        (data / "harbour_bank" / "labels").mkdir()
        (data / "harbour_bank" / "labels" / "labels.json").write_text(json.dumps({"quote": LABEL_MARKER}))
        (data / "hard_cases" / "docs").mkdir(parents=True)
        (data / "hard_cases" / "docs" / "manifest.json").write_text(
            json.dumps({"deal": "hard_cases", "documents": [{"source_id": HARD_CASES_MARKER}]})
        )
        (data / "coral_pay").mkdir()
        (data / "coral_pay" / "canary.txt").write_text(CANARY)
        (data / "coral_pay" / "manifest.json").write_text(json.dumps({"documents": [{"source_id": CANARY}]}))
        (data / "catalogue.json").write_text(json.dumps({"note": CANARY}))

        results.mkdir()
        # Written oldest-timestamp last, so modification time would pick the wrong file.
        (results / "extract_harbour_bank_20260930T061113Z.json").write_text(
            json.dumps(result_file("2026-09-30T06:11:13+00:00", "newest quote"))
        )
        (results / "extract_harbour_bank_20260929T100933Z.json").write_text(
            json.dumps(result_file("2026-09-29T10:09:33+00:00", "older quote"))
        )
        # Later timestamps, but not extract_{deal}_<timestamp>.json: must be ignored.
        for name in (
            "eval_extract_harbour_bank_20261001T000000Z_t0.8.json",
            "regression_extract_harbour_bank_20261001T000000Z.json",
            "extract_harbour_bank_20261001T000000Z_copy.json",
            "extract_harbour_bank_latest.json",
        ):
            (results / name).write_text(json.dumps({"documents": [], "marker": EVAL_MARKER}))
        (results / "extract_hard_cases_20261001T000000Z.json").write_text(
            json.dumps(result_file("2026-10-01T00:00:00+00:00", HARD_CASES_MARKER))
        )

        dist.mkdir()
        (dist / "index.html").write_text("<html>index</html>")

        for name, value in (("DATA_DIR", data), ("RESULTS_DIR", results)):
            patcher = mock.patch.object(config, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

        self.client = TestClient(api.create_app(dist_dir=dist), base_url="http://127.0.0.1", follow_redirects=False)

    def assert_clean(self, response):
        for marker in (CANARY, LABEL_MARKER, EVAL_MARKER, HIDDEN_MARKER, HARD_CASES_MARKER):
            self.assertNotIn(marker, response.text)


class TestHappyPath(ApiTestCase):
    def test_deals(self):
        r = self.client.get("/api/deals")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"deals": ["harbour_bank"]})

    def test_sources(self):
        r = self.client.get("/api/deals/harbour_bank/sources")
        self.assertEqual(r.status_code, 200)
        self.assert_clean(r)
        rows = {s["source_id"]: s for s in r.json()["sources"]}
        self.assertEqual(rows["HB-01"]["status"], "extracted")
        self.assertEqual(rows["HB-05"]["status"], "reference_only")
        self.assertEqual(rows["HB-09"]["status"], "unclassified")
        self.assertEqual(set(rows["HB-01"]), {"source_id", "file", "doc_type", "date", "status"})

    def test_latest_is_highest_filename_timestamp_and_labelled_intermediate(self):
        r = self.client.get("/api/deals/harbour_bank/results/latest")
        self.assertEqual(r.status_code, 200)
        self.assert_clean(r)
        body = r.json()
        self.assertIs(body["intermediate"], True)
        self.assertEqual([s["quote"] for s in body["statements"]], ["newest quote"])
        self.assertEqual(body["run"]["timestamp_utc"], "2026-09-30T06:11:13+00:00")
        self.assertEqual(
            set(body["statements"][0]), {"statement_id", "source_id", "quote", "language", "speaker"}
        )

    def test_no_matching_results_is_empty_200(self):
        for p in config.RESULTS_DIR.glob("extract_harbour_bank_2*Z.json"):
            p.unlink()
        r = self.client.get("/api/deals/harbour_bank/results/latest")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["statements"], [])
        self.assertIs(r.json()["intermediate"], True)

    def test_unreadable_results_is_generic_500(self):
        (config.RESULTS_DIR / "extract_harbour_bank_20270101T000000Z.json").write_text("{not json")
        r = self.client.get("/api/deals/harbour_bank/results/latest")
        self.assertEqual(r.status_code, 500)
        self.assertEqual(r.json(), {"detail": "Results unavailable"})


class TestSeal(ApiTestCase):
    def test_1_coral_pay_is_404_and_canary_never_appears(self):
        for path in ("/api/deals/coral_pay/sources", "/api/deals/coral_pay/results/latest"):
            r = self.client.get(path)
            self.assertEqual(r.status_code, 404, path)
            self.assert_clean(r)

    def test_1b_ui_guard_holds_even_if_allowed_deals_were_widened(self):
        with mock.patch.object(config, "ALLOWED_DEALS", config.ALLOWED_DEALS + ["coral_pay"]):
            for path in ("/api/deals/coral_pay/sources", "/api/deals/coral_pay/results/latest"):
                r = self.client.get(path)
                self.assertEqual(r.status_code, 404, path)
                self.assert_clean(r)

    def test_1c_rejected_deals_get_one_generic_body(self):
        names = ("coral_pay", "hard_cases", "nope")
        bodies = {self.client.get(f"/api/deals/{name}/sources").text for name in names}
        self.assertEqual(len(bodies), 1)
        body = bodies.pop()
        for name in names:
            self.assertNotIn(name, body)

    def test_2_traversal_variants(self):
        paths = [
            "/api/deals/harbour_bank/../coral_pay/sources",
            "/api/deals/..%2Fcoral_pay/sources",
            "/api/deals/harbour_bank%2F..%2Fcoral_pay/sources",
            "/api/deals/%2e%2e/coral_pay/sources",
            "/api/deals/%2e%2e%2Fcoral_pay/results/latest",
            "/api/deals/coral_pay/sources/",
            "/api/deals/coral_pay/results/latest/",
            "/api/deals/Coral_Pay/sources",
            "/api/deals/CORAL_PAY/results/latest",
            "/api/deals/%63oral_pay/sources",
        ]
        for path in paths:
            r = self.client.get(path)
            self.assertIn(r.status_code, (404, 422), path)
            self.assert_clean(r)

    def test_2b_trailing_slash_on_a_real_route_does_not_redirect(self):
        r = self.client.get("/api/deals/harbour_bank/sources/")
        self.assertEqual(r.status_code, 404)

    def test_3_hard_cases_is_404(self):
        for path in ("/api/deals/hard_cases/sources", "/api/deals/hard_cases/results/latest"):
            r = self.client.get(path)
            self.assertEqual(r.status_code, 404, path)
            self.assert_clean(r)

    def test_4_no_label_content_in_any_response(self):
        for path in ("/api/deals", "/api/deals/harbour_bank/sources", "/api/deals/harbour_bank/results/latest"):
            self.assert_clean(self.client.get(path))
        for path in ("/api/deals/harbour_bank/labels", "/api/deals/harbour_bank/labels/labels.json"):
            r = self.client.get(path)
            self.assertEqual(r.status_code, 404, path)
            self.assert_clean(r)

    def test_5_static_mount_serves_only_dist(self):
        self.assertEqual(self.client.get("/").status_code, 200)  # the mount is live
        for path in ("/config.py", "/api.py", "/data/catalogue.json", "/.env", "/%2e%2e/config.py", "/../config.py"):
            r = self.client.get(path)
            self.assertEqual(r.status_code, 404, path)
            self.assert_clean(r)

    def test_6_ui_deals_subset_of_allowed_and_excludes_coral_pay(self):
        self.assertTrue(set(config.UI_DEALS) <= set(config.ALLOWED_DEALS))
        self.assertNotIn("coral_pay", config.UI_DEALS)

    def test_6b_import_check_rejects_a_ui_deal_that_is_not_allowed(self):
        config.check_ui_deals(["harbour_bank"], ["harbour_bank", "hard_cases"])
        for bad in (["coral_pay"], ["harbour_bank", "hard_cases_x"]):
            with self.assertRaises(RuntimeError):
                config.check_ui_deals(bad, ["harbour_bank", "hard_cases"])


class TestSurface(ApiTestCase):
    def test_get_only(self):
        for method in ("post", "put", "delete", "patch"):
            r = getattr(self.client, method)("/api/deals")
            self.assertIn(r.status_code, (404, 405), method)

    def test_no_route_takes_a_path_parameter_other_than_deal(self):
        for route in api.app.routes:
            for name in getattr(route, "param_convertors", {}):
                self.assertEqual(name, "deal", route.path)

    def test_api_docs_are_disabled(self):
        for path in ("/docs", "/redoc", "/openapi.json"):
            self.assertEqual(self.client.get(path).status_code, 404, path)

    def test_foreign_host_header_is_rejected(self):
        r = self.client.get("/api/deals", headers={"host": "evil.example"})
        self.assertEqual(r.status_code, 400)


if __name__ == "__main__":
    unittest.main()
