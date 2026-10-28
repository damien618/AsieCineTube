#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Adversarial Stress Test Suite for Milestone 1 (server.py)
Empirical verification across 5 challenge dimensions:
1. Excluded channels adversarial variations (casing, whitespace, url encoding, accents, spaceless handles)
2. Adversarial B-movie titles & short-drama clickbait detection
3. False-positive resistance (YouTube hash IDs, common family names, substrings)
4. Legitimate auteur martial arts / action films preservation & enrichment
5. 100% preservation of KOFA classics and SOONER catalog titles
"""

import json
import os
import re
import sys
import unittest
import urllib.parse

# Ensure repository root is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import server


class TestAdversarialExcludedChannels(unittest.TestCase):
    """Dimension 1: Adversarial variations of excluded channels."""

    def test_casing_variations(self):
        """Upper, lower, and mixed case variations of excluded channels must be rejected."""
        channels = [
            ("SAMURAI VS NINJA", "https://youtube.com/c/samuraivsninja"),
            ("sAmUrAi Vs NiNjA", "https://youtube.com/c/samuraivsninja"),
            ("MARTIAL ARTS THEATER", "https://youtube.com/@MartialArtsTheater"),
            ("mArTiAl ArTs ThEaTeR", "https://youtube.com/@MartialArtsTheater"),
            ("IQIYI ACTION", "https://youtube.com/@iqiyiaction"),
            ("iQiYi AcTiOn", "https://youtube.com/@iqiyiaction"),
            ("CINÉ NANAR", "https://youtube.com/@cinenanar"),
            ("cInÉ nAnAr", "https://youtube.com/@cinenanar"),
            ("CINE NANAR", "https://youtube.com/@cinenanar"),
            ("CHINESE ONLINE MOVIE CHANNEL", "https://youtube.com/@chineseonlinemoviechannel"),
            ("SHAW BROTHERS CINEMA", "https://youtube.com/@shawbrotherscinema"),
            ("ALLOCINÉ FILMS COMPLETS", "https://youtube.com/@allocine"),
            ("ALLOCINE FILMS COMPLETS", "https://youtube.com/@allocine"),
            ("SBS CATCH", "https://youtube.com/@sbscatch"),
            ("KBS DRAMA", "https://youtube.com/@kbsdrama"),
            ("FRENCH ACTION HUB", "https://youtube.com/@frenchactionhub"),
            ("THE BEST OF ACTION", "https://youtube.com/@thebestofaction"),
        ]
        for name, url in channels:
            with self.subTest(channel=name):
                res = server.is_strictly_asian_movie(
                    title="Classic Film 1980 (한국 영화)",
                    channel=name,
                    description="Korean drama film",
                    channel_url=url,
                )
                self.assertFalse(res, f"Channel '{name}' should be rejected despite casing.")

    def test_whitespace_variations(self):
        """Trailing, leading spaces, tabs, and newlines in channel names must be rejected."""
        variations = [
            "  samurai vs ninja  ",
            "\tsamurai vs ninja\n",
            "   martial arts theater   ",
            "\t\nciné nanar\r\n",
            "  iqiyi action  ",
            "   shaw brothers cinema   ",
            "  양파극장  ",
            " \tchinese online movie channel\t ",
        ]
        for ch in variations:
            with self.subTest(channel=repr(ch)):
                res = server.is_strictly_asian_movie(
                    title="Asian Film (한국)",
                    channel=ch,
                    description="Drama",
                    channel_url="https://youtube.com/@channel",
                )
                self.assertFalse(res, f"Whitespace padded channel '{ch}' should be rejected.")

    def test_url_encoded_handles(self):
        """Percent-encoded channel handles and names must be unquoted and rejected."""
        encoded_cases = [
            ("양파극장", "%EC%96%91%ED%8C%8C%EA%B7%B9%EC%9E%A5", "https://youtube.com/@%EC%96%91%ED%8C%8C%EA%B7%B9%EC%9E%A5"),
            ("浪子走天下", "%E6%B5%AA%E5%AD%90%E8%B5%B0%E5%A4%A9%E4%B8%8B", "https://youtube.com/@%E6%B5%AA%E5%AD%90%E8%B5%B0%E5%A4%A9%E4%B8%8B"),
            ("武道劇場", "%E6%AD%A6%E9%81%93%E5%8A%87%E5%A0%B4", "https://youtube.com/@%E6%AD%A6%E9%81%93%E5%8A%87%E5%A0%B4"),
            ("글로리 시어터", "%EA%B8%80%EB%A1%9C%EB%A6%AC%20%EC%8B%9C%EC%96%B4%ED%84%B0", "https://youtube.com/@glory"),
            ("ciné nanar", "%43%69%6e%c3%a9%20%4e%61%6e%61%72", "https://youtube.com/@cinenanar"),
            ("samurai vs ninja", "%73%61%6d%75%72%61%69%20%76%73%20%6e%69%6e%6a%61", "https://youtube.com/@samurai"),
        ]
        for original, enc_name, enc_url in encoded_cases:
            with self.subTest(channel=original):
                res = server.is_strictly_asian_movie(
                    title="Authentic Asian Movie (한국 영화)",
                    channel=enc_name,
                    description="Korean classic movie",
                    channel_url=enc_url,
                )
                self.assertFalse(res, f"URL-encoded channel '{enc_name}' should be rejected.")

    def test_accent_variations(self):
        """Accent variations of French channels (ciné/cine nanar, allociné/allocine) must both be rejected."""
        pairs = [
            ("ciné nanar", "https://youtube.com/@cinenanar"),
            ("cine nanar", "https://youtube.com/@cinenanar"),
            ("allociné films complets", "https://youtube.com/@allocine"),
            ("allocine films complets", "https://youtube.com/@allocine"),
        ]
        for name, url in pairs:
            with self.subTest(channel=name):
                res = server.is_strictly_asian_movie(
                    title="Grand Film Asiatique (Japon)",
                    channel=name,
                    description="Film complet en VF",
                    channel_url=url,
                )
                self.assertFalse(res, f"Channel '{name}' must be rejected.")

    def test_spaceless_channel_handle_urls(self):
        """Spaceless channel handle URLs (e.g. @cinenanar, @chineseonlinemoviechannel) must be excluded even if channelName is generic."""
        handles = [
            ("https://www.youtube.com/@cinenanar", "ciné nanar"),
            ("https://www.youtube.com/@chineseonlinemoviechannel", "chinese online movie channel"),
            ("https://www.youtube.com/@martialartstheater", "martial arts theater"),
            ("https://www.youtube.com/@iqiyiaction", "iqiyi action"),
            ("https://www.youtube.com/@shawbrotherscinema", "shaw brothers cinema"),
        ]
        for url, ec_name in handles:
            with self.subTest(handle=url):
                res = server.is_strictly_asian_movie(
                    title="Classic Drama 1975 (한국 영화)",
                    channel="Asian Film Vault",
                    description="Korean drama classic",
                    channel_url=url,
                )
                self.assertFalse(res, f"Channel handle '{url}' ({ec_name}) must be rejected even with generic channelName.")


class TestAdversarialBMovieTitlesAndClickbait(unittest.TestCase):
    """Dimension 2: Adversarial B-movie titles and clickbaits."""

    def test_adversarial_bmovie_titles(self):
        """B-movie titles must be rejected even with Asian markers or scripts if non-auteur."""
        bmovie_cases = [
            ("Super Kung Fu Ninja 2024", "Action Cinema", "Epic battle of warriors"),
            ("Shaolin Master vs Wuxia Warrior", "Martial World", "Ancient Chinese clash"),
            ("The Drunken Fist Champion", "Asia Hub", "Martial arts combat in Hong Kong"),
            ("Sword King: The Unbeatable Hermit's Sword", "Eastern Action", "Costume drama wuxia swordplay"),
            ("Super Kung Fu Ninja 2024 (슈퍼 닌자)", "Random Channel", "Korean subtitles"),
            ("Shaolin Master vs Wuxia Warrior (功夫大师)", "Random Channel", "Chinese subtitles"),
            ("Ninja Revenge 1985 (ニンジャ)", "Japanese Hub", "Tokyo action movie"),
            ("Police vs Gansters: Action Supercut", "HK Movies", "Hong Kong police action"),
            ("무협 액션 대작: 신의 검 (Epic Wuxia Action)", "Action KR", "Full movie"),
            ("Drunken Fist & Shaolin Poing Ivre", "Cinema Martial", "French dubbed martial arts"),
        ]
        for title, channel, desc in bmovie_cases:
            with self.subTest(title=title):
                res = server.is_strictly_asian_movie(
                    title=title,
                    channel=channel,
                    description=desc,
                    channel_url="https://youtube.com/@random",
                )
                self.assertFalse(res, f"B-movie title '{title}' must be rejected.")

    def test_short_drama_and_clickbait(self):
        """Short-dramas, binge summaries, and recap spam must be rejected."""
        spam_cases = [
            ("[160분요약] 대부호의 숨겨진 아내", "드라마몰아보기", "결말포함 160분요약"),
            ("[통합본] 재벌 3세와의 정략결혼 숏드라마", "쇼츠드라마", "정략결혼 풀버전"),
            ("女社長の秘密と愛 (短剧 全集)", "日本ドラマ", "短剧 女社長"),
            ("神医 下山 逆襲 短剧 (全集)", "中国剧场", "神医 逆襲"),
            ("스릴러 액션 영화 제이슨 스타뎀 주연", "영화채널", "제이슨 스타뎀"),
            ("병맛자막 영화리뷰 결말포함", "영화리뷰", "병맛자막 영화 리뷰"),
            ("The Billionaire CEO's Secret Love (Short Drama)", "Vertical Hub", "Mini drama billionaire"),
            ("Alpha Wolf Mafia Boss (Vertical Drama)", "Pocket Series", "Vertical drama full"),
        ]
        for title, channel, desc in spam_cases:
            with self.subTest(title=title):
                res = server.is_strictly_asian_movie(
                    title=title,
                    channel=channel,
                    description=desc,
                    channel_url="https://youtube.com/@random",
                )
                self.assertFalse(res, f"Clickbait/spam title '{title}' must be rejected.")


class TestFalsePositiveResistance(unittest.TestCase):
    """Dimension 3: False-positive resistance (hashes, URLs, common family names)."""

    def test_youtube_video_ids_with_https_protocol(self):
        """YouTube video IDs/hashes in full HTTPS URLs must NEVER trigger auteur match."""
        hashes = [
            "https://youtu.be/gil_9u4oZuI",
            "https://youtu.be/xxx_oZu_yyy",
            "https://www.youtube.com/watch?v=gil_9u4oZuI",
            "https://youtu.be/abc_kurosawa_xyz",
            "https://youtu.be/test_bong_123",
            "https://youtu.be/sample_lee_456",
            "https://youtu.be/vid_kitano_999",
            "https://youtu.be/mizoguchi_hash_77",
            "https://youtu.be/miike_film_001",
        ]
        for url in hashes:
            with self.subTest(url=url):
                director = server.detect_auteur(url)
                self.assertIsNone(director, f"URL hash '{url}' falsely identified as auteur '{director}'.")

    def test_schemeless_youtube_video_ids_and_domains(self):
        """Schemeless YouTube video URLs (youtu.be/..., www.youtube.com/...) must NOT trigger false positives."""
        schemeless_urls = [
            "youtu.be/gil-ozu-xyz",
            "youtu.be/abc-oZu-def",
            "www.youtube.com/watch?v=abc-ozu-def",
            "youtube.com/vi/123-ozu-456",
            "Check out youtu.be/abc-oZu-def for more details",
        ]
        for text in schemeless_urls:
            with self.subTest(text=text):
                director = server.detect_auteur(text)
                self.assertIsNone(director, f"Schemeless URL '{text}' falsely identified as auteur '{director}'.")

    def test_bmovie_with_schemeless_url_hash_not_whitelisted(self):
        """A B-movie mentioning a schemeless URL containing '-ozu-' must NOT be accepted as Ozu."""
        title = "Super Kung Fu Ninja 2024"
        channel = "Action Hub"
        desc = "Full martial arts action movie. See also: youtu.be/abc-ozu-def"
        channel_url = "https://youtube.com/@actionhub"
        
        is_asian = server.is_strictly_asian_movie(title, channel, desc, channel_url)
        self.assertFalse(is_asian, "B-movie with schemeless URL hash must NOT be whitelisted as Ozu.")
        
        is_auteur, auteur_label = server.detect_auteur_label(title, channel, desc, channel_url)
        self.assertFalse(is_auteur, "B-movie with schemeless URL hash must NOT be marked isAuteur=True.")

    def test_common_family_names_without_director_context(self):
        """Common surnames ('famille Kobayashi', 'Docteur Lee', 'Mister Park') must NOT match as auteur."""
        false_positive_names = [
            "la famille Kobayashi passe des vacances au village",
            "Hospitalité : la famille Kobayashi et leurs voisins",
            "Docteur Lee consulte ses patients à Séoul",
            "Dr. Lee et l'équipe médicale de Busan",
            "Mister Park arrive au bureau de Gangnam",
            "Monsieur Park et Madame Kim discutent",
            "Madame Kim prépare le repas traditionnel",
            "Chef Wang cuisine à Pékin",
            "Professeur Zhang enseigne la calligraphie",
            "L'inspecteur Chen enquête sur le cambriolage",
            "Maître Yang pratique la méditation",
            "Général Hu commande les troupes de la frontière",
            "Agent To surveille le quartier de Kowloon",
            "Capitaine Chan patrouille dans le port",
            "Le président Suzuki annonce les résultats financiers",
            "Mademoiselle Kawase chante dans la chorale",
            "L'écrivain Iwai publie son nouveau roman",
            "Kon et ses amis jouent au football",
            "Hosoda travaille dans l'atelier familial",
            "Shindo visite le temple de Kyoto",
        ]
        for phrase in false_positive_names:
            with self.subTest(phrase=phrase):
                director = server.detect_auteur(phrase)
                self.assertIsNone(director, f"Phrase '{phrase}' falsely identified as auteur '{director}'.")

    def test_non_director_substring_collisions(self):
        """Substrings containing letters of directors must not falsely match."""
        substring_cases = [
            "Kozushima",  # Contains 'ozu'
            "Kozushima Island travel documentary",
            "Bongo drums and music festival",  # Contains 'bong'
            "Underground parking in Gangnam",  # Contains 'park'
            "Camping trip in Hokkaido",  # Contains 'kim'
            "Hokkaido winter landscape",
            "Kozuki clan history",
        ]
        for phrase in substring_cases:
            with self.subTest(phrase=phrase):
                director = server.detect_auteur(phrase)
                self.assertIsNone(director, f"Substring '{phrase}' falsely identified as auteur '{director}'.")


class TestAuteurMartialArtsPreservation(unittest.TestCase):
    """Dimension 4: Legitimate auteur films with martial arts or action themes."""

    def test_seven_samurai_kurosawa(self):
        """Akira Kurosawa's Seven Samurai must be accepted and marked as auteur."""
        title = "Seven Samurai (七人の侍, 1954) — Akira Kurosawa"
        channel = "Toho Classic Cinema"
        desc = "Chef-d'œuvre absolu d'Akira Kurosawa avec Toshiro Mifune. Film de sabre et d'arts martiaux."
        
        is_asian = server.is_strictly_asian_movie(title, channel, desc)
        self.assertTrue(is_asian, "Seven Samurai must be accepted despite 'arts martiaux'.")
        
        enriched = server.enrich_movie_fields({
            "videoId": "kurosawa_7sam",
            "title": title,
            "channelName": channel,
            "description": desc,
        })
        self.assertTrue(enriched["isAuteur"], "Seven Samurai must have isAuteur=True.")
        self.assertEqual(enriched["auteurLabel"], "🎬 Akira Kurosawa")

    def test_harakiri_masaki_kobayashi(self):
        """Masaki Kobayashi's Harakiri (Seppuku) must be accepted and marked as auteur."""
        title = "Harakiri (切腹, 1962) — Masaki Kobayashi"
        channel = "Shochiku Classics"
        desc = "Film de sabre et d'arts martiaux réalisé par Masaki Kobayashi. Prix spécial du Jury Festival de Cannes 1963."
        
        is_asian = server.is_strictly_asian_movie(title, channel, desc)
        self.assertTrue(is_asian, "Harakiri must be accepted despite 'arts martiaux'.")
        
        enriched = server.enrich_movie_fields({
            "videoId": "kobayashi_harakiri",
            "title": title,
            "channelName": channel,
            "description": desc,
        })
        self.assertTrue(enriched["isAuteur"], "Harakiri must have isAuteur=True.")
        self.assertEqual(enriched["auteurLabel"], "🎬 Masaki Kobayashi")

    def test_detective_dee_ii_tsui_hark(self):
        """Tsui Hark's Détective Dee II must be accepted and marked as auteur."""
        title = "Détective Dee II : La Légende du Dragon des Mers — Tsui Hark"
        channel = "SOONER (@soonerfrance)"
        channel_url = "https://www.youtube.com/@soonerfrance"
        desc = "Film wuxia et d'arts martiaux avec combats spectaculaires réalisé par Tsui Hark."
        
        is_asian = server.is_strictly_asian_movie(title, channel, desc, channel_url)
        self.assertTrue(is_asian, "Détective Dee II must be accepted despite 'wuxia' and 'arts martiaux'.")
        
        enriched = server.enrich_movie_fields({
            "videoId": "eA4Py_OT4uQ",
            "title": title,
            "channelName": channel,
            "channelUrl": channel_url,
            "description": desc,
        })
        self.assertTrue(enriched["isAuteur"], "Détective Dee II must have isAuteur=True.")
        self.assertEqual(enriched["auteurLabel"], "🎬 Tsui Hark")

    def test_a_touch_of_zen_king_hu(self):
        """King Hu's A Touch of Zen must be accepted and marked as auteur."""
        title = "A Touch of Zen (俠女, 1971) — King Hu"
        channel = "Taiwan Cinema Classics"
        desc = "Grand chef-d'œuvre du cinéma wuxia et arts martiaux réalisé par King Hu. Prix de la commission supérieure technique au Festival de Cannes 1975."
        
        is_asian = server.is_strictly_asian_movie(title, channel, desc)
        self.assertTrue(is_asian, "A Touch of Zen must be accepted despite 'wuxia' and 'arts martiaux'.")
        
        enriched = server.enrich_movie_fields({
            "videoId": "kinghu_zen",
            "title": title,
            "channelName": channel,
            "description": desc,
        })
        self.assertTrue(enriched["isAuteur"], "A Touch of Zen must have isAuteur=True.")
        self.assertEqual(enriched["auteurLabel"], "🎬 King Hu")

    def test_other_canonical_auteur_martial_arts(self):
        """Other canonical auteur martial arts films (Wong Kar-wai, Ang Lee, Zhang Yimou, Kitano)."""
        films = [
            ("The Grandmaster (一代宗師) — Wong Kar-wai", "Grandmaster of kung fu and martial arts", "🎬 Wong Kar-wai"),
            ("Ashes of Time (東邪西毒) — Wong Kar-wai", "Wuxia martial arts adaptation of Jin Yong", "🎬 Wong Kar-wai"),
            ("Crouching Tiger, Hidden Dragon — Ang Lee", "Wuxia swordplay and martial arts masterpiece", "🎬 Ang Lee"),
            ("Hero (英雄) — Zhang Yimou", "Wuxia martial arts historical epic", "🎬 Zhang Yimou"),
            ("House of Flying Daggers — Zhang Yimou", "Wuxia martial arts romantic drama", "🎬 Zhang Yimou"),
            ("The Assassin (刺客聶隱娘) — Hou Hsiao-hsien", "Wuxia martial arts Prix de la mise en scène Festival de Cannes", "🎬 Hou Hsiao-hsien"),
            ("Zatoichi — Takeshi Kitano", "Chambara martial arts sabre duel", "🎬 Takeshi Kitano"),
            ("Yojimbo (用心棒) — Akira Kurosawa", "Samurai martial arts classic", "🎬 Akira Kurosawa"),
        ]
        for title, desc, expected_label in films:
            with self.subTest(title=title):
                is_asian = server.is_strictly_asian_movie(title, "Asian Cinema Classics", desc)
                self.assertTrue(is_asian, f"Auteur martial film '{title}' must pass filter.")
                
                enriched = server.enrich_movie_fields({
                    "videoId": "vid_test",
                    "title": title,
                    "channelName": "Asian Cinema Classics",
                    "description": desc,
                })
                self.assertTrue(enriched["isAuteur"], f"Film '{title}' must have isAuteur=True.")
                self.assertEqual(enriched["auteurLabel"], expected_label)


