#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AsieCinéTube FR — Serveur Local & Export GitHub Pages
Films Coréens 🇰🇷, Japonais 🇯🇵 et Chinois 🇨🇳 accessibles au sous-titrage en français
(natif VOSTFR/VF ou traduction automatique YouTube CC), triés par date décroissante de publication.
Génère également 'movies.json' pour un fonctionnement 100% autonome sur GitHub Pages.
"""

import concurrent.futures
import datetime
import html
import http.server
import json
import os
import re
import socketserver
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

PORT = int(os.environ.get("PORT", "8000"))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(BASE_DIR, "cache_movies.json")
STATIC_EXPORT_FILE = os.path.join(BASE_DIR, "movies.json")

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36"
)

FRENCH_MONTHS = [
    "",
    "janv.",
    "févr.",
    "mars",
    "avr.",
    "mai",
    "juin",
    "juil.",
    "août",
    "sept.",
    "oct.",
    "nov.",
    "déc.",
]

COUNTRY_LABELS = {
    "kr": "🇰🇷 Corée",
    "jp": "🇯🇵 Japon",
    "cn": "🇨🇳 Chine",
}

# ==============================================================================
# FILTRES STRICTS : EXCLUSION DES FILMS AMÉRICAINS / OCCIDENTAUX & VALIDATION ASIATIQUE
# ==============================================================================

SPAM_EXCLUSION_KEYWORDS = [
    # Mots-clés initiaux
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
    # Mots-clés de short-dramas, résumés et clic-bait additionnels
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

WESTERN_EXCLUSIONS_LIST = [
    "samuel fuller",
    "gene evans",
    "the steel helmet",
    "baïonnette au canon",
    "aladdin",
    "oxford",
    "crazy party",
    "wolf king",
    "alpha wolf",
    "hollywood",
    "u.s.a",
    "u.s. army",
    "us army",
    "film américain",
    "film americain",
    "american movie",
    "american film",
    "cinéma américain",
    "western complet",
    "les films western",
    "les aubes sont calmes",
    "russian fury",
    "film russe",
    "téléfilm français",
    "film français complet",
    "lana condor",
    "x-men",
    "bruce willis",
    "steven seagal",
    "van damme",
    "schwarzenegger",
    "stallone",
    "boxoffice | romances",
    "boxoffice | comédies",
    "boxoffice | action",
    "sagas",
    "world at war",
    "filmstation",
]

VERIFIED_ASIAN_CHANNELS = [
    "@koreanfilm",
    "korean classic film",
    "한국고전영화",
    "korean film archive",
    "kofa",
    "kbs",
    "sbs",
    "mbc",
    "tvn",
    "cj enm",
    "showbox",
    "lotte",
    "toei",
    "kadokawa",
    "shochiku",
    "nikkatsu",
    "1905",
    "iqiyi",
    "youku",
    "tencent",
    "sooner",
    "ciné club",
    "movie district",
    "dramas coréens",
]

AUTHENTIC_ASIAN_MARKERS = [
    "bong joon",
    "park chan",
    "kim ki-young",
    "im kwon-taek",
    "lee chang-dong",
    "hong sang-soo",
    "song kang-ho",
    "choi min-sik",
    "ma dong-seok",
    "jang hyuk",
    "ha jung-woo",
    "son ye-jin",
    "sol kyung-gu",
    "kurosawa",
    "ozu",
    "mizoguchi",
    "miyazaki",
    "kitano",
    "kore-eda",
    "koreeda",
    "takashi miike",
    "tsukamoto",
    "wong kar-wai",
    "tsui hark",
    "zhang yimou",
    "bruce lee",
    "jackie chan",
    "jet li",
    "donnie yen",
    "stephen chow",
    "seoul",
    "séoul",
    "busan",
    "incheon",
    "tokyo",
    "kyoto",
    "osaka",
    "beijing",
    "pékin",
    "shanghai",
    "hong kong",
    "taïwan",
    "taiwan",
    "joseon",
    "samurai",
    "samouraï",
    "yakuza",
    "pansori",
    "film coréen",
    "film sud-coréen",
    "film sud coréen",
    "cinéma coréen",
    "film japonais",
    "cinéma japonais",
    "film chinois",
    "cinéma chinois",
]

# ==============================================================================
# CATALOGUE DES RÉALISATEURS D'AUTEUR & MARQUEURS DE FESTIVAL / PATRIMOINE
# ==============================================================================

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

    # 🇯🇵 Japon (Noms complets priorisés sur les patronymes isolés)
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
    ("Shin'ya Tsukamoto", [r"\bshin'?ya\s+tsukamoto\b", r"\btsukamoto\b"]),
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

# Patterns précompilés avec re.IGNORECASE pour performances et précision
AUTEUR_DIRECTORS_COMPILED: List[Tuple[str, List[re.Pattern]]] = [
    (director, [re.compile(p, re.IGNORECASE) for p in patterns])
    for director, patterns in AUTEUR_DIRECTORS_TABLE
]

URL_STRIP_REGEX = re.compile(
    r"(?:https?://|www\.|(?:\w+\.)?youtu\.be/|(?:\w+\.)?youtube\.com/)\S+",
    re.IGNORECASE,
)
RE_CHANNEL_NORM = re.compile(r"[\s\-_@]+")


def detect_auteur(text: str) -> Optional[str]:
    """Détecte si le texte mentionne un réalisateur d'auteur majeur."""
    clean = URL_STRIP_REGEX.sub("", text or "")
    for director, patterns in AUTEUR_DIRECTORS_COMPILED:
        for pat in patterns:
            if pat.search(clean):
                return director
    return None


