# Handoff Report: Milestone 1 Adversarial Verification (`server.py`)

**Agent**: `teamwork_challenger_m1_2` (Empirical Challenger)  
**Date**: 2026-10-28T17:50:00Z  
**Verdict**: `REQUEST_CHANGES`

---

## 1. Observation

Empirical testing was executed directly against `server.py` and test suites via `tests/test_challenger_m1_stress.py` and `tests/test_tier1_features.py`.

### 1.1 Test 1: `/api/movies?category=auteur` with Query Variations (Mission 1)
- **Tool Command**: `python3 -m unittest tests.test_challenger_m1_stress.EmpiricalStressTests.test_01_api_auteur_queries`
- **Result**:
  - 20 distinct query variations tested via hermetic `KCineTubeHandler` mock request.
  - All 20 returned `status: 200`, `Content-Type: application/json; charset=utf-8`, and CORS `Access-Control-Allow-Origin: *`.
  - Baseline `category=auteur`: Returned **207 auteur movies**, all with `isAuteur=True` or `category in ('auteur', 'kofa')` or Sooner channel.
  - Queries:
    - `q=Kurosawa`: 8 movies returned
    - `q=ozu`: 1 movie returned
    - `q=Rashōmon` (macron `ō`): 1 movie returned
    - `q=Seven Samurai` (multiword): 2 movies returned
    - `q=NonExistentDirectorZ99`: 0 movies returned
    - `q=    ` (whitespace): 207 movies returned safely
    - `q=한국고전영화` (CJK text): 147 movies returned
    - `q=🎬 !@#$%^&*()_+` (emojis & punctuation): 119 matches returned without regex crash or injection
    - `min_duration=0` / `min_duration=-60`: clamped safely via `max(20, min_duration)`
    - `min_duration=not_a_number`: falls back safely to 40 mins
    - `sub_filter=native`: 52 native VOSTFR auteur movies returned
    - `page=2&limit=5` (unsupported pagination): returns full 207 catalog without crashing.

### 1.2 Test 2: `server.enrich_movie_fields` Malformed Inputs (Mission 2)
- **Tool Command**: `python3 -m unittest tests.test_challenger_m1_stress.EmpiricalStressTests.test_02_enrich_movie_fields_stress`
- **Result**: **18 passed, 8 crashed** out of 26 adversarial inputs.
- **Verbatim Exceptions**:
  1. `publish_date_none`:
     ```
     File "/Users/damienferrion/Documents/AppleDevelopper/AsieCineTube/server.py", line 971, in enrich_movie_fields
       pub_date = raw.get("publishDate", "2025-01-01")[:10]
     TypeError: 'NoneType' object is not subscriptable
     ```
  2. `duration_seconds_none`:
     ```
     File "/Users/damienferrion/Documents/AppleDevelopper/AsieCineTube/server.py", line 969, in enrich_movie_fields
       dur_sec = int(raw.get("durationSeconds", 5400))
     TypeError: int() argument must be a string, a bytes-like object or a number, not 'NoneType'
     ```
  3. `duration_seconds_str_invalid` (`{"durationSeconds": "one_hour"}`):
     ```
     File "/Users/damienferrion/Documents/AppleDevelopper/AsieCineTube/server.py", line 969, in enrich_movie_fields
       dur_sec = int(raw.get("durationSeconds", 5400))
     ValueError: invalid literal for int() with base 10: 'one_hour'
     ```
  4. `view_count_none`:
     ```
     File "/Users/damienferrion/Documents/AppleDevelopper/AsieCineTube/server.py", line 970, in enrich_movie_fields
       views = int(raw.get("viewCount", 25000))
     TypeError: int() argument must be a string, a bytes-like object or a number, not 'NoneType'
     ```
  5. `view_count_str_formatted` (`{"viewCount": "15k"}`):
     ```
     File "/Users/damienferrion/Documents/AppleDevelopper/AsieCineTube/server.py", line 970, in enrich_movie_fields
       views = int(raw.get("viewCount", 25000))
     ValueError: invalid literal for int() with base 10: '15k'
     ```
  6. `channel_name_none`:
     ```
     File "/Users/damienferrion/Documents/AppleDevelopper/AsieCineTube/server.py", line 990, in enrich_movie_fields
       is_sooner = ("sooner" in channel_name.lower() or "@soonerfrance" in channel_url.lower())
     AttributeError: 'NoneType' object has no attribute 'lower'
     ```
  7. `channel_url_none`:
     ```
     File "/Users/damienferrion/Documents/AppleDevelopper/AsieCineTube/server.py", line 991, in enrich_movie_fields
       or "@soonerfrance" in channel_url.lower()
     AttributeError: 'NoneType' object has no attribute 'lower'
     ```
  8. `none_keys_dict` (`{"videoId": None, "title": None, "channelName": None}`):
     ```
     AttributeError: 'NoneType' object has no attribute 'lower'
     ```

