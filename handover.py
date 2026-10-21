"""Handover records (16 Oct, after Checkpoint 3 with a Delivery lead; DECISIONS 16 Oct).

Two reviewers (a COO on 15 Oct, a Delivery lead on 16 Oct) asked for visibility, not workflow: see what you are
inheriting, know who has looked at it, read the notes from both sides, open the documents where they already live,
and freeze the record when the handover is complete. This module holds those human records:

- "Seen by <name>" on a finding: someone has looked at it. It is not a decision and never closes or changes anything.
- Two handover notes per deal: the deal owner's (sales) and the accepting Delivery lead's. Latest per role wins.
- A link per document to where it lives (Drive). The tool never copies or edits the file at that link.
- Handover complete: a frozen snapshot of what was handed over. From then on the API refuses every change to the deal.

Everything is append-only (handover_schema.sql) and touches neither issues nor closure_checks, so findings still come
only from the detector and close only on the recheck of a new document version.
"""

import hashlib
import json
from pathlib import Path

import deal_catalogue
import deal_stage
import ledger_fixes

SCHEMA_PATH = Path(__file__).resolve().parent / "handover_schema.sql"
TABLES = ("item_seen", "handover_notes", "document_links", "handover_completions", "deal_signatures", "note_resolutions")
ROLES = {"sales": "Deal owner's handoff note", "delivery": "Delivery acceptance note"}
HANDOVER_FROM = deal_stage.STAGE_INDEX["contracting"]  # deals appear in the handover list from Contracting onwards
FROZEN = "Handover is complete. This deal is frozen and can no longer be changed."


class HandoverError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def ensure_schema(conn) -> None:
    have = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'trigger')")}
    if set(TABLES) <= have and "note_resolutions_append_only_d" in have:
        return
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()


def _has(conn, table: str) -> bool:
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)).fetchone() is not None


def _text(value, what: str, limit: int) -> str:
    value = value.strip() if isinstance(value, str) else ""
    if not value or len(value) > limit:
        raise HandoverError(f"Add {what} (up to {limit:,} characters).")
    return value


def _insert(conn, sql: str, values: tuple) -> int:
    try:
        rid = conn.execute(sql, values).lastrowid
    except BaseException:
        conn.rollback()
        raise
    conn.commit()
    return rid


# --- Frozen or not ---------------------------------------------------------------------------------------------------
def completion(conn, did: int):
    """{'completed_by', 'at'} once the handover is complete, else None."""
    if not _has(conn, "handover_completions"):
        return None
    row = conn.execute("SELECT completed_by, created_at FROM handover_completions WHERE deal_id = ?", (did,)).fetchone()
    return {"completed_by": row[0], "at": row[1]} if row else None


def is_frozen(conn, slug: str) -> bool:
    """True when this deal's handover is complete. Unknown deals are not frozen (the route refuses them itself)."""
    if not _has(conn, "handover_completions"):
        return False
    return conn.execute("SELECT 1 FROM handover_completions h JOIN deals d ON d.id = h.deal_id WHERE d.slug = ?",
                        (slug,)).fetchone() is not None


def _open_for_changes(conn, slug: str) -> int:
    did = ledger_fixes.deal_id(conn, slug)
    ensure_schema(conn)
    if completion(conn, did):
        raise HandoverError(FROZEN, 409)
    return did


# --- Seen by -----------------------------------------------------------------------------------------------------------
def mark_seen(conn, slug: str, issue_id, seen_by) -> dict:
    did = _open_for_changes(conn, slug)
    who = _text(seen_by, "your name", 120)
    try:
        issue_id = int(issue_id)
    except (TypeError, ValueError):
        raise HandoverError("That item is not in this deal.", 404) from None
    if not conn.execute("SELECT 1 FROM issues i JOIN commitments c ON c.id = i.commitment_id WHERE i.id = ? AND c.deal_id = ?",
                        (issue_id, did)).fetchone():
        raise HandoverError("That item is not in this deal.", 404)
    if not conn.execute("SELECT 1 FROM item_seen WHERE issue_id = ? AND seen_by = ?", (issue_id, who)).fetchone():
        _insert(conn, "INSERT INTO item_seen (deal_id, issue_id, seen_by) VALUES (?, ?, ?)", (did, issue_id, who))
    return {"issue_id": issue_id, "seen": seen_for(conn, issue_id)}


