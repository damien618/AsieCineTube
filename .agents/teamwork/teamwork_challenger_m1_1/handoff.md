# Handoff Report: Milestone 1 Verification (Challenger)

**Verdict**: `REQUEST_CHANGES`

## 1. Observation

### 1.1 Empirical Test Suite Execution
An adversarial test suite was authored and executed in `tests/test_adversarial_m1.py` targeting all 5 mission requirements across 20 test methods and 150+ assertions.

Command:
```bash
python3 -m unittest tests/test_adversarial_m1.py
```
Output summary:
```
Ran 20 tests in 0.077s
FAILED (failures=11)
```

### 1.2 Vulnerability A: Schemeless YouTube URLs Falsely Trigger Auteur Matches (`Yasujirō Ozu`)
- **Location**: `server.py:408` and `server.py:474`
  ```python
  clean = re.sub(r"https?://\S+", "", text or "")
  ```
- **Observed Behavior**:
  URLs lacking `http://` or `https://` (common in YouTube descriptions such as `youtu.be/...`, `www.youtube.com/...`, `youtube.com/...`) are NOT stripped. In Python regex, `-` is a word boundary (`\b`). Consequently, any YouTube video ID or hash containing `-ozu-` triggers `AUTEUR_DIRECTORS_TABLE`'s pattern `\bozu\b`.
- **Verbatim Empirical Proof**:
  ```python
  import server
  print(server.detect_auteur("youtu.be/gil-ozu-xyz"))
  # Output: 'Yasujirō Ozu'
  print(server.detect_auteur("www.youtube.com/watch?v=abc-ozu-def"))
  # Output: 'Yasujirō Ozu'
  
  title = "Super Kung Fu Ninja 2024"
  channel = "Action Hub"
  desc = "Full martial arts action movie. See also: youtu.be/abc-ozu-def"
  channel_url = "https://youtube.com/@actionhub"
  print(server.is_strictly_asian_movie(title, channel, desc, channel_url))
  # Output: True  (B-movie is accepted!)
  print(server.detect_auteur_label(title, channel, desc, channel_url))
  # Output: (True, '🎬 Yasujirō Ozu')  (B-movie is tagged as Ozu auteur!)
  ```

### 1.3 Vulnerability B: Spaceless YouTube Channel Handles Bypass Exclusion
- **Location**: `server.py:488`
  ```python
  if any(ec in ch_combined for ec in EXCLUDED_CHANNELS):
      return False
  ```
- **Observed Behavior**:
  `EXCLUDED_CHANNELS` contains spaced titles (`"chinese online movie channel"`, `"ciné nanar"`, `"cine nanar"`, `"martial arts theater"`, `"iqiyi action"`). When YouTube metadata provides a generic display name (`channel="Asian Cinema"`) and a spaceless handle URL (`channel_url="https://www.youtube.com/@cinenanar"` or `https://www.youtube.com/@chineseonlinemoviechannel`), `ec in ch_combined` evaluates to `False`. If the title contains CJK characters, the film is admitted.
- **Verbatim Empirical Proof**:
  ```python
  import server
  res = server.is_strictly_asian_movie(
      title="Classic Drama 1975 (한국 영화)",
      channel="Asian Cinema",
      description="Classic Korean drama",
      channel_url="https://www.youtube.com/@cinenanar"
  )
  print(res)
  # Output: True  (Ciné Nanar channel URL bypassed exclusion!)
  ```

### 1.4 Inconsistency: Unit Test Failures in `TestF4AuteurCategoryInAPI`
- **Location**: `server.py:1199-1203`
  ```python
  for seed in SEED_MOVIES:
      vid = seed["videoId"]
      if vid not in cache_map:
          cache_map[vid] = enrich_movie_fields(seed)
  ```
- **Observed Behavior**:
  Running `python3 -m unittest tests.test_tier1_features.TestF4AuteurCategoryInAPI` produces 3 failures (`test_f4_02`, `test_f4_03`, `test_f4_04`). `get_movies()` unconditionally injects `SEED_MOVIES` whenever a seed ID is missing from `cache_map`, even when `cache_map` is non-empty (as mocked by tests). In contrast, `main()` at line 1372 only injects seeds `if not cache_map:`.

### 1.5 Positive Verifications (Robust Functionality)
- **KOFA Classics**: 147/147 KOFA films in `cache_movies.json` are 100% preserved (`is_strictly_asian_movie == True`) and 100% have `isAuteur: True` with valid `auteurLabel`.
- **SOONER Titles**: 51/51 SOONER films in `cache_movies.json` are 100% preserved and 100% have `isAuteur: True` with valid `auteurLabel`.
- **Auteur Martial Arts Classics**: Kurosawa's *Seven Samurai*, Kobayashi's *Harakiri*, Tsui Hark's *Détective Dee II*, and King Hu's *A Touch of Zen* are correctly whitelisted through the B-movie filter and enriched with their canonical director labels.
- **Surname False Positives**: "famille Kobayashi", "Docteur Lee", "Mister Park", "Madame Kim", "Chef Wang", "Agent To", etc., all return `None` (0 false positives).
- **Standard Variations**: Upper/lower/mixed case, whitespace padding, URL encoding (`%EC%96%91%ED%8C%8C%EA%B7%B9%EC%9E%A5`), and French accents (`ciné nanar` / `cine nanar`) are properly rejected.

