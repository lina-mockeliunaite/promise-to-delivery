"""Reset the demo workspace: back up the current ledger, then rebuild a fresh one from the v2 demo deals.

    .venv/bin/python reset_demo.py

Since 10 Oct the app runs v2 (model detects, code verifies): ledger_v2.build imports each deal in config.V2_DEALS and
makes its first review from the saved, frozen v2 output in config.V2_SEED_FILES, verifying every finding again. No model
call, no API key, no network. Writes only inside workspace/ (the ledger) and results/v2_cache/ (the model-output cache);
data/ is read and never written, and it refuses to write a ledger inside data/.

The new ledger is built beside the old one and swapped in only if the whole build succeeds; the old ledger is then
backed up (a consistent SQLite copy) next to it as ledger.backup-<UTC timestamp>.sqlite. Anything created in the app
since the last reset (user deals, fixes, handoffs) is only in that backup. Stop the app first, then start it again.
"""

import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import config
import ledger
import ledger_import
import ledger_v2
import workspace


class ResetError(Exception):
    pass


def reset(db_path=None, now=None) -> dict:
    """Back up and rebuild the ledger. Returns what it did: paths, per-deal counts and the model-call count (always 0)."""
    final = Path(db_path) if db_path is not None else config.LEDGER_DB_PATH
    if final.resolve().is_relative_to(config.DATA_DIR.resolve()):
        raise ResetError(f"refusing to write a ledger inside the data folder: {final}")
    stamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    final.parent.mkdir(parents=True, exist_ok=True)
    fresh = final.with_name(final.name + ".resetting")
    fresh.unlink(missing_ok=True)  # leftover from an earlier crash: our own temporary file

    try:
        built = ledger_v2.build(fresh)
        conn = ledger.connect(fresh)
        try:
            deals = [{"deal": d["deal"], "open_issues": d["open_issues"], "freshness": d["freshness"]["state"]}
                     for d in workspace.deal_list(conn)]
            commitments = {slug: conn.execute(
                "SELECT COUNT(*) FROM commitments c JOIN deals d ON d.id = c.deal_id WHERE d.slug = ?", (slug,)).fetchone()[0]
                for slug in config.V2_DEALS}
        finally:
            conn.close()
        model_calls = sum(r["model_calls"] for r in built.values())
        backup = None
        if final.exists():
            backup = final.with_name(f"{final.stem}.backup-{stamp}{final.suffix}")
            if backup.exists():
                raise ResetError(f"{backup.name} already exists; wait a second and run again")
            source, target = sqlite3.connect(f"file:{final}?mode=ro", uri=True), sqlite3.connect(backup)
            try:
                source.backup(target)
            finally:
                target.close()
                source.close()
        os.replace(fresh, final)
    except BaseException:
        fresh.unlink(missing_ok=True)
        raise
    return {"ledger": final, "backup": backup, "deals": deals, "commitments": commitments, "model_calls": model_calls}


def main(argv: list) -> int:
    if argv:
        print("usage: python reset_demo.py", file=sys.stderr)
        return 2
    try:
        done = reset()
    except (ResetError, ledger_import.LedgerImportError, ledger.LedgerDealNotAllowed, ledger_v2.NeedsModel) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    print("Demo reset.")
    if done["backup"]:
        print(f"  Backed up the old ledger to {done['backup']}")
    else:
        print("  No existing ledger, so nothing to back up.")
    print(f"  Built a fresh ledger at {done['ledger']} from the v2 demo deals (saved v2 findings, each verified again; "
          f"model calls: {done['model_calls']}).")
    for d in done["deals"]:
        print(f"  Shown in the app: {d['deal']}, {done['commitments'][d['deal']]} commitments, {d['open_issues']} open issues, "
              f"review {d['freshness'].lower()}.")
    print("  Anything created in the app since the last reset (user deals, fixes, handoffs) is only in the backup.")
    print("  Restart the app so it opens the new ledger.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
