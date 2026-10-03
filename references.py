"""Reference resolution for contract-side documents. Pure functions: no database, no files, no model calls.

A draft contract incorporates other documents by reference ("the Statement of Work dated 20 October 2026, including
Annex A"). What the contract commits to is therefore the contract plus everything it incorporates, followed reference
by reference. This module finds those references, resolves each one against the versions a review uses, and builds
the contract chain.

Resolution rule (docs/LEDGER_SCHEMA.md 3.4): a document reference resolves by target type plus cited date to the
newest included version whose document date equals the cited date; with no cited date, to the newest included version.
A section reference (Annex, Schedule, Appendix, Exhibit, SOW section) resolves to a heading in an included
contract-side document. Outcomes: resolved; unresolved (the target document exists but no version or section matches
the citation); missing (nothing to resolve to). When unsure, the reference is not resolved: an unresolved or missing
reference never produces a confident conclusion downstream.
"""

import re
from dataclasses import dataclass, field

import terms

CONTRACT_TYPES = ("draft_contract",)
SOW_TYPES = ("draft_sow",)
CONTRACT_SIDE_TYPES = CONTRACT_TYPES + SOW_TYPES

_MONTHS = "|".join(m.capitalize() for m in terms.MONTHS)
SOW_REF = re.compile(
    rf"\b(?:Statement of Work|SOW)\b(?:\s+dated\s+(\d{{1,2}})\s+({_MONTHS})\s+(\d{{4}}))?"
    rf"(?:\s+(?:section|§)\s*(\d+(?:\.\d+)*))?", re.I)
SECTION_REF = re.compile(r"\b(Annex|Schedule|Appendix|Exhibit)\s+([A-Z]|\d+)\b")
HEADING = re.compile(r"^(#{1,6})\s+(.*)$", re.M)
CLAUSE_LINE = re.compile(r"^\s*\*\*(Clause\s+[\d.]+)", re.I)

# Words that say nothing about what a referenced section covers. Used only to decide which conclusions a missing
# reference makes uncertain; an empty topic makes every absence uncertain.
TOPIC_STOPWORDS = frozenset("""
    provider customer will shall deliver delivers provide provides provided perform services service described
    accordance forms form part this that with from include includes including incorporated reference agreement
    statement work these those which under annex schedule appendix exhibit section clause specification parties party
    elva into each every have their there where when what set out given meaning meanings terms term during hold
""".split())


@dataclass(frozen=True)
class Version:
    id: int
    source_key: str
    doc_type: str
    doc_date: str | None
    text: str
    included: bool = True


@dataclass
class Resolution:
    from_version_id: int
    from_source_key: str
    from_locator: str
    cited_label: str
    cited_date: str | None
    kind: str                      # "document" or "section"
    target_source_key: str | None
    target_locator: str | None
    status: str                    # resolved | unresolved | missing
    resolved_version_id: int | None
    reason: str
    topic: list = field(default_factory=list)


# --- Small helpers ------------------------------------------------------------------------------------------

def stem(word: str) -> str:
    """Crude, deterministic stem: enough to see that 'reporting' and 'reports' share a topic."""
    w = word.lower()
    for suffix in ("ing", "ions", "ion", "es", "s", "ed"):
        if len(w) > len(suffix) + 3 and w.endswith(suffix):
            return w[: -len(suffix)]
    return w


def topic_stems(text: str) -> set:
    return {stem(w) for w in re.findall(r"[A-Za-z]{4,}", text) if w.lower() not in TOPIC_STOPWORDS}


def _sentence(text: str, pos: int) -> str:
    start = max(text.rfind(".", 0, pos), text.rfind("\n", 0, pos)) + 1
    ends = [i for i in (text.find(".", pos), text.find("\n", pos)) if i != -1]
    return text[start:(min(ends) if ends else len(text))].strip()


