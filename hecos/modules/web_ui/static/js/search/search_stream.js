/**
 * search_stream.js
 * Real-time SSE query execution, engine progress badges, and stop control for Deep Search.
 */
(function () {
  const state = window.SearchState;
  const api = window.SearchAPI;

  function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  /**
   * parseQueryOperators(rawQuery)
   * Parses special operators from a query string.
   * Returns { cleanQuery, excluded, site, lang, after, before, mode, limit }
   *
   * Supported operators:
   *   -provider      Exclude a provider (e.g. -youtube, -bing, -eporner)
   *   site:domain    Restrict results to a domain
   *   lang:XX        Language filter (e.g. lang:it, lang:en)
   *   after:YYYY     Results after year (e.g. after:2020)
   *   before:YYYY    Results before year (e.g. before:2024)
   *   mode:M         Force search mode (clear/dark/files/osint/deep)
   *   limit:N        Override result limit
   */
  function parseQueryOperators(rawQuery) {
    // Engine/provider name prefixes that signal a valid -exclusion token.
    // Also accepts exact raw engine strings like ddgs:images, searxng:yahoo, rss:google_news.
    const ENGINE_PREFIXES = [
      'google', 'bing', 'yandex', 'duckduckgo', 'ddg', 'yahoo', 'wikipedia', 'brave',
      'startpage', 'unsplash', 'openverse', 'dailymotion', 'peertube', 'youtube', 'yt',
      'vimeo', 'rumble', 'eporner', 'redtube', 'archive', 'soundcloud', 'mixcloud',
      'itunes', 'artic', 'genius', 'dork', 'ahmia', 'torch', 'haystak', 'excavator',
      'phobos', 'tor66', 'danieltore', 'searxng', 'ddgs', 'rss', 'bandcamp',
      'clear', 'media', 'audio', 'news', 'files', 'osint', 'dark'
    ];

    const tokens = rawQuery.trim().split(/\s+/);
    const excluded = [];
    let site = null, lang = null, after = null, before = null, mode = null, limit = null;
    const cleanTokens = [];

    for (const token of tokens) {
      const lower = token.toLowerCase();

      // -provider or -engine exclusion
      // Accept: -youtube, -bing, -ddgs:images, -searxng:yahoo, -rss:google_news, etc.
      if (lower.startsWith('-') && lower.length > 1) {
        const maybeProvider = lower.slice(1);
        // Allow if it starts with a known prefix or contains a colon (raw engine format)
        const isKnown = ENGINE_PREFIXES.some(pfx => maybeProvider === pfx || maybeProvider.startsWith(pfx));
        const hasColon = maybeProvider.includes(':');
        if (isKnown || hasColon) {
          excluded.push(maybeProvider);
          continue;
        }
      }

      // site:domain
      if (lower.startsWith('site:') && lower.length > 5) {
        site = lower.slice(5);
        continue;
      }

      // lang:XX
      if (lower.startsWith('lang:') && lower.length > 5) {
        lang = lower.slice(5);
        continue;
      }

      // after:YYYY
      if (lower.startsWith('after:') && lower.length > 6) {
        after = lower.slice(6);
        continue;
      }

      // before:YYYY
      if (lower.startsWith('before:') && lower.length > 7) {
        before = lower.slice(7);
        continue;
      }

      // mode:M
      if (lower.startsWith('mode:') && lower.length > 5) {
        const m = lower.slice(5);
        if (['clear', 'dark', 'files', 'osint', 'deep', 'media'].includes(m)) {
          mode = m;
          continue;
        }
      }

      // limit:N
      if (lower.startsWith('limit:') && lower.length > 6) {
        const n = parseInt(lower.slice(6));
        if (!isNaN(n) && n >= 0) {
          limit = n;
          continue;
        }
      }

      cleanTokens.push(token);
    }

    return {
      cleanQuery: cleanTokens.join(' ').trim(),
      excluded,
      site,
      lang,
      after,
      before,
      mode,
      limit
    };
  }

  // ── Engine Display Names & Descriptions (Top Row) ─────────────────────────
  const HECOS_ENGINE_INFO = {
    'clear_ddgs': {
      name: 'DuckDuckGo Web',
      icon: 'fas fa-feather',
      desc: 'DuckDuckGo direct multi-page web scraper (Clearnet)'
    },
    'clear_searxng': {
      name: 'SearXNG Meta',
      icon: 'fas fa-magnifying-glass',
      desc: 'Local metasearch aggregator (Yahoo, Bing, Yandex, Wikipedia)'
    },
    'clear_news': {
      name: 'Live News',
      icon: 'fas fa-newspaper',
      desc: 'News aggregator: DuckDuckGo News + Google News RSS'
    },
    'media_videos': {
      name: 'Video Hunter',
      icon: 'fas fa-video',
      desc: 'Video aggregator: YouTube (yt-dlp), Dailymotion, PeerTube, Archive'
    },
    'media_images': {
      name: 'Images HD',
      icon: 'fas fa-image',
      desc: 'High-res image scraper: DuckDuckGo Images, Wikimedia, Unsplash'
    },
    'media_audio': {
      name: 'Audio & Music',
      icon: 'fas fa-music',
      desc: 'Audio aggregator: Apple Podcasts/Music, Archive.org, SoundCloud'
    },
    'files_dorks': {
      name: 'File Hunter',
      icon: 'fas fa-file-shield',
      desc: 'Targeted file & document dorking (PDF, DOCX, XLSX, ZIP, EPUB)'
    },
    'osint_sherlock': {
      name: 'OSINT Hunt',
      icon: 'fas fa-id-badge',
      desc: 'Targeted identity discovery across 400+ online platforms'
    },
    'dark_ahmia': { name: 'Ahmia (Tor)', icon: 'fas fa-user-secret', desc: 'Tor onion search directory' },
    'dark_torch': { name: 'Torch (Tor)', icon: 'fas fa-fire', desc: 'Tor hidden services index' },
    'dark_haystak': { name: 'Haystak (Tor)', icon: 'fas fa-wheat-awn', desc: 'Deep Tor onion search engine' },
    'dark_excavator': { name: 'Excavator (Tor)', icon: 'fas fa-compass', desc: 'Tor hidden services crawler' },
    'dark_phobos': { name: 'Phobos (Tor)', icon: 'fas fa-moon', desc: 'Tor onion network index' },
    'dark_tor66': { name: 'Tor66 (Tor)', icon: 'fas fa-route', desc: 'Tor relay directory and onion crawler' },
    'dark_danieltore': { name: 'Daniel (Tor)', icon: 'fas fa-network-wired', desc: 'Daniel Winzen onion directory' }
  };

  function getHecosEngineInfo(engineId) {
    if (!engineId) return { name: 'Unknown', icon: 'fas fa-circle-nodes', desc: '' };
    const lower = engineId.toLowerCase();
    if (HECOS_ENGINE_INFO[lower]) return HECOS_ENGINE_INFO[lower];
    // Fallback: humanize "media_videos" -> "Media Videos"
    const cleanName = lower.replace(/^(clear_|media_|files_|dark_|osint_)/, '').replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    return { name: cleanName, icon: 'fas fa-circle-nodes', desc: engineId };
  }

  function executeSearch(queryStr, mode = 'clear') {
    if (!queryStr || !queryStr.trim()) return;
    queryStr = queryStr.trim();
    state.currentQuery = queryStr;
    state.currentMode = mode;

    const filters = window.SearchFilters;
    const resultsRenderer = window.SearchResults;
    const copilot = window.SearchCopilot;

    // Ensure contextual subtabs match the active mode
    if (filters && filters.renderFilterTabsForMode) {
      filters.renderFilterTabsForMode(mode, true);
    }

    state.resetResults();
    if (filters && filters.updateFilterCounts) {
      filters.updateFilterCounts();
    }

    const resultsCountEl = document.getElementById('results-count');
    const resultsDurationEl = document.getElementById('results-duration');
    const streamBar = document.getElementById('stream-live-bar');
    const streamBadges = document.getElementById('stream-badges');
    const streamStatusIcon = document.getElementById('stream-status-icon');
    const streamStatusText = document.getElementById('stream-status-text');
    const btnClearEngine = document.getElementById('btn-clear-engine-filter');
    const btnStop = document.getElementById('search-stop');

    if (resultsRenderer) {
      resultsRenderer.render([], 'results-list', mode, state.activeFilter);
    }
    if (resultsCountEl) resultsCountEl.innerText = 'Searching across engines...';
    if (resultsDurationEl) resultsDurationEl.innerText = '';

    // Setup persistent engine stream bar & provider section
    if (streamBadges) streamBadges.innerHTML = '';
    const streamProviderBadges = document.getElementById('stream-provider-badges');
    const streamProvidersSection = document.getElementById('stream-providers-section');
    if (streamProviderBadges) streamProviderBadges.innerHTML = '';
    if (streamProvidersSection) streamProvidersSection.style.display = 'none';
    if (streamBar) {
      streamBar.classList.add('active');
      streamBar.classList.toggle('is-collapsed', Boolean(state.isStreamCollapsed));
    }
    if (streamStatusIcon) {
      streamStatusIcon.className = 'fas fa-satellite fa-spin';
      streamStatusIcon.style.color = 'var(--accent-cyan)';
    }
    if (streamStatusText) {
      streamStatusText.innerText = 'Real-time engine query:';
    }
    if (btnClearEngine) {
      btnClearEngine.style.display = 'none';
    }
    if (btnStop) {
      btnStop.style.display = 'inline-flex';
    }

    // ── Query Operator Parser ─────────────────────────────────────────────────
    // Parse inline operators from query string before sending to backend.
    // Supported: -provider, site:domain, lang:XX, after:YYYY, before:YYYY, mode:M, limit:N
    const parsedOps = parseQueryOperators(queryStr);
    const cleanQuery = parsedOps.cleanQuery;
    const parsedExcluded = parsedOps.excluded;   // from -provider tokens
    const parsedSite = parsedOps.site;           // from site:domain
    const parsedLang = parsedOps.lang;           // from lang:XX
    const parsedAfter = parsedOps.after;         // from after:YYYY
    const parsedBefore = parsedOps.before;       // from before:YYYY
    const parsedMode = parsedOps.mode || mode;   // from mode:M
    const parsedLimit = parsedOps.limit || state.searchLimit;

    // Merge state.excludedProviders with parsed -provider tokens
    const allExcluded = [...new Set([...(state.excludedProviders || []), ...parsedExcluded])];

    // Update search input to show clean query (without operators) subtly
    const searchInput = document.getElementById('search-input');
    if (searchInput && cleanQuery !== queryStr) {
      searchInput.dataset.rawQuery = queryStr;
      // Show a badge that operators are active
      let opBadge = document.getElementById('op-indicator-badge');
      if (!opBadge) {
        opBadge = document.createElement('div');
        opBadge.id = 'op-indicator-badge';
        opBadge.className = 'op-indicator-badge';
        opBadge.title = 'Active query operators — click [?] for syntax help';
        const parent = searchInput.closest('.search-input-row') || searchInput.parentElement;
        if (parent) parent.appendChild(opBadge);
      }
      const opParts = [];
      if (parsedExcluded.length > 0) opParts.push(`-${parsedExcluded.join(', -')}`);
      if (parsedSite) opParts.push(`site:${parsedSite}`);
      if (parsedLang) opParts.push(`lang:${parsedLang}`);
      if (parsedAfter) opParts.push(`after:${parsedAfter}`);
      if (parsedBefore) opParts.push(`before:${parsedBefore}`);
      if (parsedOps.mode) opParts.push(`mode:${parsedOps.mode}`);
      if (parsedOps.limit) opParts.push(`limit:${parsedOps.limit}`);
      opBadge.innerHTML = `<i class="fas fa-sliders"></i> ${opParts.join(' · ')}`;
      opBadge.style.display = 'flex';
    } else {
      const opBadge = document.getElementById('op-indicator-badge');
      if (opBadge) opBadge.style.display = 'none';
    }

    const params = {
      query: cleanQuery || queryStr,
      mode: parsedMode,
      limit: parsedLimit,
      safe_search: state.safeSearch,
      dark_bypass: state.darkBypass !== false,
      local_only: !!state.localOnly,
      excluded_providers: allExcluded.join(','),
      language: parsedLang || '',
      domain_filter: parsedSite || ''
    };

    state.activeEventSource = api.queryStream(
      params,
      // On Engine Event
      (evt) => {
        if (evt.type === 'start') {
          if (evt.session_id) {
            state.activeSessionId = evt.session_id;
            state.currentSessionId = evt.session_id;
          }
          if (streamBadges && evt.engines) {
            streamBadges.innerHTML = evt.engines.map(e => {
              const info = getHecosEngineInfo(e);
              return `
                <button class="engine-chip running" id="chip-${e}" data-engine="${e}" onclick="window.filterByEngine('${e}')" title="${info.name}\n${info.desc}\nStatus: Querying in background...">
                  <i class="fas fa-spinner fa-spin"></i> <span class="chip-engine-name">${info.name}</span>
                </button>
              `;
            }).join('');
          }
        } else if (evt.type === 'engine_done') {
          // If there are net-new results, add them to state first
          if (evt.new_results && evt.new_results.length > 0) {
            state.addResults(evt.new_results, evt.engine);
          }

          // Count all results matching this engine in state (including deduplicated results attributed to it)
          const matchingInState = state.results.filter(r => {
            if (window.SearchFilters && window.SearchFilters.engineMatches) {
              return window.SearchFilters.engineMatches(r, evt.engine);
            }
            if (window.engineMatches) {
              return window.engineMatches(r, evt.engine);
            }
            return r.engine_id === evt.engine;
          }).length;

          const newCnt = evt.new_results ? evt.new_results.length : 0;
          // Effective count: use raw_count found by backend, net-new results, or matching results in state
          const effectiveCount = Math.max(evt.raw_count || 0, newCnt, matchingInState);

          // Compute per-category breakdown for this engine's results
          const catBreakdown = {};
          if (evt.new_results && evt.new_results.length > 0) {
            evt.new_results.forEach(r => {
              const cat = r.category || 'web';
              catBreakdown[cat] = (catBreakdown[cat] || 0) + 1;
            });
          }

          state.engineStats[evt.engine] = {
            count: effectiveCount,
            raw_count: evt.raw_count || 0,
            new_count: newCnt,
            duration_ms: evt.duration_ms,
            status: 'done',
            categories: catBreakdown
          };

          let chip = document.getElementById(`chip-${evt.engine}`);
          if (!chip && streamBadges) {
            chip = document.createElement('button');
            chip.id = `chip-${evt.engine}`;
            chip.dataset.engine = evt.engine;
            streamBadges.appendChild(chip);
          }
          if (chip) {
            // Status icon: green check if has results, grey dash if 0
            const hasResults = effectiveCount > 0;
            const statusIcon = hasResults ? 'fa-check' : 'fa-minus';
            const chipClass = hasResults ? 'done' : 'done empty';

            // Build category breakdown pills (images/videos/web/etc.)
            const CAT_ICONS = {
              images: '🖼', videos: '🎬', audio: '🎵', files: '📄',
              web: '🌐', general: '🌐', news: '📰', osint: '🔍'
            };
            let catPills = '';
            if (hasResults && Object.keys(catBreakdown).length > 0) {
              catPills = Object.entries(catBreakdown)
                .sort((a, b) => b[1] - a[1])
                .map(([cat, cnt]) => {
                  const icon = CAT_ICONS[cat] || '•';
                  return `<span class="chip-cat-pill" data-cat="${cat}" title="Filter ${cat}">${icon}${cnt}</span>`;
                }).join('');
            }

            const engInfo = getHecosEngineInfo(evt.engine);
            const dur = evt.duration_ms ? ` (${evt.duration_ms}ms)` : '';
            const tooltipLines = [`${engInfo.name}${dur}`, engInfo.desc, `Results found: ${effectiveCount}`];
            if (Object.keys(catBreakdown).length > 0) {
              tooltipLines.push('Categories: ' + Object.entries(catBreakdown).map(([c, n]) => `${c}: ${n}`).join(', '));
            }
            tooltipLines.push('Click to filter exclusively to this engine');

            chip.className = `engine-chip ${chipClass}` + (state.activeEngine === evt.engine ? ' selected-engine' : '');
            chip.dataset.engine = evt.engine;
            chip.title = tooltipLines.join('\n');
            chip.innerHTML = `<i class="fas ${statusIcon}"></i> <span class="chip-engine-name">${engInfo.name}</span> <span class="chip-count">${effectiveCount}</span>${catPills ? '<span class="chip-cats">' + catPills + '</span>' : ''}`;
            chip.onclick = (e) => {
              // Clicking a cat pill filters to that engine + category
              const catPillEl = e && e.target && e.target.closest('.chip-cat-pill');
              if (catPillEl) {
                e.preventDefault(); e.stopPropagation();
                const cat = catPillEl.dataset.cat;
                window.filterByEngine(evt.engine);
                if (window.SearchFilters && window.SearchFilters.setFilter) {
                  window.SearchFilters.setFilter(cat, true, false);
                }
                return;
              }
              if (e) { e.preventDefault(); e.stopPropagation(); }
              window.filterByEngine(evt.engine);
            };
          }

          if (evt.new_results && evt.new_results.length > 0) {
            if (filters) {
              filters.updateFilterCounts();
              if (filters.renderGranularProviderChips) {
                filters.renderGranularProviderChips();
              }
              filters.renderCurrentView();
            }
            if (copilot && copilot.update) {
              copilot.update(state.results, queryStr, mode);
            }
          }
        } else if (evt.type === 'fallback') {
          if (streamBadges) {
            streamBadges.innerHTML += `
              <button class="engine-chip" style="border-color:var(--accent-purple); color:var(--accent-purple);" title="Tor Fallback">
                <i class="fas fa-random"></i> Tor Fallback
              </button>
            `;
          }
        } else if (evt.type === 'error') {
          if (btnStop) btnStop.style.display = 'none';
          if (resultsCountEl) resultsCountEl.innerText = 'Search unavailable';
          const container = document.getElementById('results-list');
          if (container) {
            container.innerHTML = `
              <div style="text-align:center; padding: 48px 20px; color: var(--accent-rose, #f43f5e);">
                <div style="font-size: 36px; margin-bottom: 12px;"><i class="fas fa-exclamation-triangle"></i></div>
                <div style="font-size: 15px; font-weight:600; margin-bottom:6px;">Search Error</div>
                <div style="font-size: 13px; max-width: 500px; margin: 0 auto; color:var(--text-muted); line-height:1.6;">${escapeHtml(evt.error || 'Requested search mode is currently unavailable.')}</div>
              </div>
            `;
          }
        }
      },
      // On Complete
      (completeEvt) => {
        if (btnStop) btnStop.style.display = 'none';
        if (completeEvt && completeEvt.session_id) {
          state.activeSessionId = completeEvt.session_id;
          state.currentSessionId = completeEvt.session_id;
        }

        // Safety sweep: ensure NO engine chip is left spinning in .running state
        document.querySelectorAll('.engine-chip.running').forEach(chip => {
          const eng = chip.dataset.engine || chip.id.replace('chip-', '');
          const info = getHecosEngineInfo(eng);
          const matching = state.results.filter(r => {
            if (window.SearchFilters && window.SearchFilters.engineMatches) {
              return window.SearchFilters.engineMatches(r, eng);
            }
            if (window.engineMatches) {
              return window.engineMatches(r, eng);
            }
            return r.engine_id === eng;
          }).length;
          const stat = (state.engineStats && state.engineStats[eng]) || {};
          const cnt = Math.max(stat.count || 0, stat.raw_count || 0, matching);
          const icon = cnt > 0 ? 'fa-check' : 'fa-minus';
          chip.className = `engine-chip ${cnt > 0 ? 'done' : 'done empty'}` + (state.activeEngine === eng ? ' selected-engine' : '');
          chip.title = `${info.name}\n${info.desc}\nResults found: ${cnt}\nClick to filter exclusively to this engine`;
          chip.innerHTML = `<i class="fas ${icon}"></i> <span class="chip-engine-name">${info.name}</span> <span class="chip-count">${cnt}</span>`;
        });

        // Stream bar stays visible with clickable engine chips
        if (streamBar) {
          streamBar.classList.add('active');
          streamBar.classList.toggle('is-collapsed', Boolean(state.isStreamCollapsed));
        }
        if (streamStatusIcon) {
          streamStatusIcon.className = 'fas fa-circle-check';
          streamStatusIcon.style.color = 'var(--accent-emerald)';
        }

        // Build diagnostic summary: show count of empty vs populated engines
        const allStats = state.engineStats || {};
        const totalEngines = Object.keys(allStats).length;
        const enginesWithResults = Object.values(allStats).filter(s => s.count > 0).length;
        const emptyEngines = totalEngines - enginesWithResults;

        let statusLabel = `Engines completed (${enginesWithResults}/${totalEngines} with results):`;
        if (emptyEngines > 0) {
          statusLabel += ` — ${emptyEngines} returned 0 results (grey chips)`;
        }

        if (streamStatusText) {
          streamStatusText.innerText = statusLabel;
        }
        if (resultsDurationEl) {
          resultsDurationEl.innerText = `(${completeEvt.duration_ms}ms)`;
        }
        if (filters) {
          filters.updateFilterCounts();
          if (filters.renderGranularProviderChips) {
            filters.renderGranularProviderChips();
          }
          if (filters.updateCollapsedPill) {
            filters.updateCollapsedPill();
          }
          filters.renderCurrentView();
        }
        if (copilot && copilot.update) {
          copilot.update(state.results, queryStr, mode);
        }
        if (window.SearchHistory && window.SearchHistory.loadHistory) {
          window.SearchHistory.loadHistory();
        }
      },
      // On Error
      (err) => {
        if (btnStop) btnStop.style.display = 'none';
        console.error('[SearchStream] Stream error:', err);
      }
    );
  }

  function stopSearch() {
    if (state.activeEventSource) {
      state.activeEventSource.close();
      state.activeEventSource = null;
    }
    const btnStop = document.getElementById('search-stop');
    if (btnStop) btnStop.style.display = 'none';

    const streamStatusIcon = document.getElementById('stream-status-icon');
    const streamStatusText = document.getElementById('stream-status-text');

    if (streamStatusIcon) {
      streamStatusIcon.className = 'fas fa-stop-circle';
      streamStatusIcon.style.color = 'var(--accent-amber, #f59e0b)';
    }
    if (streamStatusText) {
      streamStatusText.innerText = `Search halted by user (${state.results.length} total results collected):`;
    }

    const filters = window.SearchFilters;
    const copilot = window.SearchCopilot;
    if (filters) {
      filters.updateFilterCounts();
      filters.renderCurrentView();
    }
    if (copilot && copilot.update) {
      copilot.update(state.results, state.currentQuery, state.currentMode);
    }
  }

  function fetchMoreFromWeb() {
    if (!state.currentQuery || state.isFetchingMore) return;
    if (state.activeEventSource) {
      console.warn('[SearchStream] An active query stream is already running. Wait for completion.');
      return;
    }

    state.isFetchingMore = true;
    const nextPage = (state.backendPage || 1) + 1;
    const mode = state.currentMode || 'clear';
    const queryStr = state.currentQuery;

    const filters = window.SearchFilters;
    const copilot = window.SearchCopilot;
    const streamBar = document.getElementById('stream-live-bar');
    const streamStatusIcon = document.getElementById('stream-status-icon');
    const streamStatusText = document.getElementById('stream-status-text');
    const btnStop = document.getElementById('search-stop');
    const infiniteStatus = document.getElementById('infinite-scroll-status');

    if (streamBar) {
      streamBar.classList.add('active');
    }
    if (streamStatusIcon) {
      streamStatusIcon.className = 'fas fa-satellite fa-spin';
      streamStatusIcon.style.color = 'var(--accent-cyan)';
    }
    if (streamStatusText) {
      streamStatusText.innerText = `Fetching next page from web (Page ${nextPage})...`;
    }
    if (btnStop) {
      btnStop.style.display = 'inline-flex';
    }
    if (infiniteStatus) {
      infiniteStatus.innerHTML = `<div class="fetch-more-status loading"><i class="fas fa-circle-notch fa-spin"></i> <span>Fetching Page ${nextPage} from web across engines...</span></div>`;
    }

    const parsedOps = parseQueryOperators(queryStr);
    const cleanQuery = parsedOps.cleanQuery;
    const parsedExcluded = parsedOps.excluded;
    const allExcluded = [...new Set([...(state.excludedProviders || []), ...parsedExcluded])];

    const params = {
      query: cleanQuery || queryStr,
      mode: parsedOps.mode || mode,
      limit: parsedOps.limit || state.searchLimit,
      page: nextPage,
      safe_search: state.safeSearch,
      dark_bypass: state.darkBypass !== false,
      local_only: !!state.localOnly,
      excluded_providers: allExcluded.join(','),
      language: parsedOps.lang || '',
      domain_filter: parsedOps.site || ''
    };

    let newItemsBatchCount = 0;

    state.activeEventSource = api.queryStream(
      params,
      (evt) => {
        if (evt.type === 'engine_done') {
          if (evt.new_results && evt.new_results.length > 0) {
            const beforeLen = state.results.length;
            state.addResults(evt.new_results, evt.engine);
            const added = state.results.length - beforeLen;
            if (added > 0) {
              newItemsBatchCount += added;
              state.scrollRenderCount += added;
              if (filters) {
                filters.updateFilterCounts();
                if (filters.renderGranularProviderChips) filters.renderGranularProviderChips();
                filters.renderCurrentView();
              }
              if (copilot && copilot.update) {
                copilot.update(state.results, queryStr, mode);
              }
            }
          }
          // Dynamically update the engine chip badge count
          const chip = document.getElementById(`chip-${evt.engine}`);
          if (chip) {
            const matching = state.results.filter(r => {
              if (window.SearchFilters && window.SearchFilters.engineMatches) {
                return window.SearchFilters.engineMatches(r, evt.engine);
              }
              if (window.engineMatches) {
                return window.engineMatches(r, evt.engine);
              }
              return r.engine_id === evt.engine;
            }).length;
            const cnt = Math.max(matching, (state.engineStats[evt.engine]?.count || 0) + (evt.new_results ? evt.new_results.length : 0));
            if (state.engineStats[evt.engine]) {
              state.engineStats[evt.engine].count = cnt;
            }
            const icon = cnt > 0 ? 'fa-check' : 'fa-minus';
            chip.className = `engine-chip ${cnt > 0 ? 'done' : 'done empty'}` + (state.activeEngine === evt.engine ? ' selected-engine' : '');
            const countSpan = chip.querySelector('.chip-count');
            if (countSpan) countSpan.innerText = cnt;
          }
        }
      },
      (completeEvt) => {
        state.backendPage = nextPage;
        state.isFetchingMore = false;
        state.activeEventSource = null;
        if (btnStop) btnStop.style.display = 'none';

        if (streamStatusIcon) {
          streamStatusIcon.className = 'fas fa-circle-check';
          streamStatusIcon.style.color = 'var(--accent-emerald)';
        }
        if (streamStatusText) {
          streamStatusText.innerText = `Web fetch complete (+${newItemsBatchCount} new results from Page ${nextPage}, ${state.results.length} total in memory)`;
        }
        if (infiniteStatus) {
          if (newItemsBatchCount > 0) {
            infiniteStatus.innerHTML = `<div class="fetch-more-status success"><i class="fas fa-check-circle"></i> <span>Loaded +${newItemsBatchCount} new results (Page ${nextPage})</span></div>`;
            setTimeout(() => {
              if (infiniteStatus.innerHTML.includes('Loaded +')) infiniteStatus.innerHTML = '';
            }, 4000);
          } else {
            infiniteStatus.innerHTML = `<div class="fetch-more-status info"><i class="fas fa-info-circle"></i> <span>No further unique results found from upstream engines on Page ${nextPage}</span></div>`;
            setTimeout(() => {
              if (infiniteStatus.innerHTML.includes('No further')) infiniteStatus.innerHTML = '';
            }, 5000);
          }
        }
        if (filters) {
          filters.updateFilterCounts();
          if (filters.renderGranularProviderChips) filters.renderGranularProviderChips();
          filters.renderCurrentView();
        }
      },
      (err) => {
        state.isFetchingMore = false;
        state.activeEventSource = null;
        if (btnStop) btnStop.style.display = 'none';
        console.warn('[SearchStream] Fetch more error:', err);
        if (streamStatusIcon) {
          streamStatusIcon.className = 'fas fa-triangle-exclamation';
          streamStatusIcon.style.color = 'var(--accent-amber)';
        }
        if (streamStatusText) {
          streamStatusText.innerText = `Web fetch completed or reached engine limit for Page ${nextPage}`;
        }
        if (infiniteStatus) {
          infiniteStatus.innerHTML = '';
        }
        if (filters) filters.renderCurrentView();
      }
    );
  }

  window.SearchStream = {
    executeSearch,
    stopSearch,
    fetchMoreFromWeb
  };

  // Global window aliases
  window.executeSearch = executeSearch;
  window.stopSearch = stopSearch;
  window.fetchMoreFromWeb = fetchMoreFromWeb;
})();

