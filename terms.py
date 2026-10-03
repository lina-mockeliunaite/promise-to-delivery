"""Deterministic term parser: quote -> term sets. Pure functions; no database, no files, no model calls.

Closed vocabularies come from data/catalogue.json (capability names, networks, assets, modes, regions, limit units
and periods). Anything outside them is not recognised, so it under-merges instead of guessing. The one exception is
blockchain network names: a small general list (GENERIC_NETWORKS) lets the parser see a network the catalogue does
not offer, and records it with in_catalogue = False so the rules can see it.
"""

import json
import re
from dataclasses import dataclass, field

# Well-known blockchain networks, for recognising networks the catalogue does not list. General knowledge, not taken
# from any deal or label. Proper nouns only, matched case-sensitively; names that are also everyday words (Base, Near,
# Stellar, Optimism in lower case) are left out or matched only when capitalised.
GENERIC_NETWORKS = [
    "Bitcoin", "Ethereum", "Polygon", "Arbitrum", "Optimism", "Solana", "Tron", "Avalanche", "BNB Chain",
    "Litecoin", "Cardano", "Polkadot", "Algorand", "Tezos", "XRP Ledger",
]

# Names the catalogue does not carry. build_vocabulary raises if the catalogue has a region or mode without one,
# so a new catalogue value is a visible error, never a silently unparsed term.
REGION_NAMES = {"SG": ["singapore"], "AU": ["australia"]}
MODE_PHRASES = {"real_time": [r"real[\s-]?time"], "batch": [r"batch(?:es)?"]}
# Extra capability phrases beyond the catalogue name. Kept minimal and general.
CAPABILITY_EXTRA_ALIASES = {"CAP-007": ["sanctions screening"], "CAP-014": ["audit history"]}
# CAP-021 is recognised by context rather than by its (long) name: a screening verb plus an on-chain cue.
ONCHAIN_SCREENING_CAPABILITY = "CAP-021"
SCREEN_WORD = re.compile(r"\bscreen(?:s|ed|ing)?\b", re.I)
ONCHAIN_CUES = re.compile(r"\b(wallets?|payouts?|on-chain|blockchain|analytics (?:integration|provider|service|connector))\b", re.I)
SANCTIONS = re.compile(r"\bsanctions?\b", re.I)

MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
_MONTH_RE = "|".join(m.capitalize() for m in MONTHS)
DATE_DMY = re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({_MONTH_RE})(?:,?\s+(\d{{4}}))?\b", re.I)
DATE_MDY = re.compile(rf"\b({_MONTH_RE})\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:,?\s+(\d{{4}}))?\b", re.I)
DATE_MY = re.compile(rf"\b({_MONTH_RE})\s+(\d{{4}})\b", re.I)
DATE_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")

