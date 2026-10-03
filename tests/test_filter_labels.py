"""Labels vs the sales-housekeeping filter. This is the only place labels are read for the filter.

Labels score the filter; they never shape it. Each labelled statement is matched to a frozen-run statement with the
same one-to-one matcher evaluate.py uses, then the filter's decision on that statement is checked. If this test
fails, the fix is a general rule change, never a special case for a label or a Harbour Bank sentence.
"""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
import evaluate
import sales_filter
import terms

VOCAB = terms.build_vocabulary(json.loads((config.DATA_DIR / "catalogue.json").read_text(encoding="utf-8")))
DEALS = ("harbour_bank", "hard_cases")


def matched(slug):
    """{label id: (label, run statement)} for the labels the matcher pairs with a statement in the frozen run."""
    run = json.loads((config.RESULTS_DIR / config.LEDGER_IMPORT_RUN_FILES[slug]).read_text(encoding="utf-8"))
    outputs = [s for d in run["documents"] for s in d["statements"]]
    labels, _ = evaluate.load_labels(slug)
    result = evaluate.assign(labels, outputs, config.MATCH_THRESHOLD, config.NEAR_MISS_FLOOR)
    return {l["id"]: (l, o) for _, l, o in result["matches"]}, result["unmatched_labels"]


class TestFilterAgainstLabels(unittest.TestCase):
    def test_no_labelled_statement_is_dropped_on_either_deal(self):
        dropped = []
        for slug in DEALS:
            pairs, _ = matched(slug)
            for label_id, (label, statement) in pairs.items():
                decision = sales_filter.classify(statement["quote"], VOCAB)
                if not decision.kept:
                    dropped.append(f"{slug} {label_id} = {statement['statement_id']} dropped by {decision.rule}")
        self.assertEqual(dropped, [], "labelled statements dropped by the filter")

    def test_label_s15_the_weekly_status_meeting_is_kept(self):
        pairs, _ = matched("harbour_bank")
        self.assertIn("S15", pairs, "label S15 was not matched to a statement in the frozen run")
        label, statement = pairs["S15"]
        self.assertIn("status meeting", label["quote"])
        self.assertEqual(statement["statement_id"], "HB-06-S03")
        self.assertTrue(sales_filter.classify(statement["quote"], VOCAB).kept)

    def test_every_dropped_statement_is_unlabelled(self):
        """The same check from the other side: list every dropped statement and whether a label matched it."""
        labelled = {}
        for slug in DEALS:
            pairs, _ = matched(slug)
            labelled[slug] = {o["statement_id"] for _, o in pairs.values()}
            run = json.loads((config.RESULTS_DIR / config.LEDGER_IMPORT_RUN_FILES[slug]).read_text(encoding="utf-8"))
            for d in run["documents"]:
                for s in d["statements"]:
                    if not sales_filter.classify(s["quote"], VOCAB).kept:
                        self.assertNotIn(s["statement_id"], labelled[slug], s["statement_id"])


if __name__ == "__main__":
    unittest.main()
