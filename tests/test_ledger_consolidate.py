"""Tests for consolidation and the write path.

The import runs on byte-identical copies in a temporary folder into a temporary database (see test_ledger_import.py),
then consolidation runs on that database. Nothing here touches workspace/ledger.sqlite or the real coral_pay path.
Labels are read only in TestLabels, and only to check the result, never to build groups.
"""

import contextlib
import io
import json
import shutil
import sqlite3
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
import evaluate
import ledger
import ledger_consolidate
import ledger_import
import terms
from test_ledger_import import CANARY, DEALS, DECOY, REAL_DATA, REAL_RESULTS, ImportCase
from test_terms import CATALOGUE, VOCAB, synthetic_catalogue_with_usdc

GOLDEN = {
    'harbour_bank': [
        ('C01', 'On-chain wallet screening integration: Polygon, real time', ('HB-01-S01', 'HB-02-S01', 'HB-03-S01', 'HB-04-S01'), (), 'firm', 'supported'),
        ('C02', 'Go-live', ('HB-01-S03',), (), 'conditional', 'supported'),
        ('C03', 'On-chain wallet screening integration: Ethereum, real time', ('HB-03-S01', 'HB-04-S02', 'HB-06-S04'), (), 'firm', 'supported'),
        ('C04', 'Payout ledger connector: up to 12,000 payouts per day, at launch', ('HB-04-S03', 'HB-06-S01'), (), 'firm', 'supported'),
        ('C05', 'Payout ledger connector: up to 40,000 payouts per day, by end of first year', ('HB-04-S04',), (), 'firm', 'supported'),
        ('C06', 'VASP counterparty data exchange', ('HB-04-S05',), (), 'firm', 'supported'),
        ('C07', 'On-chain wallet screening integration: Ethereum [terms incomplete: mode; HB-06-S02]', ('HB-06-S02',), ('mode',), 'firm', 'supported'),
        ('C08', 'On-chain wallet screening integration: Polygon [terms incomplete: mode; HB-06-S02]', ('HB-06-S02',), ('mode',), 'firm', 'supported'),
        ('C09', 'Unclassified promise: The parties will hold a weekly project status meet [terms incomplete: capability; HB-06-S03]', ('HB-06-S03',), ('capability',), 'firm', 'supported'),
        ('C10', 'On-chain wallet screening integration: Polygon, batch', ('HB-06-S05', 'HB-06-S06'), (), 'firm', 'supported'),
    ],
    'hard_cases': [
        ('C01', 'On-chain wallet screening integration: Arbitrum [terms incomplete: mode; KR-01-S01]', ('KR-01-S01',), ('mode',), 'firm', 'supported'),
        ('C02', 'On-chain wallet screening integration: Polygon, real time', ('KR-01-S03',), (), 'conditional', 'supported'),
        ('C03', 'Go-live', ('KR-02-S01',), (), 'firm', 'supported'),
        ('C04', 'Payout ledger connector: up to 30,000 payouts per day, at launch', ('KR-02-S02', 'KR-03-S01'), (), 'firm', 'supported'),
        ('C05', 'On-chain wallet screening integration: Arbitrum, real time', ('KR-02-S03',), (), 'firm', 'supported'),
        ('C06', 'VASP counterparty data exchange', ('KR-02-S04',), (), 'conditional', 'supported'),
        ('C07', 'Case audit history', ('KR-02-S05',), (), 'firm', 'supported'),
        ('C08', 'On-chain wallet screening integration: Ethereum, real time', ('KR-03-S02',), (), 'firm', 'supported'),
    ],
}

EXPECTED_DROPPED = {
    "harbour_bank": {
        "HB-01-S02": "sales_next_call", "HB-01-S04": "sales_rfp_or_proposal_response", "HB-02-S02": "sales_walkthrough",
        "HB-03-S02": "sales_methodology", "HB-04-S06": "sales_draft_sow_to_follow",
    },
    "hard_cases": {"KR-01-S02": "sales_security_pack"},
}
CONSOLIDATED_COUNTS = {"review_statements": 30, "commitments": 18, "review_statement_commitments": 26, "commitment_assessments": 18}
CONSOLIDATION_TABLES = ("review_statements", "commitments", "review_statement_commitments", "commitment_assessments")
RANK = {"exploratory": 0, "conditional": 1, "firm": 2}


