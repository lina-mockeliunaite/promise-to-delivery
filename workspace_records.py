"""Workspace records for the redesigned overview (built 9 Oct, docs/BRIEF_2026-10-06_layout.md).

- The deal note: one or two lines typed by a person, never generated, with the one decision deadline per deal.
- "Must fix before signing": a per-finding flag with name and reason. It never changes the finding. It stays visible
  when the finding later resolves or the review goes out of date, until a named person clears it with a reason.

"Okay to proceed" is integrity.record_accepted_risk (bound to the three hashes, so it can need re-confirmation).
Everything here is append-only (workspace_records_schema.sql) and touches neither issues nor closure_checks.
"""

import re
from pathlib import Path

import integrity
import ledger_fixes

SCHEMA_PATH = Path(__file__).resolve().parent / "workspace_records_schema.sql"
TABLES = ("deal_notes", "signing_flags", "flag_clearances")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


class RecordError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def ensure_schema(conn) -> None:
    have = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'trigger')")}
    if set(TABLES) <= have and "flag_clearances_append_only_d" in have:
        return
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()


def _has(conn, table: str) -> bool:
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)).fetchone() is not None


def _text(value, what: str, limit: int) -> str:
    value = (value or "").strip() if isinstance(value, str) or value is None else ""
    if not value or len(value) > limit:
        raise RecordError(f"Add {what} (up to {limit:,} characters).")
    return value


def _issue_in_deal(conn, did: int, issue_id) -> int:
    try:
        issue_id = int(issue_id)
    except (TypeError, ValueError):
        raise RecordError("That finding is not in this deal.", 404) from None
    if not conn.execute("SELECT 1 FROM issues i JOIN commitments c ON c.id = i.commitment_id WHERE i.id = ? AND c.deal_id = ?",
                        (issue_id, did)).fetchone():
        raise RecordError("That finding is not in this deal.", 404)
    return issue_id


def _insert(conn, sql: str, values: tuple) -> int:
    try:
        rid = conn.execute(sql, values).lastrowid
    except BaseException:
        conn.rollback()
        raise
    conn.commit()
    return rid


# --- Deal note and deadline ------------------------------------------------------------------------------------------
def set_deal_note(conn, slug: str, note, entered_by, deadline=None) -> int:
    did = ledger_fixes.deal_id(conn, slug)
    ensure_schema(conn)
    note = _text(note, "the deal note", 300)
    who = _text(entered_by, "who wrote the note", 120)
    deadline = (deadline or "").strip() or None
    if deadline is not None and not DATE.fullmatch(deadline):
        raise RecordError("Give the decision deadline as a date.")
    return _insert(conn, "INSERT INTO deal_notes (deal_id, note, entered_by, deadline) VALUES (?, ?, ?, ?)",
                   (did, note, who, deadline))


def deal_note(conn, did: int):
    """{'note', 'entered_by', 'deadline', 'at'} for the latest note, or None."""
    if not _has(conn, "deal_notes"):
        return None
    row = conn.execute("SELECT note, entered_by, deadline, created_at FROM deal_notes WHERE deal_id = ? ORDER BY id DESC LIMIT 1",
                       (did,)).fetchone()
    return {"note": row[0], "entered_by": row[1], "deadline": row[2], "at": row[3]} if row else None


# --- Must fix before signing -----------------------------------------------------------------------------------------
def flag_must_fix(conn, slug: str, issue_id, flagged_by, reason) -> int:
    did = ledger_fixes.deal_id(conn, slug)
    ensure_schema(conn)
    issue_id = _issue_in_deal(conn, did, issue_id)
    who, why = _text(flagged_by, "who is flagging this", 120), _text(reason, "the reason", 2000)
    if active_flag(conn, issue_id):
        raise RecordError("This finding is already marked Must fix before signing.", 409)
    return _insert(conn, "INSERT INTO signing_flags (deal_id, issue_id, flagged_by, reason) VALUES (?, ?, ?, ?)",
                   (did, issue_id, who, why))


def clear_flag(conn, slug: str, flag_id, cleared_by, reason) -> int:
    did = ledger_fixes.deal_id(conn, slug)
    ensure_schema(conn)
    try:
        flag_id = int(flag_id)
    except (TypeError, ValueError):
        raise RecordError("That flag is not in this deal.", 404) from None
    row = conn.execute("SELECT 1 FROM signing_flags WHERE id = ? AND deal_id = ?", (flag_id, did)).fetchone()
    if row is None:
        raise RecordError("That flag is not in this deal.", 404)
    if conn.execute("SELECT 1 FROM flag_clearances WHERE flag_id = ?", (flag_id,)).fetchone():
        raise RecordError("This flag has already been cleared.", 409)
    who, why = _text(cleared_by, "who is clearing the flag", 120), _text(reason, "the reason", 2000)
    return _insert(conn, "INSERT INTO flag_clearances (flag_id, cleared_by, reason) VALUES (?, ?, ?)", (flag_id, who, why))


def active_flag(conn, issue_id: int):
    """The uncleared Must-fix flag on a finding, or None. Independent of the finding's state and of freshness."""
    if not _has(conn, "signing_flags"):
        return None
    row = conn.execute("SELECT f.id, f.flagged_by, f.reason, f.created_at FROM signing_flags f WHERE f.issue_id = ?"
                       " AND NOT EXISTS (SELECT 1 FROM flag_clearances c WHERE c.flag_id = f.id) ORDER BY f.id DESC LIMIT 1",
                       (issue_id,)).fetchone()
    return {"flag_id": row[0], "by": row[1], "reason": row[2], "at": row[3]} if row else None


# --- Okay to proceed (integrity's accepted risk) and the decision a finding shows -------------------------------------
def okay_to_proceed(conn, slug: str, issue_id, by, reason) -> int:
    try:
        return integrity.record_accepted_risk(conn, slug, int(issue_id), by, reason)
    except integrity.IntegrityError as exc:
        raise RecordError(str(exc), exc.status) from None
    except (TypeError, ValueError):
        raise RecordError("That finding is not in this deal.", 404) from None


def decision_for(conn, slug: str, issue_id: int) -> dict:
    """What the finding's decision line shows. Never derived from, and never changes, the finding's state.

    {'status': 'none' | 'okay' | 'reconfirm', 'by', 'reason', 'reasons', 'must_fix': flag or None}"""
    out = {"status": "none", "must_fix": active_flag(conn, issue_id)}
    if integrity._has(conn, "accepted_risks"):
        row = conn.execute("SELECT id, accepted_by, rationale, created_at FROM accepted_risks WHERE issue_id = ? ORDER BY id DESC LIMIT 1",
                           (issue_id,)).fetchone()
        if row:
            st = integrity.decision_status(conn, ledger_fixes.deal_id(conn, slug), "accepted_risk", row[0])
            out.update({"status": "okay" if st["current"] else "reconfirm", "by": row[1], "reason": row[2], "at": row[3],
                        "reasons": st["reasons"]})
    return out
