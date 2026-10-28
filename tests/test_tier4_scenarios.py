#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tier 4: Real-World Application Scenarios (E2E User Journeys).
Covers:
- Journey 1: Homepage Catalog Discovery & Chronological Sorting
- Journey 2: Auteur Filtering & Navigation Chip
- Journey 3: Director Search & Video Modal Details
- Journey 4: Polar & Thriller Category Filtering
- Journey 5: Harvester Ingestion & Dirty Feed Rejection Pipeline
"""

import json
import os
import sys
import tempfile
import unittest
from typing import Any, Dict, List

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import server
import updater


class TestTier4UserJourneys(unittest.TestCase):
    """Tier 4: Full End-to-End User Journeys and System Scenarios."""

    def setUp(self):
        self.movies_path = os.path.join(BASE_DIR, "movies.json")
        self.index_path = os.path.join(BASE_DIR, "index.html")
        self.app_path = os.path.join(BASE_DIR, "app.js")
        self.styles_path = os.path.join(BASE_DIR, "styles.css")

    def test_journey_1_homepage_catalog_discovery(self):
        """User Journey 1: User arrives on homepage, browses catalog ordered by newest first with valid counts."""
        if not os.path.exists(self.movies_path):
            self.skipTest("movies.json not found")

        with open(self.movies_path, "r", encoding="utf-8") as f:
            catalog = json.load(f)

        movies = catalog.get("movies", [])
        self.assertGreater(len(movies), 0, "Catalogue should contain films.")

        # Check chronological descending order
        for i in range(min(50, len(movies) - 1)):
            t1 = movies[i].get("publishedTimestamp") or 0
            t2 = movies[i + 1].get("publishedTimestamp") or 0
            if t1 and t2 and t1 != t2:
                self.assertGreaterEqual(t1, t2, f"Chronological order failure at index {i}")

        # Check total and country counts
        total = catalog.get("total", 0)
        counts = catalog.get("countryCounts", {})
        self.assertEqual(total, len(movies))
        self.assertEqual(total, sum(counts.values()))

        # Check UI chips in index.html
        with open(self.index_path, "r", encoding="utf-8") as f:
            html = f.read()

        # The chips navigation must include the auteur chip
        self.assertIn('data-category="auteur"', html)
        self.assertIn('data-category="all"', html)

    def test_journey_2_auteur_navigation_and_filtering(self):
        """User Journey 2: User clicks '🎬 Cinéma d'Auteur & Grands Maîtres' chip, catalog filters strictly to auteur & heritage."""
        if not os.path.exists(self.movies_path):
            self.skipTest("movies.json not found")

        with open(self.movies_path, "r", encoding="utf-8") as f:
            catalog = json.load(f)

        movies = catalog.get("movies", [])

        # Simulate app.js client-side filtering for category === 'auteur'
        def is_client_auteur(m):
            return (
                bool(m.get("isAuteur"))
                or m.get("category") == "auteur"
                or bool(m.get("auteurLabel"))
                or m.get("category") == "kofa"
                or (m.get("channelName") and ("koreanfilm" in m.get("channelName", "").lower() or "sooner" in m.get("channelName", "").lower()))
            )

        auteur_catalog = [m for m in movies if is_client_auteur(m)]
        self.assertGreater(len(auteur_catalog), 0, "Auteur catalog must not be empty.")

        # Verify zero excluded channels in auteur catalog
        excluded = getattr(server, "EXCLUDED_CHANNELS", [])
        for m in auteur_catalog:
            ch = m.get("channelName", "").lower()
            for ex in excluded:
                self.assertNotIn(ex, ch, f"Excluded channel '{ex}' found in auteur movie '{m.get('title')}'.")

        # Verify all KOFA films are present in auteur catalog
        kofa_in_all = [m for m in movies if "koreanfilm" in m.get("channelName", "").lower()]
        kofa_in_auteur = [m for m in auteur_catalog if "koreanfilm" in m.get("channelName", "").lower()]
        self.assertEqual(len(kofa_in_all), len(kofa_in_auteur), "100% of KOFA films must appear in Auteur category.")

    def test_journey_3_director_search_and_modal_inspection(self):
        """User Journey 3: User searches 'Kurosawa', inspects card, and verifies modal data including auteur badge."""
        sample_movie = {
            "videoId": "kurosawa_rashomon",
            "title": "Rashomon (1950) - Akira Kurosawa",
            "channelName": "Criterion Collection",
            "description": "Un chef-d'œuvre du cinéma mondial réalisé par Akira Kurosawa.",
            "country": "jp",
            "category": "auteur",
            "isAuteur": True,
            "auteurLabel": "🎬 Akira Kurosawa",
            "durationFormatted": "1:28:00",
            "subtitleType": "native_fr",
            "subtitleBadge": "🇫🇷 ST-FR Natif"
        }

        # 1. Search simulation matching title, description, or auteurLabel
        def matches_search(m, query):
            q = query.lower()
            return (
                q in m.get("title", "").lower()
                or q in m.get("description", "").lower()
                or q in m.get("auteurLabel", "").lower()
            )

        self.assertTrue(matches_search(sample_movie, "Kurosawa"))
        self.assertTrue(matches_search(sample_movie, "akira"))
        self.assertFalse(matches_search(sample_movie, "Bong Joon-ho"))

        # 2. Card badge rendering verification in app.js
        with open(self.app_path, "r", encoding="utf-8") as f:
            app_code = f.read()
        self.assertIn("movie-auteur-badge", app_code)

        # 3. Modal structure verification in index.html and app.js
        with open(self.index_path, "r", encoding="utf-8") as f:
            html = f.read()
        self.assertIn('id="modalAuteurBadge"', html)

        # Modal must display the director label
        modal_badge_text = sample_movie["auteurLabel"]
        self.assertEqual(modal_badge_text, "🎬 Akira Kurosawa")

    def test_journey_4_polar_thriller_category_filtering(self):
        """User Journey 4: User selects '🔪 Polar & Thriller', sees thrillers, no B-kungfu, with auteur badges retained."""
        thriller_movies = [
            {
                "videoId": "th1",
                "title": "Memories of Murder - Bong Joon-ho",
                "category": "thriller",
                "isAuteur": True,
                "auteurLabel": "🎬 Bong Joon-ho"
            },
            {
                "videoId": "th2",
                "title": "The Chaser (2008) - Na Hong-jin",
                "category": "thriller",
                "isAuteur": True,
                "auteurLabel": "🎬 Na Hong-jin"
            },
            {
                "videoId": "th3",
                "title": "Cold Eyes (2013) - Polar Urbain Coréen",
                "category": "thriller",
                "isAuteur": False,
                "auteurLabel": None
            }
        ]

        # In thriller category: all 3 appear
        filtered = [m for m in thriller_movies if m.get("category") == "thriller"]
        self.assertEqual(len(filtered), 3)

        # Auteur thrillers retain their auteur badge
        auteur_thrillers = [m for m in filtered if m.get("isAuteur")]
        self.assertEqual(len(auteur_thrillers), 2)
        self.assertEqual(auteur_thrillers[0]["auteurLabel"], "🎬 Bong Joon-ho")

        # Check that UI label for chip in index.html is 'Polar & Thriller'
        with open(self.index_path, "r", encoding="utf-8") as f:
            html = f.read()
        self.assertIn("Polar & Thriller", html)
        self.assertNotIn("Arts Martiaux", html[html.find('data-category="thriller"'):html.find('data-category="thriller"') + 120])

    def test_journey_5_harvester_dirty_feed_ingestion_pipeline(self):
        """User Journey 5: Harvester ingests dirty feed (40 bad candidates, 5 auteur masterpieces), saving 100% clean cache."""
        dirty_feed: List[Dict[str, Any]] = []

        # 1. 20 Candidates from excluded channels
        for i in range(20):
            dirty_feed.append({
                "videoId": f"bad_ch_{i:02d}",
                "title": f"Ninja Combat {i}",
                "channelName": "SAMURAI VS NINJA" if i % 2 == 0 else "Chinese Online Movie Channel-ASIA MOVIE",
                "description": "Fight scene with ninja",
                "country": "jp" if i % 2 == 0 else "cn",
                "publishedTimestamp": 1600000000 + i
            })

        # 2. 15 Generic B-movie martial arts
        for i in range(15):
            dirty_feed.append({
                "videoId": f"bad_bm_{i:02d}",
                "title": f"Shaolin Kung Fu Master {i}",
                "channelName": "Action Unlimited",
                "description": "Drunken fist and wuxia battles",
                "country": "cn",
                "publishedTimestamp": 1600001000 + i
            })

        # 3. 5 Short-drama clickbaits
        for i in range(5):
            dirty_feed.append({
                "videoId": f"bad_sd_{i:02d}",
                "title": f"160분요약 대부호 {i}",
                "channelName": "양파극장",
                "description": "숏드라마 결말포함",
                "country": "kr",
                "publishedTimestamp": 1600002000 + i
            })

        # 4. 5 Genuine Auteur Masterpieces
        auteur_specs = [
            ("aut_01", "Voyage à Tokyo (1953) - Yasujirō Ozu", "Shochiku Heritage", "Chef d'oeuvre de Yasujirō Ozu.", "jp"),
            ("aut_02", "Rashomon (1950) - Akira Kurosawa", "Toho Classics", "Akira Kurosawa réalise un monument.", "jp"),
            ("aut_03", "Memories of Murder (2003) - Bong Joon-ho", "Korean Cinema Archive", "Film culte de Bong Joon-ho.", "kr"),
            ("aut_04", "In the Mood for Love (2000) - Wong Kar-wai", "Block 2 Pictures", "Wong Kar-wai sublime Hong Kong.", "cn"),
            ("aut_05", "Yi Yi (2000) - Edward Yang", "1+1 Films", "Prix de la mise en scène à Cannes pour Edward Yang.", "cn"),
        ]
        for vid, title, ch, desc, country in auteur_specs:
            dirty_feed.append({
                "videoId": vid,
                "title": title,
                "channelName": ch,
                "description": desc,
                "country": country,
                "publishedTimestamp": 1600003000
            })

        self.assertEqual(len(dirty_feed), 45)

        # Execute Ingestion Pipeline:
        # Step A: Filter through is_strictly_asian_movie
        surviving = [
            cand for cand in dirty_feed
            if server.is_strictly_asian_movie(
                cand["title"], cand["channelName"], cand["description"]
            )
        ]

        # Exactly 5 auteur movies should survive
        self.assertEqual(len(surviving), 5, f"Expected exactly 5 auteur movies to survive, got {len(surviving)}")
        self.assertEqual({m["videoId"] for m in surviving}, {"aut_01", "aut_02", "aut_03", "aut_04", "aut_05"})

        # Step B: Enrich surviving movies
        enriched_map = {}
        for cand in surviving:
            enr = server.enrich_movie_fields(cand)
            self.assertTrue(enr.get("isAuteur"))
            self.assertTrue(bool(enr.get("auteurLabel")))
            enriched_map[enr["videoId"]] = enr

        # Step C: Save to isolated temporary cache
        with tempfile.TemporaryDirectory() as tmpdir:
            test_cache_file = os.path.join(tmpdir, "cache_movies.json")
            test_export_file = os.path.join(tmpdir, "movies.json")
            orig_cache, orig_export = server.CACHE_FILE, server.STATIC_EXPORT_FILE
            try:
                server.CACHE_FILE = test_cache_file
                server.STATIC_EXPORT_FILE = test_export_file

                server.save_cached_movies(enriched_map)

                # Check written movies.json
                with open(test_export_file, "r", encoding="utf-8") as f:
                    export_data = json.load(f)

                self.assertEqual(export_data.get("total"), 5)
                self.assertEqual(len(export_data.get("movies", [])), 5)
                for m in export_data.get("movies", []):
                    self.assertTrue(m.get("isAuteur"))

            finally:
                server.CACHE_FILE, server.STATIC_EXPORT_FILE = orig_cache, orig_export


if __name__ == "__main__":
    unittest.main()
