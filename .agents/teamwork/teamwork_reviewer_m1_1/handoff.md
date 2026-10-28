# Code Review & Adversarial Challenge Report: Milestone 1 (`server.py`)

**Reviewer & Critic**: `teamwork_reviewer_m1_1`  
**Verdict**: **APPROVE**  
**Integrity Audit**: **PASS** (Zero integrity violations, no dummy facades, no hardcoded bypasses)  
**Date**: 2026-10-28T16:53:00Z  

---

## 1. Observation

### 1.1 Python Compilation Check
- **Command**: `python3 -m py_compile server.py updater.py`
- **Result**: Exit code `0`, clean compilation, zero syntax or indentation errors.

### 1.2 Inspection of Constants & Table Definitions in `server.py`
- **`EXCLUDED_CHANNELS`** (`server.py:107-146`):
  - Count: **38 channels** (Requirement: >= 35).
  - Contains: `samurai vs ninja`, `martial arts theater`, `武道劇場`, `chinese online movie channel`, `iqiyi english`, `iqiyi action`, `iqiyi movie theater`, `iqiyi 한글자막`, `moxi movie`, `epic movies`, `hit english`, `drama shifter`, `ciné nanar`, `cine nanar`, `the best of action`, `french action hub`, `allociné films complets`, `allocine films complets`, `boxoffice`, `shortflix`, `happyshorttv`, `stardusttv`, `글로리 시어터`, `양파극장`, `浮生剧场`, `日本語スキット工房`, `青い月ドラマ`, `棠糖短剧`, `멀더의 무비파일`, `시네마버튼`, `영화리뷰하는사람`, `sbs 옛날 드라마`, `sbs catch`, `kbs drama`, `ytkiss`, `shaw brothers cinema`, `功夫侦探所`, `浪子走天下`.
- **`BMOVIE_MARTIAL_ARTS_EXCLUSIONS`** (`server.py:148-167`):
  - Count: **18 keywords** (Requirement: >= 17).
  - Contains: `ninja`, `kung fu`, `kung-fu`, `kungfu`, `kongfu`, `wuxia`, `shaolin`, `arts martiaux`, `martial arts`, `drunken fist`, `poing ivre`, `sword king`, `hermit's sword`, `unbeatable`, `costume drama/wuxia`, `police vs gansters`, `action supercut`, `무협`.
- **`SPAM_EXCLUSION_KEYWORDS`** (`server.py:62-105`):
  - Total count: **40 keywords**.
  - Includes short-drama and recap markers: `숏드라마`, `短剧`, `스릴러 액션 영화`, `제이슨 스타뎀`, `대부호`, `大富豪`, `女社長`, `재벌`, `정략결혼`, `神医`, `逆襲`, `160분요약`, `통합본`, `병맛자막`.
- **Sanitization of Legacy Tables**:
  - `VERIFIED_ASIAN_CHANNELS` (`server.py:210-235`): `"ciné nanar"` completely removed.
  - `AUTHENTIC_ASIAN_MARKERS` (`server.py:237-294`): `"wuxia"`, `"shaolin"`, `"kung fu"`, `"kung-fu"` completely removed.
- **`AUTEUR_DIRECTORS_TABLE` & Regex Boundaries** (`server.py:300-403`):
  - Count: **45 master directors** (64 compiled regexes in `AUTEUR_DIRECTORS_COMPILED`).
  - Covers South Korea (Hong Sang-soo, Lee Chang-dong, Park Chan-wook, Bong Joon-ho, Kim Ki-young, Im Kwon-taek...), Japan (Akira Kurosawa, Yasujirō Ozu, Kenji Mizoguchi, Masaki Kobayashi, Nagisa Ōshima, Hirokazu Kore-eda, Takeshi Kitano...), China/HK/Taiwan (Wong Kar-wai, Edward Yang, Hou Hsiao-hsien, Tsai Ming-liang, Jia Zhangke, Zhang Yimou, King Hu, Tsui Hark...).
  - Every single pattern enforces regex word boundaries `\b` at start and end.
  - Precompiled with `re.IGNORECASE`.
  - Helper `detect_auteur(text)` scrubs URLs (`re.sub(r"https?://\S+", "", text or "")`) before regex evaluation.

