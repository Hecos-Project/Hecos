function _hpmStoreBuildDetailModal() {
  const closeLabel = _t('Close', 'Chiudi', 'Cerrar');
  return `
    <div id="hpm-store-detail-modal"
         style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.85);z-index:9999;
                align-items:flex-start;justify-content:center;padding:24px;overflow-y:auto;"
         onclick="if(event.target===this)this.style.display='none'">
      <div style="background:var(--bg2);border:1px solid var(--border-color);border-radius:20px;
                  max-width:800px;width:100%;margin:auto;box-shadow:0 32px 80px rgba(0,0,0,.75);
                  position:relative;overflow:hidden;">

        <!-- Accent band -->
        <div id="hpm-detail-band" style="height:5px;background:linear-gradient(90deg,var(--accent),#7c3aed);"></div>

        <!-- Close X -->
        <button onclick="document.getElementById('hpm-store-detail-modal').style.display='none'"
                style="position:absolute;top:14px;right:14px;background:rgba(255,255,255,.08);border:none;
                       border-radius:50%;width:32px;height:32px;color:var(--text);font-size:1em;cursor:pointer;
                       display:flex;align-items:center;justify-content:center;z-index:2;transition:background .2s;"
                onmouseover="this.style.background='rgba(255,255,255,.18)'"
                onmouseout="this.style.background='rgba(255,255,255,.08)'">
          <i class="fas fa-times"></i>
        </button>

        <!-- Package meta header -->
        <div id="hpm-detail-header" style="padding:24px 28px 0;"></div>

        <!-- Image carousel -->
        <div id="hpm-detail-carousel-wrap" style="display:none;padding:18px 28px 0;">
          <div style="position:relative;border-radius:12px;overflow:hidden;background:#060606;
                      border:1px solid rgba(255,255,255,0.08);aspect-ratio:16/9;">
            <img id="hpm-detail-carousel-img" src="" alt=""
                 style="width:100%;height:100%;object-fit:contain;display:block;cursor:zoom-in;"
                 onclick="window.open(this.src,'_blank')">
            <button id="hpm-carousel-prev" onclick="window._hpmCarouselStep(-1)"
                    style="display:none;position:absolute;left:10px;top:50%;transform:translateY(-50%);
                           background:rgba(0,0,0,.6);border:none;border-radius:50%;width:38px;height:38px;
                           color:#fff;font-size:1em;cursor:pointer;align-items:center;justify-content:center;
                           transition:background .2s;"
                    onmouseover="this.style.background='rgba(0,0,0,.9)'"
                    onmouseout="this.style.background='rgba(0,0,0,.6)'">
              <i class="fas fa-chevron-left"></i>
            </button>
            <button id="hpm-carousel-next" onclick="window._hpmCarouselStep(1)"
                    style="display:none;position:absolute;right:10px;top:50%;transform:translateY(-50%);
                           background:rgba(0,0,0,.6);border:none;border-radius:50%;width:38px;height:38px;
                           color:#fff;font-size:1em;cursor:pointer;align-items:center;justify-content:center;
                           transition:background .2s;"
                    onmouseover="this.style.background='rgba(0,0,0,.9)'"
                    onmouseout="this.style.background='rgba(0,0,0,.6)'">
              <i class="fas fa-chevron-right"></i>
            </button>
            <div id="hpm-carousel-counter"
                 style="display:none;position:absolute;bottom:10px;right:12px;background:rgba(0,0,0,.65);
                        color:#fff;font-size:0.72em;padding:3px 9px;border-radius:12px;
                        pointer-events:none;font-weight:600;letter-spacing:.4px;"></div>
          </div>
          <!-- Thumbnail strip -->
          <div id="hpm-carousel-thumbs" style="display:flex;gap:7px;margin-top:10px;overflow-x:auto;padding-bottom:4px;"></div>
        </div>

        <!-- README content -->
        <div style="padding:22px 28px 4px;">
          <div id="hpm-store-detail-content" style="color:var(--text);font-size:0.88em;line-height:1.75;"></div>
        </div>

        <!-- Footer -->
        <div style="padding:16px 28px 22px;border-top:1px solid var(--border-color);
                    display:flex;align-items:center;justify-content:flex-end;gap:10px;">
          <div id="hpm-detail-install-btn"></div>
          <button onclick="document.getElementById('hpm-store-detail-modal').style.display='none'"
                  class="btn btn-secondary" style="font-size:0.85em;">${closeLabel}</button>
        </div>
      </div>
    </div>`;
}

