"""Rule-based assessment: authorisation, contractual presence and issues per commitment. Pure functions: no database,
no files, no model calls. The same inputs always give the same findings, with a citation for every verdict.

Inputs are a consolidation plan (ledger_consolidate.plan_review), the review's source versions and contract chain
(references.py), the catalogue and the vocabulary. Output is one assessment per commitment, with its issues, each
issue's closure criteria and its `raised` closure check, and links between commitments. The write path stores them.

Principles (DESIGN.md, docs/LEDGER_SCHEMA.md, docs/BRIEF_2026-10-04.md):
- Approval is never inferred from confident language or from appearing in a proposal, SOW or contract. Only the
  catalogue and the pricing and services note count.
- Anything the complete catalogue does not list is an absolute limit; an exception cannot override it.
- Authorisation is assessed for firm commitments only; exploratory and conditional ones get None (not applicable).
- An incomplete commitment never gets a confirmed contract gap, only "needs evidence". Its authorisation stands only
  if every completion of the missing terms gives the same catalogue verdict.
- A missing or unresolved reference makes an absence uncertain wherever its topic could cover the commitment.
- Nothing here reads 'not_assessed' as 'absent'. Without a draft contract, presence stays 'not_assessed'.
"""

import re
from dataclasses import dataclass, field

import references
import terms

CRITERIA_VERSION = 1
APPROVAL_EVIDENCE_TYPES = ("pricing_services_note",)
CONTRACT_EVIDENCE_TYPES = ("draft_contract", "draft_sow")
LIMIT = re.compile(r"max_(\w+)_per_(\w+)")
NEGATIVE = re.compile(r"\b(?:no|not|without|declined|rejected|refused)\b[^|\n]*\b(?:approv\w*|exceptions?)\b", re.I)
POSITIVE = re.compile(r"\b(?:exception approved|approved exception|named approval (?:granted|given)|approved for)\b", re.I)
APPROVER = re.compile(r"\bapproved by\s+([A-Z][\w.'-]*(?:\s+[A-Z][\w.'-]*)*(?:\s*\([^)]*\))?)|\bapprover:\s*([^|;\n]+)", re.I)
CONDITIONS = re.compile(r"\b(?:subject to|conditional on|provided that|only if|until|limited to)\b[^|\n]*", re.I)
GLOBAL_NO_EXCEPTION = re.compile(r"\bno (?:named )?exceptions?\b[^.\n]*\bapproved\b", re.I)
# A spreadsheet cell whose formula has no stored value or an error (adapters.NO_VALUE, 9 Oct). In the approval cell
# of a scoped row it means the note cannot say either way: needs evidence, never approved and never "not approved".
NO_STORED_VALUE = "[no stored value]"
WHEN_LABELS = {"launch": "at launch", "end_of_first_year": "by end of first year"}


# --- Small helpers ----------------------------------------------------------------------------------------------

def scope_text(ts: dict) -> str:
    """The promised terms in words, for reasons and criteria."""
    parts = [ts.get("network"), ts.get("asset"), (ts.get("mode") or "").replace("_", " ") or None, ts.get("region")]
    q = ts.get("quantity")
    if q:
        parts.append(f"{'up to ' if q.get('bound') == 'max' else ''}{q['value']:,} {q.get('unit') or '?'} per {q.get('period') or '?'}")
        parts += [WHEN_LABELS.get(w, w) for w in ts.get("when", [])]
    return ", ".join(p for p in parts if p)


def must_cover(ts: dict, dates=()) -> dict:
    """The promised terms an approval or a contract term must cover. Dates promised in the quotes are included."""
    keep = ("promise_type", "capability", "network", "asset", "mode", "region", "quantity", "when", "go_live_date")
    out = {k: ts[k] for k in keep if ts.get(k) not in (None, [], {})}
    if dates:
        out["dates"] = sorted(set(dates))
    return out