### 1.3 Precedence Evaluation in `is_strictly_asian_movie` (`server.py:464-534`)
- **Step 1 (Immediate Exclusions)**: Evaluates `WESTERN_EXCLUSIONS_LIST`, `EXCLUDED_CHANNELS`, and `SPAM_EXCLUSION_KEYWORDS` first. Returns `False` unconditionally.
- **Step 2 (B-Movie Martial Arts with Whitelist)**: Intercepts `BMOVIE_MARTIAL_ARTS_EXCLUSIONS`. Returns `False` unless film is on Sooner, KOFA, or matches an Auteur/Festival marker.
- **Step 3 (Strict Asian Authenticity)**: Requires CJK scripts in title/channel, verified Asian channels, auteur/festival match, or authentic Asian markers.

### 1.4 API Contract & Field Enrichment
- **`enrich_movie_fields`** (`server.py:1032-1092`):
  - Invokes `detect_auteur_label(title, channel_name, description, channel_url)`.
  - Outputs `isAuteur: bool` and `auteurLabel: Optional[str]`.
  - Correctly transitions default genre from `"drama"` to `"auteur"` if `isAuteur` is `True` and no explicit genre was detected.
- **`get_movies`** (`server.py:1226-1235`):
  - Implements `category == "auteur"`.
  - Filters titles having `m.get('isAuteur')` or category in `('auteur', 'kofa')` or `"sooner"` in channel.
  - Adds `auteurLabel` to the text search query haystack (`server.py:1281`).

### 1.5 Seed Hygiene & Cache Persistence
- **`SEED_MOVIES`** (`server.py:686-815`):
  - Seed #5 replaced with Akira Kurosawa's *Rashōmon* (1950, Lion d'Or Venise, `videoId`: `6a9cQy-8d-Q`, category: `"auteur"`, `isAuteur`: `True`, `auteurLabel`: `"🎬 Akira Kurosawa"`).
  - No legacy Ciné Nanar seeds remain.
- **`save_cached_movies`** (`server.py:1108-1188`):
  - Directly cleans `cache_map` in memory:
    ```python
    to_delete = [vid for vid, m in cache_map.items() if not is_strictly_asian_movie(...)]
    for vid in to_delete:
        del cache_map[vid]
    ```
  - Writes purged data to `cache_movies.json` and generates sorted static export for `movies.json`.

### 1.6 Test Suite Execution
- **Unit & Boundary Tests**:
  - `python3 -m unittest tests.test_tier1_features.TestF1ExcludedChannels tests.test_tier1_features.TestF2BMovieMartialArtsExclusion tests.test_tier1_features.TestF3AuteurDetectionAndEnrichment tests.test_tier1_features.TestF4AuteurCategoryInAPI tests.test_tier1_features.TestF5SeedHygieneAndCachePersistence tests.test_tier2_boundaries tests.test_tier3_combinations`
  - **52 tests ran, 52 PASSED, 0 failures, 0 errors** in 0.104s.

---

## 2. Logic Chain

1. **Integrity Verification**: Code inspection revealed genuine pattern matching, dictionary processing, and cache management. No dummy mocks, hardcoded video IDs, or test-bypass shortcuts exist.
2. **Precedence Inversion**: Testing confirmed that `samurai vs ninja` with an Akira Kurosawa title returns `False`. The exclusion step occurs prior to auteur whitelisting or script validation, preventing malicious or low-grade channels from bypassing filtering by mentioning famous directors.
3. **B-Movie Whitelist Functionality**: Generic martial arts movies (*Ninja Revenge 1985*) return `False`, while authorized auteur films (*Seven Samurai*, *Harakiri*, *Détective Dee II*) and KOFA/Sooner releases return `True`.
4. **Collision Resistance**: Tests confirmed that YouTube URLs containing director names (e.g., `youtu.be/gil_9u4oZuI` containing substring `ozu`) are stripped and return `None`. Common surnames like "Kobayashi" do not trigger auteur attribution unless prefixed with "Masaki".
5. **Interface Conformance**: The output dictionary of `enrich_movie_fields` includes all required fields (`isAuteur`, `auteurLabel`), matching the contract specified in `PROJECT.md`.
6. **Active Cache Invalidation**: `save_cached_movies` purges `cache_map` before persisting, guaranteeing that un-purged entries cannot survive restarts.

