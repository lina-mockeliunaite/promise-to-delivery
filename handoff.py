"""Handoff record for Delivery, Customer Success and Support: a saved, immutable snapshot of one review, plus its exports.

Reads the ledger only. No rules, no model, no new extraction: anything the ledger does not hold is left out, not
inferred. A saved version never changes (database triggers); a new save is a new version. The reviewer's decision
changes no issue. For "Proceed with open items" the reviewer ticks the owner of each open issue; those ticks live in
the snapshot only (the issues table is untouched). The view, CSV and printable summary are all rendered from the
saved snapshot, never from the live screen. Snapshots hold no internal keys, IDs, hashes or file paths.
"""

import csv
import html
import io
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import integrity
import ledger_fixes
import workspace

SCHEMA_PATH = Path(__file__).resolve().parent / "handoff_schema.sql"
DECISIONS = {"ready": "Ready for handoff", "proceed": "Proceed with open items", "not_ready": "Not ready"}
ROUTE_LABELS = {"align_documents": "Align the documents", "allowed_exception": "Record an allowed exception",
                "change_or_withdraw_promise": "Change or withdraw the promise"}
CSV_COLUMNS = ["Commitment", "What needs attention", "Status", "Owner", "Note", "Evidence quote", "Source document",
               "Source version"]
STATE_ORDER = {"Needs action": 0, "Needs evidence": 1}
STRENGTH = {"firm": 2, "conditional": 1, "exploratory": 0}


def main_statement(statements: list) -> list:
    """The one statement that best stands for a commitment: the strongest language, the latest document among equals.
    Statements arrive in document order. Empty if there are none."""
    if not statements:
        return []
    best = max(STRENGTH.get(s["language"], -1) for s in statements)
    return [[s for s in statements if STRENGTH.get(s["language"], -1) == best][-1]]


def trigger_statements(statements: list) -> list:
    """The statements that raised an issue. Every rule that raises one runs on firm commitments only, so these are the
    commitment's firm statements; if it has none (an older issue on a commitment that has since changed), its main one."""
    return [s for s in statements if s["language"] == "firm"] or main_statement(statements)


class HandoffError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def ensure_schema(conn) -> None:
    """Create the handoff table and its immutability triggers if this database does not have them yet."""
    have = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE name LIKE 'handoff_versions%'")}
    if not {"handoff_versions", "handoff_versions_immutable_u", "handoff_versions_immutable_d"} <= have:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.commit()
    integrity.ensure_schema(conn)


def validate_decision(decision, reviewer, note, open_issue_ids, confirmed_ids) -> tuple:
    """Check a decision against the open issues. Returns (decision, reviewer, note) cleaned, or raises HandoffError."""
    if decision not in DECISIONS:
        raise HandoffError("Choose a decision: Ready for handoff, Proceed with open items or Not ready.")
    reviewer = (reviewer or "").strip()
    if not reviewer or len(reviewer) > 120:
        raise HandoffError("Add the reviewer's name (up to 120 characters).")
    note = (note or "").strip()
    if len(note) > 2000:
        raise HandoffError("The note can be up to 2,000 characters.")
    if decision == "ready" and open_issue_ids:
        raise HandoffError("This deal can't be ready for handoff while issues are open. "
                           "Choose Proceed with open items or Not ready.")
    if decision == "proceed" and not set(open_issue_ids) <= set(confirmed_ids):
        raise HandoffError("Confirm the owner of every open issue before saving with open items.")
    return decision, reviewer, note


def contract_phrase(label: str, detail: str) -> str:
    """One clean phrase for where a promise sits in the contract: no repetition, no trailing full stop."""
    label, detail = (label or "").strip(), (detail or "").strip()
    prefix = "Not in the contract: the contract says"
    if label.startswith(prefix):  # the card says it twice; a table cell says it once
        return "The contract says" + label[len(prefix):].rstrip(".")
    if detail and (detail.startswith(("In ", "Not in the draft contract")) or detail.lower().startswith(label.lower())):
        return detail.rstrip(".")
    return label


