/**
 * ca_fish_server.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Local Fish Speech Server Management & Model Selection.
 * Handles server lifecycle (status, start, stop, restart), checkpoints browser,
 * and active model switching.
 * Modularized from ca_fish_presets.js to adhere to Hecos architectural standards (<250 lines).
 * ─────────────────────────────────────────────────────────────────────────────
 */

(function () {
    'use strict';

    let _fishModelsCache = null;

    // ── Local Fish Speech Server Management (Status, Start, Stop, Restart) ─────

    window.checkFishServerStatus = async function (interactive = false) {
        const badge = document.getElementById('fish-server-status-pill');
        const desc = document.getElementById('fish-server-desc');
        const startBtn = document.getElementById('btn-fish-server-start');
        const stopBtn = document.getElementById('btn-fish-server-stop');
        const restartBtn = document.getElementById('btn-fish-server-restart');

        try {
            const res = await fetch('/api/audio/fish/server-status');
            const data = await res.json();
            if (!data.ok) throw new Error(data.error || 'Failed to fetch status');

            if (data.status === 'online') {
                if (badge) {
                    badge.className = 'badge-pill badge-ok';
                    badge.style.background = '';
                    badge.style.color = '';
                    badge.innerHTML = '🟢 Server Online (CUDA S2-Pro Ready)';
                }
                if (desc) desc.textContent = `Running on ${data.host}:${data.port} · Model: ${data.model_name}`;
                if (startBtn) startBtn.style.display = 'none';
                if (stopBtn) stopBtn.style.display = 'inline-flex';
                if (restartBtn) restartBtn.style.display = 'inline-flex';
                if (interactive && window.showToast) window.showToast("Fish Speech server is healthy and responding!", "success");
            } else if (data.status === 'starting') {
                if (badge) {
                    badge.className = 'badge-pill';
                    badge.style.background = 'rgba(234, 179, 8, 0.2)';
                    badge.style.color = '#eab308';
                    badge.innerHTML = '🟡 Initializing Model on GPU...';
                }
                if (desc) desc.textContent = `Port ${data.port} active. Loading weights...`;
                if (startBtn) startBtn.style.display = 'none';
                if (stopBtn) stopBtn.style.display = 'inline-flex';
                if (restartBtn) restartBtn.style.display = 'inline-flex';
                if (interactive && window.showToast) window.showToast("Server is starting, please wait a few seconds...", "info");
            } else {
                if (badge) {
                    badge.className = 'badge-pill';
                    badge.style.background = 'rgba(239, 68, 68, 0.2)';
                    badge.style.color = '#ef4444';
                    badge.innerHTML = '🔴 Server Offline (VRAM Free)';
                }
                if (desc) desc.textContent = `Daemon stopped. Click 'Start Server' to load S2-Pro into VRAM.`;
                if (startBtn) startBtn.style.display = 'inline-flex';
                if (stopBtn) stopBtn.style.display = 'none';
                if (restartBtn) restartBtn.style.display = 'none';
                if (interactive && window.showToast) window.showToast("Fish Speech server is offline.", "warning");
            }
        } catch (e) {
            if (badge) {
                badge.className = 'badge-pill';
                badge.style.background = 'rgba(239, 68, 68, 0.2)';
                badge.style.color = '#ef4444';
                badge.innerHTML = '⚠️ Unreachable';
            }
            if (desc) desc.textContent = e.message;
            if (interactive && window.showToast) window.showToast("Cannot connect to server status endpoint: " + e.message, "error");
        }
    };

    window.fishServerAction = async function (action) {
        const restartBtn = document.getElementById('btn-fish-server-restart');
        const startBtn = document.getElementById('btn-fish-server-start');
        const stopBtn = document.getElementById('btn-fish-server-stop');
        const badge = document.getElementById('fish-server-status-pill');

        const actionLabels = {
            restart: "Restarting Fish Speech server (reloading PyTorch model into VRAM)...",
            start: "Starting Fish Speech server on port 8080...",
            stop: "Stopping Fish Speech server and freeing GPU VRAM..."
        };

        if (badge) {
            badge.className = 'badge-pill';
            badge.style.background = 'rgba(234, 179, 8, 0.2)';
            badge.style.color = '#eab308';
            badge.innerHTML = `⏳ ${action.toUpperCase()} in progress...`;
        }

        if (window.showToast) window.showToast(actionLabels[action] || `Executing ${action}...`, "info");

        if (restartBtn) restartBtn.disabled = true;
        if (startBtn) startBtn.disabled = true;
        if (stopBtn) stopBtn.disabled = true;

        try {
            const res = await fetch('/api/audio/fish/server-action', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: action })
            });
            const data = await res.json();
            if (data.ok) {
                if (window.showToast) window.showToast(data.message || `Action ${action} completed successfully!`, "success");
            } else {
                if (window.showToast) window.showToast("Server action failed: " + (data.error || data.message), "error");
            }
        } catch (e) {
            if (window.showToast) window.showToast("Request error: " + e.message, "error");
        } finally {
            if (restartBtn) restartBtn.disabled = false;
            if (startBtn) startBtn.disabled = false;
            if (stopBtn) stopBtn.disabled = false;
            await window.checkFishServerStatus();
        }
    };

    // ── Model Selection & Explorer Integration ───────────────────────────────────

    window.loadFishModelList = async function () {
        const select = document.getElementById('v-fish-model-checkpoint');
        if (!select) return;

        try {
            const res = await fetch('/api/audio/fish/models');
            const data = await res.json();
            if (!data.ok) return;

            _fishModelsCache = data;
            const currentActive = data.active_checkpoint || 's2-pro';

            select.innerHTML = '';
            data.installed_models.forEach(m => {
                const opt = document.createElement('option');
                opt.value = m.id;
                opt.textContent = `${m.name} (${m.size_mb} MB)${m.active ? ' — [Active]' : ''}`;
                opt.style.background = 'var(--bg3)';
                opt.style.color = 'var(--text)';
                if (m.id === currentActive) opt.selected = true;
                select.appendChild(opt);
            });

            window.updateFishModelInfoDisplay(currentActive);
        } catch (e) {
            console.warn("[FishSpeech] Could not load models list:", e);
        }
    };

    window.updateFishModelInfoDisplay = function (modelId) {
        if (!_fishModelsCache || !_fishModelsCache.installed_models) return;
        const model = _fishModelsCache.installed_models.find(m => m.id === modelId);
        const pathDisplay = document.getElementById('v-fish-model-path-display');
        const descDisplay = document.getElementById('v-fish-model-desc-display');
        const familyPill = document.getElementById('v-fish-model-family-pill');

        if (model) {
            if (pathDisplay) pathDisplay.innerHTML = `📁 Path: <code>checkpoints/${model.id}</code> (~${model.size_mb} MB)`;
            if (descDisplay) descDisplay.textContent = model.description;
            if (familyPill) familyPill.textContent = model.id === 's2-pro' ? 'Dual-AR S2-Pro' : 'Dual-AR 1.5';
        }
    };

    window.onFishModelSelectChange = function () {
        const val = document.getElementById('v-fish-model-checkpoint')?.value;
        if (val) window.updateFishModelInfoDisplay(val);
    };

    window.applyFishModelSelection = async function () {
        const select = document.getElementById('v-fish-model-checkpoint');
        const btn = document.getElementById('btn-fish-apply-model');
        if (!select || !btn) return;

        const val = select.value;
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Switching Model...';

        if (window.showToast) window.showToast(`Loading checkpoint '${val}' into Fish Speech daemon...`, "info");

        try {
            const res = await fetch('/api/audio/fish/select-model', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ checkpoint: val })
            });
            const data = await res.json();
            if (data.ok) {
                if (window.showToast) window.showToast(`Active model switched to '${val}'!`, "success");
                await window.loadFishModelList();
                await window.checkFishServerStatus();
            } else {
                if (window.showToast) window.showToast("Failed to switch model: " + data.error, "error");
            }
        } catch (e) {
            if (window.showToast) window.showToast("Error switching model: " + e.message, "error");
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-check"></i> Apply & Reload Model';
        }
    };

    window.openFishCheckpointsFolder = async function () {
        try {
            const res = await fetch('/api/audio/fish/open-folder', { method: 'POST' });
            const data = await res.json();
            if (data.ok) {
                if (window.showToast) window.showToast("Opened checkpoints folder in Explorer!", "info");
            } else {
                if (window.showToast) window.showToast("Error opening folder: " + data.error, "error");
            }
        } catch (e) {
            if (window.showToast) window.showToast("Error opening folder: " + e.message, "error");
        }
    };

    window.copyFishCheckpointsPath = function () {
        const p = "C:\\Hecos\\hecos\\engines\\fish_speech\\checkpoints";
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(p).then(() => {
                if (window.showToast) window.showToast("Copied path to clipboard: " + p, "success");
            }).catch(() => {
                prompt("Checkpoints directory path:", p);
            });
        } else {
            prompt("Checkpoints directory path:", p);
        }
    };

    // Check server status & load models on initial DOM load if card is present
    document.addEventListener('DOMContentLoaded', () => {
        if (document.getElementById('card-fish_speech')) {
            window.checkFishServerStatus();
            window.loadFishModelList();
        }
    });

})();
