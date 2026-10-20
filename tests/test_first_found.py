"""The origin line is deterministic (20 Oct): the earliest dated checked document that contains one of the commitment's exact
quoted sentences, under the verifier's normalisation. A paraphrase elsewhere does not count. Read-time only."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
import detect_v2
import ledger
import reset_demo
import workspace

SENTENCE = "A dedicated Aivuna launch specialist will work with Noma Journeys for the first 30 days after launch at no extra charge."


def doc(key, date, text, label="Proposal"):
    return {"key": key, "date": date, "label": label, "norm": detect_v2._n(text)}


class TestFirstFound(unittest.TestCase):
    def c(self, *quotes):
        return {"statements": [{"quote": q} for q in quotes]}

    def test_the_earliest_dated_document_with_the_sentence_wins_whatever_document_the_model_quoted(self):
        docs = [doc("NJ-04", "2026-10-05", SENTENCE), doc("NJ-03", "2026-09-28", SENTENCE, "RFP response")]
        self.assertEqual(workspace.first_found(self.c(SENTENCE), docs), {"doc_type_label": "RFP response", "date": "2026-09-28"})

    def test_a_paraphrase_elsewhere_does_not_count(self):
        call = doc("NJ-01", "2026-09-14", "A dedicated Aivuna launch specialist will work with your team for the first 30 days "
                                          "after launch, at no extra charge.", "Call transcript")
        rfp = doc("NJ-03", "2026-09-28", SENTENCE, "RFP response")
        self.assertEqual(workspace.first_found(self.c(SENTENCE), [call, rfp])["doc_type_label"], "RFP response")

    def test_the_verifiers_normalisation_applies_case_and_whitespace_and_nothing_more(self):
        messy = doc("A", "2026-09-01", SENTENCE.upper().replace(" ", "  ").replace("JOURNEYS", "JOURNEYS\n"))
        self.assertEqual(workspace.first_found(self.c(SENTENCE), [messy])["date"], "2026-09-01")
        curly = doc("B", "2026-09-02", "Elva’s assistant will answer guests’ phone calls.")
        self.assertIsNone(workspace.first_found(self.c("Elva's assistant will answer guests' phone calls."), [curly]))  # same strictness as the verifier: a different apostrophe is a different sentence

    def test_any_of_the_commitments_quotes_may_match_and_the_earliest_across_them_wins(self):
        other = "Aivuna will support guest conversations in 12 languages from the 1 February 2027 launch."
        docs = [doc("P", "2026-10-05", other), doc("R", "2026-09-28", SENTENCE, "RFP response")]
        self.assertEqual(workspace.first_found(self.c(other, SENTENCE), docs)["date"], "2026-09-28")

    def test_the_same_date_is_broken_by_the_source_key_so_the_answer_never_flips(self):
        docs = [doc("B", "2026-10-01", SENTENCE, "Proposal"), doc("A", "2026-10-01", SENTENCE, "RFP response")]
        self.assertEqual(workspace.first_found(self.c(SENTENCE), docs)["doc_type_label"], "RFP response")
        self.assertEqual(workspace.first_found(self.c(SENTENCE), list(reversed(docs)))["doc_type_label"], "RFP response")

    def test_no_match_or_no_quote_gives_none_so_the_screens_fall_back(self):
        self.assertIsNone(workspace.first_found(self.c(SENTENCE), [doc("X", "2026-09-01", "Something else entirely.")]))
        self.assertIsNone(workspace.first_found(self.c(), [doc("X", "2026-09-01", SENTENCE)]))
        self.assertIsNone(workspace.first_found({"statements": [{"quote": ""}]}, [doc("X", "2026-09-01", SENTENCE)]))
        self.assertIsNone(workspace.first_found(self.c(SENTENCE), []))


class TestOnTheFiveDeals(unittest.TestCase):
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

    def earliest_statement(self, c):
        st = [s for s in c["statements"] if s.get("doc_type_label")]
        return min(st, key=lambda s: s.get("date") or "9999")

    def test_only_the_launch_specialist_row_changes_and_it_moves_to_the_rfp_response(self):
        changed = []
        for slug in config.UI_DEALS:
            for c in workspace.overview(self.conn, slug)["commitments"]:
                found, old = c["first_found"], self.earliest_statement(c)
                self.assertIsNotNone(found, (slug, c["name"]))
                if (found["doc_type_label"], found["date"]) != (old["doc_type_label"], old["date"]):
                    changed.append((slug, c["display_name"], found["doc_type_label"], found["date"], old["doc_type_label"], old["date"]))
        self.assertEqual(changed, [("noma_journeys", "Dedicated launch specialist for the first 30 days, at no extra charge",
                                    "RFP response", "2026-09-28", "Proposal", "2026-10-05")])

    def test_the_discovery_call_paraphrase_is_not_the_origin(self):
        c = next(c for c in workspace.overview(self.conn, "noma_journeys")["commitments"] if "specialist" in c["name"])
        self.assertNotEqual(c["first_found"]["doc_type_label"], "Call transcript")

    def test_new_snapshots_store_it_and_it_is_the_same_answer_the_live_page_gives(self):
        import handover
        snap = handover.build_snapshot(self.conn, "noma_journeys", "Priya Nair")
        live = {c["name"]: c["first_found"] for c in workspace.overview(self.conn, "noma_journeys")["commitments"]}
        self.assertTrue(snap["open_items"])
        for item in snap["open_items"]:
            self.assertEqual(item["first_found"], live[item["promise"]])
        specialist = next(i for i in snap["open_items"] if "specialist" in i["promise"].lower())
        self.assertEqual(specialist["first_found"], {"doc_type_label": "RFP response", "date": "2026-09-28"})
        self.assertNotIn("source_key", json.dumps(snap["open_items"][0]["first_found"]))

    def test_it_is_read_time_only_the_register_the_handoff_reads_has_no_such_field(self):
        reg = workspace.register(self.conn, "noma_journeys")
        self.assertTrue(all("first_found" not in c for c in reg["commitments"]))


class TestTheStageBarAgreesWithTheOriginLine(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        db = Path(tmp.name) / "l.sqlite"
        reset_demo.reset(db_path=db)
        self.conn = ledger.connect(db)
        self.addCleanup(self.conn.close)

    def bar(self):
        import deal_stage
        return {s["key"]: s["gaps_started"] for s in deal_stage.deal_stage(self.conn, "noma_journeys")["stages"] if s["gaps_started"]}

    def test_every_gap_starts_where_the_origin_line_says(self):
        self.assertEqual(self.bar(), {"proposal": 3})  # all three promises were first found in the RFP response (28 Sep)

    def test_when_an_earlier_document_contains_the_exact_sentence_both_move_together(self):
        import ledger_fixes
        call = (config.doc_path("noma_journeys", "NJ-01_discovery_call.md")).read_text(encoding="utf-8")
        ledger_fixes.add_source_version(self.conn, "noma_journeys", "NJ-01", call + "\n**Liam Hart:** " + SENTENCE + "\n", "NJ-01_v2.md")
        c = next(c for c in workspace.overview(self.conn, "noma_journeys")["commitments"] if "specialist" in c["name"])
        self.assertEqual((c["first_found"]["doc_type_label"], c["first_found"]["date"]), ("Call transcript", "2026-09-14"))
        self.assertEqual(self.bar(), {"discovery": 1, "proposal": 2})

    def test_a_paraphrase_in_an_earlier_document_moves_neither(self):
        # the discovery call already holds the paraphrase of the specialist promise, and the bar still starts it at the RFP stage
        self.assertEqual(self.bar().get("discovery"), None)


if __name__ == "__main__":
    unittest.main()
