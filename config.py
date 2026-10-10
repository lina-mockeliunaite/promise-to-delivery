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

# Default mode for extract.py. "model_default" = send no thinking parameter and let the model decide.
# "off" is implemented and chosen per run with `extract.py --thinking off` (sends thinking={"type": "disabled"},
# only for models in THINKING_DISABLED_ACCEPTED). The default here stays "model_default".
# extract.py refuses any other value.
THINKING_MODE = "model_default"

# Models that accept thinking={"type": "disabled"}, which `extract.py --thinking off` sends.
# Source: "Troubleshooting thinking", per-model table, platform.claude.com/docs/en/build-with-claude/thinking-troubleshooting,
# fetched 2026-09-30. claude-sonnet-5 is named there as accepting "disabled". Haiku 4.5's entry is inferred
# from its absence on the rejected list (the page says any value not listed as rejected is accepted); the page
# does not state it explicitly. Not accepted: claude-sonnet-5-5 (needs "between_tools") and the always-on
# models (Opus 5.5, Fable, Mythos).
THINKING_DISABLED_ACCEPTED = ["claude-sonnet-5", "claude-haiku-4-5-20251001"]

# Agent (5 Oct block, rules-vs-agent comparison). Same model as extraction so the comparison is about the method,
# not the model. Bounds from the decision rule (DECISIONS 2026-10-03): tool calls per commitment and per deal.
AGENT_MODEL = EXTRACTION_MODEL
AGENT_MAX_TOKENS = 4000
AGENT_MAX_TOOL_CALLS_PER_COMMITMENT = 6
AGENT_MAX_TOOL_CALLS_PER_DEAL = 40
AGENT_MAX_TURNS = 15
# Decision-rule bounds: extra cost and latency per deal review (means of three runs; no single run above 2x).
AGENT_BOUND_COST_USD = 0.10
AGENT_BOUND_LATENCY_S = 60

# One retry: the first attempt plus one more.
MAX_ATTEMPTS = 2

# USD per million tokens, standard (non-batch, no caching, global routing).
# Checked by Lina against https://platform.claude.com/docs/en/about-claude/pricing
# on 2026-09-29 (Haiku 4.5 on 2026-09-30). Cost is null for any model with None here or no entry.
PRICE_PER_MTOK = {
    EXTRACTION_MODEL: {"input": 2.0, "output": 10.0},
    "claude-haiku-4-5-20251001": {"input": 1.0, "output": 5.0},
}

# --- Document types ------------------------------------------------------
# Extracted: one model call per document of these types.
EXTRACTABLE_DOC_TYPES = [
    "call_transcript",
    "rfp_response",
    "proposal",
    "draft_sow",
    "draft_contract",
    # Decided 3 Oct (Lina): security answers (SSO, MFA, encryption, certifications) are commitments Delivery and
    # Security inherit. The extraction prompt is generic (doc type passed as text), so no frozen hash changes.
    "security_questionnaire",
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

# --- Evaluation ----------------------------------------------------------
# Jaccard overlap of lowercase alphanumeric word sets (evaluate.py).
MATCH_THRESHOLD = 0.8  # score >= this counts as a match
NEAR_MISS_FLOOR = 0.5  # floor <= score < threshold is reported, not counted

# --- Deal guard ----------------------------------------------------------
# The sealed test deal is deliberately absent until it is released.
ALLOWED_DEALS = [
    "harbour_bank",
    "hard_cases",  # development fixture deal, Day 7 (data/hard_cases/BRIEF.md)
    "practice_cases",  # rules-vs-agent practice set, 3 Oct (data/practice_cases/BRIEF.md)
    "questionnaire_cases",  # security-questionnaire extraction fixture, 10 Oct; extraction only, never in LEDGER_DEALS
]


# Deals the local web UI may show. Narrower than ALLOWED_DEALS: hard_cases is for the pipeline only.
UI_DEALS = [
    "harbour_bank",
]


def check_ui_deals(ui_deals: list, allowed_deals: list) -> None:
    """Raise if any UI deal is not also an allowed deal."""
    extra = [d for d in ui_deals if d not in allowed_deals]
    if extra:
        raise RuntimeError(f"UI_DEALS must be a subset of ALLOWED_DEALS; not allowed: {extra}")


check_ui_deals(UI_DEALS, ALLOWED_DEALS)

# --- Ledger --------------------------------------------------------------
# Development deals the ledger may hold. An allowlist of its own, not ALLOWED_DEALS: widening
# ALLOWED_DEALS for extract.py must never let another deal into the ledger.
LEDGER_DEALS = [
    "harbour_bank",
    "hard_cases",
    "practice_cases",  # frozen 3 Oct (data/practice_cases.sha256); run file pinned below
]

LEDGER_DB_PATH = ROOT / "workspace" / "ledger.sqlite"

# Resolution scenarios (12 Oct block, built 3 Oct): new versions of development sources, plus expected outcomes.
SCENARIOS_DIR = DATA_DIR / "scenarios"


def scenario_path(filename: str) -> Path:
    """A file inside data/scenarios/, or ValueError if it resolves outside it. Never a deal folder."""
    base = (DATA_DIR / "scenarios").resolve()
    path = (base / filename).resolve()
    if not path.is_relative_to(base):
        raise ValueError(f"{filename!r} resolves outside the scenarios folder")
    return path

# Frozen run files the development import reads (docs/BRIEF_2026-10-03.md), pinned by file name. A newer
# run file never replaces these silently: the import refuses until the pin is changed on purpose.
LEDGER_IMPORT_RUN_FILES = {
    "harbour_bank": "extract_harbour_bank_20260930T061113Z.json",
    "hard_cases": "extract_hard_cases_20260930T061133Z.json",
    "practice_cases": "extract_practice_cases_20261003T034401Z.json",  # 3 Oct, $0.031, Lina's Mac
}


def check_ledger_deals(ledger_deals: list, allowed_deals: list) -> None:
    """Raise if any ledger deal is not also an allowed deal."""
    extra = [d for d in ledger_deals if d not in allowed_deals]
    if extra:
        raise RuntimeError(f"LEDGER_DEALS must be a subset of ALLOWED_DEALS; not allowed: {extra}")


check_ledger_deals(LEDGER_DEALS, ALLOWED_DEALS)


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
