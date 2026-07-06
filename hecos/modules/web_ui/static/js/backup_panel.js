/**
 * backup_panel.js
 * Global Backup Orchestrator — UI Logic
 * One function per action. Called by config_backup.html
 */

// ── State ─────────────────────────────────────────────────────────────────────
let _backupCfg = {};
let _backupStatusInterval = null;
let _dynamicModules = [];

// ── Init ──────────────────────────────────────────────────────────────────────

function backupPanelInit() {
    backupLoadConfig();
    backupLoadStatus();
    backupLoadHistory();
    // Poll status while panel is open
    if (_backupStatusInterval) clearInterval(_backupStatusInterval);
    _backupStatusInterval = setInterval(backupLoadStatus, 8000);
}

// ── Config ────────────────────────────────────────────────────────────────────

async function backupLoadConfig() {
    try {
        const res = await fetch('/hecos/api/backup/config');
        const data = await res.json();
        if (!data.ok) return;
        _backupCfg = data.config;

        // Destination
        const destEl = document.getElementById('backup-destination');
        if (destEl) destEl.value = data.config.destination || '';

        // Keep last
        const keepEl = document.getElementById('backup-keep-last');
        if (keepEl) keepEl.value = data.config.keep_last || 7;

        // Enabled toggle
        const enabledEl = document.getElementById('backup-enabled');
        if (enabledEl) enabledEl.checked = !!data.config.enabled;

        // Preset selector
        const presetEl = document.getElementById('backup-schedule-preset');
        if (presetEl) {
            presetEl.value = data.config.schedule_preset || 'daily_2am';
            backupToggleCustomCron(presetEl.value);
        }

        // Custom cron field
        const cronEl = document.getElementById('backup-cron-custom');
        if (cronEl) cronEl.value = data.config.schedule_cron || '';

        // Dynamic Modules UI
        const meta = data.modules_meta || {};
        _dynamicModules = Object.keys(meta);
        
        const grid = document.querySelector('.backup-modules-grid');
        if (grid) {
            grid.innerHTML = '';
            for (const [mod, info] of Object.entries(meta)) {
                const isEnabled = data.config.modules ? !!data.config.modules[mod] : true;
                const checkedStr = isEnabled ? 'checked' : '';
                const lbl = window.t ? (window.t(`hub_mod_${mod}`) || window.t(`ext_${mod}_title`) || info.label) : info.label;
                const icon = info.icon || '📦';
                
                grid.innerHTML += `
                    <label class="backup-mod-check">
                        <input type="checkbox" id="backup-mod-${mod}" ${checkedStr}>
                        ${icon} ${lbl}
                    </label>
                `;
            }
        }

    } catch (e) {
        console.error('[Backup] loadConfig error:', e);
    }
}

async function backupSaveConfig(silent = false) {
    try {
        const destination = document.getElementById('backup-destination')?.value.trim() || '';
        const keep_last   = parseInt(document.getElementById('backup-keep-last')?.value || '7', 10);
        const enabled     = document.getElementById('backup-enabled')?.checked || false;
        const preset      = document.getElementById('backup-schedule-preset')?.value || 'daily_2am';
        const custom_cron = document.getElementById('backup-cron-custom')?.value.trim() || '';

        const modules = {};
        _dynamicModules.forEach(mod => {
            const el = document.getElementById(`backup-mod-${mod}`);
            modules[mod] = el ? el.checked : true;
        });

        const payload = {
            destination,
            keep_last,
            enabled,
            schedule_preset: preset,
            schedule_cron: preset === 'custom' ? custom_cron : undefined,
            modules
        };

        const res = await fetch('/hecos/api/backup/config', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.ok) {
            if (!silent) {
                _backupToast('success', window.t ? window.t('backup_saved') : '✅ Configurazione salvata.');
            }
            backupLoadStatus(); // refresh next_run
        } else {
            _backupToast('error', data.error || 'Save failed');
        }
    } catch (e) {
        _backupToast('error', e.message);
    }
}

function backupToggleCustomCron(preset) {
    const customRow = document.getElementById('backup-custom-cron-row');
    if (customRow) customRow.style.display = preset === 'custom' ? 'flex' : 'none';
}

// ── Status ────────────────────────────────────────────────────────────────────

