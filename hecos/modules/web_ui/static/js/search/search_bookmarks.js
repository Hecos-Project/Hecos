/**
 * search_bookmarks.js
 * Dedicated manager for Hecos Deep Search saved links & bookmarks.
 * Handles instant toggling (star icon), local caching, and the Saved Links drawer/modal.
 */
window.BookmarksManager = (function() {
  const bookmarkedUrls = new Set();
  let currentFilter = 'all';

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function getDomain(url) {
    try {
      return new URL(url).hostname;
    } catch {
      return url;
    }
  }

  async function init() {
    try {
      const res = await fetch('/api/hsearch/bookmarks/urls').then(r => r.json());
      if (res && res.ok && Array.isArray(res.urls)) {
        bookmarkedUrls.clear();
        res.urls.forEach(u => bookmarkedUrls.add(u));
        updateCountBadge(res.total || bookmarkedUrls.size);
        refreshResultStarButtons();
      }
    } catch (e) {
      console.warn('[Bookmarks] Init error:', e);
    }
  }

  function updateCountBadge(count) {
    const badges = document.querySelectorAll('.badge-bookmarks-count');
    badges.forEach(b => {
      b.textContent = count;
      b.style.display = count > 0 ? 'inline-flex' : 'none';
    });
  }

  function isBookmarked(url) {
    return bookmarkedUrls.has(url);
  }

  function refreshResultStarButtons() {
    document.querySelectorAll('.btn-bookmark-action').forEach(btn => {
      const url = btn.dataset.url;
      if (!url) return;
      const active = bookmarkedUrls.has(url);
      btn.classList.toggle('active', active);
      const icon = btn.querySelector('i');
      if (icon) {
        icon.className = active ? 'fas fa-star' : 'far fa-star';
        icon.style.color = active ? '#f59e0b' : '';
      }
      btn.title = active ? 'Remove from Saved Links' : 'Save to Bookmarks';
    });
  }

  async function toggle(url, title, snippet, engine, isTor, btnEl) {
    if (!url) return;
    const wasBookmarked = bookmarkedUrls.has(url);

    // Optimistic UI update
    if (wasBookmarked) {
      bookmarkedUrls.delete(url);
    } else {
      bookmarkedUrls.add(url);
    }
    updateCountBadge(bookmarkedUrls.size);
    refreshResultStarButtons();

    try {
      const res = await fetch('/api/hsearch/bookmarks/toggle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: url,
          title: title || url,
          snippet: snippet || '',
          engine: engine || 'web',
          network: isTor ? 'tor' : 'clear',
          category: 'web'
        })
      }).then(r => r.json());

      if (res && res.ok) {
        if (res.bookmarked) {
          bookmarkedUrls.add(url);
        } else {
          bookmarkedUrls.delete(url);
        }
        updateCountBadge(res.total);
        refreshResultStarButtons();

        // If bookmarks modal is currently open, refresh list
        const modal = document.getElementById('bookmarks-modal');
        if (modal && modal.classList.contains('open')) {
          loadList(currentFilter);
        }
      }
    } catch (e) {
      console.warn('[Bookmarks] Toggle error:', e);
      // Revert on error
      if (wasBookmarked) bookmarkedUrls.add(url);
      else bookmarkedUrls.delete(url);
      updateCountBadge(bookmarkedUrls.size);
      refreshResultStarButtons();
    }
  }

  async function removeBookmark(url) {
    if (!confirm('Remove this saved link?')) return;
    try {
      const res = await fetch('/api/hsearch/bookmarks', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url })
      }).then(r => r.json());

      if (res && res.ok) {
        bookmarkedUrls.delete(url);
        updateCountBadge(res.total);
        refreshResultStarButtons();
        loadList(currentFilter);
      }
    } catch (e) {
      console.warn('[Bookmarks] Remove error:', e);
    }
  }

  function openDrawer() {
    const modal = document.getElementById('bookmarks-modal');
    if (modal) {
      modal.classList.add('open');
      loadList('all');
    }
  }

  function closeDrawer() {
    const modal = document.getElementById('bookmarks-modal');
    if (modal) modal.classList.remove('open');
  }

  async function loadList(filter = 'all') {
    currentFilter = filter;
    const listEl = document.getElementById('bookmarks-list-container');
    if (!listEl) return;

    listEl.innerHTML = '<div style="text-align:center; padding:24px; color:var(--muted);"><i class="fas fa-spinner fa-spin"></i> Loading saved links...</div>';

    // Update filter tabs
    document.querySelectorAll('.bookmark-filter-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.filter === filter);
    });

    const netParam = filter === 'tor' ? '&network=tor' : (filter === 'clear' ? '&network=clear' : '');
    const searchVal = document.getElementById('bookmarks-search-input')?.value.trim() || '';
    const qParam = searchVal ? `&q=${encodeURIComponent(searchVal)}` : '';

    try {
      const res = await fetch(`/api/hsearch/bookmarks?limit=200${netParam}${qParam}`).then(r => r.json());
      if (!res.ok || !res.bookmarks || res.bookmarks.length === 0) {
        listEl.innerHTML = `
          <div style="text-align:center; padding:36px 20px; color:var(--muted);">
            <div style="font-size:32px; margin-bottom:10px; opacity:0.4;">⭐</div>
            <strong style="font-size:14px; color:var(--text); display:block; margin-bottom:6px;">No saved links found</strong>
            <p style="font-size:12px; max-width:320px; margin:0 auto;">Click the star icon (★) on any search result to save it here for quick offline access.</p>
          </div>
        `;
        return;
      }

      listEl.innerHTML = res.bookmarks.map(b => {
        const isTor = b.network === 'tor' || b.url.includes('.onion');
        const netBadge = isTor
          ? '<span class="badge-network tor" style="font-size:10px;"><i class="fas fa-user-secret"></i> Onion</span>'
          : '<span class="badge-network clearnet" style="font-size:10px;"><i class="fas fa-globe"></i> Web</span>';
        const domain = getDomain(b.url);
        const safeTitle = escapeHtml(b.title || b.url);
        const safeSnippet = escapeHtml(b.snippet || '');
        const safeUrl = escapeHtml(b.url);
        const safeEngine = escapeHtml(b.engine || 'web');
        const dateStr = b.created_at ? new Date(b.created_at).toLocaleDateString() : '';

        return `
          <div class="bookmark-card ${isTor ? 'onion-card' : ''}" data-url="${safeUrl}">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:6px;">
              <div style="display:flex; align-items:center; gap:8px;">
                ${netBadge}
                <span style="font-size:11px; color:var(--muted); font-family:monospace;">${domain}</span>
              </div>
              <div style="display:flex; align-items:center; gap:6px;">
                <span style="font-size:10px; color:var(--muted);">${dateStr}</span>
                <button type="button" class="btn btn-sm btn-danger" style="border-radius:6px; padding:3px 7px; font-size:11px;" onclick="window.BookmarksManager.remove('${safeUrl}')" title="Remove bookmark">
                  <i class="fas fa-trash"></i>
                </button>
              </div>
            </div>
            <a href="${safeUrl}" target="_blank" rel="noopener noreferrer" style="font-size:13.5px; font-weight:600; color:var(--text); text-decoration:none; display:block; margin-bottom:4px; line-height:1.4;">
              ${safeTitle}
            </a>
            ${safeSnippet ? `<p style="font-size:12px; color:var(--muted); margin-bottom:8px; line-height:1.4; max-height:48px; overflow:hidden; text-overflow:ellipsis;">${safeSnippet}</p>` : ''}
            <div style="display:flex; gap:6px; align-items:center; flex-wrap:wrap;">
              <button class="btn-result-action primary" style="font-size:10.5px; padding:3px 8px;" onclick="SearchResults.readPage('${safeUrl}')">
                <i class="fas fa-file-alt"></i> Read AI
              </button>
              <button class="btn-result-action" style="font-size:10.5px; padding:3px 8px;" onclick="SearchResults.copyLink('${safeUrl}')">
                <i class="fas fa-copy"></i> Copy Link
              </button>
              <button class="btn-result-action" style="font-size:10.5px; padding:3px 8px;" onclick="SearchResults.sendToChat('${safeTitle}', '${safeUrl}')">
                <i class="fas fa-comment-dots"></i> Chat
              </button>
            </div>
          </div>
        `;
      }).join('');
    } catch (e) {
      listEl.innerHTML = `<div style="color:var(--accent-rose); padding:20px;">Error loading bookmarks: ${e.message}</div>`;
    }
  }

  function exportBookmarks() {
    fetch('/api/hsearch/bookmarks?limit=500')
      .then(r => r.json())
      .then(d => {
        if (!d.ok || !d.bookmarks) return alert('No bookmarks to export');
        const blob = new Blob([JSON.stringify(d.bookmarks, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `hecos_saved_links_${new Date().toISOString().slice(0, 10)}.json`;
        a.click();
        URL.revokeObjectURL(url);
      })
      .catch(e => alert('Export error: ' + e.message));
  }

  return {
    init: init,
    isBookmarked: isBookmarked,
    toggle: toggle,
    remove: removeBookmark,
    open: openDrawer,
    close: closeDrawer,
    loadList: loadList,
    exportBookmarks: exportBookmarks,
    refreshResultStarButtons: refreshResultStarButtons
  };
})();

// Auto initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
  window.BookmarksManager.init();
});
