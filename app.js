/**
 * K-CinéTube FR - Application JavaScript
 * Catalogue de films coréens avec sous-titres français sur YouTube
 * Triés par date décroissante de publication sur YouTube
 */

(function () {
  'use strict';

  // =========================================================================
  // ÉTAT DE L'APPLICATION
  // =========================================================================
  const state = {
    movies: [],
    currentCategory: 'all',
    currentSubFilter: 'all', // 'all' ou 'native'
    currentQuery: '',
    isLoading: false,
    selectedMovie: null
  };

  // =========================================================================
  // ÉLÉMENTS DU DOM
  // =========================================================================
  const DOM = {
    searchForm: document.getElementById('searchForm'),
    searchInput: document.getElementById('searchInput'),
    clearSearchBtn: document.getElementById('clearSearchBtn'),
    searchBtn: document.getElementById('searchBtn'),
    subFilter: document.getElementById('subFilter'),
    refreshBtn: document.getElementById('refreshBtn'),
    chipsTrack: document.getElementById('chipsTrack'),
    chips: document.querySelectorAll('.chip'),
    statusBar: document.getElementById('statusBar'),
    movieCount: document.getElementById('movieCount'),
    activeFilterBadge: document.getElementById('activeFilterBadge'),
    moviesGrid: document.getElementById('moviesGrid'),
    emptyState: document.getElementById('emptyState'),
    emptyDesc: document.getElementById('emptyDesc'),
    resetFiltersBtn: document.getElementById('resetFiltersBtn'),
    errorState: document.getElementById('errorState'),
    errorMsg: document.getElementById('errorMsg'),
    retryFetchBtn: document.getElementById('retryFetchBtn'),
    // Modale
    movieModal: document.getElementById('movieModal'),
    closeModalBtn: document.getElementById('closeModalBtn'),
    modalPlayerContainer: document.getElementById('modalPlayerContainer'),
    modalIframe: document.getElementById('modalIframe'),
    fullscreenBtn: document.getElementById('fullscreenBtn'),
    fullscreenBtnText: document.getElementById('fullscreenBtnText'),
    overlayFullscreenBtn: document.getElementById('overlayFullscreenBtn'),
    modalSubHelp: document.getElementById('modalSubHelp'),
    modalSubHelpText: document.getElementById('modalSubHelpText'),
    modalMovieTitle: document.getElementById('modalMovieTitle'),
    modalYtLink: document.getElementById('modalYtLink'),
    modalChannelAvatar: document.getElementById('modalChannelAvatar'),
    modalChannelName: document.getElementById('modalChannelName'),
    modalChannelVerified: document.getElementById('modalChannelVerified'),
    modalStatsText: document.getElementById('modalStatsText'),
    modalSubtitleBadge: document.getElementById('modalSubtitleBadge'),
    modalDurationBadge: document.getElementById('modalDurationBadge'),
    modalDescription: document.getElementById('modalDescription'),
    modalSubLanguagesList: document.getElementById('modalSubLanguagesList'),
    // Toast
    toast: document.getElementById('toastNotification'),
    toastMessage: document.getElementById('toastMessage')
  };

  // =========================================================================
  // DONNÉES DE SECOURS (Si l'API /api/movies n'est pas encore démarrée)
  // Permet de tester le Frontend immédiatement avec de vrais films coréens KOFA / VOSTFR
  // =========================================================================
  const FALLBACK_MOVIES = [
    {
      id: "o0w7v-e2vY0",
      videoId: "o0w7v-e2vY0",
      title: "Aimless Bullet (Obaltan, 오발탄) - Chef-d'œuvre du cinéma coréen (1961)",
      channelName: "Korean Film Archive (KOFA)",
      channelAvatar: "https://yt3.googleusercontent.com/ytc/AIdro_n4g-aO0kHhJkW8B98ZJ6e8z8eZ7_Gz8m4n=s176-c-k-c0x00ffffff-no-rj",
      channelVerified: true,
      thumbnail: "https://i.ytimg.com/vi/o0w7v-e2vY0/hqdefault.jpg",
      duration: "1:47:20",
      durationFormatted: "1:47:20",
      subtitleType: "native_fr",
      subtitleLanguages: ["Français", "Anglais", "Coréen"],
      viewCount: 382400,
      viewCountFormatted: "382 k vues",
      publishedAt: "2024-10-15T10:00:00Z",
      publishDate: "2024-10-15",
      publishedFormatted: "15 oct. 2024",
      publishedRelative: "il y a 6 jours",
      publishedTimestamp: 1729000000000,
      description: "Le chef-d'œuvre indémodable du cinéma classique coréen réalisé par Yu Hyun-mok. À Séoul au lendemain de la guerre de Corée, une famille tente de survivre dans la misère et le traumatisme.",
      category: "drama"
    },
    {
      id: "uKq3sW4nZ8s",
      videoId: "uKq3sW4nZ8s",
      title: "The Housemaid (Hanyeo, 하녀) - Thriller psychologique culte de Kim Ki-young (1960)",
      channelName: "Korean Film Archive (KOFA)",
      channelAvatar: "https://yt3.googleusercontent.com/ytc/AIdro_n4g-aO0kHhJkW8B98ZJ6e8z8eZ7_Gz8m4n=s176-c-k-c0x00ffffff-no-rj",
      channelVerified: true,
      thumbnail: "https://i.ytimg.com/vi/uKq3sW4nZ8s/hqdefault.jpg",
      duration: "1:51:30",
      durationFormatted: "1:51:30",
      subtitleType: "native_fr",
      subtitleLanguages: ["Français", "Anglais", "Coréen"],
      viewCount: 1250000,
      viewCountFormatted: "1,2 M de vues",
      publishedAt: "2024-09-28T14:30:00Z",
      publishDate: "2024-09-28",
      publishedFormatted: "28 sept. 2024",
      publishedRelative: "il y a 3 semaines",
      publishedTimestamp: 1727533800000,
      description: "L'un des thrillers les plus influents du cinéma coréen, cité par Bong Joon-ho comme inspiration majeure pour Parasite. Un professeur de musique embauche une jeune servante qui va semer la discorde.",
      category: "thriller"
    },
    {
      id: "3e5a7b8c9d0",
      videoId: "3e5a7b8c9d0",
      title: "Chilsu and Mansu (칠수와 만수) - Chronique sociale & Comédie dramatique (1988)",
      channelName: "Korean Classic Film",
      channelAvatar: "https://yt3.googleusercontent.com/ytc/AIdro_n4g-aO0kHhJkW8B98ZJ6e8z8eZ7_Gz8m4n=s176-c-k-c0x00ffffff-no-rj",
      channelVerified: true,
      thumbnail: "https://images.unsplash.com/photo-1578632767115-351597cf2477?w=640&q=80",
      duration: "1:44:10",
      durationFormatted: "1:44:10",
      subtitleType: "auto_fr",
      subtitleLanguages: ["Coréen (original)", "Traduction automatique FR disponible"],
      viewCount: 94000,
      viewCountFormatted: "94 k vues",
      publishedAt: "2024-08-14T09:00:00Z",
      publishDate: "2024-08-14",
      publishedFormatted: "14 août 2024",
      publishedRelative: "il y a 2 mois",
      publishedTimestamp: 1723626000000,
      description: "Film emblématique de Park Kwang-su mettant en vedette Park Joong-hoon et Ahn Sung-ki. Deux peintres d'enseignes publicitaires perchés au sommet d'un gratte-ciel de Séoul se retrouvent pris dans un quiproquo géant.",
      category: "comedy"
    },
    {
      id: "7f8g9h0i1j2",
      videoId: "7f8g9h0i1j2",
      title: "Suddenly in Dark Night (깊은 밤 갑자기) - Horreur & Mystère Coréen (1981)",
      channelName: "Korean Film Archive (KOFA)",
      channelAvatar: "https://yt3.googleusercontent.com/ytc/AIdro_n4g-aO0kHhJkW8B98ZJ6e8z8eZ7_Gz8m4n=s176-c-k-c0x00ffffff-no-rj",
      channelVerified: true,
      thumbnail: "https://images.unsplash.com/photo-1509281373149-e957c6296406?w=640&q=80",
      duration: "1:38:45",
      durationFormatted: "1:38:45",
      subtitleType: "native_fr",
      subtitleLanguages: ["Français", "Anglais"],
      viewCount: 420000,
      viewCountFormatted: "420 k vues",
      publishedAt: "2024-07-02T16:20:00Z",
      publishDate: "2024-07-02",
      publishedFormatted: "2 juil. 2024",
      publishedRelative: "il y a 3 mois",
      publishedTimestamp: 1719937200000,
      description: "Un chef-d'œuvre du cinéma d'horreur psychologique et gothique coréen des années 80 par Go Yeong-nam. Une poupée de chaman ancestrale et une jeune servante troublent une maîtresse de maison.",
      category: "horror"
    },
    {
      id: "2b4c6d8e0f1",
      videoId: "2b4c6d8e0f1",
      title: "Sopyonje (서편제) - Drame musical Pansori traditionnel (1993)",
      channelName: "Korean Classic Film",
      channelAvatar: "https://yt3.googleusercontent.com/ytc/AIdro_n4g-aO0kHhJkW8B98ZJ6e8z8eZ7_Gz8m4n=s176-c-k-c0x00ffffff-no-rj",
      channelVerified: true,
      thumbnail: "https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=640&q=80",
      duration: "1:52:00",
      durationFormatted: "1:52:00",
      subtitleType: "native_fr",
      subtitleLanguages: ["Français", "Anglais", "Coréen"],
      viewCount: 890000,
      viewCountFormatted: "890 k vues",
      publishedAt: "2024-05-19T11:15:00Z",
      publishDate: "2024-05-19",
      publishedFormatted: "19 mai 2024",
      publishedRelative: "il y a 5 mois",
      publishedTimestamp: 1716117300000,
      description: "Réalisé par le maître Im Kwon-taek, premier film coréen à dépasser le million d'entrées à Séoul. L'histoire poignante d'une famille d'artistes ambulants de pansori à travers la Corée rurale.",
      category: "drama"
    },
    {
      id: "9k8j7h6g5f4",
      videoId: "9k8j7h6g5f4",
      title: "The Coachman (Mabu, 마부) - Ours d'Argent Berlin 1961 (Drame)",
      channelName: "Korean Film Archive (KOFA)",
      channelAvatar: "https://yt3.googleusercontent.com/ytc/AIdro_n4g-aO0kHhJkW8B98ZJ6e8z8eZ7_Gz8m4n=s176-c-k-c0x00ffffff-no-rj",
      channelVerified: true,
      thumbnail: "https://images.unsplash.com/photo-1485846234645-a62644f84728?w=640&q=80",
      duration: "1:45:00",
      durationFormatted: "1:45:00",
      subtitleType: "native_fr",
      subtitleLanguages: ["Français", "Anglais", "Allemand"],
      viewCount: 215000,
      viewCountFormatted: "215 k vues",
      publishedAt: "2024-03-10T08:00:00Z",
      publishDate: "2024-03-10",
      publishedFormatted: "10 mars 2024",
      publishedRelative: "il y a 7 mois",
      publishedTimestamp: 1710057600000,
      description: "Premier film coréen à remporter un prix majeur dans un festival international (Ours d'argent extraordinaire à la Berlinale 1961). Réalisé par Kang Dae-jin avec Kim Seung-ho.",
      category: "drama"
    }
  ];

  // =========================================================================
  // FONCTIONS UTILITAIRES & FORMATAGE
  // =========================================================================

  /**
   * Trie défensivement une liste de films par date de publication décroissante
   */
  function defensiveSortByDateDesc(movies) {
    if (!Array.isArray(movies)) return [];
    return [...movies].sort((a, b) => {
      const timeA = getTimestamp(a);
      const timeB = getTimestamp(b);
      return timeB - timeA;
    });
  }

  /**
   * Extrait un timestamp numérique depuis les champs variés d'un film
   */
  function getTimestamp(movie) {
    if (!movie) return 0;
    if (typeof movie.publishedTimestamp === 'number' && !isNaN(movie.publishedTimestamp)) {
      return movie.publishedTimestamp;
    }
    const dateStr = movie.publishedAt || movie.publishDate || movie.publishedDate || movie.date;
    if (dateStr) {
      const ts = new Date(dateStr).getTime();
      if (!isNaN(ts)) return ts;
    }
    return 0;
  }

  /**
   * Échappement HTML sécurisé pour éviter toute faille XSS
   */
  function escapeHTML(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  /**
   * Formate la durée (e.g. "1:45:20" ou "52:10")
   */
  function formatDuration(movie) {
    if (movie.durationFormatted) return movie.durationFormatted;
    if (typeof movie.duration === 'string') return movie.duration;
    if (typeof movie.duration === 'number' && !isNaN(movie.duration)) {
      const totalSec = Math.floor(movie.duration);
      const h = Math.floor(totalSec / 3600);
      const m = Math.floor((totalSec % 3600) / 60);
      const s = totalSec % 60;
      if (h > 0) {
        return `${h}:${m < 10 ? '0' : ''}${m}:${s < 10 ? '0' : ''}${s}`;
      }
      return `${m}:${s < 10 ? '0' : ''}${s}`;
    }
    return 'Film';
  }

  /**
   * Formate le nombre de vues YouTube
   */
  function formatViews(movie) {
    if (movie.viewCountFormatted) return movie.viewCountFormatted;
    const views = Number(movie.viewCount);
    if (isNaN(views)) return 'Vues indisponibles';
    if (views >= 1000000) {
      return `${(views / 1000000).toFixed(1).replace('.', ',')} M de vues`;
    }
    if (views >= 1000) {
      return `${Math.round(views / 1000)} k vues`;
    }
    return `${views} vue${views > 1 ? 's' : ''}`;
  }

  /**
   * Formate la date de publication exacte
   */
  function formatPublishedDate(movie) {
    if (movie.publishedFormatted) return movie.publishedFormatted;
    const ts = getTimestamp(movie);
    if (!ts) return 'Date inconnue';
    try {
      const d = new Date(ts);
      return d.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' });
    } catch {
      return 'Date inconnue';
    }
  }

  /**
   * Formate la date relative (il y a X jours / mois / ans)
   */
  function formatRelativeDate(movie) {
    if (movie.publishedRelative) return movie.publishedRelative;
    const ts = getTimestamp(movie);
    if (!ts) return '';
    const now = Date.now();
    const diffSec = Math.floor((now - ts) / 1000);
    if (diffSec < 60) return "à l'instant";
    if (diffSec < 3600) return `il y a ${Math.floor(diffSec / 60)} min`;
    const diffHours = Math.floor(diffSec / 3600);
    if (diffHours < 24) return `il y a ${diffHours} heure${diffHours > 1 ? 's' : ''}`;
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) return `il y a ${diffDays} jour${diffDays > 1 ? 's' : ''}`;
    const diffWeeks = Math.floor(diffDays / 7);
    if (diffDays < 30) return `il y a ${diffWeeks} semaine${diffWeeks > 1 ? 's' : ''}`;
    const diffMonths = Math.floor(diffDays / 30);
    if (diffDays < 365) return `il y a ${diffMonths} mois`;
    const diffYears = Math.floor(diffDays / 365);
    return `il y a ${diffYears} an${diffYears > 1 ? 's' : ''}`;
  }

  /**
   * Construit l'URL d'intégration (iframe embed) avec sous-titres FR automatiques
   * Autoplay désactivé (autoplay=0) pour laisser l'utilisateur décider de lancer
   * la lecture ou de basculer directement sur YouTube.
   */
  function buildEmbedUrl(movie) {
    const videoId = movie.videoId || movie.id;
    if (movie.embedUrl && movie.embedUrl.includes('embed')) {
      const url = new URL(movie.embedUrl, window.location.origin);
      url.searchParams.set('autoplay', '0'); // Ne lance pas directement la vidéo
      url.searchParams.set('cc_load_policy', '1');
      url.searchParams.set('cc_lang_pref', 'fr');
      url.searchParams.set('hl', 'fr');
      url.searchParams.set('fs', '1');
      url.searchParams.set('rel', '0');
      return url.toString();
    }
    return `https://www.youtube.com/embed/${videoId}?autoplay=0&cc_load_policy=1&cc_lang_pref=fr&hl=fr&fs=1&rel=0`;
  }

  /**
   * Construit l'URL directe sur YouTube
   */
  function buildYoutubeUrl(movie) {
    if (movie.youtubeUrl) return movie.youtubeUrl;
    const videoId = movie.videoId || movie.id;
    return `https://www.youtube.com/watch?v=${videoId}`;
  }

  /**
   * Formate la liste des langues disponibles
   */
  function formatLanguagesList(languages) {
    if (Array.isArray(languages)) {
      return languages.join(', ');
    }
    if (typeof languages === 'string') return languages;
    return 'Français (FR)';
  }

  /**
   * Affichage d'un toast notification discret
   */
  let toastTimer = null;
  function showToast(message) {
    if (!DOM.toast || !DOM.toastMessage) return;
    DOM.toastMessage.textContent = message;
    DOM.toast.classList.remove('hidden');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      DOM.toast.classList.add('hidden');
    }, 3500);
  }

  // =========================================================================
  // RENDU DES SQUELETTES (SHIMMER SKELETONS)
  // =========================================================================
  function renderSkeletons(count = 8) {
    let skeletonsHtml = '';
    for (let i = 0; i < count; i++) {
      skeletonsHtml += `
        <div class="skeleton-card" aria-hidden="true">
          <div class="skeleton-thumbnail shimmer"></div>
          <div class="skeleton-details">
            <div class="skeleton-avatar shimmer"></div>
            <div class="skeleton-text-group">
              <div class="skeleton-line title-1 shimmer"></div>
              <div class="skeleton-line title-2 shimmer"></div>
              <div class="skeleton-line channel shimmer"></div>
              <div class="skeleton-line meta shimmer"></div>
            </div>
          </div>
        </div>
      `;
    }
    DOM.moviesGrid.innerHTML = skeletonsHtml;
    DOM.emptyState.classList.add('hidden');
    DOM.errorState.classList.add('hidden');
  }

  // =========================================================================
  // RENDU DE LA GRILLE DES FILMS
  // =========================================================================
  function renderMovies(movies) {
    if (!Array.isArray(movies) || movies.length === 0) {
      DOM.moviesGrid.innerHTML = '';
      DOM.emptyState.classList.remove('hidden');
      DOM.errorState.classList.add('hidden');
      DOM.movieCount.textContent = '0 film coréen trouvé';
      return;
    }

    DOM.emptyState.classList.add('hidden');
    DOM.errorState.classList.add('hidden');

    // Mise à jour du bandeau d'état avec détail par pays (Corée, Japon, Chine) et Sooner
    const krCount = movies.filter(m => m.country === 'kr').length;
    const jpCount = movies.filter(m => m.country === 'jp').length;
    const cnCount = movies.filter(m => m.country === 'cn').length;
    const paidCount = movies.filter(m => m.isPaid).length;
    const countrySummary = (krCount || jpCount || cnCount)
      ? ` — 🇰🇷 Corée : ${krCount} • 🇯🇵 Japon : ${jpCount} • 🇨🇳 Chine : ${cnCount}`
      : '';
    const paidSummary = paidCount > 0 ? ` • 🟢 ${paidCount} sur Sooner (@soonerfrance)` : '';
    DOM.movieCount.textContent = `${movies.length} film${movies.length > 1 ? 's' : ''} disponible${movies.length > 1 ? 's' : ''}${countrySummary}${paidSummary}`;
    
    // Badge informatif du filtre actuel
    updateFilterBadge();

    // Rendu des cartes de film
    DOM.moviesGrid.innerHTML = movies.map((movie, index) => {
      const isNative = movie.subtitleType === 'native_fr';
      const isPaid = Boolean(movie.isPaid);
      const countryPrefix = movie.countryLabel ? `${movie.countryLabel} • ` : '🇫🇷 ';
      const subBadgeText = movie.subtitleLabel || (isNative ? `${countryPrefix}ST-FR Natif` : `${countryPrefix}ST-FR Auto (CC)`);
      const subBadgeClass = isNative ? 'native' : 'auto';
      const duration = formatDuration(movie);
      const views = formatViews(movie);
      const pubDate = formatPublishedDate(movie);
      const pubRelative = formatRelativeDate(movie);
      const metaText = pubRelative ? `${views} • Publié le ${pubDate} (${pubRelative})` : `${views} • Publié le ${pubDate}`;

      // Miniature et fallback
      const videoId = movie.videoId || movie.id || '';
      const fallbackThumb = videoId ? `https://i.ytimg.com/vi/${videoId}/hqdefault.jpg` : '';
      const thumbUrl = movie.thumbnail || fallbackThumb;

      // Avatar de chaîne ou fallback initiale
      const initial = (movie.channelName || 'K').charAt(0).toUpperCase();

      return `
        <article 
          class="movie-card" 
          role="button" 
          tabindex="0" 
          data-index="${index}"
          aria-label="Regarder ${escapeHTML(movie.title)}"
        >
          <!-- Conteneur Miniature 16:9 -->
          <div class="thumbnail-wrapper">
            <img 
              class="thumbnail-img" 
              src="${escapeHTML(thumbUrl)}" 
              alt="${escapeHTML(movie.title)}" 
              loading="lazy"
              onerror="this.onerror=null; if('${videoId}') this.src='https://i.ytimg.com/vi/${videoId}/hqdefault.jpg';"
            />
            
            <!-- Badge Sous-titres Haut Gauche -->
            <span class="badge-subtitle-top ${subBadgeClass}" title="${isNative ? 'Sous-titres français créés nativement' : 'Sous-titres français via traduction automatique YouTube'}">
              ${subBadgeText}
            </span>

            ${isPaid ? `
              <!-- Badge Payant Haut Droite avec Point Vert YouTube -->
              <span class="badge-paid-top" title="Film payant sur la chaîne YouTube @soonerfrance">
                <span class="yt-paid-dot" aria-hidden="true"></span>
                <span>Payant</span>
              </span>
            ` : ''}

            <!-- Badge Durée Bas Droite -->
            <span class="badge-duration-bottom">${escapeHTML(duration)}</span>

            <!-- Bouton direct pour regarder sur YouTube (si l'utilisateur préfère YouTube) -->
            <a 
              href="${escapeHTML(buildYoutubeUrl(movie))}" 
              target="_blank" 
              rel="noopener noreferrer" 
              class="card-yt-direct-btn" 
              title="Regarder directement sur YouTube ↗ (nouvel onglet)"
              onclick="event.stopPropagation();"
            >
              <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
                <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
              </svg>
              <span>Sur YouTube ↗</span>
            </a>

            <!-- Bouton Play en surimpression au survol (ouvre la fiche sans lancer directement) -->
            <div class="play-overlay-btn" aria-hidden="true" title="Afficher la fiche du film">
              <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor">
                <path d="M8 5v14l11-7z"/>
              </svg>
            </div>
          </div>

          <!-- Métadonnées sous la miniature -->
          <div class="movie-details">
            <div class="channel-avatar-wrapper">
              ${movie.channelAvatar ? `
                <img 
                  class="channel-avatar-img" 
                  src="${escapeHTML(movie.channelAvatar)}" 
                  alt="${escapeHTML(movie.channelName || '')}" 
                  loading="lazy"
                  onerror="this.onerror=null; this.parentElement.innerHTML='<div class=\\'channel-avatar-fallback\\'>${escapeHTML(initial)}</div>';"
                />
              ` : `
                <div class="channel-avatar-fallback">${escapeHTML(initial)}</div>
              `}
            </div>

            <div class="movie-text-content">
              <h2 class="movie-card-title" title="${escapeHTML(movie.title)}">
                ${escapeHTML(movie.title)}
              </h2>
              
              <div class="movie-channel-line">
                <span>${escapeHTML(movie.channelName || 'Chaîne YouTube')}</span>
                ${movie.channelVerified ? `
                  <svg class="verified-icon" viewBox="0 0 24 24" fill="currentColor" title="Chaîne vérifiée">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                  </svg>
                ` : ''}
              </div>

              <div class="movie-meta-line" title="${escapeHTML(metaText)}">
                ${escapeHTML(metaText)}
              </div>

              ${isPaid ? `
                <div class="movie-paid-line" title="Visionnage payant (location ou abonnement) sur la chaîne YouTube @soonerfrance">
                  <span class="yt-paid-dot" aria-hidden="true"></span>
                  <span>${escapeHTML(movie.paidLabel || 'Visionnage payant • @soonerfrance')}</span>
                </div>
              ` : ''}
            </div>
          </div>
        </article>
      `;
    }).join('');

    // Attachement des écouteurs sur chaque carte
    DOM.moviesGrid.querySelectorAll('.movie-card').forEach((cardEl) => {
      cardEl.addEventListener('click', () => {
        const index = parseInt(cardEl.dataset.index, 10);
        if (!isNaN(index) && state.movies[index]) {
          openMovieModal(state.movies[index]);
        }
      });
      cardEl.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          const index = parseInt(cardEl.dataset.index, 10);
          if (!isNaN(index) && state.movies[index]) {
            openMovieModal(state.movies[index]);
          }
        }
      });
    });
  }

  /**
   * Met à jour le badge d'état des filtres
   */
  function updateFilterBadge() {
    if (!DOM.activeFilterBadge) return;
    const parts = [];
    if (state.currentQuery) {
      parts.push(`Recherche : "${escapeHTML(state.currentQuery)}"`);
    }
    if (state.currentSubFilter === 'native') {
      parts.push('ST-FR Natif');
    }
    if (state.currentCategory && state.currentCategory !== 'all') {
      const activeChip = document.querySelector(`.chip[data-category="${state.currentCategory}"]`);
      if (activeChip) {
        parts.push(activeChip.textContent.trim());
      }
    }
    DOM.activeFilterBadge.textContent = parts.length > 0 ? parts.join(' | ') : 'Tous les films';
  }

  // =========================================================================
  // CHARGEMENT DE L'API /api/movies
  // =========================================================================
  async function loadMovies(refresh = false) {
    if (state.isLoading) return;
    state.isLoading = true;

    // Affichage des squelettes
    renderSkeletons(8);

    if (refresh && DOM.refreshBtn) {
      DOM.refreshBtn.classList.add('refreshing');
    }

    const queryParams = new URLSearchParams({
      q: state.currentQuery,
      category: state.currentCategory,
      sub_filter: state.currentSubFilter,
      refresh: refresh ? '1' : '0'
    });

    const apiUrl = `/api/movies?${queryParams.toString()}`;

    try {
      const response = await fetch(apiUrl, {
        headers: { 'Accept': 'application/json' }
      });

      if (!response.ok) {
        throw new Error(`Erreur serveur (${response.status})`);
      }

      const data = await response.json();
      let rawMovies = [];

      if (data && Array.isArray(data.movies)) {
        rawMovies = data.movies;
      } else if (Array.isArray(data)) {
        rawMovies = data;
      }

      // TRI DÉFENSIF PAR DATE DE PUBLICATION DÉCROISSANTE (PLUS RÉCENT EN PREMIER)
      state.movies = defensiveSortByDateDesc(rawMovies);
      renderMovies(state.movies);

      if (refresh) {
        showToast('Catalogue actualisé avec succès depuis YouTube !');
      }
    } catch (err) {
      console.warn('Impossible de joindre /api/movies, basculement sur données locales de secours :', err);
      
      // Fallback gracieux : si l'API backend n'est pas encore démarrée, on filtre et trie les films de secours
      let filtered = [...FALLBACK_MOVIES];

      // Filtre catégorie
      if (state.currentCategory && state.currentCategory !== 'all') {
        if (state.currentCategory === 'recent') {
          // Déjà trié par date
        } else if (state.currentCategory === 'native') {
          filtered = filtered.filter(m => m.subtitleType === 'native_fr');
        } else if (state.currentCategory === 'kofa') {
          filtered = filtered.filter(m => (m.channelName || '').toLowerCase().includes('korean film archive') || (m.channelName || '').toLowerCase().includes('kofa'));
        } else {
          filtered = filtered.filter(m => m.category === state.currentCategory);
        }
      }

      // Filtre sous-titres
      if (state.currentSubFilter === 'native') {
        filtered = filtered.filter(m => m.subtitleType === 'native_fr');
      }

      // Filtre recherche
      if (state.currentQuery.trim()) {
        const q = state.currentQuery.trim().toLowerCase();
        filtered = filtered.filter(m => 
          (m.title || '').toLowerCase().includes(q) ||
          (m.channelName || '').toLowerCase().includes(q) ||
          (m.description || '').toLowerCase().includes(q)
        );
      }

      // TRI DÉFENSIF GARANTI
      state.movies = defensiveSortByDateDesc(filtered);
      renderMovies(state.movies);

      if (refresh) {
        showToast('Données actualisées en mode local');
      }
    } finally {
      state.isLoading = false;
      if (DOM.refreshBtn) {
        DOM.refreshBtn.classList.remove('refreshing');
      }
    }
  }

  // =========================================================================
  // GESTION DE LA MODALE DU LECTEUR CINÉMA
  // =========================================================================
  function openMovieModal(movie) {
    if (!movie) return;
    state.selectedMovie = movie;

    // 1. Titre & lien direct YouTube
    DOM.modalMovieTitle.textContent = movie.title || 'Film Coréen';
    DOM.modalYtLink.href = buildYoutubeUrl(movie);

    // 2. Chaîne et vérification
    DOM.modalChannelName.textContent = movie.channelName || 'Chaîne YouTube';
    if (movie.channelVerified) {
      DOM.modalChannelVerified.classList.remove('hidden');
    } else {
      DOM.modalChannelVerified.classList.add('hidden');
    }

    // Avatar chaîne
    const initial = (movie.channelName || 'K').charAt(0).toUpperCase();
    if (movie.channelAvatar) {
      DOM.modalChannelAvatar.innerHTML = `
        <img src="${escapeHTML(movie.channelAvatar)}" alt="${escapeHTML(movie.channelName || '')}" onerror="this.onerror=null; this.parentElement.innerHTML='<div class=\\'channel-avatar-fallback\\'>${escapeHTML(initial)}</div>';" />
      `;
    } else {
      DOM.modalChannelAvatar.innerHTML = `<div class="channel-avatar-fallback">${escapeHTML(initial)}</div>`;
    }

    // Stats
    const views = formatViews(movie);
    const pubDate = formatPublishedDate(movie);
    DOM.modalStatsText.textContent = `${views} • Publié le ${pubDate}`;

    // 3. Badges sous-titre & durée
    const isNative = movie.subtitleType === 'native_fr';
    const isPaid = Boolean(movie.isPaid);
    const countryPrefix = movie.countryLabel ? `${movie.countryLabel} • ` : '🇫🇷 ';
    if (isPaid) {
      DOM.modalSubtitleBadge.className = 'badge-paid-modal';
      DOM.modalSubtitleBadge.innerHTML = `<span class="yt-paid-dot" aria-hidden="true"></span><span>${escapeHTML(countryPrefix)}Visionnage payant • @soonerfrance</span>`;

      DOM.modalSubHelp.className = 'sub-help-banner native';
      DOM.modalSubHelpText.textContent = '🟢 Film proposé en visionnage payant sur la chaîne officielle YouTube @soonerfrance (VOSTFR / VF). Cliquez sur « Regarder directement sur YouTube ↗ » pour louer ou débloquer le film complet.';
    } else if (isNative) {
      DOM.modalSubtitleBadge.className = 'badge-subtitle native';
      DOM.modalSubtitleBadge.textContent = `${countryPrefix}ST-FR Natif`;

      DOM.modalSubHelp.className = 'sub-help-banner native';
      DOM.modalSubHelpText.textContent = 'Sous-titres français (ou VF) activés automatiquement.';
    } else {
      DOM.modalSubtitleBadge.className = 'badge-subtitle auto';
      DOM.modalSubtitleBadge.textContent = `${countryPrefix}ST-FR Auto (CC)`;

      DOM.modalSubHelp.className = 'sub-help-banner auto';
      DOM.modalSubHelpText.textContent = "Sous-titres activés : si le texte s'affiche en anglais/coréen/japonais/chinois, cliquez sur ⚙️ Paramètres > Sous-titres > Traduire automatiquement > Français dans le lecteur YouTube.";
    }

    DOM.modalDurationBadge.textContent = formatDuration(movie);

    // 4. Description et langues
    DOM.modalDescription.textContent = movie.description || 'Aucune description détaillée disponible pour cette vidéo.';
    DOM.modalSubLanguagesList.textContent = formatLanguagesList(movie.availableLanguages || movie.subtitleLanguages);

    // 5. Iframe YouTube (avec autoplay et sous-titres FR forcés)
    const embedSrc = buildEmbedUrl(movie);
    DOM.modalIframe.src = embedSrc;

    // Affichage et blocage du défilement d'arrière-plan
    DOM.movieModal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
    DOM.closeModalBtn.focus();
  }

  function closeMovieModal() {
    // Si en plein écran, quitter le plein écran d'abord
    if (document.fullscreenElement || document.webkitFullscreenElement || document.mozFullScreenElement) {
      if (document.exitFullscreen) document.exitFullscreen();
      else if (document.webkitExitFullscreen) document.webkitExitFullscreen();
    }
    // Vider la source de l'iframe pour stopper le son de la vidéo
    DOM.modalIframe.src = '';
    DOM.movieModal.classList.add('hidden');
    document.body.style.overflow = '';
    state.selectedMovie = null;
  }

  /**
   * Bascule l'affichage du lecteur en Plein Écran (Fullscreen API)
   */
  function toggleFullscreen() {
    const container = DOM.modalPlayerContainer || document.getElementById('modalPlayerContainer');
    if (!container) return;

    const isFullscreen = Boolean(
      document.fullscreenElement ||
      document.webkitFullscreenElement ||
      document.mozFullScreenElement ||
      document.msFullscreenElement
    );

    if (!isFullscreen) {
      if (container.requestFullscreen) {
        container.requestFullscreen().catch(err => console.warn('Plein écran non autorisé:', err));
      } else if (container.webkitRequestFullscreen) {
        container.webkitRequestFullscreen();
      } else if (container.mozRequestFullScreen) {
        container.mozRequestFullScreen();
      } else if (container.msRequestFullscreen) {
        container.msRequestFullscreen();
      }
    } else {
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
  }

  function handleFullscreenChange() {
    const isFullscreen = Boolean(
      document.fullscreenElement ||
      document.webkitFullscreenElement ||
      document.mozFullScreenElement ||
      document.msFullscreenElement
    );

    if (DOM.fullscreenBtn) {
      if (isFullscreen) {
        DOM.fullscreenBtn.classList.add('active');
        if (DOM.fullscreenBtnText) DOM.fullscreenBtnText.textContent = 'Quitter plein écran';
      } else {
        DOM.fullscreenBtn.classList.remove('active');
        if (DOM.fullscreenBtnText) DOM.fullscreenBtnText.textContent = 'Plein écran';
      }
    }
  }

  // Écouteurs de changement d'état plein écran
  document.addEventListener('fullscreenchange', handleFullscreenChange);
  document.addEventListener('webkitfullscreenchange', handleFullscreenChange);
  document.addEventListener('mozfullscreenchange', handleFullscreenChange);

  // =========================================================================
  // ÉCOUTEURS D'ÉVÉNEMENTS
  // =========================================================================

  // Recherche textuelle
  if (DOM.searchForm) {
    DOM.searchForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const val = DOM.searchInput.value.trim();
      state.currentQuery = val;
      loadMovies();
    });
  }

  if (DOM.searchInput) {
    DOM.searchInput.addEventListener('input', () => {
      if (DOM.searchInput.value.length > 0) {
        DOM.clearSearchBtn.classList.remove('hidden');
      } else {
        DOM.clearSearchBtn.classList.add('hidden');
      }
    });

    DOM.searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        DOM.searchInput.value = '';
        DOM.clearSearchBtn.classList.add('hidden');
        if (state.currentQuery !== '') {
          state.currentQuery = '';
          loadMovies();
        }
      }
    });
  }

  if (DOM.clearSearchBtn) {
    DOM.clearSearchBtn.addEventListener('click', () => {
      DOM.searchInput.value = '';
      DOM.clearSearchBtn.classList.add('hidden');
      DOM.searchInput.focus();
      if (state.currentQuery !== '') {
        state.currentQuery = '';
        loadMovies();
      }
    });
  }

  // Filtre sous-titrage select
  if (DOM.subFilter) {
    DOM.subFilter.addEventListener('change', (e) => {
      state.currentSubFilter = e.target.value;
      loadMovies();
    });
  }

  // Bouton Actualiser
  if (DOM.refreshBtn) {
    DOM.refreshBtn.addEventListener('click', () => {
      loadMovies(true);
    });
  }

  // Barre de puces (Chips)
  if (DOM.chipsTrack) {
    DOM.chipsTrack.addEventListener('click', (e) => {
      const chip = e.target.closest('.chip');
      if (!chip) return;

      DOM.chips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');

      state.currentCategory = chip.dataset.category || 'all';
      loadMovies();
    });
  }

  // Réinitialiser les filtres
  if (DOM.resetFiltersBtn) {
    DOM.resetFiltersBtn.addEventListener('click', () => {
      state.currentQuery = '';
      state.currentCategory = 'all';
      state.currentSubFilter = 'all';

      if (DOM.searchInput) DOM.searchInput.value = '';
      if (DOM.clearSearchBtn) DOM.clearSearchBtn.classList.add('hidden');
      if (DOM.subFilter) DOM.subFilter.value = 'all';

      DOM.chips.forEach(c => {
        if (c.dataset.category === 'all') c.classList.add('active');
        else c.classList.remove('active');
      });

      loadMovies();
    });
  }

  // Réessayer en cas d'erreur
  if (DOM.retryFetchBtn) {
    DOM.retryFetchBtn.addEventListener('click', () => {
      loadMovies();
    });
  }

  // Fermeture de la modale
  if (DOM.closeModalBtn) {
    DOM.closeModalBtn.addEventListener('click', closeMovieModal);
  }

  if (DOM.movieModal) {
    // Clic sur l'arrière-plan sombre hors de la fenêtre modale
    DOM.movieModal.addEventListener('click', (e) => {
      if (e.target === DOM.movieModal) {
        closeMovieModal();
      }
    });
  }

  // Plein écran
  if (DOM.fullscreenBtn) {
    DOM.fullscreenBtn.addEventListener('click', toggleFullscreen);
  }

  if (DOM.overlayFullscreenBtn) {
    DOM.overlayFullscreenBtn.addEventListener('click', toggleFullscreen);
  }

  // Touches clavier dans la modale :
  // - Échap : ferme la modale (si non plein écran, car le navigateur gère déjà la sortie du plein écran)
  // - F / f : bascule en plein écran
  window.addEventListener('keydown', (e) => {
    const isModalOpen = DOM.movieModal && !DOM.movieModal.classList.contains('hidden');
    if (!isModalOpen) return;

    const isFullscreen = Boolean(
      document.fullscreenElement ||
      document.webkitFullscreenElement ||
      document.mozFullScreenElement
    );

    if (e.key === 'Escape' && !isFullscreen) {
      closeMovieModal();
    } else if ((e.key === 'f' || e.key === 'F') && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
      e.preventDefault();
      toggleFullscreen();
    }
  });

  // =========================================================================
  // INITIALISATION
  // =========================================================================
  document.addEventListener('DOMContentLoaded', () => {
    loadMovies();
  });

})();