async function backupLoadStatus() {
    try {
        const res  = await fetch('/hecos/api/backup/status');
        const data = await res.json();
        if (!data.ok) return;

        const s = data.status;

        const nextRunEl = document.getElementById('backup-next-run');
        if (nextRunEl) {
            nextRunEl.textContent = s.next_run
                ? _backupFmtDate(s.next_run)
                : (window.t ? window.t('backup_not_scheduled') : '—');
        }

        const lastRunEl = document.getElementById('backup-last-run');
        if (lastRunEl) {
            lastRunEl.textContent = s.last_backup
                ? _backupFmtDate(s.last_backup)
                : (window.t ? window.t('backup_never') : 'Mai');
        }

        const lastResultEl = document.getElementById('backup-last-result');
        if (lastResultEl) {
            lastResultEl.textContent = s.last_result
                ? (s.last_result === 'ok' ? '✅' : '❌')
                : '—';
        }

        const inProgressEl = document.getElementById('backup-in-progress');
        if (inProgressEl) {
            inProgressEl.style.display = s.in_progress ? 'flex' : 'none';
        }

    } catch (e) { /* silent */ }
}

// ── Manual Backup ─────────────────────────────────────────────────────────────

async function backupRunNow() {
    const destEl = document.getElementById('backup-destination');
    if (!destEl || !destEl.value.trim()) {
        _backupToast('error', window.t ? window.t('backup_no_dest_path') : 'You have not entered a destination path!');
        return;
    }

    // Force save the configuration first to ensure backend uses the correct path
    await backupSaveConfig(true);

    const btn = document.getElementById('backup-run-btn');
    if (btn) { btn.disabled = true; }

    const progressEl = document.getElementById('backup-in-progress');
    if (progressEl) progressEl.style.display = 'flex';

    try {
        const res  = await fetch('/hecos/api/backup/run', { method: 'POST' });
        const data = await res.json();
        if (data.ok) {
            _backupToast('info', window.t ? window.t('backup_started') : '⏳ Backup avviato...');
            // Poll until done
            let polls = 0;
            const poll = setInterval(async () => {
                await backupLoadStatus();
                polls++;
                const s2 = await fetch('/hecos/api/backup/status').then(r => r.json());
                if (!s2?.status?.in_progress || polls > 60) {
                    clearInterval(poll);
                    if (btn) btn.disabled = false;
                    if (progressEl) progressEl.style.display = 'none';
                    if (s2?.status?.last_result === 'ok') {
                        _backupToast('success', window.t ? window.t('backup_ok') : '✅ Backup completato!');
                        backupLoadHistory();
                    } else {
                        _backupToast('error', window.t ? window.t('backup_error') : '❌ Backup fallito.');
                    }
                }
            }, 2500);
        } else {
            _backupToast('error', data.error || 'Backup failed');
            if (btn) btn.disabled = false;
            if (progressEl) progressEl.style.display = 'none';
        }
    } catch (e) {
        _backupToast('error', e.message);
        if (btn) btn.disabled = false;
    }
}

// ── History ───────────────────────────────────────────────────────────────────

async function backupLoadHistory() {
    try {
        const res  = await fetch('/hecos/api/backup/history');
        const data = await res.json();
        const container = document.getElementById('backup-history-list');
        if (!container) return;

        if (!data.ok || !data.files || data.files.length === 0) {
            container.innerHTML = `<div class="backup-empty-note">${window.t ? window.t('backup_no_history') : 'Nessun backup trovato.'}</div>`;
            return;
        }

        container.innerHTML = data.files.map(f => `
            <div class="backup-history-row" data-filename="${f.filename}">
                <div class="backup-history-info">
                    <span class="backup-history-name"><i class="fas fa-file-zipper"></i> ${f.filename}</span>
                    <span class="backup-history-meta">${_backupFmtDate(f.modified)} · ${_backupFmtSize(f.size)}</span>
                </div>
                <div class="backup-history-actions">
                    <button class="btn btn-secondary btn-sm" onclick="backupDownload('${f.filename}')" title="${window.t ? window.t('backup_download') : 'Scarica'}">
                        <i class="fas fa-download"></i>
                    </button>
                    <button class="btn btn-primary btn-sm" onclick="backupRestoreFromHistory('${f.filename}')" title="${window.t ? window.t('backup_restore') : 'Ripristina'}">
                        <i class="fas fa-rotate-left"></i>
                    </button>
                    <button class="btn btn-danger btn-sm" onclick="backupDeleteHistory('${f.filename}')" title="${window.t ? window.t('backup_delete') : 'Elimina'}">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `).join('');
    } catch (e) {
        console.error('[Backup] loadHistory error:', e);
    }
}

