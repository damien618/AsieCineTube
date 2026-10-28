# Analyse Technique Approfondie — Interface Utilisateur & Cinéma d'Auteur (R3)

**Agent** : `teamwork_explorer_survey_3` (Explorer / Enquête en lecture seule)  
**Date** : 2026-10-28  
**Périmètre** : `index.html`, `app.js`, `styles.css`, schéma de données `movies.json` / `server.py`  
**Objectif** : Spécifier en détail et sans ambiguïté les modifications nécessaires pour le Requirement R3 de l'orientation « Cinéma d'Auteur & Grands Maîtres » d'AsieCinéTube.

---

## 1. Synthèse Exécutive

L'exigence R3 vise à recentrer l'interface utilisateur sur le cinéma d'auteur et de patrimoine asiatique à travers trois leviers :
1. **La navigation par puces** : Intégration prioritaire de la puce « 🎬 Cinéma d'Auteur & Grands Maîtres » (`data-category="auteur"`), et renommage de la puce thriller en « 🔪 Polar & Thriller ».
2. **La recherche textuelle** : Mise à jour du placeholder et inclusion des réalisateurs majeurs et marqueurs d'auteurs dans la recherche instantanée côté client.
3. **La valorisation visuelle** : Affichage d'un badge élégant « Cinéma d'Auteur » (ou avec le nom du cinéaste, ex. *« 🎬 Akira Kurosawa »*) à la fois sous les métadonnées de la carte de film et dans la modale plein écran.

L'analyse de l'existant révèle une architecture frontend bien structurée en JavaScript natif modulaire (sans framework lourd), fonctionnant à la fois sur serveur local Python (`/api/movies`) et sur GitHub Pages (`movies.json`). Le filtrage et le tri s'effectuent intégralement **côté client en mémoire** dans `app.js`, ce qui nécessite une intégration rigoureuse de la catégorie `auteur` dans le moteur de filtrage JS afin d'assurer réactivité instantanée et cohérence parfaite avec le backend.

---

## 2. Examen Détaillé de `index.html`

### 2.1 Barre de Navigation par Puces (`.chips-track`)

**Emplacement direct** : Lignes 92 à 130 de `index.html`.

#### Structure actuelle :
```html
<nav class="chips-container" aria-label="Pays, catégories et genres">
  <div class="chips-track" id="chipsTrack">
    <button class="chip active" data-category="all">
      <span>🌏 Tous les films (Corée • Japon • Chine)</span>
    </button>
    <button class="chip chip-sooner" data-category="sooner" title="...">
      <span class="yt-paid-dot" aria-hidden="true"></span>
      <span>Sooner (@soonerfrance)</span>
    </button>
    <button class="chip" data-category="kr"><span>🇰🇷 Films Coréens</span></button>
    <button class="chip" data-category="kofa" title="..."><span>🏛️ @KoreanFilm (KOFA)</span></button>
    <button class="chip" data-category="jp"><span>🇯🇵 Films Japonais</span></button>
    <button class="chip" data-category="cn"><span>🇨🇳 Films Chinois</span></button>
    <button class="chip" data-category="native"><span>⭐ ST-FR / VF Natif</span></button>
    <button class="chip" data-category="thriller"><span>🔪 Thriller, Action & Arts Martiaux</span></button>
    <button class="chip" data-category="drama"><span>🎭 Drame, Romance & Historique</span></button>
    <button class="chip" data-category="horror"><span>👻 Horreur & Mystère</span></button>
    <button class="chip" data-category="comedy"><span>🍿 Comédie</span></button>
  </div>
</nav>
```

#### Modifications Requises :
1. **Insertion de la puce Auteur** :  
   Insérer le bouton avec `data-category="auteur"` et la classe dédiée `chip-auteur` immédiatement après `data-category="all"` (ligne 97) et avant `data-category="sooner"`.  
   *Justification* : Positionner le cinéma d'auteur en tête de la navigation matérialise immédiatement l'orientation éditoriale du site dès la première seconde d'arrivée de l'internaute.
   ```html
   <button class="chip chip-auteur" data-category="auteur" title="Sélection de chefs-d'œuvre patrimoniaux, cinéma d'auteur et festivals (Cannes, Berlin, Venise, KOFA, Sooner...)">
     <span>🎬 Cinéma d'Auteur & Grands Maîtres</span>
   </button>
   ```
