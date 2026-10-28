# Handoff Report: Technical Investigation of Backend Filtering & Auteur Enrichment (`server.py`)

## 1. Observation

### Source Code Inspections:
- In [`server.py:62-89`](file:///Users/damienferrion/Documents/AppleDevelopper/AsieCineTube/server.py#L62), `SPAM_EXCLUSION_KEYWORDS` contains basic clickbait keywords but lacks common Asian short-drama (`숏드라마`, `短剧`, `神医`, `逆襲`), binge summary (`160분요약`, `통합본`), and western clickbait actor terms (`제이슨 스타뎀`).
- In [`server.py:155`](file:///Users/damienferrion/Documents/AppleDevelopper/AsieCineTube/server.py#L155), `VERIFIED_ASIAN_CHANNELS` contains `"ciné nanar"`, which directly contradicts the requirement to exclude `Ciné Nanar`.
- In [`server.py:205-212`](file:///Users/damienferrion/Documents/AppleDevelopper/AsieCineTube/server.py#L205), `AUTHENTIC_ASIAN_MARKERS` includes `"wuxia"`, `"shaolin"`, `"kung fu"`, and `"kung-fu"`, allowing low-grade B-movies to pass authentication without auteur validation.
- In [`server.py:234-240`](file:///Users/damienferrion/Documents/AppleDevelopper/AsieCineTube/server.py#L234), `is_strictly_asian_movie` evaluates `if has_hangul or has_kana or has_hanzi: return True`, unconditionally accepting any video with CJK characters before evaluating whether the channel or content is spam/short-drama.
- In [`server.py:474-489`](file:///Users/damienferrion/Documents/AppleDevelopper/AsieCineTube/server.py#L474), `SEED_MOVIES` includes item `IgY-P7pO0x4` from channel `"Ciné Nanar - Films Complets en Français"`.
- In [`server.py:832-850`](file:///Users/damienferrion/Documents/AppleDevelopper/AsieCineTube/server.py#L832), `save_cached_movies` dumps `cache_map` directly into `cache_movies.json` without filtering; only the secondary export `movies.json` is filtered through `is_strictly_asian_movie`.
- In [`server.py:918-952`](file:///Users/damienferrion/Documents/AppleDevelopper/AsieCineTube/server.py#L918), `get_movies` does not handle `category == "auteur"`, falling back to a generic title/description text search.
- In [`server.py:681-794`](file:///Users/damienferrion/Documents/AppleDevelopper/AsieCineTube/server.py#L681), `enrich_movie_fields` lacks `isAuteur` and `auteurLabel` properties.

### Data Metric Commands & Verbatim Results:
- Command: `python3 -c "import json; m = json.load(open('movies.json'))['movies']; ..."`
  Result: **96 movies** in `movies.json` match `EXCLUDED_CHANNELS` (e.g. `samurai vs ninja`: 14, `chinese online movie channel`: 15, `iqiyi english`: 17, `ciné nanar`: 5, `boxoffice`: 5, `shaw brothers cinema`: 4, `양파극장`: 2, `浮生剧场`: 2).
- Command: `python3 -c "import json; cache = json.load(open('cache_movies.json')); ..."`
  Result: **104 movies** in `cache_movies.json` match `EXCLUDED_CHANNELS`.
- B-movie simulation command: Matching `BMOVIE_MARTIAL_ARTS_EXCLUSIONS` identified 94 movies; 52 originated from excluded channels, 42 were generic B-movies on unexcluded channels, and 1 legitimate movie (*Détective Dee II* by Tsui Hark on SOONER) was successfully protected by auteur/Sooner whitelist exception logic.
- Auteur detection simulation command: Identified **208 films** in current `movies.json` meeting auteur criteria (88 KOFA, 39 Sooner, 24 Im Kwon-taek, 13 Shin Sang-ok, 10 Lee Man-hee, 7 Akira Kurosawa, 5 Kim Ki-young, 4 Shin'ya Tsukamoto, 3 Yasujirō Ozu, 2 Masaki Kobayashi, 2 Tsui Hark, 2 Bong Joon-ho, etc.).
- Edge case discovery command: Searching for `ozu` in `movies.json` matched `https://youtu.be/gil_9u4oZuI` in the description of a generic gangster movie (*"Hong Kong gangster movie..."*), demonstrating that URL stripping (`re.sub(r"https?://\S+", "", desc)`) and regex word-boundary matching (`\bozu\b`) are mandatory.

---

## 2. Logic Chain

1. **Premise 1 (Observed channel pollution)**: 96 items in `movies.json` and 104 in `cache_movies.json` come from excluded channels because `is_strictly_asian_movie` accepted any Hangul/Kana/Hanzi title (Observation lines 234–240) and `save_cached_movies` never filtered `cache_movies.json` (Observation lines 832–850).
2. **Premise 2 (Order of Operations)**: To prevent clickbait short-dramas and excluded channels from leaking through via CJK character matching, `EXCLUDED_CHANNELS`, `WESTERN_EXCLUSIONS_LIST`, and `SPAM_EXCLUSION_KEYWORDS` must be evaluated **before** CJK character or Asian authenticity checks.
3. **Premise 3 (Martial Arts B-Movie Scrutiny)**: Filtering out `BMOVIE_MARTIAL_ARTS_EXCLUSIONS` eliminates 42 low-budget martial arts titles while preserving auteur works (e.g., Tsui Hark's *Détective Dee II*, Kurosawa's *Seven Samurai*, Kobayashi's *Harakiri*, Miike's *Seppuku*) only when paired with a whitelist exception for SOONER, KOFA, and `AUTEUR_DIRECTORS_AND_MARKERS`.
4. **Premise 4 (Precision in Auteur Detection)**: Short director names (e.g., *Ozu*, *Lee*, *To*, *Hu*, *Bo*, *Ye*) and common family names (*Kobayashi* in Fukada's *Hospitalité*) cause false-positive matches when matched naively. Pre-cleaning descriptions by removing URLs and using regex word boundaries `\b` with full names eliminates false positives.
5. **Premise 5 (Data Integrity & Seed Hygiene)**: Removing `IgY-P7pO0x4` (*Ciné Nanar*) from `SEED_MOVIES` and updating `save_cached_movies` to purge `cache_map` ensures that neither startup nor scheduled harvesting can re-pollute `cache_movies.json` or `movies.json`.
6. **Premise 6 (API Consistency)**: Implementing `category == "auteur"` inside `get_movies` and enriching movie records with `isAuteur: bool` and `auteurLabel: Optional[str]` inside `enrich_movie_fields` ensures seamless alignment between `/api/movies`, `movies.json`, and the frontend navigation chips.

---

## 3. Caveats

- **Scope boundary**: This investigation is read-only. No source files (`server.py`, `updater.py`, `movies.json`) were altered.
- **YouTube API Variability**: Channel handles may occasionally appear with URL encoding (e.g. `%EC%96%91%ED%8C%8C%EA%B7%B9%EC%9E%A5`) in `channelUrl`; the engine must use `urllib.parse.unquote` prior to channel evaluation.
- **Front-end synchronization**: While the backend contract defines `isAuteur` and `auteurLabel`, full user-facing display requires Requirement R3 (`app.js`, `index.html`, `styles.css`) to consume these attributes.

---

## 4. Conclusion

The backend filtering architecture in `server.py` requires 5 coordinated modifications:
1. **Define Constants**: Add `EXCLUDED_CHANNELS` (35 channels), `BMOVIE_MARTIAL_ARTS_EXCLUSIONS` (17 terms), expand `SPAM_EXCLUSION_KEYWORDS`, remove `"ciné nanar"` from `VERIFIED_ASIAN_CHANNELS`, and structure `AUTEUR_DIRECTORS_TABLE` with word-bounded regexes.
2. **Refactor `is_strictly_asian_movie`**: Enforce strict precedence: Immediate Exclusions (Western, Spam, Excluded Channels) -> B-Movie Filter with Auteur/SOONER/KOFA Whitelist Exception -> Asian Authenticity Validation.
3. **Enhance `enrich_movie_fields`**: Add `isAuteur: bool` and `auteurLabel: Optional[str]`, supporting priority labeling (`🎬 <Director>`, `🏛️ KOFA (Patrimoine)`, `🎬 Sélection Sooner`, `🎬 Cinéma d'Auteur`).
4. **Update `get_movies` & Endpoints**: Explicitly handle `category == "auteur"` to filter movies where `isAuteur == True` or category is `auteur`/`kofa`/`sooner`.
5. **Fix Cache Persistence & Seeds**: Remove `IgY-P7pO0x4` from `SEED_MOVIES` and update `save_cached_movies` to delete non-compliant movies from `cache_map` before writing `cache_movies.json`.

All implementation contracts and code blueprints are fully detailed in `analysis.md`.

---

## 5. Verification Method

To verify the implementation once applied by the downstream agent:
1. **Syntax & Compilation check**:
   ```bash
   python3 -m py_compile server.py updater.py
   ```
2. **Catalogue Purity Verification on `movies.json` and `cache_movies.json`**:
   ```bash
   python3 -c "
   import json
   for path in ['movies.json', 'cache_movies.json']:
       with open(path) as f:
           raw = json.load(f)
           movies = raw['movies'] if isinstance(raw, dict) and 'movies' in raw else list(raw.values())
       
       # Check 1: Excluded channels
       excluded = ['samurai vs ninja', 'martial arts theater', 'chinese online movie channel', 'iqiyi action', 'ciné nanar', '양파극장', '浮生剧场']
       violations = [m.get('title') for m in movies if any(e in (m.get('channelName','') + ' ' + m.get('channelUrl','')).lower() for e in excluded)]
       assert len(violations) == 0, f'{path} contains excluded channels: {violations}'
       
       # Check 2: Auteur enrichment
       kurosawa = [m for m in movies if 'kurosawa' in m.get('title','').lower() or 'kurosawa' in m.get('description','').lower()]
       for k in kurosawa:
           assert k.get('isAuteur') is True, f'Kurosawa film missing isAuteur: {k.get(\"title\")}'
           assert k.get('auteurLabel') is not None, f'Kurosawa film missing auteurLabel: {k.get(\"title\")}'
   print('✅ All verification assertions passed!')
   "
   ```
3. **Endpoint Validation**:
   ```bash
   python3 -c "
   import server
   movies, _ = server.get_movies(category='auteur')
   assert len(movies) > 0, 'Category auteur returned 0 movies'
   assert all(m.get('isAuteur') or m.get('category') in ('auteur', 'kofa') or 'sooner' in m.get('channelName','').lower() for m in movies)
   print(f'✅ Category auteur endpoint successfully returned {len(movies)} auteur movies')
   "
   ```