NUMBER_DIGITS = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)(\s?[kKmM]\b)?")
SMALL = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split())}
TENS = {w: 10 * i for i, w in enumerate("_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()) if w != "_"}
SCALES = {"hundred": 100, "thousand": 1000, "million": 1_000_000}
NUMBER_WORD_RUN = re.compile(
    r"\b(?:(?:%s)(?:[\s-]+(?:and[\s-]+)?)?)+\b" % "|".join(sorted([*SMALL, *TENS, *SCALES], key=len, reverse=True)), re.I)

BOUND_MAX = re.compile(r"\b(up to|no more than|at most|maximum of|maximum|max)\b", re.I)
BOUND_MIN = re.compile(r"\b(at least|no fewer than|minimum of|minimum)\b", re.I)
PERIOD_PHRASE = re.compile(r"\b(?:per|a|an|each|every)\s+(hour|day|week|month|year)\b", re.I)
PERIOD_ADVERB = {"hourly": "hour", "daily": "day", "weekly": "week", "monthly": "month", "yearly": "year", "annually": "year"}
CADENCE = re.compile(r"\b(hourly|daily|weekly|fortnightly|monthly|quarterly|annually|yearly)\b", re.I)
WHEN_LAUNCH = re.compile(r"\bat (?:launch|go-?live)\b", re.I)
WHEN_FIRST_YEAR = re.compile(r"\b(?:by|at) the end of (?:the )?(?:first year|year (?:1|one))\b", re.I)
CLAUSE_REF = re.compile(r"^\s*[A-Z]\.\d+(?:\.\d+)*\s+")
# go_live is the one promise type that is not a catalogue capability. "at go-live" is a milestone qualifier on a
# volume (see WHEN_LAUNCH), not a go-live promise.
GO_LIVE = re.compile(r"(?<!at )\bgo(?:es|ing)?[\s-]*live\b", re.I)
GO_LIVE_KEY = json.dumps({"promise_type": "go_live"}, separators=(",", ":"))


@dataclass(frozen=True)
class Capability:
    id: str
    name: str
    networks: frozenset
    assets: frozenset
    modes: frozenset
    regions: frozenset

    @property
    def required_dims(self):
        """What a promise about this capability must state: a network and a mode where the capability has them."""
        dims = []
        if self.networks:
            dims.append("network")
        if self.modes:
            dims.append("mode")
        return dims

    @property
    def key_dims(self):
        """Dimensions that identify a promise: required ones, plus any the catalogue shows can vary (asset, region)."""
        dims = list(self.required_dims)
        if len(self.assets) > 1:
            dims.append("asset")
        if len(self.regions) > 1:
            dims.append("region")
        return dims


@dataclass
class Vocabulary:
    capabilities: dict
    networks: list               # catalogue networks (matched case-insensitively)
    generic_networks: list       # GENERIC_NETWORKS not in the catalogue (matched case-sensitively)
    assets: list
    mode_patterns: dict          # mode key -> compiled regex
    region_patterns: dict        # region code -> compiled regex
    units: dict                  # surface form -> canonical unit
    capability_patterns: dict    # capability id -> compiled regex


def _phrase(text):
    words = re.split(r"[\s-]+", text.strip().lower())
    return re.compile(r"\b" + r"[\s-]+".join(re.escape(w) for w in words) + r"\b", re.I)


def build_vocabulary(catalogue: dict) -> Vocabulary:
    capabilities, networks, assets, modes, regions, units = {}, set(), set(), set(), set(), {}
    for cap in catalogue["capabilities"]:
        c_networks, c_assets, c_modes = set(), set(), set()
        c_regions = set(cap["regions"])
        for region_code, region in cap["regions"].items():
            for network, ndata in region.get("networks", {}).items():
                c_networks.add(network)
                for asset, adata in ndata.get("assets", {}).items():
                    c_assets.add(asset)
                    c_modes.update(adata.get("modes", {}))
            for limit in region.get("limits", {}):
                m = re.fullmatch(r"max_(\w+)_per_(\w+)", limit)
                if m:
                    unit = m.group(1)
                    units[unit] = unit
                    units[unit[:-1] if unit.endswith("s") else unit] = unit
        capabilities[cap["id"]] = Capability(
            cap["id"], cap["name"], frozenset(c_networks), frozenset(c_assets), frozenset(c_modes), frozenset(c_regions))
        networks |= c_networks
        assets |= c_assets
        modes |= c_modes
        regions |= c_regions
    missing = (modes - set(MODE_PHRASES)) | {f"region {r}" for r in regions - set(REGION_NAMES)}
    if missing:
        raise ValueError(f"catalogue has values the parser has no phrases for: {sorted(missing)}")

    patterns = {}
    for cap_id, cap in capabilities.items():
        if cap_id == ONCHAIN_SCREENING_CAPABILITY:
            continue  # by context, see detect_capabilities
        phrases = [cap.name, *CAPABILITY_EXTRA_ALIASES.get(cap_id, [])]
        patterns[cap_id] = re.compile("|".join(_phrase(p).pattern for p in phrases), re.I)
    return Vocabulary(
        capabilities=capabilities,
        networks=sorted(networks),
        generic_networks=[n for n in GENERIC_NETWORKS if n not in networks],
        assets=sorted(assets),
        mode_patterns={m: re.compile("|".join(MODE_PHRASES[m]), re.I) for m in modes},
        region_patterns={r: re.compile(r"\b(?:%s)\b" % "|".join(REGION_NAMES[r]), re.I) for r in regions},
        units=units,
        capability_patterns=patterns,
    )


def load_vocabulary(path) -> Vocabulary:
    with open(path, encoding="utf-8") as f:
        return build_vocabulary(json.load(f))


# --- Normalisers -----------------------------------------------------------

def words_to_number(run: str):
    """'thirty thousand' -> 30000; 'twenty-five' -> 25. None if the words do not form a number."""
    total, current, seen = 0, 0, False
    for w in re.split(r"[\s-]+", run.lower().strip()):
        if w == "and" or not w:
            continue
        if w in SMALL:
            current += SMALL[w]
        elif w in TENS:
            current += TENS[w]
        elif w == "hundred":
            current = max(current, 1) * 100
        elif w in SCALES:
            total += max(current, 1) * SCALES[w]
            current = 0
        else:
            return None
        seen = True
    return total + current if seen else None


def normalise_date(day, month, year):
    m = MONTHS.index(month.lower()) + 1
    if year and day:
        return f"{int(year):04d}-{m:02d}-{int(day):02d}"
    if year:
        return f"{int(year):04d}-{m:02d}"
    return f"--{m:02d}-{int(day):02d}"  # no year in the quote: the parser never guesses one


def find_dates(text: str):
    """[(start, end, normalised)] for every date in the text. Spans are non-overlapping."""
    found = []

    def add(m, value):
        if not any(m.start() < e and s < m.end() for s, e, _ in found):
            found.append((m.start(), m.end(), value))

    for m in DATE_ISO.finditer(text):
        add(m, m.group(0))
    for m in DATE_DMY.finditer(text):
        add(m, normalise_date(m.group(1), m.group(2), m.group(3)))
    for m in DATE_MDY.finditer(text):
        add(m, normalise_date(m.group(2), m.group(1), m.group(3)))
    for m in DATE_MY.finditer(text):
        add(m, normalise_date(None, m.group(1), m.group(2)))
    return sorted(found)


def _blank(text, spans):
    chars = list(text)
    for s, e, *_ in spans:
        for i in range(s, e):
            chars[i] = " "
    return "".join(chars)


def find_numbers(text: str):
    """[(start, end, value)] for digit numbers (1,000 / 12000 / 30k) and number words (thirty thousand)."""
    found = []
    for m in NUMBER_DIGITS.finditer(text):
        value = float(m.group(1).replace(",", ""))
        suffix = (m.group(2) or "").strip().lower()
        value *= {"k": 1000, "m": 1_000_000}.get(suffix, 1)
        found.append((m.start(), m.end(), int(value) if value == int(value) else value))
    for m in NUMBER_WORD_RUN.finditer(text):
        run = m.group(0).strip()
        value = words_to_number(run)
        if value is not None and run.lower() not in ("and",):
            found.append((m.start(), m.start() + len(m.group(0).rstrip()), value))
    return sorted(found)


# --- Parsing ---------------------------------------------------------------

@dataclass
class TermSet:
    promise_type: str | None = None    # "capability", "go_live", or None when no promise type was recognised
    capability: str | None = None
    network: str | None = None
    network_in_catalogue: bool | None = None   # False for a network named in GENERIC_NETWORKS but not offered
    asset: str | None = None
    mode: str | None = None
    region: str | None = None
    quantity: dict | None = None   # {"value", "bound", "unit", "period"}
    when: list = field(default_factory=list)   # milestones tied to a volume: launch, end_of_first_year, dates
    go_live_date: str | None = None   # go_live only: an attribute, never part of the key
    missing: list = field(default_factory=list)
    key: str | None = None         # None when incomplete: an incomplete set never merges with another

    def as_dict(self):
        return {k: v for k, v in self.__dict__.items() if v not in (None, [], {}) or k == "capability"}


@dataclass
class ParseResult:
    term_sets: list
    dates: list            # every normalised date in the quote (attribute, never part of the key)
    cadence: list          # hourly / weekly ... (attribute, never part of the key)
    missing: list          # union over term sets, plus statement-level problems such as "association"
    ambiguous: bool = False

    @property
    def terms_incomplete(self):
        return bool(self.missing)


def _mentions(text, words, flags=re.I):
    """Mentioned vocabulary words in order of appearance: [(position, word)]."""
    hits = []
    for w in words:
        for m in re.finditer(rf"\b{re.escape(w)}\b", text, flags):
            hits.append((m.start(), w))
    return sorted(hits)


def _nearest_date(match, date_spans):
    """The date closest to a phrase (the go-live date, as opposed to a condition's date). None if there is none."""
    if not date_spans:
        return None
    def distance(span):
        s, e, _ = span
        return max(s - match.end(), match.start() - e, 0)
    return min(date_spans, key=lambda span: (distance(span), span[0]))[2]


def detect_capabilities(text, vocab, networks, assets):
    found = [cid for cid, pat in vocab.capability_patterns.items() if pat.search(text)]
    if (
        ONCHAIN_SCREENING_CAPABILITY in vocab.capabilities
        and SCREEN_WORD.search(text)
        and not SANCTIONS.search(text)
        and (ONCHAIN_CUES.search(text) or networks or assets)
    ):
        found.append(ONCHAIN_SCREENING_CAPABILITY)
    return found


def detect_quantity(text, vocab, number_spans):
    """The first number that looks like a volume: a bound word before it, or a known unit / period after it."""
    for start, end, value in number_spans:
        before, after = text[max(0, start - 20):start], text[end:end + 60]
        bound = "max" if BOUND_MAX.search(before) else "min" if BOUND_MIN.search(before) else None
        words = re.findall(r"[A-Za-z]+", after)
        unit = vocab.units.get(words[0].lower()) if words else None
        period = None
        pm = PERIOD_PHRASE.search(after)
        if pm:
            period = pm.group(1).lower()
        else:
            am = re.search(r"\b(hourly|daily|weekly|monthly|yearly|annually)\b", after, re.I)
            period = PERIOD_ADVERB[am.group(1).lower()] if am else None
        if bound or unit or period:
            return {"value": value, "bound": bound, "unit": unit, "period": period}
    return None


def detect_when(text, date_spans):
    when = []
    if WHEN_LAUNCH.search(text):
        when.append("launch")
    if WHEN_FIRST_YEAR.search(text):
        when.append("end_of_first_year")
    for s, e, value in date_spans:
        if re.search(r"\b(by|on|from|before|until)\s+(the\s+)?$", text[max(0, s - 12):s], re.I):
            when.append(value)
    return when


def parse_terms(quote: str, vocab: Vocabulary) -> ParseResult:
    text = CLAUSE_REF.sub("", quote)
    date_spans = find_dates(text)
    dates = [v for _, _, v in date_spans]
    scrubbed = _blank(text, date_spans)  # numbers inside dates are not quantities
    quantity = detect_quantity(scrubbed, vocab, find_numbers(scrubbed))
    when = detect_when(text, date_spans) if quantity else []
    cadence = sorted({m.group(1).lower() for m in CADENCE.finditer(text)})

    networks = sorted(_mentions(text, vocab.networks) + _mentions(text, vocab.generic_networks, 0))
    assets = _mentions(text, vocab.assets)
    modes = sorted((m.start(), key) for key, pat in vocab.mode_patterns.items() for m in pat.finditer(text))
    regions = sorted((m.start(), key) for key, pat in vocab.region_patterns.items() for m in pat.finditer(text))
    net_values = list(dict.fromkeys(w for _, w in networks))
    asset_values = list(dict.fromkeys(w for _, w in assets))
    mode_values = list(dict.fromkeys(k for _, k in modes))
    region_values = list(dict.fromkeys(k for _, k in regions))
    capabilities = detect_capabilities(text, vocab, net_values, asset_values)

    dims = {"network": net_values, "asset": asset_values, "mode": mode_values, "region": region_values}
    multi = [d for d, v in dims.items() if len(v) > 1]
    combos, ambiguous = [], False
    if not multi:
        combos = [{d: (v[0] if v else None) for d, v in dims.items()}]
    elif len(multi) == 1:
        d = multi[0]
        for value in dims[d]:
            combos.append({**{k: (v[0] if v else None) for k, v in dims.items()}, d: value})
    else:
        # Several dimensions list several values: expand only along an explicit "<value> on <network>" pairing.
        combos = _pairings(text, dims, multi, vocab)
        ambiguous = not combos

    result = ParseResult(term_sets=[], dates=dates, cadence=cadence, missing=[], ambiguous=ambiguous)
    go_live = GO_LIVE.search(text)
    go_live_set = (
        TermSet(promise_type="go_live", go_live_date=_nearest_date(go_live, date_spans), key=GO_LIVE_KEY)
        if go_live else None
    )
    if ambiguous:
        result.missing.append("association")
        result.term_sets = [go_live_set] if go_live_set else []
        return result

    cap_list = capabilities or ([] if go_live_set else [None])
    for cap_id in cap_list:
        for combo in combos:
            ts = TermSet(
                promise_type="capability" if cap_id else None, capability=cap_id, quantity=quantity,
                when=list(when), network_in_catalogue=(
                    None if combo["network"] is None else combo["network"] in vocab.networks),
                **combo,
            )
            cap = vocab.capabilities.get(cap_id)
            if cap is None:
                ts.missing.append("capability")
            else:
                ts.missing += [d for d in cap.required_dims if getattr(ts, d) is None]
            if quantity:
                ts.missing += [f for f in ("unit", "period") if not quantity.get(f)]
                if len(cap_list) > 1:
                    ts.missing.append("association")  # a volume next to several capabilities: which one?
            if not ts.missing:
                ts.key = _key(ts, cap)
            result.term_sets.append(ts)
    if go_live_set:
        result.term_sets.append(go_live_set)
    for ts in result.term_sets:
        for m in ts.missing:
            if m not in result.missing:
                result.missing.append(m)
    return result


def _pairings(text, dims, multi, vocab):
    """Term sets for a statement whose network and one other dimension both list several values.

    Only explicit pairings count: "<value> on <network>" (also for / via / over) or "<network>: <value>".
    Every value and every network must be paired exactly once; otherwise the association is ambiguous and the
    caller marks the statement terms_incomplete. No Cartesian product is ever formed.
    """
    if "network" not in multi or len(multi) != 2:
        return []
    other = next(d for d in multi if d != "network")
    if other not in ("asset", "mode"):
        return []
    pairs = []
    for value in dims[other]:
        vpat = re.escape(value) if other == "asset" else vocab.mode_patterns[value].pattern
        for network in dims["network"]:
            n = re.escape(network)
            if re.search(rf"(?:{vpat})\s+(?:on|for|via|over)\s+{n}\b", text, re.I) or re.search(
                rf"\b{n}\s*[:\u2013-]\s*(?:\w+\W+){{0,4}}?(?:{vpat})", text, re.I
            ):
                pairs.append((value, network))
    values_paired = [v for v, _ in pairs]
    networks_paired = [n for _, n in pairs]
    if (
        sorted(values_paired) != sorted(dims[other])
        or sorted(networks_paired) != sorted(dims["network"])
        or len(set(values_paired)) != len(values_paired)
        or len(set(networks_paired)) != len(networks_paired)
    ):
        return []
    fixed = {d: (v[0] if v else None) for d, v in dims.items()}
    return [{**fixed, other: value, "network": network} for value, network in pairs]


def _key(ts: TermSet, cap: Capability):
    parts = {"capability": ts.capability}
    for d in cap.key_dims:
        parts[d] = getattr(ts, d)
    if ts.quantity:
        parts["quantity"] = ts.quantity
        parts["when"] = sorted(ts.when)
    return json.dumps(parts, sort_keys=True, separators=(",", ":"))