def build_snapshot(conn, slug: str, decision: str, reviewer: str, note: str, confirmed_ids, review_date: str,
                   decided_on: str) -> dict:
    """The content of a handoff, from the ledger as it stands now. Plain language, no keys or IDs."""
    reg = workspace.register(conn, slug)
    did = ledger_fixes.deal_id(conn, slug)
    confirmed = set(confirmed_ids)
    issues, commitments, info = [], [], {}
    for c in reg["commitments"]:
        def cite(items):
            return [{"quote": s["quote"], "source": s["source_name"], "type": s["doc_type_label"], "version": s["version"],
                     "page": s.get("page")} for s in items]
        trigger, main = cite(trigger_statements(c["statements"])), cite(main_statement(c["statements"]))
        for i in c["issues"]:
            info[i["id"]] = (c["name"], i["label"], i["state"])
            issues.append({
                "commitment": c["name"], "attention": i["label"], "why": i["reason"], "state": i["state"],
                "open": i["state"] != "Resolved", "owner": i["owner"],
                "owner_basis": f"confirmed by {reviewer}" if i["id"] in confirmed else "default",
                "next_step": i["next_step"], "note": i["note"] or "", "evidence": trigger,
            })
        commitments.append({
            "promise": c["name"], "status": c["status"], "language": c["language"], "authorisation": c["authorisation"],
            "contract": contract_phrase(c["presence"], c["presence_detail"]), "issue_count": len(c["issues"]),
            "check_note": c["check_note"], "evidence": main,
        })
    issues.sort(key=lambda i: STATE_ORDER.get(i["state"], 2))  # stable: open first, register order kept inside
    exceptions = [{"commitment": c["name"], "evidence": c["authorisation_evidence"]}
                  for c in reg["commitments"] if c["authorisation"] == "Exception approved"]
    names = workspace.document_labels(conn, did)
    history = []
    for fid, route, owner, approved_at, approved_by, rationale in conn.execute(
            "SELECT id, route, owner_function, approved_at, approved_by, rationale FROM fixes"
            " WHERE deal_id = ? AND status = 'approved' ORDER BY id", (did,)).fetchall():
        history.append({
            "route": ROUTE_LABELS.get(route, route), "owner": owner, "date": (approved_at or "")[:10],
            "approved_by": approved_by, "rationale": workspace.plain(rationale, names),
            "addresses": [f"{info[r[0]][0]}: {info[r[0]][1]}" for r in
                          conn.execute("SELECT issue_id FROM fix_issues WHERE fix_id = ? ORDER BY issue_id", (fid,))
                          if r[0] in info],
            "evidence": [{"source": names[sk], "version": vn, "where": workspace.plain(loc, names)} for sk, vn, loc in conn.execute(
                "SELECT so.source_key, v.version_no, e.locator FROM fix_evidence e"
                " JOIN source_versions v ON v.id = e.source_version_id JOIN sources so ON so.id = v.source_id"
                " WHERE e.fix_id = ? ORDER BY e.id", (fid,))],
        })
    sources = [{"document": d["name"], "type": d["doc_type_label"], "version": d["version"], "date": d["date"],
                "included": d["included"]} for d in workspace.documents(conn, slug)]
    return {
        "deal": reg["name"], "scope_note": reg["scope_note"], "review_date": review_date, "freshness": "Up to date",
        "decision": {"value": decision, "label": DECISIONS[decision], "reviewer": reviewer, "date": decided_on, "note": note},
        "issues": issues, "commitments": commitments, "exceptions": exceptions, "history": history, "sources": sources,
        "resolved_means": reg["resolved_means"],
    }