def has_festival_marker(text: str) -> bool:
    """Vérifie la présence d'un marqueur de festival ou de patrimoine."""
    clean = URL_STRIP_REGEX.sub("", text or "").lower()
    return any(marker in clean for marker in FESTIVAL_HERITAGE_MARKERS)


def detect_auteur_label(
    title: str, channel_name: str, description: str, channel_url: str = ""
) -> Tuple[bool, Optional[str]]:
    """
    Détermine si un film relève du cinéma d'auteur / patrimoine et retourne (is_auteur, auteur_label).
    Priorité des labels :
    1. Grand maître identifié : '🎬 <Nom du réalisateur>'
    2. Chaîne KOFA : '🏛️ KOFA (Patrimoine)'
    3. Chaîne SOONER : '🎬 Sélection Sooner'
    4. Marqueur Festival / Patrimoine : '🎬 Cinéma d'Auteur'
    """
    clean_desc = URL_STRIP_REGEX.sub("", description or "")
    clean_title = URL_STRIP_REGEX.sub("", title or "")
    unquoted_ch = urllib.parse.unquote(channel_name or "")
    unquoted_url = urllib.parse.unquote(channel_url or "")
    text = f"{clean_title} {unquoted_ch} {clean_desc}"
    ch_text = f"{channel_name} {unquoted_ch} {channel_url} {unquoted_url}".lower()

    # 1. Grand réalisateur identifié
    director = detect_auteur(text)
    if director:
        return True, f"🎬 {director}"

    # 2. Chaîne KOFA
    if (
        "@koreanfilm" in ch_text
        or "korean classic film" in ch_text
        or "한국고전영화" in ch_text
        or "kofa" in ch_text
    ):
        return True, "🏛️ KOFA (Patrimoine)"

    # 3. Chaîne SOONER
    if "sooner" in ch_text or "@soonerfrance" in ch_text:
        return True, "🎬 Sélection Sooner"

    # 4. Marqueur Festival / Patrimoine
    if has_festival_marker(text):
        return True, "🎬 Cinéma d'Auteur"

    return False, None


def is_strictly_asian_movie(
    title: str, channel: str, description: str, channel_url: str = ""
) -> bool:
    """
    Vérifie qu'un film est bien asiatique selon les critères stricts de prestige :
    1. Rejet immédiat : films occidentaux, chaînes exclues, spam/short-drama/recap.
    2. Filtrage B-movie : ninja, kung-fu, wuxia rejetés sauf exception Auteur, SOONER ou KOFA.
    3. Validation asiatique stricte : CJK, chaînes vérifiées, table d'auteurs ou marqueurs authentiques.
    """
    # Nettoyage préalable des URLs pour éviter les faux positifs (ex: hashes YouTube contenant des noms courts)
    clean_desc = URL_STRIP_REGEX.sub("", description or "")
    clean_title = URL_STRIP_REGEX.sub("", title or "")
    unquoted_ch = urllib.parse.unquote(channel or "")
    unquoted_url = urllib.parse.unquote(channel_url or "")

    combined = f"{title} {channel} {unquoted_ch} {channel_url} {unquoted_url} {clean_desc}".lower()
    ch_combined = f"{channel} {unquoted_ch} {channel_url} {unquoted_url}".lower()
    ch_norm = RE_CHANNEL_NORM.sub("", ch_combined)
    clean_text = f"{clean_title} {unquoted_ch} {clean_desc}"

    # --------------------------------------------------------------------------
    # Étape 1 : Rejets immédiats (Occidental, Chaînes exclues, Spam / Short-drama)
    # --------------------------------------------------------------------------
    if any(excl in combined for excl in WESTERN_EXCLUSIONS_LIST):
        return False

    if any(
        ec in ch_combined or RE_CHANNEL_NORM.sub("", ec) in ch_norm
        for ec in EXCLUDED_CHANNELS
    ):
        return False

    if any(spam in combined for spam in SPAM_EXCLUSION_KEYWORDS):
        return False

    # --------------------------------------------------------------------------
    # Étape 2 : Filtrage B-Movies Arts Martiaux / Sabre avec Exception Auteur / SOONER / KOFA
    # --------------------------------------------------------------------------
    matches_bmovie = any(b_excl in combined for b_excl in BMOVIE_MARTIAL_ARTS_EXCLUSIONS)
    if matches_bmovie:
        is_sooner_whitelisted = "sooner" in ch_combined or "@soonerfrance" in ch_combined
        is_kofa_whitelisted = (
            "@koreanfilm" in ch_combined
            or "korean classic film" in ch_combined
            or "한국고전영화" in ch_combined
            or "kofa" in ch_combined
        )
        is_auteur_whitelisted = bool(detect_auteur(clean_text)) or has_festival_marker(clean_text)

        if not (is_sooner_whitelisted or is_kofa_whitelisted or is_auteur_whitelisted):
            return False

    # --------------------------------------------------------------------------
    # Étape 3 : Validation stricte de l'authenticité asiatique
    # --------------------------------------------------------------------------
    # 3.1 Détection directe par écriture asiatique dans le titre ou la chaîne
    has_hangul = bool(re.search(r"[\uac00-\ud7a3]", f"{title} {unquoted_ch}"))
    has_kana = bool(re.search(r"[\u3040-\u309f\u30a0-\u30ff]", f"{title} {unquoted_ch}"))
    has_hanzi = bool(re.search(r"[\u4e00-\u9fff]", f"{title} {unquoted_ch}"))
    if has_hangul or has_kana or has_hanzi:
        return True

    # 3.2 Chaînes asiatiques vérifiées
    if any(vc in ch_combined for vc in VERIFIED_ASIAN_CHANNELS):
        return True

    # 3.3 Présence d'un grand auteur ou marqueur festival / patrimoine
    if detect_auteur(clean_text) or has_festival_marker(clean_text):
        return True

    # 3.4 Marqueurs authentiques asiatiques
    if any(marker in combined for marker in AUTHENTIC_ASIAN_MARKERS):
        return True

    return False


