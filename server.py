#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AsieCinéTube FR — Serveur Local de Recherche YouTube
Films Coréens 🇰🇷, Japonais 🇯🇵 et Chinois 🇨🇳 accessibles au sous-titrage en français
(natif VOSTFR/VF ou traduction automatique YouTube CC), triés par date décroissante de publication.
"""

import concurrent.futures
import datetime
import html
import http.server
import json
import os
import re
import socketserver
import threading
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

PORT = int(os.environ.get("PORT", "8000"))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(BASE_DIR, "cache_movies.json")

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

# Requêtes YouTube élargies par catégorie et par pays (Corée, Japon, Chine)
CATEGORY_QUERIES: Dict[str, List[Tuple[str, str, str]]] = {
    # Tuple: (requête YouTube, code_pays_par_défaut, genre_par_défaut)
    "all": [
        ("film coréen complet vostfr", "kr", "thriller"),
        ("film coréen complet en français", "kr", "thriller"),
        ("Korean Classic Film full movie", "kr", "drama"),
        ("한국영화 풀버전 영어자막", "kr", "drama"),
        ("film japonais complet vostfr", "jp", "drama"),
        ("film japonais complet en français", "jp", "thriller"),
        ("japanese full movie eng sub", "jp", "drama"),
        ("日本映画 フル 字幕", "jp", "drama"),
        ("film chinois complet vostfr", "cn", "thriller"),
        ("film chinois arts martiaux complet français", "cn", "thriller"),
        ("chinese movie full eng sub 1905", "cn", "drama"),
        ("wuxia action full movie eng sub", "cn", "thriller"),
    ],
    "kr": [
        ("film coréen complet vostfr", "kr", "thriller"),
        ("film sud coréen complet français", "kr", "thriller"),
        ("Korean Classic Film full movie 4K", "kr", "drama"),
        ("한국영화 풀버전 자막", "kr", "drama"),
        ("korean thriller action full movie eng sub", "kr", "thriller"),
        ("korean drama romance full movie eng sub", "kr", "drama"),
    ],
    "jp": [
        ("film japonais complet vostfr", "jp", "drama"),
        ("film japonais complet en français", "jp", "thriller"),
        ("japanese full movie eng sub drama", "jp", "drama"),
        ("samurai movie full eng sub", "jp", "thriller"),
        ("japanese horror mystery full movie eng sub", "jp", "horror"),
        ("japanese comedy film full movie eng sub", "jp", "comedy"),
    ],
    "cn": [
        ("film chinois complet vostfr", "cn", "drama"),
        ("film chinois complet en français action", "cn", "thriller"),
        ("chinese historical action movie full eng sub", "cn", "thriller"),
        ("hong kong action crime movie full eng sub", "cn", "thriller"),
        ("chinese drama movie full eng sub", "cn", "drama"),
        ("wuxia sword movie full eng sub", "cn", "thriller"),
    ],
    "recent": [
        ("film coréen complet français 2025 2026", "kr", "thriller"),
        ("film japonais complet vostfr 2025", "jp", "drama"),
        ("film chinois complet français 2025 2026", "cn", "thriller"),
    ],
    "native": [
        ("film coréen complet vostfr", "kr", "thriller"),
        ("film japonais complet vostfr", "jp", "drama"),
        ("film chinois complet vostfr", "cn", "thriller"),
    ],
    "thriller": [
        ("film thriller action coréen complet français", "kr", "thriller"),
        ("samurai yakuza japanese movie full sub", "jp", "thriller"),
        ("film action arts martiaux chinois complet français", "cn", "thriller"),
    ],
    "drama": [
        ("film drame romance coréen complet vostfr", "kr", "drama"),
        ("japanese drama romance full movie eng sub", "jp", "drama"),
        ("chinese emotional drama full movie eng sub", "cn", "drama"),
    ],
    "horror": [
        ("film horreur coréen complet vostfr", "kr", "horror"),
        ("japanese horror full movie eng sub", "jp", "horror"),
        ("chinese mystery fantasy full movie eng sub", "cn", "horror"),
    ],
    "comedy": [
        ("film comédie coréen complet vostfr", "kr", "comedy"),
        ("japanese comedy full movie eng sub", "jp", "comedy"),
        ("hong kong comedy full movie eng sub", "cn", "comedy"),
    ],
}

# Exclusion des compilations de mini-séries verticales / romans-savons CEO bas de gamme
SPAM_EXCLUSION_KEYWORDS = [
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
]

# ==============================================================================
# FILTRES STRICTS : EXCLUSION DES FILMS AMÉRICAINS / OCCIDENTAUX & VALIDATION ASIATIQUE
# ==============================================================================

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
    "ciné nanar",
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
    "wuxia",
    "shaolin",
    "kung fu",
    "kung-fu",
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


def is_strictly_asian_movie(title: str, channel: str, description: str) -> bool:
    """
    Vérifie avec rigueur qu'un film est bien une production asiatique (Corée, Japon, Chine)
    et élimine formellement tout film américain ou occidental.
    """
    combined = f"{title} {channel} {description}".lower()

    # 1. Élimination formelle si un marqueur de film américain / occidental est présent
    if any(excl in combined for excl in WESTERN_EXCLUSIONS_LIST):
        return False

    # Élimination des spams mini-dramas verticaux TikTok/CEO
    if any(spam in combined for spam in SPAM_EXCLUSION_KEYWORDS):
        return False

    # 2. Validation positive d'origine asiatique obligatoire :
    # A. Présence d'un alphabet asiatique dans le titre ou la chaîne
    has_hangul = bool(re.search(r"[\uac00-\ud7a3]", f"{title} {channel}"))
    has_kana = bool(re.search(r"[\u3040-\u309f\u30a0-\u30ff]", f"{title} {channel}"))
    has_hanzi = bool(re.search(r"[\u4e00-\u9fff]", f"{title} {channel}"))

    if has_hangul or has_kana or has_hanzi:
        return True

    # B. Chaîne asiatique vérifiée
    ch_low = channel.lower()
    if any(vc in ch_low for vc in VERIFIED_ASIAN_CHANNELS):
        return True

    # C. Réalisateur, acteur, lieu ou marqueur culturel asiatique authentique
    if any(marker in combined for marker in AUTHENTIC_ASIAN_MARKERS):
        return True

    # Sans aucun marqueur positif asiatique, le film est rejeté (évite les films américains)
    return False


def detect_country(title: str, channel: str, description: str, default_country: str = "kr") -> str:
    """Détermine si un film est Coréen (kr), Japonais (jp) ou Chinois (cn)."""
    full_text = f"{title} {channel} {description}"
    low = full_text.lower()

    # 1. Mots-clés explicites dans le titre/chaîne
    if any(k in low for k in ["japonais", "japanese", "japon", "tokyo", "kyoto", "osaka", "samurai", "samouraï", "yakuza", "kurosawa", "toei", "nikkatsu", "shochiku"]):
        return "jp"
    if any(k in low for k in ["coréen", "coréenne", "coreen", "korean", "corée", "seoul", "séoul", "busan", "joseon", "kofa", "kbs"]):
        return "kr"
    if any(k in low for k in ["chinois", "chinese", "chine", "hong kong", "hong-kong", "wuxia", "shaolin", "kung fu", "kung-fu", "beijing", "pékin", "shanghai", "1905", "iqiyi", "youku", "tencent"]):
        return "cn"

    # 2. Détection par alphabet
    # Hiragana / Katakana -> Japonais
    if re.search(r"[\u3040-\u309f\u30a0-\u30ff]", full_text):
        return "jp"
    # Hangul -> Coréen
    if re.search(r"[\uac00-\ud7a3]", full_text):
        return "kr"
    # Caractères Hanzi sans Hangul ni Kana -> Chinois
    if re.search(r"[\u4e00-\u9fff]", full_text):
        return "cn"

    return default_country if default_country in ("kr", "jp", "cn") else "kr"


def detect_genre(title: str, description: str, default_genre: str = "drama") -> str:
    """Détermine le genre principal du film à partir du titre et de la description."""
    low = f"{title} {description}".lower()
    if any(k in low for k in ["horreur", "horror", "ghost", "fantôme", "zombie", "curse", "malédiction", "terrifiant", "mystère", "mystery"]):
        return "horror"
    if any(k in low for k in ["comédie", "comedie", "comedy", "drôle", "humour", "funny", "hilarious"]):
        return "comedy"
    if any(k in low for k in ["thriller", "action", "policier", "crime", "espion", "agent", "guerre", "war", "arts martiaux", "martial", "kung fu", "wuxia", "samurai", "sabre", "duel", "yakuza", "suspect", "vengeance", "revenge"]):
        return "thriller"
    if any(k in low for k in ["drame", "drama", "romance", "amour", "love", "famille", "family", "histoire", "historical"]):
        return "drama"
    return default_genre


def is_valid_asian_movie(title: str, channel: str, description: str) -> bool:
    """Exclut les compilations de mini-dramas TikTok/CEO et les vidéos hors-sujet."""
    combined = f"{title} {channel} {description}".lower()
    if any(spam in combined for spam in SPAM_EXCLUSION_KEYWORDS):
        return False
    return True


# Catalogue initial vérifié de vrais films coréens, japonais et chinois sur YouTube
SEED_MOVIES: List[Dict[str, Any]] = [
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
        "videoId": "IgY-P7pO0x4",
        "title": "PANDÉMIE (The Flu / 감기) | Film Coréen Complet en Français | Jang Hyuk, Soo Ae",
        "koreanTitle": "감기 (The Flu)",
        "country": "kr",
        "channelName": "Ciné Nanar - Films Complets en Français",
        "channelUrl": "https://www.youtube.com/watch?v=IgY-P7pO0x4",
        "channelAvatar": "https://ui-avatars.com/api/?name=CN&background=1f6feb&color=fff&bold=true",
        "channelVerified": True,
        "durationSeconds": 7290,
        "viewCount": 890000,
        "publishDate": "2026-04-19",
        "subtitleType": "native_fr",
        "availableLanguages": ["fr", "ko"],
        "category": "thriller",
        "description": "À Bundang, dans la banlieue de Séoul, un virus respiratoire mortel se propage à une vitesse foudroyante.",
    },
    {
        "videoId": "VvCsPXo53Rc",
        "title": "L'AGENT FANTÔME (The Berlin File) | Film d'Espionnage Coréen Complet en Français | Ha Jung-woo",
        "koreanTitle": "베를린 (The Berlin File)",
        "country": "kr",
        "channelName": "The Best Of Action - Films Complets en Français",
        "channelUrl": "https://www.youtube.com/watch?v=VvCsPXo53Rc",
        "channelAvatar": "https://ui-avatars.com/api/?name=BA&background=0052cc&color=fff&bold=true",
        "channelVerified": True,
        "durationSeconds": 7230,
        "viewCount": 612000,
        "publishDate": "2026-04-18",
        "subtitleType": "native_fr",
        "availableLanguages": ["fr", "ko"],
        "category": "thriller",
        "description": "Un agent nord-coréen infiltré est trahi lors d'une vente d'armes secrète et traqué par les services de renseignement.",
    },
    {
        "videoId": "KlwPxCS9UN4",
        "title": "The Swordsman : L'Ultime Duel sous la Dynastie Joseon | Film Coréen Complet (Jang Hyuk)",
        "koreanTitle": "검객 (The Swordsman)",
        "country": "kr",
        "channelName": "Movie District",
        "channelUrl": "https://www.youtube.com/watch?v=KlwPxCS9UN4",
        "channelAvatar": "https://ui-avatars.com/api/?name=MD&background=d97706&color=fff&bold=true",
        "channelVerified": True,
        "durationSeconds": 6040,
        "viewCount": 734000,
        "publishDate": "2026-03-02",
        "subtitleType": "native_fr",
        "availableLanguages": ["fr", "ko", "en"],
        "category": "thriller",
        "description": "Après la chute du roi Gwanghaegun, le meilleur épéiste du royaume de Joseon reprend son sabre pour sauver sa fille.",
    },
    {
        "videoId": "gzVaW_fyV-Q",
        "title": "[4K] 초우 (1966) / Green Rain (Chou) — Im Kwon-taek | Korean Classic Film",
        "koreanTitle": "초우 (1966)",
        "country": "kr",
        "channelName": "한국고전영화 Korean Classic Film",
        "channelUrl": "https://www.youtube.com/@KoreanClassicFilm",
        "channelAvatar": "https://ui-avatars.com/api/?name=KC&background=dc2626&color=fff&bold=true",
        "channelVerified": True,
        "durationSeconds": 6120,
        "viewCount": 145000,
        "publishDate": "2025-12-29",
        "subtitleType": "auto_fr",
        "availableLanguages": ["ko", "en", "fr (auto)"],
        "category": "drama",
        "description": "Drame romantique classique coréen restauré en 4K par les Archives du Film Coréen (KOFA).",
    },
    {
        "videoId": "cYC0Qzp1fKg",
        "title": "The Goblin (2022, 피는 물보다 진하다) | Korean Action Crime Drama | Full Movie Multi-Sub",
        "koreanTitle": "피는 물보다 진하다 (2022)",
        "country": "kr",
        "channelName": "Smings World",
        "channelUrl": "https://www.youtube.com/watch?v=cYC0Qzp1fKg",
        "channelAvatar": "https://ui-avatars.com/api/?name=SW&background=059669&color=fff&bold=true",
        "channelVerified": False,
        "durationSeconds": 5460,
        "viewCount": 420000,
        "publishDate": "2025-04-20",
        "subtitleType": "native_fr",
        "availableLanguages": ["fr", "en", "ko", "es"],
        "category": "thriller",
        "description": "Doo-hyun, surnommé 'Le Gobelin', sort de dix ans de prison et découvre que son ancien rival a usurpé son identité.",
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


def enrich_movie_fields(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalise et enrichit un objet film avec pays, sous-titres et dates."""
    vid = raw.get("videoId", "")
    dur_sec = int(raw.get("durationSeconds", 5400))
    views = int(raw.get("viewCount", 25000))
    pub_date = raw.get("publishDate", "2025-01-01")[:10]
    sub_type = raw.get("subtitleType", "auto_fr")
    title = raw.get("title", "Film Asiatique Complet")
    channel_name = raw.get("channelName", "Asian Cinema")
    description = raw.get(
        "description",
        "Film complet disponible sur YouTube avec sous-titres accessibles en français.",
    )
    country = raw.get("country") or detect_country(title, channel_name, description, "kr")
    country_label = COUNTRY_LABELS.get(country, "🇰🇷 Corée")
    category = raw.get("category") or detect_genre(title, description, "drama")
    if category in ("all", "kofa", "kr", "jp", "cn", "recent", "native"):
        category = detect_genre(title, description, "drama")

    return {
        "videoId": vid,
        "title": title,
        "koreanTitle": raw.get("koreanTitle", ""),
        "country": country,
        "countryLabel": country_label,
        "isPaid": bool(raw.get("isPaid", False)),
        "paidProvider": raw.get("paidProvider", ""),
        "paidLabel": raw.get("paidLabel", "Visionnage payant" if raw.get("isPaid") else ""),
        "channelName": channel_name,
        "channelUrl": raw.get(
            "channelUrl", f"https://www.youtube.com/watch?v={vid}"
        ),
        "channelAvatar": raw.get("channelAvatar")
        or "https://ui-avatars.com/api/?name=AC&background=e50914&color=fff&bold=true",
        "channelVerified": bool(raw.get("channelVerified", False)),
        "thumbnail": raw.get("thumbnail")
        or f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
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
        "subtitleLabel": (
            f"{country_label} • ST-FR Natif"
            if sub_type == "native_fr"
            else f"{country_label} • ST-FR Auto"
        ),
        "availableLanguages": raw.get(
            "availableLanguages",
            ["fr"] if sub_type == "native_fr" else ["en", "fr (auto)"],
        ),
        "category": category,
        "description": description,
        "youtubeUrl": f"https://www.youtube.com/watch?v={vid}",
        "embedUrl": (
            f"https://www.youtube.com/embed/{vid}"
            "?autoplay=0&cc_load_policy=1&cc_lang_pref=fr&hl=fr&fs=1&rel=0"
        ),
    }


