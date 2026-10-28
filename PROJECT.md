# Project: AsieCinéTube — Recentrage Cinéma d'Auteur & Patrimoine Asiatique

## Architecture
- **Backend Core (`server.py`)**: HTTP server, API endpoints (`/api/movies`, `/api/update`), movie classification, spam & B-movie filtering engine (`is_strictly_asian_movie`), auteur detection and enrichment (`enrich_movie_fields`), cache persistence (`save_cached_movies`).
- **YouTube Harvester (`updater.py`)**: YouTube InnerTube scraper, targeted query definitions (`SEARCH_QUERIES`), candidate deduplication, filtering via `server.is_strictly_asian_movie`, metadata enrichment, in-memory cache purge.
- **Data Stores**:
  - `cache_movies.json`: Complete harvester cache mapping `videoId -> movie_data`.
  - `movies.json`: Public static JSON export consumed by the frontend and clients.
- **Frontend Web UI (`index.html`, `app.js`, `styles.css`)**: Vanilla JS SPA with dark mode, category navigation chips, search bar, responsive movie cards with duration/subtitle/auteur badges, video player modal.
- **Validation & Test Track**:
  - Automated verification script (`validate_catalog.py`).
  - Opaque-box E2E test suite (`tests/` or standalone test runner).

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F1 | Exclusion des chaînes indésirables | Bannir 35 chaînes de nanars, kung-fu série B, iQIYI Action, SAMURAI VS NINJA, Ciné Nanar, short-dramas | M1 | R1 |
| F2 | Filtrage B-movies arts martiaux | Bannir les termes de série B (ninja, wuxia générique, kung fu) sauf exception auteur | M1 | R1 |
| F3 | Détection et enrichissement Auteur | Table de 45+ réalisateurs et marqueurs de festivals/patrimoine avec `isAuteur: true` et `auteurLabel` | M1 | R1 |
| F4 | Support catégorie auteur dans l'API | Endpoint `/api/movies?category=auteur` filtrant les films d'auteur | M1 | R1 |
| F5 | Hygiène du seed & persistance du cache | Remplacement du seed n°5 (Ciné Nanar) et purge active de `cache_map` dans `save_cached_movies` | M1 | R1 |
| F6 | Requêtes moissonneur ciblées Auteur | Remplacement des requêtes arts martiaux dans `updater.py` par 24 requêtes d'auteurs et patrimoine | M2 | R2 |
| F7 | Purge complète du catalogue | Élimination des 144 films indésirables de `cache_movies.json` et `movies.json` | M2 | R2 |
| F8 | Préservation certifiée KOFA & Sooner | Conservation de 100% des films KOFA (>=140) et Sooner (>=50) avec enrichissement | M2 | R2 |
| F9 | Tri par date décroissante | Maintien du tri chronologique inverse sur la page d'accueil et les exports | M2 | R2, AC |
| F10 | Puce de navigation Auteur | Ajout de `<button class="chip chip-auteur" data-category="auteur">` en 2e position | M3 | R3 |
| F11 | Renommage puce Polar & Thriller | Renommer le filtre thriller en « 🔪 Polar & Thriller » (sans mention arts martiaux) | M3 | R3 |
| F12 | Placeholder recherche enrichi | Mettre à jour la barre de recherche pour mentionner les réalisateurs (Ozu, Bong Joon-ho, etc.) | M3 | R3 |
| F13 | Badges Auteur (Cartes & Modale) | Affichage du badge doré/ambre « Cinéma d'Auteur » sur les vignettes et dans la modale | M3 | R3 |
| F14 | Thème CSS de prestige doré/ambre | Règles CSS pour `.chip-auteur`, `.movie-auteur-badge`, `.badge-auteur` | M3 | R3 |
| F15 | Validation automatisée du catalogue | Script `validate_catalog.py` validant l'absence de chaînes exclues et la conformité des données | M4 | R4 |
| F16 | E2E Testing Suite (Tiers 1-4) | Suite de tests opaque-box couvrant l'ensemble des exigences fonctionnelles et aux limites | M4 | R4, E2E |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Moteur de filtrage et détection d'auteur | `server.py` : constantes d'exclusion, règles de filtrage, table auteurs, enrichissement, API, seeds | none | DONE |
| M2 | Moissonneur YouTube et purge du catalogue | `updater.py`, `cache_movies.json`, `movies.json` : requêtes d'auteurs, purge du cache, moisson ciblée | M1 | DONE |
| M3 | Interface utilisateur et navigation | `index.html`, `app.js`, `styles.css` : puces, renommage polar, badge doré cartes/modale, recherche | M1 | DONE |
| M4 | Validation finale & E2E Testing Track | `validate_catalog.py`, suite de tests E2E, audit forensic d'intégrité, validation finale | M1, M2, M3 | DONE |

## Interface Contracts
### `server.py` ↔ `updater.py`
- `server.is_strictly_asian_movie(title: str, channel_name: str, description: str, channel_url: str = "") -> bool`
  - Rejette tout film issu de `EXCLUDED_CHANNELS` ou `SPAM_EXCLUSION_KEYWORDS`.
  - Rejette les termes de `BMOVIE_MARTIAL_ARTS_EXCLUSIONS` sauf si le film provient de SOONER, KOFA ou d'un grand maître de `AUTEUR_DIRECTORS_TABLE`.
  - Doit être appelé lors de la découverte de candidats et lors de la purge en mémoire de `cache_map`.
- `server.save_cached_movies(cache_map: dict)`
  - Purge `cache_map` en éliminant les entrées non conformes à `is_strictly_asian_movie` avant d'écrire atomiquement dans `cache_movies.json` et `movies.json`.
- `server.enrich_movie_fields(movie: dict) -> dict`
  - Produit obligatoirement `isAuteur: bool` (true si grand maître, KOFA ou Sooner patrimoine) et `auteurLabel: Optional[str]` (ex. `"Akira Kurosawa"`, `"KOFA (Patrimoine)"`).

### `server.py` / `movies.json` ↔ Frontend (`app.js`)
- Format d'un objet film dans `movies.json` :
  ```json
  {
    "videoId": "string",
    "title": "string",
    "country": "kr" | "jp" | "cn",
    "isPaid": boolean,
    "paidProvider": "sooner" | null,
    "channelName": "string",
    "durationFormatted": "string",
    "viewCountFormatted": "string",
    "publishDate": "string",
    "publishedTimestamp": number,
    "category": "auteur" | "thriller" | "drama" | "horror" | "comedy" | "kofa" | "sooner",
    "isAuteur": boolean,
    "auteurLabel": "string" | null
  }
  ```
- Filtrage catégorie `"auteur"` :
  - Correspondance frontend : `Boolean(movie.isAuteur) || movie.category === 'auteur' || Boolean(movie.auteurLabel) || movie.category === 'kofa' || (movie.channelName && (movie.channelName.toLowerCase().includes('koreanfilm') || movie.channelName.toLowerCase().includes('sooner')))`

## Code Layout
- `server.py` : Backend Python HTTP server, filtrage et enrichissement (détenu par Milestone 1).
- `updater.py` : Harvester Python et requêtes YouTube (détenu par Milestone 2).
- `cache_movies.json`, `movies.json` : Fichiers de données (détenus par Milestone 2).
- `index.html`, `app.js`, `styles.css` : Frontend Web (détenus par Milestone 3).
- `validate_catalog.py` & tests E2E : Outils de vérification et tests (détenus par Milestone 4 / E2E Track).