class TestKofaAndSoonerPreservation(unittest.TestCase):
    """Dimension 5: Ensure KOFA classics and SOONER films are 100% preserved."""

    def setUp(self):
        with open(server.CACHE_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
            self.cached_movies = list(raw.values()) if isinstance(raw, dict) else raw

    def test_all_kofa_movies_in_cache_preserved_and_auteur(self):
        """100% of KOFA movies in cache must pass filter and have isAuteur=True."""
        kofa_movies = [
            m for m in self.cached_movies
            if "@koreanfilm" in m.get("channelUrl", "").lower()
            or "@koreanfilm" in m.get("channelName", "").lower()
            or "korean classic" in m.get("channelName", "").lower()
            or m.get("category") == "kofa"
        ]
        self.assertGreaterEqual(len(kofa_movies), 140, "There must be >= 140 KOFA movies in cache.")

        for m in kofa_movies:
            title = m.get("title", "")
            ch_name = m.get("channelName", "")
            desc = m.get("description", "")
            ch_url = m.get("channelUrl", "")
            
            with self.subTest(kofa_title=title):
                passes = server.is_strictly_asian_movie(title, ch_name, desc, ch_url)
                self.assertTrue(passes, f"KOFA film '{title}' was rejected by is_strictly_asian_movie.")

                enriched = server.enrich_movie_fields(m)
                self.assertTrue(enriched["isAuteur"], f"KOFA film '{title}' missing isAuteur=True.")
                self.assertIsNotNone(enriched["auteurLabel"], f"KOFA film '{title}' missing auteurLabel.")

    def test_all_sooner_movies_in_cache_preserved_and_auteur(self):
        """100% of SOONER movies in cache must pass filter and have isAuteur=True."""
        sooner_movies = [
            m for m in self.cached_movies
            if "sooner" in m.get("channelName", "").lower()
            or "@soonerfrance" in m.get("channelUrl", "").lower()
            or m.get("paidProvider") == "sooner"
        ]
        self.assertGreaterEqual(len(sooner_movies), 50, "There must be >= 50 SOONER movies in cache.")

        for m in sooner_movies:
            title = m.get("title", "")
            ch_name = m.get("channelName", "")
            desc = m.get("description", "")
            ch_url = m.get("channelUrl", "")
            
            with self.subTest(sooner_title=title):
                passes = server.is_strictly_asian_movie(title, ch_name, desc, ch_url)
                self.assertTrue(passes, f"SOONER film '{title}' was rejected by is_strictly_asian_movie.")

                enriched = server.enrich_movie_fields(m)
                self.assertTrue(enriched["isAuteur"], f"SOONER film '{title}' missing isAuteur=True.")
                self.assertIsNotNone(enriched["auteurLabel"], f"SOONER film '{title}' missing auteurLabel.")

    def test_kofa_and_sooner_with_bmovie_keywords_whitelisted(self):
        """KOFA and SOONER films containing B-movie keywords must be whitelisted and preserved."""
        kofa_martial = server.is_strictly_asian_movie(
            title="The Sword of the Warrior (조선의 검)",
            channel="한국고전영화 Korean Classic Film (@KoreanFilm)",
            description="Classic martial arts and wuxia swordplay from KOFA archive.",
            channel_url="https://www.youtube.com/@KoreanFilm",
        )
        self.assertTrue(kofa_martial, "KOFA martial arts film must be whitelisted.")

        sooner_ninja = server.is_strictly_asian_movie(
            title="Legend of the Secret Ninja Combat",
            channel="SOONER (@soonerfrance)",
            description="Restored ninja kung-fu film available on Sooner.",
            channel_url="https://www.youtube.com/@soonerfrance",
        )
        self.assertTrue(sooner_ninja, "SOONER ninja film must be whitelisted.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
