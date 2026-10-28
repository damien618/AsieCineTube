#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AsieCinéTube — Unified E2E Test Suite Runner.
Executes all 4 Tiers of testing (Tier 1: Feature Coverage F1-F16,
Tier 2: Boundaries, Tier 3: Combinations, Tier 4: Real-World Scenarios).

Usage:
    python3 tests/test_catalog_e2e.py
    python3 -m unittest discover tests
"""

import os
import sys
import time
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from tests.test_tier1_features import (
    TestF1ExcludedChannels,
    TestF2BMovieMartialArtsExclusion,
    TestF3AuteurDetectionAndEnrichment,
    TestF4AuteurCategoryInAPI,
    TestF5SeedHygieneAndCachePersistence,
    TestF6HarvesterAuteurQueries,
    TestF7CompleteCatalogPurge,
    TestF8PreservationKofaAndSooner,
    TestF9ChronologicalSortOrder,
    TestF10AuteurNavigationChip,
    TestF11RenamePolarThrillerChip,
    TestF12EnrichedSearchPlaceholder,
    TestF13AuteurBadgesCardsAndModal,
    TestF14GoldAmberPrestigeThemeCSS,
    TestF15AutomatedCatalogValidation,
    TestF16E2ETestingSuiteIntegrity,
)
from tests.test_tier2_boundaries import TestTier2Boundaries
from tests.test_tier3_combinations import TestTier3Combinations
from tests.test_tier4_scenarios import TestTier4UserJourneys


def build_suite() -> unittest.TestSuite:
    """Build complete test suite across all 4 tiers."""
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()

    # Tier 1: F1 to F16
    tier1_classes = [
        TestF1ExcludedChannels,
        TestF2BMovieMartialArtsExclusion,
        TestF3AuteurDetectionAndEnrichment,
        TestF4AuteurCategoryInAPI,
        TestF5SeedHygieneAndCachePersistence,
        TestF6HarvesterAuteurQueries,
        TestF7CompleteCatalogPurge,
        TestF8PreservationKofaAndSooner,
        TestF9ChronologicalSortOrder,
        TestF10AuteurNavigationChip,
        TestF11RenamePolarThrillerChip,
        TestF12EnrichedSearchPlaceholder,
        TestF13AuteurBadgesCardsAndModal,
        TestF14GoldAmberPrestigeThemeCSS,
        TestF15AutomatedCatalogValidation,
        TestF16E2ETestingSuiteIntegrity,
    ]
    for cls in tier1_classes:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    # Tier 2: Boundaries
    suite.addTests(loader.loadTestsFromTestCase(TestTier2Boundaries))

    # Tier 3: Combinations
    suite.addTests(loader.loadTestsFromTestCase(TestTier3Combinations))

    # Tier 4: Scenarios
    suite.addTests(loader.loadTestsFromTestCase(TestTier4UserJourneys))

    return suite


def load_tests(loader, standard_tests, pattern):
    """Prevent double-counting when running 'python3 -m unittest discover tests'."""
    return unittest.TestSuite()


def main():
    print("=" * 80)
    print("  🎬 AsieCinéTube FR — Opaque-Box E2E Test Suite (Tiers 1 - 4)")
    print("=" * 80)
    print("Test Suite Plan:")
    print("  - Tier 1: Feature Coverage (F1 to F16, >=5 test cases per feature)")
    print("  - Tier 2: Boundary & Corner Cases (URL encoding, hash collisions, limits)")
    print("  - Tier 3: Cross-Feature Combinations (Auteur + Sooner + Martial Arts)")
    print("  - Tier 4: Real-World Scenarios (5 End-to-End User Journeys)")
    print("-" * 80)

    start_time = time.time()
    suite = build_suite()
    total_count = suite.countTestCases()
    print(f"Total test cases loaded: {total_count}\n")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    elapsed = time.time() - start_time

    print("\n" + "=" * 80)
    print(f"Execution completed in {elapsed:.2f}s")
    print(f"Ran: {result.testsRun} tests")
    print(f"Passed: {result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    print("=" * 80)

    if result.wasSuccessful():
        print("🟢 All E2E test cases PASSED!")
        sys.exit(0)
    else:
        print("🔴 Test suite reported failures or errors. See details above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
