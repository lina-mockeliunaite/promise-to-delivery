"""Public demo mode (10 Nov): a hosted, read-and-try copy that many visitors share.

DEALSHAPE_PUBLIC_DEMO=1 turns it on; off by default, and with it off nothing here is used. Public mode serves two deals,
accepts only the bundled sample files, never calls the model, refuses what would let a visitor plant content other
visitors would see (user deals, catalogue capabilities, document links), caps note length, and resets the shared ledger
every hour with the same reset_demo.reset() the Reset demo button uses. No key is read. Data files are never edited:
the sample titles, summaries and filing details live here.
"""

import hashlib
import os
import threading
from pathlib import Path

import config

PUBLIC_DEALS = ["noma_journeys", "alder_bank"]  # also the order the public deal list shows them in: Noma Journeys first
BANNER = "Public demo · fictional data"  # the demo bar's status text (11 Nov: the guide moved into the bar)
SHARED_NOTE = "Shared with other visitors. If a deal has already been worked through, click Reset demo."  # under "All steps"
NOTE_MAX = 500
NOTE_FIELDS = ("note", "reason", "rationale", "evidence")
BACKUPS_KEPT = 3
RESET_EVERY_SECONDS = 60 * 60
NO_MODEL = "The public demo can't read new documents. Use one of the sample files."
NOT_A_SAMPLE = "This public demo only accepts its sample files. Pick one under \"Use a sample file\"."
REFUSED = {
    "user_deal": "The public demo has no new deals; open one of the sample deals.",
    "capability": "The public demo's product catalogue can't be changed.",
    "link": "The public demo doesn't take document links, because other visitors would see them.",
}

# file, a short title, one line of who did what and when (names and dates only as the file states them), and how it is filed (what the add-document form would set). "version_of" is a source key; a new
# document carries its type, its name and the date the file states about itself (the form pre-fills the same date).
SAMPLES = {
    "noma_journeys": [
        {"file": "NJ-05_v2_named_exception.md", "version_of": "NJ-05", "title": "Approval for the launch specialist",
         "summary": "Omar Haddad, Head of Customer Success, approves a named exception: first 30 days, no extra charge (18 October 2026)."},
        {"file": "NJ-07_v2_languages_aligned.md", "version_of": "NJ-07", "title": "Revised draft contract",
         "summary": "The languages clause now says 12 languages (19 October 2026)."},
        {"file": "NJ-09_signed_contract.md", "doc_type": "signed_contract", "doc_date": "2026-10-20", "title": "Signed contract",
         "summary": "Signed 20 October 2026 by Liam Hart (Aivuna) and Celeste Wong (Noma Journeys)."},
    ],
    "alder_bank": [
        {"file": "AB-05_v2_named_exception.md", "version_of": "AB-05", "title": "Approval for the BioCatch connector (coaching detection)",
         "summary": "Arjun Rao, Head of Product, approves the BioCatch connector (beta) as a named exception for the 1 February 2027 launch (16 October 2026)."},
        {"file": "AB-06_v2_coaching_added.md", "version_of": "AB-06", "title": "Revised statement of work",
         "summary": "Scam coaching detection is added as section 5 (16 October 2026)."},
        {"file": "AB-09_signed_contract.md", "doc_type": "signed_contract", "doc_date": "2026-10-12", "title": "Signed contract",
         "summary": "Signed 20 October 2026 by Tom Fraser (Elva) and Priya Nair (Alder Bank); it incorporates the SOW dated 9 October."},
    ],
}


def enabled(env=None) -> bool:
    return (os.environ if env is None else env).get("DEALSHAPE_PUBLIC_DEMO") == "1"


def extra_hosts(env=None) -> list:
    raw = (os.environ if env is None else env).get("DEALSHAPE_ALLOWED_HOSTS", "")
    return [h.strip() for h in raw.split(",") if h.strip()]


def sample_path(file: str) -> Path:
    return config.scenario_path(file)


def samples(deal: str) -> list:
    return [dict(s, deal=deal) for s in SAMPLES.get(deal, [])]


def find_sample(deal: str, file: str):
    return next((s for s in SAMPLES.get(deal, []) if s["file"] == file), None)


def sample_text(deal: str, file: str):
    """The sample's text, or None when this deal has no such sample. The name is matched against the catalogue, never used as a path."""
    s = find_sample(deal, file)
    return sample_path(s["file"]).read_text(encoding="utf-8") if s else None


def sample_hashes(deal: str) -> set:
    return {hashlib.sha256(sample_path(s["file"]).read_bytes()).hexdigest() for s in SAMPLES.get(deal, [])}


def is_sample(deal: str, content: bytes) -> bool:
    return hashlib.sha256(content).hexdigest() in sample_hashes(deal)


def prune_backups(ledger_path, keep: int = BACKUPS_KEPT) -> list:
    """Keep the newest `keep` ledger.backup-<UTC stamp> files next to the ledger (the stamp sorts as time); returns what was removed."""
    final = Path(ledger_path)
    found = sorted(final.parent.glob(f"{final.stem}.backup-*{final.suffix}"), key=lambda p: p.name)
    gone = found[:-keep] if keep > 0 else found
    for p in gone:
        p.unlink(missing_ok=True)
    return gone


class HourlyReset:
    """Runs `run` (the app's one reset function, which takes the reset lock) every `every` seconds on a daemon thread.
    tick() is the unit a test drives; a reset that fails or is refused is reported once and the loop carries on."""

    def __init__(self, run, every: float = RESET_EVERY_SECONDS, report=print):
        self.run, self.every, self.report = run, every, report
        self._stop = threading.Event()
        self._thread = None

    def tick(self):
        try:
            return self.run()
        except Exception as exc:  # the next hour tries again; the old ledger is left as it was
            self.report(f"hourly reset skipped: {getattr(exc, 'detail', exc)}")
            return None

    def start(self):
        def loop():
            while not self._stop.wait(self.every):
                self.tick()
        self._thread = threading.Thread(target=loop, name="hourly-reset", daemon=True)
        self._thread.start()
        return self

    def stop(self):
        self._stop.set()
