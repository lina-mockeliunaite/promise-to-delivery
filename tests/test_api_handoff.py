"""Handoff API: saving, the guards, the exports, and the Harbour Bank flow (fix, recheck, save with open items).

Temporary ledger only; a scripted fake stands in for the model (the flow needs none). Only harbour_bank and user deals
are reachable. Nothing under data/coral_pay/ is touched.
"""

import csv
import io
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from test_api_workspace import H, WorkspaceCase
from test_handoff import INTERNAL

SENTINEL_KEY = "sk-ant-sentinel-do-not-leak-0123456789"
BASE = "/api/deals/harbour_bank"


class HandoffApiCase(WorkspaceCase):
    def open_issue_ids(self, deal="harbour_bank"):
        return [i["id"] for c in self.register(deal)["commitments"] for i in c["issues"] if i["state"] != "Resolved"]

    def save(self, decision="proceed", confirmed=None, **extra):
        body = {"decision": decision, "reviewer": "Lina", "note": "Walk-through",
                "confirmed_issue_ids": self.open_issue_ids() if confirmed is None else confirmed,
                "review_id": self.register()["freshness"]["review_id"], **extra}
        return self.post(f"{BASE}/handoffs", body)

    def approval_fix_and_recheck(self):
        text = config.scenario_path("HB-05_v2_named_exception.md").read_text(encoding="utf-8")
        vid = self.post(f"{BASE}/documents", {"source_key": "HB-05", "filename": "HB-05_v2.md", "text": text}).json()["source_version_id"]
        approval = next(i for i in self.commitment("Polygon, real time")["issues"] if i["type"] == "approval")
        fix = self.post(f"{BASE}/fixes", {"route": "allowed_exception", "owner": "Product", "rationale": "Named exception recorded.",
                                          "issue_ids": [approval["id"]], "approved_by": "Daniel Koh",
                                          "evidence": [{"source_version_id": vid, "locator": "Polygon row"}]})
        self.assertEqual(fix.status_code, 200, fix.text)
        r = self.post(f"{BASE}/review", {"fix_id": fix.json()["fix_id"]})
        self.assertEqual(r.status_code, 200, r.text)


class TestGuards(HandoffApiCase):
    def test_every_handoff_route_is_404_for_deals_outside_the_allowlist(self):
        for deal in ("hard_cases", "coral_pay", "u_0123456789abcdef", "..", "harbour_bank%2F..%2Fcoral_pay"):
            for path in ("handoffs", "handoffs/view", "handoffs/export.csv", "handoffs/summary"):
                self.assertIn(self.client.get(f"/api/deals/{deal}/{path}").status_code, (404, 422), (deal, path))
            r = self.post(f"/api/deals/{deal}/handoffs", {"decision": "not_ready", "reviewer": "x"})
            self.assertIn(r.status_code, (404, 422), deal)

    def test_a_write_without_the_header_or_a_json_body_is_refused(self):
        body = {"decision": "not_ready", "reviewer": "Lina"}
        self.assertEqual(self.client.post(f"{BASE}/handoffs", json=body).status_code, 403)
        r = self.client.post(f"{BASE}/handoffs", data="x", headers={**H, "Content-Type": "text/plain"})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.client.get(f"{BASE}/handoffs").json(), {"versions": []})  # nothing was saved

    def test_nothing_saved_yet_and_unknown_versions_are_404(self):
        for path in ("handoffs/view", "handoffs/export.csv", "handoffs/summary"):
            self.assertEqual(self.client.get(f"{BASE}/{path}").status_code, 404, path)
        self.save("not_ready", confirmed=[])
        for path in ("handoffs/view", "handoffs/export.csv", "handoffs/summary"):
            self.assertEqual(self.client.get(f"{BASE}/{path}?version=99").status_code, 404, path)
            self.assertEqual(self.client.get(f"{BASE}/{path}?version=1").status_code, 200, path)

    def test_save_is_refused_when_out_of_date_with_a_plain_message(self):
        self.post(f"{BASE}/documents/include", {"source_key": "HB-04", "included": False})
        r = self.save("not_ready", confirmed=[])
        self.assertEqual((r.status_code, r.json()["detail"]), (409, "Rerun the review before saving the handoff"))

    def test_decision_rules_over_http(self):
        self.assertEqual(self.save("ready", confirmed=[]).status_code, 400)  # issues are open
        ids = self.open_issue_ids()
        r = self.save("proceed", confirmed=ids[:-1])
        self.assertEqual((r.status_code, r.json()["detail"]), (400, "Confirm the owner of every open issue before saving with open items."))
        self.assertEqual(self.client.get(f"{BASE}/handoffs").json(), {"versions": []})
        self.assertEqual(self.save("proceed", confirmed=ids).json(), {"version": 1})


