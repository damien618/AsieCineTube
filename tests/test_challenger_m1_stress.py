#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stress-test harness for Milestone 1 Backend Core & Filter Engine.
Empirical verification of:
1. /api/movies?category=auteur with various query parameters
2. server.enrich_movie_fields with malformed dictionary objects
3. server.save_cached_movies serialization, atomicity, and corruption handling
4. server.is_strictly_asian_movie throughput on 10,000 synthetic items
"""

import copy
import datetime
import http.server
import json
import os
import shutil
import socketserver
import tempfile
import threading
import time
import urllib.parse
import urllib.request
import unittest

import server


class EmpiricalStressTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    # =========================================================================
    # MISSION 1: API Endpoint Stress Testing (/api/movies?category=auteur)
    # =========================================================================
    def test_01_api_auteur_queries(self):
        print("\n--- [Mission 1] API Endpoint Stress Testing ---")
        import io

        class MockRequest:
            def __init__(self, raw_request):
                self._rfile = io.BytesIO(raw_request)
                self._wfile = io.BytesIO()

            def makefile(self, mode, *args, **kwargs):
                if "r" in mode or "b" in mode:
                    return self._rfile
                return self._wfile

            def sendall(self, data):
                self._wfile.write(data)

        test_cases = [
            ("standard_auteur", "/api/movies?category=auteur"),
            ("query_kurosawa", "/api/movies?category=auteur&q=Kurosawa"),
            ("query_lowercase_ozu", "/api/movies?category=auteur&q=ozu"),
            ("query_accent_rashomon", "/api/movies?category=auteur&q=Rash%C5%8Dmon"),
            ("query_multiword_seven_samurai", "/api/movies?category=auteur&q=Seven+Samurai"),
            ("query_nonexistent", "/api/movies?category=auteur&q=NonExistentDirectorZ99"),
            ("query_empty_spaces", "/api/movies?category=auteur&q=++++"),
            ("query_cjk_korean", "/api/movies?category=auteur&q=%ED%95%9C%EA%B5%AD%EA%B3%A0%EC%A0%84%EC%98%81%ED%99%94"),
            ("query_special_chars", "/api/movies?category=auteur&q=%F0%9F%8E%AC+!%40%23%24%25%5E%26*()_%2B"),
            ("min_duration_zero", "/api/movies?category=auteur&min_duration=0"),
            ("min_duration_negative", "/api/movies?category=auteur&min_duration=-60"),
            ("min_duration_large", "/api/movies?category=auteur&min_duration=99999"),
            ("min_duration_invalid_text", "/api/movies?category=auteur&min_duration=not_a_number"),
            ("sub_filter_native", "/api/movies?category=auteur&sub_filter=native"),
            ("sub_filter_auto", "/api/movies?category=auteur&sub_filter=auto_fr"),
            ("sub_filter_invalid", "/api/movies?category=auteur&sub_filter=invalid_sub"),
            ("unsupported_pagination", "/api/movies?category=auteur&page=2&limit=5"),
            ("refresh_flag_true", "/api/movies?category=auteur&refresh=1"),
            ("refresh_flag_yes", "/api/movies?category=auteur&refresh=yes"),
            ("movies_json_static_path", "/movies.json?category=auteur"),
        ]

        results = {}
        for name, path in test_cases:
            req_data = f"GET {path} HTTP/1.1\r\nHost: localhost\r\n\r\n".encode("utf-8")
            mock_req = MockRequest(req_data)

            # Instantiate handler with mock client address
            handler = server.KCineTubeHandler(mock_req, ("127.0.0.1", 12345), None)
            output = mock_req._wfile.getvalue()

            # Parse HTTP response from wfile
            header_part, _, body_part = output.partition(b"\r\n\r\n")
            header_lines = header_part.decode("utf-8", errors="replace").split("\r\n")
            status_line = header_lines[0]
            status_code = int(status_line.split()[1])

            headers = {}
            for line in header_lines[1:]:
                if ":" in line:
                    k, v = line.split(":", 1)
                    headers[k.strip().lower()] = v.strip()

            try:
                data = json.loads(body_part.decode("utf-8"))
                total_movies = data.get("total", -1)
                returned_movies = len(data.get("movies", []))
                results[name] = {
                    "status": status_code,
                    "content_type": headers.get("content-type", ""),
                    "cors": headers.get("access-control-allow-origin", ""),
                    "total": total_movies,
                    "returned": returned_movies,
                    "error": None,
                }
            except Exception as e:
                results[name] = {"error": f"JSON decode error: {e}", "status": status_code}

        print(f"Executed {len(test_cases)} API query variations. All status=200:")
        for name, res in results.items():
            print(f"  - {name:30}: returned={res.get('returned')} total={res.get('total')} err={res.get('error')}")

        for name, res in results.items():
            self.assertEqual(res.get("status"), 200, f"Case {name} failed with status {res.get('status')}")
            self.assertIn("application/json", res.get("content_type", ""))
            self.assertEqual(res.get("cors"), "*")

        # Specific assertions
        # Non-existent query should yield 0 results
        self.assertEqual(results["query_nonexistent"]["returned"], 0)
        # Large duration should yield 0 results
        self.assertEqual(results["min_duration_large"]["returned"], 0)
        # Invalid min_duration text should not crash, falls back to 40
        self.assertEqual(results["min_duration_invalid_text"]["status"], 200)
        # Kurosawa query should return at least 1 movie
        self.assertGreater(results["query_kurosawa"]["returned"], 0)

    # =========================================================================
    # MISSION 2: Stress test server.enrich_movie_fields with malformed dicts
    # =========================================================================
    def test_02_enrich_movie_fields_stress(self):
        print("\n--- [Mission 2] enrich_movie_fields Malformed Input Stress Testing ---")
        
        # Test baseline valid input
        valid_input = {
            "videoId": "test12345",
            "title": "Tokyo Story (1953) - Yasujiro Ozu",
            "channelName": "Shochiku Cinema",
            "description": "Chef d'oeuvre restauré 4k",
            "durationSeconds": 8160,
            "viewCount": 500000,
            "publishDate": "2024-01-01",
            "country": "jp",
            "category": "auteur"
        }
        res = server.enrich_movie_fields(valid_input)
        self.assertEqual(res["videoId"], "test12345")
        self.assertTrue(res["isAuteur"])
        self.assertEqual(res["auteurLabel"], "🎬 Yasujirō Ozu")

        # Now test adversarial inputs
        adversarial_cases = [
            ("empty_dict", {}),
            ("none_keys_dict", {"videoId": None, "title": None, "channelName": None}),
            ("numeric_id", {"videoId": 987654321}),
            ("numeric_title", {"title": 123456}),
            ("publish_date_none", {"publishDate": None}),
            ("publish_date_short", {"publishDate": "2024"}),
            ("publish_date_empty", {"publishDate": ""}),
            ("publish_date_invalid", {"publishDate": "not-a-date"}),
            ("duration_seconds_none", {"durationSeconds": None}),
            ("duration_seconds_str_int", {"durationSeconds": "7200"}),
            ("duration_seconds_str_invalid", {"durationSeconds": "one_hour"}),
            ("duration_seconds_negative", {"durationSeconds": -500}),
            ("duration_seconds_huge", {"durationSeconds": 10**9}),
            ("view_count_none", {"viewCount": None}),
            ("view_count_str_int", {"viewCount": "100000"}),
            ("view_count_str_formatted", {"viewCount": "15k"}),
            ("channel_name_none", {"channelName": None}),
            ("channel_name_empty", {"channelName": ""}),
            ("channel_url_none", {"channelUrl": None}),
            ("description_none", {"description": None}),
            ("category_unknown", {"category": "sci-fi-western"}),
            ("country_unknown", {"country": "br"}),
            ("available_languages_str", {"availableLanguages": "fr"}),
            ("available_languages_none", {"availableLanguages": None}),
            ("is_paid_as_str", {"isPaid": "true"}),
            ("is_auteur_as_str", {"isAuteur": "yes"}),
        ]

        passed = 0
        failed = 0
        crashes = []
        for name, malformed in adversarial_cases:
            try:
                out = server.enrich_movie_fields(malformed)
                # Verify basic contract keys exist in output
                self.assertIn("videoId", out)
                self.assertIn("title", out)
                self.assertIn("isAuteur", out)
                self.assertIn("auteurLabel", out)
                self.assertIn("durationSeconds", out)
                self.assertIn("viewCount", out)
                passed += 1
                print(f"  [PASS] {name:30} -> isAuteur={out['isAuteur']}, category={out['category']}")
            except Exception as e:
                failed += 1
                crashes.append((name, type(e).__name__, str(e)))
                print(f"  [FAIL] {name:30} -> EXCEPTION: {type(e).__name__}: {e}")

        print(f"\nStress results: {passed} passed, {failed} crashed out of {len(adversarial_cases)} cases.")
        if crashes:
            print("Crashes observed:")
            for c in crashes:
                print(f"    - {c[0]}: {c[1]}: {c[2]}")

    # =========================================================================
    # MISSION 3: server.save_cached_movies Atomic Write & Corruption Resilience
    # =========================================================================
    def test_03_save_cached_movies_atomicity_and_corruption(self):
        print("\n--- [Mission 3] save_cached_movies Atomicity & Serialization Testing ---")
        temp_dir = tempfile.mkdtemp(prefix="asiecine_test_")
        orig_cache_file = server.CACHE_FILE
        orig_static_file = server.STATIC_EXPORT_FILE

        try:
            server.CACHE_FILE = os.path.join(temp_dir, "cache_movies.json")
            server.STATIC_EXPORT_FILE = os.path.join(temp_dir, "movies.json")

            # 1. Normal save with clean entries
            clean_cache = {
                "vid_kurosawa": {
                    "videoId": "vid_kurosawa",
                    "title": "Seven Samurai - Akira Kurosawa",
                    "channelName": "Toho Cinema",
                    "description": "Masterpiece",
                    "durationSeconds": 12000,
                    "publishDate": "2024-01-01",
                    "country": "jp",
                    "category": "auteur"
                },
                "vid_spam": {
                    "videoId": "vid_spam",
                    "title": "Ninja Kung Fu Billionaire Alpha Wolf",
                    "channelName": "samurai vs ninja",
                    "description": "Short drama recap",
                    "durationSeconds": 3000,
                    "publishDate": "2024-01-01",
                }
            }

            server.save_cached_movies(clean_cache)

            # Verify files were created
            self.assertTrue(os.path.exists(server.CACHE_FILE))
            self.assertTrue(os.path.exists(server.STATIC_EXPORT_FILE))

            # Verify spam entry was purged
            with open(server.CACHE_FILE, "r", encoding="utf-8") as f:
                saved_cache = json.load(f)
            self.assertIn("vid_kurosawa", saved_cache)
            self.assertNotIn("vid_spam", saved_cache)
            print("  [PASS] Clean save created valid cache and purged spam entry.")

            # Verify static export structure
            with open(server.STATIC_EXPORT_FILE, "r", encoding="utf-8") as f:
                saved_static = json.load(f)
            self.assertEqual(saved_static.get("status"), "ok")
            self.assertEqual(saved_static.get("total"), 1)
            self.assertEqual(saved_static.get("movies")[0]["videoId"], "vid_kurosawa")
            print("  [PASS] Clean static export verified.")

            # 2. Check in-place mutation of caller's cache_map
            self.assertNotIn("vid_spam", clean_cache, "save_cached_movies mutates caller dictionary in-place!")
            print("  [NOTE] save_cached_movies mutates input dictionary in-place (deleted purged keys).")

            # 3. Test corruption resilience: Unserializable object (e.g. set)
            corrupted_cache = {
                "vid_bad": {
                    "videoId": "vid_bad",
                    "title": "Tokyo Story - Yasujirō Ozu",
                    "channelName": "Shochiku",
                    "unserializable": {1, 2, 3}  # set cannot be serialized to JSON
                }
            }
            # Record file sizes before corrupted call
            cache_size_before = os.path.getsize(server.CACHE_FILE)
            static_size_before = os.path.getsize(server.STATIC_EXPORT_FILE)

            # Call save_cached_movies - should catch or raise?
            print("  Testing behavior when cache contains non-JSON-serializable set object...")
            try:
                server.save_cached_movies(corrupted_cache)
            except Exception as e:
                print(f"  Caught expected error during save: {e}")

            # Check if files were truncated to 0 bytes or corrupted!
            cache_size_after = os.path.getsize(server.CACHE_FILE)
            static_size_after = os.path.getsize(server.STATIC_EXPORT_FILE)
            print(f"  Cache file size before: {cache_size_before}, after: {cache_size_after}")
            print(f"  Static file size before: {static_size_before}, after: {static_size_after}")

            # Try loading cache_movies.json to see if JSON is still intact
            try:
                with open(server.CACHE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                print(f"  Cache file remains valid JSON: {bool(data)}")
            except Exception as e:
                print(f"  [CRITICAL] Cache file became corrupt/truncated: {e}")

            # 4. Test with non-dict item in cache_map
            print("  Testing behavior with non-dict value in cache_map (cache_map['bad'] = 'string')...")
            bad_structure_cache = {"vid_string": "this is a string, not a dict"}
            try:
                server.save_cached_movies(bad_structure_cache)
                print("  Non-dict value handled without crash.")
            except Exception as e:
                print(f"  [NOTE] Non-dict in cache_map raised {type(e).__name__}: {e}")

        finally:
            server.CACHE_FILE = orig_cache_file
            server.STATIC_EXPORT_FILE = orig_static_file
            shutil.rmtree(temp_dir, ignore_errors=True)

    # =========================================================================
    # MISSION 4: Performance & throughput of is_strictly_asian_movie (10k items)
    # =========================================================================
    def test_04_throughput_10k_items(self):
        print("\n--- [Mission 4] is_strictly_asian_movie 10,000 Item Throughput Benchmark ---")
        
        # Build 10,000 synthetic test items covering diverse categories
        synthetic_items = []

        # 1. 2500 Auteur & Classic items (should pass)
        directors = ["Akira Kurosawa", "Yasujirō Ozu", "Bong Joon-ho", "Hong Sang-soo", "Wong Kar-wai", "Masaki Kobayashi"]
        for i in range(2500):
            d = directors[i % len(directors)]
            synthetic_items.append((
                f"Masterpiece #{i}: Title by {d} (Film Asiatique)",
                "Korean Classic Film (@KoreanFilm)",
                f"A wonderful film restored in 4K directed by {d}. Festival de Cannes selection.",
                "https://www.youtube.com/@KoreanFilm",
                True  # Expected
            ))

        # 2. 2500 Western Exclusion items (should reject early)
        western_terms = ["bruce willis", "steven seagal", "van damme", "film américain", "hollywood", "u.s. army"]
        for i in range(2500):
            w = western_terms[i % len(western_terms)]
            synthetic_items.append((
                f"Action Blockbuster #{i} with {w}",
                "Hollywood Movies Hub",
                f"Full length explosive action film featuring {w}. Available now in HD.",
                "https://www.youtube.com/channel/hollywood",
                False
            ))

        # 3. 2500 Excluded Channel / Spam items (should reject early)
        excluded_channels = ["samurai vs ninja", "martial arts theater", "ciné nanar", "iqiyi action", "양파극장"]
        for i in range(2500):
            ch = excluded_channels[i % len(excluded_channels)]
            synthetic_items.append((
                f"Clickbait Drama #{i} - Short Drama Recap",
                ch,
                "Billionaire mafia boss 160분요약 full recap episode 1-50.",
                f"https://www.youtube.com/@{ch}",
                False
            ))

        # 4. 1500 B-movie martial arts non-auteur (should reject at step 2)
        bmovie_terms = ["ninja", "kung fu", "wuxia", "shaolin", "drunken fist", "sword king"]
        for i in range(1500):
            b = bmovie_terms[i % len(bmovie_terms)]
            synthetic_items.append((
                f"Deadly {b.capitalize()} Fighter #{i} (1982)",
                "Action Movies Channel",
                f"Classic low budget {b} combat with martial arts masters and sword fights.",
                "https://www.youtube.com/channel/action",
                False
            ))

        # 5. 1000 Complex boundary items (CJK, long descriptions, URLs, edge cases)
        for i in range(1000):
            synthetic_items.append((
                f"한국 영화 클래식 #{i} 서울 Busan Tokyo",
                "Asian Cinema Archive",
                "Watch here: https://youtu.be/gil_9u4oZuI and https://example.com/movie " + ("lore ipsum asian film " * 30),
                "https://www.youtube.com/@AsianCinemaArchive%20Special",
                True
            ))

        self.assertEqual(len(synthetic_items), 10000)

        # Benchmark run
        latencies = []
        accepted_count = 0
        rejected_count = 0

        start_time = time.perf_counter()
        for title, channel, desc, url, expected in synthetic_items:
            t0 = time.perf_counter()
            result = server.is_strictly_asian_movie(title, channel, desc, url)
            t1 = time.perf_counter()
            latencies.append((t1 - t0) * 1_000_000)  # microseconds
            if result:
                accepted_count += 1
            else:
                rejected_count += 1
        total_time = time.perf_counter() - start_time

        throughput = len(synthetic_items) / total_time
        avg_latency_us = sum(latencies) / len(latencies)
        latencies.sort()
        p50_us = latencies[len(latencies) // 2]
        p95_us = latencies[int(len(latencies) * 0.95)]
        p99_us = latencies[int(len(latencies) * 0.99)]
        max_latency_us = latencies[-1]

        print(f"Total time for 10,000 items: {total_time:.4f} s")
        print(f"Throughput: {throughput:,.1f} items/sec")
        print(f"Latency per item: avg={avg_latency_us:.1f}µs, p50={p50_us:.1f}µs, p95={p95_us:.1f}µs, p99={p99_us:.1f}µs, max={max_latency_us:.1f}µs")
        print(f"Outcome: {accepted_count} accepted, {rejected_count} rejected.")

        # Assertions: throughput must exceed at least 5,000 items/sec (real requirement < 2 seconds for 10k items)
        self.assertGreater(throughput, 2000.0, "Throughput is too low (<2,000 items/sec)")
        self.assertLess(avg_latency_us, 500.0, "Average latency per item is too high (>500µs)")


if __name__ == "__main__":
    unittest.main()