---

## 2. Logic Chain

1. **Premise 1 (Mission Contract)**: The challenger was instructed to verify that YouTube video IDs/hashes containing director names (e.g. `youtu.be/xxx_oZu_yyy`) are NEVER identified as Ozu, and that excluded channels cannot be bypassed.
2. **Step 1 (Regex Inadequacy)**: `re.sub(r"https?://\S+", "", text)` only matches URLs with explicit `http://` or `https://` protocols. Unprefixed URLs (`youtu.be/xxx-ozu-yyy`, `www.youtube.com/watch?v=xxx-ozu-yyy`) remain untouched.
3. **Step 2 (Token Boundary Collision)**: Because `-` is not a word character in regex `\w`, the pattern `\bozu\b` successfully matches `-ozu-` inside `youtu.be/abc-ozu-def`.
4. **Step 3 (Filter Bypass)**: A generic B-movie (`"Super Kung Fu Ninja 2024"`) with a description referencing a shortlink `youtu.be/abc-ozu-def` triggers `detect_auteur() == "Yasujirō Ozu"`. This activates the auteur whitelist exception in `is_strictly_asian_movie`, admitting the nanar and stamping it with `isAuteur: True` and `auteurLabel: "🎬 Yasujirō Ozu"`.
5. **Step 4 (Channel Handle Vulnerability)**: `EXCLUDED_CHANNELS` relies on substring matching against strings containing spaces. When YouTube harvesters retrieve channel handles (`/@cinenanar`, `/@chineseonlinemoviechannel`), the handle URL does not contain spaces. If `channelName` is generic or empty, the exclusion check fails.
6. **Step 5 (Seed Pollution in API)**: `get_movies()` unconditionally injects `SEED_MOVIES` into non-empty caches, breaking isolation and causing 3 test failures in `TestF4AuteurCategoryInAPI`.
7. **Conclusion**: The implementation contains two security/quality filter bypass vulnerabilities and an API state inconsistency. Changes must be requested before Milestone 1 can be certified.

---

## 3. Caveats
- The current production catalog (`cache_movies.json`, 484 raw entries) does not currently happen to contain a video with `-ozu-` in a schemeless description link, so existing static data is not corrupted. However, any future YouTube harvester run (`updater.py`) ingesting videos with common YouTube shortlinks is vulnerable.
- No modifications were made to implementation code (`server.py`), strictly adhering to the reviewer/challenger boundary.

---

## 4. Conclusion & Required Actions

**Verdict**: `REQUEST_CHANGES`

Worker M1 must apply three targeted modifications to `server.py`:

### Action 1: Strengthen URL Sanitization Regex
In `server.py` (`detect_auteur`, `detect_auteur_label`, and `is_strictly_asian_movie`):
Replace:
```python
clean = re.sub(r"https?://\S+", "", text or "")
```
With:
```python
clean = re.sub(r"(?:https?://|www\.|youtu\.be/)\S+", "", text or "")
```
Also strip URLs from `title` and `clean_text` to prevent hashes in titles from matching.

### Action 2: Robust Channel Handle Normalization
In `server.py` (`is_strictly_asian_movie`):
Normalize whitespace and symbols before checking `EXCLUDED_CHANNELS`:
```python
ch_norm = re.sub(r"[\s\-_@]+", "", ch_combined)
if any(ec in ch_combined or re.sub(r"[\s\-_@]+", "", ec) in ch_norm for ec in EXCLUDED_CHANNELS):
    return False
```

### Action 3: Align `SEED_MOVIES` Injection in `get_movies`
In `server.py` line 1199 (`get_movies`):
Replace:
```python
for seed in SEED_MOVIES:
    vid = seed["videoId"]
    if vid not in cache_map:
        cache_map[vid] = enrich_movie_fields(seed)
```
With:
```python
if not cache_map:
    for seed in SEED_MOVIES:
        cache_map[seed["videoId"]] = enrich_movie_fields(seed)
```

---

## 5. Verification Method

To independently verify these findings and confirm the fix once applied:

1. **Execute the Adversarial Suite**:
   ```bash
   python3 tests/test_adversarial_m1.py
   ```
   - Current state: Fails with 11 assertion errors demonstrating Vulnerabilities A and B.
   - Expected state after fix: 20 tests pass, 0 failures.

2. **Execute Tier 1 API Feature Suite**:
   ```bash
   python3 -m unittest tests.test_tier1_features.TestF4AuteurCategoryInAPI
   ```
   - Current state: Fails on `test_f4_02`, `test_f4_03`, `test_f4_04`.
   - Expected state after fix: 5 tests pass, 0 failures.

3. **Verify Catalog Preservation**:
   ```bash
   python3 -c "
   import json, server
   with open('cache_movies.json') as f:
       c = json.load(f)
   kofa = [m for m in c.values() if m.get('category') == 'kofa' or 'koreanfilm' in m.get('channelUrl','').lower()]
   assert len(kofa) >= 140
   assert all(server.is_strictly_asian_movie(m['title'], m['channelName'], m['description'], m['channelUrl']) for m in kofa)
   print('✅ KOFA preservation intact.')
   "
   ```