function backupDownload(filename) {
    window.location.href = `/hecos/api/backup/download/${encodeURIComponent(filename)}`;
}

async function backupDeleteHistory(filename) {
    if (!confirm(`Eliminare il backup "${filename}"?`)) return;
    try {
        const res  = await fetch(`/hecos/api/backup/history/${encodeURIComponent(filename)}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.ok) {
            _backupToast('success', window.t ? window.t('backup_deleted') : 'Backup eliminato.');
            backupLoadHistory();
        } else {
            _backupToast('error', data.error || 'Delete failed');
        }
    } catch (e) {
        _backupToast('error', e.message);
    }
}

// ── Restore ───────────────────────────────────────────────────────────────────

function backupHandleRestoreUpload(input) {
    const file = input.files[0];
    if (!file) return;
    input.value = '';
    _backupShowRestoreModal(null, file);
}

function backupRestoreFromHistory(filename) {
    _backupShowRestoreModal(filename, null);
}

function _backupGetModuleLabel(m) {
    if (m === 'calendar') return '📅 Calendar';
    if (m === 'contacts') return '📒 Contatti';
    if (m === 'chat') return '💬 Chat';
    if (m === 'memory') return '🧠 Memory/RAG';
    if (m === 'reminders') return '⏰ Promemoria';
    if (m === 'flows') return '⚡ Flows';
    if (m === 'users') return '👤 Utenti';
    if (m === 'lists') return '📋 Liste';
    if (m === 'system_config') return '⚙️ Configs';
    return m;
}

function _backupShowRestoreModal(filename, file) {
    // Build module selection checkboxes
    // Note: The UI dynamically builds these now, so we can just use _dynamicModules or Object.keys(_backupCfg.modules)
    const renderMods = _dynamicModules.length ? _dynamicModules : Object.keys(_backupCfg.modules || {});
    
    const checkboxes = renderMods.map(m => {
        let lbl = m;
        // Basic fallback map if meta isn't available
        const fallbackMap = {
            'calendar': 'Calendar',
            'contacts': 'Contatti',
            'chat': 'Chat History',
            'memory': 'Memory / RAG',
            'reminders': 'Promemoria',
            'flows': 'Flows',
            'users': 'Utenti',
            'lists': 'Liste',
            'system_config': 'Configurazioni'
        };
        lbl = fallbackMap[m] || m;
        if (window.t) {
            lbl = window.t(`hub_mod_${m}`) || window.t(`ext_${m}_title`) || lbl;
        }
        return `
        <label class="backup-mod-check">
            <input type="checkbox" id="restore-mod-${m}" checked> ${lbl}
        </label>
        `;
    }).join('');

    const src = filename ? `<strong>${filename}</strong>` : (file ? `<strong>${file.name}</strong>` : '');

    // Create overlay modal
    let modal = document.getElementById('backup-restore-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'backup-restore-modal';
        modal.className = 'backup-modal-overlay';
        document.body.appendChild(modal);
    }
    modal.innerHTML = `
        <div class="backup-modal-box">
            <div class="backup-modal-header">
                <i class="fas fa-rotate-left"></i>
                <span>${window.t ? window.t('backup_restore_title') : 'Ripristina Backup'}</span>
            </div>
            <div class="backup-modal-body">
                <p style="margin-bottom:12px; color:var(--muted); font-size:0.85rem;">
                    ${window.t ? window.t('backup_restore_from') : 'Sorgente:'} ${src}
                </p>
                <p style="margin-bottom:10px; font-weight:600; font-size:0.85rem;">
                    ${window.t ? window.t('backup_select_modules') : 'Seleziona i moduli da ripristinare:'}
                </p>
                <div class="backup-modules-grid">${checkboxes}</div>
                <label class="backup-select-all-row">
                    <input type="checkbox" id="restore-select-all" checked onchange="backupToggleAllRestoreMods(this.checked)">
                    ${window.t ? window.t('backup_select_all') : 'Seleziona tutti'}
                </label>
            </div>
            <div class="backup-modal-footer">
                <button class="btn btn-secondary" onclick="document.getElementById('backup-restore-modal').style.display='none'">
                    ${window.t ? window.t('cancel') : 'Annulla'}
                </button>
                <button class="btn btn-danger" onclick="_backupDoRestore('${filename || ''}', ${file ? 'window._backupRestoreFile' : 'null'})">
                    <i class="fas fa-rotate-left"></i> ${window.t ? window.t('backup_restore_confirm') : 'Ripristina'}
                </button>
            </div>
        </div>
    `;
    modal.style.display = 'flex';
    if (file) window._backupRestoreFile = file;
}

function backupToggleAllRestoreMods(checked) {
    const mods = _dynamicModules.length ? _dynamicModules : Object.keys(_backupCfg.modules || {});
    mods.forEach(m => {
        const el = document.getElementById(`restore-mod-${m}`);
        if (el) el.checked = checked;
    });
}

async function _backupDoRestore(filename, file) {
    const renderMods = _dynamicModules.length ? _dynamicModules : Object.keys(_backupCfg.modules || {});
    const selectedMods = renderMods
        .filter(m => document.getElementById(`restore-mod-${m}`)?.checked);

    document.getElementById('backup-restore-modal').style.display = 'none';

    if (selectedMods.length === 0) {
        _backupToast('error', window.t ? window.t('backup_no_modules') : 'Seleziona almeno un modulo.');
        return;
    }

    _backupToast('info', window.t ? window.t('backup_restoring') : '⏳ Ripristino in corso...');

    try {
        let res;
        if (file) {
            const form = new FormData();
            form.append('file', file);
            selectedMods.forEach(m => form.append('modules', m));
            res = await fetch('/hecos/api/backup/restore', { method: 'POST', body: form });
        } else {
            res = await fetch('/hecos/api/backup/restore', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ filename, modules: selectedMods })
            });
        }
        const data = await res.json();
        if (data.ok) {
            _backupToast('success', window.t ? window.t('backup_restore_ok') : '✅ Ripristino completato!');
        } else {
            _backupToast('error', data.error || 'Restore failed');
        }
    } catch (e) {
        _backupToast('error', e.message);
    }
}

// ── Browse folder ──────────────────────────────────────────────────────────────

function backupBrowseFolder() {
    const currentPath = document.getElementById('backup-destination')?.value || 'C:\\';
    if (typeof HecosFilePicker !== 'undefined') {
        HecosFilePicker.open({
            title: window.t ? window.t('backup_choose_folder') : 'Seleziona cartella di destinazione',
            initialPath: currentPath,
            onSelect: (path) => {
                const el = document.getElementById('backup-destination');
                if (el) el.value = path;
            }
        });
    } else {
        const p = prompt(window.t ? window.t('backup_enter_path') : 'Inserisci il percorso della cartella:', currentPath);
        if (p) {
            const el = document.getElementById('backup-destination');
            if (el) el.value = p;
        }
    }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function _backupFmtDate(iso) {
    if (!iso) return '—';
    try {
        return new Date(iso).toLocaleString('it-IT', {
            day: '2-digit', month: '2-digit', year: 'numeric',
            hour: '2-digit', minute: '2-digit'
        });
    } catch (e) { return iso; }
}

function _backupFmtSize(bytes) {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return (bytes / Math.pow(k, i)).toFixed(1) + ' ' + sizes[i];
}

function _backupToast(type, msg) {
    if (window.toast) {
        window.toast(type, msg);
    } else {
        const colors = { success: '#27ae60', error: '#e74c3c', info: '#3498db' };
        const t = document.createElement('div');
        t.style.cssText = `position:fixed;bottom:24px;right:24px;background:${colors[type]||'#333'};color:#fff;
            padding:12px 18px;border-radius:8px;z-index:9999;font-size:0.85rem;
            box-shadow:0 4px 16px rgba(0,0,0,0.3);max-width:360px;`;
        t.textContent = msg;
        document.body.appendChild(t);
        setTimeout(() => t.remove(), 4000);
    }
}