class ConsolidateCase(ImportCase):
    """An imported database with the catalogue beside it, not yet consolidated."""

    def setUp(self):
        super().setUp()
        shutil.copyfile(REAL_DATA / "catalogue.json", self.data / "catalogue.json")
        ledger_import.import_all(self.conn)

    def consolidation_counts(self):
        return {t: self.conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in CONSOLIDATION_TABLES}

    def commitments(self, slug):
        rows = []
        for cid, key, name, language, support, terms_json in self.conn.execute(
            "SELECT c.id, c.commitment_key, a.name, a.language, a.support_state, a.terms FROM commitments c"
            " JOIN commitment_assessments a ON a.commitment_id = c.id JOIN deals d ON d.id = c.deal_id"
            " WHERE d.slug = ? ORDER BY c.id", (slug,),
        ).fetchall():
            members = tuple(r[0] for r in self.conn.execute(
                "SELECT s.statement_key FROM review_statement_commitments l JOIN statements s ON s.id = l.statement_id"
                " WHERE l.commitment_id = ? ORDER BY s.id", (cid,)))
            parsed = json.loads(terms_json)
            rows.append((key, name, members, tuple(parsed["missing"]) if parsed["terms_incomplete"] else (), language, support))
        return rows

    def commitments_of(self, statement_key):
        return [r[0] for r in self.conn.execute(
            "SELECT c.commitment_key || ' ' || a.name FROM review_statement_commitments l"
            " JOIN statements s ON s.id = l.statement_id JOIN commitments c ON c.id = l.commitment_id"
            " JOIN commitment_assessments a ON a.commitment_id = c.id WHERE s.statement_key = ? ORDER BY c.id", (statement_key,))]

    def dump(self):
        return "\n".join(self.conn.iterdump())


