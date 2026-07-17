/**
 * packages_panel_manage.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Manage logic for Hecos Package Manager (Status, Uninstall)
 */

window.hpmConfirmUninstall = function (id, name) {
  const msgTemplate = window.HPM_I18N?.confirm_uninstall || 'Are you sure you want to uninstall the package \'%s\'?';
  const msg = msgTemplate.replace('%s', name);
  
  window.hpmShowConfirm(msg, window.HPM_I18N?.uninstall || 'Uninstall', () => {
    window.hpmUninstall(id, name);
  });
};

window.hpmUninstall = async function(id, name) {
  const card = document.getElementById(`hpm-pkg-${id}`);
  if (card) { card.style.opacity = '0.4'; card.style.pointerEvents = 'none'; }

  const _ti = (en, it, es) => { const l = (document.documentElement.lang||'en').toLowerCase(); if(l.startsWith('it')) return it; if(l.startsWith('es')) return es; return en; };
  const lblUninst = _ti('Uninstalling...', 'Disinstallazione in corso...', 'Desinstalando...');

  // ── Build log panel (same as batch) ──────────────────────────────────────
  const baseMsg = `<i class="fas fa-trash fa-spin" style="margin-right:6px; color:#ef4444;"></i> ${lblUninst}`;
  const uninstallHtml = `
    <div id="hpm-uninstall-header" style="font-size:1.05em; font-weight:600; color:var(--text);">${baseMsg}</div>
    <div id="hpm-uninstall-logs" style="margin-top:12px; font-size:0.92em; color:var(--muted); font-family:monospace; text-align:left; background:rgba(0,0,0,0.25); border-radius:6px; padding:8px; border-left:2px solid #ef4444; max-height:150px; overflow-y:auto; display:none; word-break:break-all;"></div>
  `;
  if (typeof window.hpmSetProgress === 'function') {
    window.hpmSetProgress(true, uninstallHtml, 30);
  }

  // ── SSE log listener ──────────────────────────────────────────────────────
  const logListener = (e) => {
    const logsContainer = document.getElementById('hpm-uninstall-logs');
    const header = document.getElementById('hpm-uninstall-header');
    if (!logsContainer || !header) return;

    const step = e.detail.step || '';
    const msg  = e.detail.message || '';

    if (step === 'pip_log' || step === 'pip_remove') {
      logsContainer.style.display = 'block';
      const div = document.createElement('div');
      div.textContent = msg;
      if (step === 'pip_remove') {
        div.style.color = '#ef4444';
        div.style.fontWeight = 'bold';
        div.style.marginTop = '4px';
        div.style.marginBottom = '2px';
      }
      logsContainer.appendChild(div);
      logsContainer.scrollTop = logsContainer.scrollHeight;
    } else if (msg) {
      header.innerHTML = `<i class="fas fa-trash fa-spin" style="margin-right:6px; color:#ef4444;"></i> ${msg}`;
    }
  };

  document.addEventListener('hpmProgressUpdate', logListener);

  try {
    const resp = await fetch(`/api/packages/${id}`, { method: 'DELETE' });
    const data = await resp.json();

    if (data.ok) {
      const lblSuccess = _ti('Uninstalled successfully!', 'Disinstallato con successo!', '¡Desinstalado con éxito!');
      const lblHint = _ti('Double click anywhere to close', 'Fai doppio clic per chiudere', 'Haz doble clic para cerrar');
      const hintHTML = `<div style="font-size:0.75em;color:var(--muted);margin-top:15px;opacity:0.6;font-weight:normal;">${lblHint}</div>`;

      if (typeof window.hpmSetProgress === 'function') {
        window.hpmSetProgress(true, `<div style="text-align:center; padding: 10px 0;"><i class="fas fa-check-circle" style="margin-right:6px; color:#10b981; font-size:1.5em; margin-bottom:8px; display:block;"></i> <b style="font-size:1.1em; color:var(--text)">${lblSuccess}</b>${hintHTML}</div>`, 100);

        const container = document.getElementById('hpm-install-progress');
        if (container) {
          container.ondblclick = () => window.hpmSetProgress(false);
          container.style.cursor = 'default';
        }
      } else {
        if (window.showToast) window.showToast(`Package uninstalled.`);
      }

      if (typeof window.hpmLoadPackages === 'function') window.hpmLoadPackages();
      if (typeof window.hpmRefreshConfigHub === 'function') window.hpmRefreshConfigHub();
      if (typeof window.loadWidgetsPanel === 'function') window.loadWidgetsPanel();
    } else {
      if (typeof window.hpmSetProgress === 'function') window.hpmSetProgress(false);
      if (window.showToast) window.showToast(`Uninstall failed: ${data.error}`, 'error');
      if (card) { card.style.opacity = '1'; card.style.pointerEvents = ''; }
    }
  } catch (err) {
    if (typeof window.hpmSetProgress === 'function') window.hpmSetProgress(false);
    if (window.showToast) window.showToast(`${err.message}`, 'error');
    if (card) { card.style.opacity = '1'; card.style.pointerEvents = ''; }
  } finally {
    document.removeEventListener('hpmProgressUpdate', logListener);
  }
};