def readable_date(value: str) -> str:
    """'2027-03-31' -> '31 Mar 2027'; '--12-01' (no year in the quote) -> '1 Dec'; anything else unchanged."""
    m = re.fullmatch(r"(\d{4}|-)-(\d{2})-(\d{2})", value)
    if not m:
        return value
    month = terms.MONTHS[int(m.group(2)) - 1][:3].capitalize()
    return f"{int(m.group(3))} {month}" + ("" if m.group(1) == "-" else f" {m.group(1)}")


def _number_forms(value) -> list:
    return [f"{value:,}", str(value)] if isinstance(value, int) else [str(value)]


# --- Catalogue --------------------------------------------------------------------------------------------------

@dataclass
class CatalogueVerdict:
    kind: str                       # standard | approval | absolute | varies | none
    paths: list = field(default_factory=list)
    reasons: list = field(default_factory=list)


def _leaf_verdict(entry, ts: dict, unlisted_rule=None):
    if entry is None:
        if unlisted_rule:
            return "absolute", "not listed; catalogue rule: " + unlisted_rule
        return "approval", "not listed, and the catalogue does not declare that unlisted items are not offered"
    if entry.get("sellable") == "not_sellable":
        return "absolute", f"{entry.get('status')}; not sellable"
    if entry.get("sellable") == "requires_named_approval":
        ga = f"; planned GA {entry['roadmap_date']}" if entry.get("roadmap_date") else ""
        return "approval", f"{entry.get('status')}; requires named approval{ga}"
    q = ts.get("quantity")
    for name, limit in (entry.get("limits") or {}).items():
        m = LIMIT.fullmatch(name)
        if q and m and isinstance(limit, (int, float)) and q.get("unit") == m.group(1) and q.get("period") == m.group(2):
            if q["value"] > limit:
                return "approval", f"{q['value']:,} {m.group(1)} per {m.group(2)} exceeds the standard limit of {limit:,}"
            return "standard", f"{entry.get('status')}; standard; {q['value']:,} within the limit of {limit:,}"
    return "standard", f"{entry.get('status')}; standard"


def catalogue_verdict(catalogue: dict, ts: dict) -> CatalogueVerdict:
    """The catalogue's verdict for a term set, over every completion of the terms it does not state."""
    cap_id = ts.get("capability")
    cap = next((c for c in catalogue["capabilities"] if c["id"] == cap_id), None)
    if cap is None:
        return CatalogueVerdict("none")
    leaves = []
    regions = [ts["region"]] if ts.get("region") else sorted(cap["regions"])
    for region in regions:
        r = cap["regions"].get(region)
        if r is None:
            leaves.append((f"{cap_id}/{region}", None))
            continue
        if "networks" not in r:
            leaves.append((f"{cap_id}/{region}", r))
            continue
        networks = [ts["network"]] if ts.get("network") else sorted(r["networks"])
        for network in networks:
            n = r["networks"].get(network)
            if n is None:
                leaves.append((f"{cap_id}/{region}/{network}", None))
                continue
            assets = [ts["asset"]] if ts.get("asset") else sorted(n["assets"])
            for asset in assets:
                a = n["assets"].get(asset)
                if a is None:
                    leaves.append((f"{cap_id}/{region}/{network}/{asset}", None))
                    continue
                modes = [ts["mode"]] if ts.get("mode") else sorted(a["modes"])
                for mode in modes:
                    leaves.append((f"{cap_id}/{region}/{network}/{asset}/{mode}", a["modes"].get(mode)))
    unlisted_rule = catalogue.get("unlisted_rule") if catalogue.get("coverage") == "complete" else None
    verdicts = [(path, *_leaf_verdict(entry, ts, unlisted_rule)) for path, entry in leaves]
    kinds = {k for _, k, _ in verdicts}
    return CatalogueVerdict(kinds.pop() if len(kinds) == 1 else "varies",
                            [p for p, _, _ in verdicts], [f"{p}: {why}" for p, _, why in verdicts])


# --- Pricing and services note ----------------------------------------------------------------------------------

