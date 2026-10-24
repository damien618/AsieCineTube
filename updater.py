#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AsieCinéTube FR — Moissonneur Automatique de Films Asiatiques sur YouTube
Ce script recherche les nouveaux films complets coréens, japonais et chinois
sur YouTube (avec sous-titres FR natifs ou auto-traduits) et met à jour
directement 'cache_movies.json' et 'movies.json'.

Conçu pour s'exécuter en local ou automatiquement via GitHub Actions.
"""

import concurrent.futures
import datetime
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Set, Tuple

import server

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(BASE_DIR, "cache_movies.json")
STATIC_EXPORT_FILE = os.path.join(BASE_DIR, "movies.json")

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36"
)

# Requêtes ciblées pour trouver des films asiatiques complets avec sous-titres FR
SEARCH_QUERIES = [
    # 🇰🇷 Corée du Sud
    ("film coréen complet en français", "kr", "thriller"),
    ("film coréen vostfr complet", "kr", "drama"),
    ("korean movie full french subtitles", "kr", "drama"),
    ("film sud coréen complet vostfr", "kr", "thriller"),
    ("korean classic film kofa vostfr", "kr", "kofa"),
    ("korean movie english subtitles full", "kr", "drama"),
    # 🇯🇵 Japon
    ("film japonais complet vostfr", "jp", "thriller"),
    ("film japonais vostfr complet", "jp", "drama"),
    ("film samourai complet vostfr", "jp", "thriller"),
    ("japanese movie full french subtitles", "jp", "drama"),
    ("film yakuza complet vostfr", "jp", "thriller"),
    # 🇨🇳 Chine / Hong-Kong / Taïwan
    ("film chinois complet vostfr", "cn", "thriller"),
    ("film arts martiaux vostfr complet", "cn", "thriller"),
    ("film kung fu complet en français", "cn", "thriller"),
    ("chinese movie full french sub", "cn", "drama"),
    ("film wuxia complet vostfr", "cn", "thriller"),
    # 🟢 Chaîne payante Sooner France
    ("@soonerfrance film coréen", "kr", "sooner"),
    ("@soonerfrance film japonais", "jp", "sooner"),
    ("@soonerfrance film chinois", "cn", "sooner"),
]


def fetch_video_exact_metadata(video_id: str) -> Tuple[Optional[str], Optional[str], List[str]]:
    """Récupère la date exacte YYYY-MM-DD et les pistes de sous-titres d'une vidéo YouTube."""
    url = f"https://www.youtube.com/watch?v={video_id}&hl=fr"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            page_html = resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return None, None, []

    publish_date = None
    m_date = re.search(r'"(?:publishDate|uploadDate)"\s*:\s*"(\d{4}-\d{2}-\d{2})', page_html)
    if m_date:
        publish_date = m_date.group(1)

    langs: List[str] = []
    sub_type: Optional[str] = None
    m_tracks = re.search(r'"captionTracks"\s*:\s*(\[[^\]]+\])', page_html)
    if m_tracks:
        tracks_raw = m_tracks.group(1)
        lang_codes = re.findall(r'"languageCode"\s*:\s*"([^"]+)"', tracks_raw)
        is_translatable = '"isTranslatable":true' in tracks_raw
        langs = list(dict.fromkeys(lang_codes))
        if any(code.startswith("fr") for code in langs):
            sub_type = "native_fr"
        elif langs and is_translatable:
            sub_type = "auto_fr"
            if "fr (auto)" not in langs:
                langs.append("fr (auto)")
        elif langs:
            sub_type = "auto_fr"

    return publish_date, sub_type, langs


