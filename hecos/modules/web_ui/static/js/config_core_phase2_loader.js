/**
 * config_core_phase2_loader.js
 * ─────────────────────────────────────────────────────────────────────────────
 * NON-CRITICAL SCRIPT LOADER — Phase 2
 *
 * Waits until the hub menu has rendered (initAll fires), then dynamically
 * injects the remaining 34 scripts in dependency order.
 *
 * This moves ~530KB of JS parsing OUT of the critical path, cutting the
 * "Initializing Tab Engine" wait from 5-60 seconds down to <1 second.
 *
 * Scripts are loaded in batches with a micro-yield between each batch
 * so the browser main thread stays responsive for user interaction.
 * ─────────────────────────────────────────────────────────────────────────────
 */
(function () {
    'use strict';

    const V = window.VERSION || '';
    const VER = V ? `?v=${V}` : '';

    // ── Phase 2 script list — loaded AFTER hub menu is visible ────────────────
    // Order matters within each batch (dependency chain).
    const PHASE2_BATCHES = [
        // Batch A: Mapper core (needed by populateUI, which runs at 50ms in initAll)
        [
            `/static/js/config_mapper_utils.js${VER}`,
            `/static/js/config_mapper_llm.js${VER}`,
            `/static/js/config_mapper_plugins.js${VER}`,
            `/static/js/config_mapper_drive.js${VER}`,
            `/static/js/config_mapper_components.js${VER}`,
            `/static/js/config_mapper_extras.js${VER}`,
            `/static/js/config_mapper.js${VER}`,
        ],
        // Batch B: UI components (panels that auto-init on load)
        [
            `/static/js/hecos_file_picker.js${VER}`,
            `/static/js/config_audio_logic.js${VER}`,
            `/static/js/config_media_logic.js${VER}`,
            `/static/js/config_system_logic.js${VER}`,
            `/static/js/config_persona_logic.js${VER}`,
        ],
        // Batch C: Aesthetic picker (lazy, only needed for aesthetics tab)
        [
            `/static/js/aesthetic_picker/core.js${VER}`,
            `/static/js/aesthetic_picker/palettes.js${VER}`,
            `/static/js/aesthetic_picker/color_ui.js${VER}`,
            `/static/js/aesthetic_picker/image_ui.js${VER}`,
            `/static/js/aesthetic_picker/style_ui.js${VER}`,
        ],
        // Batch D: Chat history engine (used by config panel history section)
        [
            `/static/js/chat_history/ch_state.js${VER}`,
            `/static/js/chat_history/ch_modes.js${VER}`,
            `/static/js/chat_history/ch_render.js${VER}`,
            `/static/js/chat_history/ch_restore.js${VER}`,
            `/static/js/chat_history/ch_actions.js${VER}`,
        ],
        // Batch E: Logs engine
        [
            `/static/js/logs_engine/le_core.js${VER}`,
            `/static/js/logs_engine/le_fetch.js${VER}`,
            `/static/js/logs_engine/le_render.js${VER}`,
            `/static/js/logs_engine/le_windows.js${VER}`,
            `/static/js/logs_engine/le_modals.js${VER}`,
        ],
        // Batch F: Routing panel
        [
            `/static/js/config_routing_data.js${VER}`,
            `/static/js/config_routing_render.js${VER}`,
            `/static/js/config_routing_actions.js${VER}`,
            `/static/js/config_routing_logic.js${VER}`,
        ],
        // Batch G: Search + Events (last — depends on all panels being registered)
        [
            `/static/js/config_search.js${VER}`,
            `/static/js/chat_events.js${VER}`,
            `/ext/calendar/static/js/hecos_wheel_picker.js${VER}`,
        ],
    ];

    // ── Loader helper ─────────────────────────────────────────────────────────
    function loadScript(src) {
        return new Promise((resolve) => {
            // Skip if already loaded
            if (document.querySelector(`script[src^="${src.split('?')[0]}"]`)) {
                return resolve();
            }
            const s = document.createElement('script');
            s.src = src;
            s.onload = resolve;
            s.onerror = () => {
                console.warn(`[Phase2Loader] Failed: ${src}`);
                resolve(); // non-blocking fail
            };
            document.head.appendChild(s);
        });
    }

    // Load scripts in a batch sequentially, yielding between each to stay responsive
    async function loadBatch(batch) {
        for (const src of batch) {
            await loadScript(src);
            // Micro-yield: let the browser handle any pending paint/input before next script
            await new Promise(r => setTimeout(r, 0));
        }
    }

    // Load all batches with a small gap between batches so user interaction is smooth
    async function loadAllBatches() {
        console.log('[Phase2Loader] Starting background script loading...');
        const t0 = performance.now();
        for (let i = 0; i < PHASE2_BATCHES.length; i++) {
            await loadBatch(PHASE2_BATCHES[i]);
            // After each batch, yield 10ms so the browser can paint and handle input
            await new Promise(r => setTimeout(r, 10));
            console.log(`[Phase2Loader] Batch ${i + 1}/${PHASE2_BATCHES.length} done.`);
        }
        const elapsed = Math.round(performance.now() - t0);
        console.log(`[Phase2Loader] All non-critical scripts loaded in ${elapsed}ms.`);

        // After all scripts are loaded, run populateUI once more to fill in
        // any panels that were opened before mappers were ready.
        if (typeof populateUI === 'function') {
            try { populateUI(); } catch(e) {}
        }
        if (typeof initRestartIndicators === 'function') {
            try { initRestartIndicators(); } catch(e) {}
        }
    }

    // ── Entry point: fire after hub has rendered ──────────────────────────────
    // Strategy:
    //  1. If initAll has already signaled completion (isInitialLoading === false), start immediately.
    //  2. Otherwise, poll every 50ms until the hub is done — then start.
    //  3. Hard fallback: start after 3 seconds regardless, to handle edge cases.

    let _started = false;

    function startIfReady() {
        if (_started) return;
        // HECOS_HUB_READY is set by config_core_init.js after initAll Phase 2 completes.
        // isInitialLoading === false is the fallback for backward compatibility.
        const hubReady = window.HECOS_HUB_READY === true ||
                         (typeof isInitialLoading !== 'undefined' && isInitialLoading === false);
        if (hubReady) {
            _started = true;
            // Small delay so the browser finishes painting the hub before we start
            setTimeout(loadAllBatches, 80);
            return;
        }
        // Hub not done yet — check again soon
        setTimeout(startIfReady, 50);
    }

    // Start polling once the DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', startIfReady);
    } else {
        startIfReady();
    }

    // Hard fallback: if after 3s the hub still hasn't signaled, load anyway
    setTimeout(() => {
        if (!_started) {
            console.warn('[Phase2Loader] Fallback: starting after 3s timeout.');
            _started = true;
            loadAllBatches();
        }
    }, 3000);

})();