---

## 3. Caveats & Adversarial Critic Findings

### Finding 1: Title vs. Description Director Attribution Precedence (Minor / Quality Improvement)
- **Observation**: In `detect_auteur_label`, text is formed as `text = f"{title} {unquoted_ch} {clean_desc}"`. `detect_auteur(text)` iterates through `AUTEUR_DIRECTORS_TABLE` in fixed order.
- **Scenario**: *The Housemaid (하녀, 1960)* directed by Kim Ki-young contains the description: `"Le thriller psychologique ayant directement inspiré Parasite de Bong Joon-ho."` Because Bong Joon-ho appears earlier in the table than Kim Ki-young, the film is labeled `🎬 Bong Joon-ho` instead of `🎬 Kim Ki-young`.
- **Mitigation Recommendation**: In `detect_auteur_label`, evaluate `detect_auteur(title)` first; only fallback to evaluating `clean_desc` if no director was detected in the title.

### Finding 2: Space-stripped Channel Handle Matching (Minor / Defense-in-Depth)
- **Observation**: `EXCLUDED_CHANNELS` contains display names with spaces (e.g. `'samurai vs ninja'`). If a channel display name is blank or spoofed and only `channelUrl` contains `@samuraivsninja`, substring matching fails.
- **Scenario**: In the present catalogue, all items have display names and are properly filtered (0 violations). However, normalizing `channel_url` by removing spaces or including handle variations in `EXCLUDED_CHANNELS` would provide added robustness.

### Finding 3: Given Name Spacing Romanization (Minor / Quality Improvement)
- **Observation**: Regex patterns such as `r"\bhong\s+sang-?soo\b"` match `hong sang-soo` and `hong sangsoo`, but not `hong sang soo` (with space between the given name syllables).
- **Mitigation Recommendation**: Use `r"\bhong\s+sang[-\s]?soo\b"` to support space-separated Korean/Chinese romanizations.

---

## 4. Conclusion

**Verdict: APPROVE**

Milestone 1 satisfies all functional, architectural, interface, and security requirements:
- Clean compilation without errors or warnings.
- Robust 3-tier filtering engine with zero leaks for excluded channels and B-movies.
- Complete, boundary-protected Auteur detection covering 45 master directors.
- Correct contract implementation for `isAuteur`, `auteurLabel`, and `/api/movies?category=auteur`.
- 100% pass rate across 52 automated tests in Tiers 1, 2, and 3.
- The identified adversarial findings are minor, non-blocking improvements that can be incorporated during routine maintenance.

---

## 5. Verification Method

To independently verify this assessment, execute the following commands in the project root:

1. **Compilation Check**:
   ```bash
   python3 -m py_compile server.py updater.py
   ```
2. **Milestone 1 Test Suite (52 tests across Tiers 1-3)**:
   ```bash
   python3 -m unittest tests.test_tier1_features.TestF1ExcludedChannels \
       tests.test_tier1_features.TestF2BMovieMartialArtsExclusion \
       tests.test_tier1_features.TestF3AuteurDetectionAndEnrichment \
       tests.test_tier1_features.TestF4AuteurCategoryInAPI \
       tests.test_tier1_features.TestF5SeedHygieneAndCachePersistence \
       tests.test_tier2_boundaries \
       tests.test_tier3_combinations
   ```
3. **Precedence & Collision Adversarial Check**:
   ```bash
   python3 -c "
   import server
   # Excluded channel with Auteur name -> Must be False
   assert server.is_strictly_asian_movie('Seven Samurai Akira Kurosawa', 'samurai vs ninja', 'Classic') is False
   # URL hash collision -> Must be None
   assert server.detect_auteur('https://youtu.be/gil_9u4oZuI') is None
   # Masaki Kobayashi vs plain Kobayashi
   assert server.detect_auteur('famille Kobayashi') is None
   assert server.detect_auteur('Masaki Kobayashi') == 'Masaki Kobayashi'
   # Auteur category query
   movies, _ = server.get_movies(category='auteur')
   assert len(movies) > 0
   print(f'Verification passed: {len(movies)} auteur movies verified.')
   "
   ```
