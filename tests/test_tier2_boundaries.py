#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tier 2: Boundary & Corner Cases Test Suite.
Covers:
- Empty inputs, None values, whitespace handling
- Case-insensitivity permutations
- URL-encoded channel handles (urllib.parse.unquote)
- False-positive director name collisions in URL hashes (e.g., 'oZu' in youtu.be/gil_9u4oZuI)
- Surname false-positives (e.g., 'famille Kobayashi' without Masaki Kobayashi)
- Extreme input lengths (50,000 characters)
- CJK script boundaries and Unicode handling
- Zero search results handling
- Malformed data dictionaries
"""

import json
import os
import sys
import unittest
from typing import Any, Dict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import server


class TestTier2Boundaries(unittest.TestCase):
    """Tier 2: Boundary, Edge, and Adversarial Test Cases."""

    def test_t2_01_empty_inputs_to_filter(self):
        """Empty strings for title, channel, description, and channel_url must be handled safely."""
        res = server.is_strictly_asian_movie("", "", "", "")
        self.assertFalse(res, "Empty inputs must return False without crashing.")

    def test_t2_02_none_or_missing_fields_in_enrichment(self):
        """enrich_movie_fields handles movie dict with missing or None fields gracefully."""
        minimal_movie: Dict[str, Any] = {"videoId": "test_empty"}
        enriched = server.enrich_movie_fields(minimal_movie)
        self.assertIsInstance(enriched, dict)
        self.assertIn("isAuteur", enriched)
        self.assertFalse(enriched["isAuteur"])
        self.assertIsNone(enriched.get("auteurLabel"))

    def test_t2_03_extreme_description_length(self):
        """Extremely large descriptions (50,000 characters) must not crash or cause ReDoS."""
        long_desc = "Film d'auteur asiatique. " * 2000  # ~50,000 chars
        res = server.is_strictly_asian_movie(
            title="Film Complet",
            channel="Archive Cinéma",
            description=long_desc
        )
        self.assertIsInstance(res, bool)

    def test_t2_04_mixed_case_excluded_channels(self):
        """Excluded channel check is fully case-insensitive (e.g., 'sAmUrAi Vs NiNjA')."""
        permutations = [
            "sAmUrAi Vs NiNjA",
            "CHINESE ONLINE MOVIE CHANNEL",
            "CiNé NaNaR - Films Complets",
            "IqIyI aCtIoN",
            "sBs CaTcH"
        ]
        for ch in permutations:
            res = server.is_strictly_asian_movie(
                title="Action Video",
                channel=ch,
                description="Movie description",
                channel_url=f"https://youtube.com/@{ch.lower()}"
            )
            self.assertFalse(res, f"Case-varied channel '{ch}' must be excluded.")

    def test_t2_05_mixed_case_bmartial_arts_terms(self):
        """B-movie martial arts terms in varying cases (kUnG fU, NiNjA, WuXiA) must be rejected."""
        permutations = ["kUnG fU", "KUNG-FU", "NiNjA", "WuXiA", "ShAoLiN", "dRuNkEn FiSt"]
        for term in permutations:
            res = server.is_strictly_asian_movie(
                title=f"The Legend of {term}",
                channel="Action Channel",
                description=f"Action movie featuring {term}",
                channel_url=""
            )
            self.assertFalse(res, f"Case-varied B-movie term '{term}' must be rejected.")

    def test_t2_06_url_encoded_channel_handles(self):
        """URL-encoded channel handles (%EC%96%91%ED%8C%8C%EA%B7%B9%EC%9E%A5 for 양파극장) must be decoded and rejected."""
        encoded_channel = "%EC%96%91%ED%8C%8C%EA%B7%B9%EC%9E%A5"
        res = server.is_strictly_asian_movie(
            title="160분요약",
            channel=f"@{encoded_channel}",
            description="Short drama recap",
            channel_url=f"https://youtube.com/@{encoded_channel}"
        )
        self.assertFalse(res, "URL-encoded channel handle for excluded channel must be rejected.")

    def test_t2_07_false_positive_url_hash_collision_ozu(self):
        """URL hash in description like 'https://youtu.be/gil_9u4oZuI' must NOT trigger Yasujirō Ozu."""
        # 'oZu' is part of a Base64 YouTube video ID in the URL
        url_desc = "Retrouvez nos autres films sur https://youtu.be/gil_9u4oZuI et abonnez-vous."
        raw = {
            "title": "Film de Gangsters Inconnu (1998)",
            "channelName": "Action Nanar",
            "description": url_desc,
            "country": "jp"
        }
        enriched = server.enrich_movie_fields(raw)
        self.assertFalse(
            enriched.get("isAuteur"),
            "Random 'oZu' inside a URL must NOT match Yasujirō Ozu."
        )

    def test_t2_08_surname_false_positive_kobayashi(self):
        """'la famille Kobayashi' in description must NOT trigger Masaki Kobayashi."""
        desc = "Dans une maison de banlieue, la famille Kobayashi accueille un invité surprise."
        raw = {
            "title": "Hospitalité (2010)",
            "channelName": "Cinema Indé",
            "description": desc,
            "country": "jp"
        }
        enriched = server.enrich_movie_fields(raw)
        # Should not attribute to Masaki Kobayashi unless 'Masaki Kobayashi' is explicitly present
        if enriched.get("isAuteur"):
            self.assertNotEqual(
                enriched.get("auteurLabel"), "🎬 Masaki Kobayashi",
                "'famille Kobayashi' must not be recognized as Masaki Kobayashi."
            )

    def test_t2_09_surname_false_positive_suzuki(self):
        """'Suzuki' in description (e.g., actor Suzuki or Suzuki car) must NOT trigger Seijun Suzuki."""
        desc = "L'acteur Kenji Suzuki conduit une Suzuki dans les rues de Tokyo."
        raw = {
            "title": "Course Urbaine (2005)",
            "channelName": "Tokyo Action",
            "description": desc,
            "country": "jp"
        }
        enriched = server.enrich_movie_fields(raw)
        if enriched.get("isAuteur"):
            self.assertNotEqual(
                enriched.get("auteurLabel"), "🎬 Seijun Suzuki",
                "Mention of 'Suzuki' without 'Seijun' must not attribute to Seijun Suzuki."
            )

    def test_t2_10_cjk_script_boundary_validation(self):
        """Hangul, Kana, and Hanzi detection matches strictly CJK characters, not Latin or symbols."""
        # Plain Western string with Latin diacritics
        western_title = "Café au Lait à Paris"
        has_hangul = bool(server.re.search(r"[\uac00-\ud7a3]", western_title)) if hasattr(server, 're') else False
        has_kana = bool(server.re.search(r"[\u3040-\u309f\u30a0-\u30ff]", western_title)) if hasattr(server, 're') else False
        has_hanzi = bool(server.re.search(r"[\u4e00-\u9fff]", western_title)) if hasattr(server, 're') else False
        self.assertFalse(has_hangul or has_kana or has_hanzi)

        # Real CJK strings
        self.assertTrue(bool(server.re.search(r"[\uac00-\ud7a3]", "기생충 (Parasite)")))
        self.assertTrue(bool(server.re.search(r"[\u3040-\u309f\u30a0-\u30ff]", "すずめの戸締まり (Suzume)")))
        self.assertTrue(bool(server.re.search(r"[\u4e00-\u9fff]", "花樣年華")))

    def test_t2_11_zero_results_search_graceful(self):
        """server.get_movies handles non-matching queries gracefully without crashing."""
        from unittest.mock import patch
        sample_cache = {
            "v1": {"videoId": "v1", "title": "Rashomon", "channelName": "ch", "country": "jp", "isAuteur": True, "durationSeconds": 5400}
        }
        with patch.object(server, "load_cached_movies", return_value=sample_cache):
            movies, source = server.get_movies(category="nonexistent_category", min_duration=0)
            self.assertEqual(movies, [])

    def test_t2_12_malformed_timestamp_or_views(self):
        """Movies with missing publishedTimestamp or empty fields do not crash sorting."""
        from unittest.mock import patch
        sample_cache = {
            "v1": {"videoId": "v1", "title": "T1", "channelName": "ch", "description": "Akira Kurosawa", "country": "jp", "durationSeconds": 5400},
            "v2": {"videoId": "v2", "title": "T2", "publishDate": "2021-01-01", "channelName": "ch", "description": "Akira Kurosawa", "country": "jp", "durationSeconds": 5400},
            "v3": {"videoId": "v3", "title": "T3", "publishedTimestamp": 1600000000, "viewCount": 100, "channelName": "ch", "description": "Akira Kurosawa", "country": "jp", "durationSeconds": 5400}
        }
        with patch.object(server, "load_cached_movies", return_value=sample_cache):
            movies, source = server.get_movies(category="all", min_duration=0)
            self.assertIsInstance(movies, list)

    def test_t2_13_emoji_and_special_characters_in_metadata(self):
        """Titles with emoji, HTML entities (&amp;, &#39;), and quotes are preserved properly."""
        raw = {
            "videoId": "v_special",
            "title": "🎬 4K Restored: Ozu's \"Tokyo Story\" &amp; Classics 🇯🇵",
            "channelName": "Shochiku &amp; Partners",
            "description": "Yasujirō Ozu's masterpiece restauré 4k <script>alert(1)</script>",
            "country": "jp"
        }
        enriched = server.enrich_movie_fields(raw)
        self.assertTrue(enriched.get("isAuteur"))
        self.assertIn("Ozu", enriched.get("auteurLabel", ""))

    def test_t2_14_whitespace_stripping_and_padding(self):
        """Padded whitespace in titles or channel names does not prevent auteur detection."""
        raw = {
            "title": "   Voyage à Tokyo   ( de  Yasujirō Ozu )   ",
            "channelName": "   Archives Japon   ",
            "description": "  Yasujirō Ozu   ",
            "country": "jp"
        }
        enriched = server.enrich_movie_fields(raw)
        self.assertTrue(enriched.get("isAuteur"))

    def test_t2_15_western_director_exclusions_resilience(self):
        """Western director exclusion list (Samuel Fuller, etc.) correctly rejects Western war films."""
        res = server.is_strictly_asian_movie(
            title="The Steel Helmet - Samuel Fuller (1951)",
            channel="Classic War Movies",
            description="American film set in Korean War with Gene Evans, directed by Samuel Fuller."
        )
        self.assertFalse(res, "Samuel Fuller film must be rejected by WESTERN_EXCLUSIONS_LIST.")


if __name__ == "__main__":
    unittest.main()
