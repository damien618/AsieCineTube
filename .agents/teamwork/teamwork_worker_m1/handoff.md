# Handoff Report: Milestone 1 — Backend Core & Filter Engine (`server.py`)

## 1. Observation
- **Modified File**: `/Users/damienferrion/Documents/AppleDevelopper/AsieCineTube/server.py`
  - Diff stats: `1 file changed, 364 insertions(+), 46 deletions(-)`
- **Compilation Check**:
  - Command: `python3 -m py_compile server.py updater.py`
  - Result: Returncode `0`, no errors or warnings.
- **Unit Assertion Results**:
  - Rejection of excluded channels (`samurai vs ninja`, `Martial Arts Theater`, `Ciné Nanar`, `양파극장`, `iqiyi action`, `Shaw Brothers Cinema`): All rejected (`False`).
  - Rejection of B-movie martial arts without auteur (`Ninja Revenge 1985`, `Shaolin Master`): All rejected (`False`).
  - Whitelist exemption for B-movie titles with auteur master or on SOONER/KOFA (*Seven Samurai*, *Détective Dee II*, *Harakiri*, KOFA classic): All preserved (`True`).
  - URL hash collision prevention (`youtu.be/gil_9u4oZuI` containing `ozu`): Stripped, returns `None` and `False`.
  - Common surname collision prevention (e.g. "famille Kobayashi" in *Hospitalité*): Returns `None`; Masaki Kobayashi explicitly requires `\bmasaki\s+kobayashi\b`.
  - URL-encoded channel handles (e.g. `%EC%96%91%ED%8C%8C%EA%B7%B9%EC%9E%A5`): Successfully unquoted and rejected (`False`).
- **Endpoint & Query Results**:
  - `server.get_movies(category='auteur')`: Returned **207 auteur movies**, all satisfying `isAuteur is True` or category in (`auteur`, `kofa`) or official Sooner channel.
  - `server.get_movies(category='all')`: Returned **338 strictly Asian movies**, matching Explorer 1's survey projection.
- **Catalogue Purity Verification**:
  - Zero excluded channel titles remain in `movies.json` and `cache_movies.json`.
  - All Akira Kurosawa films possess `isAuteur == True` and `auteurLabel == '🎬 Akira Kurosawa'`.

## 2. Logic Chain
1. **Premise 1**: The degradation of the catalog was caused by unconditional CJK script matching in `is_strictly_asian_movie`, `"ciné nanar"` in `VERIFIED_ASIAN_CHANNELS`, martial arts terms in `AUTHENTIC_ASIAN_MARKERS`, and an un-purged `cache_movies.json`.
2. **Step 1 (Precedence Inversion)**: By evaluating `WESTERN_EXCLUSIONS_LIST`, `EXCLUDED_CHANNELS`, and `SPAM_EXCLUSION_KEYWORDS` first, low-grade Chinese short-dramas and Korean TV binges are filtered before character script detection is reached.
3. **Step 2 (B-Movie Martial Arts with Auteur Whitelist)**: By intercepting `BMOVIE_MARTIAL_ARTS_EXCLUSIONS` and requiring an explicit match in `AUTEUR_DIRECTORS_TABLE`, `FESTIVAL_HERITAGE_MARKERS`, KOFA, or SOONER, generic kung-fu/ninja junk is purged while classics (*Seven Samurai*, *Harakiri*, *Détective Dee II*) are protected.
4. **Step 3 (False Positive Mitigation)**: By stripping URLs with `re.sub(r"https?://\S+", "", desc)` and requiring regex word boundaries `\b` with full names for ambiguous surnames, false positives from video hash IDs or descriptions are eliminated.
5. **Step 4 (Cache Integrity)**: Updating `save_cached_movies` to purge `cache_map` using `is_strictly_asian_movie` before writing to `cache_movies.json` guarantees that purged movies cannot be resurrected across server restarts or updater cycles.
6. **Step 5 (Seed Sanitation)**: Replacing entry #5 in `SEED_MOVIES` with Akira Kurosawa's *Rashōmon* removes the hardcoded dependency on Ciné Nanar.
7. **Step 6 (Contract Fulfillment)**: Adding `isAuteur` and `auteurLabel` to `enrich_movie_fields`, along with `category == "auteur"` handling in `get_movies`, fully implements the interface contracts specified in `PROJECT.md`.