def save(conn, slug: str, decision, reviewer, note, confirmed_ids, review_id=None) -> dict:
    ensure_schema(conn)
    did = ledger_fixes.deal_id(conn, slug)
    fresh = ledger_fixes.freshness(conn, did)
    if fresh["state"] == "Not reviewed":
        raise HandoffError("Run the review before saving the handoff", 409)
    if fresh["state"] == "Review out of date":
        raise HandoffError("Rerun the review before saving the handoff", 409)
    if fresh["reasons"]:  # made under an older hash definition, or its config was never recorded: not comparable
        raise HandoffError("Rerun the review before saving the handoff", 409)
    if review_id is not None and review_id != fresh["review_id"]:
        raise HandoffError("The review has changed. Reload the page and check it before saving.", 409)
    try:
        confirmed = {int(i) for i in confirmed_ids or []}
    except (TypeError, ValueError):
        raise HandoffError("The owner confirmations were not understood.") from None
    reg = workspace.register(conn, slug)
    all_ids = {i["id"] for c in reg["commitments"] for i in c["issues"]}
    open_ids = {i["id"] for c in reg["commitments"] for i in c["issues"] if i["state"] != "Resolved"}
    if not confirmed <= all_ids:
        raise HandoffError("An owner confirmation does not match an issue in this deal.")
    decision, reviewer, note = validate_decision(decision, reviewer, note, open_ids, confirmed)
    decided_on = datetime.now(timezone.utc).date().isoformat()
    snapshot = build_snapshot(conn, slug, decision, reviewer, note, confirmed, (fresh["finished_at"] or "")[:10], decided_on)
    src_hash, ev_hash = conn.execute("SELECT source_set_sha256, decision_evidence_sha256 FROM reviews WHERE id = ?",
                                     (fresh["review_id"],)).fetchone()
    binding = integrity.current_binding(conn, did)  # all three hashes; refused unless the review is current
    saved_id = conn.execute(
        "INSERT INTO handoff_versions (deal_id, version_no, review_id, source_set_sha256, decision_evidence_sha256,"
        " decision, reviewer, decided_on, note, snapshot_json) VALUES (?, (SELECT COALESCE(MAX(version_no), 0) + 1"
        " FROM handoff_versions WHERE deal_id = ?), ?, ?, ?, ?, ?, ?, ?, ?)",
        (did, did, fresh["review_id"], src_hash, ev_hash, decision, reviewer, decided_on, note or None,
         json.dumps(snapshot, sort_keys=True))).lastrowid
    integrity.write_decision_binding(conn, "handoff", saved_id, binding)
    conn.commit()
    return {"version": conn.execute("SELECT MAX(version_no) FROM handoff_versions WHERE deal_id = ?", (did,)).fetchone()[0]}


def _status(conn, did: int, handoff_id: int, review_id: int, src_hash, ev_hash) -> dict:
    """A saved version against the deal now, on its three bound hashes. A version saved before bindings existed is read
    as hash definition 1 from its review: it says "checking rules updated", never "Documents changed"."""
    return integrity.decision_status(conn, did, "handoff", handoff_id, derived=(src_hash, ev_hash, review_id))


def list_versions(conn, slug: str) -> list:
    ensure_schema(conn)
    did = ledger_fixes.deal_id(conn, slug)
    out = []
    for hid, v, d, r, on, rid, sh, eh in conn.execute(
            "SELECT id, version_no, decision, reviewer, decided_on, review_id, source_set_sha256, decision_evidence_sha256"
            " FROM handoff_versions WHERE deal_id = ? ORDER BY version_no DESC", (did,)).fetchall():
        st = _status(conn, did, hid, rid, sh, eh)
        out.append({"version": v, "decision": DECISIONS[d], "reviewer": r, "date": on,
                    "changed_since_saved": not st["current"], "reasons": st["reasons"]})
    return out


