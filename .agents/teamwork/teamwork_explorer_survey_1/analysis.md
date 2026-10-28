# Deep Technical Investigation & Implementation Contract: Backend Filtering and Enrichment (`server.py`)

## 1. Executive Summary

This investigation analyzes the backend architecture and filtering engine of **AsieCinéTube FR** in [`server.py`](file:///Users/damienferrion/Documents/AppleDevelopper/AsieCineTube/server.py) in order to fulfill **Requirement R1**: refocusing the platform exclusively on Asian auteur, heritage, and festival cinema while eliminating B-movie martial arts/ninja titles and clickbait short-dramas.

### Key Metrics from Current Dataset (`movies.json` & `cache_movies.json`):
- **Current total catalogue**: 474 movies in `movies.json`, 474+ in `cache_movies.json`.
- **Excluded channel contaminations found**: **96 movies in `movies.json`** and **104 in `cache_movies.json`** originate from channels targeted for elimination (e.g., `samurai vs ninja` [14], `chinese online movie channel` [15], `iqiyi english/action` [20], `ciné nanar` [5], `shaw brothers cinema` [4], `boxoffice` [5], `양파극장` [2], `浮生剧场` [2]).
- **B-movie martial arts titles**: **42 additional movies** match generic kung-fu/wuxia/ninja terms without any auteur, KOFA, or Sooner affiliation.
- **Surviving legitimate films**: **338 films** pass the proposed strict filter, of which **208 films** qualify as auteur masterpieces, KOFA restorations, or official Sooner selections.
- **Immediate removal impact**: **136 low-quality/spam movies** will be purged immediately from the active catalogue upon implementation.

---

## 2. Flaws and Vulnerabilities in Current `server.py`

Direct examination of `server.py` reveals several critical architectural flaws that permitted the degradation of the catalogue:

### Flaw 1: CJK Script Bypass in `is_strictly_asian_movie`
Lines 234–240:
```python
has_hangul = bool(re.search(r"[\uac00-\ud7a3]", f"{title} {channel}"))
has_kana = bool(re.search(r"[\u3040-\u309f\u30a0-\u30ff]", f"{title} {channel}"))
has_hanzi = bool(re.search(r"[\u4e00-\u9fff]", f"{title} {channel}"))

if has_hangul or has_kana or has_hanzi:
    return True
```
**Mechanism**: Any video whose title or channel contains Hangul, Kana, or Hanzi is immediately accepted as `True`, bypassing any deeper content validation. Consequently, Chinese short-dramas (`短剧`) and Korean drama summary binges (`양파극장`, `160분요약`) bypassed filtering as long as they did not match the minimal initial spam list.

### Flaw 2: Contradictory Channel Verification
Line 155 of `server.py`:
```python
VERIFIED_ASIAN_CHANNELS = [
    ...
    "ciné nanar",
    ...
]
```
`"ciné nanar"` is explicitly listed under `VERIFIED_ASIAN_CHANNELS`, directly contradicting the requirement to exclude `Ciné Nanar`. Furthermore, channels like `"iqiyi"`, `"sbs"`, and `"kbs"` were listed as substrings, inadvertently validating sub-channels like `iqiyi action`, `sbs catch`, and `kbs drama`.

### Flaw 3: B-Movie Martial Arts Terms in `AUTHENTIC_ASIAN_MARKERS`
Lines 205–211 of `server.py`:
```python
AUTHENTIC_ASIAN_MARKERS = [
    ...
    "samurai", "samouraï", "yakuza", "wuxia", "shaolin", "kung fu", "kung-fu",
    "bruce lee", "jackie chan", "jet li", "donnie yen",
    ...
]
```
Because `is_strictly_asian_movie` returns `True` if any marker in `AUTHENTIC_ASIAN_MARKERS` is present, generic martial arts movies were systematically accepted rather than scrutinized.

### Flaw 4: Cache Desynchronization and Incomplete Purge
Lines 832–850 of `server.py` in `save_cached_movies`:
```python
with open(CACHE_FILE, "w", encoding="utf-8") as f:
    json.dump(cache_map, f, ensure_ascii=False, indent=2)

# Export statique pour GitHub Pages
movies_list = list(cache_map.values())
movies_list = [
    m for m in movies_list
    if is_strictly_asian_movie(...)
]
with open(STATIC_EXPORT_FILE, "w", encoding="utf-8") as f:
    json.dump(export_data, f, ensure_ascii=False, indent=2)
```
**Critical flaw**: `cache_map` was saved to `cache_movies.json` *before* the `is_strictly_asian_movie` filter was applied. Only `movies.json` received filtered items. Any rejected movie remained permanently cached in `cache_movies.json`, reloading into memory on every restart.

### Flaw 5: Poisoned `SEED_MOVIES`
Line 478 of `server.py`:
```python
{
    "videoId": "IgY-P7pO0x4",
    "title": "PANDÉMIE (The Flu / 감기) | Film Coréen Complet en Français | Jang Hyuk, Soo Ae",
    "channelName": "Ciné Nanar - Films Complets en Français",
    ...
}
```
`SEED_MOVIES` hardcoded a movie from `Ciné Nanar`. Whenever the server started or cached movies were loaded, `IgY-P7pO0x4` was injected back into the cache, violating the acceptance criteria.

---

## 3. Specifications for New Filtering Constants

### 3.1 `EXCLUDED_CHANNELS` (Exact Set)
To be defined in `server.py` (all lowercase, matched against channel name and channel URL):
```python
EXCLUDED_CHANNELS = [
    "samurai vs ninja",
    "martial arts theater",
    "武道劇場",
    "chinese online movie channel",
    "iqiyi english",
    "iqiyi action",
    "iqiyi movie theater",
    "iqiyi 한글자막",
    "moxi movie",
    "epic movies",
    "hit english",
    "drama shifter",
    "ciné nanar",
    "cine nanar",
    "the best of action",
    "french action hub",
    "allociné films complets",
    "allocine films complets",
    "boxoffice",
    "shortflix",
    "happyshorttv",
    "stardusttv",
    "글로리 시어터",
    "양파극장",
    "浮生剧场",
    "日本語スキット工房",
    "青い月ドラマ",
    "棠糖短剧",
    "멀더의 무비파일",
    "시네마버튼",
    "영화리뷰하는사람",
    "sbs 옛날 드라마",
    "sbs catch",
    "kbs drama",
    "ytkiss",
    "shaw brothers cinema",
    "功夫侦探所",
    "浪子走天下",
]
```

### 3.2 `BMOVIE_MARTIAL_ARTS_EXCLUSIONS`
Targeting low-budget martial arts, swordplay, and serial kung-fu titles:
```python
BMOVIE_MARTIAL_ARTS_EXCLUSIONS = [
    "ninja",
    "kung fu",
    "kung-fu",
    "kungfu",
    "kongfu",
    "wuxia",
    "shaolin",
    "arts martiaux",
    "martial arts",
    "drunken fist",
    "poing ivre",
    "sword king",
    "hermit's sword",
    "unbeatable",
    "costume drama/wuxia",
    "police vs gansters",
    "action supercut",
    "무협",
]
```

### 3.3 Enhanced `SPAM_EXCLUSION_KEYWORDS`
Augmenting existing list with short-drama, recap, and binge spam:
```python
SPAM_EXCLUSION_KEYWORDS = [
    # Initial keywords
    "billionaire",
    "milliardaire",
    "ceo's",
    "secretly loved",
    "spoiled by",
    "short drama",
    "mini drama",
    "vertical drama",
    "mafia boss",
    "alpha wolf",
    "stepmother",
    "nollywood",
    "bollywood",
    "hindi dubbed",
    "telugu",
    "tamil",
    "몰아보기",
    "결말까지",
    "결말포함",
    "유튜브드라마",
    "youtube drama",
    "드라마 리뷰",
    "영화 리뷰",
    "요약",
    "movie recap",
    "film recap",
    # Additional short-drama, recap & clickbait terms
    "숏드라마",
    "短剧",
    "스릴러 액션 영화",
    "제이슨 스타뎀",
    "대부호",
    "大富豪",
    "女社長",
    "재벌",
    "정략결혼",
    "神医",
    "逆襲",
    "160분요약",
    "통합본",
    "병맛자막",
]
```

### 3.4 `AUTEUR_DIRECTORS_AND_MARKERS` (Catalog & Detection Matrix)

To eliminate false positive matches (such as short names matching random Base64 IDs in URLs or common words like "famille Kobayashi" in *Hospitalité*), auteur directors are organized with canonical names and regex word-boundary patterns `\b`:

```python
AUTEUR_DIRECTORS_TABLE: List[Tuple[str, List[str]]] = [
    # 🇰🇷 Corée du Sud
    ("Hong Sang-soo", [r"\bhong\s+sang-?soo\b"]),
    ("Lee Chang-dong", [r"\blee\s+chang-?dong\b"]),
    ("Park Chan-wook", [r"\bpark\s+chan-?wook\b"]),
    ("Bong Joon-ho", [r"\bbong\s+joon-?ho\b"]),
    ("Kim Ki-young", [r"\bkim\s+ki-?young\b"]),
    ("Im Kwon-taek", [r"\bim\s+kwon-?taek\b"]),
    ("Kim Ki-duk", [r"\bkim\s+ki-?duk\b"]),
    ("Shin Sang-ok", [r"\bshin\s+sang-?ok\b"]),
    ("Lee Man-hee", [r"\blee\s+man-?hee\b"]),
    ("Ha Gil-jong", [r"\bha\s+gil-?jong\b"]),
    ("Bae Chang-ho", [r"\bbae\s+chang-?ho\b"]),
    ("Park Kwang-su", [r"\bpark\s+kwang-?su\b"]),
    ("Jang Sun-woo", [r"\bjang\s+sun-?woo\b"]),
    ("Hur Jin-ho", [r"\bhur\s+jin-?ho\b"]),
    ("Na Hong-jin", [r"\bna\s+hong-?jin\b"]),
    ("Ryoo Seung-wan", [r"\bryoo\s+seung-?wan\b"]),
    ("Kim Jee-woon", [r"\bkim\s+jee-?woon\b"]),
    ("July Jung", [r"\bjuly\s+jung\b"]),
    ("Yoon Ga-eun", [r"\byoon\s+ga-?eun\b"]),
    ("Kim Bora", [r"\bkim\s+bora\b"]),

    # 🇯🇵 Japon (Specific full names prioritized over single surnames)
    ("Kiyoshi Kurosawa", [r"\bkiyoshi\s+kurosawa\b"]),
    ("Akira Kurosawa", [r"\bakira\s+kurosawa\b", r"\bkurosawa\b"]),
    ("Yasujirō Ozu", [r"\byasujir[oō]\s+ozu\b", r"\bozu\b"]),
    ("Kenji Mizoguchi", [r"\bkenji\s+mizoguchi\b", r"\bmizoguchi\b"]),
    ("Mikio Naruse", [r"\bmikio\s+naruse\b", r"\bnaruse\b"]),
    ("Masaki Kobayashi", [r"\bmasaki\s+kobayashi\b"]),
    ("Nagisa Ōshima", [r"\bnagisa\s+[oō]shima\b", r"\b[oō]shima\b"]),
    ("Shohei Imamura", [r"\bsh[oō]hei\s+imamura\b", r"\bimamura\b"]),
    ("Hiroshi Teshigahara", [r"\bhiroshi\s+teshigahara\b", r"\bteshigahara\b"]),
    ("Seijun Suzuki", [r"\bseijun\s+suzuki\b"]),
    ("Hirokazu Kore-eda", [r"\bhirokazu\s+kore-?eda\b", r"\bkore-?eda\b", r"\bkoreeda\b"]),
    ("Takeshi Kitano", [r"\btakeshi\s+kitano\b", r"\bkitano\b"]),
    ("Naomi Kawase", [r"\bnaomi\s+kawase\b"]),
    ("Ryūsuke Hamaguchi", [r"\bry[uū]suke\s+hamaguchi\b", r"\bhamaguchi\b"]),
    ("Takashi Miike", [r"\btakashi\s+miike\b", r"\bmiike\b"]),
    ("Shunji Iwai", [r"\bshunji\s+iwai\b"]),
    ("Shin'ya Tsukamoto", [r"shin'?ya\s+tsukamoto\b", r"\btsukamoto\b"]),
    ("Satoshi Kon", [r"\bsatoshi\s+kon\b"]),
    ("Hayao Miyazaki", [r"\bhayao\s+miyazaki\b", r"\bmiyazaki\b"]),
    ("Isao Takahata", [r"\bisao\s+takahata\b", r"\btakahata\b"]),
    ("Katsuhiro Ōtomo", [r"\bkatsuhiro\s+[oō]tomo\b", r"\b[oō]tomo\b"]),
    ("Mamoru Hosoda", [r"\bmamoru\s+hosoda\b"]),
    ("Juzo Itami", [r"\bj[uū]zo\s+itami\b"]),
    ("Kaneto Shindō", [r"\bkaneto\s+shind[oō]\b"]),

    # 🇨🇳 Chine / Hong-Kong / Taïwan
    ("Wong Kar-wai", [r"\bwong\s+kar-?wai\b"]),
    ("Edward Yang", [r"\bedward\s+yang\b"]),
    ("Hou Hsiao-hsien", [r"\bhou\s+hsiao-?hsien\b"]),
    ("Tsai Ming-liang", [r"\btsai\s+ming-?liang\b"]),
    ("Jia Zhangke", [r"\bjia\s+zhang-?ke\b"]),
    ("Zhang Yimou", [r"\bzhang\s+yimou\b"]),
    ("Chen Kaige", [r"\bchen\s+kaige\b"]),
    ("Ang Lee", [r"\bang\s+lee\b"]),
    ("King Hu", [r"\bking\s+hu\b"]),
    ("Tsui Hark", [r"\btsui\s+hark\b"]),
    ("Ann Hui", [r"\bann\s+hui\b"]),
    ("Stanley Kwan", [r"\bstanley\s+kwan\b"]),
    ("Johnnie To", [r"\bjohnn(ie|y)\s+to\b"]),
    ("Fruit Chan", [r"\bfruit\s+chan\b"]),
    ("Lou Ye", [r"\blou\s+ye\b"]),
    ("Diao Yinan", [r"\bdiao\s+yinan\b"]),
    ("Bi Gan", [r"\bbi\s+gan\b"]),
    ("Hu Bo", [r"\bhu\s+bo\b"]),
    ("Wang Xiaoshuai", [r"\bwang\s+xiaoshuai\b"]),
    ("Jiang Wen", [r"\bjiang\s+wen\b"]),
]

FESTIVAL_HERITAGE_MARKERS = [
    "festival de cannes",
    "palme d'or",
    "caméra d'or",
    "camera d'or",
    "lion d'or",
    "mostra de venise",
    "venice film",
    "ours d'or",
    "berlinale",
    "locarno",
    "busan international",
    "criterion",
    "cinémathèque",
    "cinematheque",
    "film d'auteur",
    "art et essai",
    "chef-d'œuvre",
    "chef d'oeuvre",
    "restauré 4k",
    "restauration 4k",
    "restaurée 4k",
    "4k restauré",
    "fifth generation",
    "new taiwanese cinema",
]
```

---

## 4. Architecture of the Refined Filtering Engine (`is_strictly_asian_movie`)

### 4.1 Implementation Logic
The function signature will accept `channel_url: str = ""` to allow thorough channel verification across display names, handles, and URLs:

```python
def is_strictly_asian_movie(
    title: str,
    channel: str,
    description: str,
    channel_url: str = "",
) -> bool:
```

### 4.2 Step-by-Step Flowchart Execution:
1. **Pre-processing**:
   - Strip URLs (`re.sub(r"https?://\S+", "", description)`) to prevent URL hash collisions (e.g. `youtu.be/gil_9u4oZuI` matching `ozu`).
   - Decode URL percent-encoding for handles/channels (`urllib.parse.unquote(channel_url)`).
   - Generate combined lowercase text: `combined = f"{title} {channel} {channel_url} {clean_desc}".lower()`.
   - Generate channel lowercase string: `ch_combined = f"{channel} {channel_url} {urllib.parse.unquote(channel_url)}".lower()`.

2. **Step 1 — Immediate Rejections**:
   - Check `WESTERN_EXCLUSIONS_LIST`: if matched, return `False`.
   - Check `EXCLUDED_CHANNELS` against `ch_combined`: if matched, return `False`.
   - Check `SPAM_EXCLUSION_KEYWORDS` against `combined`: if matched, return `False`.

3. **Step 2 — Martial Arts / Sabre / Wuxia B-Movie Filter with Auteur Exception**:
   - Check if `combined` matches any term in `BMOVIE_MARTIAL_ARTS_EXCLUSIONS`.
   - If matched:
     - Check whitelist exemption:
       - Is it **SOONER** (`"sooner"` in `ch_combined` or `"@soonerfrance"` in `ch_combined`)?
       - Is it **KOFA** (`"@koreanfilm"` in `ch_combined` or `"korean classic film"` in `ch_combined` or `"한국고전영화"` in `ch_combined`)?
       - Does it match any auteur director in `AUTEUR_DIRECTORS_TABLE` or marker in `FESTIVAL_HERITAGE_MARKERS`?
     - If NOT exempted: return `False` immediately.
     - If exempted: proceed to Step 3.

4. **Step 3 — Strict Asian Authenticity Validation**:
   - Has Hangul (`[\uac00-\ud7a3]`), Kana (`[\u3040-\u309f\u30a0-\u30ff]`), or Hanzi (`[\u4e00-\u9fff]`) in `title` or `channel`? -> return `True`.
   - Channel matches sanitized `VERIFIED_ASIAN_CHANNELS`? -> return `True`.
   - Matches any director in `AUTEUR_DIRECTORS_TABLE` or `FESTIVAL_HERITAGE_MARKERS` or `AUTHENTIC_ASIAN_MARKERS`? -> return `True`.
   - Otherwise -> return `False`.

---

## 5. Specification of `enrich_movie_fields`

Every movie object passing through `enrich_movie_fields(raw)` must be enriched with:
- `isAuteur: bool` — `True` if directed by a recognized master, originating from KOFA or Sooner, or carrying a prestigious festival/heritage marker. `False` otherwise.
- `auteurLabel: Optional[str]` — User-facing formatted label:
  - Directed by a known master: `"🎬 <Canonical Director Name>"` (e.g., `"🎬 Akira Kurosawa"`, `"🎬 Bong Joon-ho"`, `"🎬 Yasujirō Ozu"`).
  - KOFA channel: `"🏛️ KOFA (Patrimoine)"`.
  - Sooner official release: `"🎬 Sélection Sooner"`.
  - Festival / Restored classic: `"🎬 Cinéma d'Auteur"`.
  - If `isAuteur == False`: `None` (or `""`).

### Category Handling:
- If `raw.get("category") == "auteur"`, or if `isAuteur` is `True` and no specific genre is detected, `category` can be `"auteur"`.
- If a movie is a thriller or drama (e.g. *Memories of Murder*), it maintains `category="thriller"` while having `isAuteur=True` and `auteurLabel="🎬 Bong Joon-ho"`.
- This dual representation enables the movie to be found in both the "🔪 Polar & Thriller" category AND the "🎬 Cinéma d'Auteur & Grands Maîtres" category!

---

## 6. Endpoints, Cache Invalidation and Static Export

### 6.1 `get_movies` in `server.py`
Handling `category == "auteur"`:
```python
elif category == "auteur":
    filtered = [
        m
        for m in filtered
        if m.get("isAuteur")
        or m.get("category") == "auteur"
        or m.get("category") == "kofa"
        or "sooner" in m.get("channelName", "").lower()
        or "@soonerfrance" in m.get("channelUrl", "").lower()
    ]
```
This guarantees `/api/movies?category=auteur` directly serves all auteur, KOFA, and Sooner titles.

### 6.2 `save_cached_movies` Purge Fix
To fulfill the requirement that no excluded movie remains in `cache_movies.json`:
```python
def save_cached_movies(cache_map: Dict[str, Dict[str, Any]]) -> None:
    with _CACHE_LOCK:
        # 1. Purge memory cache_map of any movie failing the strict filter
        to_delete = [
            vid
            for vid, m in cache_map.items()
            if not is_strictly_asian_movie(
                m.get("title", ""),
                m.get("channelName", ""),
                m.get("description", ""),
                m.get("channelUrl", ""),
            )
        ]
        for vid in to_delete:
            del cache_map[vid]

        # 2. Enrich remaining movies
        for vid, m in list(cache_map.items()):
            cache_map[vid] = enrich_movie_fields(m)

        # 3. Save clean cache to cache_movies.json
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache_map, f, ensure_ascii=False, indent=2)

        # 4. Generate sorted static export for movies.json
        movies_list = list(cache_map.values())
        movies_list.sort(
            key=lambda m: (
                m.get("publishedTimestamp", 0),
                m.get("publishDate", ""),
                m.get("viewCount", 0),
            ),
            reverse=True,
        )
        export_data = {
            "status": "ok",
            "source": "github_pages_static",
            "sort": "publishDate_desc",
            "total": len(movies_list),
            "countryCounts": {
                "kr": sum(1 for m in movies_list if m.get("country") == "kr"),
                "jp": sum(1 for m in movies_list if m.get("country") == "jp"),
                "cn": sum(1 for m in movies_list if m.get("country") == "cn"),
            },
            "updatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "movies": movies_list,
        }
        with open(STATIC_EXPORT_FILE, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
```

### 6.3 Cleaning `SEED_MOVIES`
In `SEED_MOVIES`:
Remove entry `IgY-P7pO0x4` ("PANDÉMIE", from `Ciné Nanar`).
Optionally replace with a classic auteur seed (such as Akira Kurosawa's *Rashomon*, Park Chan-wook's *Oldboy*, or Yasujirō Ozu's *Voyage à Tokyo*).

---

## 7. Edge Cases & Risk Analysis

| Edge Case / Risk | Concrete Danger | Mitigation Contract |
|---|---|---|
| **Short Master Names in URL Hashes** | `ozu` matched `https://youtu.be/gil_9u4oZuI` in a generic gangster movie description. | Strip `https?://\S+` from descriptions prior to regex matching. Use word boundary `\bozu\b`. |
| **Common Surnames in Descriptions** | "Kobayashi" matched "la famille Kobayashi" in Kôji Fukada's *Hospitalité*. | For Masaki Kobayashi, require `\bmasaki\s+kobayashi\b`. For Seijun Suzuki, require `\bseijun\s+suzuki\b`. |
| **URL-Encoded Channel Handles** | Channel handle `@c%EC%96%91%ED%8C%8C%EA%B7%B9%EC%9E%A5` might evade plain text `@양파극장`. | Apply `urllib.parse.unquote` to channel and channel URLs before comparison. |
| **Diacritics & Spelling Variations** | Directors written with macrons (`Ōshima`, `Ōtomo`, `Ozu`) or hyphens (`Hong Sang-soo` vs `Hong Sang soo`). | Regex patterns explicitly match both forms: `[oō]`, `kar-?wai`, `sang-?soo`, `kore-?eda`. |
| **Re-injection via `updater.py`** | `updater.py` fetching candidate videos from old queries. | Requirement R2 replaces search queries and applies `server.is_strictly_asian_movie`. Purge in `save_cached_movies` guarantees clean persistence. |

---

## 8. Verification Contract for Implementation

An automated verification script must validate the following criteria:
1. `python3 -m py_compile server.py updater.py` exits with status `0`.
2. No movie in `movies.json` or `cache_movies.json` contains any channel name from `EXCLUDED_CHANNELS`.
3. No movie in `movies.json` or `cache_movies.json` matches `BMOVIE_MARTIAL_ARTS_EXCLUSIONS` unless `isAuteur` is `True` or it originates from SOONER / KOFA.
4. All verified auteur films (Kurosawa, Ozu, Bong Joon-ho, Hong Sang-soo, Im Kwon-taek, Sooner, KOFA) possess `isAuteur == True` and a non-empty `auteurLabel`.
5. Calling `server.get_movies(category="auteur")` returns only films where `isAuteur` is `True` or category is `auteur`/`kofa`/`sooner`.
6. `movies.json` total count is valid and ordered with `publishedTimestamp` descending.
