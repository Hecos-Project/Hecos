/**
 * docs_engine.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Hecos Docs Logic
 * Fetches chapters from the API, parses Markdown using Marked.js, handles
 * document search, and manages client-side navigation.
 * ─────────────────────────────────────────────────────────────────────────────
 */

let currentGroup = window.docsEnv ? window.docsEnv.currentGroup : "";
let currentChapter = window.docsEnv ? window.docsEnv.currentChapter : "";
let currentLang = window.docsEnv ? window.docsEnv.currentLang : "en";
let chapters = [];

async function loadChapters() {
    try {
        const resp = await fetch(`/api/docs/list/${currentGroup}?lang=${currentLang}`);
        chapters = await resp.json();
        renderSidebar();
        if (currentChapter) {
            loadContent(currentChapter);
        } else if (chapters.length > 0) {
            loadContent(chapters[0].id);
        }
    } catch (e) {
        console.error("Error loading chapters:", e);
    }
}

function renderSidebar() {
    const container = document.getElementById('chapters-container');
    if (!container) return;
    
    container.innerHTML = '';
    
    chapters.forEach((ch, index) => {
        const a = document.createElement('a');
        a.href = `javascript:void(0)`;
        a.className = `chapter-item ${ch.id === currentChapter ? 'active' : ''}`;
        a.textContent = ch.name;
        a.onclick = () => loadContent(ch.id);
        container.appendChild(a);
    });

    // Update Group Tabs
    const userBtn = document.getElementById('btn-group-user');
    if (userBtn) userBtn.classList.toggle('active', currentGroup === 'user');
    
    const techBtn = document.getElementById('btn-group-tech');
    if (techBtn) techBtn.classList.toggle('active', currentGroup === 'tech');

    // Update Lang Links
    document.querySelectorAll('.lang-link').forEach(el => {
        el.classList.toggle('active', el.id === `lang-${currentLang}`);
    });
}

async function loadContent(chapterId) {
    if (!chapterId) return;
    currentChapter = chapterId;
    
    const overlay = document.getElementById('loading-overlay');
    if (overlay) overlay.style.display = 'flex';

    try {
        const resp = await fetch(`/api/docs/content/${currentGroup}/${chapterId}?lang=${currentLang}`);
        const data = await resp.json();
        
        const target = document.getElementById('content-target');
        if (!target) return;

        if (data.error) {
            target.innerHTML = `<h1>Error</h1><p>${data.error}</p>`;
        } else {
            target.innerHTML = marked.parse(data.content);
            
            // Highlight code using highlight.js
            target.querySelectorAll('pre code').forEach((el) => {
                if (window.hljs) hljs.highlightElement(el);
            });
            
            // Scroll to top
            const mainContainer = document.querySelector('.docs-main');
            if (mainContainer) mainContainer.scrollTop = 0;
        }
        
        updatePagination();
        renderSidebar();
        
        // Update URL without refresh
        const newUrl = `${window.location.pathname}?group=${currentGroup}&chapter=${chapterId}&lang=${currentLang}`;
        window.history.pushState({ group: currentGroup, chapter: chapterId, lang: currentLang }, '', newUrl);

    } catch (e) {
        console.error("Error loading content:", e);
    } finally {
        if (overlay) overlay.style.display = 'none';
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Search Logic
// ─────────────────────────────────────────────────────────────────────────────
let searchTimeout = null;

function handleSearch(e) {
    const query = e.target.value.trim();
    clearTimeout(searchTimeout);
    
    if (query.length < 2) {
        if (query.length === 0) closeSearch();
        return;
    }
    
    searchTimeout = setTimeout(() => {
        performSearch(query);
    }, 300);
}

async function performSearch(query) {
    const searchRes = document.getElementById("search-results");
    const queryDisplay = document.getElementById("search-query-display");
    const list = document.getElementById("results-list");
    
    if (!searchRes || !list) return;

    searchRes.style.display = "block";
    if (queryDisplay) queryDisplay.innerText = `Results for "${query}"`;
    list.innerHTML = `<div style="color: #666; padding: 20px;">Searching...</div>`;
    
    try {
        const resp = await fetch(`/api/docs/search?group=${currentGroup}&query=${encodeURIComponent(query)}&lang=${currentLang}`);
        const results = await resp.json();
        
        if (results.length === 0) {
            list.innerHTML = `<div style="color: #666; padding: 20px;">No results found for "${query}".</div>`;
            return;
        }
        
        list.innerHTML = results.map(r => `
            <div class="search-result-item" onclick="goToSearchResult('${r.id}')">
                <div class="search-result-title">${r.title}</div>
                <div class="search-result-snippet">${highlightQuery(r.snippet, query)}</div>
            </div>
        `).join('');
    } catch (e) {
        list.innerHTML = `<div style="color: #f66; padding: 20px;">Error during search.</div>`;
    }
}

function highlightQuery(text, query) {
    const regex = new RegExp(`(${query})`, 'gi');
    return text.replace(regex, '<b>$1</b>');
}

function closeSearch() {
    const searchRes = document.getElementById("search-results");
    if (searchRes) searchRes.style.display = "none";
    const srcInput = document.getElementById("docs-search");
    if (srcInput) srcInput.value = "";
}

function goToSearchResult(chapterId) {
    closeSearch();
    loadContent(chapterId);
}

// ─────────────────────────────────────────────────────────────────────────────
// UI Helpers & Navigation
// ─────────────────────────────────────────────────────────────────────────────

function updatePagination() {
    const idx = chapters.findIndex(c => c.id === currentChapter);
    const prev = chapters[idx - 1];
    const next = chapters[idx + 1];

    const prevEl = document.getElementById('pag-prev');
    if (prevEl) {
        if (prev) {
            prevEl.style.visibility = 'visible';
            const prevTitle = document.getElementById('pag-prev-title');
            if (prevTitle) prevTitle.textContent = prev.name;
            prevEl.onclick = (e) => { e.preventDefault(); loadContent(prev.id); };
        } else {
            prevEl.style.visibility = 'hidden';
        }
    }

    const nextEl = document.getElementById('pag-next');
    if (nextEl) {
        if (next) {
            nextEl.style.visibility = 'visible';
            const nextTitle = document.getElementById('pag-next-title');
            if (nextTitle) nextTitle.textContent = next.name;
            nextEl.onclick = (e) => { e.preventDefault(); loadContent(next.id); };
        } else {
            nextEl.style.visibility = 'hidden';
        }
    }
}

function switchGroup(group) {
    if (group === currentGroup) return;
    currentGroup = group;
    currentChapter = ""; // Load first chapter of new group
    loadChapters();
}

function switchLang(lang) {
    if (lang === currentLang) return;
    currentLang = lang;
    loadChapters(); // Reload titles and content
}

// ─────────────────────────────────────────────────────────────────────────────
// Bootstrap
// ─────────────────────────────────────────────────────────────────────────────

window.onpopstate = function(event) {
    if (event.state) {
        currentGroup = event.state.group || currentGroup;
        currentChapter = event.state.chapter || currentChapter;
        currentLang = event.state.lang || currentLang;
        loadChapters();
    }
};

document.addEventListener('DOMContentLoaded', loadChapters);

// Expose public API
window.switchLang = switchLang;
window.switchGroup = switchGroup;
window.handleSearch = handleSearch;
window.closeSearch = closeSearch;
window.goToSearchResult = goToSearchResult;

