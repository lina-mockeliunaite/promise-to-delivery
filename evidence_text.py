"""Plain sentences for approval and contract evidence, built from structured ledger fields, not from the rules' prose.

The rules write evidence as compact system text ("CAP-021/SG/Polygon/NUSD/real_time: beta; requires named approval; ...",
a raw pricing-note table row). The ledger also keeps the structured facts behind that text: the catalogue paths the
verdict covered, the cited pricing-note row, the approver and conditions, the term sets and the document references.
This module turns those into sentences a delivery reader can use. Read-only: no rules run, no model call. The one
file it reads besides the ledger is data/catalogue.json, the same capability catalogue the rules use.
"""

import json

import config
import rules
import terms

MODE_WORDS = {"real_time": "real-time", "batch": "batch"}
STATUS_PHRASES = {"generally_available": "generally available", "beta": "in beta", "roadmap": "on the roadmap"}
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November",
          "December"]
CATALOGUE_PATH = config.DATA_DIR / "catalogue.json"
_cache = {}


def load_catalogue():
    """The capability catalogue, re-read when the file changes; None if it cannot be read (callers then say less)."""
    try:
        stamp = CATALOGUE_PATH.stat().st_mtime_ns
        if _cache.get("stamp") != stamp:
            _cache.update(stamp=stamp, data=json.loads(CATALOGUE_PATH.read_text(encoding="utf-8")))
        return _cache["data"]
    except (OSError, ValueError):
        return None


def long_date(iso) -> str:
    try:
        y, m, d = (int(x) for x in str(iso).split("-"))
        return f"{d} {MONTHS[m - 1]} {y}"
    except (ValueError, IndexError):
        return str(iso or "")


def region_name(code: str) -> str:
    return (terms.REGION_NAMES.get(code) or [code])[0].title()


def representative_terms(terms_json):
    """The first member term set of a consolidation snapshot, as the rules read it."""
    members = (terms_json or {}).get("members") or []
    sets = [m["term_set"] for m in members if m.get("term_set")]
    return sets[0] if sets else None


def _leaf(catalogue: dict, path: str):
    """(entry or None, parts) for a catalogue path 'CAP-021/SG/Polygon/NUSD/real_time'."""
    parts = path.split("/")
    cap = next((c for c in catalogue["capabilities"] if c["id"] == parts[0]), None)
    if cap is None or len(parts) < 2:
        return None, parts, None
    node = cap["regions"].get(parts[1])
    rest = parts[2:]
    if node is not None and "networks" in node:
        for key, field in zip(rest, ("networks", "assets", "modes")):
            node = (node.get(field) or {}).get(key)
            if node is None:
                break
    return node, parts, cap


def scope_phrase(cap: dict, parts: list, entry) -> str:
    name = cap["name"] if cap else parts[0]
    where = f" in {region_name(parts[1])}" if len(parts) > 1 else ""
    if len(parts) >= 5:
        return f"{name} on {parts[2]} ({parts[3]}, {MODE_WORDS.get(parts[4], parts[4])}){where}"
    return f"{name}{where}"


def _matching_limit(entry, quantity):
    """(limit, unit, period) when the entry has a limit in the unit and period the promise uses."""
    for name, limit in ((entry or {}).get("limits") or {}).items():
        m = rules.LIMIT.fullmatch(name)
        if quantity and m and isinstance(limit, (int, float)) and quantity.get("unit") == m.group(1) \
                and quantity.get("period") == m.group(2):
            return limit, m.group(1), m.group(2)
    return None


