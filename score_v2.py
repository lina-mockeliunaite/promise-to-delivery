"""Score v2 findings against a deal's frozen labels (10 Oct 2026).

A target is a (labelled commitment, issue) pair for the three issue types the product reports. An accepted finding
hits a target when its type maps to the issue and one of its promise quotes matches one of that commitment's labelled
statement quotes (one contains the other after whitespace and case are normalised, or word overlap >= 0.8).
A finding that hits nothing is a false flag. Several findings on one target count as one hit; the extras are
reported as duplicates, not as false flags. Rejected findings that would have hit a target are reported too: they
show where the verifier is stricter than it should be.
"""

import json

import config

KIND_TO_ISSUES = {"approval_required": ("overcommitment",), "absolute_limit": ("overcommitment",),
                  "over_limit": ("overcommitment",), "contract_gap": ("expectation_gap",),
                  "conflicting_terms": ("contradiction", "expectation_gap")}
ISSUES = ("overcommitment", "expectation_gap", "contradiction")


def _norm(text: str) -> str:
    return " ".join((text or "").lower().replace("’", "'").split())


def quotes_match(a: str, b: str) -> bool:
    a, b = _norm(a), _norm(b)
    if not a or not b:
        return False
    if (len(a) >= 20 and a in b) or (len(b) >= 20 and b in a):
        return True
    wa, wb = set(a.split()), set(b.split())
    return len(wa & wb) / len(wa | wb) >= 0.8


def load_labels(deal: str) -> dict:
    base = config.deal_dir(deal) / "labels"
    commitments = json.loads((base / "commitments.json").read_text(encoding="utf-8"))["commitments"]
    statements = json.loads((base / "statements.json").read_text(encoding="utf-8"))["statements"]
    quotes = {c["id"]: [] for c in commitments}
    for s in statements:
        for cid in s.get("commitment_ids") or []:
            quotes.setdefault(cid, []).append(s["quote"])
    targets = sorted((c["id"], i) for c in commitments for i in c.get("issues") or [] if i in ISSUES)
    names = {c["id"]: c["name"] for c in commitments}
    return {"targets": targets, "quotes": quotes, "names": names}


def matched_commitments(finding: dict, quotes: dict) -> list:
    fq = [q["quote"] for q in finding.get("promise_quotes") or []]
    return sorted(cid for cid, qs in quotes.items() if any(quotes_match(a, b) for a in fq for b in qs))


def score(deal: str, accepted: list, rejected: list, labels: dict = None) -> dict:
    labels = labels or load_labels(deal)
    targets = set(labels["targets"])
    hit, rows, false_flags, duplicates = set(), [], 0, 0
    for f in accepted:
        cids = matched_commitments(f, labels["quotes"])
        hits = [(c, i) for c in cids for i in KIND_TO_ISSUES.get(f["kind"], ()) if (c, i) in targets]
        if not hits:
            verdict = "false_flag"
            false_flags += 1
        elif all(h in hit for h in hits):
            verdict = "duplicate"
            duplicates += 1
        else:
            verdict = "hit"
        hit.update(hits)
        rows.append({"kind": f["kind"], "commitment": f.get("commitment"), "matched": cids, "verdict": verdict})
    rejected_true = []
    for f in rejected:
        cids = [c for c in matched_commitments(f, labels["quotes"])
                for i in KIND_TO_ISSUES.get(f["kind"], ()) if (c, i) in targets and (c, i) not in hit]
        if cids:
            rejected_true.append({"kind": f["kind"], "commitment": f.get("commitment"), "matched": cids,
                                  "problems": f.get("problems")})
    missed = [{"commitment": c, "name": labels["names"].get(c), "issue": i} for c, i in sorted(targets - hit)]
    counted = len(accepted) - duplicates
    return {"deal": deal, "targets": len(targets), "found": len(hit & targets), "missed": missed,
            "accepted": len(accepted), "false_flags": false_flags, "duplicates": duplicates,
            "precision": round((counted - false_flags) / counted, 3) if counted else None,
            "recall": round(len(hit & targets) / len(targets), 3) if targets else None,
            "rejected": len(rejected), "rejected_true": rejected_true, "rows": rows}
