"""Ledger database: opening, schema creation, and the deal guard.

The ledger holds only deals in config.LEDGER_DEALS. That list is checked here at call time, never
ALLOWED_DEALS, so widening ALLOWED_DEALS for extract.py cannot let another deal in.
"""

import re
import sqlite3
from pathlib import Path

import config

SCHEMA_PATH = Path(__file__).resolve().parent / "ledger_schema.sql"
SCHEMA_VERSION = 2  # 2 (10 Oct): model_v2 checker


class LedgerDealNotAllowed(Exception):
    """Raised when a development deal slug is not in config.LEDGER_DEALS."""


def connect(db_path=None, check_same_thread: bool = True) -> sqlite3.Connection:
    """Open the ledger database with foreign keys on. Defaults to config.LEDGER_DB_PATH.

    check_same_thread=False is for the API only: one connection per request, opened by a dependency that the web
    framework may run on a different worker thread from the endpoint. The connection is never shared between requests.
    """
    path = Path(db_path) if db_path is not None else config.LEDGER_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=check_same_thread)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_schema(conn: sqlite3.Connection) -> None:
    """Create all tables, triggers and views on an empty database."""
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()


def schema_version(conn: sqlite3.Connection):
    """The stored schema version, or None if the schema has not been created."""
    has_meta = conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'schema_meta'").fetchone()
    if not has_meta:
        return None
    row = conn.execute("SELECT value FROM schema_meta WHERE key = 'schema_version'").fetchone()
    return int(row[0]) if row else None


def open_ledger(db_path=None) -> sqlite3.Connection:
    """Connect, creating the schema if the database is new. Raises if it holds another schema version."""
    conn = connect(db_path)
    version = schema_version(conn)
    if version is None:
        create_schema(conn)
    elif version != SCHEMA_VERSION:
        conn.close()
        raise RuntimeError(f"ledger schema_version is {version}, expected {SCHEMA_VERSION}; rebuild the database")
    return conn


def require_ledger_deal(slug: str) -> str:
    """Return the slug if it is in config.LEDGER_DEALS or config.V2_DEALS, else raise. Exact match; ALLOWED_DEALS is
    never consulted."""
    if slug not in config.LEDGER_DEALS and slug not in config.V2_DEALS:
        raise LedgerDealNotAllowed(f"Deal {slug!r} is not in LEDGER_DEALS {config.LEDGER_DEALS}; refusing to write it.")
    return slug


def create_development_deal(conn: sqlite3.Connection, slug: str, display_name=None, commit: bool = True) -> int:
    """Insert a development deal and return its id. The slug must be in config.LEDGER_DEALS.

    commit=False leaves the transaction open, so a caller can write a whole import atomically.
    """
    require_ledger_deal(slug)
    cur = conn.execute(
        "INSERT INTO deals (slug, kind, display_name) VALUES (?, 'development', ?)",
        (slug, display_name or slug),
    )
    if commit:
        conn.commit()
    return cur.lastrowid


def discover_run_files(results_dir=None) -> dict:
    """Latest extract_{slug}_<timestamp>.json per slug in LEDGER_DEALS. Names only; no file is opened.

    Lookalike names (copies, eval_/regression_ prefixes, "latest") never match, and slugs outside
    LEDGER_DEALS are never looked for.
    """
    base = Path(results_dir) if results_dir is not None else config.RESULTS_DIR
    if not base.is_dir():
        return {}
    found = {}
    for slug in config.LEDGER_DEALS:
        pattern = re.compile(rf"extract_{re.escape(slug)}_\d{{8}}T\d{{6}}Z\.json")
        names = sorted(p.name for p in base.iterdir() if p.is_file() and pattern.fullmatch(p.name))
        if names:
            found[slug] = base / names[-1]  # fixed-width UTC timestamps sort chronologically
    return found
