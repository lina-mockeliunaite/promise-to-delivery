"""Handover records (16 Oct, after Checkpoint 3): seen marks, both notes, document links, handover complete, the deal list.

Visibility only: none of these records may change a finding, and once the handover is complete no route may change the
deal. Runs against a temporary ledger built from the development deals, like test_api_workspace.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_api_workspace import WorkspaceCase


def states(reg):
    return [(c["name"], i["id"], i["state"], i["finding"]) for c in reg["commitments"] for i in c["issues"]]


class HandoverCase(WorkspaceCase):
    def first_open_issue(self):
        reg = self.register()
        return next(i["id"] for c in reg["commitments"] for i in c["issues"] if i["state"] != "Resolved")

    def a_document(self):
        return self.client.get("/api/deals/harbour_bank/documents").json()["documents"][0]["source_key"]

    def sign(self, on="2026-10-15"):
        r = self.post("/api/deals/harbour_bank/signature", {"signed_on": on, "recorded_by": "Maya (sales)"})
        self.assertEqual(r.status_code, 200, r.text)

    def both_notes(self):
        self.assertEqual(self.post("/api/deals/harbour_bank/handover/notes",
                                   {"role": "sales", "note": "Polygon real-time was promised in the proposal.",
                                    "entered_by": "Maya (sales)"}).status_code, 200)
        self.assertEqual(self.post("/api/deals/harbour_bank/handover/notes",
                                   {"role": "delivery", "note": "Accepted; payout capacity to confirm at kick-off.",
                                    "entered_by": "Sam (delivery)"}).status_code, 200)


class TestSeen(HandoverCase):
    def test_seen_is_recorded_once_per_person_and_shown_on_the_item(self):
        issue = self.first_open_issue()
        r = self.post("/api/deals/harbour_bank/seen", {"issue_id": issue, "seen_by": "Lina"})
        self.assertEqual(r.status_code, 200, r.text)
        self.post("/api/deals/harbour_bank/seen", {"issue_id": issue, "seen_by": "Lina"})
        self.post("/api/deals/harbour_bank/seen", {"issue_id": issue, "seen_by": "Sam"})
        item = next(i for c in self.register()["commitments"] for i in c["issues"] if i["id"] == issue)
        self.assertEqual([s["by"] for s in item["seen"]], ["Lina", "Sam"])

    def test_seen_needs_a_name_and_an_item_in_this_deal(self):
        self.assertEqual(self.post("/api/deals/harbour_bank/seen",
                                   {"issue_id": self.first_open_issue(), "seen_by": " "}).status_code, 400)
        self.assertEqual(self.post("/api/deals/harbour_bank/seen", {"issue_id": 999999, "seen_by": "Lina"}).status_code, 404)


class TestNotesAndLinks(HandoverCase):
    def test_latest_note_per_role_wins_and_role_is_required(self):
        self.both_notes()
        self.post("/api/deals/harbour_bank/handover/notes",
                  {"role": "sales", "note": "Updated note.", "entered_by": "Maya (sales)"})
        notes = self.register()["handover"]["notes"]
        self.assertEqual(notes["sales"]["note"], "Updated note.")
        self.assertEqual(notes["delivery"]["by"], "Sam (delivery)")
        self.assertEqual(self.post("/api/deals/harbour_bank/handover/notes",
                                   {"role": "product", "note": "x", "entered_by": "y"}).status_code, 400)

    def test_a_document_link_must_be_https_and_appears_wherever_the_document_is_listed(self):
        key = self.a_document()
        bad = self.post("/api/deals/harbour_bank/documents/link",
                        {"source_key": key, "url": "javascript:alert(1)", "set_by": "Lina"})
        self.assertEqual(bad.status_code, 400)
        url = "https://drive.google.com/file/d/example/view"
        ok = self.post("/api/deals/harbour_bank/documents/link", {"source_key": key, "url": url, "set_by": "Lina"})
        self.assertEqual(ok.status_code, 200, ok.text)
        docs = self.client.get("/api/deals/harbour_bank/documents").json()["documents"]
        self.assertEqual(next(d for d in docs if d["source_key"] == key)["link"], url)
        staged = [d["link"] for s in self.register()["stage"]["stages"] for d in s["documents"]]
        self.assertIn(url, staged)
        self.assertEqual(self.post("/api/deals/harbour_bank/documents/link",
                                   {"source_key": "NOPE", "url": url, "set_by": "Lina"}).status_code, 404)


class TestVisibilityNeverChangesFindings(HandoverCase):
    def test_seen_notes_and_links_leave_every_finding_as_it_was(self):
        before = self.register()
        self.post("/api/deals/harbour_bank/seen", {"issue_id": self.first_open_issue(), "seen_by": "Lina"})
        self.both_notes()
        self.post("/api/deals/harbour_bank/documents/link",
                  {"source_key": self.a_document(), "url": "https://drive.google.com/x", "set_by": "Lina"})
        after = self.register()
        self.assertEqual(states(before), states(after))
        self.assertEqual(before["finding_counts"], after["finding_counts"])
        self.assertEqual(before["freshness"]["state"], after["freshness"]["state"])

    def test_the_contract_column_never_says_not_assessed(self):
        for c in self.register()["commitments"]:
            if "contract" in c:
                self.assertNotEqual(c["contract"], "Not assessed")


class TestHandoverComplete(HandoverCase):
    def test_completion_needs_the_deal_signed(self):
        self.both_notes()
        r = self.post("/api/deals/harbour_bank/handover/complete", {"completed_by": "Sam (delivery)"})
        self.assertEqual(r.status_code, 409)
        self.assertIn("signed", r.json()["detail"])
        self.assertEqual(self.post("/api/deals/harbour_bank/signature", {"signed_on": "2999-01-01", "recorded_by": "x"}).status_code, 400)
        self.sign()
        stage = self.register()["stage"]
        self.assertEqual((stage["current"], stage["basis"]), ("signed", "signature"))
        self.assertEqual(self.post("/api/deals/harbour_bank/signature", {"signed_on": "2026-10-15", "recorded_by": "x"}).status_code, 409)
        self.assertEqual(self.post("/api/deals/harbour_bank/handover/complete", {"completed_by": "Sam (delivery)"}).status_code, 200)

    def test_completion_needs_both_notes(self):
        self.sign()
        r = self.post("/api/deals/harbour_bank/handover/complete", {"completed_by": "Sam (delivery)"})
        self.assertEqual(r.status_code, 409)
        self.assertIn("note", r.json()["detail"])

    def test_completion_freezes_the_deal_against_every_change(self):
        issue = self.first_open_issue()
        self.post("/api/deals/harbour_bank/seen", {"issue_id": issue, "seen_by": "Lina"})
        self.both_notes()
        self.sign()
        done = self.post("/api/deals/harbour_bank/handover/complete", {"completed_by": "Sam (delivery)"})
        self.assertEqual(done.status_code, 200, done.text)
        body = done.json()
        self.assertTrue(body["complete"])
        snap = body["snapshot"]
        self.assertEqual(snap["completed_by"], "Sam (delivery)")
        self.assertEqual(snap["notes"]["delivery"]["by"], "Sam (delivery)")
        self.assertTrue(snap["open_items"])
        self.assertIn("Lina", [s["by"] for it in snap["open_items"] for f in it["findings"] for s in f["seen"]])

        for path, payload in [
            ("/api/deals/harbour_bank/seen", {"issue_id": issue, "seen_by": "Late"}),
            ("/api/deals/harbour_bank/handover/notes", {"role": "sales", "note": "x", "entered_by": "y"}),
            ("/api/deals/harbour_bank/documents/link", {"source_key": self.a_document(), "url": "https://x.y", "set_by": "y"}),
            ("/api/deals/harbour_bank/handover/complete", {"completed_by": "again"}),
            ("/api/deals/harbour_bank/signature", {"signed_on": "2026-10-14", "recorded_by": "y"}),
            ("/api/deals/harbour_bank/note", {"note": "x", "entered_by": "y"}),
            ("/api/deals/harbour_bank/decisions", {"kind": "must_fix", "issue_id": issue, "by": "y", "reason": "z"}),
            ("/api/deals/harbour_bank/review", {}),
        ]:
            r = self.post(path, payload)
            self.assertEqual(r.status_code, 409, path)
        view = self.client.get("/api/deals/harbour_bank/handover")
        self.assertEqual(view.status_code, 200)
        self.assertEqual(view.json()["snapshot"], snap)
        self.assertRegex(view.json()["fingerprint"], r"^[0-9a-f]{64}$")
        self.assertEqual(view.json()["fingerprint"], self.client.get("/api/deals/harbour_bank/handover").json()["fingerprint"])
        self.assertTrue(all("told_in" in it and "contract_detail" in it for it in snap["open_items"]))
        self.assertTrue(self.register()["handover"]["complete"])


class TestNotesOnGaps(HandoverCase):
    def test_a_note_on_a_gap_keeps_it_open_and_is_frozen_with_the_record(self):
        issue = self.first_open_issue()
        before = self.register()["finding_counts"]["unresolved"]
        r = self.post("/api/deals/harbour_bank/decisions", {"kind": "okay_to_proceed", "issue_id": issue, "by": "Sam (delivery)",
                                                            "reason": "Delivery will raise it at kick-off."})
        self.assertEqual(r.status_code, 200, r.text)
        reg = self.register()
        self.assertEqual(reg["finding_counts"]["unresolved"], before)  # a note is not a fix
        item = next(i for c in reg["commitments"] for i in c["issues"] if i["id"] == issue)
        self.assertEqual((item["state"] != "Resolved", item["decision"]["status"], item["decision"]["by"]), (True, "okay", "Sam (delivery)"))
        self.both_notes()
        self.sign()
        snap = self.post("/api/deals/harbour_bank/handover/complete", {"completed_by": "Sam (delivery)"}).json()["snapshot"]
        notes = [f["note"] for it in snap["open_items"] for f in it["findings"] if f["note"]]
        self.assertIn({"by": "Sam (delivery)", "reason": "Delivery will raise it at kick-off.", "current": True}, notes)


class TestResolvedByNote(HandoverCase):
    def open_promise(self):
        reg = self.register()
        c = next(c for c in reg["commitments"] if c["id"] in reg["open_rows"])
        return c, [i["id"] for i in c["issues"] if i["state"] != "Resolved"]

    def test_a_note_resolution_leaves_the_open_list_everywhere_but_is_never_called_closed(self):
        before = self.register()
        hb = lambda: next(d for d in self.client.get("/api/workspace/deals").json()["deals"] if d["deal"] == "harbour_bank")
        gaps_before = hb()["open_gaps"]
        c, ids = self.open_promise()
        r = self.post("/api/deals/harbour_bank/resolve-note", {"issue_ids": ids, "resolved_by": "Sam (delivery)",
                                                               "reason": "Customer agreed on the 14 Oct call."})
        self.assertEqual(r.status_code, 200, r.text)
        after = self.register()
        self.assertNotIn(c["id"], after["open_rows"])
        self.assertIn(c["id"], after["noted_rows"])
        self.assertEqual(hb()["open_gaps"], gaps_before - 1)
        self.assertEqual(states(before), states(after))  # the documents' verdict is untouched: still open by the documents
        self.assertFalse(any(i["id"] in ids for x in after["resolved_findings"] for i in [{"id": x["issue_id"]}]))
        item = next(i for cc in after["commitments"] for i in cc["issues"] if i["id"] == ids[0])
        self.assertEqual((item["note_resolution"]["by"], item["note_resolution"]["current"]), ("Sam (delivery)", True))

    def test_a_document_change_reopens_it_until_someone_reconfirms(self):
        c, ids = self.open_promise()
        self.post("/api/deals/harbour_bank/resolve-note", {"issue_ids": ids, "resolved_by": "Sam", "reason": "Agreed on a call."})
        self.assertIn(c["id"], self.register()["noted_rows"])
        key = self.a_document()
        self.post("/api/deals/harbour_bank/documents/include", {"source_key": key, "included": False})
        reg = self.register()
        self.assertNotIn(c["id"], reg["noted_rows"])
        item = next(i for cc in reg["commitments"] for i in cc["issues"] if i["id"] == ids[0])
        self.assertFalse(item["note_resolution"]["current"])

    def test_it_is_frozen_apart_from_the_open_gaps(self):
        c, ids = self.open_promise()
        self.post("/api/deals/harbour_bank/resolve-note", {"issue_ids": ids, "resolved_by": "Sam", "reason": "Agreed on a call."})
        self.both_notes()
        self.sign()
        snap = self.post("/api/deals/harbour_bank/handover/complete", {"completed_by": "Sam"}).json()["snapshot"]
        self.assertIn(c["name"], [x["promise"] for x in snap["resolved_by_note"]])
        self.assertNotIn(c["name"], [x["promise"] for x in snap["open_items"]])


class TestDealList(HandoverCase):
    def test_each_deal_shows_stage_last_update_and_handover_flags(self):
        deals = self.client.get("/api/workspace/deals").json()["deals"]
        hb = next(d for d in deals if d["deal"] == "harbour_bank")
        for field in ("stage", "stage_label", "owner", "last_updated", "in_handover", "handover_complete"):
            self.assertIn(field, hb)
        self.assertTrue(hb["in_handover"])  # draft SOW in the deal: Contracting
        self.assertFalse(hb["handover_complete"])
        self.assertIsNotNone(hb["last_updated"])

    def test_the_list_counts_open_gaps_per_promise_like_the_stage_bar(self):
        hb = next(d for d in self.client.get("/api/workspace/deals").json()["deals"] if d["deal"] == "harbour_bank")
        reg = self.register()
        promises = sum(1 for c in reg["commitments"] if any(i["state"] != "Resolved" for i in c["issues"]))
        self.assertEqual(hb["open_gaps"], promises)  # the stage-bar match is checked on v2 deals in test_one_truth


if __name__ == "__main__":
    unittest.main()
