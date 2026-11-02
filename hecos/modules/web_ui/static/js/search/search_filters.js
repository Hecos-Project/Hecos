/**
 * search_filters.js
 * Category subtabs, moderation toggles, engine chip filters, pagination, and infinite scroll for Deep Search.
 */
(function () {
  const state = window.SearchState;

  function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  // ── Contextual Mode Subtabs Architecture ──────────────────────────────────
  const MODE_SUBTABS = {
    clear: [
      { id: 'all', label: 'All', icon: 'fa-layer-group' },
      { id: 'web', label: 'Web & News', icon: 'fa-newspaper' },
      { id: 'images', label: 'Images', icon: 'fa-image' },
      { id: 'videos', label: 'Videos', icon: 'fa-video' },
      { id: 'audio', label: 'Audio', icon: 'fa-music' },
      { id: 'files', label: 'Files & Dorks', icon: 'fa-file-shield' }
    ],
    dark: [
      { id: 'all', label: 'All (.onion)', icon: 'fa-user-secret' },
      { id: 'dark_directories', label: 'Wiki & Directory', icon: 'fa-compass' },
      { id: 'dark_forums', label: 'Forum & Board', icon: 'fa-comments' },
      { id: 'dark_leaks', label: 'Leaks & Dumps', icon: 'fa-shield-halved' },
      { id: 'dark_market', label: 'Markets & Services', icon: 'fa-store' }
    ],
    files: [
      { id: 'all', label: 'All Files', icon: 'fa-file-shield' },
      { id: 'files_docs', label: 'Documents (PDF/DOC)', icon: 'fa-file-pdf' },
      { id: 'files_data', label: 'Data & Sheets (XLS/CSV)', icon: 'fa-file-excel' },
      { id: 'files_archives', label: 'Archives (ZIP/ISO)', icon: 'fa-file-zipper' },
      { id: 'files_code', label: 'Code & Config', icon: 'fa-file-code' }
    ],
    osint: [
      { id: 'all', label: 'All Profiles', icon: 'fa-id-badge' },
      { id: 'osint_social', label: 'Social Networks', icon: 'fa-users' },
      { id: 'osint_dev', label: 'Dev & Tech', icon: 'fa-code-branch' },
      { id: 'osint_media', label: 'Gaming & Media', icon: 'fa-gamepad' }
    ],
    deep: [
      { id: 'all', label: 'All Aggregated', icon: 'fa-layer-group' },
      { id: 'deep_clear', label: 'Clearnet (Web)', icon: 'fa-globe' },
      { id: 'deep_dark', label: 'Darknet (.onion)', icon: 'fa-user-secret' },
      { id: 'deep_media', label: 'Media (Img/Vid/Audio)', icon: 'fa-photo-film' },
      { id: 'deep_files', label: 'Files & Documents', icon: 'fa-file-shield' }
    ]
  };

  function renderFilterTabsForMode(mode, preserveFilter = true) {
    const container = document.getElementById('filter-categories');
    if (!container) return;
    const subtabs = MODE_SUBTABS[mode] || MODE_SUBTABS.clear;
    const validIds = subtabs.map(s => s.id);

    if (!preserveFilter || !validIds.includes(state.activeFilter)) {
      state.activeFilter = 'all';
    }

    container.innerHTML = subtabs.map(tab => `
      <button class="filter-tab ${state.activeFilter === tab.id ? 'active' : ''}" data-filter="${tab.id}" id="filter-tab-${tab.id}" onclick="window.setFilter('${tab.id}')">
        <i class="fas ${tab.icon}"></i> <span>${tab.label}</span> <span class="filter-count" id="count-${tab.id}">0</span>
      </button>
    `).join('');

    updateFilterCounts();
  }

  // ── Filter Controls ────────────────────────────────────────────────────────
  function setFilter(filterName, shouldRender = true, clearEngine = true) {
    state.activeFilter = filterName || 'all';
    if (clearEngine) {
      if (state.activeEngine || state.activeProvider) {
        state.activeEngine = null;
        state.activeProvider = null;
        updateEngineChipsSelection();
      }
    }
    document.querySelectorAll('.filter-tab').forEach(tab => {
      tab.classList.toggle('active', tab.dataset.filter === state.activeFilter);
    });
    if (shouldRender) {
      renderCurrentView();
    }
  }

  // ── Known Providers Catalog & Extraction ─────────────────────────────────
  const KNOWN_PROVIDERS = [
    { id: 'google', name: 'Google', icon: 'fab fa-google', test: /(google|google_images|google_videos)/i },
    { id: 'bing', name: 'Bing', icon: 'fab fa-microsoft', test: /(bing|bing_images|bing_videos)/i },
    { id: 'yandex', name: 'Yandex', icon: 'fab fa-yandex', test: /(yandex|yandex_images)/i },
    { id: 'duckduckgo', name: 'DuckDuckGo', icon: 'fas fa-feather', test: /(duckduckgo|ddgs)/i },
    { id: 'yahoo', name: 'Yahoo', icon: 'fab fa-yahoo', test: /yahoo/i },
    { id: 'wikipedia', name: 'Wikipedia / Commons', icon: 'fab fa-wikipedia-w', test: /(wikipedia|wikicommons|commons)/i },
    { id: 'brave', name: 'Brave', icon: 'fas fa-shield', test: /brave/i },
    { id: 'startpage', name: 'Startpage', icon: 'fas fa-magnifying-glass', test: /startpage/i },
    { id: 'unsplash', name: 'Unsplash', icon: 'fas fa-camera', test: /unsplash/i },
    { id: 'openverse', name: 'Openverse', icon: 'fas fa-images', test: /openverse/i },
    { id: 'dailymotion', name: 'Dailymotion', icon: 'fas fa-play', test: /dailymotion/i },
    { id: 'peertube', name: 'PeerTube', icon: 'fas fa-circle-play', test: /peertube/i },
    { id: 'youtube', name: 'YouTube', icon: 'fab fa-youtube', test: /(youtube|yt-dlp)/i },
    { id: 'vimeo', name: 'Vimeo', icon: 'fab fa-vimeo-v', test: /vimeo/i },
    { id: 'rumble', name: 'Rumble', icon: 'fas fa-play-circle', test: /rumble/i },
    { id: 'eporner', name: 'Eporner', icon: 'fas fa-film', test: /eporner/i },
    { id: 'redtube', name: 'RedTube', icon: 'fas fa-video', test: /redtube/i },
    { id: 'archive_org', name: 'Archive.org', icon: 'fas fa-landmark', test: /archive_org/i },
    { id: 'soundcloud', name: 'SoundCloud', icon: 'fab fa-soundcloud', test: /soundcloud/i },
    { id: 'mixcloud', name: 'Mixcloud', icon: 'fab fa-mixcloud', test: /mixcloud/i },
    { id: 'itunes', name: 'Apple Podcasts', icon: 'fab fa-apple', test: /itunes/i },
    { id: 'artic', name: 'Artic Museum', icon: 'fas fa-palette', test: /artic/i },
    { id: 'genius', name: 'Genius', icon: 'fas fa-align-left', test: /genius/i },
    { id: 'file_dork', name: 'Dorks Hunter', icon: 'fas fa-file-shield', test: /(dork|file_dork)/i },
    { id: 'ahmia', name: 'Tor: Ahmia', icon: 'fas fa-user-secret', test: /ahmia/i },
    { id: 'torch', name: 'Tor: Torch', icon: 'fas fa-fire', test: /torch/i },
    { id: 'haystak', name: 'Tor: Haystak', icon: 'fas fa-wheat-awn', test: /haystak/i },
    { id: 'excavator', name: 'Tor: Excavator', icon: 'fas fa-compass', test: /excavator/i },
    { id: 'phobos', name: 'Tor: Phobos', icon: 'fas fa-moon', test: /phobos/i },
    { id: 'tor66', name: 'Tor: Tor66', icon: 'fas fa-route', test: /tor66/i },
    { id: 'danieltore', name: 'Tor: DanielTore', icon: 'fas fa-network-wired', test: /danieltore/i },
    // News & Media
    { id: 'reuters', name: 'Reuters', icon: 'fas fa-newspaper', test: /reuters/i },
    { id: 'wikinews', name: 'Wikinews', icon: 'fab fa-wikipedia-w', test: /wikinews/i },
    // Social & Discussions
    { id: 'reddit', name: 'Reddit', icon: 'fab fa-reddit', test: /reddit/i },
    { id: 'mastodon', name: 'Mastodon', icon: 'fab fa-mastodon', test: /mastodon/i },
    { id: 'lemmy', name: 'Lemmy', icon: 'fas fa-comments', test: /lemmy/i },
    // Science & Academic
    { id: 'arxiv', name: 'arXiv', icon: 'fas fa-graduation-cap', test: /arxiv/i },
    { id: 'scholar', name: 'Google Scholar', icon: 'fas fa-book', test: /scholar/i },
    { id: 'pubmed', name: 'PubMed', icon: 'fas fa-dna', test: /pubmed/i },
    { id: 'semantic_scholar', name: 'Semantic Scholar', icon: 'fas fa-brain', test: /semantic.*scholar/i },
    // IT & Development
    { id: 'github', name: 'GitHub', icon: 'fab fa-github', test: /github/i },
    { id: 'stackoverflow', name: 'Stack Overflow', icon: 'fab fa-stack-overflow', test: /(stackoverflow|askubuntu|superuser)/i },
    { id: 'pypi', name: 'PyPI', icon: 'fab fa-python', test: /pypi/i },
    { id: 'docker', name: 'Docker Hub', icon: 'fab fa-docker', test: /docker/i },
    { id: 'hackernews', name: 'Hacker News', icon: 'fab fa-y-combinator', test: /(hackernews|hn)/i },
    { id: 'mdn', name: 'MDN Web Docs', icon: 'fab fa-firefox-browser', test: /mdn/i },
    // Files & Torrents
    { id: 'kickass', name: 'Kickass', icon: 'fas fa-download', test: /kickass/i },
    { id: 'piratebay', name: 'The Pirate Bay', icon: 'fas fa-skull-crossbones', test: /piratebay/i },
    { id: 'solidtorrents', name: 'Solid Torrents', icon: 'fas fa-magnet', test: /solidtorrents/i },
    { id: 'bt4g', name: 'BT4G', icon: 'fas fa-magnet', test: /bt4g/i },
    { id: 'annas_archive', name: "Anna's Archive", icon: 'fas fa-book-open', test: /anna.*archive/i },
    { id: 'zlibrary', name: 'Z-Library', icon: 'fas fa-book-bookmark', test: /(zlibrary|z-library)/i },
    // Visual Media
    { id: 'flickr', name: 'Flickr', icon: 'fab fa-flickr', test: /flickr/i },
    { id: 'deviantart', name: 'DeviantArt', icon: 'fab fa-deviantart', test: /deviantart/i },
    { id: 'wallhaven', name: 'Wallhaven', icon: 'fas fa-image', test: /wallhaven/i },
    { id: 'pinterest', name: 'Pinterest', icon: 'fab fa-pinterest', test: /pinterest/i },
    // Music & Radio
    { id: 'bandcamp', name: 'Bandcamp', icon: 'fab fa-bandcamp', test: /bandcamp/i },
    { id: 'deezer', name: 'Deezer', icon: 'fas fa-music', test: /deezer/i },
    { id: 'radio_browser', name: 'Radio Browser', icon: 'fas fa-radio', test: /radio.*browser/i },
    // References & Maps
    { id: 'imdb', name: 'IMDB', icon: 'fab fa-imdb', test: /imdb/i },
    { id: 'openstreetmap', name: 'OpenStreetMap', icon: 'fas fa-map-location-dot', test: /(openstreetmap|osm|photon)/i },
    { id: 'wikidata', name: 'Wikidata', icon: 'fas fa-barcode', test: /wikidata/i },
    { id: 'wttr', name: 'Weather', icon: 'fas fa-cloud-sun', test: /wttr/i }
  ];


  // ── Sub-Engine Display Labels & Icons ────────────────────────────────────
  // Maps raw r.engine strings (actual data sources) to display metadata.
  // Used by renderGranularProviderChips() for the bottom-row source panel.
  const ENGINE_LABELS = {
    // DuckDuckGo variants
    'ddgs': { name: 'DDG Web', icon: 'fas fa-feather' },
    'ddgs:images': { name: 'DDG Images', icon: 'fas fa-feather' },
    'ddgs:news': { name: 'DDG News', icon: 'fas fa-feather' },
    'ddgs:videos': { name: 'DDG Videos', icon: 'fas fa-feather' },
    'clear_ddgs': { name: 'DDG Web', icon: 'fas fa-feather' },
    // SearXNG aggregated
    'clear_searxng': { name: 'SearXNG Web', icon: 'fas fa-magnifying-glass' },
    'searxng': { name: 'SearXNG', icon: 'fas fa-magnifying-glass' },
    // SearXNG per-engine sub-sources
    'searxng:yahoo': { name: 'Yahoo (SXG)', icon: 'fab fa-yahoo' },
    'searxng:bing': { name: 'Bing (SXG)', icon: 'fab fa-microsoft' },
    'searxng:google': { name: 'Google (SXG)', icon: 'fab fa-google' },
    'searxng:duckduckgo': { name: 'DDG (SXG)', icon: 'fas fa-feather' },
    'searxng:yandex': { name: 'Yandex (SXG)', icon: 'fab fa-yandex' },
    'searxng:startpage': { name: 'Startpage (SXG)', icon: 'fas fa-magnifying-glass' },
    'searxng:brave': { name: 'Brave (SXG)', icon: 'fas fa-shield' },
    'searxng:wikipedia': { name: 'Wikipedia (SXG)', icon: 'fab fa-wikipedia-w' },
    'searxng:wikicommons': { name: 'Wiki Commons (SXG)', icon: 'fab fa-wikipedia-w' },
    'searxng:artic': { name: 'Artic Museum', icon: 'fas fa-palette' },
    'searxng:genius': { name: 'Genius', icon: 'fas fa-align-left' },
    'searxng:soundcloud': { name: 'SoundCloud', icon: 'fab fa-soundcloud' },
    'searxng:mixcloud': { name: 'Mixcloud', icon: 'fab fa-mixcloud' },
    'searxng:bandcamp': { name: 'Bandcamp', icon: 'fas fa-music' },
    'searxng:unsplash': { name: 'Unsplash', icon: 'fas fa-camera' },
    'searxng:openverse': { name: 'Openverse', icon: 'fas fa-images' },
    'searxng:peertube': { name: 'PeerTube (SXG)', icon: 'fas fa-circle-play' },
    'searxng:vimeo': { name: 'Vimeo (SXG)', icon: 'fab fa-vimeo-v' },
    'searxng:youtube': { name: 'YouTube (SXG)', icon: 'fab fa-youtube' },
    'searxng:dailymotion': { name: 'Dailymotion (SXG)', icon: 'fas fa-play' },
    'searxng:rumble': { name: 'Rumble (SXG)', icon: 'fas fa-play-circle' },
    'searxng:reddit': { name: 'Reddit (SXG)', icon: 'fab fa-reddit' },
    // RSS
    'rss:google_news': { name: 'Google News', icon: 'fab fa-google' },
    'rss:bing_news': { name: 'Bing News', icon: 'fab fa-microsoft' },
    'rss:yahoo_news': { name: 'Yahoo News', icon: 'fab fa-yahoo' },
    'rss': { name: 'RSS Feed', icon: 'fas fa-rss' },
    // Video platforms (direct)
    'youtube': { name: 'YouTube', icon: 'fab fa-youtube' },
    'yt-dlp': { name: 'YouTube (yt-dlp)', icon: 'fab fa-youtube' },
    'dailymotion': { name: 'Dailymotion', icon: 'fas fa-play' },
    'peertube': { name: 'PeerTube', icon: 'fas fa-circle-play' },
    'vimeo': { name: 'Vimeo', icon: 'fab fa-vimeo-v' },
    'rumble': { name: 'Rumble', icon: 'fas fa-play-circle' },
    'eporner': { name: 'Eporner', icon: 'fas fa-film' },
    'eporner:stream': { name: 'Eporner', icon: 'fas fa-film' },
    'redtube': { name: 'RedTube', icon: 'fas fa-video' },
    'redtube:stream': { name: 'RedTube', icon: 'fas fa-video' },
    // Archive
    'archive_org:video': { name: 'Archive.org Video', icon: 'fas fa-landmark' },
    'archive_org:audio': { name: 'Archive.org Audio', icon: 'fas fa-landmark' },
    'archive_org:texts': { name: 'Archive.org Texts', icon: 'fas fa-landmark' },
    'archive_org': { name: 'Archive.org', icon: 'fas fa-landmark' },
    // Audio platforms
    'soundcloud': { name: 'SoundCloud', icon: 'fab fa-soundcloud' },
    'mixcloud': { name: 'Mixcloud', icon: 'fab fa-mixcloud' },
    'bandcamp': { name: 'Bandcamp', icon: 'fas fa-music' },
    'audio_stream': { name: 'Audio Stream', icon: 'fas fa-music' },
    'itunes:music': { name: 'Apple Music', icon: 'fab fa-apple' },
    'itunes:podcast': { name: 'Apple Podcasts', icon: 'fab fa-apple' },
    'itunes': { name: 'Apple Podcasts', icon: 'fab fa-apple' },
    // Images
    'media_images': { name: 'Images (all)', icon: 'fas fa-image' },
    'media_videos': { name: 'Videos (all)', icon: 'fas fa-video' },
    'media_audio': { name: 'Audio (all)', icon: 'fas fa-music' },
    // Tor
    'ahmia': { name: 'Tor: Ahmia', icon: 'fas fa-user-secret' },
    'torch': { name: 'Tor: Torch', icon: 'fas fa-fire' },
    'haystak': { name: 'Tor: Haystak', icon: 'fas fa-wheat-awn' },
    'excavator': { name: 'Tor: Excavator', icon: 'fas fa-compass' },
    'phobos': { name: 'Tor: Phobos', icon: 'fas fa-moon' },
    'tor66': { name: 'Tor: Tor66', icon: 'fas fa-route' },
    'danieltore': { name: 'Tor: DanielTore', icon: 'fas fa-network-wired' },
    // Files / Dorks
    'file_dork': { name: 'Dorks Hunter', icon: 'fas fa-file-shield' },
    'files_dorks': { name: 'Dorks Hunter', icon: 'fas fa-file-shield' },
    // News
    'clear_news': { name: 'News Aggregator', icon: 'fas fa-newspaper' },
    'searxng:google news': { name: 'Google News (SXG)', icon: 'fab fa-google' },
    'searxng:bing news': { name: 'Bing News (SXG)', icon: 'fab fa-microsoft' },
    'searxng:yahoo news': { name: 'Yahoo News (SXG)', icon: 'fab fa-yahoo' },
    'searxng:brave news': { name: 'Brave News (SXG)', icon: 'fas fa-shield' },
    'searxng:duckduckgo news': { name: 'DDG News (SXG)', icon: 'fas fa-feather' },
    'searxng:reuters': { name: 'Reuters', icon: 'fas fa-newspaper' },
    'searxng:wikinews': { name: 'Wikinews', icon: 'fab fa-wikipedia-w' },
    // Social & Discussions
    'searxng:mastodon users': { name: 'Mastodon', icon: 'fab fa-mastodon' },
    'searxng:lemmy posts': { name: 'Lemmy', icon: 'fas fa-comments' },
    // Science & Academic
    'searxng:arxiv': { name: 'arXiv', icon: 'fas fa-graduation-cap' },
    'searxng:google scholar': { name: 'Google Scholar', icon: 'fas fa-book' },
    'searxng:pubmed': { name: 'PubMed', icon: 'fas fa-dna' },
    'searxng:semantic scholar': { name: 'Semantic Scholar', icon: 'fas fa-brain' },
    // IT & Development
    'searxng:github': { name: 'GitHub', icon: 'fab fa-github' },
    'searxng:stackoverflow': { name: 'Stack Overflow', icon: 'fab fa-stack-overflow' },
    'searxng:pypi': { name: 'PyPI', icon: 'fab fa-python' },
    'searxng:docker hub': { name: 'Docker Hub', icon: 'fab fa-docker' },
    'searxng:hackernews': { name: 'Hacker News', icon: 'fab fa-y-combinator' },
    'searxng:mdn': { name: 'MDN Web Docs', icon: 'fab fa-firefox-browser' },
    // Files & Torrents
    'searxng:kickass': { name: 'Kickass', icon: 'fas fa-download' },
    'searxng:piratebay': { name: 'The Pirate Bay', icon: 'fas fa-skull-crossbones' },
    'searxng:solidtorrents': { name: 'Solid Torrents', icon: 'fas fa-magnet' },
    'searxng:bt4g': { name: 'BT4G', icon: 'fas fa-magnet' },
    'searxng:annas archive': { name: "Anna's Archive", icon: 'fas fa-book-open' },
    'searxng:z-library': { name: 'Z-Library', icon: 'fas fa-book-bookmark' },
    // Visual Media
    'searxng:flickr': { name: 'Flickr', icon: 'fab fa-flickr' },
    'searxng:deviantart': { name: 'DeviantArt', icon: 'fab fa-deviantart' },
    'searxng:wallhaven': { name: 'Wallhaven', icon: 'fas fa-image' },
    'searxng:pinterest': { name: 'Pinterest', icon: 'fab fa-pinterest' },
    // Music & Audio
    'searxng:deezer': { name: 'Deezer', icon: 'fas fa-music' },
    'searxng:piped.music': { name: 'Piped Music', icon: 'fas fa-headphones' },
    'searxng:radio browser': { name: 'Radio Browser', icon: 'fas fa-radio' },
    // Other & Reference
    'searxng:imdb': { name: 'IMDB', icon: 'fab fa-imdb' },
    'searxng:openstreetmap': { name: 'OpenStreetMap', icon: 'fas fa-map-location-dot' },
    'searxng:wikidata': { name: 'Wikidata', icon: 'fas fa-barcode' },
    'searxng:wttr.in': { name: 'Weather', icon: 'fas fa-cloud-sun' },
    'searxng:currency': { name: 'Currency', icon: 'fas fa-coins' },
  };

  /**
   * getEngineDisplayInfo(engineStr)
   * Returns {name, icon} for a raw r.engine string.
   * Falls back to a prettified version of the engine string itself.
   */
  function getEngineDisplayInfo(engineStr) {
    if (!engineStr) return { name: 'Unknown', icon: 'fas fa-circle-nodes' };
    const lower = engineStr.toLowerCase();
    if (ENGINE_LABELS[lower]) return ENGINE_LABELS[lower];
    // Prettify unknown: "searxng:custom_name" -> "Custom Name (SXG)"
    if (lower.startsWith('searxng:')) {
      const sub = lower.slice(8).replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
      return { name: `${sub} (SXG)`, icon: 'fas fa-magnifying-glass' };
    }
    if (lower.startsWith('ddgs:')) {
      const sub = lower.slice(5).replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
      return { name: `DDG ${sub}`, icon: 'fas fa-feather' };
    }
    if (lower.startsWith('rss:')) {
      const sub = lower.slice(4).replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
      return { name: sub, icon: 'fas fa-rss' };
    }
    const cleanName = lower.replace(/_/g, ' ').replace(/:/g, ' · ').replace(/\b\w/g, c => c.toUpperCase());
    return { name: cleanName, icon: 'fas fa-circle-nodes' };
  }

  function extractProvider(r) {
    if (!r) return { id: 'unknown', name: 'Unknown', icon: 'fas fa-circle-nodes' };
    const sourceEng = (r.metadata?.source_engine || '').toLowerCase();
    const eng = (r.engine || '').toLowerCase();
    const engId = (r.engine_id || r.metadata?.engine_id || '').toLowerCase();
    const publisher = (r.metadata?.publisher || '').toLowerCase();
    const combined = `${sourceEng} ${eng} ${engId} ${publisher}`;

    for (const kp of KNOWN_PROVIDERS) {
      if (kp.test.test(combined)) {
        return kp;
      }
    }

    if (r.network === 'tor' || (r.url && r.url.includes('.onion'))) {
      try {
        const onionHost = r.url ? (new URL(r.url, 'http://onion.invalid')).hostname.replace('.onion', '') : 'onion';
        const label = onionHost.length > 12 ? onionHost.slice(0, 8) + '...' : onionHost;
        return { id: 'onion_' + label, name: `Tor: ${label}`, icon: 'fas fa-user-secret' };
      } catch (e) {
        return { id: 'onion_site', name: 'Tor .onion', icon: 'fas fa-user-secret' };
      }
    }

    const fallbackId = (sourceEng || eng.replace(/^(searxng:|ddgs:|rss:)/, '') || engId || 'other').trim().toLowerCase();
    const cleanName = fallbackId.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    return { id: fallbackId, name: cleanName, icon: 'fas fa-circle-nodes' };
  }

  function providerMatches(r, targetProviderId) {
    if (!targetProviderId) return true;
    const target = targetProviderId.toLowerCase();
    // Match on raw r.engine — same key used by renderGranularProviderChips
    const rawEng = (r.engine || r.engine_id || '').trim().toLowerCase();
    return rawEng === target;
  }

  function filterByProvider(providerId) {
    if (state.activeProvider === providerId) {
      state.activeProvider = null; // Toggle off
    } else {
      state.activeProvider = providerId;
      state.activeEngine = null; // Prioritize granular provider
    }
    updateEngineChipsSelection();
    renderCurrentView();
  }

  function clearProviderFilter() {
    state.activeProvider = null;
    updateEngineChipsSelection();
    renderCurrentView();
  }

  // ── Provider Exclusion System ──────────────────────────────────────────
  function toggleExcludeProvider(providerId) {
    if (!state.excludedProviders) state.excludedProviders = [];
    const idx = state.excludedProviders.indexOf(providerId);
    if (idx >= 0) {
      // Already excluded — re-include
      state.excludedProviders.splice(idx, 1);
    } else {
      state.excludedProviders.push(providerId);
      // Cannot both include-filter and exclude same provider
      if (state.activeProvider === providerId) state.activeProvider = null;
    }
    renderGranularProviderChips();
    renderCurrentView();
    updateExclusionBar();
  }

  function clearAllExclusions() {
    state.excludedProviders = [];
    renderGranularProviderChips();
    renderCurrentView();
    updateExclusionBar();
  }

  function updateExclusionBar() {
    // Show/hide excluded-providers pill in the stream header
    const bar = document.getElementById('exclusion-bar');
    if (!bar) return;
    const excluded = state.excludedProviders || [];
    if (excluded.length === 0) {
      bar.style.display = 'none';
      return;
    }
    const names = excluded.map(id => {
      const kp = KNOWN_PROVIDERS.find(p => p.id === id);
      return kp ? kp.name : id;
    });
    bar.style.display = 'flex';
    bar.innerHTML = `<i class="fas fa-ban"></i> Excluded: ${names.map(n => `<span class="excl-tag">${n} <span class="excl-remove" data-provider-excl="${excluded[names.indexOf(n)]}" onclick="window.toggleExcludeProvider(this.dataset.providerExcl)">✕</span></span>`).join(' ')}<button type="button" class="excl-clear-all" onclick="window.clearAllExclusions()">Clear all</button>`;
  }


  function filterByEngine(engineId) {
    if (state.activeEngine === engineId) {
      state.activeEngine = null; // Toggle off
    } else {
      state.activeEngine = engineId;
      state.activeProvider = null;
      setFilter('all', false, false);
    }
    updateEngineChipsSelection();
    renderCurrentView();
  }

  function clearEngineFilter() {
    state.activeEngine = null;
    state.activeProvider = null;
    updateEngineChipsSelection();
    renderCurrentView();
  }

  function updateEngineChipsSelection() {
    const btnClearEngine = document.getElementById('btn-clear-engine-filter');
    const clearLabel = document.getElementById('btn-clear-filter-label');
    const hasAnyFilter = Boolean(state.activeEngine || state.activeProvider);
    if (btnClearEngine) {
      btnClearEngine.style.display = hasAnyFilter ? 'inline-flex' : 'none';
      if (clearLabel) {
        if (state.activeProvider) {
          const prov = KNOWN_PROVIDERS.find(p => p.id === state.activeProvider);
          const name = prov ? prov.name : state.activeProvider;
          clearLabel.innerText = `Active filter: ${name} (✖ Show all)`;
        } else if (state.activeEngine) {
          const engChip = document.getElementById(`chip-${state.activeEngine}`);
          const engName = engChip ? (engChip.querySelector('.chip-engine-name')?.innerText || state.activeEngine) : state.activeEngine;
          clearLabel.innerText = `Active filter: ${engName} (✖ Show all)`;
        } else {
          clearLabel.innerText = 'Show all sources';
        }
      }
    }
    document.querySelectorAll('.engine-chip').forEach(chip => {
      const eng = chip.dataset.engine || chip.id.replace('chip-', '');
      chip.classList.toggle('selected-engine', eng === state.activeEngine && !state.activeProvider);
    });
    document.querySelectorAll('.provider-chip').forEach(chip => {
      const prov = chip.dataset.provider;
      chip.classList.toggle('selected-provider', prov === state.activeProvider);
    });
    updateCollapsedPill();
  }

  function toggleStreamBarCollapse(event, explicitVal) {
    if (event) {
      const t = event.target;
      if (t && (t.closest('#btn-clear-engine-filter') || t.closest('.engine-chip') || t.closest('.provider-chip'))) {
        return;
      }
    }
    const bar = document.getElementById('stream-live-bar');
    const btn = document.getElementById('btn-toggle-stream-collapse');
    const icon = document.getElementById('icon-stream-collapse');
    const text = document.getElementById('text-stream-collapse');
    if (!bar) return;

    if (typeof explicitVal === 'boolean') {
      state.isStreamCollapsed = explicitVal;
    } else {
      state.isStreamCollapsed = !state.isStreamCollapsed;
    }

    try {
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem('hecos_stream_collapsed', state.isStreamCollapsed ? 'true' : 'false');
      }
    } catch (e) { }

    bar.classList.toggle('is-collapsed', state.isStreamCollapsed);
    if (icon) {
      icon.className = state.isStreamCollapsed ? 'fas fa-chevron-down' : 'fas fa-chevron-up';
    }
    if (text) {
      text.innerText = state.isStreamCollapsed ? 'Expand' : 'Collapse';
    }
    if (btn) {
      btn.title = state.isStreamCollapsed ? 'Expand engines and providers panel' : 'Collapse engines and providers panel';
    }

    updateCollapsedPill();
  }

  function updateCollapsedPill() {
    const pill = document.getElementById('stream-collapsed-pill');
    if (!pill) return;
    if (state.isStreamCollapsed) {
      let label = '';
      if (state.activeProvider) {
        const prov = KNOWN_PROVIDERS.find(p => p.id === state.activeProvider);
        label = `<i class="fas fa-filter"></i> Filter: ${prov ? prov.name : state.activeProvider}`;
      } else if (state.activeEngine) {
        const engChip = document.getElementById(`chip-${state.activeEngine}`);
        const engName = engChip ? (engChip.querySelector('.chip-engine-name')?.innerText || state.activeEngine) : state.activeEngine;
        label = `<i class="fas fa-filter"></i> Filter: ${engName}`;
      } else {
        const allStats = state.engineStats || {};
        const total = Object.keys(allStats).length;
        const withRes = Object.values(allStats).filter(s => s.count > 0).length;
        if (total > 0) {
          label = `<i class="fas fa-layer-group"></i> ${withRes}/${total} sources (${state.results.length} res.)`;
        } else {
          label = `<i class="fas fa-layer-group"></i> Engines collapsed`;
        }
      }
      pill.innerHTML = label;
      pill.style.display = 'inline-flex';
    } else {
      pill.style.display = 'none';
    }
  }

  function renderGranularProviderChips() {
    const container = document.getElementById('stream-provider-badges');
    const section = document.getElementById('stream-providers-section');
    if (!container || !section) return;

    const results = state.results || [];
    if (results.length === 0) {
      section.style.display = 'none';
      return;
    }

    // Group by raw r.engine string — the actual data-source sub-engine identifier.
    // This preserves full granularity: ddgs:images, searxng:yahoo, rss:google_news, etc.
    const engineMap = {};
    results.forEach(r => {
      const rawEng = (r.engine || r.engine_id || 'unknown').trim().toLowerCase();
      if (!engineMap[rawEng]) {
        const display = getEngineDisplayInfo(rawEng);
        engineMap[rawEng] = {
          id: rawEng,
          name: display.name,
          icon: display.icon,
          count: 0,
          categories: {}
        };
      }
      engineMap[rawEng].count += 1;
      const cat = r.category || 'web';
      engineMap[rawEng].categories[cat] = (engineMap[rawEng].categories[cat] || 0) + 1;
    });

    const list = Object.values(engineMap).sort((a, b) => b.count - a.count);
    const excludedSet = new Set(state.excludedProviders || []);

    container.innerHTML = list.map(p => {
      const isSelected = state.activeProvider === p.id;
      const isExcluded = excludedSet.has(p.id);
      const catBreakdown = Object.entries(p.categories).map(([c, n]) => `${c}: ${n}`).join(', ');
      const title = isExcluded
        ? `${p.name} [${p.id}]: EXCLUDED\nShift+Click or Right-Click to re-include`
        : `${p.name}\nEngine: ${p.id}\n${p.count} results (${catBreakdown})\nClick: filter  •  Shift+Click / Right-Click: exclude`;
      const chipClass = `provider-chip has-results ${isSelected ? 'selected-provider' : ''} ${isExcluded ? 'excluded-provider' : ''}`;
      const badgeHtml = isExcluded
        ? '<span class="provider-chip-excl-badge"><i class="fas fa-ban"></i></span>'
        : `<span class="provider-chip-count">${p.count}</span>`;
      return `
        <button type="button" class="${chipClass}"
                data-provider="${p.id}"
                onclick="if(event.shiftKey||event.ctrlKey){window.toggleExcludeProvider('${p.id}')}else{window.filterByProvider('${p.id}')}"
                oncontextmenu="event.preventDefault();window.toggleExcludeProvider('${p.id}')"
                title="${title}">
          <i class="${p.icon}"></i>
          <span class="provider-chip-name">${p.name}</span>
          ${badgeHtml}
        </button>
      `;
    }).join('');

    section.style.display = 'flex';
    updateEngineChipsSelection();
  }

  function toggleContentFilter() {
    state.safeSearch = !state.safeSearch;
    const badge = document.getElementById('badge-content-filter');
    const btn = document.getElementById('btn-content-filter');
    if (badge) {
      if (state.safeSearch) {
        badge.innerText = 'ON';
        badge.className = 'badge-pill badge-warn';
        if (btn) btn.title = 'Content Filter: ON (SafeSearch Moderate active)';
      } else {
        badge.innerText = 'OFF';
        badge.className = 'badge-pill badge-neutral';
        if (btn) btn.title = 'Content Filter: OFF (Unfiltered / Raw Search)';
      }
    }
  }

  function toggleDarkFilter() {
    state.darkBypass = !state.darkBypass;
    const badge = document.getElementById('badge-dark-filter');
    const btn = document.getElementById('btn-dark-filter');
    if (badge) {
      if (state.darkBypass) {
        badge.innerText = 'BYPASSED';
        badge.className = 'badge-pill badge-ok';
        if (btn) btn.title = 'DarkWeb Filters: BYPASSED (100% Uncensored / Blacklists disabled)';
      } else {
        badge.innerText = 'FILTERED';
        badge.className = 'badge-pill badge-neutral';
        if (btn) btn.title = 'DarkWeb Filters: ACTIVE (Ahmia standard moderation)';
      }
    }
  }

  function toggleLocalOnly(explicitVal) {
    if (typeof explicitVal === 'boolean') {
      state.localOnly = explicitVal;
    } else {
      state.localOnly = !state.localOnly;
    }
    const badge = document.getElementById('badge-local-only');
    const btn = document.getElementById('btn-local-only');
    if (badge) {
      if (state.localOnly) {
        badge.innerText = 'LOCAL ONLY';
        badge.className = 'badge-pill badge-ok';
        if (btn) btn.title = 'Privacy Shield: LOCAL ONLY (Strictly querying local private SearXNG and Tor onion circuits)';
      } else {
        badge.innerText = 'ALL ENGINES';
        badge.className = 'badge-pill badge-neutral';
        if (btn) btn.title = 'Privacy Shield: ALL ENGINES (Querying all active local and cloud search engines)';
      }
    }
  }

  function setSearchDepth(val) {
    let num = parseInt(val);
    if (isNaN(num) || num < 0) num = 0;
    state.searchLimit = num;
    try {
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem('hecos_netsearch_depth', String(num));
      }
    } catch (e) { }
    const presetSel = document.getElementById('search-depth-presets');
    if (presetSel) {
      const matchingOpt = Array.from(presetSel.options).find(o => parseInt(o.value) === num);
      presetSel.value = matchingOpt ? matchingOpt.value : "";
    }
  }

  function setSearchDepthPreset(val) {
    const num = parseInt(val) || 0;
    state.searchLimit = num;
    try {
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem('hecos_netsearch_depth', String(num));
      }
    } catch (e) { }
    const input = document.getElementById('search-depth-input');
    if (input) input.value = num;
  }

  // ── View Mode & Pagination ────────────────────────────────────────────────
  function setViewMode(mode) {
    state.viewMode = mode;
    try {
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem('hecos_search_view_mode', mode);
      }
    } catch (e) { }
    updateViewModeButtons();
    renderCurrentView();
  }

  function updateViewModeButtons() {
    const btnScroll = document.getElementById('btn-view-scroll');
    const btnPaging = document.getElementById('btn-view-paging');
    if (btnScroll) btnScroll.classList.toggle('active', state.viewMode === 'scroll');
    if (btnPaging) btnPaging.classList.toggle('active', state.viewMode === 'paging');
  }

  function gotoPage(p) {
    state.currentPage = p;
    renderCurrentView();
    const list = document.getElementById('results-list');
    if (list) list.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function prevPage() {
    if (state.currentPage > 1) {
      gotoPage(state.currentPage - 1);
    }
  }

  function nextPage() {
    const filtered = getFilteredResults();
    const totalPages = Math.max(1, Math.ceil(filtered.length / state.pageSize));
    if (state.currentPage < totalPages) {
      gotoPage(state.currentPage + 1);
    }
  }

  function gotoLastPage() {
    const filtered = getFilteredResults();
    const totalPages = Math.max(1, Math.ceil(filtered.length / state.pageSize));
    gotoPage(totalPages);
  }

  function setPageSize(size) {
    state.pageSize = parseInt(size) || 25;
    state.currentPage = 1;
    renderCurrentView();
  }

  // ── Infinite Scroll Observer ───────────────────────────────────────────────
  let infiniteScrollObserver = null;
  let stageScrollListenerBound = false;

  function initInfiniteScroll() {
    const sentinel = document.getElementById('infinite-scroll-sentinel');
    const stage = document.querySelector('.search-stage');
    if (!sentinel) return;

    if (infiniteScrollObserver) {
      infiniteScrollObserver.disconnect();
    }

    // Explicitly observe scrolling relative to .search-stage scroll container
    infiniteScrollObserver = new IntersectionObserver((entries) => {
      const entry = entries[0];
      if (entry && entry.isIntersecting && state.viewMode === 'scroll') {
        const filtered = getFilteredResults();
        if (state.scrollRenderCount < filtered.length) {
          state.scrollRenderCount += 35;
          renderCurrentView();
        } else if (state.autoFetchMore && !state.isFetchingMore && !state.activeEventSource && state.currentQuery && state.results.length > 0) {
          if (window.fetchMoreFromWeb) window.fetchMoreFromWeb();
        }
      }
    }, {
      root: stage || null,
      rootMargin: '350px'
    });

    infiniteScrollObserver.observe(sentinel);

    // Complementary scroll listener on .search-stage for 100% reliability
    if (stage && !stageScrollListenerBound) {
      stageScrollListenerBound = true;
      stage.addEventListener('scroll', () => {
        if (state.viewMode !== 'scroll') return;
        const remaining = stage.scrollHeight - stage.scrollTop - stage.clientHeight;
        if (remaining < 400) {
          const filtered = getFilteredResults();
          if (state.scrollRenderCount < filtered.length) {
            state.scrollRenderCount += 35;
            renderCurrentView();
          } else if (remaining < 150 && state.autoFetchMore && !state.isFetchingMore && !state.activeEventSource && state.currentQuery && state.results.length > 0) {
            if (window.fetchMoreFromWeb) window.fetchMoreFromWeb();
          }
        }
      }, { passive: true });
    }
  }

  // ── Matching & Filtering Predicates ───────────────────────────────────────
  function itemMatchesFilter(item, filterId, currentMode) {
    if (!filterId || filterId === 'all') return true;

    // 1. Clear Web subtabs
    if (filterId === 'web') {
      return item.network === 'clearnet' && (
        item.category === 'web' || item.category === 'news' || item.category === 'general' ||
        item.category === 'social media' || item.category === 'it' || item.category === 'science' ||
        ['clear_ddgs', 'clear_news', 'clear_searxng'].includes(item.engine_id) ||
        (!['images', 'videos', 'audio', 'music', 'files'].includes(item.category) && !item.metadata?.extension)
      );
    }
    if (filterId === 'images') {
      return item.category === 'images' || (item.engine_id === 'media_images') || (item.engine && (item.engine.includes('image') || item.engine.includes('flickr') || item.engine.includes('deviantart') || item.engine.includes('wallhaven') || item.engine.includes('pinterest') || item.engine.includes('unsplash') || item.engine.includes('openverse'))) || (item.thumbnail_url && item.category !== 'videos');
    }
    if (filterId === 'videos') {
      return item.category === 'videos' || (item.engine_id === 'media_videos') || (item.engine && (item.engine.includes('video') || item.engine.includes('youtube') || item.engine.includes('dailymotion') || item.engine.includes('peertube') || item.engine.includes('vimeo') || item.engine.includes('rumble') || item.engine.includes('piped') || item.engine.includes('odysee') || item.engine.includes('bitchute')));
    }
    if (filterId === 'audio') {
      return item.category === 'audio' || item.category === 'music' || (item.engine_id === 'media_audio') || (item.engine && (item.engine.includes('audio') || item.engine.includes('podcast') || item.engine.includes('soundcloud') || item.engine.includes('music') || item.engine.includes('itunes') || item.engine.includes('deezer') || item.engine.includes('bandcamp') || item.engine.includes('radio') || item.engine.includes('mixcloud') || item.engine.includes('genius')));
    }
    if (filterId === 'files') {
      return item.category === 'files' || item.category === 'packages' || (item.engine_id === 'files_dorks') || (item.engine && (item.engine.includes('dork') || item.engine.includes('torrent') || item.engine.includes('piratebay') || item.engine.includes('kickass') || item.engine.includes('solidtorrent') || item.engine.includes('bt4g') || item.engine.includes('archive') || item.engine.includes('zlibrary'))) || Boolean(item.metadata && item.metadata.extension);
    }

    // 2. Dark Web subtabs
    if (filterId === 'dark_directories') {
      const text = `${item.title || ''} ${item.snippet || ''} ${item.url || ''}`.toLowerCase();
      return /wiki|directory|tordir|hidden\s*wiki|index|portal|catalog|onion\s*links|dark\s*dir|links\s*list/.test(text);
    }
    if (filterId === 'dark_forums') {
      const text = `${item.title || ''} ${item.snippet || ''} ${item.url || ''}`.toLowerCase();
      return /forum|board|chan|talk|community|dread|discuss|chat|thread|post/.test(text);
    }
    if (filterId === 'dark_leaks') {
      const text = `${item.title || ''} ${item.snippet || ''} ${item.url || ''}`.toLowerCase();
      return /leak|dump|whistle|paste|archive|breach|database|vault|hack|exfiltrat|secret|expose/.test(text);
    }
    if (filterId === 'dark_market') {
      const text = `${item.title || ''} ${item.snippet || ''} ${item.url || ''}`.toLowerCase();
      return /market|shop|store|vendor|service|escrow|crypto|exchange|wallet|drug|carding|counterfeit|buy|sell/.test(text);
    }

    // 3. File Hunter subtabs
    const ext = (item.metadata?.extension || (item.url ? item.url.split('.').pop().split(/[?#]/)[0] : '') || '').toLowerCase();
    if (filterId === 'files_docs') {
      return ['pdf', 'docx', 'doc', 'epub', 'odt', 'txt', 'rtf'].includes(ext) || /\[(pdf|doc|docx|epub)\]/i.test(item.title || '');
    }
    if (filterId === 'files_data') {
      return ['xlsx', 'xls', 'csv', 'sql', 'json', 'xml', 'sqlite', 'db', 'tsv'].includes(ext) || /\[(xlsx|csv|sql|json)\]/i.test(item.title || '');
    }
    if (filterId === 'files_archives') {
      return ['zip', 'rar', '7z', 'tar', 'gz', 'iso', 'bz2', 'xz'].includes(ext) || /\[(zip|rar|7z|iso)\]/i.test(item.title || '');
    }
    if (filterId === 'files_code') {
      return ['py', 'js', 'sh', 'bat', 'c', 'cpp', 'html', 'css', 'yaml', 'yml', 'env', 'rs', 'go', 'php'].includes(ext);
    }

    // 4. OSINT subtabs
    const platform = (item.metadata?.platform || item.title || '').toLowerCase();
    if (filterId === 'osint_social') {
      return /reddit|telegram|medium|pinterest|producthunt|twitter|instagram|facebook|tiktok|threads/.test(platform);
    }
    if (filterId === 'osint_dev') {
      return /github|gitlab|dev\.to|hackernews|keybase|bitbucket|stackoverflow/.test(platform);
    }
    if (filterId === 'osint_media') {
      return /steam|twitch|spotify|soundcloud|flickr|vimeo|youtube/.test(platform);
    }

    // 5. Global Sweep (Deep) subtabs
    if (filterId === 'deep_clear') {
      return item.network === 'clearnet' && !['images', 'videos', 'audio'].includes(item.category);
    }
    if (filterId === 'deep_dark') {
      return item.network === 'tor' || (item.url && item.url.includes('.onion')) || (item.engine_id && item.engine_id.startsWith('dark_'));
    }
    if (filterId === 'deep_media') {
      return ['images', 'videos', 'audio'].includes(item.category) || ['media_images', 'media_videos', 'media_audio'].includes(item.engine_id);
    }
    if (filterId === 'deep_files') {
      return item.category === 'files' || Boolean(item.metadata?.extension);
    }

    return true;
  }

  function updateFilterCounts() {
    const currentMode = state.currentMode || 'clear';
    const subtabs = MODE_SUBTABS[currentMode] || MODE_SUBTABS.clear;
    const results = state.results || [];

    subtabs.forEach(tab => {
      let count = 0;
      if (tab.id === 'all') {
        count = results.length;
      } else {
        count = results.filter(r => itemMatchesFilter(r, tab.id, currentMode)).length;
      }
      const el = document.getElementById(`count-${tab.id}`);
      if (el) el.innerText = count;
      const tabEl = document.getElementById(`filter-tab-${tab.id}`);
      if (tabEl) {
        tabEl.classList.toggle('has-results', count > 0);
      }
    });
  }

  function engineMatches(r, target) {
    if (!target) return true;
    target = target.toLowerCase();
    const engId = (r.engine_id || r.metadata?.engine_id || '').toLowerCase();
    const eng = (r.engine || '').toLowerCase();
    const cat = (r.category || '').toLowerCase();

    if (engId === target || eng === target) return true;
    if (r.metadata?.engine_ids && r.metadata.engine_ids.includes(target)) return true;

    const cleanTarget = target.replace(/^(clear_|media_|dark_|osint_)/, '');
    const cleanEng = eng.replace(/^(ddgs:|rss:|torch:|ahmia:|haystak:|osint:)/, '');

    if (cleanTarget === cleanEng) return true;
    if (eng.includes(cleanTarget) || cleanEng.includes(cleanTarget)) return true;
    if (engId && (engId.includes(cleanTarget) || cleanTarget.includes(engId))) return true;

    if (target === 'clear_news' && (cat === 'news' || eng.includes('news'))) return true;
    if (target === 'clear_ddgs' && (eng.includes('ddgs') || eng.includes('clearnet') || eng.includes('duckduckgo') || engId.includes('ddgs') || engId.includes('duckduckgo'))) return true;
    if (target === 'media_images' && (cat === 'images' || eng.includes('image') || eng.includes('commons'))) return true;
    if (target === 'media_videos' && (cat === 'videos' || eng.includes('video') || eng.includes('yt-dlp') || eng.includes('youtube') || eng.includes('archive_org:video'))) return true;
    if (target === 'media_audio' && (cat === 'audio' || eng.includes('audio') || eng.includes('podcast') || eng.includes('archive_org:audio'))) return true;
    if (target === 'files_dorks' && (cat === 'files' || eng.includes('dork') || eng.includes('file') || eng.includes('archive_org:texts'))) return true;
    if (target === 'clear_searxng' && (eng.includes('searx') || eng.includes('searxng') || engId.includes('searx') || engId.includes('searxng'))) return true;
    if (target === 'osint_sherlock' && (cat === 'osint' || eng.includes('sherlock'))) return true;
    if (target.startsWith('dark_')) {
      const darkName = target.replace(/^dark_/, '');
      if (engId === target || eng === darkName || eng.includes(darkName) || engId.includes(darkName)) return true;
      if (r.network === 'tor' || (r.url && r.url.includes('.onion'))) return true;
    }

    return false;
  }

  function getFilteredResults() {
    let filtered = [...state.results];
    // Apply exclusions first — match on raw r.engine (same key as provider chips)
    if (state.excludedProviders && state.excludedProviders.length > 0) {
      filtered = filtered.filter(r => {
        const rawEng = (r.engine || r.engine_id || '').trim().toLowerCase();
        return !state.excludedProviders.includes(rawEng);
      });
    }
    if (state.activeProvider) {
      filtered = filtered.filter(r => providerMatches(r, state.activeProvider));
    } else if (state.activeEngine) {
      filtered = filtered.filter(r => engineMatches(r, state.activeEngine));
    }
    if (state.activeFilter && state.activeFilter !== 'all') {
      filtered = filtered.filter(r => itemMatchesFilter(r, state.activeFilter, state.currentMode));
    }
    return filtered;
  }

  function renderCurrentView() {
    const resultsRenderer = window.SearchResults;
    const filtered = getFilteredResults();
    const infiniteFooter = document.getElementById('infinite-scroll-footer');
    const infiniteStatus = document.getElementById('infinite-scroll-status');
    const paginationFooter = document.getElementById('pagination-footer');
    const resultsCountEl = document.getElementById('results-count');

    updateViewModeButtons();

    if (filtered.length === 0) {
      if (infiniteFooter) infiniteFooter.style.display = 'none';
      if (paginationFooter) paginationFooter.style.display = 'none';
      if (resultsRenderer) resultsRenderer.render([], 'results-list', state.currentMode, state.activeFilter);
      const filterText = state.activeFilter !== 'all' ? ` (Filter: ${state.activeFilter})` : '';
      let sourceText = '';
      if (state.activeProvider) {
        const prov = KNOWN_PROVIDERS.find(p => p.id === state.activeProvider);
        sourceText = ` • Provider: ${prov ? prov.name : state.activeProvider}`;
      } else if (state.activeEngine) {
        sourceText = ` • Engine: ${state.activeEngine}`;
      }
      if (resultsCountEl) {
        resultsCountEl.innerText = state.results.length === 0 ? 'No results found' : `0 di ${state.results.length} results match active filter${filterText}${sourceText}`;
      }
      return;
    }

    if (state.viewMode === 'scroll') {
      if (paginationFooter) paginationFooter.style.display = 'none';
      if (infiniteFooter) infiniteFooter.style.display = 'flex';

      const visibleCount = Math.min(state.scrollRenderCount, filtered.length);
      const visibleItems = filtered.slice(0, visibleCount);
      if (resultsRenderer) resultsRenderer.render(visibleItems, 'results-list', state.currentMode, state.activeFilter);

      if (infiniteStatus) {
        if (state.isFetchingMore) {
          infiniteStatus.innerHTML = `
            <div class="fetch-more-status loading">
              <i class="fas fa-satellite fa-spin" style="color:var(--accent-cyan);"></i>
              <span>Fetching Page ${(state.backendPage || 1) + 1} from web across engines...</span>
            </div>
          `;
        } else if (visibleCount < filtered.length) {
          infiniteStatus.innerHTML = `
            <div class="fetch-more-status in-memory">
              <i class="fas fa-circle-notch fa-spin"></i>
              <span>Showing ${visibleCount} of ${filtered.length} in-memory results (scroll down for more)</span>
            </div>
          `;
        } else {
          const nextPage = (state.backendPage || 1) + 1;
          infiniteStatus.innerHTML = `
            <div class="fetch-more-container">
              <div class="fetch-more-info">
                <i class="fas fa-check-circle" style="color:var(--accent-emerald);"></i>
                <span>All <strong>${filtered.length}</strong> results in current pool displayed.</span>
              </div>
              <div class="fetch-more-controls">
                <button type="button" class="btn-fetch-more-web" id="btn-fetch-more-web" onclick="window.fetchMoreFromWeb()">
                  <i class="fas fa-globe"></i>
                  <span>Fetch More from Web (Page ${nextPage})</span>
                </button>
                <label class="auto-fetch-toggle" title="Automatically query web engines for subsequent pages when you reach the bottom">
                  <input type="checkbox" id="chk-auto-fetch-more" ${state.autoFetchMore ? 'checked' : ''} onchange="window.toggleAutoFetchMore(this.checked)">
                  <span class="toggle-box"></span>
                  <span class="toggle-label">Auto-fetch on scroll</span>
                </label>
              </div>
            </div>
          `;
        }
      }
      initInfiniteScroll();
    } else {
      if (infiniteFooter) infiniteFooter.style.display = 'none';
      if (paginationFooter) paginationFooter.style.display = 'flex';

      const totalPages = Math.max(1, Math.ceil(filtered.length / state.pageSize));
      if (state.currentPage > totalPages) state.currentPage = totalPages;
      if (state.currentPage < 1) state.currentPage = 1;

      const startIndex = (state.currentPage - 1) * state.pageSize;
      const visibleItems = filtered.slice(startIndex, startIndex + state.pageSize);
      if (resultsRenderer) resultsRenderer.render(visibleItems, 'results-list', state.currentMode, state.activeFilter);

      const badgePage = document.getElementById('badge-page-info');
      if (badgePage) {
        badgePage.innerText = `Page ${state.currentPage} of ${totalPages} (${filtered.length} items)`;
      }

      const btnFirst = document.getElementById('btn-page-first');
      const btnPrev = document.getElementById('btn-page-prev');
      const btnNext = document.getElementById('btn-page-next');
      const btnLast = document.getElementById('btn-page-last');
      if (btnFirst) btnFirst.disabled = (state.currentPage === 1);
      if (btnPrev) btnPrev.disabled = (state.currentPage === 1);
      if (btnNext) btnNext.disabled = (state.currentPage === totalPages);
      if (btnLast) btnLast.disabled = (state.currentPage === totalPages);

      const pagePills = document.getElementById('page-pills');
      if (pagePills) {
        pagePills.innerHTML = '';
        const maxPagesToShow = 5;
        let startPage = Math.max(1, state.currentPage - Math.floor(maxPagesToShow / 2));
        let endPage = Math.min(totalPages, startPage + maxPagesToShow - 1);
        if (endPage - startPage < maxPagesToShow - 1) {
          startPage = Math.max(1, endPage - maxPagesToShow + 1);
        }

        function createPageBtn(p) {
          const btn = document.createElement('button');
          btn.type = 'button';
          btn.className = 'page-num-btn' + (p === state.currentPage ? ' active' : '');
          btn.innerText = p;
          btn.onclick = () => window.gotoPage(p);
          return btn;
        }

        if (startPage > 1) {
          pagePills.appendChild(createPageBtn(1));
          if (startPage > 2) {
            const dots = document.createElement('span');
            dots.innerText = '…';
            dots.style.cssText = 'color:var(--muted); padding:0 3px; font-size:12px;';
            pagePills.appendChild(dots);
          }
        }

        for (let p = startPage; p <= endPage; p++) {
          pagePills.appendChild(createPageBtn(p));
        }

        if (endPage < totalPages) {
          if (endPage < totalPages - 1) {
            const dots = document.createElement('span');
            dots.innerText = '…';
            dots.style.cssText = 'color:var(--muted); padding:0 3px; font-size:12px;';
            pagePills.appendChild(dots);
          }
          pagePills.appendChild(createPageBtn(totalPages));
        }
      }
    }

    const filterText = state.activeFilter !== 'all' ? ` (Filter: ${state.activeFilter})` : '';
    let sourceText = '';
    if (state.activeProvider) {
      const prov = KNOWN_PROVIDERS.find(p => p.id === state.activeProvider);
      sourceText = ` • Provider: ${prov ? prov.name : state.activeProvider}`;
    } else if (state.activeEngine) {
      sourceText = ` • Engine: ${state.activeEngine}`;
    }
    if (resultsCountEl) {
      resultsCountEl.innerText = `${filtered.length} of ${state.results.length} results found${filterText}${sourceText}`;
    }
  }

  // ── Export Interface and Global Aliases ─────────────────────────────────────
  window.SearchFilters = {
    MODE_SUBTABS,
    renderFilterTabsForMode,
    setFilter,
    filterByEngine,
    clearEngineFilter,
    updateFilterCounts,
    updateEngineChipsSelection,
    toggleContentFilter,
    toggleDarkFilter,
    toggleLocalOnly,
    setSearchDepth,
    setSearchDepthPreset,
    setViewMode,
    updateViewModeButtons,
    gotoPage,
    prevPage,
    nextPage,
    gotoLastPage,
    setPageSize,
    initInfiniteScroll,
    getFilteredResults,
    renderCurrentView,
    itemMatchesFilter,
    engineMatches,
    extractProvider,
    providerMatches,
    filterByProvider,
    clearProviderFilter,
    toggleExcludeProvider,
    clearAllExclusions,
    updateExclusionBar,
    renderGranularProviderChips,
    toggleStreamBarCollapse,
    updateCollapsedPill
  };

  // Global window bindings for backward compatibility and HTML onclick handlers
  window.setFilter = setFilter;
  window.filterByEngine = filterByEngine;
  window.clearEngineFilter = clearEngineFilter;
  window.engineMatches = engineMatches;
  window.filterByProvider = filterByProvider;
  window.clearProviderFilter = clearProviderFilter;
  window.toggleExcludeProvider = toggleExcludeProvider;
  window.clearAllExclusions = clearAllExclusions;
  window.updateExclusionBar = updateExclusionBar;
  window.renderGranularProviderChips = renderGranularProviderChips;
  window.toggleStreamBarCollapse = toggleStreamBarCollapse;
  window.updateCollapsedPill = updateCollapsedPill;
  window.updateFilterCounts = updateFilterCounts;
  window.renderCurrentView = renderCurrentView;
  window.toggleContentFilter = toggleContentFilter;
  window.toggleDarkFilter = toggleDarkFilter;
  window.toggleLocalOnly = toggleLocalOnly;
  window.setSearchDepth = setSearchDepth;
  window.setSearchDepthPreset = setSearchDepthPreset;
  window.setViewMode = setViewMode;
  window.gotoPage = gotoPage;
  window.prevPage = prevPage;
  window.nextPage = nextPage;
  window.gotoLastPage = gotoLastPage;
  function toggleAutoFetchMore(val) {
    state.autoFetchMore = Boolean(val);
    try {
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem('hecos_netsearch_autofetch', state.autoFetchMore ? 'true' : 'false');
      }
    } catch (e) { }
  }
  window.toggleAutoFetchMore = toggleAutoFetchMore;
  window.setPageSize = setPageSize;
  // Restore initial collapse state from state.isStreamCollapsed
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      if (state.isStreamCollapsed) toggleStreamBarCollapse(null, true);
    });
  } else {
    if (state.isStreamCollapsed) toggleStreamBarCollapse(null, true);
  }
})();

