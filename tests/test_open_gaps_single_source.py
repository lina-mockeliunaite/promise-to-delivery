"""Every count of open gaps goes through open_gaps.rows, which includes the signed-contract overlay (21 Oct).

Two guards. A static one: no module computes "not Resolved" in SQL itself, and no new module reads issue_current_state without being
listed here (so a new count cannot quietly bypass the overlay). A behavioural one: with the shared function replaced by "nothing is
open", every count that should depend on it goes to zero, and with a reopened gap in place all the counts agree."""

import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import deal_stage
import handover
import integrity
import ledger_fixes
import open_gaps
import workspace
from test_signed_check import NJ9_FOUR, Replay

ROOT = Path(__file__).resolve().parents[1]
# Modules that read issue_current_state, and why that is allowed. Anything not listed fails the test: read this list before adding to it.
ALLOWED_STATE_READERS = {
    "open_gaps.py": "the shared reading of which gaps are open",
    "signed_check.py": "finds the gaps closed by documents, to check them against signed paperwork",
    "workspace.py": "reads each issue's own state to build the register, then applies open_gaps.effective_state",
    "handover.py": "resolve_by_note: a note can settle an open gap (and a reopened one) but not a closed one",
    "finding_check.py": "compares each issue's state before and after a fix, to report what the fix closed (a ledger transition, not a count)",
    "ledger_v2.py": "inside the config hash: the review itself, which writes the ledger's states",
    "recheck.py": "inside the config hash: the recheck, which writes the ledger's states",
}


def modules():
    return [p for p in sorted(ROOT.glob("*.py")) if not p.name.startswith("scratch")]


class TestNoCountBypassesTheSharedFunction(unittest.TestCase):
    def test_no_module_but_open_gaps_computes_not_resolved_in_sql(self):
        offenders = []
        for p in modules():
            for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                if re.search(r"(<>|!=)\s*'Resolved'", line) and p.name != "open_gaps.py":
                    offenders.append(f"{p.name}:{n}: {line.strip()[:100]}")
        self.assertEqual(offenders, [], "count open gaps through open_gaps.rows, which includes the signed-contract overlay")

    def test_no_unlisted_module_reads_issue_current_state(self):
        readers = {p.name for p in modules() if "issue_current_state" in p.read_text(encoding="utf-8")}
        self.assertEqual(sorted(readers - set(ALLOWED_STATE_READERS)), [],
                         "a module reads issue_current_state: use open_gaps, or list it in ALLOWED_STATE_READERS with the reason")
        self.assertEqual(sorted(set(ALLOWED_STATE_READERS) - readers), [], "an allowed reader no longer reads it: remove it from the list")

    def test_the_consumers_import_the_shared_function(self):
        for name in ("workspace.py", "handover.py", "deal_stage.py", "integrity.py"):
            self.assertIn("open_gaps", (ROOT / name).read_text(encoding="utf-8"), name)


class TestTheCountsAgreeAndDependOnIt(Replay):
    def reopened_deal(self):
        for key, name in (("NJ-05", "NJ-05_v2_named_exception.md"), ("NJ-07", "NJ-07_v2_languages_aligned.md")):
            self.filed(key, name)
        self.sign(NJ9_FOUR)  # the fix never reached the signed agreement: one closed gap is open again
        return ledger_fixes.deal_id(self.conn, self.deal)

    def counts(self, did):
        row = {r["deal"]: r for r in handover.deal_rows(self.conn, workspace.deal_list(self.conn))}[self.deal]
        listed = {r["deal"]: r for r in workspace.deal_list(self.conn)}[self.deal]
        ov = workspace.overview(self.conn, self.deal)
        return {
            "deal_list issues": listed["open_issues"],
            "deal_rows promises": row["open_gaps"],
            "stage bar promises": sum(s["gaps_started"] for s in deal_stage.deal_stage(self.conn, self.deal)["stages"]),
            "overview open rows": len(ov["open_rows"]),
            "overview unresolved issues": ov["finding_counts"]["unresolved"],
            "register open issues": sum(1 for c in ov["commitments"] for i in c["issues"] if i["state"] != "Resolved"),
        }

    def test_with_a_reopened_gap_every_count_agrees_with_the_shared_function(self):
        did = self.reopened_deal()
        n_issues, n_promises = open_gaps.count(self.conn, did), len(open_gaps.commitment_ids(self.conn, did))
        got = self.counts(did)
        self.assertEqual(got["deal_list issues"], n_issues)
        self.assertEqual(got["overview unresolved issues"], n_issues)
        self.assertEqual(got["register open issues"], n_issues)
        for name in ("deal_rows promises", "stage bar promises", "overview open rows"):
            self.assertEqual(got[name], n_promises, name)
        # and the reopened gap really is in the count: one more open promise than before the signed contract
        languages = next(c for c in workspace.overview(self.conn, self.deal)["commitments"] if "12 languages" in c["name"])
        self.assertIn(languages["id"], open_gaps.commitment_ids(self.conn, did))

    def test_replacing_the_shared_function_with_nothing_open_zeroes_every_count_that_uses_it(self):
        did = self.reopened_deal()
        self.assertGreater(open_gaps.count(self.conn, did), 0)
        with mock.patch.object(open_gaps, "rows", lambda conn, did, slug=None: []):
            listed = {r["deal"]: r for r in workspace.deal_list(self.conn)}[self.deal]
            row = {r["deal"]: r for r in handover.deal_rows(self.conn, workspace.deal_list(self.conn))}[self.deal]
            stage = deal_stage.deal_stage(self.conn, self.deal)
            self.assertEqual(listed["open_issues"], 0, "workspace.deal_list counts open gaps without the shared function")
            self.assertEqual(row["open_gaps"], 0, "handover.deal_rows counts open gaps without the shared function")
            self.assertEqual(sum(s["gaps_started"] for s in stage["stages"]), 0, "the stage bar counts open gaps without the shared function")
            ok, _ = integrity.is_current(self.conn, did)
            if ok:  # the decision summary lists open gaps only while the review is current
                self.assertEqual(integrity.decision_summary(self.conn, self.deal)["items"], [])


if __name__ == "__main__":
    unittest.main()