def fetch_video_exact_metadata(
    video_id: str,
) -> Tuple[Optional[str], Optional[str], List[str], Optional[str]]:
    """
    Récupère rapidement via /youtubei/v1/player :
    1. La date exacte de publication (publishDate YYYY-MM-DD)
    2. Le type de sous-titrage ('native_fr', 'auto_fr', ou None)
    3. Les langues de sous-titres disponibles
    4. La description complète du film
    """
    url = "https://www.youtube.com/youtubei/v1/player?prettyPrint=false"
    payload = {
        "context": {
            "client": {
                "hl": "fr",
                "gl": "FR",
                "clientName": "WEB",
                "clientVersion": "2.20241015.01.00",
            }
        },
        "videoId": video_id,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "fr-FR,fr;q=0.9",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
    except Exception:
        return None, None, [], None

    mf = data.get("microformat", {}).get("playerMicroformatRenderer", {})
    publish_date = mf.get("publishDate") or mf.get("uploadDate")
    if publish_date:
        publish_date = publish_date[:10]

    full_desc = mf.get("description", {}).get("simpleText") or data.get(
        "videoDetails", {}
    ).get("shortDescription")

    langs: List[str] = []
    sub_type: Optional[str] = None
    tracklist = (
        data.get("captions", {})
        .get("playerCaptionsTracklistRenderer", {})
        .get("captionTracks", [])
    )
    if tracklist:
        for tr in tracklist:
            code = tr.get("languageCode", "")
            if code and code not in langs:
                langs.append(code)
            if tr.get("isTranslatable"):
                if "fr (auto)" not in langs:
                    langs.append("fr (auto)")
        if any(c.startswith("fr") for c in langs):
            sub_type = "native_fr"
        elif langs:
            sub_type = "auto_fr"

    return publish_date, sub_type, langs, full_desc


def search_youtube_innertube(
    query: str,
    default_country: str = "kr",
    default_genre: str = "drama",
    min_duration_minutes: int = 40,
    verify_top_n: int = 8,
) -> List[Dict[str, Any]]:
    """
    Interroge YouTube (/youtubei/v1/search) avec filtre de durée > 20 min (films)
    et retourne tous les films asiatiques valides trouvés.
    """
    url = "https://www.youtube.com/youtubei/v1/search?prettyPrint=false"
    payload = {
        "context": {
            "client": {
                "hl": "fr",
                "gl": "FR",
                "clientName": "WEB",
                "clientVersion": "2.20241015.01.00",
            }
        },
        "query": query,
        "params": "EgIYAg%3D%3D",  # Vidéos longues (> 20 min)
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
            "Accept-Language": "fr-FR,fr;q=0.9",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=6.0) as resp:
            result = json.loads(resp.read().decode("utf-8", errors="ignore"))
    except Exception:
        return []

    video_renderers: List[Dict[str, Any]] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if "videoRenderer" in node and isinstance(node["videoRenderer"], dict):
                video_renderers.append(node["videoRenderer"])
            else:
                for val in node.values():
                    walk(val)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(result)

    candidates: List[Dict[str, Any]] = []
    min_seconds = max(20, min_duration_minutes) * 60

    for vr in video_renderers:
        vid = vr.get("videoId")
        if not vid:
            continue

        title_runs = vr.get("title", {}).get("runs", [])
        title = "".join(r.get("text", "") for r in title_runs).strip()
        if not title:
            title = vr.get("title", {}).get("simpleText", "").strip()
        if not title:
            continue

        length_text = vr.get("lengthText", {}).get("simpleText", "")
        if not length_text:
            length_runs = vr.get("lengthText", {}).get("runs", [])
            length_text = "".join(r.get("text", "") for r in length_runs)
        dur_seconds = parse_duration_text(length_text)
        if dur_seconds < min_seconds:
            continue

        owner_runs = vr.get("ownerText", {}).get("runs", [])
        channel_name = (
            owner_runs[0].get("text", "YouTube Movies")
            if owner_runs
            else "YouTube Movies"
        )
        channel_nav = (
            owner_runs[0]
            .get("navigationEndpoint", {})
            .get("commandMetadata", {})
            .get("webCommandMetadata", {})
            .get("url", "")
            if owner_runs
            else ""
        )
        channel_url = (
            f"https://www.youtube.com{channel_nav}"
            if channel_nav.startswith("/")
            else f"https://www.youtube.com/watch?v={vid}"
        )

        avatar_thumbs = (
            vr.get("channelThumbnailSupportedRenderers", {})
            .get("channelThumbnailWithLinkRenderer", {})
            .get("thumbnail", {})
            .get("thumbnails", [])
        )
        channel_avatar = avatar_thumbs[-1].get("url", "") if avatar_thumbs else ""

        owner_badges = vr.get("ownerBadges", [])
        channel_verified = any(
            "VERIFIED"
            in b.get("metadataBadgeRenderer", {}).get("style", "")
            for b in owner_badges
        )

        view_text = vr.get("viewCountText", {}).get("simpleText", "")
        if not view_text:
            view_runs = vr.get("viewCountText", {}).get("runs", [])
            view_text = "".join(r.get("text", "") for r in view_runs)
        view_count = parse_view_count(view_text)

        pub_rel_text = vr.get("publishedTimeText", {}).get("simpleText", "")
        estimated_iso = parse_relative_time_to_iso(pub_rel_text)

        desc_parts: List[str] = []
        for snip in vr.get("detailedMetadataSnippets", []):
            for run in snip.get("snippetText", {}).get("runs", []):
                desc_parts.append(run.get("text", ""))
        description = "".join(desc_parts).strip()

        if not is_strictly_asian_movie(title, channel_name, description):
            continue

        badges = vr.get("badges", [])
        has_cc_badge = any(
            b.get("metadataBadgeRenderer", {}).get("label", "").upper()
            in ("CC", "SOUS-TITRES", "SUBTITLES")
            or "CLOSED_CAPTION"
            in b.get("metadataBadgeRenderer", {}).get("icon", {}).get("iconType", "")
            for b in badges
        )

        combined_text = f"{title} {description} {channel_name} {query}".lower()
        is_explicit_fr = any(
            kw in combined_text
            for kw in [
                "vostfr",
                "en français",
                "en francais",
                "film complet français",
                "sous-titré français",
                "sous titré français",
                "sub fr",
                "stfr",
                "vf",
            ]
        )
        has_sub_keyword = any(
            kw in combined_text
            for kw in ["sub", "eng sub", "multi sub", "cc", "자막", "字幕", "korean classic film"]
        )

        if not (has_cc_badge or is_explicit_fr or has_sub_keyword):
            continue

        sub_type = "native_fr" if is_explicit_fr else "auto_fr"
        country = detect_country(title, channel_name, description, default_country)
        genre = detect_genre(title, description, default_genre)

        candidates.append(
            {
                "videoId": vid,
                "title": html.unescape(title),
                "koreanTitle": "",
                "country": country,
                "channelName": channel_name,
                "channelUrl": channel_url,
                "channelAvatar": channel_avatar,
                "channelVerified": channel_verified,
                "durationSeconds": dur_seconds,
                "viewCount": view_count,
                "publishDate": estimated_iso,
                "subtitleType": sub_type,
                "availableLanguages": (
                    ["fr"] if sub_type == "native_fr" else ["en", "fr (auto)"]
                ),
                "category": genre,
                "description": description
                or f"Film {COUNTRY_LABELS.get(country, 'asiatique')} complet sur YouTube avec sous-titres accessibles en français.",
            }
        )

    # Enrichissement exact de publishDate sur les premiers candidats de la requête
    top_candidates = candidates[:verify_top_n]

    def enrich_candidate(cand: Dict[str, Any]) -> Dict[str, Any]:
        exact_date, verified_sub, langs, full_desc = fetch_video_exact_metadata(
            cand["videoId"]
        )
        if exact_date:
            cand["publishDate"] = exact_date
        if verified_sub and cand["subtitleType"] != "native_fr":
            cand["subtitleType"] = verified_sub
        if langs:
            cand["availableLanguages"] = langs
        if full_desc and len(full_desc) > len(cand.get("description", "")):
            cand["description"] = full_desc[:450]
        return cand

    enriched_list: List[Dict[str, Any]] = []
    if top_candidates:
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(enrich_candidate, c) for c in top_candidates]
            for fut in concurrent.futures.as_completed(futures):
                try:
                    enriched_list.append(fut.result())
                except Exception:
                    pass

    enriched_ids = {c["videoId"] for c in enriched_list}
    for c in candidates[verify_top_n:]:
        if c["videoId"] not in enriched_ids:
            enriched_list.append(c)

    return enriched_list


