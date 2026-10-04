/**
 * MODULE: hecos_gallery.js
 * PURPOSE: Reusable modal gallery for images, video, and audio.
 * Provides filmstrip, prev/next, zoom, download, folder and custom actions.
 *
 * Shared by:
 *   - Chat (AI images [[IMG:...]], Soul media [[SOUL_MEDIA:...]], avatar click)
 *   - Config panel → Soul Media Library
 *
 * The script is idempotent: it can be loaded multiple times (e.g. by the
 * lazy-loaded config panels) without redeclaring anything.
 */
(function () {
    if (window.HecosGallery && window.HecosGallery.__hg_version >= 2) return;

    const ZOOM_MIN = 1;
    const ZOOM_MAX = 5;

    class HecosGalleryManager {
        constructor() {
            this.__hg_version = 2;
            this.items = [];
            this.currentIndex = 0;
            this.modal = null;
            this.zoom = 1;
            this.pan = { x: 0, y: 0 };
            this.config = { onOpenFolder: null, extraActions: null, title: '' };
        }

        // ── DOM creation (lazy, on first open) ─────────────────────────────
        ensureModal() {
            if (this.modal && document.body.contains(this.modal)) return;
            const existing = document.getElementById('hg-gallery-modal');
            if (existing) existing.remove();

            if (!document.getElementById('hg-gallery-style')) {
                const style = document.createElement('style');
                style.id = 'hg-gallery-style';
                style.textContent = `
                #hg-gallery-modal {
                    display:none; position:fixed; inset:0; z-index:99999;
                    background:rgba(6,7,12,0.94); backdrop-filter:blur(8px);
                    flex-direction:column; align-items:center; justify-content:center;
                    font-family:inherit;
                }
                #hg-gallery-modal.open { display:flex; animation:hg-fadein .2s ease; }
                @keyframes hg-fadein { from{opacity:0} to{opacity:1} }

                #hg-gallery-top {
                    position:absolute; top:0; left:0; right:0; height:56px;
                    display:flex; align-items:center; justify-content:center; pointer-events:none;
                }
                #hg-gallery-title {
                    position:absolute; left:20px; color:rgba(255,255,255,.85);
                    font-size:13px; font-weight:600; letter-spacing:.3px;
                    display:flex; align-items:center; gap:8px;
                }
                #hg-gallery-counter {
                    color:rgba(255,255,255,.75); font-size:12px; font-weight:500;
                    background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.12);
                    padding:4px 12px; border-radius:20px;
                }
                #hg-gallery-close {
                    position:absolute; top:12px; right:18px; pointer-events:auto;
                    background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.15);
                    color:#fff; font-size:16px; width:36px; height:36px; border-radius:10px;
                    cursor:pointer; transition:background .2s, transform .15s;
                }
                #hg-gallery-close:hover { background:rgba(255,80,80,.35); transform:scale(1.05); }

                #hg-gallery-main {
                    position:relative; display:flex; align-items:center; justify-content:center;
                    width:100%; flex:1; min-height:0; overflow:hidden; margin-top:56px;
                }
                #hg-gallery-stage {
                    display:flex; align-items:center; justify-content:center;
                    transition:transform .18s ease; will-change:transform;
                }
                #hg-gallery-stage.dragging { transition:none; }
                #hg-gallery-img {
                    max-width:88vw; max-height:70vh; border-radius:10px;
                    object-fit:contain; box-shadow:0 12px 60px rgba(0,0,0,.7);
                    transition:opacity .15s ease; user-select:none; -webkit-user-drag:none;
                    cursor:zoom-in;
                }
                #hg-gallery-modal.zoomed #hg-gallery-img { cursor:grab; }
                #hg-gallery-modal.zoomed #hg-gallery-stage.dragging #hg-gallery-img { cursor:grabbing; }
                #hg-gallery-vid {
                    max-width:88vw; max-height:70vh; border-radius:10px;
                    box-shadow:0 12px 60px rgba(0,0,0,.7); outline:none; background:#000;
                }
                #hg-gallery-audio-wrapper {
                    background:linear-gradient(145deg, rgba(108,140,255,.12), rgba(255,255,255,.03));
                    border:1px solid rgba(255,255,255,.1); padding:36px 40px; border-radius:16px;
                    display:flex; flex-direction:column; align-items:center; min-width:320px;
                }
                #hg-gallery-audio-icon { font-size:52px; color:var(--accent, #6c8cff); margin-bottom:22px; }

                .hg-nav {
                    position:absolute; top:50%; transform:translateY(-50%); z-index:2;
                    background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.15);
                    color:#fff; font-size:26px; width:46px; height:64px; border-radius:12px;
                    cursor:pointer; transition:background .2s; backdrop-filter:blur(4px); user-select:none;
                }
                .hg-nav:hover { background:rgba(255,255,255,.2); }
                #hg-gallery-prev { left:18px; }
                #hg-gallery-next { right:18px; }

                #hg-gallery-name {
                    color:rgba(255,255,255,.6); font-size:12px; margin-top:12px;
                    max-width:80vw; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;
                }
                #hg-gallery-actions {
                    display:flex; gap:8px; margin:10px 0 8px; flex-wrap:wrap; justify-content:center;
                }
                .hg-act-btn {
                    background:rgba(255,255,255,.1); backdrop-filter:blur(6px);
                    border:1px solid rgba(255,255,255,.18); color:#fff;
                    padding:6px 14px; border-radius:8px; cursor:pointer;
                    font-size:12px; font-family:inherit; white-space:nowrap;
                    transition:background .15s, transform .1s;
                }
                .hg-act-btn:hover { background:rgba(255,255,255,.25); transform:translateY(-1px); }
                .hg-act-btn.active { background:var(--accent, #6c8cff); border-color:transparent; }
                .hg-act-btn[hidden] { display:none; }

                #hg-gallery-filmstrip {
                    display:flex; gap:8px; padding:8px 16px 16px; overflow-x:auto;
                    max-width:92vw; scrollbar-width:thin;
                }
                #hg-gallery-filmstrip[hidden] { display:none; }
                .hg-strip-thumb {
                    width:60px; height:60px; border-radius:8px; object-fit:cover;
                    cursor:pointer; opacity:.45; border:2px solid transparent;
                    transition:opacity .15s, border-color .15s, transform .15s; flex-shrink:0;
                    background:rgba(255,255,255,.06); display:flex; align-items:center; justify-content:center;
                    font-size:20px; color:rgba(255,255,255,.6); overflow:hidden; position:relative;
                }
                .hg-strip-thumb video { width:100%; height:100%; object-fit:cover; pointer-events:none; }
                .hg-strip-thumb .hg-strip-badge {
                    position:absolute; inset:0; display:flex; align-items:center; justify-content:center;
                    font-size:16px; color:#fff; text-shadow:0 1px 4px #000;
                }
                .hg-strip-thumb.active { opacity:1; border-color:var(--accent, #fff); transform:translateY(-2px); }
                .hg-strip-thumb:hover { opacity:.85; }
                `;
                document.head.appendChild(style);
            }

            this.modal = document.createElement('div');
            this.modal.id = 'hg-gallery-modal';
            this.modal.innerHTML = `
                <div id="hg-gallery-top">
                    <div id="hg-gallery-title"></div>
                    <div id="hg-gallery-counter"></div>
                    <button id="hg-gallery-close" title="Close (Esc)">✕</button>
                </div>
                <div id="hg-gallery-main">
                    <button class="hg-nav" id="hg-gallery-prev" title="Previous (←)">‹</button>
                    <div id="hg-gallery-stage">
                        <img id="hg-gallery-img" src="" alt="" style="display:none;" draggable="false">
                        <video id="hg-gallery-vid" controls playsinline style="display:none;"></video>
                        <div id="hg-gallery-audio-wrapper" style="display:none;">
                            <div id="hg-gallery-audio-icon"><i class="fas fa-music"></i></div>
                            <audio id="hg-gallery-audio" controls></audio>
                        </div>
                    </div>
                    <button class="hg-nav" id="hg-gallery-next" title="Next (→)">›</button>
                </div>
                <div id="hg-gallery-name"></div>
                <div id="hg-gallery-actions">
                    <button class="hg-act-btn" id="hg-act-download">⬇ Download</button>
                    <button class="hg-act-btn" id="hg-act-zoom">🔍 Zoom</button>
                    <button class="hg-act-btn" id="hg-act-folder">📁 Folder</button>
                    <span id="hg-gallery-extra-actions" style="display:contents;"></span>
                </div>
                <div id="hg-gallery-filmstrip"></div>
            `;
            document.body.appendChild(this.modal);
            this._bindEvents();
        }

        _bindEvents() {
            const $ = id => document.getElementById(id);
            $('hg-gallery-close').onclick = () => this.close();
            $('hg-gallery-prev').onclick = (e) => { e.stopPropagation(); this.show(this.currentIndex - 1); };
            $('hg-gallery-next').onclick = (e) => { e.stopPropagation(); this.show(this.currentIndex + 1); };

            // Click on empty backdrop closes
            this.modal.addEventListener('click', e => {
                if (e.target === this.modal || e.target.id === 'hg-gallery-main') this.close();
            });

            $('hg-act-download').onclick = () => {
                const item = this.items[this.currentIndex];
                if (!item) return;
                const a = document.createElement('a');
                a.href = item.url;
                a.download = item.name || 'media';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            };

            $('hg-act-zoom').onclick = () => this.setZoom(this.zoom > 1 ? 1 : 2);

            $('hg-act-folder').onclick = () => {
                if (typeof this.config.onOpenFolder === 'function') {
                    this.config.onOpenFolder(this.items[this.currentIndex], this.currentIndex);
                } else {
                    fetch('/api/open_media_folder', { method: 'POST' }).catch(() => {});
                }
            };

            // ── Zoom & pan on the image ──
            const img = $('hg-gallery-img');
            const stage = $('hg-gallery-stage');
            img.addEventListener('click', (e) => {
                e.stopPropagation();
                if (this._dragMoved) return;
                this.setZoom(this.zoom > 1 ? 1 : 2);
            });
            $('hg-gallery-main').addEventListener('wheel', (e) => {
                if (!this.modal.classList.contains('open')) return;
                if (img.style.display === 'none') return;
                e.preventDefault();
                const step = e.deltaY < 0 ? 0.25 : -0.25;
                this.setZoom(this.zoom + step);
            }, { passive: false });

            let dragStart = null;
            img.addEventListener('mousedown', (e) => {
                if (this.zoom <= 1) return;
                e.preventDefault();
                this._dragMoved = false;
                dragStart = { x: e.clientX - this.pan.x, y: e.clientY - this.pan.y };
                stage.classList.add('dragging');
            });
            window.addEventListener('mousemove', (e) => {
                if (!dragStart) return;
                this._dragMoved = true;
                this.pan.x = e.clientX - dragStart.x;
                this.pan.y = e.clientY - dragStart.y;
                this._applyTransform();
            });
            window.addEventListener('mouseup', () => {
                if (!dragStart) return;
                dragStart = null;
                stage.classList.remove('dragging');
                setTimeout(() => { this._dragMoved = false; }, 0);
            });

            document.addEventListener('keydown', e => {
                if (!this.modal || !this.modal.classList.contains('open')) return;
                if (e.key === 'ArrowLeft')  { e.preventDefault(); this.show(this.currentIndex - 1); }
                if (e.key === 'ArrowRight') { e.preventDefault(); this.show(this.currentIndex + 1); }
                if (e.key === 'Escape')     { e.preventDefault(); e.stopPropagation(); this.close(); }
                if (e.key === '+' || e.key === '=') this.setZoom(this.zoom + 0.5);
                if (e.key === '-') this.setZoom(this.zoom - 0.5);
            }, true);
        }

        setZoom(z) {
            this.zoom = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, z));
            if (this.zoom === 1) this.pan = { x: 0, y: 0 };
            this.modal.classList.toggle('zoomed', this.zoom > 1);
            const zb = document.getElementById('hg-act-zoom');
            if (zb) {
                zb.classList.toggle('active', this.zoom > 1);
                zb.textContent = this.zoom > 1 ? `🔍 ${Math.round(this.zoom * 100)}%` : '🔍 Zoom';
            }
            this._applyTransform();
        }

        _applyTransform() {
            const stage = document.getElementById('hg-gallery-stage');
            if (stage) stage.style.transform = `translate(${this.pan.x}px, ${this.pan.y}px) scale(${this.zoom})`;
        }

        pauseMedia() {
            const vid = document.getElementById('hg-gallery-vid');
            const aud = document.getElementById('hg-gallery-audio');
            if (vid) vid.pause();
            if (aud) aud.pause();
        }

        close() {
            if (!this.modal) return;
            this.modal.classList.remove('open');
            this.pauseMedia();
            this.setZoom(1);
        }

        guessType(url) {
            const ext = (url || '').split('?')[0].split('#')[0].split('.').pop().toLowerCase();
            if (['mp4', 'webm', 'mov', 'avi', 'm4v', 'ogv'].includes(ext)) return 'video';
            if (['mp3', 'wav', 'ogg', 'm4a', 'flac', 'aac'].includes(ext)) return 'audio';
            return 'image';
        }

        show(index) {
            if (!this.items.length) return;
            this.currentIndex = (index + this.items.length) % this.items.length;
            const item = this.items[this.currentIndex];
            const $ = id => document.getElementById(id);

            const img = $('hg-gallery-img');
            const vid = $('hg-gallery-vid');
            const audWrap = $('hg-gallery-audio-wrapper');
            const aud = $('hg-gallery-audio');

            this.pauseMedia();
            this.setZoom(1);
            img.style.display = 'none';
            vid.style.display = 'none';
            audWrap.style.display = 'none';

            const type = item.type || this.guessType(item.url);
            $('hg-act-zoom').hidden = (type !== 'image');

            if (type === 'video') {
                vid.style.display = 'block';
                vid.src = item.url;
                vid.loop = true;
                vid.play().catch(() => {});
            } else if (type === 'audio') {
                audWrap.style.display = 'flex';
                aud.src = item.url;
                aud.play().catch(() => {});
            } else {
                img.style.display = 'block';
                img.style.opacity = '0';
                img.onload = () => { img.style.opacity = '1'; };
                img.src = item.url;
            }

            $('hg-gallery-name').textContent = item.name || '';
            $('hg-gallery-counter').textContent = `${this.currentIndex + 1} / ${this.items.length}`;

            document.querySelectorAll('#hg-gallery-filmstrip .hg-strip-thumb').forEach((t, i) => {
                t.classList.toggle('active', i === this.currentIndex);
                if (i === this.currentIndex) t.scrollIntoView({ behavior: 'smooth', inline: 'nearest', block: 'nearest' });
            });

            const extra = $('hg-gallery-extra-actions');
            extra.innerHTML = '';
            if (typeof this.config.extraActions === 'function') {
                const btns = this.config.extraActions(item, this.currentIndex);
                (Array.isArray(btns) ? btns : (btns ? [btns] : [])).forEach(b => {
                    if (b && !b.classList.contains('hg-act-btn')) b.classList.add('hg-act-btn');
                    if (b) extra.appendChild(b);
                });
            }
        }

        /**
         * Helper to build an action button for `extraActions`.
         */
        button(label, onClick, title) {
            const b = document.createElement('button');
            b.className = 'hg-act-btn';
            b.innerHTML = label;
            if (title) b.title = title;
            b.onclick = (e) => { e.stopPropagation(); onClick && onClick(e); };
            return b;
        }

        /**
         * items:    array of {name, url, type?}
         * startIdx: int
         * options:  { onOpenFolder(item, idx), extraActions(item, idx) → btn|btn[], title, hideFolder }
         */
        open(items, startIdx = 0, options = {}) {
            if (!Array.isArray(items) || !items.length) return;
            this.ensureModal();
            this.items = items;
            this.config = Object.assign({ onOpenFolder: null, extraActions: null, title: '', hideFolder: false }, options);

            const $ = id => document.getElementById(id);
            $('hg-gallery-title').innerHTML = this.config.title || '';
            $('hg-act-folder').hidden = !!this.config.hideFolder;

            const multi = items.length > 1;
            $('hg-gallery-prev').style.display = multi ? '' : 'none';
            $('hg-gallery-next').style.display = multi ? '' : 'none';
            $('hg-gallery-counter').style.display = multi ? '' : 'none';

            const strip = $('hg-gallery-filmstrip');
            strip.innerHTML = '';
            strip.hidden = !multi;
            if (multi) {
                items.forEach((item, i) => {
                    const type = item.type || this.guessType(item.url);
                    let el;
                    if (type === 'image') {
                        el = document.createElement('img');
                        el.src = item.url;
                        el.loading = 'lazy';
                        el.className = 'hg-strip-thumb';
                    } else if (type === 'video') {
                        el = document.createElement('div');
                        el.className = 'hg-strip-thumb';
                        el.innerHTML = `<video src="${item.url}#t=0.1" muted preload="metadata"></video><span class="hg-strip-badge"><i class="fas fa-play"></i></span>`;
                    } else {
                        el = document.createElement('div');
                        el.className = 'hg-strip-thumb';
                        el.innerHTML = '<i class="fas fa-music"></i>';
                    }
                    el.title = item.name || '';
                    el.onclick = (e) => { e.stopPropagation(); this.show(i); };
                    strip.appendChild(el);
                });
            }

            this.modal.classList.add('open');
            this.show(Math.max(0, Math.min(startIdx || 0, items.length - 1)));
        }
    }

    window.HecosGallery = new HecosGalleryManager();
})();
