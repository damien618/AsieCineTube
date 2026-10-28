#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AsieCinéTube — Automated Catalog & System Validation Script (R4).

Validates that:
1. Python backend files (server.py, updater.py, validate_catalog.py) compile cleanly.
2. Datasets (movies.json, cache_movies.json) exist, are valid JSON, and meet integrity criteria.
3. ZERO movies from excluded channels (SAMURAI VS NINJA, Martial Arts Theater,
   iQIYI Action, Chinese Online Movie Channel, Ciné Nanar, short-dramas, etc.)
   exist in movies.json or cache_movies.json.
4. Auteur classics and heritage collections are preserved and enriched:
   - KOFA >= 140 movies, all with isAuteur=True and valid auteurLabel.
   - Sooner >= 50 movies, all with isAuteur=True and valid auteurLabel.
   - Major masters (Akira Kurosawa, Yasujirō Ozu, Masaki Kobayashi,
     Hong Sang-soo, Bong Joon-ho, etc.) are present and properly labeled.
   - Total auteur catalog count >= 200 movies.
5. Catalog in movies.json is strictly sorted descending by publishedTimestamp.
6. Frontend files (index.html, app.js, styles.css) include all required UI elements:
   - "🎬 Cinéma d'Auteur & Grands Maîtres" navigation chip (data-category="auteur").
   - Renamed "🔪 Polar & Thriller" chip.
   - Director-enriched search input placeholder.
   - Card badge (.movie-auteur-badge) and modal badge (.badge-auteur).
   - Amber/gold CSS styling rules and custom properties.
7. Backend filtering and enrichment contracts (server.py) function accurately.
8. Harvester query hygiene (updater.py) has zero B-movie queries and targeted auteur searches.

Usage:
    python3 validate_catalog.py
