"""workspace.plain turns a document's file name inside a stored sentence into the document's plain label (31 Oct).

ledger_v2.py (in the config hash) writes "...is no longer in NJ-07_draft_contract.md." when the key it captured is the file name;
the register, the handoff exports and the locked record read that sentence through plain(), so the rewrite lives here."""
import unittest

import workspace

NAMES = {"NJ-07": "Draft contract", "NJ-05": "Internal approvals note", "NJ-1": "Call transcript"}


class PlainFileNames(unittest.TestCase):
    def test_a_file_name_becomes_the_documents_label(self):
        out = workspace.plain("Closed: the contract clause behind this conflict is no longer in NJ-07_draft_contract.md.", NAMES)
        self.assertEqual(out, "Closed: the contract clause behind this conflict is no longer in Draft contract.")

    def test_other_extensions_and_a_key_alone(self):
        self.assertEqual(workspace.plain("see NJ-05_v2_named_exception.docx and NJ-05.", NAMES), "see Internal approvals note and Internal approvals note.")

    def test_a_file_name_of_an_unknown_document_is_left_alone_and_a_longer_key_wins(self):
        self.assertEqual(workspace.plain("in XX-01_notes.md", NAMES), "in XX-01_notes.md")
        self.assertEqual(workspace.plain("in NJ-1_call.md", NAMES), "in Call transcript")

    def test_text_without_a_file_name_is_unchanged(self):
        text = "The approvals note now records an approval."
        self.assertEqual(workspace.plain(text, NAMES), text)


if __name__ == "__main__":
    unittest.main()