def catalogue_sentences(catalogue: dict, paths: list, ts) -> tuple:
    """([sentence, ...], {kind, ...}) for the catalogue leaves a verdict covered."""
    out, kinds = [], set()
    unlisted_rule = catalogue.get("unlisted_rule") if catalogue.get("coverage") == "complete" else None
    quantity = (ts or {}).get("quantity")
    for path in paths:
        entry, parts, cap = _leaf(catalogue, path)
        kind, _ = rules._leaf_verdict(entry, ts or {}, unlisted_rule)
        kinds.add(kind)
        scope = scope_phrase(cap, parts, entry)
        if entry is None and kind == "absolute":
            out.append(f"Catalogue: {scope} is not listed, and the catalogue says anything unlisted is not offered, "
                       "so no exception can cover it.")
        elif entry is None:
            out.append(f"Catalogue: {scope} is not listed, so it needs named approval.")
        elif kind == "absolute":
            out.append(f"Catalogue: {scope} is not sellable.")
        elif kind == "approval" and entry.get("sellable") == "requires_named_approval":
            bits = [f"is {STATUS_PHRASES.get(entry.get('status'), entry.get('status'))}", "needs named approval"]
            if entry.get("roadmap_date"):
                bits.append(f"general availability planned {long_date(entry['roadmap_date'])}")
            out.append(f"Catalogue: {scope} {', '.join(bits)}.")
        elif kind == "approval":
            limit, unit, period = _matching_limit(entry, quantity) or (None, "", "")
            out.append(f"Catalogue: {scope}: {quantity['value']:,} {unit} per {period} is above the standard limit "
                       f"of {limit:,}.")
        else:
            sentence = f"Catalogue: {scope} is {STATUS_PHRASES.get(entry.get('status'), entry.get('status'))} and standard."
            found = _matching_limit(entry, quantity)
            if found:
                sentence += f" {quantity['value']:,} {found[1]} per {found[2]} is within the standard limit of {found[0]:,}."
            out.append(sentence)
    return out, kinds


def pricing_note_cell(row: str) -> str:
    """The approval cell of a pricing-note row (the last cell of a table row), or the whole line if it is not a row."""
    cells = [c.strip() for c in row.strip().strip("|").split("|")] if "|" in row else [row.strip()]
    text = (cells[-1] if len(cells) > 1 else cells[0]).strip().rstrip(".")
    return text[:1].lower() + text[1:] if text[1:2].islower() else text


def approval_text(authorisation, language, refs, terms_json) -> str:
    """The approval evidence for a commitment, in plain sentences. Empty if the rules have not assessed it."""
    refs = refs or {}
    if authorisation == "not_assessed":
        return ""
    if authorisation is None:
        return f"Approval isn't assessed for a {language} promise."
    ts = representative_terms(terms_json)
    catalogue = load_catalogue()
    paths = refs.get("catalogue") or []
    notes = [s for s in refs.get("source_versions", []) if s.get("role") == "approval_evidence"]
    searched = any(s.get("role") == "approval_evidence_searched" for s in refs.get("source_versions", []))
    sentences, kinds = [], set()
    if paths and catalogue:
        sentences, kinds = catalogue_sentences(catalogue, paths, ts)
        if len(paths) > 1:
            sentences.insert(0, "The promise doesn't state every term, so each listed option was checked.")
            if len(kinds) > 1:
                sentences.append("The answers differ, so the verdict can't be confirmed from the catalogue.")
    elif not paths:
        sentences.append("Catalogue: no entry for this promise.")
    if authorisation == "standard_authorised":
        return " ".join(sentences)
    if kinds == {"absolute"}:
        sentences.append("A named exception can't cover this: change or withdraw the promise.")
    elif authorisation == "exception_approved":
        approval = refs.get("approval") or {}
        sentences.append(f"Pricing note: named exception approved by {approval.get('approver', 'a named approver')}.")
        if approval.get("conditions"):
            sentences.append("Conditions: " + "; ".join(c.rstrip(".") for c in approval["conditions"])
                             + ". Each must be carried into the contract.")
    elif authorisation == "no_approval_evidence":
        row = notes[0].get("line") if notes else None
        sentences.append(f"Pricing note: {pricing_note_cell(row)}." if row else "Pricing note: names no approval for this scope.")
    elif authorisation == "unknown_needs_review":
        if not paths:
            sentences.append("Approval isn't inferred from implementation scope or from inclusion in the contract.")
            if searched:
                sentences.append("The pricing note was searched and names nothing for it.")
        elif notes and notes[0].get("line"):
            sentences.append("Pricing note: approval wording found, but no approver is named.")
        elif not notes and len(kinds) <= 1:
            sentences.append("No pricing and services note among the selected documents.")
    return " ".join(sentences)
