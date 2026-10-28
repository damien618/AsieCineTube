# Changes Summary — Milestone 1 (Backend Core & Filter Engine)

**Target file modified**: `/Users/damienferrion/Documents/AppleDevelopper/AsieCineTube/server.py`
**Diff stats**: 1 file changed, 364 insertions(+), 46 deletions(-)

## Summary of Modifications

### 1. Expanded `SPAM_EXCLUSION_KEYWORDS`
- Appended short-drama markers, TV series binge summaries, and clickbait keywords:
  `숏드라마`, `短剧`, `스릴러 액션 영화`, `제이슨 스타뎀`, `대부호`, `大富豪`, `女社長`, `재벌`, `정략결혼`, `神医`, `逆襲`, `160분요약`, `통합본`, `병맛자막`.

### 2. Added `EXCLUDED_CHANNELS` (38 normalized names/handles)
- Banned channels specializing in low-quality martial arts/nanars/recap spam:
  `samurai vs ninja`, `martial arts theater`, `武道劇場`, `chinese online movie channel`, `iqiyi english`, `iqiyi action`, `iqiyi movie theater`, `iqiyi 한글자막`, `moxi movie`, `epic movies`, `hit english`, `drama shifter`, `ciné nanar`, `cine nanar`, `the best of action`, `french action hub`, `allociné films complets`, `allocine films complets`, `boxoffice`, `shortflix`, `happyshorttv`, `stardusttv`, `글로리 시어터`, `양파극장`, `浮生剧场`, `日本語スキット工房`, `青い月ドラマ`, `棠糖短剧`, `멀더의 무비파일`, `시네마버튼`, `영화리뷰하는사람`, `sbs 옛날 드라마`, `sbs catch`, `kbs drama`, `ytkiss`, `shaw brothers cinema`, `功夫侦探所`, `浪子走天下`.

### 3. Added `BMOVIE_MARTIAL_ARTS_EXCLUSIONS` (18 keywords)
- Targeted generic martial arts, low-budget swordplay, and serialized kung-fu:
  `ninja`, `kung fu`, `kung-fu`, `kungfu`, `kongfu`, `wuxia`, `shaolin`, `arts martiaux`, `martial arts`, `drunken fist`, `poing ivre`, `sword king`, `hermit's sword`, `unbeatable`, `costume drama/wuxia`, `police vs gansters`, `action supercut`, `무협`.

### 4. Sanitized Existing Channel & Marker Tables
- Removed `"ciné nanar"` from `VERIFIED_ASIAN_CHANNELS`.
- Removed `"wuxia"`, `"shaolin"`, `"kung fu"`, `"kung-fu"` from `AUTHENTIC_ASIAN_MARKERS`.

### 5. Defined Auteur Catalog & Festival Markers
- Defined `AUTEUR_DIRECTORS_TABLE`: 45 canonical master directors covering South Korea (e.g. Hong Sang-soo, Bong Joon-ho, Lee Chang-dong, Park Chan-wook, Im Kwon-taek), Japan (e.g. Akira Kurosawa, Yasujirō Ozu, Kenji Mizoguchi, Masaki Kobayashi, Hirokazu Kore-eda, Takeshi Kitano, Takashi Miike), and China / HK / Taiwan (e.g. Wong Kar-wai, Edward Yang, Hou Hsiao-hsien, Tsai Ming-liang, Jia Zhangke, Zhang Yimou, King Hu, Tsui Hark).
- Enforced word boundaries `\b` and diacritic patterns (e.g. `[oō]`, `sang-?soo`, `kar-?wai`) to prevent substring false positives.
- Defined `FESTIVAL_HERITAGE_MARKERS`: Cannes, Palme d'Or, Venise, Lion d'Or, Berlinale, Ours d'Or, Locarno, Busan, Criterion, Cinémathèque, Art et essai, Restauration 4K, Fifth Generation, New Taiwanese Cinema.
- Added precompiled regex cache `AUTEUR_DIRECTORS_COMPILED` and helpers: `detect_auteur()`, `has_festival_marker()`, and `detect_auteur_label()`.

### 6. Overhauled `is_strictly_asian_movie`
- Added optional `channel_url: str = ""` argument while retaining 3-argument backward compatibility.
- Stripped HTTP/HTTPS URLs from descriptions prior to regex matching to prevent URL hash collisions (e.g. `youtu.be/gil_9u4oZuI` falsely matching `ozu`).
- Unquoted percent-encoded channel handles and URLs via `urllib.parse.unquote`.
- Enforced 3-tier evaluation precedence:
  1. Immediate rejections: Western exclusions, Excluded channels, Spam/short-dramas.
  2. B-movie martial arts filter with explicit whitelist exception for SOONER, KOFA, or recognized Auteur/Festival works.
  3. Strict Asian authenticity validation: CJK characters in title/channel, verified channel whitelist, auteur/festival match, or authentic Asian markers.

### 7. Refactored `enrich_movie_fields`
- Computes `isAuteur: bool` and `auteurLabel: Optional[str]` following prestige hierarchy:
  - Grand Master: `"🎬 <Director Name>"`
  - KOFA: `"🏛️ KOFA (Patrimoine)"`
  - SOONER: `"🎬 Sélection Sooner"`
  - Festival / Restored: `"🎬 Cinéma d'Auteur"`
  - Default: `isAuteur = False`, `auteurLabel = None`
- Supports category `"auteur"` (preserves explicit category, or sets `"auteur"` if isAuteur is True and no specific genre was detected).

### 8. Sanitized `SEED_MOVIES`
- Replaced seed #5 (`IgY-P7pO0x4` from Ciné Nanar) with Akira Kurosawa's *Rashōmon* (1950, Lion d'Or Venise) categorized as `"auteur"` with `isAuteur=True` and `auteurLabel="🎬 Akira Kurosawa"`.

### 9. Updated `save_cached_movies`
- Purges `cache_map` in memory using `is_strictly_asian_movie` BEFORE writing to `cache_movies.json`, ensuring cache integrity on restart and harvest.
- Enriches all remaining movies and generates sorted static export for `movies.json`.

### 10. Enhanced `get_movies` & Endpoints
- Handles `category == "auteur"` to retrieve all auteur, KOFA, and Sooner catalog titles.
- Included `channelUrl` in `is_strictly_asian_movie` validation.
- Added `auteurLabel` to the text search query haystack.