// ── Carousel logic ────────────────────────────────────────────────────────────
window._hpmCarouselStep = function (dir) {
  const imgs = _detailCarousel.images;
  if (!imgs.length) return;
  _detailCarousel.index = (_detailCarousel.index + dir + imgs.length) % imgs.length;
  _hpmCarouselRender();
};

window._hpmCarouselGoto = function (i) {
  _detailCarousel.index = i;
  _hpmCarouselRender();
};

function _hpmCarouselRender() {
  const { images, index } = _detailCarousel;
  const img     = document.getElementById('hpm-detail-carousel-img');
  const counter = document.getElementById('hpm-carousel-counter');
  const prev    = document.getElementById('hpm-carousel-prev');
  const next    = document.getElementById('hpm-carousel-next');
  const thumbs  = document.getElementById('hpm-carousel-thumbs');
  if (!img) return;

  img.src = images[index];
  const multi = images.length > 1;

  if (counter) { counter.textContent = `${index + 1} / ${images.length}`; counter.style.display = multi ? 'block' : 'none'; }
  if (prev)    { prev.style.display  = multi ? 'flex' : 'none'; }
  if (next)    { next.style.display  = multi ? 'flex' : 'none'; }

  if (thumbs) {
    if (multi) {
      thumbs.innerHTML = images.map((src, i) => `
        <img src="${_hesc(src)}" onclick="window._hpmCarouselGoto(${i})"
             style="width:74px;height:46px;object-fit:cover;border-radius:6px;cursor:pointer;flex-shrink:0;
                    border:2px solid ${i === index ? 'var(--accent)' : 'rgba(255,255,255,.12)'};
                    opacity:${i === index ? '1' : '0.5'};transition:opacity .2s,border-color .2s;"
             onerror="this.style.display='none'">`).join('');
    } else {
      thumbs.innerHTML = '';
    }
  }
}