SOONER_ASIAN_QUERIES: List[Tuple[str, str]] = [
    ("coréen", "kr"),
    ("corée", "kr"),
    ("séoul", "kr"),
    ("bong joon-ho", "kr"),
    ("japonais", "jp"),
    ("japon", "jp"),
    ("tokyo", "jp"),
    ("tsukamoto", "jp"),
    ("fukada", "jp"),
    ("samouraï", "jp"),
    ("yakuza", "jp"),
    ("anime", "jp"),
    ("chinois", "cn"),
    ("chine", "cn"),
    ("hong kong", "cn"),
    ("taïwan", "cn"),
    ("tsui hark", "cn"),
]

# Mots-clés dans le synopsis ou le titre confirmant qu'un film de @soonerfrance est bien Coréen, Japonais ou Chinois
SOONER_ASIAN_VERIFY_MARKERS = {
    "kr": [
        "coréen",
        "coréenne",
        "corée",
        "séoul",
        "seoul",
        "busan",
        "bong joon",
        "park chan",
        "song kang-ho",
        "davy chou",
    ],
    "jp": [
        "japon",
        "japonais",
        "japonaise",
        "tokyo",
        "kyoto",
        "osaka",
        "tsukamoto",
        "fukada",
        "miyake",
        "okuyama",
        "kore-eda",
        "hamaguchi",
        "samouraï",
        "samurai",
        "yakuza",
        "hokusai",
        "akira",
        "otom",
        "evangelion",
        "albator",
        "matsumoto",
        "dragon ball",
        "toriyama",
        "ghost in the shell",
        "oshii",
        "conan",
        "satoshi",
        "tetsuo",
        "asako",
        "asada",
        "tempura",
        "kotoko",
    ],
    "cn": [
        "chinois",
        "chinoise",
        "chine",
        "hong kong",
        "hong-kong",
        "taïwan",
        "taiwan",
        "pékin",
        "beijing",
        "shanghai",
        "tsui hark",
        "détective dee",
        "detective dee",
        "moonlight express",
        "initial d",
        "blue sun palace",
        "wuxia",
    ],
}

