"""Adding output fields to signed_check.py changed no verdict (11 Nov). tests/fixtures/signed_verdicts_golden.json was written from the code before the change, for all five
deals in three states each (a signed agreement as shipped, one that repeats every draft sentence, one that repeats none): confirmed, not found and not confirmed. Every
pre-existing key of every verdict must still be identical; only new keys may appear. See signed_verdict_matrix.py."""

import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import signed_verdict_matrix as m

GOLDEN = json.loads((Path(__file__).parent / "fixtures" / "signed_verdicts_golden.json").read_text(encoding="utf-8"))


class TestVerdictsUnchanged(unittest.TestCase):
    def test_every_verdict_for_all_five_deals_is_identical_to_before(self):
        self.assertEqual(sorted(GOLDEN), sorted(f"{d}/{v}" for d in m.DEALS for v in ("shipped", "full", "bare")))
        # the stored closing text carries the day the gap was checked ("... unchanged \u00b7 11 Nov 2026"): the matrix runs fresh each day, so that date is not compared
        norm = lambda d: json.loads(re.sub(r"\d{1,2} [A-Z][a-z]{2} 2026\"", '<day>"', json.dumps(d)))
        now = norm(json.loads(json.dumps(m.matrix())))  # the file stores tuples as lists
        statuses = set()
        for key, before in norm(GOLDEN).items():
            self.assertEqual(now[key], before, key)  # the accepted documents, and every verdict key as it was
            statuses |= {v["status"] for k, v in before.items() if k != "_steps"}
        self.assertEqual(statuses, {"confirmed", "not_found", "not_confirmed"})  # all three outcomes are covered

    def test_the_golden_file_covers_each_outcome_on_the_demo_deals(self):
        self.assertEqual([v["status"] for k, v in GOLDEN["noma_journeys/shipped"].items() if k != "_steps"], ["confirmed"])
        self.assertEqual([v["status"] for k, v in GOLDEN["alder_bank/shipped"].items() if k != "_steps"], ["not_found"])
        self.assertEqual([v["status"] for k, v in GOLDEN["harbour_bank/bare"].items() if k != "_steps"], ["not_confirmed"])
        for deal in ("coral_pay", "atlas_remit"):  # no gap was closed by a contract or SOW: nothing to check, before and after
            self.assertEqual([k for k in GOLDEN[f"{deal}/shipped"] if k != "_steps"], [])

    def test_new_fields_are_additions_only(self):
        import signed_check
        src = Path(signed_check.__file__).read_text(encoding="utf-8")
        self.assertIn('"signed_sentence": locate(hit["text"], lookup["quote"])', src)
        for key in m.KEYS:
            self.assertIn(f'"{key}"', src)  # the verdict keys are all still produced


if __name__ == "__main__":
    unittest.main()
