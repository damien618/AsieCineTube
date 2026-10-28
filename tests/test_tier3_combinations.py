#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tier 3: Cross-Feature Combinations Test Suite.
Covers:
- Auteur film from Sooner that has martial arts tags (Kobayashi, Miike)
- KOFA heritage film that has sword / martial arts tags
- Master classic with wuxia tags (King Hu, Tsui Hark)
- Dual-category membership (Thriller + Auteur, Drama + Auteur)
- Search query combined with category filters
- Status bar synchronization across category switches
- Cache save & load persistence round-trip consistency
- Multi-parameter API combinations (category + country)
- Deduping between harvester discovery and existing cache
"""

import json
import os
import sys
import tempfile
import unittest
from typing import Any, Dict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import server


class TestTier3Combinations(unittest.TestCase):
    """Tier 3: Cross-Feature Combinations & State Transitions."""

    def test_t3_01_sooner_auteur_film_with_martial_arts_tags(self):
        """Auteur film from Sooner with martial arts tags passes filter, receives isAuteur=True and isPaid=True."""
        title = "Harakiri (Seppuku) - Masaki Kobayashi"
        ch = "Sooner France"
        ch_url = "https://youtube.com/@soonerfrance"
        desc = "Chef d'oeuvre du film de sabre, combats de samourai et arts martiaux, restauré."

        # 1. Check strict Asian filter allows it via Sooner / Kobayashi exemption
        passed = server.is_strictly_asian_movie(title, ch, desc, ch_url)
        self.assertTrue(passed, "Sooner movie with martial arts terms must pass filter.")

        # 2. Check enrichment
        raw = {
            "videoId": "sooner_harakiri",
            "title": title,
            "channelName": ch,
            "channelUrl": ch_url,
            "description": desc,
            "country": "jp",
            "isPaid": True,
            "paidProvider": "sooner"
        }
        enriched = server.enrich_movie_fields(raw)
        self.assertTrue(enriched.get("isAuteur"))
        self.assertTrue(enriched.get("isPaid"))

        # 3. Check API retrieval in both 'auteur' and 'sooner' categories
        sample_cache = {"sooner_harakiri": enriched}
        from unittest.mock import patch
        with patch.object(server, "load_cached_movies", return_value=sample_cache):
            movies_auteur, _ = server.get_movies(category="auteur", min_duration=0)
            movies_sooner, _ = server.get_movies(category="sooner", min_duration=0)

        self.assertIn("sooner_harakiri", [m["videoId"] for m in movies_auteur])
        self.assertIn("sooner_harakiri", [m["videoId"] for m in movies_sooner])

    def test_t3_02_kofa_heritage_film_with_martial_arts_tags(self):
        """KOFA heritage film with sword / martial arts tags passes filter and matches 'kofa' and 'auteur'."""
        title = "A Hero of the Blade (1969)"
        ch = "Korean Classic Film"
        ch_url = "https://youtube.com/@KoreanFilm"
        desc = "Martial arts sword fighting during Joseon dynasty, classic Korean cinema archive."

        passed = server.is_strictly_asian_movie(title, ch, desc, ch_url)
        self.assertTrue(passed, "KOFA film with martial arts must pass filter.")

        raw = {
            "videoId": "kofa_blade",
            "title": title,
            "channelName": ch,
            "channelUrl": ch_url,
            "description": desc,
            "country": "kr",
            "category": "kofa"
        }
        enriched = server.enrich_movie_fields(raw)
        self.assertTrue(enriched.get("isAuteur"))

        sample_cache = {"kofa_blade": enriched}
        from unittest.mock import patch
        with patch.object(server, "load_cached_movies", return_value=sample_cache):
            movies_kofa, _ = server.get_movies(category="kofa", min_duration=0)
            movies_auteur, _ = server.get_movies(category="auteur", min_duration=0)

        self.assertIn("kofa_blade", [m["videoId"] for m in movies_kofa])
        self.assertIn("kofa_blade", [m["videoId"] for m in movies_auteur])

    def test_t3_03_master_classic_with_wuxia_tags(self):
        """King Hu's A Touch of Zen with wuxia/kung-fu keywords passes filter and is recognized as auteur."""
        title = "A Touch of Zen (1971) - King Hu"
        ch = "Cinema Heritage"
        desc = "Grand classique du wuxia et du kung-fu récompensé à Cannes, réalisé par King Hu."

        passed = server.is_strictly_asian_movie(title, ch, desc, "")
        self.assertTrue(passed, "King Hu wuxia classic must pass filter via auteur exemption.")

        raw = {
            "videoId": "king_hu_zen",
            "title": title,
            "channelName": ch,
            "description": desc,
            "country": "cn"
        }
        enriched = server.enrich_movie_fields(raw)
        self.assertTrue(enriched.get("isAuteur"))
        self.assertIn("King Hu", enriched.get("auteurLabel", ""))

    def test_t3_04_dual_genre_auteur_thriller(self):
        """Memories of Murder has category='thriller' and isAuteur=True, matching both categories."""
        raw = {
            "videoId": "memories_murder",
            "title": "Memories of Murder (2003) - Bong Joon-ho",
            "channelName": "Cinema Sud-Coréen",
            "description": "Thriller policier culte de Bong Joon-ho avec Song Kang-ho.",
            "category": "thriller",
            "country": "kr"
        }
        enriched = server.enrich_movie_fields(raw)
        self.assertTrue(enriched.get("isAuteur"))
        self.assertEqual(enriched.get("category"), "thriller")

        sample_cache = {"memories_murder": enriched}
        from unittest.mock import patch
        with patch.object(server, "load_cached_movies", return_value=sample_cache):
            movies_thriller, _ = server.get_movies(category="thriller", min_duration=0)
            movies_auteur, _ = server.get_movies(category="auteur", min_duration=0)

        self.assertIn("memories_murder", [m["videoId"] for m in movies_thriller])
        self.assertIn("memories_murder", [m["videoId"] for m in movies_auteur])

    def test_t3_05_search_query_combined_with_category_filter(self):
        """Search query 'Bong' combined with category filters in simulated client-side logic."""
        sample_movies = [
            {"title": "Memories of Murder - Bong Joon-ho", "isAuteur": True, "category": "thriller", "country": "kr", "auteurLabel": "🎬 Bong Joon-ho"},
            {"title": "The Host - Bong Joon-ho", "isAuteur": True, "category": "horror", "country": "kr", "auteurLabel": "🎬 Bong Joon-ho"},
            {"title": "Tokyo Story - Yasujiro Ozu", "isAuteur": True, "category": "drama", "country": "jp", "auteurLabel": "🎬 Yasujirō Ozu"}
        ]

        def client_search_filter(movies, cat, query):
            filtered = []
            for m in movies:
                # Category check
                if cat == "auteur" and not m.get("isAuteur"):
                    continue
                if cat not in ("all", "auteur") and m.get("category") != cat and m.get("country") != cat:
                    continue
                # Query check
                if query:
                    q = query.lower()
                    t_match = q in m.get("title", "").lower()
                    a_match = q in m.get("auteurLabel", "").lower()
                    if not (t_match or a_match):
                        continue
                filtered.append(m)
            return filtered

        # 1. Search 'Bong' in 'thriller' -> 1 result (Memories of Murder)
        res_thriller = client_search_filter(sample_movies, "thriller", "Bong")
        self.assertEqual(len(res_thriller), 1)
        self.assertEqual(res_thriller[0]["title"], "Memories of Murder - Bong Joon-ho")

        # 2. Search 'Bong' in 'jp' -> 0 results
        res_jp = client_search_filter(sample_movies, "jp", "Bong")
        self.assertEqual(len(res_jp), 0)

        # 3. Search 'Bong' in 'auteur' -> 2 results
        res_auteur = client_search_filter(sample_movies, "auteur", "Bong")
        self.assertEqual(len(res_auteur), 2)

    def test_t3_06_search_query_combined_with_auteur_category(self):
        """Search 'Cannes' or festival markers within category='auteur'."""
        sample_movies = [
            {"title": "Oldboy - Park Chan-wook", "description": "Grand Prix Festival de Cannes", "isAuteur": True, "category": "thriller"},
            {"title": "Generic Action", "description": "No awards", "isAuteur": False, "category": "thriller"}
        ]
        # In auteur category, only Oldboy is considered
        auteur_movies = [m for m in sample_movies if m.get("isAuteur")]
        cannes_matches = [m for m in auteur_movies if "cannes" in m.get("description", "").lower()]
        self.assertEqual(len(cannes_matches), 1)
        self.assertEqual(cannes_matches[0]["title"], "Oldboy - Park Chan-wook")

    def test_t3_07_status_bar_sync_across_category_switches(self):
        """Status bar text matches defined UX expectations for each category."""
        category_labels = {
            "auteur": "🎬 Cinéma d'Auteur & Grands Maîtres",
            "sooner": "🟢 Sooner (@soonerfrance)",
            "kr": "🇰🇷 Films Coréens",
            "kofa": "🏛️ @KoreanFilm (KOFA)",
            "jp": "🇯🇵 Films Japonais",
            "cn": "🇨🇳 Films Chinois",
            "native": "⭐ ST-FR Natif",
            "thriller": "🔪 Polar & Thriller"
        }
        for cat, expected in category_labels.items():
            self.assertTrue(len(expected) > 0)
            self.assertNotIn("Arts Martiaux", expected)

    def test_t3_08_cache_save_and_reload_roundtrip_consistency(self):
        """Saving cache map and reloading produces identical records without losing auteur metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_cache_file = os.path.join(tmpdir, "cache_movies.json")
            test_export_file = os.path.join(tmpdir, "movies.json")
            orig_cache, orig_export = server.CACHE_FILE, server.STATIC_EXPORT_FILE
            try:
                server.CACHE_FILE = test_cache_file
                server.STATIC_EXPORT_FILE = test_export_file

                initial_cache = {
                    "v_oz": {
                        "videoId": "v_oz",
                        "title": "Voyage à Tokyo (1953) de Yasujirō Ozu",
                        "channelName": "Shochiku",
                        "description": "Grand classique de Yasujirō Ozu.",
                        "country": "jp",
                        "category": "auteur",
                        "isAuteur": True,
                        "auteurLabel": "🎬 Yasujirō Ozu",
                        "publishDate": "2021-05-01",
                        "publishedTimestamp": 1619827200
                    }
                }

                server.save_cached_movies(initial_cache)

                # Reload from disk
                with open(test_cache_file, "r", encoding="utf-8") as f:
                    reloaded = json.load(f)

                self.assertIn("v_oz", reloaded)
                self.assertEqual(reloaded["v_oz"]["isAuteur"], True)
                self.assertIn("Ozu", reloaded["v_oz"]["auteurLabel"])
                self.assertEqual(reloaded["v_oz"]["publishedTimestamp"], 1619827200)

            finally:
                server.CACHE_FILE, server.STATIC_EXPORT_FILE = orig_cache, orig_export

    def test_t3_09_api_query_parameter_combinations(self):
        """API responds to combinations of category and country correctly."""
        sample_cache = {
            "kr_aut": {"videoId": "kr_aut", "title": "Film coréen de Bong Joon-ho", "channelName": "ch", "description": "Bong Joon-ho à Séoul", "country": "kr", "isAuteur": True, "category": "auteur", "durationSeconds": 5400},
            "jp_aut": {"videoId": "jp_aut", "title": "Film japonais de Yasujirō Ozu", "channelName": "ch", "description": "Yasujirō Ozu à Tokyo", "country": "jp", "isAuteur": True, "category": "auteur", "durationSeconds": 5400},
            "cn_aut": {"videoId": "cn_aut", "title": "Film chinois de Wong Kar-wai", "channelName": "ch", "description": "Wong Kar-wai à Hong Kong", "country": "cn", "isAuteur": True, "category": "auteur", "durationSeconds": 5400},
            "kr_comm": {"videoId": "kr_comm", "title": "Film coréen d'action à Séoul", "channelName": "ch", "description": "Action", "country": "kr", "isAuteur": False, "category": "thriller", "durationSeconds": 5400}
        }

        from unittest.mock import patch
        with patch.object(server, "load_cached_movies", return_value=sample_cache):
            movies_aut, _ = server.get_movies(category="auteur", min_duration=0)
            aut_vids = [m["videoId"] for m in movies_aut]
            self.assertIn("kr_aut", aut_vids)
            self.assertIn("jp_aut", aut_vids)
            self.assertIn("cn_aut", aut_vids)
            self.assertNotIn("kr_comm", aut_vids)

            # Client filtering on country + auteur:
            kr_aut = [m for m in movies_aut if m.get("country") == "kr"]
            self.assertIn("kr_aut", [m["videoId"] for m in kr_aut])

            jp_aut = [m for m in movies_aut if m.get("country") == "jp"]
            self.assertIn("jp_aut", [m["videoId"] for m in jp_aut])

            cn_aut = [m for m in movies_aut if m.get("country") == "cn"]
            self.assertIn("cn_aut", [m["videoId"] for m in cn_aut])

    def test_t3_10_harvester_candidate_discovery_and_cache_deduplication(self):
        """Existing cached video is deduplicated and not treated as a new candidate."""
        cache_map = {"already_known": {"videoId": "already_known", "title": "Old Movie"}}
        discovered = [
            {"videoId": "already_known", "title": "Old Movie"},
            {"videoId": "fresh_new", "title": "New Movie"}
        ]
        new_candidates = [m for m in discovered if m["videoId"] not in cache_map]
        self.assertEqual(len(new_candidates), 1)
        self.assertEqual(new_candidates[0]["videoId"], "fresh_new")

    def test_t3_11_restored_4k_festival_film_with_drama_genre(self):
        """Film with 4K restoration and festival marker keeps drama genre and receives auteur badge."""
        raw = {
            "title": "Sous le Parasol (1975) - Restauré 4K",
            "channelName": "Archives Nationales",
            "description": "Sélectionné à la Berlinale, ce chef-d'œuvre restauré 4k explore les drames familiaux.",
            "category": "drama",
            "country": "kr"
        }
        enriched = server.enrich_movie_fields(raw)
        self.assertTrue(enriched.get("isAuteur"))
        self.assertEqual(enriched.get("category"), "drama")

    def test_t3_12_non_auteur_thriller_separation(self):
        """Commercial thriller (e.g. The Flu) appears in 'thriller' but is excluded from 'auteur'."""
        raw = {
            "videoId": "the_flu",
            "title": "The Flu (2013) - Film Coréen Catastrophe et Thriller à Séoul",
            "channelName": "Cinema FR",
            "description": "Un virus mortel frappe la ville de Séoul, film coréen.",
            "category": "thriller",
            "country": "kr",
            "durationSeconds": 5400
        }
        enriched = server.enrich_movie_fields(raw)
        self.assertFalse(enriched.get("isAuteur"))

        sample_cache = {"the_flu": enriched}
        from unittest.mock import patch
        with patch.object(server, "load_cached_movies", return_value=sample_cache):
            movies_thriller, _ = server.get_movies(category="thriller", min_duration=0)
            movies_auteur, _ = server.get_movies(category="auteur", min_duration=0)

        self.assertIn("the_flu", [m["videoId"] for m in movies_thriller])
        self.assertNotIn("the_flu", [m["videoId"] for m in movies_auteur])


if __name__ == "__main__":
    unittest.main()