def _scoped_rows(note: references.Version, ts: dict, cap_name: str) -> list:
    """Lines of the note about this capability and this exact scope (network, mode, quantity where stated)."""
    rows = []
    for line in note.text.splitlines():
        if not (ts["capability"] in line or cap_name.lower() in line.lower()):
            continue
        if ts.get("network") and not re.search(rf"\b{re.escape(ts['network'])}\b", line):
            continue
        if ts.get("mode") and not re.search("|".join(terms.MODE_PHRASES[ts["mode"]]), line, re.I):
            continue
        q = ts.get("quantity")
        if q and not any(f in line for f in _number_forms(q["value"])):
            continue  # a limit row that does not name the promised number says nothing about approving it
        rows.append(line.strip())
    return rows


def note_finding(notes: list, ts: dict, cap_name: str):
    """(authorisation, cited line, note version) from the pricing notes, for a scope that needs named approval."""
    for note in notes:
        rows = _scoped_rows(note, ts, cap_name)
        for row in rows:
            if "|" in row and row.strip().strip("|").split("|")[-1].strip() == NO_STORED_VALUE:
                return "value_missing", row, note
        for row in rows:
            if NEGATIVE.search(row):
                return "no_approval_evidence", row, note
        for row in rows:
            if POSITIVE.search(row):
                if not APPROVER.search(row):
                    return "approval_without_approver", row, note
                return "exception_approved", row, note
        for line in note.text.splitlines():
            # A deal-wide statement only: a table row, or a line about a named capability, speaks for that row alone.
            if GLOBAL_NO_EXCEPTION.search(line) and "|" not in line and not re.search(r"\bCAP-\d+", line):
                return "no_approval_evidence", line.strip(), note
    if notes:
        return "no_approval_evidence", None, notes[0]
    return "unknown_needs_review", None, None


# --- Assessment -------------------------------------------------------------------------------------------------

@dataclass
class Assessment:
    authorisation: str | None
    authorisation_evidence: str
    evidence_refs: dict
    contractual_presence: str
    presence_detail: str
    issues: list = field(default_factory=list)
    links: list = field(default_factory=list)       # (from_key, to_key, link_type, basis)


def _representative(c: dict):
    sets = [m["term_set"] for m in c["terms"]["members"] if m["term_set"]]
    return sets[0] if sets else None