def detect_country(
    title: str, channel: str, description: str, default_country: str = "kr"
) -> str:
    full_text = f"{title} {channel} {description}"
    low = full_text.lower()

    if any(
        k in low
        for k in [
            "japonais",
            "japanese",
            "japon",
            "tokyo",
            "kyoto",
            "osaka",
            "samurai",
            "samouraï",
            "yakuza",
            "kurosawa",
            "toei",
            "nikkatsu",
            "shochiku",
        ]
    ):
        return "jp"
    if any(
        k in low
        for k in [
            "coréen",
            "coréenne",
            "coreen",
            "korean",
            "corée",
            "seoul",
            "séoul",
            "busan",
            "joseon",
            "kofa",
            "kbs",
        ]
    ):
        return "kr"
    if any(
        k in low
        for k in [
            "chinois",
            "chinese",
            "chine",
            "hong kong",
            "hong-kong",
            "wuxia",
            "shaolin",
            "kung fu",
            "kung-fu",
            "beijing",
            "pékin",
            "shanghai",
            "1905",
            "iqiyi",
            "youku",
            "tencent",
        ]
    ):
        return "cn"

    if re.search(r"[\u3040-\u309f\u30a0-\u30ff]", full_text):
        return "jp"
    if re.search(r"[\uac00-\ud7a3]", full_text):
        return "kr"
    if re.search(r"[\u4e00-\u9fff]", full_text):
        return "cn"

    return default_country if default_country in ("kr", "jp", "cn") else "kr"


def detect_genre(title: str, description: str, default_genre: str = "drama") -> str:
    low = f"{title} {description}".lower()
    if any(
        k in low
        for k in [
            "horreur",
            "horror",
            "ghost",
            "fantôme",
            "zombie",
            "curse",
            "malédiction",
            "terrifiant",
            "mystère",
            "mystery",
        ]
    ):
        return "horror"
    if any(
        k in low
        for k in [
            "comédie",
            "comedie",
            "comedy",
            "drôle",
            "humour",
            "funny",
            "hilarious",
        ]
    ):
        return "comedy"
    if any(
        k in low
        for k in [
            "thriller",
            "action",
            "policier",
            "crime",
            "espion",
            "agent",
            "guerre",
            "war",
            "arts martiaux",
            "martial",
            "kung fu",
            "wuxia",
            "samurai",
            "sabre",
            "duel",
            "yakuza",
            "suspect",
            "vengeance",
            "revenge",
        ]
    ):
        return "thriller"
    if any(
        k in low
        for k in [
            "drame",
            "drama",
            "romance",
            "amour",
            "love",
            "famille",
            "family",
            "histoire",
            "historical",
        ]
    ):
        return "drama"
    return default_genre