def seen_for(conn, issue_id: int) -> list:
    """Everyone who has marked this item as seen, earliest first: [{'by', 'at'}]."""
    if not _has(conn, "item_seen"):
        return []
    return [{"by": b, "at": a} for b, a in
            conn.execute("SELECT seen_by, created_at FROM item_seen WHERE issue_id = ? ORDER BY id", (issue_id,))]


# --- Handover notes ----------------------------------------------------------------------------------------------------
def set_note(conn, slug: str, role, note, entered_by) -> dict:
    if role not in ROLES:
        raise HandoverError("Choose whose note this is: the deal owner's or Delivery's.")
    did = _open_for_changes(conn, slug)
    note, who = _text(note, "the note", 2000), _text(entered_by, "your name", 120)
    _insert(conn, "INSERT INTO handover_notes (deal_id, role, note, entered_by) VALUES (?, ?, ?, ?)", (did, role, note, who))
    return notes(conn, did)


def notes(conn, did: int) -> dict:
    """{'sales': {...} | None, 'delivery': {...} | None}, each {'label', 'note', 'by', 'at'} from the latest row."""
    out = {role: None for role in ROLES}
    if not _has(conn, "handover_notes"):
        return out
    for role in ROLES:
        row = conn.execute("SELECT note, entered_by, created_at FROM handover_notes WHERE deal_id = ? AND role = ?"
                           " ORDER BY id DESC LIMIT 1", (did, role)).fetchone()
        if row:
            out[role] = {"label": ROLES[role], "note": row[0], "by": row[1], "at": row[2]}
    return out


# --- Document links ----------------------------------------------------------------------------------------------------
def set_link(conn, slug: str, source_key, url, set_by) -> dict:
    did = _open_for_changes(conn, slug)
    row = conn.execute("SELECT id FROM sources WHERE deal_id = ? AND source_key = ?", (did, source_key)).fetchone()
    if row is None:
        raise HandoverError("That document is not in this deal.", 404)
    url, who = _text(url, "the link", 2000), _text(set_by, "your name", 120)
    if not url.startswith("https://") or any(ch.isspace() or ord(ch) < 32 for ch in url):
        raise HandoverError("Give the link as a full https:// address, for example the document's Drive link.")
    _insert(conn, "INSERT INTO document_links (deal_id, source_id, url, set_by) VALUES (?, ?, ?, ?)", (did, row[0], url, who))
    return {"source_key": source_key, "link": url}


def links(conn, did: int) -> dict:
    """source_key -> latest link for this deal's documents."""
    if not _has(conn, "document_links"):
        return {}
    out = {}
    for key, url in conn.execute("SELECT s.source_key, l.url FROM document_links l JOIN sources s ON s.id = l.source_id"
                                 " WHERE l.deal_id = ? ORDER BY l.id", (did,)):
        out[key] = url  # later rows win
    return out


# --- Resolved by a note --------------------------------------------------------------------------------------------------
def resolve_by_note(conn, slug: str, issue_id, resolved_by, reason) -> dict:
    """A named person settles an open gap without a document. It is never shown as closed by the documents, and it stops
    counting as soon as the documents change."""
    did = _open_for_changes(conn, slug)
    who, why = _text(resolved_by, "your name", 120), _text(reason, "the reason", 2000)
    try:
        issue_id = int(issue_id)
    except (TypeError, ValueError):
        raise HandoverError("That item is not in this deal.", 404) from None
    row = conn.execute("SELECT s.state FROM issue_current_state s JOIN commitments c ON c.id = s.commitment_id"
                       " WHERE s.issue_id = ? AND c.deal_id = ?", (issue_id, did)).fetchone()
    if row is None:
        raise HandoverError("That item is not in this deal.", 404)
    if row[0] == "Resolved":
        import signed_check  # 21 Oct: a gap closed by a draft that the signed paperwork lacks is open again, and can be addressed by a note
        if issue_id not in signed_check.reopened(conn, did, slug):
            raise HandoverError("This gap is already closed by the documents.", 409)
    _insert(conn, "INSERT INTO note_resolutions (deal_id, issue_id, resolved_by, reason, source_set_sha256) VALUES (?, ?, ?, ?, ?)",
            (did, issue_id, who, why, ledger_fixes.source_set_sha256(conn, did)))
    return note_resolution(conn, did, issue_id)


