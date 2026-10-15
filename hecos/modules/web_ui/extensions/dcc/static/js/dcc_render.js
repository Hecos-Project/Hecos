/**
 * dcc_render.js — DCC Chip Renderer v3 (Capability Showcase)
 * Part of: extensions/dcc/
 *
 * Implements 2-level hierarchical navigation:
 * L1: Categories (Hub-style)
 * L2: Capabilities (Inspirational prompts based on installed modules)
 *
 * Featured chips are shuffled client-side on every render() call,
 * and paginated (5 per page).
 */
(function () {
    'use strict';

    let _data = null;
    let _container = null;
    let _wrapper = null;
    
    let _level = 1;
    let _activeCat = null;

    // ── Navigation ─────────────────────────────────────────────────────────────

    function _navigate(newLevel, itemId = null, direction = 'forward') {
        _level = newLevel;
        
        let newView = null;
        if (newLevel === 1) {
            _activeCat = null;
            newView = _buildL1();
        } else if (newLevel === 2) {
            if (itemId) _activeCat = _data.categories.find(c => c.id === itemId);
            newView = _buildL2();
        }

        if (!newView) return;

        const oldView = _wrapper.querySelector('.dcc-view:not(.dcc-exiting)');
        if (oldView) {
            oldView.classList.add('dcc-exiting');
            oldView.classList.add(direction === 'forward' ? 'dcc-slide-out-left' : 'dcc-slide-out-right');
            setTimeout(() => { if (oldView && oldView.parentNode) oldView.remove(); }, 200);
        }

        newView.classList.add('dcc-view');
        newView.classList.add(direction === 'forward' ? 'dcc-slide-in-right' : 'dcc-slide-in-left');
        _wrapper.appendChild(newView);

        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                newView.classList.remove('dcc-slide-in-right');
                newView.classList.remove('dcc-slide-in-left');
            });
        });
    }

    // ── Action Execution ───────────────────────────────────────────────────────

    function _executeAction(action) {
        if (!action) return;
        if (window.HecosWelcome) window.HecosWelcome.hide();

        const input = window.userInput || document.getElementById('user-input');
        if (!input) return;

        input.value = action;
        if (window.autoResize) window.autoResize(input);
        if (window.sendMessage) window.sendMessage();
    }

    // ── Shuffle utility (Fisher-Yates) ─────────────────────────────────────────

    function _shuffle(arr) {
        const a = arr.slice(); // copy
        for (let i = a.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [a[i], a[j]] = [a[j], a[i]];
        }
        return a;
    }

    // ── Level Builders ─────────────────────────────────────────────────────────

    function _buildL1() {
        const view = document.createElement('div');
        view.className = 'dcc-l1-view'; 

        // --- FEATURED CAPABILITIES WITH PAGINATED CAROUSEL ---
        if (_data.featured && _data.featured.length > 0) {
            // Separate new chips (keep in order) from the rest (shuffle for variety)
            const newChips = _data.featured.filter(m => m.is_new);
            const otherChips = _shuffle(_data.featured.filter(m => !m.is_new));
            const ordered = [...newChips, ...otherChips];

            const PAGE_SIZE = 5;
            const totalPages = Math.ceil(ordered.length / PAGE_SIZE);
            let currentPage = 0;

            // Build the carousel container
            const carousel = document.createElement('div');
            carousel.className = 'dcc-featured-carousel';

            // Left arrow
            const arrowLeft = document.createElement('button');
            arrowLeft.className = 'dcc-carousel-arrow dcc-arrow-left';
            arrowLeft.innerHTML = '<i class="fas fa-chevron-left"></i>';
            arrowLeft.title = 'Previous';
            carousel.appendChild(arrowLeft);

            // Viewport (shows exactly 5 chips)
            const viewport = document.createElement('div');
            viewport.className = 'dcc-featured-viewport';
            carousel.appendChild(viewport);

            // Right arrow
            const arrowRight = document.createElement('button');
            arrowRight.className = 'dcc-carousel-arrow dcc-arrow-right';
            arrowRight.innerHTML = '<i class="fas fa-chevron-right"></i>';
            arrowRight.title = 'Next';
            carousel.appendChild(arrowRight);

            view.appendChild(carousel);

            // Build a single chip element
            function _buildChip(mod) {
                const el = document.createElement('div');
                el.className = 'chip dcc-featured-chip';
                
                const isNew = mod.is_new && !sessionStorage.getItem('seen_new_' + mod.id);
                if (isNew) el.classList.add('dcc-has-new');

                const shortText = mod.short || mod.label;
                const modType = mod.type || 'App';
                const promptText = mod.prompt || `Launch ${mod.label}`;
                
                let tooltip = `${mod.label} (${modType}): ${promptText}`;
                if (mod.caps) {
                    if (mod.caps.llm > 0) tooltip += `\nLLM Tools: ${mod.caps.llm}`;
                    if (mod.caps.cmd > 0) tooltip += `\nSlash Commands: ${mod.caps.cmd}`;
                }
                
                el.title = tooltip;
                
                const newBadgeHtml = isNew ? `<span class="dcc-new-badge">NEW</span>` : '';
                el.innerHTML = `<i class="${mod.icon}"></i> <span>${shortText}</span> ${newBadgeHtml}`;
                
                el.addEventListener('click', (e) => {
                    e.stopPropagation();
                    if (isNew) {
                        sessionStorage.setItem('seen_new_' + mod.id, 'true');
                        const b = el.querySelector('.dcc-new-badge');
                        if (b) b.remove();
                        el.classList.remove('dcc-has-new');
                    }
                    if (mod.prompt && window.HecosWelcome) {
                        window.HecosWelcome.startPrompt(mod.prompt);
                    } else if (mod.action) {
                        _executeAction(mod.action);
                    } else if (mod.prompt) {
                        _executeAction(mod.prompt);
                    }
                });
                return el;
            }

            // Render a specific page into the viewport
            function renderPage(pageIndex, direction) {
                const start = pageIndex * PAGE_SIZE;
                const pageItems = ordered.slice(start, start + PAGE_SIZE);

                const newTrack = document.createElement('div');
                newTrack.className = 'dcc-featured-track';
                pageItems.forEach(mod => newTrack.appendChild(_buildChip(mod)));

                // Animate transition
                const oldTrack = viewport.querySelector('.dcc-featured-track');
                if (oldTrack && direction) {
                    const slideOut = direction === 'next' ? 'dcc-page-out-left' : 'dcc-page-out-right';
                    const slideIn  = direction === 'next' ? 'dcc-page-in-right' : 'dcc-page-in-left';
                    oldTrack.classList.add(slideOut);
                    newTrack.classList.add(slideIn);
                    viewport.appendChild(newTrack);
                    requestAnimationFrame(() => {
                        requestAnimationFrame(() => {
                            newTrack.classList.remove(slideIn);
                        });
                    });
                    setTimeout(() => { if (oldTrack.parentNode) oldTrack.remove(); }, 250);
                } else {
                    viewport.innerHTML = '';
                    viewport.appendChild(newTrack);
                }

                updateArrows();
            }

            function updateArrows() {
                arrowLeft.classList.toggle('dcc-arrow-disabled', currentPage === 0);
                arrowRight.classList.toggle('dcc-arrow-disabled', currentPage >= totalPages - 1);
            }

            arrowLeft.addEventListener('click', (e) => {
                e.stopPropagation();
                if (currentPage > 0) {
                    currentPage--;
                    renderPage(currentPage, 'prev');
                }
            });

            arrowRight.addEventListener('click', (e) => {
                e.stopPropagation();
                if (currentPage < totalPages - 1) {
                    currentPage++;
                    renderPage(currentPage, 'next');
                }
            });

            // Initial render
            renderPage(0, null);
        }
        
        return view;
    }

    function _buildL2() {
        const view = document.createElement('div');
        view.className = 'quick-chips dcc-l2-view';

        // Back button + Category Header combined
        const header = document.createElement('div');
        header.className = 'dcc-back-btn';
        header.innerHTML = `<i class="fas fa-chevron-left"></i> <span><i class="${_activeCat.icon}" style="opacity:0.6; margin-left:4px;"></i> ${_activeCat.label}</span>`;
        header.addEventListener('click', (e) => {
            e.stopPropagation();
            _navigate(1, null, 'backward');
        });
        view.appendChild(header);
        
        // Capability Chips (Modules)
        _activeCat.modules.forEach(mod => {
            const el = document.createElement('div');
            el.className = 'chip dcc-capability-chip';
            
            const textContent = mod.prompt || `Launch ${mod.label}`;
            
            el.innerHTML = `
                <div class="dcc-cap-badge"><i class="${mod.icon}"></i> ${mod.label}</div>
                <div class="dcc-cap-text">${textContent}</div>
            `;
            
            el.addEventListener('click', (e) => {
                e.stopPropagation();
                if (mod.prompt && window.HecosWelcome) {
                    window.HecosWelcome.startPrompt(mod.prompt);
                } else if (mod.action) {
                    _executeAction(mod.action);
                } else if (mod.prompt) {
                    _executeAction(mod.prompt);
                }
            });
            
            view.appendChild(el);
        });

        return view;
    }

    // ── Main Render Entry ──────────────────────────────────────────────────────

    function render(container, data) {
        if (!data || data.length === 0) {
            if (window.WelcomeChips) window.WelcomeChips.renderStatic(container);
            return;
        }

        _data = data;
        _container = container;
        
        // Remove old wrapper if re-rendering
        const old = container.querySelector('.dcc-nav-container');
        if (old) old.remove();

        _wrapper = document.createElement('div');
        _wrapper.className = 'dcc-nav-container';
        
        _container.appendChild(_wrapper);
        _navigate(1, null, 'forward');
        
        return _wrapper;
    }

    window.DccRender = { render };
})();