window.hpmUninstallSelected = function() {
    if (window._hpmSelectedPackages.size === 0) return;
    
    const count = window._hpmSelectedPackages.size;
    const _ti = (en, it, es) => { const l = (document.documentElement.lang||'en').toLowerCase(); if(l.startsWith('it')) return it; if(l.startsWith('es')) return es; return en; };
    
    const msgTemplate = _ti(
        `Are you sure you want to uninstall <b>{count} packages</b>?<br><br><span style="font-size:0.85em;color:var(--muted);">This operation cannot be undone.</span>`,
        `Sei sicuro di voler disinstallare <b>{count} pacchetti</b>?<br><br><span style="font-size:0.85em;color:var(--muted);">Questa operazione non è annullabile.</span>`,
        `¿Estás seguro de que deseas desinstalar <b>{count} paquetes</b>?<br><br><span style="font-size:0.85em;color:var(--muted);">Esta operación no se puede deshacer.</span>`
    );
    const msg = msgTemplate.replace('{count}', count);
    const title = _ti(`Uninstall ${count}`, `Disinstalla ${count}`, `Desinstalar ${count}`);
    
    window.hpmShowConfirm(msg, title, async () => {
        // Extract IDs BEFORE exiting selection mode (Set gets cleared)
        const ids = Array.from(window._hpmSelectedPackages);
        const total = ids.length;
        window.hpmToggleSelectionMode();

        const _ti = (en, it, es) => { const l = (document.documentElement.lang||'en').toLowerCase(); if(l.startsWith('it')) return it; if(l.startsWith('es')) return es; return en; };

        // ── Helper: update the header with current X/N counter ──────────────
        const setHeader = (done, current) => {
            const header = document.getElementById('hpm-uninstall-header');
            if (!header) return;
            const counterBadge = `<span style="background:rgba(239,68,68,0.2); color:#ef4444; border-radius:10px; padding:1px 8px; font-size:0.85em; margin-left:8px; font-weight:700;">${done}/${total}</span>`;
            const pkgLabel = current ? ` <span style="color:var(--muted);font-weight:normal;font-size:0.9em;">${current}</span>` : '';
            header.innerHTML = `<i class="fas fa-trash fa-spin" style="margin-right:6px; color:#ef4444;"></i> ${_ti('Uninstalling', 'Disinstallazione', 'Desinstalando')}${pkgLabel} ${counterBadge}`;
        };

        // ── Build log panel ───────────────────────────────────────────────────
        const uninstallHtml = `
            <div id="hpm-uninstall-header" style="font-size:1.05em; font-weight:600; color:var(--text);"></div>
            <div id="hpm-uninstall-logs" style="margin-top:12px; font-size:0.92em; color:var(--muted); font-family:monospace; text-align:left; background:rgba(0,0,0,0.25); border-radius:6px; padding:8px; border-left:2px solid #ef4444; max-height:150px; overflow-y:auto; display:none; word-break:break-all;"></div>
        `;
        window.hpmSetProgress(true, uninstallHtml, 5);
        setHeader(0, ids[0]);

        // ── SSE log listener ──────────────────────────────────────────────────
        const logListener = (e) => {
            const logsContainer = document.getElementById('hpm-uninstall-logs');
            if (!logsContainer) return;
            const step = e.detail.step || '';
            const msg  = e.detail.message || '';
            if (step === 'pip_log' || step === 'pip_remove') {
                logsContainer.style.display = 'block';
                const div = document.createElement('div');
                div.textContent = msg;
                if (step === 'pip_remove') {
                    div.style.color = '#ef4444';
                    div.style.fontWeight = 'bold';
                    div.style.marginTop = '4px';
                    div.style.marginBottom = '2px';
                }
                logsContainer.appendChild(div);
                logsContainer.scrollTop = logsContainer.scrollHeight;
            }
        };
        document.addEventListener('hpmProgressUpdate', logListener);

        const results = [];
        let succeeded = 0;
        let failed = 0;

        try {
            for (let i = 0; i < ids.length; i++) {
                const pkgId = ids[i];
                const progress = Math.round(5 + ((i / total) * 90));

                setHeader(i, pkgId);
                if (typeof window.hpmSetProgress === 'function') {
                    // Update only the progress bar without replacing the content
                    const bar = document.getElementById('hpm-progress-bar');
                    if (bar) bar.style.width = progress + '%';
                }

                // Grey separator in log box
                const logsContainer = document.getElementById('hpm-uninstall-logs');
                if (logsContainer && i > 0) {
                    const sep = document.createElement('div');
                    sep.style.cssText = 'border-top:1px dashed rgba(255,255,255,0.08); margin:6px 0; padding-top:4px; color:rgba(255,255,255,0.3); font-size:0.8em;';
                    sep.textContent = `── ${pkgId} ──`;
                    logsContainer.appendChild(sep);
                    logsContainer.scrollTop = logsContainer.scrollHeight;
                }

                try {
                    const resp = await fetch(`/api/packages/${pkgId}`, { method: 'DELETE' });
                    const data = await resp.json();
                    if (data.ok) {
                        results.push({ id: pkgId, ok: true });
                        succeeded++;
                    } else {
                        results.push({ id: pkgId, ok: false, error: data.error || 'error' });
                        failed++;
                    }
                } catch (e) {
                    results.push({ id: pkgId, ok: false, error: e.message });
                    failed++;
                }
            }

            // ── Summary screen ────────────────────────────────────────────────
            setHeader(total, null);

            let extraHTML = `<div style="text-align:left; background:rgba(0,0,0,0.2); border-radius:8px; padding:10px; margin-top:12px; max-height:150px; overflow-y:auto; font-size:0.85em; border:1px solid rgba(255,255,255,0.05);">`;
            results.forEach(r => {
                const icon = r.ok ? '<i class="fas fa-check" style="color:#10b981; margin-right:6px; width:14px;"></i>' : '<i class="fas fa-times" style="color:#ef4444; margin-right:6px; width:14px;"></i>';
                const removedMsg = r.ok
                    ? `<span style="color:var(--muted)">${_ti('removed', 'rimosso', 'eliminado')}</span>`
                    : `<span style="color:#ef4444">${r.error || 'error'}</span>`;
                extraHTML += `<div style="margin-bottom:4px; display:flex; justify-content:space-between;"><span style="color:var(--text);">${icon}${r.id}</span>${removedMsg}</div>`;
            });
            extraHTML += `</div>`;

            if (succeeded > 0) {
                const sound = localStorage.getItem('hpm_install_sound') || 'success.mp3';
                if (sound !== 'none') {
                    if (sound.startsWith('custom|')) {
                        new Audio('/api/local_file?path=' + encodeURIComponent(sound.substring(7))).play().catch(() => {});
                    } else {
                        new Audio(`/static/sounds/${sound}`).play().catch(() => {});
                    }
                }
            }

            const lblHint = `<div style="font-size:0.75em;color:var(--muted);margin-top:15px;opacity:0.6;font-weight:normal;">${_ti('Double click anywhere to close', 'Fai doppio clic per chiudere', 'Haz doble clic para cerrar')}</div>`;
            const lblSuccess = failed === 0
                ? _ti('Batch uninstall completed!', 'Disinstallazione batch completata!', '¡Desinstalación por lotes completada!')
                : _ti('Completed with some errors', 'Completato con alcuni errori', 'Completado con algunos errores');
            const mainIconColor = failed === 0 ? '#10b981' : (succeeded > 0 ? '#f59e0b' : '#ef4444');
            const mainIcon = failed === 0 ? 'fa-check-circle' : (succeeded > 0 ? 'fa-exclamation-circle' : 'fa-times-circle');

            window.hpmSetProgress(true, `
              <div style="text-align:center; padding: 10px 0;">
                  <i class="fas ${mainIcon}" style="margin-right:6px; color:${mainIconColor}; font-size:1.5em; margin-bottom:8px; display:block;"></i>
                  <b style="font-size:1.1em; color:var(--text)">${lblSuccess}</b>
                  <div style="font-size:0.85em; color:var(--muted); margin-top:4px;">${succeeded} ${_ti('removed', 'rimossi', 'eliminados')} • ${failed} ${_ti('failed', 'falliti', 'fallidos')}</div>
                  ${extraHTML}
                  ${lblHint}
              </div>`, 100);

            const container = document.getElementById('hpm-install-progress');
            if (container) {
                container.ondblclick = () => window.hpmSetProgress(false);
                container.style.cursor = 'default';
            }

            if (typeof window.hpmLoadPackages === 'function') window.hpmLoadPackages();
            if (typeof window.hpmRefreshConfigHub === 'function') window.hpmRefreshConfigHub();
            if (typeof window.loadWidgetsPanel === 'function') window.loadWidgetsPanel();

        } catch (err) {
            window.hpmSetProgress(false);
            if (window.showToast) window.showToast(`Network error: ${err.message}`, 'error');
        } finally {
            document.removeEventListener('hpmProgressUpdate', logListener);
        }
    });
};