def locator(text: str, pos: int) -> str:
    """Where a reference sits: 'Clause 3', the nearest heading above it, or a line number."""
    line_start = text.rfind("\n", 0, pos) + 1
    line_end = text.find("\n", pos)
    line = text[line_start:(line_end if line_end != -1 else len(text))]
    m = CLAUSE_LINE.match(line)
    if m:
        return re.sub(r"\s+", " ", m.group(1)).rstrip(".")
    headings = [h for h in HEADING.finditer(text) if h.start() <= pos]
    if headings:
        return headings[-1].group(2).strip()
    return f"line {text.count(chr(10), 0, pos) + 1}"


def _iso(day, month, year):
    return terms.normalise_date(day, month, year) if day else None


def _newest(versions):
    """Newest first: later document date, then higher id."""
    return sorted(versions, key=lambda v: (v.doc_date or "", v.id), reverse=True)


def section_span(text: str, kind: str, ident: str):
    """(start, end) of the section headed '<kind> <ident>' (e.g. Annex A), or of a numbered SOW section; else None.

    The section runs from its heading to the next heading of the same or a higher level.
    """
    if kind.lower() == "section":
        pattern = re.compile(rf"^(#{{1,6}})\s+{re.escape(ident)}\.?\s", re.M)
    else:
        pattern = re.compile(rf"^(#{{1,6}})\s+{re.escape(kind)}\s+{re.escape(ident)}\b", re.M | re.I)
    m = pattern.search(text)
    if not m:
        return None
    level = len(m.group(1))
    end = len(text)
    for h in HEADING.finditer(text, m.end()):
        if len(h.group(1)) <= level:
            end = h.start()
            break
    return m.start(), end


# --- Finding and resolving ------------------------------------------------------------------------------------

def find_section_in(kind: str, ident: str, candidates: list):
    """The first candidate version with that section heading, and the section's span. None if no candidate has it."""
    for v in candidates:
        span = section_span(v.text, kind, ident)
        if span:
            return v, span
    return None


def _document_refs(v: Version, versions: list) -> list:
    """References from a contract to the Statement of Work. Undated references inherit a date cited elsewhere in
    the same contract ('the Statement of Work' means the one the contract defines)."""
    matches = list(SOW_REF.finditer(v.text))
    dated = [_iso(m.group(1), m.group(2), m.group(3)) for m in matches if m.group(1)]
    defined_date = dated[0] if len(set(dated)) == 1 else None
    sows = [x for x in versions if x.included and x.doc_type in SOW_TYPES]
    out, seen = [], set()
    for m in sorted(matches, key=lambda m: (m.group(1) is None, m.start())):  # dated references first
        cited_date = _iso(m.group(1), m.group(2), m.group(3))
        inherited = cited_date is None and defined_date is not None
        date = cited_date or defined_date
        section = m.group(4)
        key = (locator(v.text, m.start()), date, section)
        if key in seen:
            continue
        seen.add(key)
        label = m.group(0).strip()
        common = dict(from_version_id=v.id, from_source_key=v.source_key, from_locator=locator(v.text, m.start()),
                      cited_label=label, cited_date=date, kind="document",
                      topic=sorted(topic_stems(_sentence(v.text, m.start()))))
        if not sows:
            out.append(Resolution(**common, target_source_key=None, target_locator=None, status="missing",
                                  resolved_version_id=None, reason="no Statement of Work among the selected sources"))
            continue
        matching = [x for x in sows if date is None or x.doc_date == date]
        if not matching:
            out.append(Resolution(**common, target_source_key=_newest(sows)[0].source_key, target_locator=None,
                                  status="unresolved", resolved_version_id=None,
                                  reason=f"no included Statement of Work is dated {date}"))
            continue
        target = _newest(matching)[0]
        target_locator = f"section {section}" if section else None
        if section and not section_span(target.text, "section", section):
            out.append(Resolution(**common, target_source_key=target.source_key, target_locator=target_locator,
                                  status="unresolved", resolved_version_id=None,
                                  reason=f"{target.source_key} has no section {section}"))
            continue
        why = "cited date matches" if cited_date else (
            f"date {date} taken from the contract's dated reference" if inherited else "no date cited; newest version")
        out.append(Resolution(**common, target_source_key=target.source_key, target_locator=target_locator,
                              status="resolved", resolved_version_id=target.id, reason=why))
    return out