# Catalogue initial vérifié de base (incluant KOFA @KoreanFilm, SOONER, Corée, Japon, Chine)
SEED_MOVIES: List[Dict[str, Any]] = [
    {
        "videoId": "oOT4ArijCA8",
        "title": "The Power of Kangwon Province (강원도의 힘, 1998) — Hong Sang-soo",
        "koreanTitle": "강원도의 힘(1998)",
        "country": "kr",
        "channelName": "한국고전영화 Korean Classic Film (@KoreanFilm)",
        "channelUrl": "https://www.youtube.com/@KoreanFilm",
        "channelAvatar": "https://ui-avatars.com/api/?name=KF&background=dc2626&color=fff&bold=true",
        "channelVerified": True,
        "durationSeconds": 6548,
        "viewCount": 182000,
        "publishDate": "2025-05-12",
        "subtitleType": "auto_fr",
        "availableLanguages": ["ko", "fr (auto)", "en"],
        "category": "kofa",
        "description": "Le deuxième chef-d'œuvre de Hong Sang-soo restauré par la Cinémathèque Coréenne (KOFA). Deux anciens amants voyagent chacun de leur côté dans la province de Kangwon.",
    },
    {
        "videoId": "gzVaW_fyV-Q",
        "title": "[4K] 초우 (1966) / Green Rain (Chou) — Im Kwon-taek | Korean Classic Film",
        "koreanTitle": "초우 (1966)",
        "country": "kr",
        "channelName": "한국고전영화 Korean Classic Film (@KoreanFilm)",
        "channelUrl": "https://www.youtube.com/@KoreanFilm",
        "channelAvatar": "https://ui-avatars.com/api/?name=KF&background=dc2626&color=fff&bold=true",
        "channelVerified": True,
        "durationSeconds": 6031,
        "viewCount": 145000,
        "publishDate": "2025-12-29",
        "subtitleType": "auto_fr",
        "availableLanguages": ["ko", "en", "fr (auto)"],
        "category": "kofa",
        "description": "Drame romantique classique coréen restauré en 4K par les Archives du Film Coréen (KOFA).",
    },
    {
        "videoId": "78__MtMCLNE",
        "title": "PIÉGÉS DANS LA TOUR (The Tower) | Film d'Action / Catastrophe Coréen Complet en Français",
        "koreanTitle": "타워 (The Tower)",
        "country": "kr",
        "channelName": "Ciné Club - Films Complets en français",
        "channelUrl": "https://www.youtube.com/watch?v=78__MtMCLNE",
        "channelAvatar": "https://ui-avatars.com/api/?name=CC&background=e50914&color=fff&bold=true",
        "channelVerified": True,
        "durationSeconds": 6085,
        "viewCount": 542000,
        "publishDate": "2026-08-15",
        "subtitleType": "native_fr",
        "availableLanguages": ["fr", "ko"],
        "category": "thriller",
        "description": "Le soir du réveillon de Noël à Séoul, un incendie catastrophique se déclare dans la tour de luxe Sky Tower. Film sud-coréen haletant avec Sol Kyung-gu et Son Ye-jin.",
    },
    {
        "videoId": "FhT6u4qklLU",
        "title": "Memories of Murder (살인의 추억) — Bong Joon-ho | Song Kang-ho",
        "koreanTitle": "살인의 추억",
        "country": "kr",
        "isPaid": True,
        "paidProvider": "Sooner (@soonerfrance)",
        "paidLabel": "Visionnage payant • @soonerfrance",
        "channelName": "SOONER (@soonerfrance)",
        "channelUrl": "https://www.youtube.com/@soonerfrance",
        "channelAvatar": "https://ui-avatars.com/api/?name=SO&background=16a34a&color=fff&bold=true",
        "channelVerified": True,
        "durationSeconds": 7537,
        "viewCount": 125000,
        "publishDate": "2025-12-31",
        "subtitleType": "native_fr",
        "availableLanguages": ["fr (VOSTFR / VF)", "ko"],
        "category": "thriller",
        "description": "En 1986, dans la province de Gyeonggi, le corps d'une jeune femme est retrouvé violée et assassinée. Chef-d'œuvre absolu de Bong Joon-ho disponible sur SOONER.",
    },
    {
        "videoId": "6a9cQy-8d-Q",
        "title": "Rashōmon (羅生門, 1950) — Akira Kurosawa | Lion d'Or Mostra de Venise",
        "koreanTitle": "라쇼몽 (1950)",
        "country": "jp",
        "channelName": "Cinéma Japonais Classique",
        "channelUrl": "https://www.youtube.com/@CinemaJaponaisClassique",
        "channelAvatar": "https://ui-avatars.com/api/?name=AK&background=b45309&color=fff&bold=true",
        "channelVerified": True,
        "durationSeconds": 5280,
        "viewCount": 320000,
        "publishDate": "2026-03-23",
        "subtitleType": "native_fr",
        "availableLanguages": ["fr (VOSTFR)", "ja"],
        "category": "auteur",
        "description": "Chef-d'œuvre absolu d'Akira Kurosawa avec Toshiro Mifune et Machiko Kyō. Lion d'or à la Mostra de Venise 1951, ce classique révolutionne la narration cinématographique sous la porte de Rashōmon.",
    },
    {
        "videoId": "Sn53ssy0N7Q",
        "title": "AKIRA (1988) — Katsuhiro Ōtomo | Chef-d'œuvre de l'Animation Japonaise",
        "koreanTitle": "アキラ (1988)",
        "country": "jp",
        "isPaid": True,
        "paidProvider": "Sooner (@soonerfrance)",
        "paidLabel": "Visionnage payant • @soonerfrance",
        "channelName": "SOONER (@soonerfrance)",
        "channelUrl": "https://www.youtube.com/@soonerfrance",
        "channelAvatar": "https://ui-avatars.com/api/?name=SO&background=16a34a&color=fff&bold=true",
        "channelVerified": True,
        "durationSeconds": 7464,
        "viewCount": 450000,
        "publishDate": "2026-05-26",
        "subtitleType": "native_fr",
        "availableLanguages": ["fr (VOSTFR / VF)", "ja"],
        "category": "thriller",
        "description": "Neo-Tokyo, 2019. Trente et un ans après la Troisième Guerre mondiale, la ville est en proie au chaos. Film d'animation culte disponible sur la chaîne officielle SOONER.",
    },
    {
        "videoId": "eA4Py_OT4uQ",
        "title": "Détective Dee II : La Légende du Dragon des Mers — Tsui Hark | Film d'Aventure et d'Action",
        "koreanTitle": "狄仁杰之神都龙王",
        "country": "cn",
        "isPaid": True,
        "paidProvider": "Sooner (@soonerfrance)",
        "paidLabel": "Visionnage payant • @soonerfrance",
        "channelName": "SOONER (@soonerfrance)",
        "channelUrl": "https://www.youtube.com/@soonerfrance",
        "channelAvatar": "https://ui-avatars.com/api/?name=SO&background=16a34a&color=fff&bold=true",
        "channelVerified": True,
        "durationSeconds": 7712,
        "viewCount": 89000,
        "publishDate": "2026-04-15",
        "subtitleType": "native_fr",
        "availableLanguages": ["fr (VOSTFR / VF)", "zh"],
        "category": "thriller",
        "description": "Le jeune Dee Renjie arrive à la capitale impériale pour rejoindre la force de justice suprême et affronter une créature marine colossale.",
    },
]