def note_resolution(conn, did: int, issue_id: int):
    """{'by', 'reason', 'at', 'current'} for the latest note resolution on a gap, or None. current is False once the
    deal's documents have changed since it was recorded."""
    if not _has(conn, "note_resolutions"):
        return None
    row = conn.execute("SELECT resolved_by, reason, created_at, source_set_sha256 FROM note_resolutions WHERE issue_id = ?"
                       " AND deal_id = ? ORDER BY id DESC LIMIT 1", (issue_id, did)).fetchone()
    if row is None:
        return None
    return {"by": row[0], "reason": row[1], "at": row[2], "current": row[3] == ledger_fixes.source_set_sha256(conn, did)}


def note_resolved_ids(conn, did: int) -> set:
    """Open gaps (by the documents) that a current note has resolved. Every count of open gaps leaves these out."""
    if not _has(conn, "note_resolutions"):
        return set()
    current = ledger_fixes.source_set_sha256(conn, did)
    out = set()
    for iid, sha in conn.execute("SELECT n.issue_id, n.source_set_sha256 FROM note_resolutions n WHERE n.deal_id = ? AND n.id ="
                                 " (SELECT MAX(id) FROM note_resolutions m WHERE m.issue_id = n.issue_id)", (did,)):
        if sha == current:
            out.add(iid)
    return out


# --- Signature (old records only, 19 Oct) ---------------------------------------------------------------------------------
def signature(conn, did: int):
    """{'signed_on', 'recorded_by', 'at'} for a signature recorded by a person before 19 Oct, else None. Read only: nothing
    records one any more, and it no longer moves the stage (the stage comes from the documents)."""
    if not _has(conn, "deal_signatures"):
        return None
    row = conn.execute("SELECT signed_on, recorded_by, created_at FROM deal_signatures WHERE deal_id = ?", (did,)).fetchone()
    return {"signed_on": row[0], "recorded_by": row[1], "at": row[2]} if row else None