// ── "Read More" / Detail show ─────────────────────────────────────────────────
window.hpmStoreShowReadMe = async function (pkgId) {
  const pkgs = window.HPM_STORE_STATE.catalog?.packages || [];
  const pkg = pkgs.find(p => p.id === pkgId);
  if (!pkg) return;

  const meta   = TYPE_META[pkg.type] || { label: pkg.type, icon: 'fa-cube', color: '#6b7280' };
  const modal  = document.getElementById('hpm-store-detail-modal');
  const content = document.getElementById('hpm-store-detail-content');
  const headerEl = document.getElementById('hpm-detail-header');
  const band   = document.getElementById('hpm-detail-band');
  const carouselWrap = document.getElementById('hpm-detail-carousel-wrap');
  const installBtn = document.getElementById('hpm-detail-install-btn');

  // Accent colour band
  if (band) band.style.background = `linear-gradient(90deg,${meta.color},${meta.color}88)`;

  // ── Package Header ────────────────────────────────────────────────────────
  const sizeFmt = pkg.size_bytes ? `${(pkg.size_bytes / 1024).toFixed(1)} KB` : '';
  const fallbackIcon = 'https://raw.githubusercontent.com/Hecos-Project/Hecos-Packages/main/Hecos_module_Image_preview_square.png';
  const iconUrl = pkg.icon_url || fallbackIcon;
  const icon = pkg.fa_icon || 'fa-cube';

  if (headerEl) headerEl.innerHTML = `
    <div style="display:flex;align-items:flex-start;gap:18px;">
      <div style="width:60px;height:60px;border-radius:16px;flex-shrink:0;background:${meta.color}18;
                  display:flex;align-items:center;justify-content:center;overflow:hidden;
                  border:1px solid ${meta.color}33;">
        <img src="${_hesc(iconUrl)}" style="width:100%;height:100%;object-fit:cover;"
             onerror="this.outerHTML='<i class=\\'fas ${icon}\\' style=\\'font-size:24px;color:${meta.color};\\'></i>'">
      </div>
      <div style="flex:1;min-width:0;">
        <div style="font-size:1.2em;font-weight:800;color:var(--text);line-height:1.2;">${_hesc(pkg.name)}</div>
        <div style="display:flex;align-items:center;gap:8px;margin-top:7px;flex-wrap:wrap;">
          <span style="font-size:0.7em;font-weight:700;letter-spacing:.6px;text-transform:uppercase;
                       color:${meta.color};background:${meta.color}18;padding:2px 8px;border-radius:5px;">
            <i class="fas ${meta.icon}" style="margin-right:4px;"></i>${meta.label}
          </span>
          <span style="font-size:0.75em;color:var(--muted);">v${_hesc(pkg.version)}</span>
          ${sizeFmt ? `<span style="font-size:0.72em;color:var(--muted);"><i class="fas fa-weight-hanging" style="margin-right:3px;opacity:.4;"></i>${sizeFmt}</span>` : ''}
          <span style="font-size:0.72em;color:var(--muted);"><i class="fas fa-user" style="margin-right:3px;opacity:.4;"></i>${_hesc(pkg.author || 'Unknown')}</span>
        </div>
        ${pkg.description ? `<div style="font-size:0.83em;color:var(--muted);margin-top:9px;line-height:1.55;">${_hesc(pkg.description)}</div>` : ''}
        ${pkg.tags && pkg.tags.length ? `
          <div style="display:flex;gap:5px;flex-wrap:wrap;margin-top:8px;">
            ${pkg.tags.map(t => `<span style="font-size:0.67em;background:rgba(255,255,255,.07);color:var(--muted);padding:2px 7px;border-radius:5px;">#${_hesc(t)}</span>`).join('')}
          </div>` : ''}
        ${(pkg.dependencies && pkg.dependencies.length > 0) || (pkg.pip_requirements && pkg.pip_requirements.length > 0) ? `
          <div style="display:flex;gap:12px;flex-wrap:wrap;margin-top:12px;padding-top:10px;border-top:1px solid rgba(255,255,255,0.05);">
            ${pkg.dependencies && pkg.dependencies.length ? `
              <div style="font-size:0.72em;color:var(--muted);display:flex;align-items:center;gap:6px;">
                <i class="fas fa-boxes" style="color:#3b82f6;"></i>
                <span style="font-weight:600;opacity:0.7;">${_t('Depends on:','Dipende da:','Depende de:')}</span>
                ${pkg.dependencies.map(d => `<span style="background:rgba(59,130,246,0.15);color:#60a5fa;padding:2px 6px;border-radius:4px;font-weight:600;">${_hesc(d)}</span>`).join('')}
              </div>` : ''}
            ${pkg.pip_requirements && pkg.pip_requirements.length ? `
              <div style="font-size:0.72em;color:var(--muted);display:flex;align-items:center;gap:6px;">
                <i class="fab fa-python" style="color:#f59e0b;"></i>
                <span style="font-weight:600;opacity:0.7;">PIP:</span>
                ${pkg.pip_requirements.map(p => `<span style="background:rgba(245,158,11,0.15);color:#fbbf24;padding:2px 6px;border-radius:4px;font-weight:600;">${_hesc(p.split('==')[0].split('>=')[0])}</span>`).join('')}
              </div>` : ''}
          </div>` : ''}
      </div>
    </div>`;

  // ── Footer Install Button ─────────────────────────────────────────────────
  if (installBtn) {
    if (!pkg.installed) {
      installBtn.innerHTML = `
        <button onclick="document.getElementById('hpm-store-detail-modal').style.display='none';window.hpmStoreInstall('${pkg.id}','${pkg.download_url}','${pkg.name}')"
                style="background:linear-gradient(135deg,var(--accent),#7c3aed);color:#fff;border:none;
                       border-radius:8px;padding:8px 20px;font-size:0.85em;font-weight:700;cursor:pointer;">
          <i class="fas fa-download" style="margin-right:6px;"></i>Install</button>`;
    } else if (pkg.update_available) {
      installBtn.innerHTML = `
        <button onclick="document.getElementById('hpm-store-detail-modal').style.display='none';window.hpmStoreInstall('${pkg.id}','${pkg.download_url}','${pkg.name}')"
                style="background:linear-gradient(135deg,#f59e0b,#d97706);color:#fff;border:none;
                       border-radius:8px;padding:8px 20px;font-size:0.85em;font-weight:700;cursor:pointer;">
          <i class="fas fa-arrow-up" style="margin-right:6px;"></i>Update to v${pkg.version}</button>`;
    } else {
      installBtn.innerHTML = `
        <span style="display:inline-flex;align-items:center;gap:6px;font-size:0.82em;color:#10b981;
                     background:rgba(16,185,129,.12);padding:7px 14px;border-radius:8px;font-weight:600;">
          <i class="fas fa-check-circle"></i> Installed</span>`;
    }
  }

  // ── Carousel ──────────────────────────────────────────────────────────────
  const fallbackShot = 'https://raw.githubusercontent.com/Hecos-Project/Hecos-Packages/main/Hecos_module_Image_preview.png';
  const screenshots  = (pkg.screenshots && pkg.screenshots.length > 0) ? pkg.screenshots : [fallbackShot];
  _detailCarousel    = { images: screenshots, index: 0 };
  if (carouselWrap) {
    carouselWrap.style.display = 'block';
    _hpmCarouselRender();
  }

  // ── Show modal + spinner ──────────────────────────────────────────────────
  modal.style.display = 'flex';
  content.innerHTML   = '<div style="text-align:center;padding:30px;"><i class="fas fa-spinner fa-spin fa-2x" style="opacity:.35;"></i></div>';

  // ── Fetch README ──────────────────────────────────────────────────────────
  let mdText = null;
  try {
    if (pkg.readme_url) {
      const res = await fetch(pkg.readme_url);
      if (res.ok) mdText = await res.text();
    }
    if (!mdText) {
      const fallbackReadme = `https://raw.githubusercontent.com/Hecos-Project/Hecos-Packages/main/${pkg.id}_src/README.md`;
      const res = await fetch(fallbackReadme);
      if (res.ok) mdText = await res.text();
    }
  } catch (e) {
    console.error('[HPM Store] Failed to fetch README', e);
  }

  if (mdText) {
    if (typeof marked !== 'undefined') {
      content.innerHTML = `
        <div class="hpm-readme-body" style="--hpm-c:${meta.color};">
          ${marked.parse(mdText)}
        </div>
        <style>
          .hpm-readme-body h1,.hpm-readme-body h2,.hpm-readme-body h3{color:var(--text);margin:1.1em 0 .4em;font-weight:700;}
          .hpm-readme-body h1{font-size:1.3em;}
          .hpm-readme-body h2{font-size:1.1em;border-bottom:1px solid var(--border-color);padding-bottom:.35em;}
          .hpm-readme-body h3{font-size:1em;}
          .hpm-readme-body a{color:var(--hpm-c);text-decoration:none;}
          .hpm-readme-body a:hover{text-decoration:underline;}
          .hpm-readme-body code{background:rgba(255,255,255,.09);padding:2px 6px;border-radius:4px;font-size:0.85em;font-family:monospace;}
          .hpm-readme-body pre{background:rgba(0,0,0,.4);border:1px solid var(--border-color);border-radius:10px;padding:16px;overflow-x:auto;margin:12px 0;}
          .hpm-readme-body pre code{background:none;padding:0;}
          .hpm-readme-body blockquote{border-left:3px solid var(--hpm-c);margin:0 0 0 4px;padding:4px 14px;color:var(--muted);font-style:italic;}
          .hpm-readme-body img{max-width:100%;border-radius:10px;margin:6px 0;}
          .hpm-readme-body table{width:100%;border-collapse:collapse;font-size:0.85em;margin:10px 0;}
          .hpm-readme-body th,.hpm-readme-body td{border:1px solid var(--border-color);padding:7px 10px;}
          .hpm-readme-body th{background:rgba(255,255,255,.06);font-weight:700;}
          .hpm-readme-body hr{border:none;border-top:1px solid var(--border-color);margin:16px 0;}
          .hpm-readme-body ul,.hpm-readme-body ol{padding-left:20px;margin:6px 0;}
          .hpm-readme-body li{margin:3px 0;}
        </style>`;
    } else {
      content.innerHTML = `<pre style="white-space:pre-wrap;font-family:inherit;font-size:0.87em;line-height:1.6;">${_hesc(mdText)}</pre>`;
    }
  } else {
    // ── Rich empty state ──────────────────────────────────────────────────
    const noDocTitle = _t('No documentation available', 'Nessuna documentazione disponibile', 'Sin documentación disponible');
    const noDocSub   = _t(
      'You can still install this module and explore its features directly.',
      'Puoi comunque installare questo modulo ed esplorarne le funzionalità.',
      'Aún puedes instalar este módulo y explorar sus funciones.'
    );
    const githubLabel = _t('View on GitHub', 'Vedi su GitHub', 'Ver en GitHub');
    content.innerHTML = `
      <div style="text-align:center;padding:36px 20px;">
        <div style="width:64px;height:64px;border-radius:50%;background:${meta.color}12;display:inline-flex;
                    align-items:center;justify-content:center;margin-bottom:16px;border:1px solid ${meta.color}25;">
          <i class="fas fa-file-alt" style="font-size:1.6em;color:${meta.color};opacity:.6;"></i>
        </div>
        <div style="font-weight:700;font-size:1.05em;color:var(--text);margin-bottom:8px;">${noDocTitle}</div>
        <div style="font-size:0.83em;color:var(--muted);line-height:1.6;max-width:380px;margin:0 auto;">${noDocSub}</div>
        ${pkg.homepage_url ? `
          <a href="${_hesc(pkg.homepage_url)}" target="_blank" rel="noopener"
             style="display:inline-flex;align-items:center;gap:7px;margin-top:20px;
                    color:${meta.color};font-size:0.83em;font-weight:600;text-decoration:none;
                    border:1px solid ${meta.color}44;padding:7px 16px;border-radius:8px;
                    transition:background .2s;" onmouseover="this.style.background='${meta.color}18'"
             onmouseout="this.style.background='transparent'">
            <i class="fas fa-external-link-alt"></i>${githubLabel}
          </a>` : ''}
      </div>`;
  }
};