### 1.3 Test 3: `server.save_cached_movies` Atomicity and Corruption (Mission 3)
- **Tool Command**: `python3 -m unittest tests.test_challenger_m1_stress.EmpiricalStressTests.test_03_save_cached_movies_atomicity_and_corruption`
- **Result**:
  - `save_cached_movies` writes directly using `open(CACHE_FILE, "w", encoding="utf-8")` (line 1147) and `open(STATIC_EXPORT_FILE, "w", encoding="utf-8")` (line 1181).
  - Empirical verification: when tested with an un-serializable entry (e.g. `set([1, 2])`), `open(..., "w")` truncates the existing file on disk before `json.dump` fails. The existing file is left corrupted with partial/invalid JSON (`Expecting value: line 1 column 26 (char 25)`), destroying previously valid cache data.
  - Contract check (`PROJECT.md` line 49): specifies "*avant d'écrire atomiquement dans cache_movies.json et movies.json*". The current implementation is **non-atomic**.
  - Non-dict item crash: `cache_map["bad"] = "string"` causes an uncaught `AttributeError: 'str' object has no attribute 'get'` at line 1116 during `to_delete` list comprehension.
  - In-place mutation: `save_cached_movies` actively mutates `cache_map` by deleting non-conforming entries (`del cache_map[vid]`), fulfilling the in-memory purge requirement.

### 1.4 Test 4: `server.is_strictly_asian_movie` Throughput Benchmark (Mission 4)
- **Tool Command**: `python3 -m unittest tests.test_challenger_m1_stress.EmpiricalStressTests.test_04_throughput_10k_items`
- **Result**:
  - Batch size: **10,000 synthetic items** (2,500 Auteur/Classics, 2,500 Western exclusions, 2,500 Excluded channels/spam, 1,500 B-movie martial arts, 1,000 complex boundaries with URLs and CJK scripts).
  - Total elapsed time: **0.2861 seconds**.
  - Throughput: **34,958.9 items/second**.
  - Latencies:
    - Average: **28.4 µs**
    - Median (p50): **14.5 µs**
    - 95th percentile (p95): **119.5 µs**
    - 99th percentile (p99): **129.0 µs**
    - Maximum: **175.7 µs**
  - Accuracy: exactly **3,500 accepted** and **6,500 rejected** (100% agreement with oracle).

### 1.5 Unit Test Suite Failures in `test_tier1_features.py`
- **Tool Command**: `python3 -m unittest tests.test_tier1_features.TestF4AuteurCategoryInAPI`
- **Result**: 3 test failures:
  - `FAIL: test_f4_02_get_movies_all_contains_all_films` (`AssertionError: 9 != 3`)
  - `FAIL: test_f4_03_get_movies_category_country_filtering` (`AssertionError: Lists differ: ['Sn53ssy0N7Q', '6a9cQy-8d-Q', 'vid1'] != ['vid1']`)
  - `FAIL: test_f4_04_get_movies_empty_filter_result` (`AssertionError: Lists differ: [{'videoId': 'eA4Py_OT4uQ', ...}] != []`)
- **Cause in `server.py`**:
  Lines 1199–1203:
  ```python
  cache_map = load_cached_movies()
  for seed in SEED_MOVIES:
      vid = seed["videoId"]
      if vid not in cache_map:
          cache_map[vid] = enrich_movie_fields(seed)
  ```
  `get_movies()` unconditionally injects `SEED_MOVIES` (AKIRA `jp`, Rashomon `jp`, Detective Dee II `cn`, etc.) whenever a mocked cache is supplied, whereas `main()` (lines 1371–1376) only seeds `if not cache_map:`.

---

## 2. Logic Chain

1. **Premise 1 (`enrich_movie_fields`)**: In Python, `raw.get("key", default)` returns `None` if `"key"` exists in `raw` with value `None`. YouTube API responses and third-party scrapers regularly produce `null` fields (e.g. unlisted/live videos lacking `publishDate` or `viewCount`).
2. **Inference 1**: Slicing `None[:10]` or converting `int(None)` causes `TypeError`; calling `None.lower()` causes `AttributeError`. As observed in 8 test crashes, any scraped video item with `null` attributes will crash the harvester and server pipeline.
3. **Premise 2 (`save_cached_movies`)**: `PROJECT.md` line 49 explicitly states that `save_cached_movies` must write *atomically* to `cache_movies.json` and `movies.json`.
4. **Inference 2**: `open(path, "w")` truncates the file immediately upon opening. If an exception occurs during serialization (e.g., unexpected object or interruption), the catalog file on disk is wiped or left unparseable. An atomic write via temporary file (`.tmp`) and `os.replace` guarantees that the previous valid catalog file remains intact if serialization fails.
5. **Premise 3 (`get_movies`)**: In `server.py`, `main()` only seeds when `not cache_map`, whereas `get_movies` unconditionally merges `SEED_MOVIES` if individual seed videoIds are missing.
6. **Inference 3**: When testing or operating with a custom or filtered cache, seed movies are resurrected, causing unit tests `test_f4_02`, `test_f4_03`, and `test_f4_04` in `tests/test_tier1_features.py` to fail. Aligning `get_movies` with `main()` (`if not cache_map:`) restores expected isolation.

---

## 3. Caveats