def _authorisation(c, ts, catalogue, vocab, notes):
    """(authorisation, evidence text, evidence refs, absolute_limit, unmet, note version, cited row)."""
    refs = {"catalogue": [], "source_versions": []}
    if c["language"] != "firm":
        return None, f"not applicable: {c['language']}", refs, False, [], None, None
    cap_id = ts.get("capability") if ts else None
    cap = vocab.capabilities.get(cap_id)
    if cap is None:
        searched = sorted({w.lower() for w in re.findall(r"[A-Za-z]{4,}", c.get("quote_text", ""))
                           if w.lower() not in references.TOPIC_STOPWORDS})[:8]
        evidence = ("Attempted match: the catalogue lists capabilities only and has no entry for this promise; "
                    + (f"pricing note {notes[0].source_key} searched" if notes else "no pricing and services note selected")
                    + (f" for: {', '.join(searched)}" if searched else "")
                    + ". Approval is not inferred from implementation scope or from contractual inclusion.")
        if notes:
            refs["source_versions"].append({"source_version_id": notes[0].id, "source_key": notes[0].source_key,
                                            "role": "approval_evidence_searched"})
        return "unknown_needs_review", evidence, refs, False, ["internal evidence that this promise is authorised"], (
            notes[0] if notes else None), None
    verdict = catalogue_verdict(catalogue, ts)
    refs["catalogue"] = verdict.paths
    cat_text = "; ".join(verdict.reasons)
    if len(verdict.paths) > 1 and verdict.kind != "varies":
        unstated = [d for d in cap.required_dims + ["region"] if not ts.get(d)]
        checked = ["capability"] + [d for d in ("network", "asset", "mode", "region") if ts.get(d)] + (
            ["volume"] if ts.get("quantity") else []) + (["milestone"] if ts.get("when") else [])
        cat_text = (f"Checked: {', '.join(checked)}. Not stated in the promise: {', '.join(unstated)}; the verdict is the "
                    f"same for every value the catalogue lists, but the deal's own {unstated[0]} is not checked here. "
                    + cat_text)
    if verdict.kind == "standard":
        return "standard_authorised", cat_text, refs, False, [], None, None
    if verdict.kind == "absolute":
        return ("no_approval_evidence", cat_text + " Not offered under the catalogue's explicit rule, so outside current "
                "authorisation and not open to a named exception.", refs, True,
                [f"{cap.name} for {scope_text(ts)} is not offered; change or withdraw the promise"], None, None)
    if verdict.kind == "varies":
        return ("unknown_needs_review", "The catalogue verdict depends on terms the promise does not state: " + cat_text,
                refs, False, ["the missing terms (" + ", ".join(c["terms"]["missing"]) + ") so the catalogue can decide"],
                None, None)
    finding, row, note = note_finding(notes, ts, cap.name)
    if note is not None:
        refs["source_versions"].append({"source_version_id": note.id, "source_key": note.source_key,
                                        "role": "approval_evidence", "line": row})
    if finding == "exception_approved":
        approver = APPROVER.search(row)
        conditions = [m.group(0).strip() for m in CONDITIONS.finditer(row)]
        refs["approval"] = {"approver": (approver.group(1) or approver.group(2)).strip(), "conditions": conditions}
        text = f"{cat_text}; {note.source_key}: '{row}'"
        if conditions:
            text += "; conditions recorded: " + "; ".join(conditions) + " (each must be carried into the contract)"
        return finding, text, refs, False, [], note, row
    if finding == "value_missing":
        return ("unknown_needs_review", f"{cat_text}; {note.source_key} has no stored value in the approval cell of this "
                f"row (a spreadsheet formula without a saved result): '{row}'", refs, False,
                ["the pricing note saved with its values, or the approval written as text"], note, row)
    if finding == "approval_without_approver":
        return ("unknown_needs_review", f"{cat_text}; {note.source_key} has approval wording but names no approver: "
                f"'{row}'", refs, False, ["the name or role of the person who approved this exception"], note, row)
    if finding == "no_approval_evidence":
        cited = f"{note.source_key}: '{row}'" if row else f"{note.source_key} names no approval for this scope"
        return (finding, f"{cat_text}; {cited}", refs, False,
                [f"named approval in a pricing and services note covering {cap.name}"
                 + (f": {scope_text(ts)}" if scope_text(ts) else "")
                 + (f", dated {', '.join(readable_date(d) for d in c['dates'])}" if c.get("dates") else "")], note, row)
    return (finding, f"{cat_text}; no pricing and services note among the selected sources", refs, False,
            ["a pricing and services note that records approval for this scope"], None, None)