2. **Renommage de la puce Thriller** (lignes 117-119) :  
   Remplacer l'intitulé `🔪 Thriller, Action & Arts Martiaux` par `🔪 Polar & Thriller`.  
   *Justification* : Éliminer la mention « Arts Martiaux » pour être en phase avec l'expurgation des séries B de kung-fu/ninja.

---

### 2.2 Champ de Recherche (`#searchInput`)

**Emplacement direct** : Lignes 37 à 51 de `index.html`.

#### Structure actuelle :
```html
<div class="search-input-box">
  <input 
    type="text" 
    id="searchInput" 
    placeholder="Rechercher un film coréen, japonais ou chinois, un acteur, un genre..." 
    autocomplete="off"
    spellcheck="false"
    aria-label="Rechercher des films asiatiques"
  >
  ...
</div>
```

#### Modifications Requises :
- Modifier `placeholder` pour inciter explicitement à la recherche de maîtres du cinéma :  
  `placeholder="Rechercher un film, un réalisateur (Ozu, Bong Joon-ho, Wong Kar-wai...)"`
- Mettre à jour `aria-label` pour l'accessibilité :  
  `aria-label="Rechercher un film asiatique ou un réalisateur"`

---

### 2.3 Modale de Visionnage (`#movieModal`)

**Emplacement direct** : Lignes 260 à 264 de `index.html`.

#### Structure actuelle :
```html
<div class="modal-badges-group">
  <span class="badge-subtitle" id="modalSubtitleBadge">🇫🇷 ST-FR Natif</span>
  <span class="badge-duration" id="modalDurationBadge">1:45:00</span>
</div>
```

#### Modifications Requises :
- Ajouter l'élément conteneur pour le badge auteur `#modalAuteurBadge` dans `.modal-badges-group` :
```html
<div class="modal-badges-group">
  <span class="badge-auteur hidden" id="modalAuteurBadge">🎬 Cinéma d'Auteur</span>
  <span class="badge-subtitle" id="modalSubtitleBadge">🇫🇷 ST-FR Natif</span>
  <span class="badge-duration" id="modalDurationBadge">1:45:00</span>
</div>
```
*Justification* : Masqué par défaut (`hidden`), il sera activé et son libellé dynamiquement injecté par `app.js` si le film est marqué `isAuteur: true`.

---

## 3. Examen Détaillé de `app.js`

### 3.1 Gestion de l'État & Références DOM

**Emplacement direct** : Lignes 16-24 (`state`) et 29-81 (`DOM`).

- Dans l'objet `DOM`, ajouter la référence :
  ```javascript
  modalAuteurBadge: document.getElementById('modalAuteurBadge'),
  ```
- Les écouteurs d'événements pour les puces sont attachés par délégation sur `DOM.chipsTrack` (lignes 789-798). Tout nouveau bouton doté de la classe `.chip` et de l'attribut `data-category` fonctionnera automatiquement sans modifier la logique de capture des clics.
- Le bouton de réinitialisation (`DOM.resetFiltersBtn`, lignes 802-818) bascule déjà l'état actif sur `c.dataset.category === 'all'`.

---

### 3.2 Filtrage Côté Client (`applyFiltersAndRender`)

**Emplacement direct** : Lignes 214 à 266 de `app.js`.

#### Analyse du comportement actuel :
Actuellement, les catégories gérées sont : `'sooner'`, `'kr'`, `'jp'`, `'cn'`, `'kofa'`, `'native'`, et la liste `['thriller', 'drama', 'horror', 'comedy']`.  
Si `category === 'auteur'`, la condition passe à travers sans correspondre, et la catégorie est ignorée ou traite le film comme vide.

#### Logique proposée pour `category === 'auteur'` :
Pour garantir robustesse et résilience (notamment si le catalogue statique `movies.json` est en cours de propagation CDN ou en transition), la détection de film d'auteur dans `applyFiltersAndRender()` doit être tolérante et multidimensionnelle :

```javascript
// 2. Filtre Puce / Catégorie
if (category === 'auteur') {
  const isAuteur = Boolean(movie.isAuteur) ||
    movie.category === 'auteur' ||
    Boolean(movie.auteurLabel) ||
    movie.category === 'kofa' ||
    (movie.channelName && (
      movie.channelName.toLowerCase().includes('koreanfilm') ||
      movie.channelName.toLowerCase().includes('sooner')
    ));
  if (!isAuteur) return false;
} else if (category === 'sooner') {
...
```

