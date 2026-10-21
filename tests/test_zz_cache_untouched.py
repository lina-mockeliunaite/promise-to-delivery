"""The reading cache holds the same files before and after the whole suite (21 Oct). The listing is taken when this module is imported,
which happens during test discovery, before any test runs; this module sorts last, so its test runs after the others."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config

BEFORE = sorted(p.name for p in Path(config.V2_CACHE_DIR).glob("*")) if Path(config.V2_CACHE_DIR).is_dir() else []


class TestTheCacheIsUntouched(unittest.TestCase):
    def test_the_real_reading_cache_has_the_same_files_after_the_suite(self):
        after = sorted(p.name for p in Path(config.V2_CACHE_DIR).glob("*")) if Path(config.V2_CACHE_DIR).is_dir() else []
        self.assertEqual(after, BEFORE)


if __name__ == "__main__":
    unittest.main()