def assess(plan: dict, versions: list, chain: references.Chain, catalogue: dict, vocab: terms.Vocabulary,
           statements: dict) -> dict:
    """Assess every commitment in a consolidation plan. Returns {commitment_key: Assessment}.

    statements: {statement_key: {"quote", "language", "source_version_id"}} for the review.
    """
    by_id = {v.id: v for v in versions}
    notes = sorted([v for v in versions if v.included and v.doc_type in APPROVAL_EVIDENCE_TYPES],
                   key=lambda v: (v.doc_date or "", v.id), reverse=True)
    chain_versions = [by_id[i] for i in chain.incorporated]
    result, presence = {}, {}

    for c in plan["commitments"]:
        key = c["commitment_key"]
        ts = _representative(c)
        member_keys = [m["statement_key"] for m in c["terms"]["members"]]
        quotes = " ".join(statements[k]["quote"] for k in member_keys if k in statements)
        dates = sorted({d for m in c["terms"]["members"] for d in m.get("dates", [])})
        c = {**c, "quote_text": quotes, "dates": dates}
        auth, auth_text, refs, absolute, auth_unmet, note, row = _authorisation(c, ts, catalogue, vocab, notes)

        member_versions = {statements[k]["source_version_id"] for k in member_keys if k in statements}
        in_chain = sorted(member_versions & set(chain.incorporated))
        incomplete = c["terms"]["terms_incomplete"]
        uncertain = []
        if not chain.has_contract:
            presence_value = "not_assessed"
            detail = "Not assessed: no draft contract among the selected sources."
        elif in_chain:
            presence_value = "included_in_draft_contract"
            where = "; ".join(f"{by_id[v].source_key} ({chain.incorporated[v]})" for v in in_chain)
            members = [k for k in member_keys if statements.get(k, {}).get("source_version_id") in in_chain]
            detail = f"Included: {', '.join(members)} in {where}."
        else:
            presence_value = "absent"
            searched = ", ".join(f"{v.source_key} ({chain.incorporated[v.id]})" for v in chain_versions)
            detail = f"Absent from the draft contract and what it incorporates: {searched}."
            if incomplete:
                uncertain.append("terms incomplete (" + ", ".join(c["terms"]["missing"]) + ")")
            stems = references.topic_stems(c["name"] + " " + quotes)
            for gap in chain.gaps():
                if not gap.topic or stems & set(gap.topic):
                    uncertain.append(f"{gap.from_source_key} {gap.from_locator} cites {gap.cited_label}, which is "
                                     f"{gap.status}: {gap.reason}")
            if uncertain:
                detail += " Uncertain: " + "; ".join(uncertain) + "."
        presence[key] = presence_value
        for v in in_chain:
            refs["source_versions"].append({"source_version_id": v, "source_key": by_id[v].source_key, "role": "contract"})

        a = Assessment(auth, auth_text, refs, presence_value, detail)
        if c["language"] == "firm":
            a.issues += _authorisation_issues(c, ts, auth, auth_text, absolute, auth_unmet, note, row, vocab)
            a.issues += _presence_issues(c, ts, presence_value, detail, uncertain, chain, chain_versions)
        result[key] = a

    _conflicts(plan, result, presence, vocab, statements, by_id)
    return result


def _criteria(**kw) -> dict:
    return {"version": CRITERIA_VERSION, **kw}


def _authorisation_issues(c, ts, auth, auth_text, absolute, unmet, note, row, vocab):
    if auth not in ("no_approval_evidence", "unknown_needs_review"):
        return []
    evidence = [{"source_version_id": note.id, "locator": row or "whole note", "role": "approval_evidence"}] if note else []
    capability = ts.get("capability") if ts else None
    if auth == "no_approval_evidence":
        return [{
            "issue_type": "approval", "subject_key": "authorisation", "owner_function": "Product",
            "absolute_limit": 1 if absolute else 0,
            "closure_criteria": _criteria(
                required_evidence=list(APPROVAL_EVIDENCE_TYPES), must_cover=must_cover(ts, c.get("dates", ())),
                absolute_limit_blocks_exception=bool(absolute),
                closes_by=(["change_or_withdraw_promise"] if absolute else ["allowed_exception", "change_or_withdraw_promise"])),
            "raised": {"outcome": "open_action", "evidence_checked": evidence, "unmet": unmet,
                       "reason": ("Firm promise outside catalogue support (absolute limit). " if absolute
                                  else "Firm promise needs named approval, and none is recorded. ") + auth_text},
        }]
    return [{
        "issue_type": "insufficient_evidence", "subject_key": "authorisation",
        "owner_function": "Product" if vocab.capabilities.get(capability) else "Delivery", "absolute_limit": 0,
        "closure_criteria": _criteria(required_evidence=list(APPROVAL_EVIDENCE_TYPES),
                                      must_cover=must_cover(ts, c.get("dates", ())) if ts else {}, missing=unmet),
        "raised": {"outcome": "open_evidence", "evidence_checked": evidence, "unmet": unmet,
                   "reason": "Authorisation cannot be confirmed from the catalogue or the pricing note. " + auth_text},
    }]


