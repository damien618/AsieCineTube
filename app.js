/**
 * AsieCinéTube FR - Application Client
 * Films Coréens, Japonais et Chinois (VOSTFR / CC-FR) sur YouTube
 * Triés par date de publication décroissante.
 * 
 * Compatible hébergement statique GitHub Pages (damien618.github.io/AsieCineTube)
 * et serveur local Python (server.py).
 */

(function () {
  'use strict';

  // ==========================================================================
  // ÉTAT GLOBAL DE L'APPLICATION
  // ==========================================================================
  const state = {
    allMovies: [],         // Tous les films chargés en mémoire
    filteredMovies: [],    // Films filtrés selon les critères actifs
    currentCategory: 'all',// Puce sélectionnée ('all', 'sooner', 'kr', 'kofa', 'jp', 'cn', 'native', etc.)
    subFilter: 'all',      // 'all' ou 'native'
    searchQuery: '',       // Chaîne de recherche saisie
    isLoading: false,
    selectedMovie: null    // Film actuellement affiché dans la modale
  };

  // ==========================================================================
  // RÉFÉRENCES DOM
  // ==========================================================================
  const DOM = {
    // Header & Recherche
    searchForm: document.getElementById('searchForm'),
    searchInput: document.getElementById('searchInput'),
    clearSearchBtn: document.getElementById('clearSearchBtn'),
    searchBtn: document.getElementById('searchBtn'),
    subFilter: document.getElementById('subFilter'),
    refreshBtn: document.getElementById('refreshBtn'),

    // Barre de puces (Chips)
    chipsTrack: document.getElementById('chipsTrack'),
    chips: document.querySelectorAll('.chip'),

    // Bandeau d'état
    statusBar: document.getElementById('statusBar'),
    movieCount: document.getElementById('movieCount'),
    activeFilterBadge: document.getElementById('activeFilterBadge'),

    // Grille de films & États
    moviesGrid: document.getElementById('moviesGrid'),
    emptyState: document.getElementById('emptyState'),
    emptyDesc: document.getElementById('emptyDesc'),
    resetFiltersBtn: document.getElementById('resetFiltersBtn'),
    errorState: document.getElementById('errorState'),
    errorMsg: document.getElementById('errorMsg'),
    retryFetchBtn: document.getElementById('retryFetchBtn'),

    // Modale Lecteur
    movieModal: document.getElementById('movieModal'),
    closeModalBtn: document.getElementById('closeModalBtn'),
    modalPlayerContainer: document.getElementById('modalPlayerContainer'),
    modalIframe: document.getElementById('modalIframe'),
    overlayFullscreenBtn: document.getElementById('overlayFullscreenBtn'),
    fullscreenBtn: document.getElementById('fullscreenBtn'),
    fullscreenBtnText: document.getElementById('fullscreenBtnText'),
    modalYtLink: document.getElementById('modalYtLink'),
    modalSubHelp: document.getElementById('modalSubHelp'),
    modalSubHelpText: document.getElementById('modalSubHelpText'),
    modalMovieTitle: document.getElementById('modalMovieTitle'),
    modalChannelAvatar: document.getElementById('modalChannelAvatar'),
    modalChannelName: document.getElementById('modalChannelName'),
    modalChannelVerified: document.getElementById('modalChannelVerified'),
    modalStatsText: document.getElementById('modalStatsText'),
    modalSubtitleBadge: document.getElementById('modalSubtitleBadge'),
    modalDurationBadge: document.getElementById('modalDurationBadge'),
    modalDescription: document.getElementById('modalDescription'),
    modalSubtitlesLanguages: document.getElementById('modalSubtitlesLanguages'),
    modalSubLanguagesList: document.getElementById('modalSubLanguagesList'),

    // Toast
    toast: document.getElementById('toastNotification'),
    toastMessage: document.getElementById('toastMessage')
  };

  let searchDebounceTimer = null;
  let toastTimer = null;

  // ==========================================================================
  // INITIALISATION
  // ==========================================================================
  function init() {
    setupEventListeners();
    loadMovies(false);
  }

  // ==========================================================================
  // GESTION DES REQUÊTES (GITHUB PAGES + LOCALHOST)
  // ==========================================================================

  /**
   * Détermine si le site est hébergé en mode statique (ex: GitHub Pages)
   */
  function isStaticHosting() {
    const hostname = window.location.hostname;
    return (
      hostname.includes('github.io') ||
      window.location.protocol === 'file:' ||
      window.location.port === '' && hostname !== 'localhost' && hostname !== '127.0.0.1'
    );
  }

  /**
   * Charge le catalogue de films.
   * Fonctionne en toute transparence sur GitHub Pages (damien618.github.io/AsieCineTube)
   * et en local avec Python server.py.
   * 
   * @param {boolean} isRefresh - S'il s'agit d'une actualisation manuelle par l'utilisateur
   */
  async function loadMovies(isRefresh = false) {
    if (state.isLoading) return;

    state.isLoading = true;
    showLoadingState(isRefresh);

    const isStatic = isStaticHosting();
    const cacheBuster = `_t=${Date.now()}`;

    // Sur GitHub Pages, nous utilisons le fichier statique movies.json avec cache-buster
    // pour forcer la récupération de la dernière version déployée sans passer par le cache CDN.
    let primaryUrl = isStatic
      ? `./movies.json?${cacheBuster}`
      : `./api/movies${isRefresh ? '?refresh=1&' + cacheBuster : ''}`;

    let fallbackUrl = `./movies.json?${cacheBuster}`;

    try {
      let data = null;
      let fetchedFromApi = false;

      try {
        const response = await fetch(primaryUrl);
        if (response.ok) {
          const contentType = response.headers.get('content-type') || '';
          if (contentType.includes('application/json') || primaryUrl.includes('.json')) {
            data = await response.json();
            fetchedFromApi = !isStatic;
          }
        }
      } catch (err) {
        console.warn(`Échec de récupération sur ${primaryUrl}, tentative de fallback...`, err);
      }

      // Si l'API échoue ou renvoie 404 (cas typique sur GitHub Pages ou si le serveur local n'a pas l'API)
      if (!data && primaryUrl !== fallbackUrl) {
        console.info(`Basculement sur le catalogue statique : ${fallbackUrl}`);
        const fallbackResponse = await fetch(fallbackUrl);
        if (fallbackResponse.ok) {
          data = await fallbackResponse.json();
        } else {
          throw new Error(`Catalogue statique introuvable (${fallbackResponse.status})`);
        }
      }

      if (!data || !Array.isArray(data.movies)) {
        throw new Error('Données reçues invalides ou corrompues');
      }

      // Traitement et tri strict par date décroissante
      state.allMovies = sortMoviesByDateDesc(data.movies);
      applyFiltersAndRender();

      hideErrorState();

      if (isRefresh) {
        showToast(`Catalogue actualisé avec succès (${state.allMovies.length} films disponibles)`);
      }
    } catch (err) {
      console.error('Erreur lors du chargement des films:', err);
      if (state.allMovies.length === 0) {
        showErrorState(err.message || 'Impossible de charger le catalogue.');
      } else {
        // Si on a déjà des films en mémoire, on n'efface pas l'écran, on avertit juste l'utilisateur
        showToast('Impossible d\'actualiser pour le moment. Conservation du catalogue actuel.');
      }
    } finally {
      state.isLoading = false;
      hideLoadingState();
    }
  }

  // ==========================================================================
  // TRI STRICT PAR DATE DÉCROISSANTE (PLUS RÉCENT EN PREMIER)
  // ==========================================================================
  function sortMoviesByDateDesc(movies) {
    return [...movies].sort((a, b) => {
      const tsA = getMovieTimestamp(a);
      const tsB = getMovieTimestamp(b);
      return tsB - tsA;
    });
  }

  function getMovieTimestamp(movie) {
    if (typeof movie.publishedTimestamp === 'number' && movie.publishedTimestamp > 0) {
      return movie.publishedTimestamp;
    }
    if (movie.publishDate) {
      const parsed = Date.parse(movie.publishDate);
      if (!isNaN(parsed)) return Math.floor(parsed / 1000);
    }
    return 0;
  }

  // ==========================================================================
  // FILTRAGE CÔTÉ CLIENT
  // ==========================================================================
  function applyFiltersAndRender() {
    const query = state.searchQuery.trim().toLowerCase();
    const category = state.currentCategory;
    const subFilter = state.subFilter;

    let filtered = state.allMovies.filter(movie => {
      // 1. Filtre Sous-titres
      if (subFilter === 'native') {
        if (movie.subtitleType !== 'native_fr') return false;
      }

      // 2. Filtre Puce / Catégorie
      if (category === 'sooner') {
        const isSooner = movie.isPaid === true ||
          (movie.channelName && movie.channelName.toLowerCase().includes('sooner')) ||
          (movie.paidProvider && movie.paidProvider.toLowerCase().includes('sooner'));
        if (!isSooner) return false;
      } else if (category === 'kr') {
        if (movie.country !== 'kr') return false;
      } else if (category === 'jp') {
        if (movie.country !== 'jp') return false;
      } else if (category === 'cn') {
        if (movie.country !== 'cn') return false;
      } else if (category === 'kofa') {
        const isKofa = (movie.category === 'kofa') ||
          (movie.channelName && (
            movie.channelName.toLowerCase().includes('koreanfilm') ||
            movie.channelName.toLowerCase().includes('korean film archive')
          ));
        if (!isKofa) return false;
      } else if (category === 'native') {
        if (movie.subtitleType !== 'native_fr') return false;
      } else if (['thriller', 'drama', 'horror', 'comedy'].includes(category)) {
        const matchesCategory = movie.category === category;
        const textContent = `${movie.title} ${movie.description || ''}`.toLowerCase();
        const matchesKeyword = matchesCategory || textContent.includes(category);
        if (!matchesKeyword) return false;
      }

      // 3. Filtre Texte Recherche
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

      return true;
    });

    // Garantir le tri par date décroissante
    state.filteredMovies = sortMoviesByDateDesc(filtered);

    updateStatusBar();
    renderMoviesGrid();
  }

  // ==========================================================================
  // RENDU DU BANDEAU D'ÉTAT
  // ==========================================================================
  function updateStatusBar() {
    const totalCount = state.filteredMovies.length;
    const allCount = state.allMovies.length;

    if (state.searchQuery || state.currentCategory !== 'all' || state.subFilter !== 'all') {
      DOM.movieCount.textContent = `${totalCount} film${totalCount > 1 ? 's' : ''} trouvé${totalCount > 1 ? 's' : ''} (sur ${allCount})`;
    } else {
      DOM.movieCount.textContent = `${totalCount} film${totalCount > 1 ? 's' : ''} disponible${totalCount > 1 ? 's' : ''}`;
    }

    // Badge de filtre actif
    let activeFilterLabel = '';
    if (state.currentCategory === 'sooner') {
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
    } else if (state.currentCategory !== 'all') {
      activeFilterLabel = `Genre : ${state.currentCategory.toUpperCase()}`;
    }

    if (state.subFilter === 'native' && state.currentCategory !== 'native') {
      activeFilterLabel += activeFilterLabel ? ' • ST-FR Natif' : 'ST-FR Natif uniquement';
    }

    if (state.searchQuery) {
      activeFilterLabel += activeFilterLabel ? ` • Recherche : "${state.searchQuery}"` : `Recherche : "${state.searchQuery}"`;
    }

    if (activeFilterLabel) {
      DOM.activeFilterBadge.textContent = activeFilterLabel;
      DOM.activeFilterBadge.style.display = 'inline-block';
    } else {
      DOM.activeFilterBadge.textContent = '';
      DOM.activeFilterBadge.style.display = 'none';
    }
  }

  // ==========================================================================
  // RENDU DE LA GRILLE DES FILMS
  // ==========================================================================
  function renderMoviesGrid() {
    DOM.moviesGrid.innerHTML = '';

    if (state.filteredMovies.length === 0) {
      DOM.emptyState.classList.remove('hidden');
      if (state.searchQuery) {
        DOM.emptyDesc.textContent = `Aucun film ne correspond à votre recherche "${state.searchQuery}".`;
      } else {
        DOM.emptyDesc.textContent = 'Aucun film ne correspond aux filtres sélectionnés.';
      }
      return;
    }

    DOM.emptyState.classList.add('hidden');

    const fragment = document.createDocumentFragment();

    state.filteredMovies.forEach(movie => {
      const card = createMovieCard(movie);
      fragment.appendChild(card);
    });

    DOM.moviesGrid.appendChild(fragment);
  }

  /**
   * Crée l'élément HTML complet d'une carte film style YouTube
   */
  function createMovieCard(movie) {
    const card = document.createElement('article');
    card.className = 'movie-card';
    card.tabIndex = 0;
    card.setAttribute('role', 'button');
    card.setAttribute('aria-label', `Voir le film : ${movie.title}`);

    // Détermination des badges
    const isNative = movie.subtitleType === 'native_fr';
    const subBadgeClass = isNative ? 'native' : 'auto';
    const subBadgeText = isNative ? '🇫🇷 ST-FR Natif' : '🇫🇷 ST-FR Auto (CC)';

    const isPaid = Boolean(movie.isPaid);
    const paidBadgeHtml = isPaid
      ? `<span class="badge-paid-top" title="${escapeHtml(movie.paidLabel || 'Visionnage payant sur YouTube')}">
           <span class="yt-paid-dot" aria-hidden="true"></span> Sooner
         </span>`
      : '';

    const paidInfoLine = isPaid
      ? `<div class="movie-paid-line">
           <span class="yt-paid-dot" aria-hidden="true"></span>
           <span>${escapeHtml(movie.paidProvider || 'Sooner (@soonerfrance)')}</span>
         </div>`
      : '';

    // Miniature avec fallback
    const thumbUrl = movie.thumbnail || `https://i.ytimg.com/vi/${movie.videoId}/hqdefault.jpg`;

    // Avatar chaîne
    const avatarUrl = movie.channelAvatar || '';
    const channelInitial = (movie.channelName || 'Y').charAt(0).toUpperCase();

    const avatarHtml = avatarUrl
      ? `<img class="channel-avatar-img" src="${escapeHtml(avatarUrl)}" alt="${escapeHtml(movie.channelName)}" loading="lazy" onerror="this.outerHTML='<div class=\\'channel-avatar-fallback\\'>${channelInitial}</div>'">`
      : `<div class="channel-avatar-fallback">${channelInitial}</div>`;

    // Coche vérifiée
    const verifiedHtml = movie.channelVerified
      ? `<svg class="verified-icon" viewBox="0 0 24 24" aria-label="Chaîne vérifiée"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>`
      : '';

    const countryFlag = movie.country === 'kr' ? '🇰🇷 ' : movie.country === 'jp' ? '🇯🇵 ' : movie.country === 'cn' ? '🇨🇳 ' : '';

    card.innerHTML = `
      <div class="thumbnail-wrapper">
        <img class="thumbnail-img" src="${escapeHtml(thumbUrl)}" alt="${escapeHtml(movie.title)}" loading="lazy">
        
        <span class="badge-subtitle-top ${subBadgeClass}">${countryFlag}${subBadgeText}</span>
        ${paidBadgeHtml}
        
        <span class="badge-duration-bottom">${escapeHtml(movie.durationFormatted || '')}</span>

        <!-- Bouton direct pour visionner sur YouTube sans ouvrir la modale -->
        <a 
          href="${escapeHtml(movie.youtubeUrl)}" 
          target="_blank" 
          rel="noopener noreferrer" 
          class="card-yt-direct-btn" 
          title="Regarder directement sur YouTube dans un nouvel onglet"
          tabindex="0"
        >
          <svg viewBox="0 0 24 24" width="13" height="13" fill="currentColor">
            <path d="M10 15l5-3-5-3v6z"/>
          </svg>
          <span>Sur YouTube ↗</span>
        </a>

        <div class="play-overlay-btn" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor">
            <path d="M8 5v14l11-7z"/>
          </svg>
        </div>
      </div>

      <div class="movie-details">
        <div class="channel-avatar-wrapper">
          ${avatarHtml}
        </div>
        <div class="movie-text-content">
          <h3 class="movie-card-title" title="${escapeHtml(movie.title)}">${escapeHtml(movie.title)}</h3>
          <div class="movie-channel-line">
            <span>${escapeHtml(movie.channelName || '')}</span>
            ${verifiedHtml}
          </div>
          <div class="movie-meta-line">
            <span>${escapeHtml(movie.viewCountFormatted || 'Vues non indiquées')}</span>
            <span>•</span>
            <span title="Date de publication : ${escapeHtml(movie.publishedFormatted || movie.publishDate || '')}">
              ${escapeHtml(movie.publishedRelative || movie.publishedFormatted || '')}
            </span>
          </div>
          ${paidInfoLine}
        </div>
      </div>
    `;

    // Clic sur le bouton direct "Sur YouTube" : ne pas ouvrir la modale
    const ytDirectBtn = card.querySelector('.card-yt-direct-btn');
    if (ytDirectBtn) {
      ytDirectBtn.addEventListener('click', (e) => {
        e.stopPropagation();
      });
      ytDirectBtn.addEventListener('keydown', (e) => {
        e.stopPropagation();
      });
    }

    // Clic sur la carte : ouvre la modale Lecteur Cinéma
    card.addEventListener('click', () => {
      openMovieModal(movie);
    });

    // Accessibilité Clavier
    card.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        openMovieModal(movie);
      }
    });

    return card;
  }

  // ==========================================================================
  // MODALE LECTEUR CINÉMA & LECTEUR INTÉGRÉ
  // ==========================================================================

  /**
   * Construit l'URL d'intégration YouTube sécurisée et non tronquée.
   * ATTENTION : autoplay=0 est volontairement appliqué suite aux retours utilisateurs
   * afin de ne pas déclencher le son et la lecture automatiquement.
   */
  function buildEmbedUrl(movie) {
    const videoId = movie.videoId || movie.id;
    // autoplay=0 : l'utilisateur choisit quand lancer la vidéo
    return `https://www.youtube.com/embed/${videoId}?autoplay=0&cc_load_policy=1&cc_lang_pref=fr&hl=fr&fs=1&rel=0`;
  }

  function openMovieModal(movie) {
    state.selectedMovie = movie;

    // Configuration de l'iframe YouTube (sans autoplay automatique)
    DOM.modalIframe.src = buildEmbedUrl(movie);

    // Titre
    DOM.modalMovieTitle.textContent = movie.title || '';

    // Lien YouTube Externe
    DOM.modalYtLink.href = movie.youtubeUrl || `https://www.youtube.com/watch?v=${movie.videoId}`;

    // Avatar et Chaîne
    const avatarUrl = movie.channelAvatar || '';
    const channelInitial = (movie.channelName || 'Y').charAt(0).toUpperCase();
    if (avatarUrl) {
      DOM.modalChannelAvatar.innerHTML = `<img class="channel-avatar-img" src="${escapeHtml(avatarUrl)}" alt="${escapeHtml(movie.channelName)}" onerror="this.outerHTML='<div class=\\'channel-avatar-fallback\\'>${channelInitial}</div>'">`;
    } else {
      DOM.modalChannelAvatar.innerHTML = `<div class="channel-avatar-fallback">${channelInitial}</div>`;
    }

    DOM.modalChannelName.textContent = movie.channelName || 'Chaîne YouTube';

    if (movie.channelVerified) {
      DOM.modalChannelVerified.classList.remove('hidden');
    } else {
      DOM.modalChannelVerified.classList.add('hidden');
    }

    // Statistiques et Date
    const statsText = `${movie.viewCountFormatted || ''} • Publié le ${movie.publishedFormatted || movie.publishDate || 'date inconnue'}`;
    DOM.modalStatsText.textContent = statsText;

    // Badges Sous-titres & Durée
    const isNative = movie.subtitleType === 'native_fr';
    DOM.modalSubtitleBadge.className = `badge-subtitle ${isNative ? 'native' : 'auto'}`;
    DOM.modalSubtitleBadge.textContent = isNative ? '🇫🇷 ST-FR Natif' : '🇫🇷 ST-FR Auto (CC)';

    DOM.modalDurationBadge.textContent = movie.durationFormatted || '';

    // Message d'aide Sous-titres FR (explication claire de la limitation du lecteur intégré YouTube)
    const ytDirectUrl = movie.youtubeUrl || `https://www.youtube.com/watch?v=${movie.videoId}`;
    if (DOM.modalSubHelp) {
      DOM.modalSubHelp.className = `sub-help-banner ${isNative ? 'native' : 'auto'}`;
    }

    if (isNative) {
      DOM.modalSubHelpText.innerHTML = `
        <div><strong>🇫🇷 Sous-titres français natifs ou VF disponibles.</strong> Cliquez sur Lecture (▶) pour lancer le film.</div>
        <div style="font-size: 12px; opacity: 0.9;">💡 <em>Astuce : Si ce film n'a que des sous-titres étrangers dans ce lecteur intégré (YouTube bloque l'option « Traduire automatiquement » hors de son site), ouvrez-le directement sur YouTube :</em></div>
        <a href="${escapeHtml(ytDirectUrl)}" target="_blank" rel="noopener noreferrer" class="sub-help-yt-btn">
          ▶ Ouvrir sur YouTube (Menu Traduction Auto FR complet) ↗
        </a>
      `;
    } else {
      DOM.modalSubHelpText.innerHTML = `
        <div><strong>⚠️ Limitation du lecteur intégré YouTube :</strong> YouTube a désactivé le sous-menu <em>« Traduire automatiquement »</em> dans les lecteurs intégrés (cliquer sur <em>Sous-titres</em> ici ne fait que les décocher/recocher dans la langue d'origine).</div>
        <div><strong>👉 Pour activer la traduction automatique en Français :</strong> ouvrez le film sur le site YouTube ci-dessous, puis cliquez sur <strong>⚙️ Paramètres > Sous-titres > Traduire automatiquement > Français</strong>.</div>
        <a href="${escapeHtml(ytDirectUrl)}" target="_blank" rel="noopener noreferrer" class="sub-help-yt-btn">
          ▶ Regarder sur YouTube avec Traduction Auto FR ↗
        </a>
      `;
    }

    // Description & Langues
    DOM.modalDescription.textContent = movie.description || 'Aucune description fournie.';

    if (Array.isArray(movie.availableLanguages) && movie.availableLanguages.length > 0) {
      DOM.modalSubLanguagesList.textContent = movie.availableLanguages.join(', ').toUpperCase();
      DOM.modalSubtitlesLanguages.classList.remove('hidden');
    } else {
      DOM.modalSubLanguagesList.textContent = isNative ? 'Français (FR)' : 'Français (traduction auto YouTube)';
      DOM.modalSubtitlesLanguages.classList.remove('hidden');
    }

    // Affichage de la modale
    DOM.movieModal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';

    // Focus sur le bouton de fermeture pour navigation clavier
    DOM.closeModalBtn.focus();
  }

  function closeMovieModal() {
    // Si en plein écran, quitter le plein écran d'abord
    if (isFullscreenActive()) {
      exitFullscreen();
    }

    // Couper la vidéo en vidant la source de l'iframe
    DOM.modalIframe.src = '';
    DOM.movieModal.classList.add('hidden');
    document.body.style.overflow = '';
    state.selectedMovie = null;
  }

  // ==========================================================================
  // GESTION DU PLEIN ÉCRAN (FULLSCREEN API)
  // ==========================================================================
  function isFullscreenActive() {
    return Boolean(
      document.fullscreenElement ||
      document.webkitFullscreenElement ||
      document.mozFullScreenElement ||
      document.msFullscreenElement
    );
  }

  function toggleFullscreen() {
    const targetElement = DOM.modalPlayerContainer || document.getElementById('modalPlayerContainer');
    if (!targetElement) return;

    if (!isFullscreenActive()) {
      if (targetElement.requestFullscreen) {
        targetElement.requestFullscreen().catch(err => console.warn('Plein écran refusé:', err));
      } else if (targetElement.webkitRequestFullscreen) {
        targetElement.webkitRequestFullscreen();
      } else if (targetElement.mozRequestFullScreen) {
        targetElement.mozRequestFullScreen();
      } else if (targetElement.msRequestFullscreen) {
        targetElement.msRequestFullscreen();
      }
    } else {
      exitFullscreen();
    }
  }

  function exitFullscreen() {
    if (document.exitFullscreen) {
      document.exitFullscreen().catch(err => console.warn('Erreur sortie plein écran:', err));
    } else if (document.webkitExitFullscreen) {
      document.webkitExitFullscreen();
    } else if (document.mozCancelFullScreen) {
      document.mozCancelFullScreen();
    } else if (document.msExitFullscreen) {
      document.msExitFullscreen();
    }
  }

  function updateFullscreenUI() {
    const inFs = isFullscreenActive();
    if (DOM.fullscreenBtn) {
      if (inFs) {
        DOM.fullscreenBtn.classList.add('active');
        if (DOM.fullscreenBtnText) DOM.fullscreenBtnText.textContent = 'Quitter plein écran';
      } else {
        DOM.fullscreenBtn.classList.remove('active');
        if (DOM.fullscreenBtnText) DOM.fullscreenBtnText.textContent = 'Plein écran';
      }
    }
  }

  // ==========================================================================
  // NOTIFICATIONS TOAST
  // ==========================================================================
  function showToast(message, duration = 3500) {
    if (!DOM.toast || !DOM.toastMessage) return;

    DOM.toastMessage.textContent = message;
    DOM.toast.classList.remove('hidden');
    DOM.toast.classList.add('visible');

    if (toastTimer) clearTimeout(toastTimer);

    toastTimer = setTimeout(() => {
      DOM.toast.classList.remove('visible');
      setTimeout(() => {
        DOM.toast.classList.add('hidden');
      }, 300);
    }, duration);
  }

  // ==========================================================================
  // SQUELETTES DE CHARGEMENT & ÉTATS D'ERREUR
  // ==========================================================================
  function showLoadingState(isRefresh = false) {
    if (isRefresh && DOM.refreshBtn) {
      DOM.refreshBtn.classList.add('refreshing');
      DOM.refreshBtn.setAttribute('disabled', 'true');
    }

    if (!isRefresh && state.allMovies.length === 0) {
      renderSkeletons(12);
      DOM.movieCount.textContent = 'Chargement des films asiatiques...';
    }
  }

  function hideLoadingState() {
    if (DOM.refreshBtn) {
      DOM.refreshBtn.classList.remove('refreshing');
      DOM.refreshBtn.removeAttribute('disabled');
    }
  }

  function renderSkeletons(count = 12) {
    DOM.moviesGrid.innerHTML = '';
    const fragment = document.createDocumentFragment();

    for (let i = 0; i < count; i++) {
      const skeleton = document.createElement('div');
      skeleton.className = 'skeleton-card';
      skeleton.innerHTML = `
        <div class="skeleton-thumbnail"></div>
        <div class="skeleton-details">
          <div class="skeleton-avatar"></div>
          <div class="skeleton-text-group">
            <div class="skeleton-line title-1"></div>
            <div class="skeleton-line title-2"></div>
            <div class="skeleton-line channel"></div>
            <div class="skeleton-line meta"></div>
          </div>
        </div>
      `;
      fragment.appendChild(skeleton);
    }

    DOM.moviesGrid.appendChild(fragment);
  }

  function showErrorState(msg) {
    DOM.moviesGrid.innerHTML = '';
    DOM.emptyState.classList.add('hidden');
    DOM.errorState.classList.remove('hidden');
    if (DOM.errorMsg) DOM.errorMsg.textContent = msg;
  }

  function hideErrorState() {
    DOM.errorState.classList.add('hidden');
  }

  // ==========================================================================
  // ÉCOUTEURS D'ÉVÉNEMENTS
  // ==========================================================================
  function setupEventListeners() {
    // 1. Barre de recherche
    DOM.searchInput.addEventListener('input', (e) => {
      const val = e.target.value;
      if (val.trim()) {
        DOM.clearSearchBtn.classList.remove('hidden');
      } else {
        DOM.clearSearchBtn.classList.add('hidden');
      }

      clearTimeout(searchDebounceTimer);
      searchDebounceTimer = setTimeout(() => {
        state.searchQuery = val;
        applyFiltersAndRender();
      }, 250);
    });

    DOM.clearSearchBtn.addEventListener('click', () => {
      DOM.searchInput.value = '';
      DOM.clearSearchBtn.classList.add('hidden');
      state.searchQuery = '';
      DOM.searchInput.focus();
      applyFiltersAndRender();
    });

    DOM.searchForm.addEventListener('submit', (e) => {
      e.preventDefault();
      clearTimeout(searchDebounceTimer);
      state.searchQuery = DOM.searchInput.value;
      applyFiltersAndRender();
    });

    // 2. Filtre sous-titres
    DOM.subFilter.addEventListener('change', (e) => {
      state.subFilter = e.target.value;
      applyFiltersAndRender();
    });

    // 3. Bouton Actualiser
    DOM.refreshBtn.addEventListener('click', () => {
      loadMovies(true);
    });

    // 4. Barre de puces (Chips)
    if (DOM.chipsTrack) {
      DOM.chipsTrack.addEventListener('click', (e) => {
        const chip = e.target.closest('.chip');
        if (!chip) return;

        DOM.chips.forEach(c => c.classList.remove('active'));
        chip.classList.add('active');

        state.currentCategory = chip.dataset.category || 'all';
        applyFiltersAndRender();
      });
    }

    // 5. Boutons de réinitialisation
    if (DOM.resetFiltersBtn) {
      DOM.resetFiltersBtn.addEventListener('click', () => {
        state.searchQuery = '';
        state.currentCategory = 'all';
        state.subFilter = 'all';

        DOM.searchInput.value = '';
        DOM.clearSearchBtn.classList.add('hidden');
        DOM.subFilter.value = 'all';

        DOM.chips.forEach(c => {
          c.classList.toggle('active', c.dataset.category === 'all');
        });

        applyFiltersAndRender();
      });
    }

    if (DOM.retryFetchBtn) {
      DOM.retryFetchBtn.addEventListener('click', () => {
        loadMovies(false);
      });
    }

    // 6. Fermeture de la modale
    DOM.closeModalBtn.addEventListener('click', closeMovieModal);

    DOM.movieModal.addEventListener('click', (e) => {
      if (e.target === DOM.movieModal) {
        closeMovieModal();
      }
    });

    // 7. Plein Écran
    if (DOM.fullscreenBtn) {
      DOM.fullscreenBtn.addEventListener('click', toggleFullscreen);
    }

    if (DOM.overlayFullscreenBtn) {
      DOM.overlayFullscreenBtn.addEventListener('click', toggleFullscreen);
    }

    // Événements d'état Plein Écran du navigateur
    ['fullscreenchange', 'webkitfullscreenchange', 'mozfullscreenchange', 'MSFullscreenChange'].forEach(evt => {
      document.addEventListener(evt, updateFullscreenUI);
    });

    // 8. Raccourcis Clavier
    document.addEventListener('keydown', (e) => {
      // Si la modale est active
      if (!DOM.movieModal.classList.contains('hidden')) {
        if (e.key === 'Escape') {
          closeMovieModal();
        } else if ((e.key === 'f' || e.key === 'F') && document.activeElement !== DOM.searchInput) {
          e.preventDefault();
          toggleFullscreen();
        }
      }
    });
  }

  // ==========================================================================
  // UTILITAIRES
  // ==========================================================================
  function escapeHtml(text) {
    if (!text) return '';
    return String(text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  // Démarrage automatique au chargement du DOM
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();