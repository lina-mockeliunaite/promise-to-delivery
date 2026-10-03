"""Sales-housekeeping filter. Pure function: drops a statement only on positive evidence.

A statement is dropped only if it matches a named sales-process rule AND carries no material term (capability,
network, asset, mode, region, quantity or date). Absence of terms alone never drops a statement. Dropped rows stay
visible with their rule name; this module only decides.
"""

import re
from dataclasses import dataclass

import terms

# (rule name, pattern). Each rule is one kind of sales-process talk: next calls, RFP / proposal responses,
# a draft SOW to follow, walk-throughs, security packs, methodology descriptions.
SALES_RULES = [
    ("sales_next_call", re.compile(r"\b(?:next|another|follow-?up)\s+(?:call|meeting|session)\b", re.I)),
    ("sales_rfp_or_proposal_response", re.compile(
        r"\b(?:respond(?:s|ing)?\s+to\s+(?:your|the)\s+(?:RFP|RFI|tender)|RFP\s+response|follow(?:s|ed)?\s+with\s+(?:a|the)\s+proposal)\b", re.I)),
    ("sales_draft_sow_to_follow", re.compile(
        r"\b(?:draft\s+(?:statement of work|SOW)|statement of work|SOW)\b[^.]{0,30}\b(?:will\s+follow|to\s+follow|follows?)\b", re.I)),
    ("sales_walkthrough", re.compile(r"\bwalk(?:s|ed)?\b[^.]{0,40}\bthrough\b|\bwalk-?through\b", re.I)),
    ("sales_security_pack", re.compile(r"\bsecurity\s+(?:pack|questionnaire|documentation)\b", re.I)),
    ("sales_methodology", re.compile(r"\b(?:phased\s+)?methodology\b|\bimplementation\s+approach\b", re.I)),
]


@dataclass(frozen=True)
class FilterDecision:
    kept: bool
    rule: str | None            # set only when dropped
    matched_rules: tuple        # every sales rule that matched, even if the statement was kept
    material_terms: bool


def has_material_term(parsed: terms.ParseResult) -> bool:
    if parsed.dates:
        return True
    for ts in parsed.term_sets:
        if any((ts.promise_type, ts.capability, ts.network, ts.asset, ts.mode, ts.region, ts.quantity)):
            return True
    return False


def classify(quote: str, vocab: terms.Vocabulary) -> FilterDecision:
    parsed = terms.parse_terms(quote, vocab)
    matched = tuple(name for name, pattern in SALES_RULES if pattern.search(quote))
    material = has_material_term(parsed)
    if matched and not material:
        return FilterDecision(False, matched[0], matched, material)
    return FilterDecision(True, None, matched, material)
