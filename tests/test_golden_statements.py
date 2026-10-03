"""Golden table: the 30 imported statements, parsed and filtered.

Any change to a term-parser or filter rule that moves a row here is deliberate and must update this table.
Rows are: statement key, language (first four letters), parsed term sets, attributes, terms_incomplete, filter outcome.
Reads the frozen run files and the catalogue (read-only). Labels are never read here.
"""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
import sales_filter
import terms

VOCAB = terms.build_vocabulary(json.loads((config.DATA_DIR / "catalogue.json").read_text(encoding="utf-8")))
RESULTS = config.RESULTS_DIR

GOLDEN = [
    ('HB-01-S01', 'expl', '{CAP-021; network=Polygon; mode=real_time}', '', 'no', 'kept'),
    ('HB-01-S02', 'firm', '{}', '', 'yes: capability', 'DROPPED sales_next_call'),
    ('HB-01-S03', 'cond', '{go_live date=--12-01}', 'dates=--12-01,--11-15', 'no', 'kept'),
    ('HB-01-S04', 'firm', '{}', '', 'yes: capability', 'DROPPED sales_rfp_or_proposal_response'),
    ('HB-02-S01', 'cond', '{CAP-021; network=Polygon; mode=real_time; region=SG}', 'dates=2027-03-31', 'no', 'kept'),
    ('HB-02-S02', 'firm', '{}', '', 'yes: capability', 'DROPPED sales_walkthrough'),
    ('HB-03-S01', 'firm', '{CAP-021; network=Ethereum; asset=NUSD; mode=real_time} + {CAP-021; network=Polygon; asset=NUSD; mode=real_time}', '', 'no', 'kept'),
    ('HB-03-S02', 'firm', '{}', '', 'yes: capability', 'DROPPED sales_methodology'),
    ('HB-04-S01', 'firm', '{CAP-021; network=Polygon; asset=NUSD; mode=real_time}', 'dates=--12-01', 'no', 'kept'),
    ('HB-04-S02', 'firm', '{CAP-021; network=Ethereum; asset=NUSD; mode=real_time}', '', 'no', 'kept'),
    ('HB-04-S03', 'firm', '{CAP-023; qty=max12000 payouts/day; when=launch}', '', 'no', 'kept'),
    ('HB-04-S04', 'firm', '{CAP-023; qty=max40000 payouts/day; when=end_of_first_year}', '', 'no', 'kept'),
    ('HB-04-S05', 'firm', '{CAP-024; region=SG}', 'dates=2027-03-31', 'no', 'kept'),
    ('HB-04-S06', 'firm', '{}', '', 'yes: capability', 'DROPPED sales_draft_sow_to_follow'),
    ('HB-06-S01', 'firm', '{CAP-023; qty=max12000 payouts/day; when=launch}', '', 'no', 'kept'),
    ('HB-06-S02', 'firm', '{CAP-021; network=Ethereum; asset=NUSD} + {CAP-021; network=Polygon; asset=NUSD}', '', 'yes: mode', 'kept'),
    ('HB-06-S03', 'firm', '{}', 'cadence=weekly', 'yes: capability', 'kept'),
    ('HB-06-S04', 'firm', '{CAP-021; network=Ethereum; mode=real_time}', '', 'no', 'kept'),
    ('HB-06-S05', 'firm', '{CAP-021; network=Polygon; mode=batch}', 'cadence=hourly', 'no', 'kept'),
    ('HB-06-S06', 'firm', '{CAP-021; network=Polygon; mode=batch}', '', 'no', 'kept'),
    ('KR-01-S01', 'firm', '{CAP-021; network=Arbitrum [not in catalogue]}', '', 'yes: mode', 'kept'),
    ('KR-01-S02', 'firm', '{}', '', 'yes: capability', 'DROPPED sales_security_pack'),
    ('KR-01-S03', 'cond', '{CAP-021; network=Polygon; mode=real_time}', '', 'no', 'kept'),
    ('KR-02-S01', 'firm', '{go_live date=2027-03-01}', 'dates=2027-03-01', 'no', 'kept'),
    ('KR-02-S02', 'firm', '{CAP-023; qty=max30000 payouts/day; when=launch}', '', 'no', 'kept'),
    ('KR-02-S03', 'firm', '{CAP-021; network=Arbitrum [not in catalogue]; asset=NUSD; mode=real_time}', '', 'no', 'kept'),
    ('KR-02-S04', 'cond', '{CAP-024}', '', 'no', 'kept'),
    ('KR-02-S05', 'firm', '{CAP-014}', '', 'no', 'kept'),
    ('KR-03-S01', 'firm', '{CAP-023; qty=max30000 payouts/day; when=launch}', '', 'no', 'kept'),
    ('KR-03-S02', 'firm', '{CAP-021; network=Ethereum; asset=NUSD; mode=real_time}', '', 'no', 'kept'),
]


