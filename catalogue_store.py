"""The product catalogue the checks use, and the capabilities people add to it (16 Oct, after Checkpoint 3).

data/catalogue.json is the published catalogue and is never written. People can add new capabilities in the app; each
addition is an append-only row in the ledger (who, when, the entry), and the catalogue every check uses is the
published one plus those additions. With no additions it is the published file byte for byte, so every hash, cache key
and saved model output stays exactly as it was.

Adding a capability changes what every deal is checked against, so the catalogue part of the config hash changes and
every deal reads "Review out of date" until it is checked again (integrity.compare). Existing entries cannot be edited
here: changing what a capability is would silently change past findings, and that belongs with Product.
"""

import json
import re
from pathlib import Path

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS catalogue_additions (
    id               INTEGER PRIMARY KEY,
    capability_id    TEXT NOT NULL UNIQUE CHECK (capability_id GLOB 'CAP-[0-9][0-9][0-9]*'),
    capability_json  TEXT NOT NULL CHECK (json_valid(capability_json)),
    added_by         TEXT NOT NULL CHECK (length(trim(added_by)) > 0 AND length(added_by) <= 120),
    created_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE TRIGGER IF NOT EXISTS catalogue_additions_append_only_u BEFORE UPDATE ON catalogue_additions
BEGIN SELECT RAISE(ABORT, 'catalogue additions are append-only'); END;
CREATE TRIGGER IF NOT EXISTS catalogue_additions_append_only_d BEFORE DELETE ON catalogue_additions
BEGIN SELECT RAISE(ABORT, 'catalogue additions are never deleted'); END;
"""

# 20 Oct: one catalogue per vendor. Elva's is the published file plus the capabilities people add in the app, exactly as before.
# Any other vendor's is its published file only: it cannot be added to here, and an Elva addition never touches it.
DEFAULT_VENDOR = "elva"
VENDORS = {
    "elva": {"name": "Elva", "file": "catalogue.json"},
    "aivuna": {"name": "Aivuna", "file": "catalogue_aivuna.json"},
}

STATUSES = {"generally_available": "Generally available", "beta": "Beta", "roadmap": "Roadmap"}
SELLABLE = {"standard": "Standard", "requires_named_approval": "Needs a named approval", "not_sellable": "Not sellable"}
REGION = re.compile(r"^[A-Z]{2}$")
LIMIT = re.compile(r"^[a-z][a-z0-9_]{2,40}$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class CatalogueError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def check_vendor(vendor) -> str:
    vendor = vendor or DEFAULT_VENDOR
    if vendor not in VENDORS:
        raise CatalogueError(f"Unknown vendor {vendor!r}.", 404)
    return vendor


def published_path(vendor=None) -> Path:
    return config.DATA_DIR / VENDORS[check_vendor(vendor)]["file"]


def published_bytes(vendor=None) -> bytes:
    return published_path(vendor).read_bytes()


def _has(conn) -> bool:
    return conn is not None and conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'catalogue_additions'").fetchone() is not None


def ensure_schema(conn) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def additions(conn) -> list:
    """[{'entry', 'added_by', 'added_at'}] in the order they were added."""
    if not _has(conn):
        return []
    return [{"entry": json.loads(j), "added_by": b, "added_at": a} for j, b, a in conn.execute(
        "SELECT capability_json, added_by, created_at FROM catalogue_additions ORDER BY id")]


def effective_bytes(conn=None, vendor=None) -> bytes:
    """The catalogue the checks use: the published file, plus additions if there are any (Elva's only)."""
    vendor = check_vendor(vendor)
    raw = published_bytes(vendor)
    extra = additions(conn) if vendor == DEFAULT_VENDOR else []
    if not extra:
        return raw  # byte for byte: hashes and cache keys unchanged
    cat = json.loads(raw.decode("utf-8"))
    cat["capabilities"] = list(cat["capabilities"]) + [a["entry"] for a in extra]
    return json.dumps(cat, indent=2, ensure_ascii=False).encode("utf-8")


def effective(conn=None, vendor=None) -> dict:
    return json.loads(effective_bytes(conn, vendor).decode("utf-8"))


def _next_id(cat: dict) -> str:
    nums = [int(m.group(1)) for c in cat["capabilities"] if (m := re.fullmatch(r"CAP-(\d+)", c.get("id", "")))]
    return f"CAP-{(max(nums) + 1 if nums else 1):03d}"


def add_capability(conn, body: dict, vendor=None) -> dict:
    """Validate and append one new capability. Returns it as the catalogue view shows it. Elva's catalogue only."""
    if check_vendor(vendor) != DEFAULT_VENDOR:
        raise CatalogueError(f"{VENDORS[vendor]['name']}'s catalogue is a published file; capabilities cannot be added to it here.", 409)
    ensure_schema(conn)
    body = body or {}
    name = (body.get("name") or "").strip() if isinstance(body.get("name"), str) else ""
    who = (body.get("added_by") or "").strip() if isinstance(body.get("added_by"), str) else ""
    if not 3 <= len(name) <= 120:
        raise CatalogueError("Give the capability a name (3 to 120 characters).")
    if not who or len(who) > 120:
        raise CatalogueError("Add your name at the top first.")
    cat = effective(conn)
    if any(c.get("name", "").lower() == name.lower() for c in cat["capabilities"]):
        raise CatalogueError("A capability with that name is already in the catalogue.", 409)
    regions = body.get("regions")
    if not isinstance(regions, list) or not regions or len(regions) > 6 or not all(isinstance(r, str) and REGION.fullmatch(r) for r in regions):
        raise CatalogueError("Choose at least one region (two-letter code, such as AU or SG).")
    status, sellable = body.get("status"), body.get("sellable")
    if status not in STATUSES:
        raise CatalogueError("Choose a status: generally available, beta or roadmap.")
    if sellable not in SELLABLE:
        raise CatalogueError("Choose how it can be sold: standard, needs a named approval, or not sellable.")
    roadmap = body.get("roadmap_date") or None
    if roadmap is not None and not (isinstance(roadmap, str) and DATE.fullmatch(roadmap)):
        raise CatalogueError("Give the planned general availability date as a date, or leave it empty.")
    if status == "generally_available":
        roadmap = None
    limits = {}
    lname, lvalue = body.get("limit_name") or None, body.get("limit_value")
    if lname is not None or lvalue not in (None, ""):
        try:
            lvalue = int(lvalue)
        except (TypeError, ValueError):
            raise CatalogueError("A limit needs a whole number.") from None
        if not (isinstance(lname, str) and LIMIT.fullmatch(lname)) or not 0 < lvalue <= 1_000_000_000:
            raise CatalogueError("A limit needs a name like max_transactions_per_day and a positive whole number.")
        limits[lname] = lvalue
    integrations = body.get("integrations") or []
    if not isinstance(integrations, list) or len(integrations) > 5 or not all(isinstance(i, str) and 0 < len(i.strip()) <= 60 for i in integrations):
        raise CatalogueError("List up to five pre-built integrations by name, or none.")
    entry = {"id": _next_id(cat), "name": name, "added_in_app": True}
    if integrations:
        entry["prebuilt_integrations"] = [i.strip() for i in integrations]
    entry["regions"] = {r: {"status": status, "sellable": sellable, "limits": dict(limits), "roadmap_date": roadmap}
                        for r in dict.fromkeys(regions)}
    try:
        conn.execute("INSERT INTO catalogue_additions (capability_id, capability_json, added_by) VALUES (?, ?, ?)",
                     (entry["id"], json.dumps(entry, sort_keys=True, ensure_ascii=False), who))
    except BaseException:
        conn.rollback()
        raise
    conn.commit()
    return next(c for c in view(conn)["capabilities"] if c["id"] == entry["id"])


# --- What the pop-up shows ---------------------------------------------------------------------------------------------
def _limit_text(key: str, value) -> str:
    if isinstance(value, list):
        return f"{key.replace('_', ' ').capitalize()}: {', '.join(map(str, value))}"
    words = key.replace("max_", "").replace("_", " ")
    return f"Max {value:,} {words}" if key.startswith("max_") and isinstance(value, int) else f"{key.replace('_', ' ')}: {value}"


def _leaves(node: dict, path: list):
    """Every sellable leaf under a region entry, with the network/asset/mode path that leads to it."""
    if "sellable" in node:
        yield path, node
        return
    for key in ("networks", "assets", "modes"):
        if key in node:
            for name, child in node[key].items():
                yield from _leaves(child, path + [name])


def view(conn=None, vendor=None) -> dict:
    vendor = check_vendor(vendor)
    cat = effective(conn, vendor)
    added = {a["entry"]["id"]: a for a in additions(conn)} if vendor == DEFAULT_VENDOR else {}
    caps, regions = [], set()
    for c in cat["capabilities"]:
        rows = []
        for region, node in (c.get("regions") or {}).items():
            regions.add(region)
            for path, leaf in _leaves(node, []):
                rows.append({
                    "region": region, "variant": " · ".join(p.replace("_", " ") for p in path),
                    "path": "/".join([c["id"], region] + path),
                    "status": leaf.get("status"), "status_label": STATUSES.get(leaf.get("status"), leaf.get("status")),
                    "sellable": leaf.get("sellable"), "sellable_label": SELLABLE.get(leaf.get("sellable"), leaf.get("sellable")),
                    "limits": [_limit_text(k, v) for k, v in (leaf.get("limits") or {}).items()],
                    "roadmap_date": leaf.get("roadmap_date"),
                })
        a = added.get(c["id"])
        caps.append({"id": c["id"], "name": c["name"], "integrations": c.get("prebuilt_integrations") or [], "rows": rows,
                     "added": {"by": a["added_by"], "at": a["added_at"]} if a else None})
    return {"vendor": vendor, "vendor_name": VENDORS[vendor]["name"], "can_add": vendor == DEFAULT_VENDOR,
            "as_of": cat.get("as_of"), "coverage": cat.get("coverage"), "unlisted_rule": cat.get("unlisted_rule"),
            "regions": sorted(regions), "capabilities": caps, "additions": len(added),
            "statuses": [{"value": k, "label": v} for k, v in STATUSES.items()],
            "sellable": [{"value": k, "label": v} for k, v in SELLABLE.items()]}