class TestConsolidation(ConsolidateCase):
    def setUp(self):
        super().setUp()
        self.plans = ledger_consolidate.consolidate_all(self.conn)

    def test_counts(self):
        self.assertEqual(self.consolidation_counts(), CONSOLIDATED_COUNTS)
        self.assertEqual({s: len(p["commitments"]) for s, p in self.plans.items()}, {"harbour_bank": 10, "hard_cases": 8})
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM commitment_links").fetchone()[0], 0)

    def test_commitments_match_the_golden_table(self):
        for slug in DEALS:
            self.assertEqual(self.commitments(slug), GOLDEN[slug], slug)

    def test_dropped_statements_are_kept_visible_with_their_rule_and_never_linked(self):
        for slug in DEALS:
            rows = self.conn.execute(
                "SELECT s.statement_key, rs.kept, rs.filter_rule FROM review_statements rs JOIN statements s ON s.id = rs.statement_id"
                " JOIN reviews r ON r.id = rs.review_id JOIN deals d ON d.id = r.deal_id WHERE d.slug = ?", (slug,)).fetchall()
            self.assertEqual({k: rule for k, kept, rule in rows if not kept}, EXPECTED_DROPPED[slug])
            self.assertTrue(all(rule is None for k, kept, rule in rows if kept))
            self.assertEqual(len(rows), {"harbour_bank": 20, "hard_cases": 10}[slug])
            for key in EXPECTED_DROPPED[slug]:
                self.assertEqual(self.commitments_of(key), [], key)

    def test_every_kept_statement_is_linked_at_least_once(self):
        unlinked = self.conn.execute(
            "SELECT s.statement_key FROM review_statements rs JOIN statements s ON s.id = rs.statement_id WHERE rs.kept = 1"
            " AND NOT EXISTS (SELECT 1 FROM review_statement_commitments l WHERE l.review_id = rs.review_id"
            " AND l.statement_id = rs.statement_id AND l.source_version_id = rs.source_version_id)").fetchall()
        self.assertEqual(unlinked, [])

    def test_a_statement_listing_two_networks_joins_both_groups(self):
        linked = self.commitments_of("HB-03-S01")
        self.assertEqual(len(linked), 2)
        self.assertTrue(any("Polygon, real time" in c for c in linked) and any("Ethereum, real time" in c for c in linked))

    def test_a_statement_with_no_mode_gives_two_incomplete_commitments(self):
        linked = self.commitments_of("HB-06-S02")
        self.assertEqual(len(linked), 2)
        self.assertTrue(all("terms incomplete: mode" in c for c in linked))

    def test_differing_terms_are_never_merged(self):
        for slug in DEALS:
            keys = []
            for (parsed,) in self.conn.execute(
                "SELECT a.terms FROM commitment_assessments a JOIN commitments c ON c.id = a.commitment_id"
                " JOIN deals d ON d.id = c.deal_id WHERE d.slug = ?", (slug,)):
                t = json.loads(parsed)
                if t["terms_incomplete"]:
                    self.assertIsNone(t["key"])
                    self.assertEqual(len(t["members"]), 1, "an incomplete commitment holds one statement")
                else:
                    keys.append(t["key"])
                    for m in t["members"]:
                        self.assertEqual(m["term_set"]["key"], t["key"], m["statement_key"])
            self.assertEqual(len(keys), len(set(keys)), "one commitment per complete key")

    def test_real_time_and_batch_polygon_are_different_commitments(self):
        self.assertTrue(set(self.commitments_of("HB-04-S01")).isdisjoint(self.commitments_of("HB-06-S05")))
        self.assertEqual(self.commitments_of("HB-06-S05"), self.commitments_of("HB-06-S06"))

    def test_thirty_thousand_and_30000_share_a_commitment_with_both_quotes_verbatim(self):
        self.assertEqual(self.commitments_of("KR-02-S02"), self.commitments_of("KR-03-S01"))
        run = json.loads((REAL_RESULTS / config.LEDGER_IMPORT_RUN_FILES["hard_cases"]).read_text(encoding="utf-8"))
        quotes = {s["statement_id"]: s["quote"] for d in run["documents"] for s in d["statements"]}
        stored = dict(self.conn.execute(
            "SELECT statement_key, quote FROM statements WHERE statement_key IN ('KR-02-S02', 'KR-03-S01')"))
        self.assertEqual(stored, {k: quotes[k] for k in stored})
        self.assertIn("thirty thousand", stored["KR-02-S02"])
        self.assertIn("30,000", stored["KR-03-S01"])

    def test_go_live_dates_stay_attributes_of_one_commitment(self):
        (terms_json,) = self.conn.execute(
            "SELECT a.terms FROM commitment_assessments a WHERE a.name = 'Go-live' ORDER BY a.id LIMIT 1").fetchone()
        t = json.loads(terms_json)
        self.assertEqual(t["key"], terms.GO_LIVE_KEY)
        self.assertEqual(t["members"][0]["term_set"]["go_live_date"], "--12-01")

    def test_assessments_hold_only_what_this_step_decides(self):
        rows = self.conn.execute(
            "SELECT authorisation, contractual_presence, evidence_refs, authorisation_evidence, presence_detail,"
            " rationale, name FROM commitment_assessments").fetchall()
        self.assertEqual(len(rows), 18)
        for authorisation, presence, refs, auth_evidence, detail, rationale, name in rows:
            self.assertEqual((authorisation, presence, refs, auth_evidence, detail),
                             ("not_assessed", "not_assessed", None, None, None))
            self.assertTrue(name and rationale)

    def test_language_is_the_firmest_member_and_the_rationale_lists_every_member(self):
        languages = dict(self.conn.execute("SELECT statement_key, language FROM statements"))
        for slug in DEALS:
            for key, name, members, missing, language, support in GOLDEN[slug]:
                self.assertEqual(language, max((languages[m] for m in members), key=RANK.get), key)
        (rationale,) = self.conn.execute(
            "SELECT rationale FROM commitment_assessments WHERE name LIKE '%Polygon, real time' ORDER BY id").fetchone()
        for key in ("HB-01-S01", "HB-02-S01", "HB-03-S01", "HB-04-S01"):
            self.assertIn(key, rationale)

    def test_the_rules_hash_is_recorded_in_every_assessment(self):
        expected = ledger_consolidate.rules_sha256((self.data / "catalogue.json").read_bytes())
        hashes = {json.loads(t)["config_sha256"] for (t,) in self.conn.execute("SELECT terms FROM commitment_assessments")}
        self.assertEqual(hashes, {expected})
        # The build-time review was frozen by the import, so its own config_sha256 stays NULL.
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM reviews WHERE config_sha256 IS NOT NULL").fetchone()[0], 0)

    def test_the_build_time_reviews_are_unchanged(self):
        self.assertEqual(self.conn.execute("SELECT DISTINCT status FROM reviews").fetchall(), [("complete",)])


