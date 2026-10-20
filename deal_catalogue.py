"""Which vendor's catalogue a deal is checked against (20 Oct, second demo scenario).

Every deal resolves explicitly to one vendor's catalogue: the `catalogue` field of data/profiles/<deal>.json, default "elva".
Elva deals (the four existing ones, and every deal made in the app) are checked exactly as before: no `catalogue_path` is
passed, so ledger_v2 reads the published file plus Elva's in-app additions, byte for byte as it always did. A deal of any
other vendor is checked against that vendor's published file, passed to ledger_v2 through its existing `catalogue_path`.

ledger_v2.py, detect_v2.py and recheck.py are inside the config hash, so they are not edited for this: the routing lives
here and in the callers. Every caller that starts a check goes through `recheck` and `needs_model` below, so a deal can
never be checked against another vendor's catalogue by forgetting an argument (tests/test_deal_catalogue.py scans for it).
"""

import json
from pathlib import Path

import catalogue_store
import deal_stage


def vendor_of(slug: str) -> str:
    """The vendor id a deal is checked against. Unknown ids fail loudly rather than falling back to Elva."""
    vendor = deal_stage.load_profile(slug).get("catalogue") or catalogue_store.DEFAULT_VENDOR
    return catalogue_store.check_vendor(vendor)


def vendor_name(slug: str) -> str:
    return catalogue_store.VENDORS[vendor_of(slug)]["name"]


def path_for(slug: str):
    """The vendor's published file for a non-default vendor, else None (meaning: the default resolution, unchanged)."""
    vendor = vendor_of(slug)
    return None if vendor == catalogue_store.DEFAULT_VENDOR else catalogue_store.published_path(vendor)


def bytes_for(conn, slug: str) -> bytes:
    """The catalogue bytes this deal's checks and hashes use."""
    return catalogue_store.effective_bytes(conn, vendor_of(slug))


def load(conn, slug: str) -> dict:
    return json.loads(bytes_for(conn, slug).decode("utf-8"))


def slug_of(conn, did: int):
    row = conn.execute("SELECT slug FROM deals WHERE id = ?", (did,)).fetchone()
    return row[0] if row else None


def bytes_for_deal(conn, did: int) -> bytes:
    """As bytes_for, from a deal id (the hash comparisons know the id, not the slug)."""
    slug = slug_of(conn, did)
    return bytes_for(conn, slug) if slug else catalogue_store.effective_bytes(conn)


def recheck(conn, slug: str, fix_id=None, client=None):
    """recheck.recheck against the deal's own catalogue."""
    import recheck as rc
    p = path_for(slug)
    return rc.recheck(conn, slug, fix_id, client, str(p) if p else None)


def needs_model(conn, slug: str, source_key, doc_type: str, canonical_text: str) -> bool:
    """ledger_v2.needs_model against the deal's own catalogue."""
    import ledger_v2
    p = path_for(slug)
    return ledger_v2.needs_model(conn, slug, source_key, doc_type, canonical_text, str(p) if p else None)
