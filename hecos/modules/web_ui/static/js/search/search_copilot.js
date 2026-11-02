/**
 * search_copilot.js
 * Hecos AI Support intelligence, live SSE chat, dynamic personality avatars, 
 * interactive sidebar/presenter drag-resizers, and Presenter telemetry feed.
 */
window.SearchCopilot = (function () {
  'use strict';

  let currentPresetId = 'default';
  let presetsMap = {};
  let chatHistory = [];
  let isGenerating = false;
  let presenterEventSource = null;
  let userAvatarUrl = window.HecosUserAvatar || '';

  async function resolveUserAvatar() {
    if (window.HecosUserAvatar) {
      userAvatarUrl = window.HecosUserAvatar;
      return;
    }
    try {
      const res = await fetch('/hecos/api/users/me/avatar');
      if (res.ok && res.url && !res.url.includes('/login')) {
        userAvatarUrl = res.url;
        window.HecosUserAvatar = res.url;
        document.querySelectorAll('.copilot-chat-messages .copilot-user-avatar').forEach(el => {
          el.innerHTML = `<img src="${escapeHtml(userAvatarUrl)}" class="copilot-avatar-img" alt="User" onerror="this.outerHTML='<i class=\\'fas fa-user\\'></i>';">`;
        });
      }
    } catch (e) {
      // Keep icon fallback
    }
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function formatMarkdown(text) {
    if (!text) return '';
    // Collapsible think/reasoning block
    text = text.replace(/<think>([\s\S]*?)<\/think>/gi, (m, p1) => {
      const thinkClean = p1.trim();
      if (!thinkClean) return '';
      return `<details class="copilot-think-box"><summary><i class="fas fa-brain"></i> Reasoning</summary><div class="copilot-think-content">${escapeHtml(thinkClean)}</div></details>`;
    });
    let html = escapeHtml(text);
    // Bold **text**
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Italic *text*
    html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
    // Inline code `code`
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    // Reference numbers [1], [2] -> link pills
    html = html.replace(/\[(\d+)\]/g, '<span class="copilot-cite">[$1]</span>');
    // Bullet points
    html = html.replace(/^• (.*?)$/gm, '<li>$1</li>');
    html = html.replace(/^- (.*?)$/gm, '<li>$1</li>');
    // Line breaks
    html = html.replace(/\n\n/g, '<br><br>').replace(/\n/g, '<br>');
    return html;
  }

  // ── 1. Avatar Helpers ──────────────────────────────────────────────────────
  function getAssistantAvatarHtml(preset) {
    const p = preset || presetsMap[currentPresetId] || {
      name: 'Hecos AI',
      soul_name: 'Hecos AI',
      avatar_url: '/assets/Hecos_Logo_SQR_NBG_LogoOnly.png',
      avatar_type: 'image'
    };
    const url = escapeHtml(p.avatar_url || '/assets/Hecos_Logo_SQR_NBG_LogoOnly.png');
    const charName = escapeHtml(p.soul_name || p.name || 'Hecos AI');

    if (p.avatar_type === 'video') {
      return `<video src="${url}" autoplay loop muted playsinline class="copilot-avatar-video" title="${charName}"></video>`;
    }
    return `<img src="${url}" class="copilot-avatar-img" alt="${charName}" title="${charName}" onerror="this.src='/assets/Hecos_Logo_SQR_NBG_LogoOnly.png';">`;
  }

  function updatePersonalityUI() {
    const curPreset = presetsMap[currentPresetId];
    const charName = curPreset ? (curPreset.soul_name || curPreset.name || 'Hecos AI') : 'Hecos AI';
    const avatarHtml = getAssistantAvatarHtml(curPreset);

    // 1. Update initial greeting avatar & persona name
    const initialAvatar = document.getElementById('copilot-initial-avatar');
    if (initialAvatar) {
      initialAvatar.innerHTML = avatarHtml;
      initialAvatar.title = charName;
    }
    const initialNameEl = document.getElementById('copilot-initial-name');
    if (initialNameEl) {
      // Character name omitted from greeting per user preference
    }

    // 2. Update all assistant avatar elements currently rendered in chat
    const allAvatars = document.querySelectorAll('.copilot-chat-messages .copilot-assistant-avatar');
    allAvatars.forEach(el => {
      el.innerHTML = avatarHtml;
      el.title = charName;
    });

    // 3. Update the Card Title: "Ask <Character Name>"
    const titleTextEl = document.getElementById('copilot-chat-title-text');
    if (titleTextEl) {
      titleTextEl.textContent = `Ask ${charName}`;
    }

    // 4. Update the input placeholder (distinct from card title)
    const inputEl = document.getElementById('copilot-chat-input');
    if (inputEl) {
      inputEl.placeholder = 'Type a question or search query...';
    }
  }

  // ── 2. Presets Management ──────────────────────────────────────────────────
  async function loadPresets() {
    const select = document.getElementById('copilot-preset-select');
    if (!select) return;

    /** Populate the <select> with an array of preset objects. */
    function _populateSelect(presets) {
      presetsMap = {};
      presets.forEach(p => { presetsMap[p.id] = p; });
      const saved = localStorage.getItem('hecos_search_copilot_preset') || 'default';
      select.innerHTML = presets.map(p => `
        <option value="${escapeHtml(p.id)}" ${p.id === saved ? 'selected' : ''}>
          ${escapeHtml(p.icon || '\u{1F9E0}')} ${escapeHtml(p.name)}
        </option>
      `).join('');
      currentPresetId = select.value || (presets[0] ? presets[0].id : 'default');
      updatePersonalityUI();
    }

    /** Minimal fallback shown when the API is unreachable or returns an error. */
    const _fallbackPresets = [
      { id: 'default', name: 'Hecos AI', soul_name: 'Hecos AI', icon: '\u{1F9E0}',
        avatar_url: '/assets/Hecos_Logo_NBG.png', avatar_type: 'image', description: 'Standard Assistant' }
    ];

    try {
      const res = await fetch('/api/hsearch/copilot/presets', { credentials: 'same-origin' });
      if (!res.ok) {
        // Non-2xx (e.g. 401 not authenticated) — use fallback silently
        console.warn(`[HecosAI] Presets API HTTP ${res.status}; using fallback preset.`);
        _populateSelect(_fallbackPresets);
      } else {
        const data = await res.json();
        if (data.ok && Array.isArray(data.presets) && data.presets.length > 0) {
          _populateSelect(data.presets);
        } else {
          console.warn('[HecosAI] Presets list empty or malformed; using fallback preset.');
          _populateSelect(_fallbackPresets);
        }
      }
    } catch (e) {
      console.warn('[HecosAI] Could not load presets:', e);
      _populateSelect(_fallbackPresets);
    }
    select.addEventListener('change', () => {
      currentPresetId = select.value;
      localStorage.setItem('hecos_search_copilot_preset', currentPresetId);
      const curPreset = presetsMap[currentPresetId];
      const charName = curPreset ? (curPreset.soul_name || curPreset.name || 'Hecos AI') : 'Hecos AI';
      updatePersonalityUI();
      appendSystemNotice(`Active Preset: <strong>${escapeHtml(charName)}</strong>`);
    });
  }

  // ── 3. Chat UI Helpers ─────────────────────────────────────────────────────
  function appendMessage(role, text) {
    const container = document.getElementById('copilot-chat-messages');
    if (!container) return null;

    const msgEl = document.createElement('div');
    msgEl.className = `copilot-msg copilot-msg-${role}`;

    let avatarInner = '';
    let avatarClass = 'copilot-msg-avatar';
    let avatarTitle = '';

    if (role === 'user') {
      avatarClass += ' copilot-user-avatar';
      const usrName = window.HecosUserName || 'User';
      avatarTitle = usrName;
      const usrSrc = window.HecosUserAvatar || userAvatarUrl;
      if (usrSrc) {
        avatarInner = `<img src="${escapeHtml(usrSrc)}" class="copilot-avatar-img" alt="${escapeHtml(usrName)}" onerror="this.outerHTML='<i class=\\'fas fa-user\\'></i>';">`;
      } else {
        avatarInner = '<i class="fas fa-user"></i>';
      }
    } else {
      avatarClass += ' copilot-assistant-avatar';
      const curPreset = presetsMap[currentPresetId];
      avatarTitle = curPreset ? (curPreset.soul_name || curPreset.name || 'Hecos AI') : 'Hecos AI';
      avatarInner = getAssistantAvatarHtml(curPreset);
    }

    msgEl.innerHTML = `
      <div class="${avatarClass}" title="${escapeHtml(avatarTitle)}">${avatarInner}</div>
      <div class="copilot-msg-bubble">
        <div class="copilot-msg-text">${formatMarkdown(text)}</div>
      </div>
    `;

    container.appendChild(msgEl);
    container.scrollTop = container.scrollHeight;
    return msgEl;
  }

  function appendSystemNotice(text) {
    const container = document.getElementById('copilot-chat-messages');
    if (!container) return;
    const el = document.createElement('div');
    el.className = 'copilot-sys-notice';
    el.innerHTML = text;
    container.appendChild(el);
    container.scrollTop = container.scrollHeight;
  }

  // ── 3.5 Search Intent & Mode Parser ───────────────────────────────────────
  function detectSearchIntent(rawText) {
    if (!rawText) return null;
    const clean = rawText.trim();

    // Explicit search verbs/phrases in Italian & English
    const searchPattern = /^(?:cerca(?:\s+su|\s+nel|\s+in|\s+per|\s+un|\s+una)?|cercami|trova(?:\s+su|\s+nel|\s+in|\s+per|\s+un|\s+una)?|trovami|fai\s+una\s+ricerca(?:\s+su|\s+per)?|esegui\s+una\s+ricerca(?:\s+su|\s+per)?|search(?:\s+for)?|find(?:\s+for)?|look\s+up(?:\s+for)?|look\s+for|\/search|\/hsearch)\s+(.+)$/i;
    const m = clean.match(searchPattern);
    if (m && m[1].trim()) {
      return { query: m[1].trim(), explicit: true };
    }

    // Direct slash commands
    if (clean.startsWith('/s ') || clean.startsWith('/find ')) {
      return { query: clean.slice(clean.indexOf(' ') + 1).trim(), explicit: true };
    }

    // Implicit search: if results are empty and input is short and not a question/greeting
    const hasResults = Boolean(window.SearchState?.results && window.SearchState.results.length > 0);
    const words = clean.split(/\s+/);
    const isGreetingOrCasual = /^(ciao|buongiorno|buonasera|salve|hey|hello|hi|chi sei|come ti chiami|cosa puoi fare|help|aiuto)\b/i.test(clean);

    if (!hasResults && !isGreetingOrCasual && words.length <= 10 && !clean.endsWith('?')) {
      return { query: clean, explicit: false };
    }

    return null;
  }

  function detectSearchMode(rawText, defaultMode) {
    const lower = rawText.toLowerCase();
    if (lower.includes('dark web') || lower.includes('.onion') || lower.includes(' tor ') || lower.startsWith('tor ') || lower.includes('hidden service')) {
      return 'dark';
    }
    if (lower.includes('deep search') || lower.includes('ricerca profonda')) {
      return 'deep';
    }
    if (lower.includes('video') || lower.includes('filmati') || lower.includes('canzoni') || lower.includes('musica') || lower.includes('audio') || lower.includes('podcast') || lower.includes('immagine') || lower.includes('immagini') || lower.includes('foto')) {
      return 'media';
    }
    if (lower.includes('dork') || lower.includes('filetype:') || lower.includes('.pdf') || lower.includes('.docx') || lower.includes('documenti') || lower.includes('file hunter')) {
      return 'files';
    }
    return defaultMode || window.SearchState?.currentMode || 'clear';
  }

  // ── 4. Chat Send & SSE Stream ──────────────────────────────────────────────
  async function sendMessage(text) {
    if (!text || !text.trim() || isGenerating) return;
    const cleanText = text.trim();

    const input = document.getElementById('copilot-chat-input');
    const sendBtn = document.getElementById('copilot-chat-send');
    if (input) input.value = '';

    appendMessage('user', cleanText);
    chatHistory.push({ role: 'user', content: cleanText });

    isGenerating = true;
    if (sendBtn) {
      sendBtn.disabled = true;
      sendBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    }

    // Prepare assistant message bubble for streaming
    const assistantMsg = appendMessage('assistant', '');
    const bubbleTextEl = assistantMsg ? assistantMsg.querySelector('.copilot-msg-text') : null;
    if (bubbleTextEl) {
      bubbleTextEl.innerHTML = '<span class="copilot-typing-dots"><span>.</span><span>.</span><span>.</span></span>';
    }

    // Trigger live engine search on the main Net Search view if search intent is detected
    const searchIntent = detectSearchIntent(cleanText);
    if (searchIntent && searchIntent.query) {
      const queryToSearch = searchIntent.query;
      const targetMode = detectSearchMode(cleanText, window.SearchState?.currentMode || 'clear');

      const searchInput = document.getElementById('search-input');
      if (searchInput) {
        searchInput.value = queryToSearch;
      }

      if (targetMode !== window.SearchState?.currentMode) {
        const targetPill = document.querySelector(`.mode-pill[data-mode="${targetMode}"]`);
        if (targetPill) {
          document.querySelectorAll('.mode-pill').forEach(p => p.classList.remove('active'));
          targetPill.classList.add('active');
          if (window.SearchState) window.SearchState.currentMode = targetMode;
          if (window.SearchFilters && window.SearchFilters.renderFilterTabsForMode) {
            window.SearchFilters.renderFilterTabsForMode(targetMode, false);
          }
        }
      }

      if (window.SearchStream && typeof window.SearchStream.executeSearch === 'function') {
        window.SearchStream.executeSearch(queryToSearch, targetMode);
      }
    }

    // If this is a fresh search intent, clear old session_id so AI synthesizes the new search
    const currentSession = searchIntent ? '' : (window.SearchState?.activeSessionId || window.SearchState?.currentSessionId || '');
    let accumulated = '';

    try {
      const response = await fetch('/api/hsearch/copilot/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: cleanText,
          preset_id: currentPresetId,
          session_id: currentSession,
          stream: true
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith('data:')) continue;
          const jsonStr = trimmed.slice(5).trim();
          if (!jsonStr) continue;

          try {
            const ev = JSON.parse(jsonStr);
            if (ev.type === 'session') {
              if (window.SearchState && ev.session_id) {
                window.SearchState.activeSessionId = ev.session_id;
                window.SearchState.currentSessionId = ev.session_id;
              }
            } else if (ev.type === 'status') {
              if (bubbleTextEl && !accumulated) {
                bubbleTextEl.innerHTML = `<span style="color:var(--accent-cyan, #06b6d4); font-size:12px;"><i class="fas fa-satellite fa-spin"></i> ${escapeHtml(ev.text || 'Processing...')}</span>`;
              }
            } else if (ev.type === 'token') {
              accumulated += ev.text || '';
              if (bubbleTextEl) {
                bubbleTextEl.innerHTML = formatMarkdown(accumulated);
                const container = document.getElementById('copilot-chat-messages');
                if (container) container.scrollTop = container.scrollHeight;
              }
            } else if (ev.type === 'done') {
              if (ev.text && !accumulated) {
                accumulated = ev.text;
                if (bubbleTextEl) bubbleTextEl.innerHTML = formatMarkdown(accumulated);
              }
            } else if (ev.type === 'error') {
              if (bubbleTextEl) bubbleTextEl.innerHTML = `<span style="color:#f87171;">⚠️ ${escapeHtml(ev.error || 'Generation error')}</span>`;
            }
          } catch (pe) {
            // Non-JSON SSE line or heartbeat
          }
        }
      }

      chatHistory.push({ role: 'assistant', content: accumulated });
    } catch (err) {
      console.error('[HecosAI] Chat streaming failed:', err);
      if (bubbleTextEl) {
        bubbleTextEl.innerHTML = `<span style="color:#f87171;">⚠️ Connection error to Hecos AI Assistant: ${escapeHtml(err.message)}</span>`;
      }
    } finally {
      isGenerating = false;
      if (sendBtn) {
        sendBtn.disabled = false;
        sendBtn.innerHTML = '<i class="fas fa-paper-plane"></i>';
      }
    }
  }

  // ── 5. Sidebar Width Resizer ──────────────────────────────────────────────
  function initSidebarResizer() {
    const resizer = document.getElementById('copilot-resizer');
    const sidebar = document.getElementById('search-copilot');
    if (!resizer || !sidebar) return;

    // Restore saved width from localStorage
    const savedWidth = parseInt(localStorage.getItem('hecos_search_copilot_w'), 10);
    if (savedWidth && savedWidth >= 240 && savedWidth <= window.innerWidth * 0.8) {
      sidebar.style.width = savedWidth + 'px';
      document.documentElement.style.setProperty('--copilot-w', savedWidth + 'px');
    }

    let isDragging = false;
    let startX = 0;
    let startW = 0;

    resizer.addEventListener('mousedown', (e) => {
      isDragging = true;
      startX = e.clientX;
      startW = sidebar.getBoundingClientRect().width;
      resizer.classList.add('is-resizing');
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';

      const onMouseMove = (moveEvent) => {
        if (!isDragging) return;
        const deltaX = startX - moveEvent.clientX; // Moving left widens sidebar
        let newW = Math.round(startW + deltaX);
        const minW = 260;
        const maxW = Math.floor(window.innerWidth * 0.65);
        if (newW < minW) newW = minW;
        if (newW > maxW) newW = maxW;

        sidebar.style.width = newW + 'px';
        document.documentElement.style.setProperty('--copilot-w', newW + 'px');
      };

      const onMouseUp = () => {
        if (!isDragging) return;
        isDragging = false;
        resizer.classList.remove('is-resizing');
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
        window.removeEventListener('mousemove', onMouseMove);
        window.removeEventListener('mouseup', onMouseUp);

        const finalW = Math.round(sidebar.getBoundingClientRect().width);
        localStorage.setItem('hecos_search_copilot_w', finalW.toString());
      };

      window.addEventListener('mousemove', onMouseMove);
      window.addEventListener('mouseup', onMouseUp);
      e.preventDefault();
    });
  }

  // ── 7. Search Updates & Synthesis ──────────────────────────────────────────
  function updateOverview(results, query, mode) {
    const summaryCard = document.getElementById('copilot-summary-content');
    if (!summaryCard) return;

    if (!results || results.length === 0) {
      summaryCard.innerHTML = '<span style="color:var(--text-dim); font-size:12px;">Waiting for search results to generate intelligence summary...</span>';
      return;
    }

    const total = results.length;
    const onionCount = results.filter(r => r.network === 'tor' || (r.url && r.url.includes('.onion'))).length;
    const clearCount = total - onionCount;
    const engines = [...new Set(results.map(r => r.engine).filter(Boolean))].join(', ');

    summaryCard.innerHTML = `
      <div style="font-weight:600; margin-bottom:6px; color:var(--text-main);">
        Analysis for "${escapeHtml(query)}"
      </div>
      <div style="display:flex; flex-direction:column; gap:4px; font-size:12px; color:var(--text-muted);">
        <div>• <strong>${total}</strong> sources indexed successfully</div>
        <div>• Distribution: <strong>${clearCount}</strong> Clearnet, <strong>${onionCount}</strong> Tor (.onion)</div>
        <div>• Active engines: <span style="font-family:var(--font-mono); color:var(--accent);">${escapeHtml(engines)}</span></div>
      </div>
    `;

    // Prompt greeting in assistant chat
    const curPreset = presetsMap[currentPresetId];
    const charName = curPreset ? (curPreset.soul_name || curPreset.name || 'AI') : 'AI';
    appendSystemNotice(`🔍 Search completed for <strong>"${escapeHtml(query)}"</strong> (${total} sources). Ask ${escapeHtml(charName)} to analyze or summarize the findings!`);
  }

  // ── 8. Export Report ───────────────────────────────────────────────────────
  function generateReport(results, query) {
    if (!results || results.length === 0) {
      alert('No results available to export.');
      return;
    }

    let md = `# Deep Search Investigation Report: ${query}\n`;
    md += `*Date: ${new Date().toLocaleString()}*  \n`;
    md += `*Total indexed sources: ${results.length}*\n\n---\n\n`;

    results.forEach((r, idx) => {
      const net = r.network === 'tor' ? '[TOR/ONION]' : '[CLEARWEB]';
      md += `### ${idx + 1}. ${net} ${r.title}\n`;
      md += `- **URL**: ${r.url}\n`;
      md += `- **Engine**: ${r.engine}\n`;
      if (r.snippet) {
        md += `- **Snippet**: ${r.snippet}\n`;
      }
      md += `\n`;
    });

    const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `hecos_search_${(query || 'report').replace(/\W+/g, '_')}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }

  // ── 9. Public API & Initialization ─────────────────────────────────────────
  return {
    init() {
      loadPresets();
      resolveUserAvatar();
      initSidebarResizer();

      const input = document.getElementById('copilot-chat-input');
      const sendBtn = document.getElementById('copilot-chat-send');

      if (sendBtn) {
        sendBtn.addEventListener('click', () => {
          if (input) sendMessage(input.value);
        });
      }

      if (input) {
        input.addEventListener('keydown', (e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage(input.value);
          }
        });
      }

      // Quick prompt chips
      document.querySelectorAll('.copilot-chip').forEach(chip => {
        chip.addEventListener('click', () => {
          const prompt = chip.dataset.prompt;
          if (prompt) sendMessage(prompt);
        });
      });
    },

    update(results, query, mode) {
      updateOverview(results, query, mode);
    },

    sendMessage(text) {
      sendMessage(text);
    },

    exportReport() {
      generateReport(window.SearchState?.results || [], window.SearchState?.currentQuery || 'query');
    },

    togglePresenter() {
      const toggle = document.getElementById('hbs-presenter-toggle');
      if (toggle) toggle.click();
    }
  };
})();

window.togglePresenterPanel = function () {
  const toggle = document.getElementById('hbs-presenter-toggle');
  if (toggle) {
    toggle.click();
  } else if (window.Presenter && typeof window.Presenter.setDisplayMode === 'function') {
    const emb = document.getElementById('hbs-presenter-embedded');
    const isColl = emb ? emb.classList.contains('collapsed') : false;
    window.Presenter.setDisplayMode(isColl ? 'embedded' : 'collapsed');
  }
};

// Auto-boot on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  if (window.SearchCopilot && typeof window.SearchCopilot.init === 'function') {
    window.SearchCopilot.init();
  }
});