*Critère d'appartenance* :
1. `movie.isAuteur === true` (attribut fourni par le nouveau `enrich_movie_fields`).
2. `movie.category === 'auteur'`.
3. Présence d'un libellé `movie.auteurLabel`.
4. Tous les classiques KOFA (`category === 'kofa'` ou `@koreanfilm`) et le catalogue Sooner (@soonerfrance) qui sont les réservoirs légaux du patrimoine asiatique.

---

### 3.3 Extension de la Recherche Textuelle

**Emplacement direct** : Lignes 252 à 264 de `app.js`.

#### Code actuel :
```javascript
if (query) {
  const titleMatch = (movie.title || '').toLowerCase().includes(query);
  const koreanTitleMatch = (movie.koreanTitle || '').toLowerCase().includes(query);
  const channelMatch = (movie.channelName || '').toLowerCase().includes(query);
  const descMatch = (movie.description || '').toLowerCase().includes(query);
  const countryMatch = (movie.countryLabel || '').toLowerCase().includes(query);

  if (!titleMatch && !koreanTitleMatch && !channelMatch && !descMatch && !countryMatch) {
    return false;
  }
}
```

#### Amélioration proposée :
Ajouter la correspondance sur `movie.auteurLabel` et un éventuel champ `movie.director` :
```javascript
const auteurMatch = (movie.auteurLabel || '').toLowerCase().includes(query) ||
  (movie.director || '').toLowerCase().includes(query);

if (!titleMatch && !koreanTitleMatch && !channelMatch && !descMatch && !countryMatch && !auteurMatch) {
  return false;
}
```
*Bénéfice* : Si l'utilisateur tape « Kurosawa » ou « Ozu », même si le mot n'était pas présent dans le titre de la vidéo mais injecté dans `auteurLabel`, le film ressort immédiatement dans la grille.

---

### 3.4 Bandeau d'État (`updateStatusBar`)

**Emplacement direct** : Lignes 278 à 321 de `app.js`.

#### Problème actuel :
Si `state.currentCategory === 'auteur'`, la fonction applique le fallback par défaut :
`activeFilterLabel = 'Genre : AUTEUR'`. Ce n'est ni élégant ni conforme au plan.  
De même pour `thriller`, il affichait `Genre : THRILLER`.

#### Modification requise :
```javascript
let activeFilterLabel = '';
if (state.currentCategory === 'auteur') {
  activeFilterLabel = '🎬 Cinéma d\'Auteur & Grands Maîtres';
} else if (state.currentCategory === 'sooner') {
  activeFilterLabel = '🟢 Sooner (@soonerfrance)';
} else if (state.currentCategory === 'kr') {
  activeFilterLabel = '🇰🇷 Films Coréens';
} else if (state.currentCategory === 'kofa') {
  activeFilterLabel = '🏛️ @KoreanFilm (KOFA)';
} else if (state.currentCategory === 'jp') {
  activeFilterLabel = '🇯🇵 Films Japonais';
} else if (state.currentCategory === 'cn') {
  activeFilterLabel = '🇨🇳 Films Chinois';
} else if (state.currentCategory === 'native') {
  activeFilterLabel = '⭐ ST-FR Natif';
} else if (state.currentCategory === 'thriller') {
  activeFilterLabel = '🔪 Polar & Thriller';
} else if (state.currentCategory !== 'all') {
  activeFilterLabel = `Genre : ${state.currentCategory.toUpperCase()}`;
}
```

---

### 3.5 Rendu des Cartes de Films (`createMovieCard`)

**Emplacement direct** : Lignes 354 à 458 de `app.js`.

#### Emplacement du Badge Auteur :
Placer le badge dans `.movie-text-content`, immédiatement sous `.movie-meta-line` (lignes 448-456).  
*Analyse comparative* :
- **Sur la miniature** : La miniature 16:9 est déjà occupée par les badges aux 4 coins (sous-titres en haut à gauche, Sooner payant en haut à droite, durée en bas à droite, bouton YouTube direct en bas à gauche au survol). Y superposer un badge auteur saturerait l'image.
- **Sous les métadonnées** : C'est l'emplacement naturel utilisé par `.movie-paid-line`. En créant un conteneur flex `.movie-badges-container`, les badges d'auteur et d'éditeur Sooner s'alignent avec fluidité.

#### Code d'intégration :
```javascript
const isAuteur = Boolean(movie.isAuteur);
const auteurLabel = movie.auteurLabel || "🎬 Cinéma d'Auteur";
const auteurBadgeHtml = isAuteur
  ? `<div class="movie-auteur-badge" title="${escapeHtml(auteurLabel)}">
       <span>${escapeHtml(auteurLabel)}</span>
     </div>`
  : '';
```