# --- Handover complete -------------------------------------------------------------------------------------------------
def build_snapshot(conn, slug: str, completed_by: str) -> dict:
    """What was handed over, in plain words: the deal, its stage, the brief, both notes, the documents, and every
    promise that still has an open gap with who has seen it. Built from the same overview every screen reads."""
    import workspace  # local: workspace imports this module for the overview
    reg = workspace.overview(conn, slug)
    by_id = {c["id"]: c for c in reg["commitments"]}
    open_items = []
    # 17 Oct: each promise also carries its exact, code-verified quotes and each gap's verified evidence, so the frozen
    # record can show the comparison itself. Records saved before this simply lack these fields.
    def signed(i):  # 21 Oct, additive: the signed-paperwork check of a gap, in the few fields a screen needs; older snapshots lack it
        sc = i.get("signed_check")
        return {k: sc[k] for k in ("status", "text", "reason", "earlier") if k in sc} if sc else None

    def quotes(c):
        return [{"quote": s["quote"], "source": s["doc_type_label"], "date": s.get("date") or ""}
                for s in c.get("statements", []) if s.get("quote")]
    noted_items = [{"promise": by_id[cid]["name"], "told": by_id[cid]["told"], "contract": by_id[cid]["contract"],
                    "quotes": quotes(by_id[cid]),
                    "first_found": by_id[cid].get("first_found"),  # 20 Oct, additive: older snapshots lack it
                    "findings": [{"finding": i["finding"], "resolved_by_note": i.get("note_resolution"),
                                  "evidence": i.get("evidence"), "catalogue_path": i.get("catalogue_path"), "signed_check": signed(i)}
                                 for i in by_id[cid]["issues"] if i["state"] != "Resolved"]}
                   for cid in reg.get("noted_rows", [])]
    for cid in reg["open_rows"]:
        c = by_id[cid]
        detail = c.get("presence_detail") or ""
        open_items.append({
            "promise": c["name"], "told": c["told"], "contract": c["contract"],
            # Only the code-verified detail ("Not found anywhere in the contract or SOW: ..."), never model prose.
            "contract_detail": detail if detail.startswith("Not found anywhere") else "",
            "told_in": sorted({(s["doc_type_label"], s.get("date") or "") for s in c.get("statements", [])},
                              key=lambda t: t[1], reverse=True),
            "quotes": quotes(c),
            "first_found": c.get("first_found"),  # 20 Oct, additive: where the exact sentence was first found; older snapshots lack it
            "findings": [{"finding": i["finding"], "why": i["reason"], "seen": i.get("seen", []), "signed_check": signed(i),
                          "evidence": i.get("evidence"), "catalogue_path": i.get("catalogue_path"),
                          # a note recorded on the gap (Okay to proceed): who, why, and whether it was still current
                          "note": ({"by": i["decision"].get("by"), "reason": i["decision"].get("reason"),
                                    "current": i["decision"]["status"] == "okay"}
                                   if (i.get("decision") or {}).get("status") in ("okay", "reconfirm") else None)}
                         for i in c["issues"] if i["state"] != "Resolved"],
        })
    return {
        "deal": reg["name"], "completed_by": completed_by, "stage": reg["stage"]["current_label"],
        "brief": reg["brief"], "notes": reg["handover"]["notes"], "scope_note": reg["scope_note"],
        # 20 Oct, additive: how many proposed findings failed verification and were not shown. Older snapshots lack it.
        "check_coverage": {"rejected": reg["check_coverage"]["rejected"]},
        # 21 Oct, additive: the exact version and the SHA-256 of the text Dealshape read (as stored, UTF-8), so the locked record can open
        # that text and prove it is unchanged. Older snapshots lack both and stay plain.
        "documents": [{"name": d["name"], "type": d["doc_type_label"], "version": d["version"], "date": d["date"],
                       "version_date": d["version_date"], "source_version_id": d["source_version_id"],
                       "sha256": conn.execute("SELECT canonical_sha256 FROM source_versions WHERE id = ?", (d["source_version_id"],)).fetchone()[0],
                       "link": d.get("link")} for d in workspace.documents(conn, slug) if d["included"]],
        "open_items": open_items,
        "resolved_by_note": noted_items,
        "resolved": [{"promise": r["commitment"], "finding": r["finding"], "resolved_by": r["resolved_by"]}
                     for r in reg["resolved_findings"]],
        # 20 Oct, additive: what a commitment with a closed gap was told and what the contract says now, so the locked record can show
        # a closed commitment in full. Records locked earlier lack it and show those sections empty.
        "closed_items": [{"promise": c["name"], "quotes": quotes(c), "first_found": c.get("first_found"), "contract": c["contract"],
                          "contract_now": c.get("contract_now"),
                          "signed": [signed(i) for i in c["issues"] if (i.get("signed_check") or {}).get("status") in ("confirmed", "not_confirmed")]}
                         for c in reg["commitments"] if any(i["state"] == "Resolved" for i in c["issues"])],
    }


def complete(conn, slug: str, completed_by) -> dict:
    did = _open_for_changes(conn, slug)
    who = _text(completed_by, "your name", 120)
    stage = deal_stage.deal_stage(conn, slug)["current"]
    if stage is None or deal_stage.STAGE_INDEX[stage] < deal_stage.STAGE_INDEX["signed"]:
        raise HandoverError("The handover can be completed once the deal is signed. Upload the signed contract or SOW first.", 409)
    have = notes(conn, did)
    missing = [ROLES[r].lower() for r in ROLES if have[r] is None]
    if missing:
        raise HandoverError(f"Add the {' and the '.join(missing)} before completing the handover.", 409)
    snapshot = build_snapshot(conn, slug, who)
    _insert(conn, "INSERT INTO handover_completions (deal_id, completed_by, snapshot_json) VALUES (?, ?, ?)",
            (did, who, json.dumps(snapshot, sort_keys=True)))
    return handover(conn, slug)


