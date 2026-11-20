/**
 * ca_engine_runtime.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Unified Runtime Status & Daemon/Model Lifecycle Controls for Piper, Kokoro,
 * and XTTSv2 in the WebUI Voice Configuration panels.
 * Complies with Hecos modular JS guidelines (<200 lines).
 * ─────────────────────────────────────────────────────────────────────────────
 */

(function () {
    'use strict';

    let _pollTimer = null;
    let _pollCount = 0;

    function _formatMem(st) {
        const parts = [];
        if (st.pid && st.mode === 'daemon') parts.push(`PID ${st.pid}`);
        else if (st.mode === 'in-process' && st.loaded) parts.push('In-Process');
        if (st.device && st.device !== '—') parts.push(st.device);
        if (st.ram_mb && st.ram_mb > 0) parts.push(`RAM ${st.ram_mb.toFixed(0)} MB`);
        if (st.vram_mb && st.vram_mb > 0) parts.push(`VRAM ${st.vram_mb.toFixed(0)} MB`);
        return parts.join(' · ');
    }

    function _renderEngineCardRuntime(engine, st) {
        const pill = document.getElementById(`${engine}-runtime-pill`);
        const desc = document.getElementById(`${engine}-runtime-desc`);
        const startBtn = document.getElementById(`btn-${engine}-runtime-start`);
        const stopBtn = document.getElementById(`btn-${engine}-runtime-stop`);
        const restartBtn = document.getElementById(`btn-${engine}-runtime-restart`);

        if (!pill && !desc) return;

        const isDaemon = (st.mode === 'daemon');
        const memInfo = _formatMem(st);

        if (st.status === 'online') {
            if (pill) {
                pill.className = 'badge-pill badge-ok';
                pill.style.background = '';
                pill.style.color = '';
                pill.innerHTML = isDaemon ? '🟢 Daemon Online' : '🟢 Loaded in Memory';
            }
            if (desc) {
                desc.textContent = `${st.model || st.label}${memInfo ? ' · ' + memInfo : ''}`;
            }
            if (startBtn) startBtn.style.display = 'none';
            if (stopBtn) stopBtn.style.display = 'inline-flex';
            if (restartBtn) restartBtn.style.display = 'inline-flex';
        } else if (st.status === 'starting') {
            if (pill) {
                pill.className = 'badge-pill';
                pill.style.background = 'rgba(234, 179, 8, 0.2)';
                pill.style.color = '#eab308';
                pill.innerHTML = '🟡 Loading...';
            }
            if (desc) {
                desc.textContent = `Initializing ${st.label || engine} in background...`;
            }
            if (startBtn) startBtn.style.display = 'none';
            if (stopBtn) stopBtn.style.display = 'inline-flex';
            if (restartBtn) restartBtn.style.display = 'none';
        } else {
            if (pill) {
                pill.className = 'badge-pill';
                pill.style.background = 'rgba(148, 163, 184, 0.16)';
                pill.style.color = 'var(--muted)';
                pill.innerHTML = isDaemon ? '⚪ Daemon Stopped' : '⚪ Unloaded (RAM Free)';
            }
            if (desc) {
                desc.textContent = isDaemon
                    ? 'Persistent IPC process is stopped. Click Start Daemon for instant synthesis.'
                    : 'Model weights are unloaded from RAM/VRAM. Click Load Model to warm up.';
            }
            if (startBtn) startBtn.style.display = 'inline-flex';
            if (stopBtn) stopBtn.style.display = 'none';
            if (restartBtn) restartBtn.style.display = 'none';
        }
    }

    window.refreshTTSEnginesRuntime = async function (interactive = false) {
        try {
            const res = await fetch('/api/audio/engines/status', { cache: 'no-store' });
            if (!res.ok) {
                throw new Error(`HTTP ${res.status}`);
            }
            const data = await res.json();
            if (!data || !data.ok || !data.engines) return;

            let anyStarting = false;
            ['piper', 'kokoro', 'xtts2'].forEach((eng) => {
                const st = data.engines[eng];
                if (st) {
                    _renderEngineCardRuntime(eng, st);
                    if (st.status === 'starting') anyStarting = true;
                }
            });

            if (data.engines.fish_speech && data.engines.fish_speech.status === 'starting') {
                anyStarting = true;
            }
            if (typeof window.checkFishServerStatus === 'function') {
                const fishCard = document.getElementById('card-fish_speech');
                if (fishCard && fishCard.style.display !== 'none') {
                    window.checkFishServerStatus(false);
                }
            }

            if (interactive && window.showToast) {
                window.showToast('TTS runtime status refreshed.', 'info');
            }

            if (anyStarting && _pollCount < 40) {
                _pollCount += 1;
                clearTimeout(_pollTimer);
                _pollTimer = setTimeout(() => window.refreshTTSEnginesRuntime(false), 2500);
            } else {
                _pollCount = 0;
            }
        } catch (err) {
            console.warn('[TTSRuntime] Status check error:', err);
            ['piper', 'kokoro', 'xtts2'].forEach((eng) => {
                const pill = document.getElementById(`${eng}-runtime-pill`);
                if (pill && pill.textContent && pill.textContent.includes('Checking')) {
                    pill.innerHTML = '⚠️ Status Unavailable';
                }
            });
        }
    };

    window.ttsEngineRuntimeAction = async function (engine, action) {
        const pill = document.getElementById(`${engine}-runtime-pill`);
        const btns = ['start', 'stop', 'restart']
            .map((a) => document.getElementById(`btn-${engine}-runtime-${a}`))
            .filter(Boolean);

        btns.forEach((b) => { b.disabled = true; });
        if (pill) {
            pill.className = 'badge-pill';
            pill.style.background = 'rgba(234, 179, 8, 0.2)';
            pill.style.color = '#eab308';
            pill.innerHTML = `⏳ ${action.toUpperCase()}...`;
        }

        try {
            const res = await fetch(`/api/audio/engines/${encodeURIComponent(engine)}/action`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: action })
            });
            const data = await res.json();
            if (data.ok) {
                if (window.showToast) window.showToast(data.message || `Action '${action}' executed.`, 'success');
            } else {
                if (window.showToast) window.showToast(data.error || data.message || 'Action failed.', 'error');
            }
        } catch (err) {
            if (window.showToast) window.showToast('Runtime request error: ' + err.message, 'error');
        } finally {
            btns.forEach((b) => { b.disabled = false; });
            _pollCount = 0;
            await window.refreshTTSEnginesRuntime(false);
        }
    };

    function _initTTSRuntimeCheck() {
        if (document.getElementById('card-piper') || document.getElementById('card-kokoro')) {
            window.refreshTTSEnginesRuntime(false);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', _initTTSRuntimeCheck);
    } else {
        _initTTSRuntimeCheck();
    }
})();