class TestHarbourBankFlow(HandoffApiCase):
    def test_review_fix_recheck_save_with_open_items_puts_the_gap_and_conflict_at_the_top_of_both_exports(self):
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": SENTINEL_KEY}):
            self.approval_fix_and_recheck()
            before = self.register()
            self.assertEqual(self.commitment("Polygon, real time")["status"], "Needs action")
            ids = self.open_issue_ids()
            polygon = {i["type"]: i["state"] for i in self.commitment("Polygon, real time")["issues"]}
            self.assertEqual(polygon, {"approval": "Resolved", "contract_gap": "Needs action", "conflicting_terms": "Needs action"})
            self.assertEqual(self.save("proceed", confirmed=ids[:-1]).status_code, 400)
            saved = self.save("proceed", confirmed=ids)
            self.assertEqual((saved.status_code, saved.json()), (200, {"version": 1}))
            self.assertEqual(self.register(), before)  # saving changed nothing on the live screen

            view = self.client.get(f"{BASE}/handoffs/view").json()
            snap = view["handoff"]
            self.assertEqual((snap["decision"]["label"], snap["decision"]["reviewer"]), ("Proceed with open items", "Lina"))
            self.assertEqual(snap["freshness"], "Up to date")
            self.assertEqual(snap["scope_note"], "Demonstrated on fictional deals with a complete capability catalogue.")
            self.assertTrue(all(i["owner_basis"] == "confirmed by Lina" for i in snap["issues"] if i["open"]))
            self.assertTrue(any(h["route"] == "Record an allowed exception" for h in snap["history"]))

            csv_resp = self.client.get(f"{BASE}/handoffs/export.csv")
            self.assertEqual(csv_resp.status_code, 200)
            self.assertTrue(csv_resp.headers["content-type"].startswith("text/csv"))
            self.assertRegex(csv_resp.headers["content-disposition"], r'^attachment; filename="handoff-[A-Za-z0-9-]+-v1\.csv"$')
            rows = list(csv.reader(io.StringIO(csv_resp.content.decode("utf-8-sig"))))
            top = [r[1].split(":")[0] for r in rows[1:len(ids) + 1]]
            self.assertIn("Missing from the contract", top)
            self.assertIn("Contract says something different", top)
            self.assertTrue(all(r[2] in ("Needs action", "Needs evidence") for r in rows[1:len(ids) + 1]))
            self.assertTrue(all("(confirmed by Lina)" in r[3] for r in rows[1:len(ids) + 1]))

            page = self.client.get(f"{BASE}/handoffs/summary")
            self.assertEqual(page.status_code, 200)
            self.assertTrue(page.headers["content-type"].startswith("text/html"))
            self.assertIn("default-src 'none'", page.headers["content-security-policy"])
            html = page.text
            top_html = html[html.index("Open items"):html.index("All commitments")]
            self.assertIn("Missing from the contract", top_html)
            self.assertIn("Contract says something different", top_html)

            self.assertIn("Closed: the issue is no longer found, and the evidence meets what was needed.", csv_resp.text)
            self.assertIn("Pricing and services note, version 2", html)  # the fix's evidence, by type and exact version
            self.assertIn("Pricing and services note", str(view["handoff"]["history"]))
            self.assertNotIn(".md", str(view) + csv_resp.text + html)
            self.assertIn("Pricing note: named exception approved by", html)  # the approval evidence, in a sentence
            self.assertEqual(self.commitment("Polygon, real time")["presence"],
                             "Not in the contract: the contract says batch instead.")
            everything = str(view) + csv_resp.text + html + str(self.register())
            self.assertEqual(INTERNAL.findall(everything), [])
            self.assertNotIn(SENTINEL_KEY, everything)
            self.assertNotIn("ANTHROPIC", everything)

    def test_a_saved_version_is_what_the_exports_show_not_the_live_screen(self):
        self.save("proceed")
        csv_before = self.client.get(f"{BASE}/handoffs/export.csv?version=1").content
        html_before = self.client.get(f"{BASE}/handoffs/summary?version=1").content
        self.approval_fix_and_recheck()  # live state moves on
        view = self.client.get(f"{BASE}/handoffs/view?version=1").json()
        self.assertTrue(view["changed_since_saved"])
        self.assertEqual(self.client.get(f"{BASE}/handoffs/export.csv?version=1").content, csv_before)
        self.assertEqual(self.client.get(f"{BASE}/handoffs/summary?version=1").content, html_before)
        self.assertEqual(self.save("not_ready", confirmed=[]).json(), {"version": 2})
        self.assertEqual(self.client.get(f"{BASE}/handoffs/export.csv?version=1").content, csv_before)
        versions = self.client.get(f"{BASE}/handoffs").json()["versions"]
        self.assertEqual([v["version"] for v in versions], [2, 1])
        self.assertTrue(versions[1]["changed_since_saved"])


class TestDocumentNamesOnScreen(HandoffApiCase):
    def test_the_documents_list_and_register_name_documents_by_type_and_version_only(self):
        docs = self.client.get(f"{BASE}/documents").json()["documents"]
        self.assertIn("Pricing and services note", [d["name"] for d in docs])
        self.assertTrue(all("filename" not in d for d in docs))
        self.approval_fix_and_recheck()
        docs = self.client.get(f"{BASE}/documents").json()["documents"]
        note = next(d for d in docs if d["name"] == "Pricing and services note")
        self.assertEqual(note["version"], 2)
        shown = [{k: v for k, v in d.items() if k != "source_key"} for d in docs]  # source_key is the API handle, never displayed
        text = str(self.register()) + str(shown)
        self.assertNotIn(".md", text)
        self.assertEqual(INTERNAL.findall(text), [])


class TestExistingDatabase(HandoffApiCase):
    def test_a_database_without_the_handoff_table_gets_it_on_first_use_and_keeps_its_data(self):
        import ledger
        conn = ledger.connect(self.db)
        conn.execute("DROP TABLE IF EXISTS handoff_versions")
        conn.commit()
        n = conn.execute("SELECT COUNT(*) FROM commitments").fetchone()[0]
        conn.close()
        self.assertEqual(self.client.get(f"{BASE}/handoffs").json(), {"versions": []})
        self.assertEqual(self.save("not_ready", confirmed=[]).status_code, 200)
        conn = ledger.connect(self.db)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM commitments").fetchone()[0], n)
        conn.close()


if __name__ == "__main__":
    unittest.main()