Et dans le template HTML de la carte :
```html
<div class="movie-meta-line">
  <span>${escapeHtml(movie.viewCountFormatted || 'Vues non indiquées')}</span>
  <span>•</span>
  <span title="Date de publication : ${escapeHtml(movie.publishedFormatted || movie.publishDate || '')}">
    ${escapeHtml(movie.publishedRelative || movie.publishedFormatted || '')}
  </span>
</div>
<div class="movie-badges-container">
  ${auteurBadgeHtml}
  ${paidInfoLine}
</div>
```

---

### 3.6 Modale de Visionnage (`openMovieModal`)

**Emplacement direct** : Lignes 502 à 551 de `app.js`.

#### Code d'intégration :
```javascript
// Badge Auteur dans la modale
if (DOM.modalAuteurBadge) {
  if (movie.isAuteur) {
    DOM.modalAuteurBadge.textContent = movie.auteurLabel || "🎬 Cinéma d'Auteur";
    DOM.modalAuteurBadge.classList.remove('hidden');
  } else {
    DOM.modalAuteurBadge.classList.add('hidden');
  }
}
```

---

### 3.7 Garantie du Tri par Date Décroissante

`app.js` possède déjà la fonction `sortMoviesByDateDesc(movies)` (lignes 192-209), s'appuyant sur `publishedTimestamp` ou `Date.parse(movie.publishDate)`.  
Dans `applyFiltersAndRender()` (ligne 269) :
```javascript
state.filteredMovies = sortMoviesByDateDesc(filtered);
```
Tout film filtré, y compris sous la puce `auteur`, est ainsi garanti d'être ordonné du plus récent au plus ancien.

---

## 4. Examen Détaillé de `styles.css`

### 4.1 Charte Graphique & Variables CSS

Le thème général d'AsieCinéTube est un Dark Mode inspiré de YouTube (`--yt-bg: #0f0f0f`, surfaces `#181818`, texte `#f1f1f1`).  
Pour le **Cinéma d'Auteur & Patrimoine**, la tonalité de référence est le **doré / ambre chaud**, rappelant la Palme d'Or du Festival de Cannes, les lions de Venise et les cinémas Art & Essai :
- **Ambre / Doré textuel** : `#fbbf24` (ambre éclatant) ou `#f59e0b`
- **Arrière-plan badge** : `rgba(245, 158, 11, 0.15)`
- **Bordure badge** : `rgba(245, 158, 11, 0.45)`
- **Dégradé actif puce** : `linear-gradient(135deg, #b45309, #d97706)`

Ajout recommandé dans `:root` (lignes 5-21) :
```css
--badge-auteur-bg: rgba(245, 158, 11, 0.15);
--badge-auteur-text: #fbbf24;
--badge-auteur-border: rgba(245, 158, 11, 0.45);
```

---

### 4.2 Styles de la Puce Auteur (`.chip.chip-auteur`)

A insérer après `.chip.chip-sooner` (lignes 326-345) :

```css
/* Puce spéciale Cinéma d'Auteur & Grands Maîtres */
.chip.chip-auteur {
  border: 1px solid rgba(245, 158, 11, 0.5);
  background-color: rgba(245, 158, 11, 0.12);
  color: #fef3c7;
}

.chip.chip-auteur:hover {
  background-color: rgba(245, 158, 11, 0.22);
  border-color: rgba(245, 158, 11, 0.7);
}

.chip.chip-auteur.active {
  background: linear-gradient(135deg, #b45309, #d97706);
  color: #ffffff;
  border-color: #f59e0b;
  box-shadow: 0 0 12px rgba(245, 158, 11, 0.35);
}
```

---

### 4.3 Styles du Badge Auteur sur Carte & Modale

A insérer dans la section des cartes (vers la ligne 637) et de la modale (vers la ligne 940) :