# Exclusion explicite de films occidentaux remontant par homonymie dans @soonerfrance
SOONER_WESTERN_EXCLUSIONS = [
    "kirikou",
    "petit vampire",
    "chicken run",
    "sing street",
    "9 semaines",
    "serious man",
    "lost in translation",
    "road house",
    "best of the best",
    "chien de la casse",
    "playa de lobos",
    "tschugger",
    "prince ahmed",
    "monde de nathan",
    "banzaï",
    "entre chiens et loups",
    "chevalier mystère",
    "la croisière jaune",
    "reporters",
    "contagion",
    "zweifler",
]


def search_sooner_channel(
    query: str, default_country: str = "jp", min_duration_minutes: int = 40
) -> List[Dict[str, Any]]:
    """
    Recherche exclusivement sur la chaîne payante @soonerfrance de YouTube
    (https://www.youtube.com/@soonerfrance/search?query=...) les films en
    'Visionnage payant' Coréens, Japonais et Chinois.
    """
    url = "https://www.youtube.com/@soonerfrance/search?query=" + urllib.parse.quote(
        query
    )
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "fr-FR,fr;q=0.9",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=7.0) as resp:
            page_html = resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return []

    m = re.search(r"var ytInitialData = (\{.*?\});</script>", page_html)
    if not m:
        return []

    try:
        data = json.loads(m.group(1))
    except Exception:
        return []

    video_renderers: List[Dict[str, Any]] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if "videoRenderer" in node and isinstance(node["videoRenderer"], dict):
                video_renderers.append(node["videoRenderer"])
            else:
                for val in node.values():
                    walk(val)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data)

    raw_candidates: List[Dict[str, Any]] = []
    min_seconds = max(20, min_duration_minutes) * 60

    for vr in video_renderers:
        vid = vr.get("videoId")
        if not vid:
            continue

        title_runs = vr.get("title", {}).get("runs", [])
        title = (
            "".join(r.get("text", "") for r in title_runs).strip()
            or vr.get("title", {}).get("simpleText", "").strip()
        )
        if not title:
            continue

        if any(excl in title.lower() for excl in SOONER_WESTERN_EXCLUSIONS):
            continue

        length_text = vr.get("lengthText", {}).get("simpleText", "")
        dur_seconds = parse_duration_text(length_text)
        if dur_seconds < min_seconds:
            continue

        badges = [
            b.get("metadataBadgeRenderer", {}).get("label", "")
            or b.get("metadataBadgeRenderer", {}).get("style", "")
            for b in vr.get("badges", [])
        ]
        is_paid_badge = any(
            "payant" in b.lower() or "achat" in b.lower() or "louer" in b.lower()
            for b in badges
        )
        if not is_paid_badge:
            continue

        raw_candidates.append(
            {
                "videoId": vid,
                "title": html.unescape(title),
                "durationSeconds": dur_seconds,
                "defaultCountry": default_country,
            }
        )

    verified_sooner: List[Dict[str, Any]] = []

    def inspect_sooner_video(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        vid = item["videoId"]
        exact_date, verified_sub, langs, full_desc = fetch_video_exact_metadata(vid)
        desc_text = full_desc or ""
        combined_low = f"{item['title']} {desc_text}".lower()

        if any(excl in combined_low for excl in SOONER_WESTERN_EXCLUSIONS):
            return None

        # Détermination du pays (Corée, Japon, Chine) à partir du titre et du synopsis officiel Sooner
        detected_country = None
        for c_code in ("kr", "jp", "cn"):
            if any(
                marker in combined_low
                for marker in SOONER_ASIAN_VERIFY_MARKERS[c_code]
            ):
                detected_country = c_code
                break

        if not detected_country:
            # Si la requête était explicitement coréen / japonais / chinois, utilise defaultCountry
            # uniquement si le synopsis ne mentionne pas un pays européen/américain exclusif
            if any(
                w in combined_low
                for w in ["coré", "japon", "chin", "hong kong", "taïwan", "asie", "séoul", "tokyo"]
            ):
                detected_country = item["defaultCountry"]
            elif item["defaultCountry"] in ("kr", "jp", "cn") and not any(
                eu in combined_low
                for eu in ["film américain", "film britannique", "film espagnol", "film italien", "film allemand"]
            ):
                detected_country = item["defaultCountry"]
            else:
                return None

        pub_date = exact_date or "2025-12-15"
        genre = detect_genre(item["title"], desc_text, "drama")

        return {
            "videoId": vid,
            "title": item["title"],
            "koreanTitle": "",
            "country": detected_country,
            "isPaid": True,
            "paidProvider": "Sooner (@soonerfrance)",
            "paidLabel": "Visionnage payant • @soonerfrance",
            "channelName": "SOONER (@soonerfrance)",
            "channelUrl": "https://www.youtube.com/@soonerfrance",
            "channelAvatar": "https://ui-avatars.com/api/?name=SO&background=16a34a&color=fff&bold=true",
            "channelVerified": True,
            "durationSeconds": item["durationSeconds"],
            "viewCount": 18500,
            "publishDate": pub_date,
            "subtitleType": "native_fr",
            "availableLanguages": langs if langs else ["fr (VOSTFR / VF)"],
            "category": genre,
            "description": (
                desc_text[:500]
                if desc_text
                else "Film disponible en visionnage payant (location ou abonnement) sur la chaîne officielle YouTube @soonerfrance avec sous-titres français / VF."
            ),
        }

    if raw_candidates:
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(inspect_sooner_video, c) for c in raw_candidates]
            for fut in concurrent.futures.as_completed(futures):
                try:
                    res = fut.result()
                    if res:
                        verified_sooner.append(res)
                except Exception:
                    pass

    return verified_sooner


