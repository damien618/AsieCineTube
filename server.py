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
    """Vérifie qu'un film est bien asiatique et élimine tout film américain ou occidental."""
    combined = f"{title} {channel} {description}".lower()

    if any(excl in combined for excl in WESTERN_EXCLUSIONS_LIST):
        return False

    if any(spam in combined for spam in SPAM_EXCLUSION_KEYWORDS):
        return False

    has_hangul = bool(re.search(r"[\uac00-\ud7a3]", f"{title} {channel}"))
    has_kana = bool(re.search(r"[\u3040-\u309f\u30a0-\u30ff]", f"{title} {channel}"))
    has_hanzi = bool(re.search(r"[\u4e00-\u9fff]", f"{title} {channel}"))

    if has_hangul or has_kana or has_hanzi:
        return True

    ch_low = channel.lower()
    if any(vc in ch_low for vc in VERIFIED_ASIAN_CHANNELS):
        return True

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
    country = raw.get("country") or detect_country(
        title, channel_name, description, "kr"
    )
    country_label = COUNTRY_LABELS.get(country, "🇰🇷 Corée")
    category = raw.get("category") or detect_genre(title, description, "drama")
    if category in ("all", "kr", "jp", "cn", "recent", "native"):
        category = detect_genre(title, description, "drama")

    is_kofa = (
        "@koreanfilm" in raw.get("channelUrl", "").lower()
        or "@koreanfilm" in channel_name.lower()
        or "korean classic film" in channel_name.lower()
        or category == "kofa"
    )
    if is_kofa:
        category = "kofa"
        sub_type = "auto_fr"
        sub_label = "🇰🇷 Corée • KOFA (Trad. Auto YT)"
    elif raw.get("isPaid"):
        sub_type = "native_fr"
        sub_label = f"{country_label} • Payant (Sooner)"
    elif sub_type == "native_fr":
        sub_label = f"{country_label} • ST-FR Natif"
    else:
        sub_label = f"{country_label} • ST-FR Auto"

    return {
        "videoId": vid,
        "title": title,
        "koreanTitle": raw.get("koreanTitle", ""),
        "country": country,
        "countryLabel": country_label,
        "isPaid": bool(raw.get("isPaid", False)),
        "paidProvider": raw.get("paidProvider", ""),
        "paidLabel": raw.get(
            "paidLabel", "Visionnage payant" if raw.get("isPaid") else ""
        ),
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
        "subtitleLabel": sub_label,
        "availableLanguages": raw.get(
            "availableLanguages",
            ["fr"] if sub_type == "native_fr" else ["en", "fr (auto)"],
        ),
        "category": category,
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
    """Sauvegarde à la fois le cache local et 'movies.json' pour GitHub Pages."""
    with _CACHE_LOCK:
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(cache_map, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        # Export statique pour GitHub Pages
        try:
            movies_list = list(cache_map.values())
            # Élimination stricte des films américains ou non asiatiques
            movies_list = [
                m
                for m in movies_list
                if is_strictly_asian_movie(
                    m.get("title", ""),
                    m.get("channelName", ""),
                    m.get("description", ""),
                )
            ]
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

            with open(STATIC_EXPORT_FILE, "w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            print(
                f"✅ Export statique GitHub Pages généré : {STATIC_EXPORT_FILE} ({len(movies_list)} films)"
            )
        except Exception as e:
            print("Erreur export statique GitHub Pages:", e)


def get_movies(
    query: str = "",
    category: str = "all",
    sub_filter: str = "all",
    min_duration: int = 40,
    refresh: bool = False,
) -> Tuple[List[Dict[str, Any]], str]:
    cache_map = load_cached_movies()

    for seed in SEED_MOVIES:
        vid = seed["videoId"]
        if vid not in cache_map:
            cache_map[vid] = enrich_movie_fields(seed)

    for vid, movie_obj in list(cache_map.items()):
        cache_map[vid] = enrich_movie_fields(movie_obj)

    clean_q = query.strip()
    all_movies = list(cache_map.values())

    # Élimination stricte des films américains / occidentaux
    all_movies = [
        m
        for m in all_movies
        if is_strictly_asian_movie(
            m.get("title", ""), m.get("channelName", ""), m.get("description", "")
        )
    ]

    min_sec = max(20, min_duration) * 60
    filtered = [m for m in all_movies if m.get("durationSeconds", 0) >= min_sec]

    if category and category not in ("all", "recent"):
        if category == "sooner":
            filtered = [
                m
                for m in filtered
                if m.get("isPaid") or "sooner" in m.get("channelName", "").lower()
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
                f"{m.get('countryLabel', '')} {m.get('category', '')}"
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
