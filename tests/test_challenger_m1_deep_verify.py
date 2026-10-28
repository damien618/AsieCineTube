#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Adversarial Deep Verification Harness for Milestone 1 Remediation (Iteration 2).
Empirical challenger tests to verify:
1. Schemeless URL stripping robustness
2. Spaceless channel handle normalization across all 35 excluded channels
3. Full NoneType and extreme value safety across server.py functions
4. Atomic cache persistence and corruption recovery
5. Seed hygiene and catalog preservation (KOFA & SOONER)
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import server


class TestMilestone1EmpiricalVerification(unittest.TestCase):

    # ----------------------------------------------------------------------
    # 1. Schemeless URL Stripping Robustness
    # ----------------------------------------------------------------------
    def test_01_schemeless_url_stripping_variations(self):
        """Verify schemeless URL stripping across varied YouTube shortlinks and domains."""
        url_variations = [
            "youtu.be/gil-ozu-xyz",
            "youtu.be/gil_ozu_xyz",
            "youtu.be/hash-kurosawa-123",
            "youtu.be/random-bong-456",
            "youtu.be/test-lee-789",
            "m.youtu.be/gil-ozu-xyz",
            "www.youtu.be/gil-ozu-xyz",
            "youtube.com/watch?v=gil-ozu-xyz",
            "m.youtube.com/watch?v=gil-ozu-xyz",
            "www.youtube.com/watch?v=gil-ozu-xyz",
            "https://youtu.be/gil-ozu-xyz",
            "http://youtu.be/gil-ozu-xyz",
            "(youtu.be/gil-ozu-xyz)",
            "[youtu.be/gil-ozu-xyz]",
            "youtu.be/gil-ozu-xyz?si=abc1234&t=100s",
            "youtu.be/gil-ozu-xyz#t=10",
        ]
        for url_sample in url_variations:
            with self.subTest(url=url_sample):
                text = f"B-movie action kung fu ninja check {url_sample} full clip"
                director = server.detect_auteur(text)
                self.assertIsNone(
                    director,
                    f"URL '{url_sample}' falsely caused detect_auteur to return '{director}'"
                )

                # Now check that is_strictly_asian_movie rejects it despite the shortlink containing an auteur name
                rejected = server.is_strictly_asian_movie(
                    title="Ninja Master Revenge",
                    channel="Action World",
                    description=f"Watch full action: {url_sample}",
                    channel_url="https://youtube.com/@actionworld"
                )
                self.assertFalse(
                    rejected,
                    f"B-movie with URL hash '{url_sample}' should NOT be whitelisted"
                )

    def test_02_schemeless_url_stripping_preserves_legitimate_auteurs(self):
        """Verify that stripping URLs does NOT strip legitimate auteur names in text."""
        legit_cases = [
            ("Tokyo Story - Yasujirō Ozu", "Classic Cinema", "Watch on youtu.be/abc-123-xyz", "Yasujirō Ozu"),
            ("Seven Samurai (1954)", "Akira Kurosawa Fan", "Link: https://youtu.be/xyz-789", "Akira Kurosawa"),
            ("Memories of Murder - Bong Joon-ho", "Korean Cine", "Trailer at youtu.be/def-456", "Bong Joon-ho"),
            ("Harakiri (1962)", "Masaki Kobayashi Cinema", "Restored version. See youtu.be/aaa-bbb", "Masaki Kobayashi"),
        ]
        for title, channel, desc, expected_director in legit_cases:
            with self.subTest(title=title):
                detected = server.detect_auteur(f"{title} {channel} {desc}")
                self.assertEqual(
                    detected,
                    expected_director,
                    f"Legitimate director '{expected_director}' not detected in '{title}'"
                )
                is_asian = server.is_strictly_asian_movie(
                    title, channel, desc, "https://youtube.com/@cinemaclassique"
                )
                self.assertTrue(
                    is_asian,
                    f"Legitimate film '{title}' by '{expected_director}' was falsely rejected!"
                )

    # ----------------------------------------------------------------------
    # 2. Spaceless Channel Handle Normalization
    # ----------------------------------------------------------------------
    def test_03_all_35_excluded_channels_rejected_under_handles(self):
        """Every channel in EXCLUDED_CHANNELS must be rejected in handle format @<spaceless_name>."""
        for ec in server.EXCLUDED_CHANNELS:
            clean_handle = server.RE_CHANNEL_NORM.sub("", ec)
            handle_url = f"https://www.youtube.com/@{clean_handle}"
            with self.subTest(channel=ec, handle=clean_handle):
                # Channel name is generic Asian archive, but URL is the excluded handle
                res = server.is_strictly_asian_movie(
                    title="Authentic Asian Movie (한국 영화)",
                    channel="Asian Heritage Vault",
                    description="Classic Korean drama film in full HD",
                    channel_url=handle_url
                )
                self.assertFalse(
                    res,
                    f"Excluded channel '{ec}' bypassed filter via handle URL '{handle_url}'"
                )

    def test_04_channel_handle_punctuation_and_encoding_variations(self):
        """Channel handles with underscores, hyphens, and url-encoded characters must be rejected."""
        test_handles = [
            ("https://www.youtube.com/@samurai-vs-ninja", "samurai vs ninja"),
            ("https://www.youtube.com/@samurai_vs_ninja", "samurai vs ninja"),
            ("https://www.youtube.com/@SAMURAI-VS-NINJA", "samurai vs ninja"),
            ("https://www.youtube.com/@chinese_online_movie_channel", "chinese online movie channel"),
            ("https://www.youtube.com/@chinese-online-movie-channel", "chinese online movie channel"),
            ("https://www.youtube.com/@iqiyi_action", "iqiyi action"),
            ("https://www.youtube.com/@iqiyi-action", "iqiyi action"),
            ("https://www.youtube.com/@cin%C3%A9-nanar", "ciné nanar"),
            ("https://www.youtube.com/@cine_nanar", "cine nanar"),
            ("https://www.youtube.com/@allocine_films_complets", "allociné films complets"),
        ]
        for url, ch_desc in test_handles:
            with self.subTest(url=url):
                res = server.is_strictly_asian_movie(
                    title="Classic Film (한국)",
                    channel="Random Asian Archive",
                    description="Korean drama",
                    channel_url=url
                )
                self.assertFalse(
                    res,
                    f"Channel handle variant '{url}' ({ch_desc}) should be rejected"
                )

    # ----------------------------------------------------------------------
    # 3. NoneType and Type Safety Across All Core Functions
    # ----------------------------------------------------------------------
    def test_05_nonetype_and_empty_safety_in_filter_engine(self):
        """Ensure no crashes when None, empty strings, or invalid types are passed to filter functions."""
        # 1. detect_auteur
        self.assertIsNone(server.detect_auteur(None))
        self.assertIsNone(server.detect_auteur(""))

        # 2. has_festival_marker
        self.assertFalse(server.has_festival_marker(None))
        self.assertFalse(server.has_festival_marker(""))

        # 3. detect_auteur_label
        is_aut, lbl = server.detect_auteur_label(None, None, None, None)
        self.assertFalse(is_aut)
        self.assertIsNone(lbl)

        # 4. is_strictly_asian_movie
        self.assertFalse(server.is_strictly_asian_movie(None, None, None, None))
        self.assertFalse(server.is_strictly_asian_movie("", "", "", ""))

        # 5. detect_country & detect_genre
        self.assertEqual(server.detect_country(None, None, None, "kr"), "kr")
        self.assertEqual(server.detect_genre(None, None, "drama"), "drama")

        # 6. date helpers
        self.assertEqual(server.date_to_timestamp(None), 0)
        self.assertEqual(server.format_french_date(None), None)
        self.assertEqual(server.format_relative_date(None), "récemment")

        # 7. duration & view helpers
        self.assertEqual(server.parse_duration_text(None), 0)
        self.assertEqual(server.format_duration(None or 0), "1:45:00")
        self.assertEqual(server.format_views(None or 0), "0 vues")

    def test_06_enrich_movie_fields_extreme_inputs(self):
        """Stress enrich_movie_fields with pathological and malformed inputs."""
        extreme_cases = [
            None,
            {},
            [],
            "not a dict",
            12345,
            {"videoId": None, "title": None, "channelName": None, "description": None},
            {"durationSeconds": "one_hour_thirty", "viewCount": "a_lot_of_views"},
            {"durationSeconds": None, "viewCount": None},
            {"durationSeconds": -500, "viewCount": -10},
            {"durationSeconds": 99999999999, "viewCount": 99999999999},
            {"publishDate": None},
            {"publishDate": "invalid_date_format"},
            {"publishDate": 20250101},
            {"availableLanguages": None},
            {"availableLanguages": "fr"},
            {"availableLanguages": {"lang": "fr"}},
            {"isPaid": None, "isAuteur": None, "channelVerified": None},
            {"category": None, "country": None},
            {"title": "Memories of Murder", "channelName": "SOONER", "isPaid": "true"},
            {"title": "The Power of Kangwon Province", "channelName": "Korean Classic Film", "category": "kofa"},
        ]
        for idx, case in enumerate(extreme_cases):
            with self.subTest(case_idx=idx):
                out = server.enrich_movie_fields(case)
                self.assertIsInstance(out, dict, "enrich_movie_fields must always return a dict")
                self.assertIn("videoId", out)
                self.assertIn("title", out)
                self.assertIn("isAuteur", out)
                self.assertIn("category", out)
                self.assertIn("durationSeconds", out)
                self.assertIsInstance(out["durationSeconds"], int)
                self.assertIsInstance(out["viewCount"], int)
                self.assertIsInstance(out["isAuteur"], bool)
                self.assertIsInstance(out["availableLanguages"], list)

    # ----------------------------------------------------------------------
    # 4. Atomic Cache Persistence & Error Recovery
    # ----------------------------------------------------------------------
    def test_07_save_cached_movies_atomic_guarantee_and_cleanup(self):
        """Verify that save_cached_movies guarantees atomic writes and cleans up temporary files on error."""
        temp_dir = tempfile.mkdtemp(prefix="asiecine_challenger_")
        orig_cache = server.CACHE_FILE
        orig_static = server.STATIC_EXPORT_FILE

        try:
            test_cache = os.path.join(temp_dir, "cache_movies.json")
            test_static = os.path.join(temp_dir, "movies.json")
            server.CACHE_FILE = test_cache
            server.STATIC_EXPORT_FILE = test_static

            # Step 1: Save valid initial cache
            initial_data = {
                "vid_valid": {
                    "videoId": "vid_valid",
                    "title": "Rashōmon (羅生門) — Akira Kurosawa",
                    "channelName": "Cinéma Japonais Classique",
                    "description": "Lion d'or Venise",
                    "durationSeconds": 5280,
                    "publishDate": "2026-03-23",
                    "country": "jp",
                    "category": "auteur",
                }
            }
            server.save_cached_movies(initial_data)

            self.assertTrue(os.path.exists(test_cache))
            self.assertTrue(os.path.exists(test_static))
            with open(test_cache, "r", encoding="utf-8") as f:
                initial_cache_content = f.read()
            with open(test_static, "r", encoding="utf-8") as f:
                initial_static_content = f.read()

            # Step 2: Attempt to save un-serializable data (availableLanguages with set)
            corrupt_data = {
                "vid_bad": {
                    "videoId": "vid_bad",
                    "title": "Rashōmon (羅生門) — Akira Kurosawa",
                    "channelName": "Cinéma Japonais Classique",
                    "description": "Lion d'or Venise",
                    "durationSeconds": 5280,
                    "publishDate": "2026-03-23",
                    "country": "jp",
                    "category": "auteur",
                    "availableLanguages": [{1, 2, 3}],  # Set inside list survives enrich_movie_fields and fails json.dump
                }
            }
            # save_cached_movies prints the error and handles it cleanly
            server.save_cached_movies(corrupt_data)

            # Verify that temporary files were cleaned up
            self.assertFalse(
                os.path.exists(test_cache + ".tmp"),
                "Temporary cache file .tmp was NOT cleaned up after error!"
            )
            self.assertFalse(
                os.path.exists(test_static + ".tmp"),
                "Temporary static file .tmp was NOT cleaned up after error!"
            )

            # Verify that the original files were NOT truncated or modified
            with open(test_cache, "r", encoding="utf-8") as f:
                current_cache_content = f.read()
            with open(test_static, "r", encoding="utf-8") as f:
                current_static_content = f.read()
            self.assertEqual(
                initial_cache_content,
                current_cache_content,
                "Cache file was altered/corrupted during failed serialization!"
            )
            self.assertEqual(
                initial_static_content,
                current_static_content,
                "Static export file was altered/corrupted during failed serialization!"
            )

        finally:
            server.CACHE_FILE = orig_cache
            server.STATIC_EXPORT_FILE = orig_static
            shutil.rmtree(temp_dir, ignore_errors=True)

    # ----------------------------------------------------------------------
    # 5. Seed Hygiene & Catalog Preservation
    # ----------------------------------------------------------------------
    def test_08_seed_movies_hygiene(self):
        """Verify that SEED_MOVIES contains NO excluded channels, NO B-movie martial arts, and valid films."""
        self.assertGreaterEqual(len(server.SEED_MOVIES), 5, "At least 5 seed movies must exist.")
        for idx, seed in enumerate(server.SEED_MOVIES):
            vid = seed.get("videoId")
            ch_name = seed.get("channelName", "")
            ch_url = seed.get("channelUrl", "")
            title = seed.get("title", "")
            desc = seed.get("description", "")

            # Must not be Ciné Nanar
            self.assertNotIn(
                "ciné nanar",
                ch_name.lower(),
                f"Seed #{idx} ({vid}) is Ciné Nanar! Seed hygiene violated."
            )
            self.assertNotIn(
                "cinenanar",
                ch_url.lower(),
                f"Seed #{idx} ({vid}) points to cinenanar URL! Seed hygiene violated."
            )

            # Must pass is_strictly_asian_movie
            passes = server.is_strictly_asian_movie(title, ch_name, desc, ch_url)
            self.assertTrue(
                passes,
                f"Seed #{idx} ({title}) failed is_strictly_asian_movie! Seed must be valid."
            )

    def test_09_kofa_and_sooner_catalog_preservation(self):
        """Verify that 100% of KOFA (>=140) and SOONER (>=50) movies in cache_movies.json are accepted."""
        cache_path = os.path.join(BASE_DIR, "cache_movies.json")
        self.assertTrue(os.path.exists(cache_path), "cache_movies.json must exist")
        with open(cache_path, "r", encoding="utf-8") as f:
            catalog = json.load(f)

        kofa_movies = [
            m for m in catalog.values()
            if isinstance(m, dict) and (
                m.get("category") == "kofa"
                or "koreanfilm" in m.get("channelUrl", "").lower()
                or "koreanfilm" in m.get("channelName", "").lower()
            )
        ]
        self.assertGreaterEqual(
            len(kofa_movies), 140, f"Expected >= 140 KOFA movies, found {len(kofa_movies)}"
        )
        for m in kofa_movies:
            ok = server.is_strictly_asian_movie(
                m.get("title", ""),
                m.get("channelName", ""),
                m.get("description", ""),
                m.get("channelUrl", "")
            )
            self.assertTrue(ok, f"KOFA film '{m.get('title')}' was falsely rejected!")

        sooner_movies = [
            m for m in catalog.values()
            if isinstance(m, dict) and (
                "sooner" in m.get("channelName", "").lower()
                or "@soonerfrance" in m.get("channelUrl", "").lower()
            )
        ]
        self.assertGreaterEqual(
            len(sooner_movies), 50, f"Expected >= 50 SOONER movies, found {len(sooner_movies)}"
        )
        for m in sooner_movies:
            ok = server.is_strictly_asian_movie(
                m.get("title", ""),
                m.get("channelName", ""),
                m.get("description", ""),
                m.get("channelUrl", "")
            )
            self.assertTrue(ok, f"SOONER film '{m.get('title')}' was falsely rejected!")


if __name__ == "__main__":
    unittest.main()
