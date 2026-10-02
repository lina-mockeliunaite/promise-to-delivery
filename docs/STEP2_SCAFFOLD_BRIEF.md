# Step two: read-only local scaffold (brief for Claude Code)

*Written 2 Oct 2026 for the 1 Oct block (carried over). Plan: `docs/PLAN_v3.4.md`. Architecture: DECISIONS.md, 2026-09-30, Revision v3.*

## Goal

A local web page that shows the permitted Harbour Bank source list and the latest saved extraction results, clearly labelled as intermediate. Read-only. Proves the frontend → API → existing modules path and the seal at runtime.

## Out of scope today

No model calls. No uploads, no `workspace/`, no SQLite, no cache. No change to `extract.py`, `schema.py`, `evaluate.py`, `regression.py`, `check_quotes.py`, prompts or labels. No styling beyond calm and readable.

## Backend

- FastAPI app in a new module (propose the name), served by uvicorn bound to `127.0.0.1` only.
- New dependencies `fastapi`, `uvicorn`, plus `httpx` for tests. Pin exact installed versions in `requirements.txt`.
- Deals shown in the UI: a new `UI_DEALS = ["harbour_bank"]` in `config.py`, checked at import to be a subset of `ALLOWED_DEALS`. `ALLOWED_DEALS`, `deal_dir()`, `docs_dir()` and `doc_path()` stay unchanged.
- GET routes only:
  - `/api/deals` → the UI deals.
  - `/api/deals/{deal}/sources` → for each manifest entry: source ID, file name, document type, date, and whether it is extracted or reference-only (from `config.py` lists). Read through `config.doc_path(deal, "manifest.json")`. Never anything under `labels/`.
  - `/api/deals/{deal}/results/latest` → the newest `results/extract_{deal}_*.json`, returned with `"intermediate": true`. Only `extract_*.json`; never eval, regression or baseline files.
- Any deal not in `UI_DEALS` → 404 with a generic message that does not echo the requested name. The check runs before any filesystem call.
- No route accepts a file path. No folder is served except `frontend/dist/`, mounted explicitly.

## Frontend

- `frontend/`: React with Vite. One page: deal name, sources table, extracted statements table (source, quote, language, speaker).
- Banner above results: "Intermediate output: extracted statements, not reviewed findings."
- Loading, empty and error states visible. Status shown in text as well as colour.
- Dev: Vite proxy `/api` → `127.0.0.1:8000`. Built files served by FastAPI from `frontend/dist/` only.

## Seal tests (`tests/test_api.py`)

Tests must never touch the real `data/coral_pay/` path. Point the app at a temporary data folder (monkeypatch `config.DATA_DIR` and `config.RESULTS_DIR`) holding a fake `harbour_bank` and a decoy `coral_pay` folder with a canary file. Assert:

1. `/api/deals/coral_pay/sources` and `/results/latest` → 404, canary text never appears in any response.
2. Traversal variants → 404 or 422, no canary: `harbour_bank/../coral_pay`, URL-encoded `..%2Fcoral_pay`, `%2e%2e`, a trailing-slash variant, a case variant (`Coral_Pay`).
3. `hard_cases` → 404 (allowed for the pipeline, not shown in the UI).
4. No labels: no response contains label content from the fake `labels/` folder.
5. Static mount does not serve repo or data files: `/config.py`, `/data/catalogue.json`, `/.env` → 404.
6. `UI_DEALS` is a subset of `ALLOWED_DEALS` and does not contain `coral_pay`.

Existing 75 tests must still pass.

## Housekeeping

- `.gitignore` add: `workspace/`, `*.db`, `*.sqlite*`, `node_modules/`, `frontend/dist/`, `frontend/.vite/`, `scratch_*`.
- `WHERE_I_STOPPED.md`: point to `docs/PLAN_v3.4.md` (renamed from v3.3); add a "Local app launch" section with the exact commands.

## Process

Per `CLAUDE.md`: first propose the file list and intended change set, wait for Lina's go-ahead, build, then report what changed and which checks ran. Lina runs Git. Split if needed: backend and tests first, frontend second.
