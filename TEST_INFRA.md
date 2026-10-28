# AsieCinéTube — Infrastructure & Spécifications de la Suite de Tests E2E

## 1. Vue d'Ensemble & Objectifs

Cette infrastructure de tests E2E a été conçue pour valider de manière exhaustive, opaque et reproductible le recentrage d'**AsieCinéTube** sur le **cinéma d'auteur et de patrimoine asiatique** (Corée du Sud 🇰🇷, Japon 🇯🇵, Chine / Hong-Kong / Taïwan 🇨🇳), conformément aux spécifications du plan d'implémentation et aux exigences R1 à R4 documentées dans `PROJECT.md` et `ORIGINAL_REQUEST.md`.

La suite applique une méthodologie rigoureuse en **4 tiers** couvrant :
- L'intégrité du moteur de filtrage backend et de détection d'auteurs (`server.py`).
- Les requêtes et la politique de purge du moissonneur YouTube (`updater.py`).
- La salubrité absolue des bases de données (`cache_movies.json`, `movies.json`).
- L'interface utilisateur Web (`index.html`, `app.js`, `styles.css`).
- Les scripts de validation et les parcours utilisateurs réels de bout en bout.

---

## 2. Méthodologie en 4 Tiers

```
+--------------------------------------------------------------------------+
|                       TIER 4: REAL-WORLD SCENARIOS                       |
|   5 parcours utilisateurs E2E complets (découverte, navigation, modale)   |
+--------------------------------------------------------------------------+
|                   TIER 3: CROSS-FEATURE COMBINATIONS                     |
|      12 tests croisés (Sooner + arts martiaux, recherche + catégories)    |
+--------------------------------------------------------------------------+
|                    TIER 2: BOUNDARY & CORNER CASES                       |
|   15 tests aux limites (URL-encoding, faux positifs Ozu, CJK boundaries) |
+--------------------------------------------------------------------------+
|                  TIER 1: SYSTEMATIC FEATURE COVERAGE                     |
|           80 tests unitaires & fonctionnels (>=5 tests par F1-F16)       |
+--------------------------------------------------------------------------+
```