- Milestone 1 ownership is restricted to `server.py`. Milestone 2 files (`updater.py`, `cache_movies.json`, `movies.json`) and Milestone 3 frontend files were not evaluated for changes.
- The 72 failures in the full test suite (`python3 -m unittest discover -s tests`) belong to Milestone 2 and Milestone 3 requirements (`updater.py` queries, `index.html` navigation chips, `app.js` UI logic) and are expected at this stage.

---

## 4. Conclusion

**Verdict: `REQUEST_CHANGES`**

The core classification logic, regex precompilation, and auteur detection in `server.py` are extraordinarily fast (35k items/s) and functionally sound. However, three stability and contract compliance defects must be resolved by the worker before Milestone 1 can be approved:

### Actionable Remediation Checklist for Worker:

1. **Harden `enrich_movie_fields` against `None` and malformed values**:
   ```python
   # server.py ~line 968
   vid = str(raw.get("videoId") or "")
   raw_dur = raw.get("durationSeconds")
   try:
       dur_sec = int(raw_dur) if raw_dur is not None else 5400
   except (ValueError, TypeError):
       dur_sec = 5400

   raw_views = raw.get("viewCount")
   try:
       views = int(raw_views) if raw_views is not None else 25000
   except (ValueError, TypeError):
       views = 25000

   pub_date = str(raw.get("publishDate") or "2025-01-01")[:10]
   title = str(raw.get("title") or "Film Asiatique Complet")
   channel_name = str(raw.get("channelName") or "Asian Cinema")
   channel_url = str(raw.get("channelUrl") or f"https://www.youtube.com/watch?v={vid}")
   description = str(raw.get("description") or "Film complet disponible sur YouTube avec sous-titres accessibles en français.")
   ```

2. **Implement Atomic File Writes in `save_cached_movies`**:
   Write to a `.tmp` file first and use `os.replace` to satisfy `PROJECT.md` contract line 49:
   ```python
   # server.py ~line 1146
   tmp_cache = CACHE_FILE + ".tmp"
   try:
       with open(tmp_cache, "w", encoding="utf-8") as f:
           json.dump(cache_map, f, ensure_ascii=False, indent=2)
       os.replace(tmp_cache, CACHE_FILE)
   except Exception as e:
       print("Erreur sauvegarde cache_movies.json:", e)
       if os.path.exists(tmp_cache):
           try:
               os.remove(tmp_cache)
           except OSError:
               pass

   # server.py ~line 1181
   tmp_static = STATIC_EXPORT_FILE + ".tmp"
   try:
       with open(tmp_static, "w", encoding="utf-8") as f:
           json.dump(export_data, f, ensure_ascii=False, indent=2)
       os.replace(tmp_static, STATIC_EXPORT_FILE)
   except Exception as e:
       print("Erreur export statique GitHub Pages:", e)
       if os.path.exists(tmp_static):
           try:
               os.remove(tmp_static)
           except OSError:
               pass
   ```
   And guard `to_delete` comprehension against non-dict items:
   ```python
   to_delete = [
       vid
       for vid, m in cache_map.items()
       if not isinstance(m, dict) or not is_strictly_asian_movie(
           m.get("title", ""),
           m.get("channelName", ""),
           m.get("description", ""),
           m.get("channelUrl", ""),
       )
   ]
   ```

3. **Align `get_movies` Seed Injection with `main()`**:
   In `server.py` line 1199, replace the unconditional per-seed loop with:
   ```python
   cache_map = load_cached_movies()
   if not cache_map:
       for seed in SEED_MOVIES:
           cache_map[seed["videoId"]] = enrich_movie_fields(seed)
   ```

---

## 5. Verification Method

To verify these fixes independently:

1. **Compilation Check**:
   ```bash
   python3 -m py_compile server.py
   ```

2. **Run Challenger Stress Harness**:
   ```bash
   python3 -m unittest tests.test_challenger_m1_stress
   ```
   *Expected*: 4 tests run, 0 failures, 0 errors, 0 crashes in `enrich_movie_fields`.

3. **Run Milestone 1 Tier 1 Feature Tests**:
   ```bash
   python3 -m unittest tests.test_tier1_features.TestF1ExcludedChannels \
       tests.test_tier1_features.TestF2BMovieMartialArtsExclusion \
       tests.test_tier1_features.TestF3AuteurDetectionAndEnrichment \
       tests.test_tier1_features.TestF4AuteurCategoryInAPI \
       tests.test_tier1_features.TestF5SeedHygieneAndCachePersistence
   ```
   *Expected*: 25 tests run, 0 failures, 0 errors.

4. **Verify Atomic Preservation on Failed Serialization**:
   ```bash
   python3 -c "
   import server, tempfile, os
   with tempfile.TemporaryDirectory() as tmpdir:
       server.CACHE_FILE = os.path.join(tmpdir, 'cache.json')
       server.save_cached_movies({'v1': {'title': 'Ozu', 'channelName': 'Shochiku'}})
       size_before = os.path.getsize(server.CACHE_FILE)
       server.save_cached_movies({'bad': {'unserializable': {1, 2}}})
       assert os.path.getsize(server.CACHE_FILE) == size_before, 'File was corrupted or truncated!'
   print('✅ Atomic write verified!')
   "
   ```
