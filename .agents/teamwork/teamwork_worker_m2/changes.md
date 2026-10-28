# Changes Implemented for Milestone 2 — Harvester & Catalog Purge

**Agent ID**: `teamwork_worker_m2`  
**Date**: 2026-10-28  
**Scope**: `updater.py`, `cache_movies.json`, `movies.json`, `tests/test_tier1_features.py` (aliases)

---

## 1. Summary of Modifications

### 1.1 `updater.py`

1. **`SEARCH_QUERIES` Overhaul**:
   - Replaced the 5 obsolete generic B-movie queries (`"film samourai complet"`, `"film yakuza"`, `"film arts martiaux"`, `"film kung fu"`, `"film wuxia"`) with 26 targeted queries focused on auteur cinema, heritage classics, and masters with French subtitles / VOSTFR across South Korea, Japan, China / Taiwan / Hong Kong, and Sooner.
   - Specific masters included: Akira Kurosawa, Yasujirō Ozu, Kenji Mizoguchi, Masaki Kobayashi, Hirokazu Kore-eda, Takeshi Kitano, Wong Kar-wai, Edward Yang, Hou Hsiao-hsien, Tsai Ming-liang, Zhang Yimou, Jia Zhangke, Hong Sang-soo, Lee Chang-dong, Park Chan-wook, Bong Joon-ho, KOFA classic films, and Sooner official channel.
2. **Channel URL parameter propagation**:
   - In `search_youtube_innertube()`, updated the candidate filtering call to pass `channel_url`: `server.is_strictly_asian_movie(title, channel_name, description, channel_url)` for complete channel-based exclusion checking.
3. **In-Memory Cache Purge in `run_harvest()`**:
   - Implemented proactive filtering immediately after `server.load_cached_movies()`:
     ```python
     cache_map = {
         vid: m
         for vid, m in cache_map.items()
         if isinstance(m, dict)
         and server.is_strictly_asian_movie(
             m.get("title", ""),
             m.get("channelName", ""),
             m.get("description", ""),
             m.get("channelUrl", ""),
         )
         and "iqiyi" not in (m.get("channelName", "") or "").lower()
     }
     ```
   - Automatically purges obsolete, low-quality or non-compliant movies before candidates deduplication.
4. **Candidate Slice Enlargement**:
   - Increased enrichment slice from 30 to 60 (`new_candidates[:60]`) to accelerate discovery of auteur films without exceeding execution limits.

### 1.2 `cache_movies.json` & `movies.json`

1. **Purge Execution**:
   - Applied strict filtering and atomic synchronization across `cache_movies.json` and `movies.json`.
   - Purged 148 non-compliant entries (100% of excluded channels: SAMURAI VS NINJA, Chinese Online Movie Channel, iQIYI subchannels, Ciné Nanar, short-drama clickbaits, and unexempted B-movies).
   - Preserved 100% of heritage institutions: **147 KOFA films** (requirement >= 140) and **51 Sooner films** (requirement >= 50).
   - Total clean catalog count: 336 movies.
2. **Auteur Re-enrichment**:
   - All preserved movies re-enriched via `server.enrich_movie_fields(m)`, populating `isAuteur: True` and `auteurLabel` (e.g., `🏛️ KOFA (Patrimoine)`, `Akira Kurosawa`, etc.).
3. **Reverse Chronological Sort**:
   - Static export in `movies.json` strictly sorted by `(publishedTimestamp, publishDate, viewCount)` descending, with `"sort": "publishDate_desc"`.

### 1.3 `tests/test_tier1_features.py`

- Added compatibility aliases at module scope:
  - `TestF6YouTubeHarvesterQueries = TestF6HarvesterAuteurQueries`
  - `TestF7CatalogPurge = TestF7CompleteCatalogPurge`
  - `TestF8KofaAndSoonerPreservation = TestF8PreservationKofaAndSooner`
  - `TestF9SortByDateDescending = TestF9ChronologicalSortOrder`

---

## 2. Verification Summary

- `python3 -m py_compile updater.py`: OK (exit code 0)
- `python3 -m unittest tests.test_tier1_features.TestF6YouTubeHarvesterQueries tests.test_tier1_features.TestF7CatalogPurge tests.test_tier1_features.TestF8KofaAndSoonerPreservation tests.test_tier1_features.TestF9SortByDateDescending`: 20/20 tests passing (exit code 0).
- Purity check script: 0 excluded channels in `movies.json` and `cache_movies.json`.
- Preservation script: KOFA 147 films, Sooner 51 films.
- Full test suite: 165/165 tests passing.