def search_youtube_innertube(
    query: str,
    default_country: str = "kr",
    default_genre: str = "drama",
    min_duration_minutes: int = 40,
) -> List[Dict[str, Any]]:
    """
    Interroge l'API interne YouTube (InnerTube /youtubei/v1/search)
    avec filtre de vidéos longues (> 20 min).
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
        "params": "EgIYAg%3D%3D",  # Filtre vidéos longues
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
        with urllib.request.urlopen(req, timeout=8.0) as resp:
            result = json.loads(resp.read().decode("utf-8", errors="ignore"))
    except Exception as e:
        print(f"⚠️ Erreur recherche pour '{query}': {e}")
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
        title = " ".join([r.get("text", "") for r in title_runs]).strip()
        if not title:
            title = vr.get("title", {}).get("simpleText", "")

        owner_runs = vr.get("ownerText", {}).get("runs", [])
        channel_name = owner_runs[0].get("text", "") if owner_runs else ""
        nav_url = (
            owner_runs[0]
            .get("navigationEndpoint", {})
            .get("commandMetadata", {})
            .get("webCommandMetadata", {})
            .get("url", "")
            if owner_runs
            else ""
        )
        channel_url = (
            f"https://www.youtube.com{nav_url}"
            if nav_url.startswith("/")
            else f"https://www.youtube.com/watch?v={vid}"
        )

        ch_thumbs = (
            vr.get("channelThumbnailSupportedRenderers", {})
            .get("channelThumbnailWithLinkRenderer", {})
            .get("thumbnail", {})
            .get("thumbnails", [])
        )
        channel_avatar = ch_thumbs[0].get("url", "") if ch_thumbs else ""

        owner_badges = vr.get("ownerBadges", [])
        channel_verified = any(
            "VERIFIED" in b.get("metadataBadgeRenderer", {}).get("style", "")
            for b in owner_badges
            if isinstance(b, dict)
        )

        desc_runs = vr.get("detailedMetadataSnippets", [{}])[0].get("snippetText", {}).get("runs", [])
        description = " ".join([r.get("text", "") for r in desc_runs]).strip()

        # Filtrage strict : éliminer les films occidentaux et le spam
        if not server.is_strictly_asian_movie(title, channel_name, description):
            continue

        # Vérification durée
        dur_text = vr.get("lengthText", {}).get("simpleText", "")
        dur_sec = server.parse_duration_text(dur_text)
        if dur_sec < min_seconds:
            continue

        views_text = vr.get("viewCountText", {}).get("simpleText", "")
        views = server.parse_view_count(views_text)

        pub_rel = vr.get("publishedTimeText", {}).get("simpleText", "")
        pub_date = server.parse_relative_time_to_iso(pub_rel)

        fallback_genre = "drama" if default_genre == "sooner" else default_genre
        detected_c = server.detect_country(title, channel_name, description, default_country)
        detected_g = server.detect_genre(title, description, fallback_genre)

        # Un film n'appartient à Sooner que si la chaîne YouTube est réellement Sooner
        is_sooner = "sooner" in channel_name.lower() or "@soonerfrance" in channel_url.lower()

        candidates.append({
            "videoId": vid,
            "title": title,
            "channelName": "SOONER (@soonerfrance)" if is_sooner else channel_name,
            "channelUrl": "https://www.youtube.com/@soonerfrance" if is_sooner else channel_url,
            "channelAvatar": (
                "https://ui-avatars.com/api/?name=SO&background=16a34a&color=fff&bold=true"
                if is_sooner and not channel_avatar
                else channel_avatar
            ),
            "channelVerified": True if is_sooner else channel_verified,
            "description": description,
            "durationSeconds": dur_sec,
            "viewCount": views,
            "publishDate": pub_date,
            "country": detected_c,
            "category": detected_g,
            "isPaid": is_sooner,
            "paidProvider": "Sooner (@soonerfrance)" if is_sooner else "",
            "paidLabel": "Visionnage payant • @soonerfrance" if is_sooner else "",
            "subtitleType": "native_fr" if is_sooner else "auto_fr",
        })

    return candidates


def harvest_korean_film_archive() -> List[Dict[str, Any]]:
    """Moissonne les films coréens de la chaîne officielle KOFA (@KoreanFilm)."""
    print("🏛️ Exploration de la chaîne KOFA (@KoreanFilm)...")
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
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
    )

    kofa_movies = []
    try:
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))

        renderers = []
        def walk(n: Any):
            if isinstance(n, dict):
                if "videoRenderer" in n:
                    renderers.append(n["videoRenderer"])
                elif "lockupViewModel" in n:
                    cid = n["lockupViewModel"].get("contentId")
                    if cid:
                        renderers.append({"videoId": cid})
                for v in n.values():
                    walk(v)
            elif isinstance(n, list):
                for item in n:
                    walk(item)

        walk(data)

        for r in renderers[:15]:
            vid = r.get("videoId")
            if vid:
                kofa_movies.append({
                    "videoId": vid,
                    "title": "Korean Classic Film",
                    "channelName": "한국고전영화 Korean Classic Film (@KoreanFilm)",
                    "channelUrl": "https://www.youtube.com/@KoreanFilm",
                    "country": "kr",
                    "category": "kofa",
                    "subtitleType": "auto_fr",
                })
    except Exception as e:
        print(f"⚠️ Erreur lors de l'accès à KOFA: {e}")

    return kofa_movies


def run_harvest() -> Tuple[int, int]:
    """
    Exécute la collecte globale sur YouTube, enrichit les métadonnées
    et met à jour cache_movies.json et movies.json.
    """
    print("🚀 Démarrage de la mise à jour AsieCinéTube...")
    cache_map = server.load_cached_movies()
    initial_count = len(cache_map)
    print(f"📦 Films actuellement en cache : {initial_count}")

    # 1. Collecte parallèle de toutes les requêtes
    all_discovered: List[Dict[str, Any]] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        future_to_query = {
            executor.submit(search_youtube_innertube, q, c, g): q
            for q, c, g in SEARCH_QUERIES
        }
        future_kofa = executor.submit(harvest_korean_film_archive)

        for future in concurrent.futures.as_completed(future_to_query):
            q_name = future_to_query[future]
            try:
                results = future.result()
                print(f"  ✓ Requête '{q_name}' : {len(results)} films trouvés")
                all_discovered.extend(results)
            except Exception as e:
                print(f"  ✗ Erreur sur '{q_name}': {e}")

        try:
            kofa_res = future_kofa.result()
            print(f"  ✓ KOFA (@KoreanFilm) : {len(kofa_res)} films trouvés")
            all_discovered.extend(kofa_res)
        except Exception as e:
            print(f"  ✗ Erreur sur KOFA: {e}")

    # 2. Filtrer les vidéos déjà connues pour économiser les requêtes de métadonnées
    new_candidates = [m for m in all_discovered if m["videoId"] not in cache_map]
    print(f"✨ Nouveaux films potentiels découverts : {len(new_candidates)}")

    # 3. Enrichir les métadonnées exactes des nouveaux films
    def enrich_candidate(cand: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        vid = cand["videoId"]
        pub_date, sub_type, langs = fetch_video_exact_metadata(vid)
        if pub_date:
            cand["publishDate"] = pub_date
        if sub_type:
            cand["subtitleType"] = sub_type
        if langs:
            cand["availableLanguages"] = langs
        return server.enrich_movie_fields(cand)

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        enriched_list = list(executor.map(enrich_candidate, new_candidates[:30]))

    added_count = 0
    for movie in enriched_list:
        if movie and movie.get("videoId"):
            cache_map[movie["videoId"]] = movie
            added_count += 1

    # 4. Sauvegarder les fichiers JSON
    server.save_cached_movies(cache_map)
    final_count = len(cache_map)

    print("\n" + "=" * 50)
    print(f"✅ Mise à jour terminée !")
    print(f"   • Nouveaux films ajoutés : {added_count}")
    print(f"   • Total des films du catalogue : {final_count}")
    print(f"   • Fichiers mis à jour : cache_movies.json, movies.json")
    print("=" * 50 + "\n")

    return added_count, final_count


if __name__ == "__main__":
    added, total = run_harvest()
    sys.exit(0)