class TestRefusalsAndAtomicity(ConsolidateCase):
    def test_a_second_run_refuses_and_changes_nothing(self):
        ledger_consolidate.consolidate_all(self.conn)
        before = self.dump()
        with self.assertRaises(ledger_consolidate.ConsolidationError):
            ledger_consolidate.consolidate_all(self.conn)
        review = self.conn.execute("SELECT id FROM reviews ORDER BY id").fetchone()[0]
        with self.assertRaises(ledger_consolidate.ConsolidationError):
            ledger_consolidate.consolidate_review(self.conn, review)
        self.assertEqual(self.dump(), before)

    def test_a_failure_mid_write_rolls_everything_back(self):
        real = ledger_consolidate.plan_review

        def corrupt(*args, **kwargs):
            plan = real(*args, **kwargs)
            plan["commitments"][1]["language"] = "bogus"  # fails the CHECK after earlier rows were written
            return plan

        before = self.dump()
        with mock.patch.object(ledger_consolidate, "plan_review", corrupt):
            with self.assertRaises(sqlite3.IntegrityError):
                ledger_consolidate.consolidate_all(self.conn)
        self.assertEqual(self.dump(), before)
        self.assertEqual(sum(self.consolidation_counts().values()), 0)

    def test_consolidation_is_all_or_nothing_across_deals(self):
        real, calls = ledger_consolidate.plan_review, []

        def corrupt_second(*args, **kwargs):
            plan = real(*args, **kwargs)
            calls.append(1)
            if len(calls) == 2:
                plan["commitments"][0]["support_state"] = "bogus"
            return plan

        with mock.patch.object(ledger_consolidate, "plan_review", corrupt_second):
            with self.assertRaises(sqlite3.IntegrityError):
                ledger_consolidate.consolidate_all(self.conn)
        self.assertEqual(sum(self.consolidation_counts().values()), 0)

    def test_a_deal_with_no_build_time_review_refuses_without_writing(self):
        with mock.patch.object(config, "LEDGER_DEALS", config.LEDGER_DEALS + ["fake"]):
            with self.assertRaises(ledger_consolidate.ConsolidationError):
                ledger_consolidate.consolidate_all(self.conn)
        self.assertEqual(sum(self.consolidation_counts().values()), 0)

    def test_an_unreadable_catalogue_refuses(self):
        with self.assertRaises(ledger_consolidate.ConsolidationError):
            ledger_consolidate.consolidate_all(self.conn, catalogue_path=self.root / "missing.json")
        self.assertEqual(sum(self.consolidation_counts().values()), 0)


class TestSeal(ConsolidateCase):
    """A decoy sealed deal planted with raw SQL (bypassing the import guard) must never be consolidated."""

    def setUp(self):
        super().setUp()
        c = self.conn
        deal = c.execute("INSERT INTO deals (slug, kind, display_name) VALUES (?, 'development', 'x')", (DECOY,)).lastrowid
        source = c.execute("INSERT INTO sources (deal_id, source_key, display_name) VALUES (?, 'CP-01', 'x')", (deal,)).lastrowid
        h = "a" * 64
        version = c.execute(
            "INSERT INTO source_versions (source_id, version_no, original_sha256, canonical_sha256, adapter_name, adapter_version,"
            " doc_type, doc_date, original_filename, canonical_text, location_map) VALUES (?, 1, ?, ?, 't', '1',"
            " 'call_transcript', '2026-10-01', 'x.md', 'x', '[]')", (source, h, h)).lastrowid
        self.decoy_review = c.execute(
            "INSERT INTO reviews (deal_id, run_kind, checker) VALUES (?, 'review', 'rules')", (deal,)).lastrowid
        extraction = c.execute("INSERT INTO extraction_cache (output_json, origin) VALUES ('[]', 'imported_run_file')").lastrowid
        c.execute("INSERT INTO review_sources (review_id, source_version_id, extraction_id, cache_outcome)"
                  " VALUES (?, ?, ?, 'imported')", (self.decoy_review, version, extraction))
        c.execute("INSERT INTO statements (extraction_id, ordinal, statement_key, quote, language)"
                  " VALUES (?, 1, 'CP-01-S01', ?, 'firm')", (extraction, f"{CANARY} will be delivered."))
        c.commit()

    def canary_in_consolidation_output(self):
        for table in CONSOLIDATION_TABLES:
            if CANARY in "\n".join(str(r) for r in self.conn.execute(f"SELECT * FROM {table}")):
                return True
        return False

    def test_the_decoy_review_is_refused_even_if_allowed_deals_is_widened(self):
        with self.assertRaises(ledger.LedgerDealNotAllowed):
            ledger_consolidate.consolidate_review(self.conn, self.decoy_review)
        with mock.patch.object(config, "ALLOWED_DEALS", config.ALLOWED_DEALS + [DECOY]):
            with self.assertRaises(ledger.LedgerDealNotAllowed):
                ledger_consolidate.consolidate_review(self.conn, self.decoy_review)
        self.assertFalse(self.canary_in_consolidation_output())
        self.assertEqual(sum(self.consolidation_counts().values()), 0)

    def test_consolidate_all_leaves_the_decoy_untouched(self):
        ledger_consolidate.consolidate_all(self.conn)
        self.assertEqual(self.consolidation_counts(), CONSOLIDATED_COUNTS)
        self.assertFalse(self.canary_in_consolidation_output())
        self.assertEqual(self.conn.execute(
            "SELECT COUNT(*) FROM review_statements WHERE review_id = ?", (self.decoy_review,)).fetchone()[0], 0)

    def test_negative_control_the_canary_check_detects_an_unguarded_consolidation(self):
        with mock.patch.object(config, "LEDGER_DEALS", config.LEDGER_DEALS + [DECOY]):
            ledger_consolidate.consolidate_review(self.conn, self.decoy_review)
        self.assertTrue(self.canary_in_consolidation_output())


