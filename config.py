"""Single home for model IDs, document types and the deal guard.

Other code reads these values from here; nothing else should hard-code them.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"

# --- Model ---------------------------------------------------------------
# Provisional (DECISIONS #1); compared against other models on Day 5.
EXTRACTION_MODEL = "claude-sonnet-5"
MAX_TOKENS = 8000  # ceiling on the whole reply; any thinking tokens count against it

# "model_default" = send no thinking parameter and let the model decide.
# extract.py refuses any other value until that mode is implemented.
THINKING_MODE = "model_default"

# One retry: the first attempt plus one more.
MAX_ATTEMPTS = 2

# USD per million tokens, standard (non-batch, no caching, global routing).
# Checked by Lina against https://platform.claude.com/docs/en/about-claude/pricing
# on 2026-09-29. Cost is null for any model with None here.
PRICE_PER_MTOK = {
    EXTRACTION_MODEL: {"input": 2.0, "output": 10.0},
}

# --- Document types ------------------------------------------------------
# Extracted: one model call per document of these types.
EXTRACTABLE_DOC_TYPES = [
    "call_transcript",
    "rfp_response",
    "proposal",
    "draft_sow",
    "draft_contract",
]

# Known but deliberately not extracted in v1. Recorded as skipped, not flagged.
# pricing_services_note stays authorisation evidence; customer_email stays
# customer context for later stages.
REFERENCE_ONLY_DOC_TYPES = [
    "pricing_services_note",
    "customer_email",
]

# Any doc_type in neither list is logged and flagged.

# Speaker: for calls the model names the actual Elva speaker. For every other
# extracted document type the code sets a fixed value and ignores the model's.
CALL_DOC_TYPES = ["call_transcript"]
WRITTEN_DOC_SPEAKER = "Elva"

# --- Deal guard ----------------------------------------------------------
# The sealed test deal is deliberately absent until it is released.
ALLOWED_DEALS = ["harbour_bank"]


class DealNotAllowed(Exception):
    """Raised when a deal name is not in ALLOWED_DEALS."""


def require_allowed_deal(deal: str) -> str:
    """Return the deal name if allowed, else raise. Exact match only."""
    if deal not in ALLOWED_DEALS:
        raise DealNotAllowed(
            f"Deal {deal!r} is not in ALLOWED_DEALS {ALLOWED_DEALS}; refusing to read it."
        )
    return deal


def deal_dir(deal: str) -> Path:
    """Path to a deal folder. The only way code builds a deal path, so the guard always runs first."""
    return DATA_DIR / require_allowed_deal(deal)


def docs_dir(deal: str) -> Path:
    """Resolved path to the deal's docs/ folder (labels/ and everything else sit outside it)."""
    return (deal_dir(deal) / "docs").resolve()


def doc_path(deal: str, filename: str) -> Path:
    """Path to a file inside the deal's docs/ folder, or ValueError if it resolves outside it.

    Resolving first means '..' segments and symlinks are followed before the check.
    """
    base = docs_dir(deal)
    path = (base / filename).resolve()
    if not path.is_relative_to(base):
        raise ValueError(f"{filename!r} resolves outside the docs folder")
    return path