def get_version(conn, slug: str, version=None):
    """A saved version as {version, changed_since_saved, handoff}, the latest if no version is given; None if absent."""
    ensure_schema(conn)
    did = ledger_fixes.deal_id(conn, slug)
    sql = ("SELECT version_no, snapshot_json, source_set_sha256, decision_evidence_sha256, id, review_id FROM handoff_versions"
           " WHERE deal_id = ?")
    row = (conn.execute(sql + " AND version_no = ?", (did, version)) if version is not None
           else conn.execute(sql + " ORDER BY version_no DESC LIMIT 1", (did,))).fetchone()
    if row is None:
        return None
    st = _status(conn, did, row[4], row[5], row[2], row[3])
    return {"version": row[0], "changed_since_saved": not st["current"], "reasons": st["reasons"], "handoff": json.loads(row[1])}


# --- Exports (rendered from a saved snapshot only) ------------------------------------------------------------------
def _cell(value) -> str:
    """A CSV cell safe to open in a spreadsheet: text that would read as a formula is prefixed with an apostrophe."""
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


def owner_text(item) -> str:
    return f"{item['owner']} ({item['owner_basis']})"


def source_cell(evidence: dict) -> str:
    """The source document, with its page when the document is a PDF: 'Proposal (page 3)'."""
    return evidence["source"] + (f" (page {evidence['page']})" if evidence.get("page") else "")


def csv_rows(snapshot: dict) -> list:
    """One row per issue (open first), then one row for each commitment with no issue at all."""
    rows = []
    for i in snapshot["issues"]:
        ev = i["evidence"]
        rows.append([i["commitment"], f"{i['attention']}: {i['why']}" if i["why"] else i["attention"], i["state"],
                     owner_text(i), i["note"], "\n".join(e["quote"] for e in ev), "\n".join(source_cell(e) for e in ev),
                     "\n".join(str(e["version"]) for e in ev)])
    for c in snapshot["commitments"]:
        if c["issue_count"] == 0:
            ev = c["evidence"]
            rows.append([c["promise"], "", c["status"], "", c.get("check_note", ""), "\n".join(e["quote"] for e in ev),
                         "\n".join(source_cell(e) for e in ev), "\n".join(str(e["version"]) for e in ev)])
    return rows


def render_csv(snapshot: dict) -> str:
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\r\n")
    writer.writerow(CSV_COLUMNS)
    for row in csv_rows(snapshot):
        writer.writerow([_cell(v) for v in row])
    return "﻿" + out.getvalue()


def export_filename(snapshot: dict, version: int, ext: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9]+", "-", snapshot["deal"]).strip("-")[:60] or "deal"
    return f"handoff-{stem}-v{version}.{ext}"


_CSS = """
:root { color-scheme: light; }
body { font: 15px/1.5 system-ui, sans-serif; color: #1d2329; max-width: 900px; margin: 24px auto; padding: 0 16px; }
h1 { font-size: 24px; margin: 0 0 4px; } h2 { font-size: 18px; margin: 28px 0 8px; border-bottom: 1px solid #dde1e5; padding-bottom: 4px; }
.meta { color: #5b6670; margin: 2px 0; } .decision { font-weight: 650; }
table { width: 100%; border-collapse: collapse; font-size: 14px; } th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid #dde1e5; vertical-align: top; }
th { background: #eef0f2; font-size: 13px; } .item { border: 1px solid #dde1e5; border-left: 4px solid #9b2c2c; border-radius: 6px; padding: 10px 12px; margin: 10px 0; break-inside: avoid; }
.item h3 { margin: 0 0 4px; font-size: 16px; } .item p { margin: 3px 0; } blockquote { margin: 4px 0; padding-left: 10px; border-left: 3px solid #dde1e5; }
cite { display: block; font-style: normal; font-size: 12px; color: #5b6670; padding-left: 13px; } .muted { color: #5b6670; }
@media print { body { margin: 0; max-width: none; } h2 { break-after: avoid; } }
"""


