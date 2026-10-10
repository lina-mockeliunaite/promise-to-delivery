"""The security-questionnaire fixture (10 Oct): extraction only, never in the ledger or the UI, labels quote the document."""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import check_quotes
import config
import evaluate


class TestQuestionnaireFixture(unittest.TestCase):
    def test_allowed_for_extraction_but_never_in_the_ledger_or_the_ui(self):
        self.assertIn("questionnaire_cases", config.ALLOWED_DEALS)
        self.assertNotIn("questionnaire_cases", config.LEDGER_DEALS)
        self.assertNotIn("questionnaire_cases", config.UI_DEALS)

    def test_the_document_is_an_extracted_type_and_every_label_quotes_it_word_for_word(self):
        manifest = json.loads((config.deal_dir("questionnaire_cases") / "docs" / "manifest.json").read_text(encoding="utf-8"))
        doc = manifest["documents"][0]
        self.assertIn(doc["doc_type"], config.EXTRACTABLE_DOC_TYPES)
        text = check_quotes.normalise((config.deal_dir("questionnaire_cases") / "docs" / doc["file"]).read_text(encoding="utf-8"))
        labels, _ = evaluate.load_labels("questionnaire_cases")
        self.assertEqual(len(labels), 8)
        self.assertEqual(sum(1 for l in labels if l["language"] == "firm"), 7)
        for l in labels:
            self.assertIn(check_quotes.normalise(l["quote"]), text, l["id"])


if __name__ == "__main__":
    unittest.main()