class TestPlanReview(unittest.TestCase):
    """The pure planning function on synthetic statements."""

    SHA = "f" * 64

    @staticmethod
    def st(n, quote, language="firm"):
        return {"statement_id": n, "source_version_id": 1, "statement_key": f"X-S{n:02d}", "quote": quote, "language": language}

    def plan(self, statements, vocab=VOCAB):
        return ledger_consolidate.plan_review(statements, vocab, self.SHA)

    def test_equal_complete_keys_merge_and_unequal_ones_do_not(self):
        plan = self.plan([
            self.st(1, "The payout ledger connector will handle up to thirty thousand payouts per day at launch."),
            self.st(2, "The payout ledger connector will handle up to 30,000 payouts per day at launch."),
            self.st(3, "The payout ledger connector will handle up to 40,000 payouts per day at launch."),
        ])
        self.assertEqual([c["members"] for c in plan["commitments"]], [[(1, 1), (2, 1)], [(3, 1)]])

    def test_two_statements_missing_the_same_term_stay_separate(self):
        plan = self.plan([self.st(1, "Wallets on Polygon are screened."), self.st(2, "Wallets on Polygon are screened.")])
        self.assertEqual(len(plan["commitments"]), 2)
        for c in plan["commitments"]:
            self.assertTrue(c["terms"]["terms_incomplete"])
            self.assertIsNone(c["terms"]["key"])
            self.assertEqual(c["terms"]["missing"], ["mode"])

    def test_language_is_the_firmest_and_the_rationale_names_all_members(self):
        plan = self.plan([
            self.st(1, "Wallets on Polygon are screened in real time.", "exploratory"),
            self.st(2, "Wallets on Polygon are screened in real time.", "conditional"),
            self.st(3, "Wallets on Polygon are screened in real time.", "firm"),
        ])
        [c] = plan["commitments"]
        self.assertEqual(c["language"], "firm")
        for key in ("X-S01", "X-S02", "X-S03"):
            self.assertIn(key, c["rationale"])

    def test_a_statement_with_two_term_sets_is_linked_twice(self):
        plan = self.plan([self.st(1, "NUSD wallets on Ethereum and Polygon are screened in real time.")])
        self.assertEqual(len(plan["commitments"]), 2)
        self.assertTrue(all(c["members"] == [(1, 1)] for c in plan["commitments"]))

    def test_an_ambiguous_association_is_an_incomplete_commitment_of_its_own(self):
        vocab = terms.build_vocabulary(synthetic_catalogue_with_usdc())
        plan = self.plan([self.st(1, "NUSD and USDC wallets on Ethereum and Polygon are screened in real time.")], vocab)
        [c] = plan["commitments"]
        self.assertEqual((c["terms"]["terms_incomplete"], c["terms"]["missing"]), (True, ["association"]))
        self.assertIn("terms incomplete: association", c["name"])

    def test_differing_go_live_dates_are_one_commitment_with_each_date_kept(self):
        plan = self.plan([self.st(1, "Elva will go live on 1 March 2027."), self.st(2, "We are targeting a 15 April 2027 go-live.")])
        [c] = plan["commitments"]
        self.assertEqual([m["term_set"]["go_live_date"] for m in c["terms"]["members"]], ["2027-03-01", "2027-04-15"])

    def test_dropped_statements_make_no_commitment(self):
        plan = self.plan([self.st(1, "We'll send our security pack by Friday.")])
        self.assertEqual(plan["commitments"], [])
        self.assertEqual(plan["statements"],
                         [{"statement_id": 1, "source_version_id": 1, "kept": 0, "filter_rule": "sales_security_pack"}])

    def test_keys_follow_first_appearance_and_planning_is_deterministic(self):
        statements = [
            self.st(1, "Elva will provide full case audit history for every alert."),
            self.st(2, "The payout ledger connector will handle up to 5,000 payouts per day at launch."),
        ]
        plan = self.plan(statements)
        self.assertEqual([c["commitment_key"] for c in plan["commitments"]], ["C01", "C02"])
        self.assertEqual(plan, self.plan(statements))
        self.assertEqual(self.plan([]), {"statements": [], "commitments": []})

    def test_the_rules_hash_follows_the_catalogue(self):
        raw = json.dumps(CATALOGUE).encode()
        self.assertEqual(ledger_consolidate.rules_sha256(raw), ledger_consolidate.rules_sha256(raw))
        self.assertNotEqual(ledger_consolidate.rules_sha256(raw), ledger_consolidate.rules_sha256(raw + b" "))


