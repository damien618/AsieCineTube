# Changes Implemented in `server.py` (Milestone 1 Remediation)

**Worker**: `teamwork_worker_m1_gen2`  
**Date**: 2026-10-28T18:02:30Z  
**Target File**: `server.py`

---

## 1. Schemeless URL Stripping (`URL_STRIP_REGEX`)
- **Problem**: Previously, `re.sub(r"https?://\S+", "", text)` only stripped URLs with an explicit `http://` or `https://` scheme. Schemeless URLs such as `youtu.be/gil-ozu-xyz`, `www.youtube.com/watch?v=abc-ozu-def`, or `youtube.com/vi/123-ozu-456` remained unstripped. In Python regex, hyphens are word boundaries (`\b`), causing IDs like `-ozu-` to falsely trigger the auteur match for `Yasujirō Ozu`.
- **Solution**:
  - Introduced precompiled regex:
    ```python
    URL_STRIP_REGEX = re.compile(
        r"(?:https?://|www\.|(?:\w+\.)?youtu\.be/|(?:\w+\.)?youtube\.com/)\S+",
        re.IGNORECASE,
    )
    ```
  - Replaced manual stripping in `detect_auteur`, `has_festival_marker`, `detect_auteur_label`, and `is_strictly_asian_movie`.
  - Added URL stripping to `title` as well as `description` in `detect_auteur_label` and `is_strictly_asian_movie`.

---

## 2. Channel Handle Normalization Against Spaceless Bypasses (`RE_CHANNEL_NORM`)
- **Problem**: Channels in `EXCLUDED_CHANNELS` have spaces (e.g. `"ciné nanar"`, `"chinese online movie channel"`, `"samurai vs ninja"`, `"martial arts theater"`). In YouTube metadata, a channel might have a generic display name (`"Asian Cinema"`) and a spaceless handle URL (`"https://www.youtube.com/@cinenanar"` or `"/@chineseonlinemoviechannel"`), bypassing substring checks (`ec in ch_combined`).
- **Solution**:
  - Introduced `RE_CHANNEL_NORM = re.compile(r"[\s\-_@]+")`.
  - In `is_strictly_asian_movie`, compute normalized channel string `ch_norm = RE_CHANNEL_NORM.sub("", ch_combined)`.
  - Check exclusion against both raw string and normalized string:
    ```python
    if any(
        ec in ch_combined or RE_CHANNEL_NORM.sub("", ec) in ch_norm
        for ec in EXCLUDED_CHANNELS
    ):
        return False
    ```

---

## 3. Hardened `enrich_movie_fields` Against None Values and Malformed Types
- **Problem**: When YouTube API or scrapers produce `None` or malformed fields (`"durationSeconds": None`, `"publishDate": None`, `"channelName": None`, `"viewCount": "15k"`, etc.), slicing `None[:10]`, calling `int(None)` or `None.lower()` caused `TypeError` or `AttributeError`.
- **Solution**:
  - Defensively guard `raw` input with `if not isinstance(raw, dict): raw = {}`.
  - Safe int parsing with try/except fallback for `durationSeconds` (default `5400`) and `viewCount` (default `25000`).
  - Safe string coercion for `publishDate` (`str(raw.get("publishDate") or "2025-01-01")[:10]`).
  - Safe string coercion for `title`, `channelName`, `channelUrl`, and `description`.
  - Safe string handling for `channelAvatar`, `koreanTitle`, and `thumbnail`.
  - Guard `availableLanguages` so non-list types fall back to valid lists.

---

## 4. Atomic File Writes & Data Corruption Guard in `save_cached_movies`
- **Problem**:
  - `open(CACHE_FILE, "w")` and `open(STATIC_EXPORT_FILE, "w")` directly truncated files upon opening. If an exception occurred during serialization (e.g. an unserializable object), the existing valid cache on disk was destroyed or truncated.
  - If `cache_map` contained a non-dict entry (e.g. `cache_map["bad"] = "string"`), `to_delete` list comprehension crashed with `AttributeError`.
- **Solution**:
  - Added `not isinstance(m, dict)` guard to `to_delete` and in-memory cache loops.
  - Atomic writes: write to `.tmp` files (`CACHE_FILE + ".tmp"` and `STATIC_EXPORT_FILE + ".tmp"`) first, then commit atomically via `os.replace`.
  - If writing or serialization fails, the `.tmp` file is cleaned up, preserving the preexisting catalog intact on disk.

---

## 5. Aligned `SEED_MOVIES` Injection in `get_movies`
- **Problem**: `get_movies` was unconditionally re-injecting `SEED_MOVIES` whenever a seed `videoId` was missing from `cache_map`, even when `cache_map` was already populated (e.g. in hermetic test fixtures or purged states), causing 3 test failures in `test_tier1_features.TestF4AuteurCategoryInAPI`.
- **Solution**:
  - Replaced the loop in `get_movies` with:
    ```python
    cache_map = load_cached_movies()
    if not cache_map:
        for seed in SEED_MOVIES:
            cache_map[seed["videoId"]] = enrich_movie_fields(seed)
    ```
  - Perfectly aligns `get_movies` with `main()`.

---

## Verification Summary
- `python3 -m py_compile server.py`: Clean compilation.
- `tests.test_adversarial_m1`: 20/20 passed (0 failures, resolved all 11 previous failures).
- `tests.test_challenger_m1_stress`: 4/4 passed (26/26 malformed dict inputs handled without crash).
- `tests.test_tier1_features`: 25/25 passed.
- `tests.test_tier2_boundaries`: 22/22 passed.
- `tests.test_tier3_combinations`: 5/5 passed.
- Total test coverage: **76 tests passed, 0 failures, 0 errors**.