def handover(conn, slug: str) -> dict:
    """The handover panel: complete or not, both notes, and the frozen snapshot once complete."""
    did = ledger_fixes.deal_id(conn, slug)
    done = completion(conn, did)
    snap = fingerprint = None
    if done:
        stored = conn.execute("SELECT snapshot_json FROM handover_completions WHERE deal_id = ?", (did,)).fetchone()[0]
        snap = json.loads(stored)
        # SHA-256 of the exact stored text: anyone can recompute it, and any later edit would change it. Tamper
        # evidence for this record, not a signature and not proof of who wrote it.
        fingerprint = hashlib.sha256(stored.encode("utf-8")).hexdigest()
    return {"complete": done is not None, "completed_by": done["completed_by"] if done else None,
            "completed_at": done["at"] if done else None, "notes": notes(conn, did), "snapshot": snap,
            "fingerprint": fingerprint, "signature": signature(conn, did),
            "display_names": _display_names(conn, did, slug) if snap else {},
            # 19 Oct: the deal owner, read now (profile, else the Sales note's author), as the deal list shows it; not in the snapshot
            "owner": deal_stage.load_profile(slug).get("owner") or ((notes(conn, did)["sales"] or {}).get("by"))}


def _display_names(conn, did: int, slug: str) -> dict:
    """{promise name as saved in the snapshot: owner-confirmed plain title}. Read at display time and never stored, so the
    snapshot and its fingerprint are untouched. A promise without a title is simply absent."""
    import workspace
    titles = workspace.commitment_titles(slug)
    if not titles:
        return {}
    out = {}
    for cid, key in conn.execute("SELECT id, commitment_key FROM commitments WHERE deal_id = ?", (did,)):
        if key not in titles:
            continue
        for (name,) in conn.execute("SELECT name FROM commitment_assessments WHERE commitment_id = ? AND support_state = 'supported'"
                                    " ORDER BY id DESC LIMIT 1", (cid,)):
            out[workspace.display_name(name, [])] = titles[key]
    return out


# --- Deal list ---------------------------------------------------------------------------------------------------------
def last_updated(conn, did: int) -> str | None:
    """The latest moment anything about the deal changed: a document version, a review, a note, a link, a seen mark."""
    stamps = [conn.execute("SELECT MAX(v.created_at) FROM source_versions v JOIN sources s ON s.id = v.source_id"
                           " WHERE s.deal_id = ?", (did,)).fetchone()[0],
              conn.execute("SELECT MAX(finished_at) FROM reviews WHERE deal_id = ?", (did,)).fetchone()[0]]
    for table in ("item_seen", "handover_notes", "document_links", "handover_completions", "deal_notes"):
        if _has(conn, table):
            stamps.append(conn.execute(f"SELECT MAX(created_at) FROM {table} WHERE deal_id = ?", (did,)).fetchone()[0])
    stamps = [s for s in stamps if s]
    return max(stamps) if stamps else None


def deal_rows(conn, rows: list) -> list:
    """workspace.deal_list() rows plus what the deal list shows: stage, owner, last update, whether the deal is in
    handover (Contracting or later, or already complete), and whether its handover is complete. Newest first."""
    out = []
    for row in rows:
        did = ledger_fixes.deal_id(conn, row["deal"])
        stage = deal_stage.deal_stage(conn, row["deal"])
        profile = deal_stage.load_profile(row["deal"])
        sales = notes(conn, did)["sales"]
        done = completion(conn, did)
        current = stage["current"]
        # Counted per promise, like the stage bar's "gaps started here", so the list and the deal page agree.
        noted = note_resolved_ids(conn, did)
        import open_gaps  # 21 Oct: the one shared reading of "open", including closed gaps the signed paperwork lacks
        live = [(iid, cid) for iid, cid, _type, _subject, _crit in open_gaps.rows(conn, did, row["deal"])]
        needing = {cid for iid, cid in live if iid not in noted}
        open_gaps = len(needing)
        # 19 Oct: promises whose every open gap is settled by a current note, as the deal page's "Addressed by note" rows
        addressed = len({cid for iid, cid in live if iid in noted} - needing)
        out.append({**row, "open_gaps": open_gaps, "addressed_by_note": addressed,
                    "stage": current, "stage_label": stage["current_label"],
                    "owner": profile.get("owner") or (sales["by"] if sales else None),
                    "scope": profile.get("scope") or None,  # 20 Oct: owner-confirmed, never generated
                    "vendor": deal_catalogue.vendor_of(row["deal"]), "vendor_name": deal_catalogue.vendor_name(row["deal"]),
                    "last_updated": last_updated(conn, did),
                    "in_handover": done is not None or (current is not None and deal_stage.STAGE_INDEX[current] >= HANDOVER_FROM),
                    "handover_complete": done is not None})
    out.sort(key=lambda r: r["last_updated"] or "", reverse=True)
    return out
