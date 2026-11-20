/**
 * hecos_tooltip.js — Unified Global Dark-Glass Tooltip Engine for Hecos
 * ─────────────────────────────────────────────────────────────────────────────
 * Replaces browser-native OS `title="..."` tooltips (yellow/white boxes) across
 * Chat, Sidebar, Welcome Chips, Preset Manager, Central Hub, Control Room, and
 * HPM plugins with the official Hecos Dark-Glass tooltip defined in
 * `hecos/assets/css/core/components.css`.
 *
 * Usage:
 *   1. Automatic: any element with `title="..."` or `data-hecos-tip="..."`
 *      (opt-out via `data-no-hecos-tip="true"`).
 *   2. Declarative rich tooltip:
 *      `data-hecos-tip-title="..."` + `data-hecos-tip="..."` + optional `data-hecos-tip-badge="..."`
 *   3. Programmatic API:
 *      `window.HecosTooltip.showRich(anchorEl, { title, iconHtml, badge, badgeColor, body, metaLines })`
 *      `window.HecosTooltip.show(anchorEl, text)`
 *      `window.HecosTooltip.hide(immediate)`
 */
(function () {
    'use strict';

    if (window.HecosTooltip && window.HecosTooltip.__initialized) return;

    let _el = null;
    let _activeAnchor = null;
    let _showTimer = null;
    let _hideTimer = null;

    function _esc(str) {
        return String(str == null ? '' : str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function _hexToRgb(hex) {
        if (!hex) return null;
        const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(String(hex).trim());
        return m ? `${parseInt(m[1], 16)}, ${parseInt(m[2], 16)}, ${parseInt(m[3], 16)}` : null;
    }

    function _ensureEl() {
        if (_el && document.body && document.body.contains(_el)) return _el;
        _el = document.getElementById('hecos-global-tooltip');
        if (!_el) {
            _el = document.createElement('div');
            _el.id = 'hecos-global-tooltip';
            _el.className = 'hecos-tooltip';
            _el.setAttribute('role', 'tooltip');
            _el.setAttribute('aria-hidden', 'true');
            (document.body || document.documentElement).appendChild(_el);
        }
        return _el;
    }

    function _clearTimers() {
        if (_showTimer) { clearTimeout(_showTimer); _showTimer = null; }
        if (_hideTimer) { clearTimeout(_hideTimer); _hideTimer = null; }
    }

    function _position(anchorEl, tipEl) {
        if (!anchorEl || !tipEl || typeof anchorEl.getBoundingClientRect !== 'function') return;
        const rect = anchorEl.getBoundingClientRect();
        if (rect.width === 0 && rect.height === 0) return;

        const tipRect = tipEl.getBoundingClientRect();
        const gap = 9;
        const margin = 10;

        let pos = 'top';
        let top = rect.top - tipRect.height - gap;
        if (top < margin) {
            pos = 'bottom';
            top = rect.bottom + gap;
            if (top + tipRect.height > window.innerHeight - margin) {
                top = Math.max(margin, window.innerHeight - tipRect.height - margin);
            }
        }

        const anchorCenterX = rect.left + rect.width / 2;
        let left = anchorCenterX - tipRect.width / 2;
        left = Math.max(margin, Math.min(left, window.innerWidth - tipRect.width - margin));

        tipEl.setAttribute('data-pos', pos);
        tipEl.style.left = `${Math.round(left)}px`;
        tipEl.style.top = `${Math.round(top)}px`;

        const arrow = tipEl.querySelector('.hecos-tooltip-arrow');
        if (arrow) {
            const arrowX = Math.max(14, Math.min(anchorCenterX - left - 4, tipRect.width - 22));
            arrow.style.left = `${Math.round(arrowX)}px`;
        }
    }

    /**
     * Format a single-line tooltip string, turning trailing `[Ctrl+X]` or `(←)/(→)`
     * shortcut hints into sleek `<kbd>` chips.
     */
    function _formatInlineWithShortcut(text) {
        const clean = String(text || '').trim();
        // Match trailing [Ctrl+B], [F3], [Esc], etc.
        const bracketMatch = clean.match(/^(.*?)\s+\[([^\]]{1,24})\]$/);
        if (bracketMatch && bracketMatch[1].trim()) {
            return `<span>${_esc(bracketMatch[1].trim())}</span><kbd class="hecos-tooltip-kbd">${_esc(bracketMatch[2].trim())}</kbd>`;
        }
        // Match trailing (←), (→), (Esc), (F3)
        const parenMatch = clean.match(/^(.*?)\s+\((←|→|↑|↓|Esc|F\d{1,2}|Ctrl\+[^)]{1,18}|Alt\+[^)]{1,18})\)$/i);
        if (parenMatch && parenMatch[1].trim()) {
            return `<span>${_esc(parenMatch[1].trim())}</span><kbd class="hecos-tooltip-kbd">${_esc(parenMatch[2].trim())}</kbd>`;
        }
        return `<span>${_esc(clean)}</span>`;
    }

    /**
     * Parse raw `title` / `data-hecos-tip` text into structured rich HTML or compact pill HTML.
     */
    function _buildHtmlFromText(rawText, explicitTitle, explicitBadge) {
        const raw = String(rawText || '').trim();
        if (!raw && !explicitTitle) return null;

        // Explicit declarative rich tooltip (`data-hecos-tip-title`)
        if (explicitTitle) {
            return {
                rich: true,
                html: _buildRichInnerHtml({
                    title: explicitTitle,
                    badge: explicitBadge || '',
                    body: raw,
                }),
            };
        }

        const lines = raw.split(/\r?\n/).map(l => l.trim()).filter(Boolean);
        if (lines.length === 0) return null;

        // Multi-line tooltip (e.g., DCC Welcome Chips, Preset Manager items, rich buttons)
        if (lines.length > 1) {
            const first = lines[0];
            const rest = lines.slice(1);

            // Detect DCC chip pattern: "Label (Type): Description..."
            const dccMatch = first.match(/^([^(:]{1,48})\s*\(([^)]{1,24})\)\s*:\s*(.+)$/);
            if (dccMatch) {
                return {
                    rich: true,
                    html: _buildRichInnerHtml({
                        title: dccMatch[1].trim(),
                        badge: dccMatch[2].trim(),
                        body: dccMatch[3].trim(),
                        metaLines: rest,
                    }),
                };
            }

            // Detect "Title (id)" + metadata lines (e.g. Preset Manager items)
            const metaOnly = rest.every(l => l.includes(':'));
            return {
                rich: true,
                html: _buildRichInnerHtml({
                    title: first,
                    body: metaOnly ? '' : rest[0],
                    metaLines: metaOnly ? rest : rest.slice(1),
                }),
            };
        }

        // Single-line tooltip: check if it also follows "Label (Type): Description"
        const single = lines[0];
        const dccSingle = single.match(/^([^(:]{1,48})\s*\((App|Plugin|System App|Core|Widget|Playbook|Library|Persona)\)\s*:\s*(.+)$/i);
        if (dccSingle) {
            return {
                rich: true,
                html: _buildRichInnerHtml({
                    title: dccSingle[1].trim(),
                    badge: dccSingle[2].trim(),
                    body: dccSingle[3].trim(),
                }),
            };
        }

        return {
            rich: false,
            html: `<div class="hecos-tooltip-simple">${_formatInlineWithShortcut(single)}</div><div class="hecos-tooltip-arrow"></div>`,
        };
    }

    function _buildRichInnerHtml(opts) {
        const title = opts.title || '';
        const iconHtml = opts.iconHtml || '';
        const badge = opts.badge || '';
        const body = opts.body || '';
        const metaLines = Array.isArray(opts.metaLines) ? opts.metaLines.filter(Boolean) : [];

        let badgeStyle = '';
        if (opts.badgeColor) {
            const rgb = _hexToRgb(opts.badgeColor);
            if (rgb) {
                badgeStyle = ` style="background:rgba(${rgb},0.16);color:${opts.badgeColor};border-color:rgba(${rgb},0.32);"`;
            }
        }

        const headHtml = (title || badge)
            ? `<div class="hecos-tooltip-head">` +
              `<span class="hecos-tooltip-title">${iconHtml}<span>${_esc(title)}</span></span>` +
              (badge ? `<span class="hecos-tooltip-badge"${badgeStyle}>${_esc(badge)}</span>` : '') +
              `</div>`
            : '';

        const bodyHtml = body ? `<div class="hecos-tooltip-body">${_esc(body)}</div>` : '';
        const metaHtml = metaLines.length
            ? `<div class="hecos-tooltip-meta">${metaLines.map(l => `<div>${_esc(l)}</div>`).join('')}</div>`
            : '';

        return `${headHtml}${bodyHtml}${metaHtml}<div class="hecos-tooltip-arrow"></div>`;
    }

    function showRich(anchorEl, opts) {
        if (!anchorEl || !document.body || !document.body.contains(anchorEl) || !opts) return;
        const tipEl = _ensureEl();
        tipEl.classList.add('hecos-tooltip-rich');
        tipEl.innerHTML = _buildRichInnerHtml(opts);
        _activeAnchor = anchorEl;
        _position(anchorEl, tipEl);
        tipEl.classList.add('visible');
        tipEl.setAttribute('aria-hidden', 'false');
    }

    function show(anchorEl, rawText, explicitTitle, explicitBadge) {
        if (!anchorEl || !document.body || !document.body.contains(anchorEl)) return;
        const built = _buildHtmlFromText(rawText, explicitTitle, explicitBadge);
        if (!built) {
            hide(true);
            return;
        }
        const tipEl = _ensureEl();
        tipEl.classList.toggle('hecos-tooltip-rich', !!built.rich);
        tipEl.innerHTML = built.html;
        _activeAnchor = anchorEl;
        _position(anchorEl, tipEl);
        tipEl.classList.add('visible');
        tipEl.setAttribute('aria-hidden', 'false');
    }

    function hide(immediate = false) {
        if (_showTimer) { clearTimeout(_showTimer); _showTimer = null; }
        const doHide = () => {
            _activeAnchor = null;
            if (_el) {
                _el.classList.remove('visible');
                _el.setAttribute('aria-hidden', 'true');
            }
        };
        if (immediate) {
            if (_hideTimer) { clearTimeout(_hideTimer); _hideTimer = null; }
            doHide();
        } else {
            if (_hideTimer) clearTimeout(_hideTimer);
            _hideTimer = setTimeout(doHide, 80);
        }
    }

    function schedule(anchorEl, renderFn, coldDelay = 220) {
        if (!anchorEl || typeof renderFn !== 'function') return;
        if (anchorEl === _activeAnchor && _el && _el.classList.contains('visible')) {
            if (_hideTimer) { clearTimeout(_hideTimer); _hideTimer = null; }
            return;
        }
        _clearTimers();
        const isAlreadyVisible = !!(_el && _el.classList.contains('visible'));
        const delay = isAlreadyVisible ? 55 : coldDelay;
        _showTimer = setTimeout(() => {
            if (anchorEl && document.body && document.body.contains(anchorEl)) {
                renderFn();
            }
        }, delay);
    }

    /**
     * Find closest element with a tooltip (`title` or `data-hecos-tip`),
     * automatically absorbing `title` into `data-hecos-tip` so the OS yellow tooltip never triggers.
     */
    function _findTipTarget(startEl) {
        let el = startEl;
        while (el && el.nodeType === 1 && el !== document.body && el !== document.documentElement) {
            if (el.getAttribute('data-no-hecos-tip') === 'true') return null;
            // Central Hub module cards/tabs use their own rich provider via showRich()
            if (el.hasAttribute('data-mod-id') && el.closest && el.closest('#config-wall, #config-tabs-bar')) {
                return null;
            }
            // Model spec pills with custom CSS ::after tooltips don't have title, ignore them cleanly
            const nativeTitle = el.getAttribute('title');
            if (nativeTitle && nativeTitle.trim()) {
                el.setAttribute('data-hecos-tip', nativeTitle);
                el.removeAttribute('title');
                return el;
            }
            const stored = el.getAttribute('data-hecos-tip');
            if (stored && stored.trim()) {
                return el;
            }
            el = el.parentElement;
        }
        return null;
    }

    function _bindGlobalListeners() {
        document.addEventListener('mouseover', (e) => {
            const target = _findTipTarget(e.target);
            if (!target) {
                if (_activeAnchor && (!_activeAnchor.contains || !_activeAnchor.contains(e.target))) {
                    // Only hide if not hovering a custom rich anchor (e.g., Central Hub card)
                    if (!(_activeAnchor.hasAttribute && _activeAnchor.hasAttribute('data-mod-id'))) {
                        hide(false);
                    }
                }
                return;
            }
            const text = target.getAttribute('data-hecos-tip') || '';
            const explicitTitle = target.getAttribute('data-hecos-tip-title') || '';
            const explicitBadge = target.getAttribute('data-hecos-tip-badge') || '';
            schedule(target, () => show(target, text, explicitTitle, explicitBadge), 240);
        }, true);

        document.addEventListener('mouseout', (e) => {
            if (!_activeAnchor) return;
            if (_activeAnchor.hasAttribute && _activeAnchor.hasAttribute('data-mod-id')) return;
            if (e.relatedTarget && _activeAnchor.contains && _activeAnchor.contains(e.relatedTarget)) return;
            const leavingTarget = _findTipTarget(e.target);
            if (leavingTarget && leavingTarget === _activeAnchor) {
                hide(false);
            }
        }, true);

        document.addEventListener('mousedown', () => hide(true), true);
        document.addEventListener('scroll', () => hide(true), true);
        window.addEventListener('resize', () => hide(true));
        window.addEventListener('blur', () => hide(true));
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' || e.key === 'Enter') hide(true);
        }, true);
    }

    _bindGlobalListeners();

    window.HecosTooltip = {
        __initialized: true,
        show,
        showRich,
        hide,
        schedule,
        _buildHtmlFromText,
    };
})();