### Tier 1 : Couverture Exhaustive des Fonctionnalités (F1 à F16)
Chaque fonctionnalité F1 à F16 fait l'objet d'au minimum 5 cas de tests dédiés et indépendants (80 tests au total pour Tier 1) :
- **F1 (Exclusion des chaînes indésirables)** : Rejet de `SAMURAI VS NINJA`, `Chinese Online Movie Channel`, `iQIYI Action`, `Ciné Nanar`, short-dramas (`양파극장`, `멀더의 무비파일`), récapitulatifs TV (`SBS Catch`, `KBS Drama`).
- **F2 (Filtrage B-movies arts martiaux)** : Rejet des termes génériques (`ninja`, `kung fu`, `wuxia`, `shaolin`, `drunken fist`, `무협`) sauf exception auteur certifiée.
- **F3 (Détection & enrichissement Auteur)** : Détection des 45+ maîtres (Kurosawa, Ozu, Bong Joon-ho, Wong Kar-wai, etc.), attribution de `isAuteur: true` et du libellé formaté `auteurLabel`.
- **F4 (Support catégorie auteur dans l'API)** : Filtrage de `/api/movies?category=auteur`, préservation des classiques KOFA et Sooner, compatibilité multi-critères.
- **F5 (Hygiène du seed & persistance du cache)** : Éviction définitive de `Ciné Nanar` (`IgY-P7pO0x4`) du seed, purge systématique de `cache_map` dans `save_cached_movies` avant écriture.
- **F6 (Requêtes moissonneur ciblées Auteur)** : Remplacement des 19 requêtes obsolètes par les 24 requêtes d'auteurs et patrimoine, suppression des requêtes génériques de combat.
- **F7 (Purge complète du catalogue)** : Vérification de l'absence totale de chaînes exclues et de nanars non exemptés dans `movies.json` et `cache_movies.json`.
- **F8 (Préservation certifiée KOFA & Sooner)** : Contrôle du maintien de 100% des films KOFA (>=140) et Sooner (>=50) avec métadonnées intactes.
- **F9 (Tri par date décroissante)** : Maintien strict de l'ordre antéchronologique (`publishedTimestamp` / `publishDate`) dans l'export et l'API.
- **F10 (Puce de navigation Auteur)** : Présence du bouton `data-category="auteur"` en 2e position dans `index.html` et activation dans `app.js`.
- **F11 (Renommage puce Polar & Thriller)** : Puce renommée « 🔪 Polar & Thriller » (sans mention d'arts martiaux), statut bar synchronisée.
- **F12 (Placeholder recherche enrichi)** : Mention explicite des réalisateurs (Ozu, Bong Joon-ho...) dans le placeholder et recherche tolérante par auteur dans `app.js`.
- **F13 (Badges Auteur Cartes & Modale)** : Intégration du badge ambre/or `movie-auteur-badge` sous les métadonnées et `#modalAuteurBadge` dans la modale.
- **F14 (Thème CSS de prestige doré/ambre)** : Définition des variables de couleurs d'auteur, styles `.chip-auteur`, `.movie-auteur-badge`, `.badge-auteur`.
- **F15 (Validation automatisée du catalogue)** : Vérification de l'existence et du fonctionnement du script de validation du catalogue.
- **F16 (E2E Testing Suite)** : Auto-vérification de la suite de tests (exécution hermétique, diagnostic, isolation et robustesse).

### Tier 2 : Cas aux Limites & Situations Extrêmes (Boundaries & Corners)
- Entrées vides (`title=""`, `channel=""`, `description=""`).
- Descriptions extrêmement volumineuses (50 000 caractères).
- Casse mixte et désordonnée (`sAmUrAi Vs NiNjA`, `kUnG fU`, `oZu`).
- Encodage d'URL dans les handles (`urllib.parse.unquote`, e.g. `%EC%96%91%ED%8C%8C%EA%B7%B9%EC%9E%A5`).
- Faux positifs d'identifiants YouTube dans les descriptions (ex. `https://youtu.be/gil_9u4oZuI` ne doit pas matcher `\bozu\b`).
- Homonymes sans prénom (ex. "la famille Kobayashi" dans un film ne doit pas déclencher `Masaki Kobayashi`).
- Requêtes de recherche renvoyant 0 résultat.
- Frontières de scripts CJK (Hangul `\uac00-\ud7a3`, Kana, Hanzi) sans plantage sur les emojis ou caractères Unicode étendus.

### Tier 3 : Combinaisons Multi-Fonctionnalités (Cross-Feature Combinations)
- Film d'auteur avec étiquette d'arts martiaux issu de Sooner (ex: *Seppuku* de Masaki Kobayashi) -> Doit passer le filtre, recevoir `isAuteur=True`, `isPaid=True`, et appartenir à la fois à "auteur" et "sooner".
- Film KOFA contenant le mot "sabre" ou "combat" -> Doit passer le filtre, recevoir `isAuteur=True`, appartenir à "kofa" et "auteur".
- Recherche textuelle combinée avec filtre de catégorie (ex: recherche "Bong" en catégorie "thriller" vs catégorie "jp").
- Cohérence du bandeau d'état lors des commutations de catégories ("auteur", "thriller", "sooner", "all").
- Cycle d'aller-retour du cache (sauvegarde -> chargement) préservant l'intégrité exacte sans perte d'attributs auteur.
- Paramètres API combinés (`category=auteur&country=kr`).

### Tier 4 : Scénarios Utilisateurs Réels de Bout en Bout (E2E User Journeys)
1. **Journey 1 : Découverte du catalogue d'accueil** (chargement de `movies.json`, vérification du tri chronologique descendant, répartition par pays, présence des badges auteur).
2. **Journey 2 : Filtrage éditorial Cinéma d'Auteur** (clic sur la puce auteur, vérification que 100% des films affichés sont d'auteur/patrimoine/KOFA/Sooner, zéro nanar présent, statut bar synchronisée).
3. **Journey 3 : Recherche réalisateur & consultation de la modale** (recherche "Kurosawa", ouverture de la carte, contrôle des badges modale : durée, ST-FR, et badge doré réalisateur).
4. **Journey 4 : Filtrage Polar & Thriller assaini** (clic sur "🔪 Polar & Thriller", vérification de l'absence de séries B de kung-fu, présence des thrillers reconnus avec leur badge auteur le cas échéant).
5. **Journey 5 : Ingestion Harvester & Résistance au flux pollué** (simulation d'une moisson YouTube avec flux candidat contenant 30 nanars/spams et 5 œuvres d'auteur -> seuls les 5 chefs-d'œuvre sont retenus et enrichis).

---

## 3. Commandes d'Exécution

La suite est exécutable via une commande unique utilisant le framework standard Python `unittest` :

```bash
# Exécution complète de la suite unifiée avec rapport détaillé :
python3 tests/test_catalog_e2e.py

# Découverte et exécution automatique standard unittest :
python3 -m unittest discover tests

# Exécution ciblée par fichier de test :
python3 -m unittest tests/test_tier1_features.py
python3 -m unittest tests/test_tier2_boundaries.py
python3 -m unittest tests/test_tier3_combinations.py
python3 -m unittest tests/test_tier4_scenarios.py
```

---

## 4. Environnement & Isolation

- **Environnement** : Python 3.9+ (Standard Library exclusivement : `unittest`, `re`, `json`, `urllib`, `html`).
- **Aucune dépendance externe** : Fonctionne sans `pytest`, `requests` ou `node`, garantissant une exécution immédiate sur tout système macOS/Linux/CI.
- **Herméticité réseau** : Aucun test n'émet de requêtes sortantes vers YouTube ou Google Cloud. Les flux InnerTube et watch-HTML sont simulés à l'aide de fixtures déterministes.
- **Isolation des fichiers de test** : Les tests d'écriture de cache (`save_cached_movies`) s'exécutent dans des répertoires temporaires isolés (`tempfile.TemporaryDirectory`) afin de ne jamais altérer les fichiers réels du dépôt durant les tests.

---

## 5. Variances Connues & Tolérances

- **Horodatages dynamiques** : Le champ `updatedAt` dans `movies.json` reflète l'instant de génération (ISO-8601). Les assertions valident la structure syntaxique ISO-8601 plutôt qu'une valeur figée.
- **Ordre des réalisateurs** : Le libellé `auteurLabel` peut varier selon le réalisateur identifié en premier dans le titre ou la description (ex. `"🎬 Akira Kurosawa"`). Les tests valident le préfixe et le nom canonique.
- **Progression des jalons** : Lorsque certains jalons (M1, M2, M3) sont en cours d'implémentation, les tests correspondants détectent rigoureusement les écarts jusqu'à complétion du code source par les agents dédiés.
