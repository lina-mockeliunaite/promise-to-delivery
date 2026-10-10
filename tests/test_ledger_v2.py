"""v2 in the app: seeded first review, then fix -> recheck -> close by re-verifying the stored claim. No real model."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
import finding_check
import handoff
import ledger
import ledger_v2
import recheck
import workspace
import workspace_records

SCEN = config.ROOT / "data" / "scenarios"


class FakeClient:
    """Returns the given findings; counts calls."""
    def __init__(self, findings):
        self.findings, self.calls = findings, 0
        self.messages = NS(create=self.create)

    def create(self, **kw):
        self.calls += 1
        return NS(content=[NS(type="text", text=json.dumps({"findings": self.findings}))], stop_reason="end_turn",
                  usage=NS(input_tokens=100, output_tokens=50, output_tokens_details=None))


class V2Case(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        p = mock.patch.object(config, "V2_CACHE_DIR", self.dir / "cache")
        p.start()
        self.addCleanup(p.stop)
        self.built = ledger_v2.build(self.dir / "l.sqlite")
        self.conn = ledger.connect(self.dir / "l.sqlite")
        self.addCleanup(self.conn.close)

    def issues(self, slug):
        """{(commitment name, finding label): state}"""
        out = {}
        for c in workspace.overview(self.conn, slug)["commitments"]:
            for i in c["issues"]:
                out[(c["name"], i["finding"])] = (i["state"], i["id"], i["reason"])
        return out

    def find(self, slug, word, finding):
        for (name, f), (state, iid, _) in self.issues(slug).items():
            if word.lower() in name.lower() and f == finding:
                return iid, state
        raise AssertionError(f"no {finding} on a commitment naming {word}: {list(self.issues(slug))}")

    def attach(self, slug, iid, path, doc_type, source_key=None, client=None, name=None):
        text = Path(path).read_text(encoding="utf-8")
        return finding_check.check(self.conn, slug, iid, confirmed_doc_type=doc_type, filename=Path(path).name, text=text,
                                   source_key=source_key, name=name, signed_off_by="Daniel Koh", client=client,
                                   doc_date=None if source_key else "2026-10-12")


class TestBuild(V2Case):
    def test_seeded_reset_makes_no_model_call_and_every_finding_verifies(self):
        self.assertEqual({s: r["model_calls"] for s, r in self.built.items()}, {s: 0 for s in config.V2_DEALS})
        self.assertEqual({s: r["rejected"] for s, r in self.built.items()}, {s: 0 for s in config.V2_DEALS})
        self.assertEqual({s: r["origin"] for s, r in self.built.items()}, {s: "seed" for s in config.V2_DEALS})
        counts = {s: workspace.overview(self.conn, s)["finding_counts"]["unresolved"] for s in config.V2_DEALS}
        self.assertEqual(counts, {"harbour_bank": 6, "coral_pay": 3, "atlas_remit": 7})

    def test_every_deal_is_current_so_decisions_can_be_made(self):
        for s in config.V2_DEALS:
            o = workspace.overview(self.conn, s)
            self.assertTrue(o["can_decide"], s)
            self.assertEqual(o["freshness_label"], "Up to date")

    def test_issues_are_raised_by_model_v2_with_the_verified_claim_as_closure_criteria(self):
        rows = self.conn.execute("SELECT raised_by, closure_criteria FROM issues").fetchall()
        self.assertTrue(rows)
        for by, crit in rows:
            self.assertEqual(by, "model_v2")
            self.assertIn("promise_quotes", json.loads(crit)["claim"])

    def test_an_unchanged_rerun_uses_the_cache_and_changes_nothing(self):
        before = self.issues("harbour_bank")
        r = recheck.recheck(self.conn, "harbour_bank", None, None)
        self.assertEqual(r["model_calls"], 0)
        self.assertIn(r["origin"], ("cache", "previous_review"))
        self.assertEqual({k: v[0] for k, v in self.issues("harbour_bank").items()}, {k: v[0] for k, v in before.items()})

    def test_statements_show_each_promise_with_its_source(self):
        c = next(c for c in workspace.overview(self.conn, "harbour_bank")["commitments"] if "Polygon" in c["name"])
        self.assertTrue(any("Polygon" in s["quote"] for s in c["statements"]))
        self.assertEqual(c["told"], "real-time")


class TestFixAndRecheck(V2Case):
    def test_a_named_exception_closes_only_the_approval_finding_and_needs_no_model(self):
        iid, state = self.find("harbour_bank", "Polygon", "No approval recorded")
        self.assertEqual(state, "Needs action")
        out = self.attach("harbour_bank", iid, SCEN / "HB-05_v2_named_exception.md", "pricing_services_note", source_key="HB-05")
        self.assertEqual(out["this_finding"], "Resolved")
        self.assertEqual(out["model_calls"], 0)
        state, _, reason = self.issues("harbour_bank")[next(k for k in self.issues("harbour_bank") if k[0].count("Polygon") and k[1] == "No approval recorded")]
        self.assertIn("Daniel Koh", reason)
        # the conflict on the same promise and the other deals' approvals stay open
        _, conflict = self.find("harbour_bank", "Polygon", "Contract says something different")
        self.assertEqual(conflict, "Needs action")
        _, vasp = self.find("harbour_bank", "VASP", "No approval recorded")
        self.assertEqual(vasp, "Needs action")
        resolved = workspace.overview(self.conn, "harbour_bank")["resolved_findings"]
        self.assertIn("Pricing and services note, version 2", resolved[0]["resolved_by"])
        self.assertNotIn("Proposal", resolved[0]["resolved_by"])  # only the document that closed it
        self.assertNotIn("RFP", resolved[0]["resolved_by"])

    def test_an_aligned_sow_needs_the_model_and_refuses_without_a_key(self):
        iid, _ = self.find("harbour_bank", "Polygon", "Contract says something different")
        with self.assertRaises(finding_check.CheckError) as cm:
            self.attach("harbour_bank", iid, SCEN / "HB-06_v2_annex_aligned.md", "draft_sow", source_key="HB-06")
        self.assertEqual(cm.exception.status, 409)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM source_versions").fetchone()[0],
                         sum(1 for _ in self.conn.execute("SELECT id FROM sources")))  # nothing was saved

    def test_an_aligned_sow_closes_the_conflict_by_reverifying_the_stored_claim(self):
        iid, _ = self.find("harbour_bank", "Polygon", "Contract says something different")
        client = FakeClient([])  # the model finds nothing new; closure does not depend on it
        out = self.attach("harbour_bank", iid, SCEN / "HB-06_v2_annex_aligned.md", "draft_sow", source_key="HB-06", client=client)
        self.assertEqual(client.calls, 1)
        self.assertEqual(out["this_finding"], "Resolved")
        _, _, reason = next(v for k, v in self.issues("harbour_bank").items() if v[1] == iid)
        self.assertIn("contract clause", reason)
        # the approval on Polygon is not closed by aligning the SOW
        _, approval = self.find("harbour_bank", "Polygon", "No approval recorded")
        self.assertEqual(approval, "Needs action")

    def test_model_variance_never_closes_a_claim_that_still_holds(self):
        client = FakeClient([])
        iid, _ = self.find("harbour_bank", "40,000", "Missing from contract") if any("40,000" in k[0] for k in self.issues("harbour_bank")) \
            else self.find("harbour_bank", "ledger", "Missing from contract")
        # a new customer email (customer-facing: needs the model), which changes nothing about the gap
        p = self.dir / "note.md"
        p.write_text("Thanks, see you Tuesday.\n", encoding="utf-8")
        out = self.attach("harbour_bank", iid, p, "customer_email", name="Follow-up email", client=client)
        self.assertEqual(out["this_finding"], "Needs action")
        self.assertEqual(workspace.overview(self.conn, "harbour_bank")["finding_counts"]["unresolved"], 6)

    def test_an_exception_cannot_close_an_absolute_limit(self):
        iid, _ = self.find("atlas_remit", "Tron", "Not offered")
        p = self.dir / "AR-05.md"
        text = config.doc_path("atlas_remit", "AR-05_pricing_services_note.md").read_text(encoding="utf-8")
        p.write_text(text + "\n| CAP-021 On-chain wallet screening integration | Tron real-time | Not in catalogue |"
                     " Exception approved by Gabriel Tan |\n", encoding="utf-8")
        out = self.attach("atlas_remit", iid, p, "pricing_services_note", source_key="AR-05")
        self.assertEqual(out["this_finding"], "Needs action")

    def test_withdrawing_the_promise_closes_its_findings(self):
        iid, _ = self.find("atlas_remit", "Tron", "Not offered")
        text = config.doc_path("atlas_remit", "AR-04_proposal.md").read_text(encoding="utf-8")
        line = next(l for l in text.splitlines() if "Tron" in l)
        p = self.dir / "AR-04.md"
        p.write_text(text.replace(line, "Tron payouts are out of scope for this proposal."), encoding="utf-8")
        out = self.attach("atlas_remit", iid, p, "proposal", source_key="AR-04", client=FakeClient([]))
        self.assertEqual(out["this_finding"], "Resolved")
        c = next(c for c in workspace.overview(self.conn, "atlas_remit")["commitments"] if "Tron" in c["name"])
        self.assertEqual(c["status"], "Not in current documents" if not c["issues"] else c["status"])
        self.assertTrue(all(i["state"] == "Resolved" for i in c["issues"]))


class TestHumanRecordsOnV2(V2Case):
    def test_okay_to_proceed_and_handoff_work_on_v2_issues(self):
        iid, _ = self.find("coral_pay", "training", "Missing from contract")
        workspace_records.okay_to_proceed(self.conn, "coral_pay", iid, "Mei Tan", "Training added at kickoff.")
        o = workspace.overview(self.conn, "coral_pay")
        self.assertEqual(o["finding_counts"]["unresolved"], 3)  # a decision never changes a finding
        self.assertEqual(o["finding_counts"]["awaiting_decision"], 2)
        open_ids = [i["id"] for c in o["commitments"] for i in c["issues"] if i["state"] != "Resolved"]
        saved = handoff.save(self.conn, "coral_pay", "proceed", "Lina", "Demo", open_ids)
        self.assertIn("version", saved)


if __name__ == "__main__":
    unittest.main()


class TestRealModelCheckScript(unittest.TestCase):
    def test_the_check_passes_with_a_model_that_finds_nothing_new(self):
        import check_v2_app
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(config, "V2_CACHE_DIR", Path(tmp) / "cache"):
            results = check_v2_app.run(FakeClient([]), Path(tmp) / "c.sqlite")
        self.assertEqual([r[0] for r in results if not r[1]], [])