```css
/* Conteneur flex des badges sous les métadonnées de la carte */
.movie-badges-container {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  margin-top: 6px;
}

/* Badge Cinéma d'Auteur sur les cartes */
.movie-auteur-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 2px 8px;
  background-color: var(--badge-auteur-bg, rgba(245, 158, 11, 0.15));
  border: 1px solid var(--badge-auteur-border, rgba(245, 158, 11, 0.45));
  border-radius: 4px;
  color: var(--badge-auteur-text, #fbbf24);
  font-size: 11.5px;
  font-weight: 600;
  letter-spacing: 0.2px;
  width: fit-content;
  white-space: nowrap;
}

/* Badge Cinéma d'Auteur dans la modale */
.badge-auteur {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 6px;
  background-color: rgba(245, 158, 11, 0.18);
  border: 1px solid rgba(245, 158, 11, 0.55);
  color: #fbbf24;
}
```

---

### 4.4 Comportement Mobile & Responsive

- `.chips-container` possède déjà `overflow-x: auto;` (ligne 279), garantissant un défilement horizontal fluide au doigt sur smartphone ou tablette.
- `.movie-badges-container` avec `flex-wrap: wrap;` assure que sur petit écran (grille 1 colonne ou écran < 360px), le badge d'auteur et le badge Sooner se superposent proprement sans dépasser de la carte ni tronquer le texte.

---

## 5. Analyse des Écarts Backend / Frontend (Schéma de Données)

| Propriété Film | Format Backend (`server.py` enrichi) | Usage Frontend (`app.js`) | Écart / Action requise |
| :--- | :--- | :--- | :--- |
| `isAuteur` | Booléen (`true`/`false`) | Actuellement absent de `createMovieCard` et `openMovieModal` | **Ajouter** l'évaluation de `Boolean(movie.isAuteur)` pour afficher le badge. Gérer fallback si `undefined`. |
| `auteurLabel` | Chaîne (ex. `"🎬 Akira Kurosawa"`, `"🎬 Cinéma d'Auteur"`) | Actuellement absent de `app.js` | **Ajouter** le libellé dans le badge carte, la modale et la recherche textuelle instantanée. |
| `category` | Peut être `"auteur"`, `"kofa"`, `"drama"`, etc. | `applyFiltersAndRender` ne gérait pas `category === 'auteur'` | **Ajouter** la branche `if (category === 'auteur')` dans `applyFiltersAndRender`. |
| `publishDate` / `publishedTimestamp` | `"YYYY-MM-DD"` / entier epoch | Utilisé par `sortMoviesByDateDesc` | **Aucun écart**. Format 100% aligné. |
| `isPaid` / `paidProvider` | Booléen / Chaîne (`"Sooner (@soonerfrance)"`) | Affiché via `paidInfoLine` et `badge-paid-top` | **Harmonisé**. Les films d'auteur Sooner (ex: *Seppuku* de Miike) cumulent `isAuteur` et `isPaid`. |

---

## 6. Guide de Modifications Ligne par Ligne (Prêt pour Implémentation)

### `index.html`
1. **Lignes 97-98** : Insérer la puce `data-category="auteur"`.
2. **Ligne 118** : Remplacer `🔪 Thriller, Action & Arts Martiaux` par `🔪 Polar & Thriller`.
3. **Ligne 40** : Remplacer le `placeholder` par `"Rechercher un film, un réalisateur (Ozu, Bong Joon-ho, Wong Kar-wai...)"`.
4. **Ligne 261** : Insérer `<span class="badge-auteur hidden" id="modalAuteurBadge">🎬 Cinéma d'Auteur</span>` avant `modalSubtitleBadge`.

### `app.js`
1. **Ligne 72** : Ajouter `modalAuteurBadge: document.getElementById('modalAuteurBadge')` dans `DOM`.
2. **Lignes 225-226** : Insérer le test de `category === 'auteur'` au tout début des filtres de puces dans `applyFiltersAndRender()`.
3. **Ligne 260** : Ajouter `auteurMatch` dans le test de recherche `query`.
4. **Ligne 290** : Ajouter la condition pour `'auteur'` et `'thriller'` dans `updateStatusBar()`.
5. **Lignes 375-385** et **455** : Définir `auteurBadgeHtml` et l'intégrer dans `.movie-badges-container` au sein de `createMovieCard()`.
6. **Ligne 545** : Gérer l'affichage et le texte de `DOM.modalAuteurBadge` dans `openMovieModal()`.

### `styles.css`
1. **Lignes 17-21** : Ajouter les variables de couleur ambre/or `--badge-auteur-*`.
2. **Lignes 345** : Ajouter les règles `.chip.chip-auteur` (repos, hover, active).
3. **Lignes 637** : Ajouter `.movie-badges-container` et `.movie-auteur-badge`.
4. **Lignes 954** : Ajouter `.badge-auteur` pour la modale.
