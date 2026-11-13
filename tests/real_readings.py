"""The two accepted Alder readings (13 Nov, Round 5), for tests that build ledgers in a scratch cache.

Alder has no seed (config.V2_SEED_FILES): its first review is read from results/v2_cache, so a test that points config.V2_CACHE_DIR at an empty scratch folder and then rebuilds the demo
ledger needs the base-document reading (K0) in that folder. `patch_cache` copies it in (K0 only: K1, the state with AB-05 and AB-06 added, is what tests script with a fake model, or read from the
real cache through the default path). Nothing here writes to results/v2_cache."""

import json
import shutil
from pathlib import Path
from unittest import mock

import config

K0 = "1a8ccdf1b36f1c6a43dd1484a82fdd655ae18c8910e906e141550a2691a8343a.json"  # the base documents AB-01 .. AB-08
K1 = "a5708d548423d9ac1a2aad04a626a08de5905a89645ffb6fb1a93795fa1d732b.json"  # ... with AB-05 and AB-06 (the demo's sample files) added


def reading(name: str) -> dict:
    return json.loads((Path(config.ROOT) / "results" / "v2_cache" / name).read_text(encoding="utf-8"))


def k1_findings() -> list:
    """The model's proposed findings for the K1 state, as a fake model would return them."""
    return [{k: v for k, v in f.items() if k != "problems"} for f in reading(K1)["findings"]]


def patch_cache(cache_dir):
    """mock.patch.object(config, "V2_CACHE_DIR", cache_dir), with Alder's base-document reading already in the scratch cache."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(Path(config.ROOT) / "results" / "v2_cache" / K0, cache_dir / K0)
    return mock.patch.object(config, "V2_CACHE_DIR", cache_dir)