"""

import json
import os
import py_compile
import sys
from typing import Any, Dict, List, Tuple

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import server
import updater


class ValidationFailure(Exception):
    """Raised when a catalog or system validation assertion fails."""
    pass


class CatalogValidator:
    """Automated validator for AsieCinéTube catalog and codebase."""

    def __init__(self, base_dir: str = BASE_DIR):
        self.base_dir = base_dir
        self.diagnostics: List[str] = []
        self.failures: List[str] = []
        self.passed_checks = 0
        self.total_checks = 0

    def _record(self, title: str, success: bool, details: str = ""):
        self.total_checks += 1
        if success:
            self.passed_checks += 1
            status = "PASS"
            msg = f"  [{status}] {title}"
            if details:
                msg += f" — {details}"
            self.diagnostics.append(msg)
            print(msg)
        else:
            status = "FAIL"
            msg = f"  [{status}] {title}"
            if details:
                msg += f" — ERROR: {details}"
            self.diagnostics.append(msg)
            print(msg)
            self.failures.append(f"{title}: {details}")

    def load_movies_json(self) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        path = os.path.join(self.base_dir, "movies.json")
        if not os.path.exists(path):
            raise ValidationFailure(f"movies.json not found at {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        movie_list = data.get("movies", []) if isinstance(data, dict) else data
        return data if isinstance(data, dict) else {}, movie_list

    def load_cache_movies_json(self) -> Dict[str, Dict[str, Any]]:
        path = os.path.join(self.base_dir, "cache_movies.json")
        if not os.path.exists(path):
            raise ValidationFailure(f"cache_movies.json not found at {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return {m.get("videoId", str(i)): m for i, m in enumerate(data)}
        return data

    # -------------------------------------------------------------------------
    # Check 1: Python Module Compilation
    # -------------------------------------------------------------------------
    def check_compilation(self) -> bool:
        print("\n[Check 1/8] Python Module Compilation")
        modules = ["server.py", "updater.py", "validate_catalog.py"]
        all_passed = True
        for mod in modules:
            mod_path = os.path.join(self.base_dir, mod)
            try:
                py_compile.compile(mod_path, doraise=True)
                self._record(f"Compile {mod}", True, f"Clean bytecode generated from {mod_path}")
            except Exception as e:
                all_passed = False
                self._record(f"Compile {mod}", False, str(e))
        return all_passed

    # -------------------------------------------------------------------------
    # Check 2: Dataset Integrity & JSON Structure
    # -------------------------------------------------------------------------
    def check_datasets_structure(self) -> bool:
        print("\n[Check 2/8] Dataset Integrity & Structure")
        all_passed = True

        # movies.json
        try:
            raw_dict, movies = self.load_movies_json()
            is_valid = len(movies) >= 200
            self._record(
                "movies.json structure",
                is_valid,
                f"Loaded {len(movies)} movies (status='{raw_dict.get('status')}', sort='{raw_dict.get('sort')}')"
            )
            if not is_valid:
                all_passed = False

            meta_match = raw_dict.get("total") == len(movies)
            self._record(
                "movies.json count consistency",
                meta_match,
                f"total field ({raw_dict.get('total')}) matches movie count ({len(movies)})"
            )
            if not meta_match:
                all_passed = False
        except Exception as e:
            all_passed = False
            self._record("movies.json load", False, str(e))

        # cache_movies.json
        try:
            cache = self.load_cache_movies_json()
            is_valid_cache = len(cache) >= 200
            self._record(
                "cache_movies.json structure",
                is_valid_cache,
                f"Loaded {len(cache)} cached items"
            )
            if not is_valid_cache:
                all_passed = False
        except Exception as e:
            all_passed = False
            self._record("cache_movies.json load", False, str(e))

        return all_passed

    # -------------------------------------------------------------------------
    # Check 3: Zero Excluded Channels & B-Movies in Datasets
    # -------------------------------------------------------------------------
    def check_excluded_channels(self) -> bool:
        print("\n[Check 3/8] Exclusion Verification (0 Banned Channels & B-Movies)")
        all_passed = True
        _, movies = self.load_movies_json()
        cache = self.load_cache_movies_json()
        cache_items = list(cache.values())

        # Specific mandated channels from requirements
        mandatory_excluded_names = [
            "samurai vs ninja",
            "martial arts theater",
            "iqiyi action",
            "chinese online movie channel",
            "ciné nanar",
            "cine nanar",
        ]

        # Scan movies.json
        violations_movies: List[Dict[str, str]] = []
        for m in movies:
            chn = (m.get("channelName") or "").strip().lower()
            title = (m.get("title") or "").strip().lower()
            desc = (m.get("description") or "").strip().lower()

            for exc in server.EXCLUDED_CHANNELS:
                if exc in chn:
                    violations_movies.append({"videoId": m.get("videoId"), "channel": chn, "rule": exc})
                    break

            # Short-drama spam markers
            for spam in ["숏드라마", "短剧", "160분요약"]:
                if spam in title or spam in desc:
                    violations_movies.append({"videoId": m.get("videoId"), "title": title, "rule": f"spam:{spam}"})
                    break

        zero_banned_movies = len(violations_movies) == 0
        self._record(
            "movies.json excluded channels = 0",
            zero_banned_movies,
            f"Found {len(violations_movies)} violations in {len(movies)} public movies"
        )
        if not zero_banned_movies:
            all_passed = False
            for v in violations_movies[:5]:
                print(f"      Violation: {v}")

        # Scan cache_movies.json
        violations_cache: List[Dict[str, str]] = []
        for m in cache_items:
            chn = (m.get("channelName") or "").strip().lower()
            title = (m.get("title") or "").strip().lower()
            desc = (m.get("description") or "").strip().lower()

            for exc in server.EXCLUDED_CHANNELS:
                if exc in chn:
                    violations_cache.append({"videoId": m.get("videoId"), "channel": chn, "rule": exc})
                    break

            for spam in ["숏드라마", "短剧", "160분요약"]:
                if spam in title or spam in desc:
                    violations_cache.append({"videoId": m.get("videoId"), "title": title, "rule": f"spam:{spam}"})
                    break

        zero_banned_cache = len(violations_cache) == 0
        self._record(
            "cache_movies.json excluded channels = 0",
            zero_banned_cache,
            f"Found {len(violations_cache)} violations in {len(cache_items)} cache items"
        )
        if not zero_banned_cache:
            all_passed = False
            for v in violations_cache[:5]:
                print(f"      Violation: {v}")

        # Specifically verify mandatory named channels
        for ch_name in mandatory_excluded_names:
            found_m = [m for m in movies if ch_name in (m.get("channelName") or "").lower()]
            found_c = [m for m in cache_items if ch_name in (m.get("channelName") or "").lower()]
            clean = len(found_m) == 0 and len(found_c) == 0
            self._record(
                f"Absence of '{ch_name}'",
                clean,
                f"movies.json: {len(found_m)}, cache: {len(found_c)}"
            )
            if not clean:
                all_passed = False

        return all_passed

    # -------------------------------------------------------------------------
    # Check 4: Auteur Classics & Heritage Preservation
    # -------------------------------------------------------------------------
    def check_auteur_classics(self) -> bool:
        print("\n[Check 4/8] Auteur Classics & Heritage Preservation")
        all_passed = True
        _, movies = self.load_movies_json()

        # KOFA verification (>= 140)
        kofa_movies = [
            m for m in movies
            if "koreanfilm" in (m.get("channelName") or "").lower()
            or "KoreanFilm" in (m.get("channelUrl") or "")
            or m.get("category") == "kofa"
        ]
        kofa_count_ok = len(kofa_movies) >= 140
        self._record(
            "KOFA archive preservation (>= 140)",
            kofa_count_ok,
            f"Found {len(kofa_movies)} KOFA films preserved"
        )
        if not kofa_count_ok:
            all_passed = False

        kofa_enriched_ok = all(
            m.get("isAuteur") is True and bool(m.get("auteurLabel"))
            for m in kofa_movies
        )
        self._record(
            "KOFA auteur metadata enrichment",
            kofa_enriched_ok,
            f"100% of {len(kofa_movies)} KOFA films have isAuteur=True and non-empty auteurLabel"
        )
        if not kofa_enriched_ok:
            all_passed = False

        # Sooner verification (>= 50)
        sooner_movies = [
            m for m in movies
            if bool(m.get("isPaid"))
            or "sooner" in (m.get("channelName") or "").lower()
            or "@soonerfrance" in (m.get("channelUrl") or "").lower()
        ]
        sooner_count_ok = len(sooner_movies) >= 50
        self._record(
            "Sooner collection preservation (>= 50)",
            sooner_count_ok,
            f"Found {len(sooner_movies)} Sooner films preserved"
        )
        if not sooner_count_ok:
            all_passed = False

        sooner_enriched_ok = all(
            m.get("isAuteur") is True and bool(m.get("auteurLabel"))
            for m in sooner_movies
        )
        self._record(
            "Sooner auteur metadata enrichment",
            sooner_enriched_ok,
            f"100% of {len(sooner_movies)} Sooner films have isAuteur=True and non-empty auteurLabel"
        )
        if not sooner_enriched_ok:
            all_passed = False

        # Major masters presence
        masters_to_check = {
            "Akira Kurosawa": {"min": 4, "query": "kurosawa"},
            "Yasujirō Ozu": {"min": 1, "query": "ozu"},
            "Masaki Kobayashi": {"min": 1, "query": "kobayashi"},
            "Hong Sang-soo": {"min": 1, "query": "hong sang-soo"},
            "Bong Joon-ho": {"min": 1, "query": "bong joon-ho"},
            "Im Kwon-taek": {"min": 10, "query": "im kwon-taek"},
            "Shin Sang-ok": {"min": 5, "query": "shin sang-ok"},
            "Lee Man-hee": {"min": 5, "query": "lee man-hee"},
        }

        for master_name, spec in masters_to_check.items():
            q = spec["query"]
            matching = [
                m for m in movies
                if q in (m.get("title", "") + " " + m.get("description", "") + " " + str(m.get("auteurLabel", ""))).lower()
                and m.get("isAuteur") is True
            ]
            count_ok = len(matching) >= spec["min"]
            self._record(
                f"Master presence: {master_name} (>={spec['min']})",
                count_ok,
                f"Found {len(matching)} films (all with isAuteur=True)"
            )
            if not count_ok:
                all_passed = False

        # Total auteur count in catalog
        total_auteur = [m for m in movies if m.get("isAuteur") is True]
        total_auteur_ok = len(total_auteur) >= 200
        self._record(
            "Total auteur catalog density (>= 200)",
            total_auteur_ok,
            f"Found {len(total_auteur)} auteur films ({len(total_auteur)/len(movies)*100:.1f}% of catalog)"
        )
        if not total_auteur_ok:
            all_passed = False

        return all_passed

    # -------------------------------------------------------------------------
    # Check 5: Catalog Sort Order on Static Export
    # -------------------------------------------------------------------------
    def check_chronological_sort_order(self) -> bool:
        print("\n[Check 5/8] Chronological Sort Order (Static Export)")
        all_passed = True
        raw_dict, movies = self.load_movies_json()

        # Check sort field in root metadata
        sort_val = raw_dict.get("sort")
        sort_field_ok = sort_val in ("publishDate_desc", "desc")
        self._record(
            "movies.json sort metadata",
            sort_field_ok,
            f"sort='{sort_val}'"
        )
        if not sort_field_ok:
            all_passed = False

        # Check descending publishedTimestamp across entire array
        timestamps = [m.get("publishedTimestamp") or 0 for m in movies]
        is_strictly_desc = True
        first_mismatch = None

        for i in range(len(timestamps) - 1):
            if timestamps[i] < timestamps[i + 1]:
                is_strictly_desc = False
                first_mismatch = (i, timestamps[i], timestamps[i + 1], movies[i].get("title"), movies[i + 1].get("title"))
                break

        if is_strictly_desc:
            self._record(
                "Descending date order verification",
                True,
                f"All {len(timestamps)} movies ordered strictly from newest to oldest"
            )
        else:
            all_passed = False
            self._record(
                "Descending date order verification",
                False,
                f"Inversion at index {first_mismatch[0]}: {first_mismatch[1]} < {first_mismatch[2]} ('{first_mismatch[3]}' before '{first_mismatch[4]}')"
            )

        return all_passed

    # -------------------------------------------------------------------------
    # Check 6: Frontend UI Integration (index.html, app.js, styles.css)
    # -------------------------------------------------------------------------
    def check_frontend_ui_integration(self) -> bool:
        print("\n[Check 6/8] Frontend UI Integration (index.html, app.js, styles.css)")
        all_passed = True

        # 1. index.html
        html_path = os.path.join(self.base_dir, "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()

        html_checks = [
            ("Auteur chip button tag", 'data-category="auteur"' in html),
            ("Auteur chip title/label", "🎬 Cinéma d'Auteur & Grands Maîtres" in html),
            ("Renamed Polar & Thriller chip", "🔪 Polar & Thriller" in html),
            ("Director search placeholder", "Rechercher un film, un réalisateur" in html),
            ("Modal auteur badge element", 'id="modalAuteurBadge"' in html or 'badge-auteur' in html),
        ]
        for name, ok in html_checks:
            self._record(f"index.html: {name}", ok)
            if not ok:
                all_passed = False

        # 2. app.js
        js_path = os.path.join(self.base_dir, "app.js")
        with open(js_path, "r", encoding="utf-8") as f:
            js = f.read()

        js_checks = [
            ("Auteur category handling", "category === 'auteur'" in js),
            ("Card auteur badge class", "movie-auteur-badge" in js),
            ("Modal auteur badge assignment", "modalAuteurBadge" in js),
            ("Auteur label property usage", "movie.auteurLabel" in js),
            ("Status bar text for auteur", "🎬 Cinéma d'Auteur" in js),
        ]
        for name, ok in js_checks:
            self._record(f"app.js: {name}", ok)
            if not ok:
                all_passed = False

        # 3. styles.css
        css_path = os.path.join(self.base_dir, "styles.css")
        with open(css_path, "r", encoding="utf-8") as f:
            css = f.read()

        css_checks = [
            ("CSS class .chip-auteur", ".chip-auteur" in css or ".chip.chip-auteur" in css),
            ("CSS class .movie-auteur-badge", ".movie-auteur-badge" in css),
            ("CSS class .badge-auteur", ".badge-auteur" in css),
            ("CSS var --badge-auteur-bg", "--badge-auteur-bg" in css),
            ("CSS var --badge-auteur-text", "--badge-auteur-text" in css),
            ("CSS var --badge-auteur-border", "--badge-auteur-border" in css),
        ]
        for name, ok in css_checks:
            self._record(f"styles.css: {name}", ok)
            if not ok:
                all_passed = False

        return all_passed

    # -------------------------------------------------------------------------
    # Check 7: Backend Filter Engine & API Contracts (server.py)
    # -------------------------------------------------------------------------
    def check_backend_filter_engine(self) -> bool:
        print("\n[Check 7/8] Backend Filter Engine & API Contracts")
        all_passed = True

        # Test rejection of excluded channels
        for bad_ch in ["SAMURAI VS NINJA", "Ciné Nanar", "iQIYI Action", "Chinese Online Movie Channel"]:
            res = server.is_strictly_asian_movie("Action Film", bad_ch, "Full movie")
            self._record(f"Filter rejects '{bad_ch}'", not res, "Correctly rejected")
            if res:
                all_passed = False

        # Test rejection of generic martial arts B-movie
        b_res = server.is_strictly_asian_movie(
            "Ninja Assassin Drunken Kung Fu", "RandomChannel", "Shaolin wuxia sword fight"
        )
        self._record("Filter rejects generic ninja/kung-fu B-movie", not b_res, "Correctly rejected")
        if b_res:
            all_passed = False

        # Test exemption preservation for KOFA
        kofa_res = server.is_strictly_asian_movie(
            "Sword of the Martial Master", "Korean Classic Film", "Classic film archive", "https://youtube.com/@KoreanFilm"
        )
        self._record("Filter preserves KOFA despite sword terms", kofa_res, "Correctly exempted")
        if not kofa_res:
            all_passed = False

        # Test exemption preservation for Sooner
        sooner_res = server.is_strictly_asian_movie(
            "Martial Legend", "SOONER (@soonerfrance)", "Cinéma d'art et essai", "https://youtube.com/@soonerfrance"
        )
        self._record("Filter preserves Sooner despite martial terms", sooner_res, "Correctly exempted")
        if not sooner_res:
            all_passed = False

        # Test exemption preservation for Grand Masters
        kuro_res = server.is_strictly_asian_movie(
            "Seven Samurai Akira Kurosawa", "Cinema Classics", "Legendary masterpiece"
        )
        self._record("Filter preserves Akira Kurosawa master film", kuro_res, "Correctly exempted")
        if not kuro_res:
            all_passed = False

        # Test enrichment
        enriched = server.enrich_movie_fields({
            "videoId": "test_kuro",
            "title": "Seven Samurai - Akira Kurosawa",
            "channelName": "Toho Cinema",
            "description": "Masterpiece directed by Akira Kurosawa"
        })
        is_aut = enriched.get("isAuteur") is True
        has_lbl = bool(enriched.get("auteurLabel"))
        self._record("Enrichment adds isAuteur=True and auteurLabel", is_aut and has_lbl, f"label='{enriched.get('auteurLabel')}'")
        if not (is_aut and has_lbl):
            all_passed = False

        return all_passed

    # -------------------------------------------------------------------------
    # Check 8: Harvester Query Hygiene & Cache Purge (updater.py)
    # -------------------------------------------------------------------------
    def check_harvester_hygiene(self) -> bool:
        print("\n[Check 8/8] Harvester Query Hygiene & Cache Purge (updater.py)")
        all_passed = True

        queries = [q[0] if isinstance(q, tuple) else q for q in updater.SEARCH_QUERIES]
        queries_text = " ".join(queries).lower()

        # Ensure no banned B-movie queries
        banned_terms = ["film samourai", "film kung fu", "film arts martiaux", "film wuxia"]
        clean_queries = True
        for b in banned_terms:
            if b in queries_text:
                clean_queries = False
                self._record(f"Harvester query hygiene: absence of '{b}'", False, "Found banned query")
                all_passed = False
            else:
                self._record(f"Harvester query hygiene: absence of '{b}'", True, "Clean")

        # Verify presence of dedicated auteur queries
        has_kr_auteur = any("vostfr" in q.lower() and "coréen" in q.lower() for q in queries)
        has_jp_auteur = any("vostfr" in q.lower() and ("japonais" in q.lower() or "kurosawa" in q.lower()) for q in queries)
        has_cn_auteur = any("vostfr" in q.lower() and ("chinois" in q.lower() or "wong kar wai" in q.lower()) for q in queries)

        self._record("Harvester targeted Korean auteur queries", has_kr_auteur)
        self._record("Harvester targeted Japanese auteur queries", has_jp_auteur)
        self._record("Harvester targeted Chinese/Taiwanese auteur queries", has_cn_auteur)

        if not (has_kr_auteur and has_jp_auteur and has_cn_auteur):
            all_passed = False

        return all_passed

    # -------------------------------------------------------------------------
    # Run All Checks & Produce Report
    # -------------------------------------------------------------------------
    def run_all(self) -> bool:
        print("=" * 80)
        print("  🎬 AsieCinéTube FR — Automated Catalog & System Validation (R4)")
        print("=" * 80)

        checks = [
            ("Compilation", self.check_compilation),
            ("Datasets Structure", self.check_datasets_structure),
            ("Zero Excluded Channels", self.check_excluded_channels),
            ("Auteur Classics Preservation", self.check_auteur_classics),
            ("Chronological Sort Order", self.check_chronological_sort_order),
            ("Frontend UI Integration", self.check_frontend_ui_integration),
            ("Backend Filter Engine", self.check_backend_filter_engine),
            ("Harvester Query Hygiene", self.check_harvester_hygiene),
        ]

        overall_ok = True
        for name, fn in checks:
            try:
                res = fn()
                if not res:
                    overall_ok = False
            except Exception as e:
                overall_ok = False
                self._record(f"Exception during {name}", False, str(e))

        print("\n" + "=" * 80)
        print(f"Validation Summary: {self.passed_checks} / {self.total_checks} assertions passed.")
        if self.failures:
            print(f"🔴 {len(self.failures)} FAILURE(S) DETECTED:")
            for f in self.failures:
                print(f"   • {f}")
            print("=" * 80 + "\n")
            return False
        else:
            print("🟢 All assertions PASSED! Catalog, backend, harvester, and UI are fully compliant.")
            print("=" * 80 + "\n")
            return True


def validate_catalog() -> bool:
    """Entry point for programmatic catalog validation."""
    validator = CatalogValidator()
    return validator.run_all()


def main():
    validator = CatalogValidator()
    success = validator.run_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