// ── Progress Modal ────────────────────────────────────────────────────────────
function _hpmStoreBuildProgressModal() {
  return `
    <div id="hpm-store-progress-modal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.85);
         z-index:10000;align-items:center;justify-content:center;padding:20px;"
         ondblclick="this.style.display='none'">
      <div style="background:var(--bg2);border:1px solid var(--border-color);border-radius:16px;
                  max-width:420px;width:100%;padding:32px;text-align:center;box-shadow:0 20px 60px rgba(0,0,0,.6);cursor:default;">
        <div id="hpm-store-progress-icon" style="font-size:2.5em;margin-bottom:16px;">
          <i class="fas fa-download" style="color:var(--accent);animation:pulse 1.5s infinite;"></i>
        </div>
        <div id="hpm-store-progress-title" style="font-weight:700;font-size:1.1em;margin-bottom:8px;color:var(--text);">Installing…</div>
        <div style="background:var(--border-color);border-radius:6px;height:6px;overflow:hidden;margin:14px 0;">
          <div id="hpm-store-progress-bar"
               style="height:100%;width:0%;background:linear-gradient(90deg,var(--accent),var(--accent2,#7c3aed));
                      border-radius:6px;transition:width .4s ease;"></div>
        </div>
        <div id="hpm-store-progress-msg" style="font-size:0.82em;color:var(--muted);min-height:1.4em;"></div>
        <div id="hpm-store-progress-log" style="font-size:0.84em;color:var(--accent);min-height:1.2em;margin-top:6px;font-family:monospace;white-space:normal;word-break:break-all;text-align:left;opacity:0.85;"></div>
        <div id="hpm-store-progress-hint" style="display:none;font-size:0.75em;color:var(--muted);margin-top:20px;opacity:0.6;">
          ${_t('Double click anywhere to close', 'Fai doppio clic per chiudere', 'Haz doble clic para cerrar')}
        </div>
        <div style="font-size:0.7em;color:var(--muted);margin-top:15px;opacity:0.5;">
          ${_t('For more info consult Hecos logs.', 'Per maggiori info consultare i log di Hecos.', 'Para más información consulte los registros de Hecos.')}
        </div>
      </div>
    </div>`;
}

// ── Install via SSE ───────────────────────────────────────────────────────────