def render_html(snapshot: dict, version: int) -> str:
    e = html.escape
    d = snapshot["decision"]
    parts = [f"<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><title>{e(snapshot['deal'])} handoff, version {version}</title>"
             f"<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"><style>{_CSS}</style></head><body>",
             f"<h1>{e(snapshot['deal'])}: handoff, version {version}</h1>",
             f"<p class=\"decision\">{e(d['label'])}</p>",
             f"<p class=\"meta\">Reviewed by {e(d['reviewer'])} on {e(workspace.short_date(d['date']))} · Review date {e(workspace.short_date(snapshot['review_date']))} · "
             f"Review {e(snapshot['freshness'].lower())} when saved</p>",
             f"<p class=\"meta\">{e(snapshot['scope_note'])}</p>"]
    if d["note"]:
        parts.append(f"<p>{e(d['note'])}</p>")
    open_items = [i for i in snapshot["issues"] if i["open"]]
    parts.append(f"<h2>Open items ({len(open_items)})</h2>")
    if not open_items:
        parts.append("<p class=\"muted\">No open items.</p>")
    for i in open_items:
        parts.append(f"<div class=\"item\"><h3>{e(i['commitment'])}</h3><p><strong>{e(i['attention'])}</strong> · {e(i['state'])}</p>")
        if i["why"]:
            parts.append(f"<p class=\"muted\">{e(i['why'])}</p>")
        parts.append(f"<p>Owner: {e(owner_text(i))}</p>")
        if i["next_step"]:
            parts.append(f"<p>Next step: {e(i['next_step'])}</p>")
        if i["note"]:
            parts.append(f"<p>Note: {e(i['note'])}</p>")
        for ev in i["evidence"]:
            parts.append(f"<blockquote>“{e(ev['quote'])}”</blockquote><cite>{e(workspace.version_label(ev['source'], ev['version'], ev.get('page')))}</cite>")
        parts.append("</div>")
    parts.append("<h2>All commitments</h2><table><thead><tr><th>Promise</th><th>Status</th><th>In the contract</th></tr></thead><tbody>")
    for c in snapshot["commitments"]:
        parts.append(f"<tr><td>{e(c['promise'])}</td><td>{e(c['status'])}</td><td>{e(c['contract'])}</td></tr>")
    parts.append("</tbody></table>")
    if any(c.get("check_note") for c in snapshot["commitments"]):
        parts.append(f"<p class=\"muted\">{e(workspace.CHECK_NOTE)}</p>")
    parts.append("<h2>Approved exceptions</h2>")
    if not snapshot["exceptions"]:
        parts.append("<p class=\"muted\">None.</p>")
    for x in snapshot["exceptions"]:
        parts.append(f"<p><strong>{e(x['commitment'])}</strong><br>{e(x['evidence'])}</p>")
    parts.append("<h2>Fix and decision history</h2>")
    if not snapshot["history"]:
        parts.append("<p class=\"muted\">No fixes recorded.</p>")
    for h in snapshot["history"]:
        ev = "; ".join(f"{workspace.version_label(x['source'], x['version'])} ({x['where']})" for x in h["evidence"]) or "none"
        parts.append(f"<p><strong>{e(h['route'])}</strong> · {e(h['owner'])} · {e(workspace.short_date(h['date']))} · signed off by {e(h['approved_by'])}<br>"
                     f"{e(h['rationale'])}<br><span class=\"muted\">Addresses: {e('; '.join(h['addresses']) or 'none')}."
                     f" Evidence: {e(ev)}</span></p>")
    parts.append("<h2>Reviewed sources</h2><table><thead><tr><th>Document</th><th>Version</th><th>Date</th><th>Used</th></tr></thead><tbody>")
    for s in snapshot["sources"]:
        parts.append(f"<tr><td>{e(s['document'])}</td><td>{e(str(s['version']))}</td><td>{e(workspace.short_date(s['date']))}</td>"
                     f"<td>{'Included' if s['included'] else 'Excluded'}</td></tr>")
    parts.append(f"</tbody></table><p class=\"muted\">{e(snapshot['resolved_means'])}</p></body></html>")
    return "".join(parts)