class TestCli(ConsolidateCase):
    def setUp(self):
        super().setUp()
        self.conn.close()
        self.target = self.root / "cli" / "ledger.sqlite"
        patcher = mock.patch.object(config, "LEDGER_DB_PATH", self.target)
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_main(self, argv=()):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = ledger_consolidate.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_a_missing_database_is_refused(self):
        code, _, err = self.run_main()
        self.assertEqual(code, 2)
        self.assertIn("does not exist", err)

    def test_it_consolidates_once_then_refuses(self):
        ledger_import.build(self.target)
        code, out, _ = self.run_main()
        self.assertEqual(code, 0)
        self.assertIn("harbour_bank: 20 statements (15 kept), 10 commitments", out)
        self.assertIn("hard_cases: 10 statements (9 kept), 8 commitments", out)
        before = self.target.read_bytes()
        code, _, err = self.run_main()
        self.assertEqual(code, 2)
        self.assertIn("already consolidated", err)
        self.assertEqual(self.target.read_bytes(), before)

    def test_a_database_from_another_schema_is_refused(self):
        ledger_import.build(self.target)
        conn = sqlite3.connect(self.target)
        conn.execute("UPDATE schema_meta SET value = '0' WHERE key = 'schema_version'")
        conn.commit()
        conn.close()
        code, _, err = self.run_main()
        self.assertEqual(code, 2)
        self.assertIn("older schema", err)

    def test_arguments_are_refused(self):
        self.assertEqual(self.run_main(["--bogus"])[0], 2)


class TestLabels(ConsolidateCase):
    """Labels check the result; they never shape it. Read straight from the real labels folder."""

    def setUp(self):
        super().setUp()
        ledger_consolidate.consolidate_all(self.conn)

    def statement_for(self, slug, label_id):
        labels = json.loads((REAL_DATA / slug / "labels" / "statements.json").read_text(encoding="utf-8"))["statements"]
        run = json.loads((REAL_RESULTS / config.LEDGER_IMPORT_RUN_FILES[slug]).read_text(encoding="utf-8"))
        outputs = [s for d in run["documents"] for s in d["statements"]]
        result = evaluate.assign(labels, outputs, config.MATCH_THRESHOLD, config.NEAR_MISS_FLOOR)
        matched = {l["id"]: o["statement_id"] for _, l, o in result["matches"]}
        self.assertIn(label_id, matched, f"label {label_id} was not matched to a statement")
        return matched[label_id]

    def test_label_s04_is_linked_to_the_polygon_and_ethereum_real_time_commitments(self):
        linked = self.commitments_of(self.statement_for("harbour_bank", "S04"))
        self.assertEqual(len(linked), 2)
        self.assertTrue(any("Polygon, real time" in c for c in linked) and any("Ethereum, real time" in c for c in linked))

    def test_label_s11_is_the_known_miss_two_incomplete_commitments(self):
        linked = self.commitments_of(self.statement_for("harbour_bank", "S11"))
        self.assertEqual(len(linked), 2)
        self.assertTrue(all("terms incomplete: mode" in c for c in linked))

    def test_labels_k04_and_k08_share_one_commitment(self):
        k04 = self.commitments_of(self.statement_for("hard_cases", "K04"))
        k08 = self.commitments_of(self.statement_for("hard_cases", "K08"))
        self.assertEqual(len(k04), 1)
        self.assertEqual(k04, k08)


if __name__ == "__main__":
    unittest.main()