## 3. Caveats
- `updater.py`, `app.js`, `index.html`, and `styles.css` were NOT modified, adhering strictly to Milestone 1 ownership boundaries. Milestone 2 will update `updater.py` search queries and harvest, and Milestone 3 will update the frontend navigation chips and styles.
- Data files `cache_movies.json` and `movies.json` were synced via `python3 server.py --export-only` to verify the active cache purge logic. Milestone 2 will execute the updated YouTube harvester to replenish fresh auteur films.

## 4. Conclusion
Milestone 1 is complete. All 12 backend core requirements are implemented in `server.py`:
- 38 excluded channels and 18 B-movie martial arts exclusion keywords added.
- Spam keyword list expanded with short-dramas and binge recap terms.
- `VERIFIED_ASIAN_CHANNELS` and `AUTHENTIC_ASIAN_MARKERS` cleansed.
- 45 canonical auteur directors and festival/heritage markers defined with word boundaries and compiled regex patterns.
- `is_strictly_asian_movie` refactored with 3-tier strict precedence and URL pre-cleaning.
- `enrich_movie_fields` produces `isAuteur` and `auteurLabel`.
- `get_movies` handles `category == "auteur"`.
- `SEED_MOVIES` sanitized with Akira Kurosawa's *Rashōmon*.
- `save_cached_movies` cleans `cache_map` before writing `cache_movies.json` and `movies.json`.
- All verification checks pass with 0 errors.

## 5. Verification Method
1. **Compilation Check**:
   ```bash
   python3 -m py_compile server.py updater.py
   ```
2. **Unit & Edge-Case Verification**:
   ```bash
   python3 -c "
   import server
   assert server.is_strictly_asian_movie('Ninja Revenge', 'Action Hub', 'Kung fu battle') is False
   assert server.is_strictly_asian_movie('Seven Samurai', 'Cinema', 'Kurosawa masterpiece') is True
   assert server.is_strictly_asian_movie('Drama', 'samurai vs ninja', 'Film') is False
   assert server.detect_auteur('https://youtu.be/gil_9u4oZuI') is None
   assert server.detect_auteur('famille Kobayashi') is None
   assert server.detect_auteur('Masaki Kobayashi') == 'Masaki Kobayashi'
   print('✅ Filter unit checks passed!')
   "
   ```
3. **Endpoint Verification**:
   ```bash
   python3 -c "
   import server
   movies, _ = server.get_movies(category='auteur')
   assert len(movies) > 0, 'Auteur category returned 0 movies'
   assert all(m.get('isAuteur') or m.get('category') in ('auteur', 'kofa') or 'sooner' in m.get('channelName','').lower() for m in movies)
   print(f'✅ Category auteur endpoint successfully returned {len(movies)} auteur movies')
   "
   ```
4. **Catalogue Purity Verification**:
   ```bash
   python3 -c "
   import json
   for path in ['movies.json', 'cache_movies.json']:
       with open(path) as f:
           raw = json.load(f)
           movies = raw['movies'] if isinstance(raw, dict) and 'movies' in raw else list(raw.values())
       excluded = ['samurai vs ninja', 'martial arts theater', 'chinese online movie channel', 'iqiyi action', 'ciné nanar', '양파극장', '浮生剧场']
       violations = [m.get('title') for m in movies if any(e in (m.get('channelName','') + ' ' + m.get('channelUrl','')).lower() for e in excluded)]
       assert len(violations) == 0, f'{path} contains excluded channels: {violations}'
   print('✅ Catalogue purity verified!')
   "
   ```