def summarise_set(ts):
    parts = []
    if ts.promise_type == "go_live":
        parts.append(f"go_live date={ts.go_live_date}")
    if ts.capability:
        parts.append(ts.capability)
    for d in ("network", "asset", "mode", "region"):
        v = getattr(ts, d)
        if v:
            parts.append(f"{d}={v}" + (" [not in catalogue]" if d == "network" and ts.network_in_catalogue is False else ""))
    if ts.quantity:
        q = ts.quantity
        parts.append(f"qty={q['bound'] or ''}{q['value']} {q['unit'] or '?'}/{q['period'] or '?'}")
    if ts.when:
        parts.append("when=" + ",".join(ts.when))
    return "{" + "; ".join(parts) + "}"


def summarise(statement):
    parsed = terms.parse_terms(statement["quote"], VOCAB)
    decision = sales_filter.classify(statement["quote"], VOCAB)
    extra = []
    if parsed.dates:
        extra.append("dates=" + ",".join(parsed.dates))
    if parsed.cadence:
        extra.append("cadence=" + ",".join(parsed.cadence))
    outcome = "kept" if decision.kept else f"DROPPED {decision.rule}"
    if decision.kept and decision.matched_rules:
        outcome += f" (matched {','.join(decision.matched_rules)} but has terms)"
    return (
        statement["statement_id"],
        statement["language"][:4],
        " + ".join(summarise_set(t) for t in parsed.term_sets) or "(none)",
        "; ".join(extra),
        ("yes: " + ", ".join(parsed.missing)) if parsed.missing else "no",
        outcome,
    )


def frozen_statements():
    out = []
    for slug in ("harbour_bank", "hard_cases"):
        run = json.loads((RESULTS / config.LEDGER_IMPORT_RUN_FILES[slug]).read_text(encoding="utf-8"))
        out += [s for d in run["documents"] for s in d["statements"]]
    return out


class TestGolden(unittest.TestCase):
    def test_the_30_imported_statements_match_the_golden_table(self):
        statements = frozen_statements()
        self.assertEqual(len(statements), 30)
        self.assertEqual([summarise(s) for s in statements], GOLDEN)

    def test_incomplete_sets_have_no_key_and_complete_sets_have_one(self):
        for s in frozen_statements():
            for ts in terms.parse_terms(s["quote"], VOCAB).term_sets:
                self.assertEqual(ts.key is None, bool(ts.missing), s["statement_id"])

    def test_the_thirty_thousand_pair_and_the_12000_pair_share_keys(self):
        by_id = {s["statement_id"]: terms.parse_terms(s["quote"], VOCAB).term_sets for s in frozen_statements()}
        self.assertEqual([t.key for t in by_id["KR-02-S02"]], [t.key for t in by_id["KR-03-S01"]])
        self.assertEqual([t.key for t in by_id["HB-04-S03"]], [t.key for t in by_id["HB-06-S01"]])
        self.assertNotEqual(by_id["HB-04-S03"][0].key, by_id["HB-04-S04"][0].key)

    def test_real_time_and_hourly_batch_polygon_are_never_merged(self):
        by_id = {s["statement_id"]: terms.parse_terms(s["quote"], VOCAB).term_sets for s in frozen_statements()}
        polygon_real_time = next(t.key for t in by_id["HB-04-S01"] if t.network == "Polygon")
        polygon_batch = by_id["HB-06-S05"][0].key
        self.assertNotEqual(polygon_real_time, polygon_batch)
        self.assertEqual(polygon_batch, by_id["HB-06-S06"][0].key)

    def test_a_statement_listing_two_networks_joins_each_matching_group(self):
        by_id = {s["statement_id"]: terms.parse_terms(s["quote"], VOCAB).term_sets for s in frozen_statements()}
        two_networks = {t.network: t.key for t in by_id["HB-03-S01"]}
        self.assertEqual(two_networks["Polygon"], by_id["HB-04-S01"][0].key)
        self.assertEqual(two_networks["Ethereum"], by_id["HB-04-S02"][0].key)


if __name__ == "__main__":
    unittest.main()