_CACHE_LOCK = threading.Lock()


def format_duration(seconds: int) -> str:
    if seconds <= 0:
        return "1:45:00"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def parse_duration_text(text: str) -> int:
    if not text:
        return 0
    cleaned = re.sub(r"[^\d:]", "", text.strip())
    parts = [p for p in cleaned.split(":") if p != ""]
    if not parts:
        return 0
    try:
        nums = [int(p) for p in parts]
        if len(nums) == 3:
            return nums[0] * 3600 + nums[1] * 60 + nums[2]
        if len(nums) == 2:
            return nums[0] * 60 + nums[1]
        return nums[0]
    except ValueError:
        return 0


def format_views(count: int) -> str:
    if count >= 1_000_000:
        val = count / 1_000_000
        formatted = f"{val:.1f}".replace(".", ",").rstrip("0").rstrip(",")
        return f"{formatted} M de vues"
    if count >= 1_000:
        val = count // 1_000
        return f"{val} k vues"
    return f"{count} vues"


def parse_view_count(text: str) -> int:
    if not text:
        return 15000
    digits = re.sub(r"[^\d]", "", text)
    if digits:
        try:
            return int(digits)
        except ValueError:
            pass
    return 15000


def date_to_timestamp(iso_date: str) -> int:
    try:
        dt = datetime.datetime.strptime(iso_date[:10], "%Y-%m-%d")
        return int(dt.replace(tzinfo=datetime.timezone.utc).timestamp())
    except Exception:
        return 0


def format_french_date(iso_date: str) -> str:
    try:
        dt = datetime.datetime.strptime(iso_date[:10], "%Y-%m-%d")
        month_name = FRENCH_MONTHS[dt.month]
        return f"{dt.day} {month_name} {dt.year}"
    except Exception:
        return iso_date