def harvest_sooner_movies(min_duration: int = 40) -> int:
    """
    Moissonne tous les films Coréens, Japonais et Chinois en visionnage payant
    sur la chaîne YouTube @soonerfrance et les enregistre dans le cache.
    """
    cache_map = load_cached_movies()
    added = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(search_sooner_channel, q_str, c_code, min_duration)
            for (q_str, c_code) in SOONER_ASIAN_QUERIES
        ]
        for fut in concurrent.futures.as_completed(futures):
            try:
                items = fut.result()
                for item in items:
                    enriched = enrich_movie_fields(item)
                    cache_map[enriched["videoId"]] = enriched
                    added += 1
            except Exception:
                pass
    if added > 0:
        save_cached_movies(cache_map)
    return added


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
    with _CACHE_LOCK:
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(cache_map, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


def harvest_korean_film_channel(min_duration: int = 40) -> int:
    """
    Moissonne l'ensemble des films coréens de la chaîne officielle
    한국고전영화 Korean Classic Film (@KoreanFilm / UCvH6u_Qzn5RQdz9W198umDw).
    """
    cache_map = load_cached_movies()
    discovered_vids: List[str] = []
    seen = set()

    # 1. Onglet Vidéos de @KoreanFilm
    try:
        url = "https://www.youtube.com/youtubei/v1/browse?prettyPrint=false"
        payload = {
            "context": {
                "client": {
                    "hl": "fr",
                    "gl": "FR",
                    "clientName": "WEB",
                    "clientVersion": "2.20241015.01.00",
                }
            },
            "browseId": "UCvH6u_Qzn5RQdz9W198umDw",
            "params": "Egl2aWRlb3PyBgQKAjoA",
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(req, timeout=8.0) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))

            def walk_browse(n: Any) -> None:
                if isinstance(n, dict):
                    if "lockupViewModel" in n:
                        lum = n["lockupViewModel"]
                        cid = lum.get("contentId")
                        if cid and cid not in seen:
                            seen.add(cid)
                            discovered_vids.append(cid)
                    else:
                        for v in n.values():
                            walk_browse(v)
                elif isinstance(n, list):
                    for i in n:
                        walk_browse(i)

            walk_browse(data)
    except Exception:
        pass

    # 2. Recherche interne ciblée sur @KoreanFilm
    queries = [
        "full movie",
        "1960",
        "1970",
        "1980",
        "1990",
        "4K",
        "Im Kwon-taek",
        "Kim Ki-young",
    ]
    for q in queries:
        try:
            ch_url = "https://www.youtube.com/@KoreanFilm/search?query=" + urllib.parse.quote(q)
            req = urllib.request.Request(
                ch_url,
                headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "fr-FR,fr;q=0.9"},
            )
            with urllib.request.urlopen(req, timeout=6.0) as resp:
                ch_html = resp.read().decode("utf-8", errors="ignore")
                matches = re.findall(r'"videoId"\s*:\s*"([a-zA-Z0-9_-]{11})"', ch_html)
                for m_id in matches:
                    if m_id not in seen:
                        seen.add(m_id)
                        discovered_vids.append(m_id)
        except Exception:
            pass

    min_seconds = max(20, min_duration) * 60
    added = 0

    def fetch_kofa_item(video_id: str) -> Optional[Dict[str, Any]]:
        exact_date, verified_sub, langs, full_desc = fetch_video_exact_metadata(video_id)
        try:
            p_url = "https://www.youtube.com/youtubei/v1/player?prettyPrint=false"
            p_payload = {
                "context": {
                    "client": {
                        "hl": "fr",
                        "gl": "FR",
                        "clientName": "WEB",
                        "clientVersion": "2.20241015.01.00",
                    }
                },
                "videoId": video_id,
            }
            p_req = urllib.request.Request(
                p_url,
                data=json.dumps(p_payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
            )
            with urllib.request.urlopen(p_req, timeout=5.0) as p_resp:
                p_data = json.loads(p_resp.read().decode("utf-8", errors="ignore"))
            vd = p_data.get("videoDetails", {})
            title = vd.get("title", "")
            dur_sec = int(vd.get("lengthSeconds", 0))
            views = int(vd.get("viewCount", 25000))
        except Exception:
            return None

        if dur_sec < min_seconds or not title:
            return None

        pub_date = exact_date or "2024-01-01"
        genre = detect_genre(title, full_desc or "", "drama")

        return {
            "videoId": video_id,
            "title": html.unescape(title),
            "koreanTitle": "",
            "country": "kr",
            "countryLabel": "🇰🇷 Corée",
            "channelName": "한국고전영화 Korean Classic Film (@KoreanFilm)",
            "channelUrl": "https://www.youtube.com/@KoreanFilm",
            "channelAvatar": "https://ui-avatars.com/api/?name=KF&background=dc2626&color=fff&bold=true",
            "channelVerified": True,
            "durationSeconds": dur_sec,
            "viewCount": views,
            "publishDate": pub_date,
            "subtitleType": verified_sub or "auto_fr",
            "subtitleLabel": "🇰🇷 Corée • KOFA Officiel",
            "availableLanguages": (
                langs
                if langs
                else ["ko (original)", "Sous-titres intégrés / Auto-traduction FR"]
            ),
            "category": "kofa",
            "description": (
                full_desc[:500]
                if full_desc
                else "Film coréen complet restauré disponible sur la chaîne officielle Korean Film Archive (@KoreanFilm)."
            ),
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(fetch_kofa_item, vid) for vid in discovered_vids]
        for fut in concurrent.futures.as_completed(futures):
            try:
                res = fut.result()
                if res:
                    enriched = enrich_movie_fields(res)
                    cache_map[enriched["videoId"]] = enriched
                    added += 1
            except Exception:
                pass

    if added > 0:
        save_cached_movies(cache_map)

    return added


def harvest_all_countries(min_duration: int = 40) -> int:
    """
    Lance une collecte parallèle sur l'ensemble des requêtes Corée, Japon et Chine
    pour peupler massivement le catalogue (100+ films).
    """
    cache_map = load_cached_movies()
    for seed in SEED_MOVIES:
        cache_map[seed["videoId"]] = enrich_movie_fields(seed)

    queries_to_run: List[Tuple[str, str, str]] = []
    seen_q = set()
    for cat_key in ("all", "kr", "jp", "cn", "thriller", "drama", "horror", "comedy"):
        for q_tuple in CATEGORY_QUERIES.get(cat_key, []):
            if q_tuple[0] not in seen_q:
                seen_q.add(q_tuple[0])
                queries_to_run.append(q_tuple)

    added = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futures = [
            executor.submit(
                search_youtube_innertube,
                q_str,
                def_country,
                def_genre,
                min_duration,
                5,
            )
            for (q_str, def_country, def_genre) in queries_to_run
        ]
        for fut in concurrent.futures.as_completed(futures):
            try:
                items = fut.result()
                for item in items:
                    enriched = enrich_movie_fields(item)
                    cache_map[enriched["videoId"]] = enriched
                    added += 1
            except Exception:
                pass

    save_cached_movies(cache_map)
    return len(cache_map)


def get_movies(
    query: str = "",
    category: str = "all",
    sub_filter: str = "all",
    min_duration: int = 40,
    refresh: bool = False,
) -> Tuple[List[Dict[str, Any]], str]:
    """
    Récupère les films Coréens, Japonais et Chinois depuis YouTube + cache vérifié,
    applique les filtres et trie strictement par date décroissante de publication.
    """
    cache_map = load_cached_movies()

    for seed in SEED_MOVIES:
        vid = seed["videoId"]
        if vid not in cache_map:
            cache_map[vid] = enrich_movie_fields(seed)

    # Normalise tous les films du cache (ajout de country / countryLabel si absent)
    for vid, movie_obj in list(cache_map.items()):
        cache_map[vid] = enrich_movie_fields(movie_obj)

    clean_q = query.strip()
    live_found = 0

    if category == "kofa":
        has_kofa = sum(
            1
            for m in cache_map.values()
            if "@koreanfilm" in m.get("channelUrl", "").lower()
            or m.get("category") == "kofa"
        )
        if refresh or has_kofa < 25:
            live_found = harvest_korean_film_channel(min_duration)
            cache_map = load_cached_movies()
    elif category == "sooner":
        has_sooner = any(m.get("isPaid") for m in cache_map.values())
        if clean_q:
            items = search_sooner_channel(clean_q, "jp", min_duration)
            for item in items:
                enriched = enrich_movie_fields(item)
                cache_map[enriched["videoId"]] = enriched
                live_found += 1
            if live_found > 0:
                save_cached_movies(cache_map)
        elif refresh or not has_sooner:
            live_found = harvest_sooner_movies(min_duration)
            cache_map = load_cached_movies()
    elif clean_q:
        # Recherche directe sur YouTube pour la requête utilisateur (Corée + Japon + Chine + Sooner)
        user_queries = [
            (f"{clean_q} film complet vostfr", "kr", "drama"),
            (f"{clean_q} full movie eng sub", "kr", "drama"),
        ]
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(
                    search_youtube_innertube, sq, ctry, gnr, min_duration, 6
                )
                for (sq, ctry, gnr) in user_queries
            ]
            futures.append(
                executor.submit(search_sooner_channel, clean_q, "jp", min_duration)
            )
            for fut in concurrent.futures.as_completed(futures):
                try:
                    for item in fut.result():
                        enriched = enrich_movie_fields(item)
                        cache_map[enriched["videoId"]] = enriched
                        live_found += 1
                except Exception:
                    pass
        if live_found > 0:
            save_cached_movies(cache_map)
    elif refresh or len(cache_map) < 40:
        # Si actualisation demandée ou cache encore petit, lance les requêtes de la catégorie
        q_list = CATEGORY_QUERIES.get(category, CATEGORY_QUERIES["all"])
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(
                    search_youtube_innertube, sq, ctry, gnr, min_duration, 5
                )
                for (sq, ctry, gnr) in q_list
            ]
            for fut in concurrent.futures.as_completed(futures):
                try:
                    for item in fut.result():
                        enriched = enrich_movie_fields(item)
                        cache_map[enriched["videoId"]] = enriched
                        live_found += 1
                except Exception:
                    pass
        if live_found > 0:
            save_cached_movies(cache_map)

    # ÉLIMINATION STRICTE ET DÉFINITIVE DE TOUT FILM AMÉRICAIN OU OCCIDENTAL
    all_movies = [
        m
        for m in cache_map.values()
        if is_strictly_asian_movie(
            m.get("title", ""), m.get("channelName", ""), m.get("description", "")
        )
    ]

    # 1. Filtre durée minimale
    min_sec = max(20, min_duration) * 60
    filtered = [m for m in all_movies if m.get("durationSeconds", 0) >= min_sec]

    # 2. Filtre par catégorie ou par pays ('sooner', 'kr', 'jp', 'cn', 'kofa', 'native', genres)
    if category and category not in ("all", "recent"):
        if category == "sooner":
            filtered = [
                m
                for m in filtered
                if m.get("isPaid")
                or "sooner" in m.get("channelName", "").lower()
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

    # 3. Filtre sous-titres FR ('native' vs 'all')
    if sub_filter == "native":
        filtered = [m for m in filtered if m.get("subtitleType") == "native_fr"]

    # 4. Filtre recherche texte libre
    if clean_q:
        q_words = [w.lower() for w in clean_q.split() if w.strip()]
        q_matched = []
        for m in filtered:
            haystack = (
                f"{m.get('title', '')} {m.get('koreanTitle', '')} "
                f"{m.get('channelName', '')} {m.get('description', '')} "
                f"{m.get('countryLabel', '')} {m.get('category', '')}"
            ).lower()
            if all(w in haystack for w in q_words) or any(
                w in haystack for w in q_words
            ):
                q_matched.append(m)
        filtered = q_matched

    # 5. TRI STRICT PAR DATE DÉCROISSANTE DE PUBLICATION
    filtered.sort(
        key=lambda m: (
            m.get("publishedTimestamp", 0),
            m.get("publishDate", ""),
            m.get("viewCount", 0),
        ),
        reverse=True,
    )

    source_label = "youtube_live" if live_found > 0 else "youtube_cache"
    return filtered, source_label


class KCineTubeHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[AsieCinéTube] {self.address_string()} - {fmt % args}")

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/movies":
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

            # Compteurs par pays pour l'interface
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
            self.end_headers()
            self.wfile.write(response_body)
            return

        if parsed.path == "/" or parsed.path == "":
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
        save_cached_movies(cache_map)

    # 1. Purge immédiate de tout film occidental / américain présent dans le cache existant
    purged_cache = {
        vid: m
        for vid, m in cache_map.items()
        if is_strictly_asian_movie(
            m.get("title", ""), m.get("channelName", ""), m.get("description", "")
        )
    }
    if len(purged_cache) != len(cache_map):
        print(
            f"🧹 Cache nettoyé : {len(cache_map) - len(purged_cache)} film(s) américain(s) ou hors-sujet purgé(s)."
        )
        save_cached_movies(purged_cache)
        cache_map = purged_cache

    # 2. Moissonnage initial de la chaîne officielle @KoreanFilm si pas encore en cache
    kofa_count = sum(
        1
        for m in cache_map.values()
        if "@koreanfilm" in m.get("channelUrl", "").lower()
        or m.get("category") == "kofa"
    )
    if kofa_count < 25:
        print("🎬 Indexation des films de la chaîne officielle @KoreanFilm (KOFA)...")
        harvest_korean_film_channel(40)

    with ThreadedHTTPServer(("0.0.0.0", PORT), KCineTubeHandler) as httpd:
        print(
            f"🎬 AsieCinéTube FR (Corée • Japon • Chine • @KoreanFilm • Sooner) démarré sur http://localhost:{PORT}"
        )
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nArrêt du serveur.")


if __name__ == "__main__":
    main()
