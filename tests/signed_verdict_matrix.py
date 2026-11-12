"""Every signed-contract verdict, for all five deals, in the states the demo can reach (11 Nov). Used by test_signed_verdicts_unchanged.py to prove that adding output
fields to signed_check.py changed no verdict: the golden file tests/fixtures/signed_verdicts_golden.json was written from the code as it stood before that change.

For each deal the scenario documents it has are added (Noma NJ-05, NJ-07; Alder AB-05, AB-06; Harbour HB-05, HB-06; Coral and Atlas have none), then a signed contract in three variants:
  shipped  the deal's own signed sample where there is one, else a plain signed agreement that repeats nothing
  full     a signed agreement that repeats every draft contract and SOW sentence (so every closed contract gap is confirmed)
  bare     a signed agreement with a signature block and nothing else (every closed contract gap is not found)
Only the keys a verdict had before the change are compared (see KEYS); anything added later is ignored. Pure reads of data/ and of the reading cache; temporary ledgers."""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

import api
import config
import ledger
import ledger_fixes
import reset_demo
import signed_check

H = {"X-Requested-With": "deal-workspace"}
SC = config.SCENARIOS_DIR
KEYS = ("status", "closed_by", "earlier", "kind", "text", "reason", "sentence", "signed", "date")
DEALS = {
    "noma_journeys": [("NJ-05_v2_named_exception.md", "NJ-05"), ("NJ-07_v2_languages_aligned.md", "NJ-07")],
    "alder_bank": [("AB-05_v2_named_exception.md", "AB-05"), ("AB-06_v2_coaching_added.md", "AB-06")],
    "harbour_bank": [("HB-05_v2_named_exception.md", "HB-05"), ("HB-06_v2_annex_aligned.md", "HB-06")],
    "coral_pay": [],
    "atlas_remit": [],
}
OWN_SIGNED = {"noma_journeys": "NJ-09_signed_contract.md", "alder_bank": "AB-09_signed_contract.md"}
PLAIN = "# Master Services Agreement (signed copy)\n\nDate: 20 October 2026\n\n**Clause 1. Definitions.** Capitalised terms have their usual meanings.\n\n## Signatures\n\nName: A. Signer\nDate: 20 October 2026\n"


def _client(db, tmp):
    return TestClient(api.create_app(dist_dir=Path(tmp) / "x", ledger_path=db, public=False), base_url="http://127.0.0.1")


def verdicts(deal, variant):
    """{ "<commitment> | <finding type> | <state before>": {KEYS...} } plus "_steps": which scenario documents were accepted."""
    with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}, clear=True):
        db = Path(tmp) / "ledger.sqlite"
        reset_demo.reset(db)
        client = _client(db, tmp)
        steps = []
        for f, key in DEALS[deal]:
            r = client.post(f"/api/deals/{deal}/documents/add-and-check", json={"source_key": key, "filename": f, "text": (SC / f).read_text(encoding="utf-8")}, headers=H)
            steps.append((f, r.status_code))
        conn = ledger.connect(db)
        try:
            did = ledger_fixes.deal_id(conn, deal)
            drafts = [t for (t,) in conn.execute(
                "SELECT v.canonical_text FROM sources s JOIN source_versions v ON v.source_id = s.id WHERE s.deal_id = ? AND v.doc_type IN ('draft_contract','draft_sow')"
                " AND v.version_no = (SELECT MAX(version_no) FROM source_versions WHERE source_id = s.id) ORDER BY s.source_key", (did,))]
        finally:
            conn.close()
        if variant == "shipped":
            text = (SC / OWN_SIGNED[deal]).read_text(encoding="utf-8") if deal in OWN_SIGNED else PLAIN
        elif variant == "full":
            text = PLAIN.replace("## Signatures", "\n\n".join(drafts) + "\n\n## Signatures")
        else:
            text = PLAIN
        r = client.post(f"/api/deals/{deal}/documents/add-and-check", json={"name": "Signed contract", "filename": "signed.md", "doc_type": "signed_contract",
                                                                            "doc_date": "2026-10-20", "text": text}, headers=H)
        steps.append(("signed", r.status_code))
        conn = ledger.connect(db)
        try:
            did = ledger_fixes.deal_id(conn, deal)
            res = signed_check.evaluate(conn, did, deal)
            names = {iid: (c, t) for iid, c, t in conn.execute(
                "SELECT i.id, c.commitment_key, i.issue_type FROM issues i JOIN commitments c ON c.id = i.commitment_id WHERE c.deal_id = ?", (did,))}
            out = {f"{names[iid][0]} | {names[iid][1]}": {k: v.get(k) for k in KEYS} for iid, v in sorted(res.items())}
        finally:
            conn.close()
        out["_steps"] = steps
        return out


def matrix():
    return {f"{deal}/{variant}": verdicts(deal, variant) for deal in DEALS for variant in ("shipped", "full", "bare")}


if __name__ == "__main__":
    if "--write" in sys.argv:
        path = Path(__file__).parent / "fixtures" / "signed_verdicts_golden.json"
        path.write_text(json.dumps(matrix(), indent=1, sort_keys=True), encoding="utf-8")
        print("written", path)
