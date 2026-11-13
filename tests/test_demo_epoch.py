"""Round 8 (13 Nov): a page that predates a reset is told so (public demo only).

Every reset (a visitor's "Start fresh", the Reset demo button, the hourly job) changes the demo's epoch. The page sends the epoch it loaded with on every write; a write
carrying an older one is refused with a plain message instead of landing silently on the restored deals. No engine, snapshot, fingerprint or stored data is involved."""
import sys
import tempfile
import time
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import api
import public_demo
import reset_demo

H = {"X-Requested-With": "deal-workspace"}
NOTE = {"role": "sales", "note": "A note.", "entered_by": "Demo visitor"}


class TestDemoEpoch(unittest.TestCase):
    def client(self, public):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        db = Path(tmp.name) / "l.sqlite"
        reset_demo.reset(db)
        return TestClient(api.create_app(dist_dir=Path(tmp.name) / "x", ledger_path=db, public=public), base_url="http://127.0.0.1")

    def test_public_config_carries_an_epoch_that_every_reset_changes(self):
        c = self.client(True)
        first = c.get("/api/demo/config").json()["epoch"]
        self.assertTrue(first)
        self.assertEqual(c.post("/api/demo/reset", json={}, headers=H).status_code, 200)
        second = c.get("/api/demo/config").json()["epoch"]
        self.assertNotEqual(first, second)
        self.assertEqual(c.get("/api/demo/config").json()["epoch"], second)  # stable between resets

    def test_a_write_from_before_the_reset_is_refused_plainly_and_a_current_one_is_not(self):
        c = self.client(True)
        old = c.get("/api/demo/config").json()["epoch"]
        c.post("/api/demo/reset", json={}, headers=H)  # another visitor (or the hourly job) resets
        r = c.post("/api/deals/noma_journeys/handover/notes", json=NOTE, headers={**H, "X-Demo-Epoch": old})
        self.assertEqual((r.status_code, r.json()["detail"], r.headers.get("X-Demo-Reset")), (409, public_demo.DEMO_WAS_RESET, "1"))
        self.assertEqual(public_demo.DEMO_WAS_RESET, "The demo was reset.")
        # nothing was written by the refused request
        self.assertIsNone(c.get("/api/deals/noma_journeys/handover").json()["notes"]["sales"])
        now = c.get("/api/demo/config").json()["epoch"]
        self.assertEqual(c.post("/api/deals/noma_journeys/handover/notes", json=NOTE, headers={**H, "X-Demo-Epoch": now}).status_code, 200)

    def test_the_reset_itself_and_requests_without_the_header_are_not_checked(self):
        c = self.client(True)
        old = c.get("/api/demo/config").json()["epoch"]
        c.post("/api/demo/reset", json={}, headers=H)
        time.sleep(1.1)  # the reset names its backup by the second
        self.assertEqual(c.post("/api/demo/reset", json={}, headers={**H, "X-Demo-Epoch": old}).status_code, 200)  # a stale page can still start fresh
        self.assertEqual(c.post("/api/deals/noma_journeys/handover/notes", json=NOTE, headers=H).status_code, 200)  # older pages and tests send no epoch

    def test_local_mode_has_no_epoch_and_ignores_the_header(self):
        c = self.client(False)
        self.assertIsNone(c.get("/api/demo/config").json()["epoch"])
        r = c.post("/api/deals/noma_journeys/handover/notes", json=NOTE, headers={**H, "X-Demo-Epoch": "anything-0"})
        self.assertEqual(r.status_code, 200)


if __name__ == "__main__":
    unittest.main()