def _presence_issues(c, ts, presence_value, detail, uncertain, chain, chain_versions):
    evidence = [{"source_version_id": v.id, "locator": "whole document", "role": "contract"} for v in chain_versions]
    targets = sorted({v.source_key for v in chain_versions})
    if presence_value == "included_in_draft_contract":
        return []
    if presence_value == "absent" and not uncertain:
        return [{
            "issue_type": "contract_gap", "subject_key": "contract", "owner_function": "Commercial", "absolute_limit": 0,
            "closure_criteria": _criteria(required_evidence=list(CONTRACT_EVIDENCE_TYPES),
                                          must_match=must_cover(ts or {}, c.get("dates", ())), target_source_keys=targets),
            "raised": {"outcome": "open_action", "evidence_checked": evidence,
                       "unmet": [f"the draft contract, or a document it incorporates, states {c['name']}"],
                       "reason": "Firm promise absent from the contract terms, and nothing withdraws it. " + detail},
        }]
    missing = uncertain or ["a draft contract among the selected sources"]
    return [{
        "issue_type": "insufficient_evidence", "subject_key": "contract",
        "owner_function": "Commercial", "absolute_limit": 0,
        "closure_criteria": _criteria(required_evidence=list(CONTRACT_EVIDENCE_TYPES),
                                      must_match=must_cover(ts or {}, c.get("dates", ())), target_source_keys=targets,
                                      missing=missing),
        "raised": {"outcome": "open_evidence", "evidence_checked": evidence, "unmet": missing,
                   "reason": "Contractual presence cannot be concluded reliably. " + detail},
    }]


def _differing_term(a: dict, b: dict, cap) -> str | None:
    """The one term on which two term sets of the same capability differ, or None if they are not one-term apart."""
    diffs = [d for d in cap.key_dims if a.get(d) != b.get(d)]
    qa, qb = a.get("quantity"), b.get("quantity")
    if qa or qb:
        if not (qa and qb) or sorted(a.get("when", [])) != sorted(b.get("when", [])):
            return None
        if (qa.get("unit"), qa.get("period")) != (qb.get("unit"), qb.get("period")):
            return None
        if qa.get("value") != qb.get("value"):
            diffs.append("quantity")
    if len(diffs) == 1 and diffs[0] in ("mode", "quantity"):
        return diffs[0]
    return None


def _conflicts(plan, result, presence, vocab, statements, by_id):
    complete = [c for c in plan["commitments"] if not c["terms"]["terms_incomplete"] and c["language"] == "firm"]
    for c in complete:
        ts = _representative(c)
        cap = vocab.capabilities.get(ts.get("capability")) if ts else None
        if cap is None:
            continue
        for d in complete:
            if d is c or presence.get(d["commitment_key"]) != "included_in_draft_contract":
                continue
            other = _representative(d)
            if other.get("capability") != ts.get("capability"):
                continue
            term = _differing_term(ts, other, cap)
            if term is None:
                continue
            promised = scope_text({term: ts.get(term)}) if term != "quantity" else scope_text({"quantity": ts["quantity"]})
            contract = scope_text({term: other.get(term)}) if term != "quantity" else scope_text({"quantity": other["quantity"]})
            d_versions = sorted({statements[m["statement_key"]]["source_version_id"] for m in d["terms"]["members"]
                                 if m["statement_key"] in statements})
            contract_keys = sorted({by_id[v].source_key for v in d_versions})
            basis = f"same capability and terms except {term}: promised {promised}, contract side says {contract}"
            a = result[c["commitment_key"]]
            a.issues.append({
                "issue_type": "conflicting_terms", "subject_key": f"conflict:{d['commitment_key']}",
                "owner_function": "Commercial", "absolute_limit": 0,
                "closure_criteria": _criteria(required_evidence=list(CONTRACT_EVIDENCE_TYPES), must_match=must_cover(ts),
                                              conflicting_commitment=d["commitment_key"], differing_term=term,
                                              target_source_keys=contract_keys),
                "raised": {"outcome": "open_action",
                           "evidence_checked": [{"source_version_id": v, "locator": "whole document", "role": "contract"}
                                                for v in d_versions],
                           "unmet": [f"{', '.join(contract_keys)} says {contract}; the promise says {promised}"],
                           "reason": f"Conflicting terms with {d['commitment_key']} ({d['name']}): {basis}."},
            })
            if presence.get(c["commitment_key"]) != "included_in_draft_contract":
                a.links.append((d["commitment_key"], c["commitment_key"], "contract_side_of", basis))