def format_relative_date(iso_date: str) -> str:
    try:
        dt = datetime.datetime.strptime(iso_date[:10], "%Y-%m-%d").date()
        today = datetime.date.today()
        delta_days = max(0, (today - dt).days)
        if delta_days == 0:
            return "aujourd'hui"
        if delta_days == 1:
            return "hier"
        if delta_days < 7:
            return f"il y a {delta_days} jours"
        if delta_days < 30:
            weeks = max(1, delta_days // 7)
            return f"il y a {weeks} sem."
        if delta_days < 365:
            months = max(1, delta_days // 30)
            return f"il y a {months} mois"
        years = max(1, delta_days // 365)
        return f"il y a {years} an{'s' if years > 1 else ''}"
    except Exception:
        return "récemment"


def parse_relative_time_to_iso(rel_text: str) -> str:
    today = datetime.date.today()
    if not rel_text:
        return (today - datetime.timedelta(days=180)).isoformat()

    low = rel_text.lower()
    m = re.search(r"(\d+)", low)
    num = int(m.group(1)) if m else 1

    if any(k in low for k in ["heure", "hour", "minute", "seconde", "시간", "분"]):
        delta = datetime.timedelta(days=0)
    elif any(k in low for k in ["jour", "day", "일"]):
        delta = datetime.timedelta(days=num)
    elif any(k in low for k in ["semaine", "week", "주"]):
        delta = datetime.timedelta(days=num * 7)
    elif any(k in low for k in ["mois", "month", "개월", "달"]):
        delta = datetime.timedelta(days=num * 30)
    elif any(k in low for k in ["an", "year", "년"]):
        delta = datetime.timedelta(days=num * 365)
    else:
        delta = datetime.timedelta(days=90)

    return (today - delta).isoformat()


def build_channel_avatar(
    channel_name: str,
    existing_avatar: str = "",
    is_sooner: bool = False,
    is_kofa: bool = False,
) -> str:
    """Retourne l'avatar de la chaîne en évitant le placeholder générique 'AC'."""
    if is_sooner:
        if existing_avatar and "yt3.ggpht.com" in existing_avatar:
            return existing_avatar
        return "https://ui-avatars.com/api/?name=SO&background=16a34a&color=fff&bold=true"
    if is_kofa:
        if existing_avatar and "yt3.ggpht.com" in existing_avatar:
            return existing_avatar
        return "https://ui-avatars.com/api/?name=KF&background=dc2626&color=fff&bold=true"
    if existing_avatar and "name=AC" not in existing_avatar:
        return existing_avatar

    words = [w for w in re.split(r"[\s\-_|@()]+", channel_name.strip()) if w]
    if len(words) >= 2:
        initials = (words[0][0] + words[1][0]).upper()
    elif words:
        initials = words[0][:2].upper()
    else:
        initials = "YT"
    encoded = urllib.parse.quote(initials)
    return f"https://ui-avatars.com/api/?name={encoded}&background=1f6feb&color=fff&bold=true"


def enrich_movie_fields(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalise et enrichit un objet film avec pays, sous-titres, dates et détection d'auteur."""
    if not isinstance(raw, dict):
        raw = {}

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
    sub_type = str(raw.get("subtitleType") or "auto_fr")
    title = str(raw.get("title") or "Film Asiatique Complet")
    channel_name = str(raw.get("channelName") or "Asian Cinema")
    channel_url = str(raw.get("channelUrl") or f"https://www.youtube.com/watch?v={vid}")
    description = str(
        raw.get("description")
        or "Film complet disponible sur YouTube avec sous-titres accessibles en français."
    )
    country = raw.get("country") or detect_country(
        title, channel_name, description, "kr"
    )
    country_label = COUNTRY_LABELS.get(country, "🇰🇷 Corée")
    category = raw.get("category") or detect_genre(title, description, "drama")
    if category in ("all", "kr", "jp", "cn", "recent", "native", "sooner"):
        category = detect_genre(title, description, "drama")

    # Vérification stricte de l'appartenance à la chaîne SOONER (@soonerfrance)
    is_sooner = (
        "sooner" in channel_name.lower()
        or "@soonerfrance" in channel_url.lower()
    )
    was_falsely_paid = bool(raw.get("isPaid")) and not is_sooner

    if is_sooner:
        channel_name = "SOONER (@soonerfrance)"
        channel_url = "https://www.youtube.com/@soonerfrance"
        is_paid = True
        paid_provider = "Sooner (@soonerfrance)"
        paid_label = "Visionnage payant • @soonerfrance"
        channel_verified = True
    else:
        is_paid = False
        paid_provider = ""
        paid_label = ""
        channel_verified = bool(raw.get("channelVerified", False))
        if was_falsely_paid and any(
            k in f"{title} {description}".lower()
            for k in ["engsub", "eng sub", "english subtitle"]
        ):
            sub_type = "auto_fr"

    is_kofa = (
        "@koreanfilm" in channel_url.lower()
        or "@koreanfilm" in channel_name.lower()
        or "korean classic film" in channel_name.lower()
        or category == "kofa"
    )
    if is_kofa:
        category = "kofa"
        sub_type = "auto_fr"
        sub_label = "🇰🇷 Corée • KOFA (Trad. Auto YT)"
        channel_verified = True
    elif is_paid:
        sub_type = "native_fr"
        sub_label = f"{country_label} • Payant (Sooner)"
    elif sub_type == "native_fr":
        sub_label = f"{country_label} • ST-FR Natif"
    else:
        sub_label = f"{country_label} • ST-FR Auto"

    # Détection et enrichissement cinéma d'auteur / grands maîtres
    is_auteur, auteur_label = detect_auteur_label(
        title, channel_name, description, channel_url
    )
    if not is_auteur and (raw.get("isAuteur") or raw.get("category") == "auteur"):
        is_auteur = True
        auteur_label = raw.get("auteurLabel") or "🎬 Cinéma d'Auteur"

    # Si le film est auteur et n'a pas de catégorie spécifique détectée (ou était drama par défaut)
    if category == "drama" and is_auteur and not raw.get("category"):
        category = "auteur"

    channel_avatar = build_channel_avatar(
        channel_name,
        str(raw.get("channelAvatar") or ""),
        is_sooner=is_sooner,
        is_kofa=is_kofa,
    )

    avail_langs = raw.get("availableLanguages")
    if not isinstance(avail_langs, list) or (was_falsely_paid and sub_type == "auto_fr"):
        avail_langs = ["fr"] if sub_type == "native_fr" else ["en", "fr (auto)"]

    return {
        "videoId": vid,
        "title": title,
        "koreanTitle": str(raw.get("koreanTitle") or ""),
        "country": country,
        "countryLabel": country_label,
        "isPaid": is_paid,
        "paidProvider": paid_provider,
        "paidLabel": paid_label,
        "channelName": channel_name,
        "channelUrl": channel_url,
        "channelAvatar": channel_avatar,
        "channelVerified": channel_verified,
        "thumbnail": str(
            raw.get("thumbnail") or f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
        ),
        "thumbnailMax": f"https://i.ytimg.com/vi/{vid}/maxresdefault.jpg",
        "durationSeconds": dur_sec,
        "durationFormatted": format_duration(dur_sec),
        "viewCount": views,
        "viewCountFormatted": format_views(views),
        "publishDate": pub_date,
        "publishedTimestamp": date_to_timestamp(pub_date),
        "publishedFormatted": format_french_date(pub_date),
        "publishedRelative": format_relative_date(pub_date),
        "subtitleType": sub_type,
        "subtitleLabel": sub_label,
        "availableLanguages": avail_langs,
        "category": category,
        "isAuteur": is_auteur,
        "auteurLabel": auteur_label,
        "description": description,
        "youtubeUrl": f"https://www.youtube.com/watch?v={vid}",
        # autoplay=0 pour ne pas lancer directement la vidéo sans le consentement de l'utilisateur
        "embedUrl": (
            f"https://www.youtube.com/embed/{vid}"
            "?autoplay=0&cc_load_policy=1&cc_lang_pref=fr&hl=fr&fs=1&rel=0"
        ),
    }


def load_cached_movies() -> Dict[str, Dict[str, Any]]:
    with _CACHE_LOCK:
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
            except Exception:
                pass
    return {}


def save_cached_movies(cache_map: Dict[str, Dict[str, Any]]) -> None:
    """Sauvegarde à la fois le cache local et 'movies.json' pour GitHub Pages en purgeant les indésirables."""
    with _CACHE_LOCK:
        # 1. Élimination stricte des films exclus ou non conformes de cache_map
        to_delete = [
            vid
            for vid, m in cache_map.items()
            if not isinstance(m, dict)
            or not is_strictly_asian_movie(
                m.get("title", ""),
                m.get("channelName", ""),
                m.get("description", ""),
                m.get("channelUrl", ""),
            )
        ]
        for vid in to_delete:
            del cache_map[vid]

        # 2. Propager les vrais avatars YouTube (yt3.ggpht.com) connus par nom de chaîne
        known_avatars: Dict[str, str] = {}
        known_urls: Dict[str, str] = {}
        for m in cache_map.values():
            if not isinstance(m, dict):
                continue
            ch = m.get("channelName", "")
            av = m.get("channelAvatar", "")
            cu = m.get("channelUrl", "")
            if ch and av and "yt3.ggpht.com" in av:
                known_avatars[ch] = av
            if ch and cu and "/@" in cu:
                known_urls[ch] = cu

        for vid, m in list(cache_map.items()):
            if not isinstance(m, dict):
                del cache_map[vid]
                continue
            ch = m.get("channelName", "")
            if ch in known_avatars and "yt3.ggpht.com" not in m.get("channelAvatar", ""):
                m["channelAvatar"] = known_avatars[ch]
            if ch in known_urls and "/@" not in m.get("channelUrl", ""):
                m["channelUrl"] = known_urls[ch]
            cache_map[vid] = enrich_movie_fields(m)

        # 3. Sauvegarde propre et atomique dans cache_movies.json
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

        # 4. Export statique atomique pour GitHub Pages
        tmp_static = STATIC_EXPORT_FILE + ".tmp"
        try:
            movies_list = list(cache_map.values())
            # Tri strict par date décroissante
            movies_list.sort(
                key=lambda m: (
                    m.get("publishedTimestamp", 0),
                    m.get("publishDate", ""),
                    m.get("viewCount", 0),
                ),
                reverse=True,
            )

            counts = {
                "kr": sum(1 for m in movies_list if m.get("country") == "kr"),
                "jp": sum(1 for m in movies_list if m.get("country") == "jp"),
                "cn": sum(1 for m in movies_list if m.get("country") == "cn"),
            }

            export_data = {
                "status": "ok",
                "source": "github_pages_static",
                "sort": "publishDate_desc",
                "total": len(movies_list),
                "countryCounts": counts,
                "updatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "movies": movies_list,
            }

            with open(tmp_static, "w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_static, STATIC_EXPORT_FILE)
            print(
                f"✅ Export statique GitHub Pages généré : {STATIC_EXPORT_FILE} ({len(movies_list)} films)"
            )
        except Exception as e:
            print("Erreur export statique GitHub Pages:", e)
            if os.path.exists(tmp_static):
                try:
                    os.remove(tmp_static)
                except OSError:
                    pass


def get_movies(
    query: str = "",
    category: str = "all",
    sub_filter: str = "all",
    min_duration: int = 40,
    refresh: bool = False,
) -> Tuple[List[Dict[str, Any]], str]:
    cache_map = load_cached_movies()

    if not cache_map:
        for seed in SEED_MOVIES:
            cache_map[seed["videoId"]] = enrich_movie_fields(seed)

    for vid, movie_obj in list(cache_map.items()):
        cache_map[vid] = enrich_movie_fields(movie_obj)

    clean_q = query.strip()
    all_movies = list(cache_map.values())

    # Élimination stricte des films américains / occidentaux
    all_movies = [
        m
        for m in all_movies
        if is_strictly_asian_movie(
            m.get("title", ""),
            m.get("channelName", ""),
            m.get("description", ""),
            m.get("channelUrl", ""),
        )
    ]

    min_sec = max(20, min_duration) * 60
    filtered = [m for m in all_movies if m.get("durationSeconds", 0) >= min_sec]

    if category and category not in ("all", "recent"):
        if category == "auteur":
            filtered = [
                m
                for m in filtered
                if m.get("isAuteur")
                or m.get("category") == "auteur"
                or m.get("category") == "kofa"
                or "sooner" in m.get("channelName", "").lower()
                or "@soonerfrance" in m.get("channelUrl", "").lower()
            ]
        elif category == "sooner":
            filtered = [
                m
                for m in filtered
                if "sooner" in m.get("channelName", "").lower()
                or "@soonerfrance" in m.get("channelUrl", "").lower()
            ]
        elif category == "kofa":
            filtered = [
                m
                for m in filtered
                if m.get("country") == "kr"
                and (
                    "@koreanfilm" in m.get("channelUrl", "").lower()
                    or "koreanfilm" in m.get("channelName", "").lower()
                    or "korean classic film" in m.get("channelName", "").lower()
                    or "kofa" in m.get("subtitleLabel", "").lower()
                    or m.get("category") == "kofa"
                )
            ]
        elif not clean_q:
            if category in ("kr", "jp", "cn"):
                filtered = [m for m in filtered if m.get("country") == category]
            elif category == "native":
                filtered = [m for m in filtered if m.get("subtitleType") == "native_fr"]
            else:
                filtered = [
                    m
                    for m in filtered
                    if m.get("category") == category
                    or category in m.get("title", "").lower()
                    or category in m.get("description", "").lower()
                ]

    if sub_filter == "native":
        filtered = [m for m in filtered if m.get("subtitleType") == "native_fr"]

    if clean_q:
        q_words = [w.lower() for w in clean_q.split() if w.strip()]
        q_matched = []
        for m in filtered:
            haystack = (
                f"{m.get('title', '')} {m.get('koreanTitle', '')} "
                f"{m.get('channelName', '')} {m.get('description', '')} "
                f"{m.get('countryLabel', '')} {m.get('category', '')} "
                f"{m.get('auteurLabel', '') or ''}"
            ).lower()
            if all(w in haystack for w in q_words) or any(
                w in haystack for w in q_words
            ):
                q_matched.append(m)
        filtered = q_matched

    filtered.sort(
        key=lambda m: (
            m.get("publishedTimestamp", 0),
            m.get("publishDate", ""),
            m.get("viewCount", 0),
        ),
        reverse=True,
    )

    return filtered, "cache"


class KCineTubeHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[AsieCinéTube] {self.address_string()} - {fmt % args}")

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ("/api/movies", "/movies.json"):
            params = urllib.parse.parse_qs(parsed.query)
            q = params.get("q", [""])[0]
            category = params.get("category", ["all"])[0]
            sub_filter = params.get("sub_filter", ["all"])[0]
            refresh = params.get("refresh", ["0"])[0] in ("1", "true", "yes")
            try:
                min_duration = int(params.get("min_duration", ["40"])[0])
            except ValueError:
                min_duration = 40

            movies, source = get_movies(
                query=q,
                category=category,
                sub_filter=sub_filter,
                min_duration=min_duration,
                refresh=refresh,
            )

            counts = {
                "kr": sum(1 for m in movies if m.get("country") == "kr"),
                "jp": sum(1 for m in movies if m.get("country") == "jp"),
                "cn": sum(1 for m in movies if m.get("country") == "cn"),
            }

            response_body = json.dumps(
                {
                    "status": "ok",
                    "source": source,
                    "sort": "publishDate_desc",
                    "query": q,
                    "category": category,
                    "subFilter": sub_filter,
                    "total": len(movies),
                    "countryCounts": counts,
                    "movies": movies,
                },
                ensure_ascii=False,
            ).encode("utf-8")

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(response_body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(response_body)
            return

        if parsed.path in ("/", ""):
            self.path = "/index.html"

        return super().do_GET()


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def main() -> None:
    cache_map = load_cached_movies()
    if not cache_map:
        for seed in SEED_MOVIES:
            enriched = enrich_movie_fields(seed)
            cache_map[enriched["videoId"]] = enriched
    else:
        for vid, movie_obj in list(cache_map.items()):
            cache_map[vid] = enrich_movie_fields(movie_obj)

    # Export automatique initial
    save_cached_movies(cache_map)

    if "--export-only" in sys.argv:
        print("Export terminé.")
        return

    with ThreadedHTTPServer(("0.0.0.0", PORT), KCineTubeHandler) as httpd:
        print(f"🎬 AsieCinéTube FR démarré sur http://localhost:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nArrêt du serveur.")


if __name__ == "__main__":
    main()