def _section_refs(v: Version, versions: list, incorporated: list) -> list:
    out, seen = [], set()
    for m in SECTION_REF.finditer(v.text):
        kind, ident = m.group(1), m.group(2)
        if (kind.lower(), ident) in seen:
            continue
        seen.add((kind.lower(), ident))
        line_start = v.text.rfind("\n", 0, m.start()) + 1
        if HEADING.match(v.text, line_start):
            continue  # the heading of the section itself, not a reference to it
        # Only the citing document and what the contract already incorporates: finding the heading in some other
        # document (for example a SOW whose date does not match the contract's citation) must not pull it in.
        candidates = [v] + [x for x in incorporated if x.id != v.id]
        found = find_section_in(kind, ident, candidates)
        common = dict(from_version_id=v.id, from_source_key=v.source_key, from_locator=locator(v.text, m.start()),
                      cited_label=f"{kind} {ident}", cited_date=None, kind="section",
                      target_locator=f"{kind} {ident}", topic=sorted(topic_stems(_sentence(v.text, m.start()))))
        if found:
            target, _ = found
            out.append(Resolution(**common, target_source_key=target.source_key, status="resolved",
                                  resolved_version_id=target.id,
                                  reason="heading found in the same document" if target.id == v.id
                                  else f"heading found in {target.source_key}"))
        else:
            out.append(Resolution(**common, target_source_key=None, status="missing", resolved_version_id=None,
                                  reason=f"no '{kind} {ident}' heading in {v.source_key} or the documents the contract "
                                         "incorporates"))
    return out


@dataclass
class Chain:
    """The draft contract and everything it incorporates, with every reference followed on the way."""
    contract_version_ids: list
    incorporated: dict             # version_id -> how it entered the chain
    resolutions: list

    @property
    def has_contract(self) -> bool:
        return bool(self.contract_version_ids)

    def gaps(self) -> list:
        """References that did not resolve: each one leaves the conclusions it could affect incomplete."""
        return [r for r in self.resolutions if r.status != "resolved"]


def contract_chain(versions: list) -> Chain:
    """Follow references from the newest included draft contract of each contract source."""
    included = [v for v in versions if v.included]
    latest = {}
    for v in _newest([v for v in included if v.doc_type in CONTRACT_TYPES]):
        latest.setdefault(v.source_key, v)
    contracts = list(latest.values())
    incorporated = {v.id: "draft contract" for v in contracts}
    order = list(contracts)
    resolutions, i = [], 0
    while i < len(order):
        doc = order[i]
        i += 1
        found = _document_refs(doc, included) if doc.doc_type in CONTRACT_TYPES else []
        for r in found:
            if r.status == "resolved" and r.resolved_version_id not in incorporated:
                target = next(v for v in included if v.id == r.resolved_version_id)
                incorporated[target.id] = f"incorporated by {doc.source_key} {r.from_locator}"
                order.append(target)
        found += _section_refs(doc, included, order)
        for r in found:
            if r.kind == "section" and r.status == "resolved" and r.resolved_version_id not in incorporated:
                target = next(v for v in included if v.id == r.resolved_version_id)
                incorporated[target.id] = f"{r.cited_label} cited by {doc.source_key} {r.from_locator}"
                order.append(target)
        resolutions += found
    return Chain([v.id for v in contracts], incorporated, resolutions)


def referenced_section(quote: str, version: Version, versions: list):
    """For a pointer statement: the section its quote cites, as (target version, span), or None.

    Only the statement's own document is searched, so a term is never filled from a document the pointer does not
    belong to. Only Annex, Schedule, Appendix and Exhibit references count: they name a self-contained specification.
    `versions` is accepted for symmetry with contract_chain and is not searched.
    """
    m = SECTION_REF.search(quote)
    if not m or not version.included:
        return None
    return find_section_in(m.group(1), m.group(2), [version])
