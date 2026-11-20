/**
 * Hecos Document Reader — UI, Layout, Overlay & Canvas Rendering
 * Handles HUD, player bar, speed controls, PDF page canvases, thumbnails, and config synchronization.
 */

(function() {
    'use strict';

    function _getState() {
        return (window.DocReaderState && window.DocReaderState.state) ? window.DocReaderState.state : {};
    }

    // ── Create Overlay DOM ───────────────────────────────────────────────────
    function createOverlay() {
        let overlay = document.getElementById('docreader-overlay');
        if (overlay) return overlay;

        const STATE = _getState();

        overlay = document.createElement('div');
        overlay.id = 'docreader-overlay';
        overlay.className = 'docreader-overlay';
        overlay.innerHTML = `
            <!-- Header -->
            <div class="docreader-header">
                <div class="docreader-header-left">
                    <div class="docreader-logo">
                        <i class="fas fa-book-reader"></i>
                        <span>Document Reader</span>
                    </div>
                    <span class="docreader-filename" id="docreader-filename"></span>
                    <div class="docreader-status" id="docreader-status">
                        <div class="docreader-status-dot" id="docreader-status-dot"></div>
                        <span id="docreader-status-text">Ready</span>
                    </div>
                </div>
                <div class="docreader-header-right">
                    <!-- View Mode Selector (Visual vs Split vs Text) -->
                    <div class="docreader-view-modes" id="docreader-view-modes">
                        <button class="docreader-view-btn active" id="docreader-mode-visual" onclick="window.DocReader.setViewMode('visual')" title="Visual Document (displays all images, artwork & layout)">
                            <i class="fas fa-image"></i> Visual
                        </button>
                        <button class="docreader-view-btn" id="docreader-mode-split" onclick="window.DocReader.setViewMode('split')" title="Split View (visual + text side-by-side)">
                            <i class="fas fa-columns"></i> Split
                        </button>
                        <button class="docreader-view-btn" id="docreader-mode-text" onclick="window.DocReader.setViewMode('text')" title="Reading Flow (text only)">
                            <i class="fas fa-align-left"></i> Text
                        </button>
                    </div>

                    <div class="docreader-font-controls">
                        <button class="docreader-font-btn" onclick="window.DocReader.changeFontSize(-0.1)" title="Zoom out / decrease text size">
                            <i class="fas fa-minus"></i>
                        </button>
                        <button class="docreader-font-btn" onclick="window.DocReader.changeFontSize(0.1)" title="Zoom in / increase text size">
                            <i class="fas fa-plus"></i>
                        </button>
                    </div>
                    <button class="docreader-btn-icon" onclick="window.DocReader.toggleSidebar()" title="Table of Contents & Page Thumbnails">
                        <i class="fas fa-list-ul"></i>
                    </button>
                    <button class="docreader-btn docreader-btn-close" onclick="window.DocReader.close()">
                        <i class="fas fa-times"></i> Close
                    </button>
                </div>
            </div>

            <!-- Body -->
            <div class="docreader-body">
                <div class="docreader-document" id="docreader-document">
                    <div class="docreader-content" id="docreader-content">
                        <div class="docreader-loading" id="docreader-loading">
                            <div class="docreader-spinner"></div>
                            <div class="docreader-loading-text">Loading document...</div>
                        </div>
                    </div>
                </div>
                <div class="docreader-sidebar" id="docreader-sidebar">
                    <div class="docreader-sidebar-header">
                        <i class="fas fa-bookmark"></i> Pages
                    </div>
                    <div class="docreader-sidebar-content" id="docreader-toc"></div>
                </div>
            </div>

            <!-- Player Bar -->
            <div class="docreader-player">
                <!-- Transport -->
                <div class="docreader-transport">
                    <button class="docreader-transport-btn" onclick="window.DocReader.prevSentence()" title="Previous sentence">
                        <i class="fas fa-step-backward"></i>
                    </button>
                    <button class="docreader-transport-btn play-btn" id="docreader-play-btn" onclick="window.DocReader.togglePlayPause()" title="Play / Pause">
                        <i class="fas fa-play" id="docreader-play-icon"></i>
                    </button>
                    <button class="docreader-transport-btn" onclick="window.DocReader.nextSentence()" title="Next sentence">
                        <i class="fas fa-step-forward"></i>
                    </button>
                    <button class="docreader-transport-btn" onclick="window.DocReader.stop()" title="Stop">
                        <i class="fas fa-stop"></i>
                    </button>
                </div>

                <!-- Progress -->
                <div class="docreader-progress-wrap">
                    <div class="docreader-progress-bar" id="docreader-progress-bar" onclick="window.DocReader.seekProgress(event)" title="Document Progress (Click to Seek)">
                        <div class="docreader-audio-buffer-fill" id="docreader-audio-buffer-fill"></div>
                        <div class="docreader-progress-fill" id="docreader-progress-fill"></div>
                    </div>
                    <div class="docreader-progress-info">
                        <span id="docreader-progress-current">0 / 0</span>
                        <span id="docreader-progress-page">Page -</span>
                    </div>
                </div>

                <!-- Controls -->
                <div class="docreader-controls">
                    <!-- Speed -->
                    <div class="docreader-control-group docreader-speed-group" id="docreader-speed-group" title="Speed: Drag slider, scroll mouse wheel, or use keyboard arrows (0.5× – 3.0×)">
                        <span class="docreader-control-label" title="Reading speed"><i class="fas fa-tachometer-alt"></i></span>
                        <input type="range" class="docreader-speed-slider" id="docreader-speed-slider" 
                               min="0.5" max="3.0" step="0.05" value="1.0"
                               oninput="window.DocReader.changeSpeed(this.value)"
                               title="Reading Speed: 0.5× to 3.0× (Step 0.05)">
                        <button class="docreader-speed-badge" id="docreader-speed-badge" 
                                onclick="window.DocReader.resetSpeed()" 
                                title="Click to reset to 1.00× (or scroll wheel to adjust)">1.00×</button>
                    </div>

                    <!-- Global Preset (GP) -->
                    <div class="docreader-control-group docreader-gp-group" id="docreader-preset-group" title="Global Preset (AI Soul / Persona Profile)">
                        <span class="docreader-control-label" title="Global Preset (AI Soul / Persona Profile)">GP</span>
                        <select class="docreader-preset-select" id="docreader-preset-select" onchange="window.DocReader.changeHecosPreset(this.value)" title="Global Preset: Select AI Soul / Character Persona">
                            <option value="current">Active Chat GP</option>
                        </select>
                    </div>

                    <!-- TTS Audio Engine -->
                    <div class="docreader-control-group docreader-engine-group" title="Text-to-Speech Engine">
                        <span class="docreader-control-label" title="TTS Audio Engine">Engine</span>
                        <select class="docreader-engine-select" id="docreader-engine-select" onchange="window.DocReader.changeAudioEngine(this.value)" title="Select Text-to-Speech Engine">
                            <option value="auto">⚡ Auto (GP/Default)</option>
                            <option value="kokoro">Kokoro TTS</option>
                            <option value="piper">Piper ONNX</option>
                            <option value="xtts2">XTTS v2</option>
                            <option value="fish_speech">Fish Speech</option>
                            <option value="browser">🌐 Browser Voices</option>
                        </select>
                    </div>

                    <!-- Voice / Audio Preset Selection -->
                    <div class="docreader-control-group docreader-voice-group" title="Voice or Audio Engine Preset">
                        <span class="docreader-control-label" title="Voice or Audio Engine Preset">Voice</span>
                        <select class="docreader-voice-select" id="docreader-voice-select" onchange="window.DocReader.changeVoice(this.value)" title="Select Voice or Audio Configuration Preset">
                            <option value="default">✨ Default Voice</option>
                        </select>
                    </div>

                    <!-- Volume -->
                    <div class="docreader-control-group">
                        <span class="docreader-control-label"><i class="fas fa-volume-up"></i></span>
                        <input type="range" class="docreader-volume-slider" id="docreader-volume" 
                               min="0" max="1" step="0.05" value="1" 
                               oninput="window.DocReader.changeVolume(this.value)">
                    </div>
                </div>
            </div>

            <!-- Live Read-Along Karaoke HUD -->
            <div class="docreader-readalong-hud" id="docreader-readalong-hud">
                <div class="docreader-readalong-badge" id="docreader-readalong-badge">Page 1</div>
                <div class="docreader-readalong-content" id="docreader-readalong-content">
                    Ready to read document...
                </div>
            </div>

            <!-- Selection Tooltip -->
            <div class="docreader-selection-tooltip" id="docreader-selection-tooltip">
                <button onclick="window.DocReader.readSelection()">
                    <i class="fas fa-volume-up"></i> Read Selection
                </button>
                <button onclick="window.DocReader.readFromHere()">
                    <i class="fas fa-play"></i> Read From Here
                </button>
            </div>
        `;
        document.body.appendChild(overlay);

        // Keyboard controls
        document.addEventListener('keydown', function(e) {
            const S = _getState();
            if (!S.isOpen) return;

            const tag = (e.target && e.target.tagName) ? e.target.tagName.toLowerCase() : '';
            if (tag === 'textarea' || (tag === 'input' && e.target.type !== 'range')) {
                return;
            }

            if (e.key === 'Escape') {
                e.preventDefault();
                e.stopPropagation();
                if (S.isReading) {
                    window.DocReader.stop();
                    if (window.showToast) window.showToast('🔇 Document Reader voice stopped', 'info');
                } else {
                    window.DocReader.close();
                }
                return;
            }

            if (e.key === 'ArrowUp') {
                e.preventDefault();
                e.stopPropagation();
                window.DocReader.changeSpeedDelta(0.05, true);
                return;
            }

            if (e.key === 'ArrowDown') {
                e.preventDefault();
                e.stopPropagation();
                window.DocReader.changeSpeedDelta(-0.05, true);
                return;
            }

            if (e.key === 'ArrowRight' && e.shiftKey) {
                e.preventDefault();
                e.stopPropagation();
                window.DocReader.changeSpeedDelta(0.05, true);
                return;
            }

            if (e.key === 'ArrowLeft' && e.shiftKey) {
                e.preventDefault();
                e.stopPropagation();
                window.DocReader.changeSpeedDelta(-0.05, true);
                return;
            }

            if (e.target !== document.getElementById('docreader-speed-slider') && e.target !== document.getElementById('docreader-volume')) {
                if (e.key === 'ArrowRight') {
                    e.preventDefault();
                    e.stopPropagation();
                    window.DocReader.nextSentence();
                    return;
                }
                if (e.key === 'ArrowLeft') {
                    e.preventDefault();
                    e.stopPropagation();
                    window.DocReader.prevSentence();
                    return;
                }
                if (e.code === 'Space') {
                    e.preventDefault();
                    e.stopPropagation();
                    window.DocReader.togglePlayPause();
                    return;
                }
                if (e.key === 'PageDown') {
                    e.preventDefault();
                    e.stopPropagation();
                    window.DocReader.nextPage();
                    return;
                }
                if (e.key === 'PageUp') {
                    e.preventDefault();
                    e.stopPropagation();
                    window.DocReader.prevPage();
                    return;
                }
            }
        });

        // Mouse Wheel speed and volume adjustment on controls
        const speedGroup = overlay.querySelector('#docreader-speed-group');
        if (speedGroup) {
            speedGroup.addEventListener('wheel', function(e) {
                e.preventDefault();
                e.stopPropagation();
                const delta = e.deltaY < 0 ? 0.05 : -0.05;
                window.DocReader.changeSpeedDelta(delta, false);
            }, { passive: false });
        }

        const volGroup = overlay.querySelector('#docreader-volume')?.parentElement;
        if (volGroup) {
            volGroup.addEventListener('wheel', function(e) {
                e.preventDefault();
                e.stopPropagation();
                const S = _getState();
                const delta = e.deltaY < 0 ? 0.05 : -0.05;
                const newVol = Math.max(0, Math.min(1, Math.round(((S.volume !== undefined ? S.volume : 1.0) + delta) * 100) / 100));
                window.DocReader.changeVolume(newVol);
                const slider = document.getElementById('docreader-volume');
                if (slider) slider.value = newVol;
            }, { passive: false });
        }

        // Selection tooltip handler
        const docEl = overlay.querySelector('#docreader-document');
        if (docEl) {
            docEl.addEventListener('mouseup', handleSelectionTooltip);
            docEl.addEventListener('mousedown', () => {
                const tooltip = document.getElementById('docreader-selection-tooltip');
                if (tooltip) tooltip.classList.remove('visible');
            });
        }

        // Initialize voices, presets, and config
        loadConfig();
        loadHecosPresets();
        if (typeof speechSynthesis !== 'undefined' && speechSynthesis.onvoiceschanged !== undefined) {
            speechSynthesis.onvoiceschanged = populateVoices;
        }

        return overlay;
    }

    // ── Load Hecos Presets, Audio Presets, and Voices from Backend ───────────
    async function loadHecosPresets() {
        const STATE = _getState();
        try {
            const res = await fetch('/hecos/api/plugins/document_reader/presets', { cache: 'no-store' });
            if (res.ok) {
                const data = await res.json();
                if (data.ok) {
                    if (Array.isArray(data.presets)) {
                        STATE.availablePresets = data.presets;
                    }
                    STATE.activePresetName = data.active_preset_name || 'Active GP';
                    STATE.systemActiveEngine = data.active_engine || 'kokoro';
                    STATE.audioPresetsMap = data.audio_presets || {};
                    STATE.audioVoicesMap = data.voices || {};

                    populatePresetSelect();
                    populateEngineSelect();
                    populateVoiceAndPresetSelect();
                    return;
                }
            }
        } catch (e) {
            console.warn('[DocReader] Presets API load failed, falling back:', e);
        }

        try {
            const soulsRes = await fetch('/api/souls', { cache: 'no-store' });
            if (soulsRes && soulsRes.ok) {
                const soulsData = await soulsRes.json();
                if (soulsData.ok && Array.isArray(soulsData.souls)) {
                    STATE.availablePresets = soulsData.souls.map(s => ({
                        id: s.meta.id,
                        name: s.meta.name,
                        engine: s.voice?.tts_engine ? s.voice.tts_engine.toUpperCase() : 'LOCAL',
                        voice: s.voice?.tts_voice || ''
                    }));
                    populatePresetSelect();
                    populateEngineSelect();
                    populateVoiceAndPresetSelect();
                }
            }
        } catch (err) {
            console.warn('[DocReader] Fallback presets load failed:', err);
        }
    }

    function populatePresetSelect() {
        const STATE = _getState();
        const pSelect = document.getElementById('docreader-preset-select');
        if (!pSelect) return;
        pSelect.innerHTML = '';

        const currOpt = document.createElement('option');
        currOpt.value = 'current';
        currOpt.textContent = `✨ Active GP (${STATE.activePresetName || 'Hecos'})`;
        pSelect.appendChild(currOpt);

        if (Array.isArray(STATE.availablePresets)) {
            STATE.availablePresets.forEach(p => {
                const opt = document.createElement('option');
                opt.value = p.id;
                opt.textContent = `${p.name} (${p.engine}${p.voice ? ' · ' + p.voice : ''})`;
                pSelect.appendChild(opt);
            });
        }

        if (STATE.hecosPresetId) {
            pSelect.value = STATE.hecosPresetId;
        }
    }

    function populateEngineSelect() {
        const STATE = _getState();
        const eSelect = document.getElementById('docreader-engine-select');
        if (!eSelect) return;
        if (STATE.audioEngine) {
            eSelect.value = STATE.audioEngine;
        }
    }

    function populateVoiceAndPresetSelect() {
        const STATE = _getState();
        const vSelect = document.getElementById('docreader-voice-select');
        if (!vSelect) return;
        vSelect.innerHTML = '';

        const engine = STATE.audioEngine || 'auto';

        if (engine === 'browser') {
            const group = document.createElement('optgroup');
            group.label = "Browser Voices (Web Speech)";
            const voices = (typeof speechSynthesis !== 'undefined') ? speechSynthesis.getVoices() : [];
            if (voices && voices.length > 0) {
                const priority = ['it', 'en', 'es', 'fr', 'de', 'pt'];
                const sorted = [...voices].sort((a, b) => {
                    const aLang = a.lang.split('-')[0].toLowerCase();
                    const bLang = b.lang.split('-')[0].toLowerCase();
                    const aIdx = priority.indexOf(aLang);
                    const bIdx = priority.indexOf(bLang);
                    if (aIdx !== -1 && bIdx !== -1) return aIdx - bIdx;
                    if (aIdx !== -1) return -1;
                    if (bIdx !== -1) return 1;
                    return a.name.localeCompare(b.name);
                });
                sorted.forEach(v => {
                    const opt = document.createElement('option');
                    opt.value = 'browser:' + v.name;
                    opt.textContent = `${v.name} (${v.lang})`;
                    group.appendChild(opt);
                });
            } else {
                const opt = document.createElement('option');
                opt.value = 'browser:default';
                opt.textContent = "Browser Default Voice";
                group.appendChild(opt);
            }
            vSelect.appendChild(group);

            if (STATE.selectedVoice) {
                vSelect.value = 'browser:' + STATE.selectedVoice;
            }
            return;
        }

        // For Neural / Local Engines:
        const defaultOpt = document.createElement('option');
        defaultOpt.value = 'default';
        if (engine === 'auto') {
            defaultOpt.textContent = `✨ Default Voice (Auto: ${STATE.systemActiveEngine || 'Kokoro'})`;
        } else {
            defaultOpt.textContent = `✨ Default Voice (${engine.toUpperCase()})`;
        }
        vSelect.appendChild(defaultOpt);

        const presets = (STATE.audioPresetsMap && STATE.audioPresetsMap[engine]) || [];
        if (presets.length > 0) {
            const pGroup = document.createElement('optgroup');
            pGroup.label = `${engine.toUpperCase()} Audio Presets`;
            presets.forEach(pName => {
                const opt = document.createElement('option');
                opt.value = 'preset:' + pName;
                opt.textContent = `🎙️ ${pName}`;
                pGroup.appendChild(opt);
            });
            vSelect.appendChild(pGroup);
        }

        const voicesObj = (STATE.audioVoicesMap && STATE.audioVoicesMap[engine]) || {};
        const voiceKeys = Object.keys(voicesObj);
        if (voiceKeys.length > 0) {
            const vGroup = document.createElement('optgroup');
            vGroup.label = `${engine.toUpperCase()} Voices & Clones`;
            voiceKeys.forEach(vId => {
                const opt = document.createElement('option');
                opt.value = 'voice:' + vId;
                const vLabel = voicesObj[vId] || vId;
                opt.textContent = (vLabel.startsWith('🎭') || vLabel.startsWith('✨')) ? vLabel : `🗣️ ${vLabel}`;
                vGroup.appendChild(opt);
            });
            vSelect.appendChild(vGroup);
        }

        if (engine === 'auto') {
            const kPresets = (STATE.audioPresetsMap && STATE.audioPresetsMap.kokoro) || [];
            if (kPresets.length > 0) {
                const kpGroup = document.createElement('optgroup');
                kpGroup.label = "Kokoro Audio Presets";
                kPresets.forEach(pName => {
                    const opt = document.createElement('option');
                    opt.value = 'preset:' + pName;
                    opt.textContent = `🎙️ ${pName}`;
                    kpGroup.appendChild(opt);
                });
                vSelect.appendChild(kpGroup);
            }

            const kVoices = (STATE.audioVoicesMap && STATE.audioVoicesMap.kokoro) || {};
            const kKeys = Object.keys(kVoices);
            if (kKeys.length > 0) {
                const kvGroup = document.createElement('optgroup');
                kvGroup.label = "Kokoro Voices";
                kKeys.forEach(vId => {
                    const opt = document.createElement('option');
                    opt.value = 'voice:' + vId;
                    opt.textContent = kVoices[vId] || vId;
                    kvGroup.appendChild(opt);
                });
                vSelect.appendChild(kvGroup);
            }

            const piperVoices = (STATE.audioVoicesMap && STATE.audioVoicesMap.piper) || {};
            const pKeys = Object.keys(piperVoices);
            if (pKeys.length > 0) {
                const ppGroup = document.createElement('optgroup');
                ppGroup.label = "Piper Voices";
                pKeys.forEach(vId => {
                    const opt = document.createElement('option');
                    opt.value = 'voice:' + vId;
                    opt.textContent = piperVoices[vId] || vId;
                    ppGroup.appendChild(opt);
                });
                vSelect.appendChild(ppGroup);
            }
        }

        // Restore selection
        if (STATE.audioPreset) {
            vSelect.value = 'preset:' + STATE.audioPreset;
        } else if (STATE.audioVoice && STATE.audioVoice !== 'default') {
            vSelect.value = 'voice:' + STATE.audioVoice;
        } else {
            vSelect.value = 'default';
        }
    }

    // ── Load User Saved Config ───────────────────────────────────────────────
    async function loadConfig() {
        const STATE = _getState();
        try {
            const res = await fetch('/hecos/api/plugins/document_reader/config');
            if (!res.ok) return;
            const cfg = await res.json();
            if (cfg.voice_source) STATE.voiceSource = cfg.voice_source;
            if (cfg.hecos_preset) STATE.hecosPresetId = cfg.hecos_preset;
            if (cfg.audio_engine) STATE.audioEngine = cfg.audio_engine;
            if (cfg.audio_preset) STATE.audioPreset = cfg.audio_preset;
            if (cfg.audio_voice) STATE.audioVoice = cfg.audio_voice;
            if (cfg.default_voice) STATE.selectedVoice = cfg.default_voice;
            if (cfg.default_rate) STATE.rate = parseFloat(cfg.default_rate);
            if (cfg.default_pitch) STATE.pitch = parseFloat(cfg.default_pitch);
            if (cfg.default_volume) STATE.volume = parseFloat(cfg.default_volume);
            if (cfg.highlight_color) {
                document.documentElement.style.setProperty('--docreader-highlight-color', cfg.highlight_color);
            }
            if (typeof cfg.word_highlight === 'boolean') STATE.wordHighlight = cfg.word_highlight;

            updateSpeedUI(STATE.rate);
            const volSlider = document.getElementById('docreader-volume');
            if (volSlider) volSlider.value = STATE.volume;

            syncVoiceUI();
        } catch (e) {
            console.warn('[DocReader] Failed to load config:', e);
        }
    }

    // ── Save User Config ─────────────────────────────────────────────────────
    async function saveConfig() {
        const STATE = _getState();
        try {
            await fetch('/hecos/api/plugins/document_reader/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    voice_source: STATE.voiceSource,
                    hecos_preset: STATE.hecosPresetId,
                    audio_engine: STATE.audioEngine,
                    audio_preset: STATE.audioPreset,
                    audio_voice: STATE.audioVoice,
                    default_voice: STATE.selectedVoice,
                    default_rate: STATE.rate,
                    default_pitch: STATE.pitch,
                    default_volume: STATE.volume
                })
            });
        } catch (e) {
            console.warn('[DocReader] Failed to save config:', e);
        }
    }

    function updateSpeedUI(val) {
        const speedSlider = document.getElementById('docreader-speed-slider');
        if (speedSlider) speedSlider.value = val;
        const speedBadge = document.getElementById('docreader-speed-badge');
        const helper = window.DocReaderState ? window.DocReaderState.formatSpeed : (v => v + '×');
        if (speedBadge) speedBadge.textContent = helper(val);
    }

    function syncVoiceUI() {
        populateEngineSelect();
        populatePresetSelect();
        populateVoiceAndPresetSelect();
    }

    function populateVoices() {
        const STATE = _getState();
        if (STATE.audioEngine === 'browser') {
            populateVoiceAndPresetSelect();
        }
    }

    function handleSelectionTooltip(e) {
        const STATE = _getState();
        const sel = window.getSelection();
        const selectedText = sel ? sel.toString().trim() : '';
        const tooltip = document.getElementById('docreader-selection-tooltip');
        if (!tooltip) return;

        if (selectedText.length > 2) {
            STATE._selectedText = selectedText;
            const range = sel.getRangeAt(0);
            const rect = range.getBoundingClientRect();
            tooltip.style.top = (rect.bottom + 8) + 'px';
            tooltip.style.left = Math.max(10, rect.left) + 'px';
            tooltip.classList.add('visible');
        } else {
            tooltip.classList.remove('visible');
        }
    }

    // ── Render Pages and Content Area ────────────────────────────────────────
    function renderContent(docData, sessionId) {
        const STATE = _getState();
        if (sessionId && STATE._sessionId !== sessionId) return;
        const contentEl = document.getElementById('docreader-content');
        const tocEl = document.getElementById('docreader-toc');
        if (!contentEl) return;

        contentEl.innerHTML = '';
        if (tocEl) tocEl.innerHTML = '';
        STATE.sentences = [];
        let globalIdx = 0;

        const pages = docData.pages || [];
        const isPdf = docData.docType === 'pdf';
        const isHtml = docData.docType === 'html';
        const isMd = docData.docType === 'md';

        const defaultMode = (isPdf || isHtml) ? 'visual' : 'text';
        STATE.viewMode = defaultMode;

        const container = document.createElement('div');
        container.className = `docreader-pages-container docreader-view-${defaultMode}`;
        container.id = 'docreader-pages-container';
        contentEl.appendChild(container);

        const modeGroup = document.getElementById('docreader-view-modes');
        if (modeGroup) {
            modeGroup.style.display = isPdf ? 'flex' : 'none';
            document.querySelectorAll('.docreader-view-btn').forEach(b => b.classList.remove('active'));
            const activeBtn = document.getElementById(`docreader-mode-${defaultMode}`);
            if (activeBtn) activeBtn.classList.add('active');
        }

        pages.forEach((page, pageIdx) => {
            const pageCard = document.createElement('div');
            pageCard.className = 'docreader-page-card';
            pageCard.id = `docreader-page-${page.pageNum}`;
            pageCard.dataset.pageIdx = pageIdx;
            pageCard.dataset.pageNum = page.pageNum;

            const pageHeader = document.createElement('div');
            pageHeader.className = 'docreader-page-header';
            pageHeader.innerHTML = `
                <span class="docreader-page-badge"><i class="fas fa-file-alt"></i> Page ${page.pageNum} of ${pages.length}</span>
                <span style="font-size:0.75em;color:rgba(255,255,255,0.4);"><i class="fas fa-mouse-pointer"></i> Click to read</span>
            `;
            pageCard.appendChild(pageHeader);

            if (isPdf) {
                const canvasWrap = document.createElement('div');
                canvasWrap.className = 'docreader-canvas-wrap';
                canvasWrap.id = `docreader-canvas-wrap-${page.pageNum}`;
                canvasWrap.innerHTML = `
                    <div class="docreader-canvas-loader">
                        <div class="docreader-spinner" style="width:20px;height:20px;border-width:2px;"></div>
                        <span>Rendering Page ${page.pageNum}...</span>
                    </div>
                `;
                pageCard.appendChild(canvasWrap);
            } else if (isHtml || isMd) {
                if (page.htmlContent) {
                    const richWrap = document.createElement('div');
                    richWrap.className = 'docreader-canvas-wrap';
                    richWrap.style.background = 'transparent';
                    richWrap.style.boxShadow = 'none';
                    richWrap.style.padding = '0';
                    richWrap.style.display = 'block';
                    richWrap.innerHTML = page.htmlContent;
                    pageCard.appendChild(richWrap);
                }
            }

            const textStrip = document.createElement('div');
            textStrip.className = 'docreader-page-text-strip';
            textStrip.id = `docreader-text-strip-${page.pageNum}`;

            const splitter = window.DocReaderState ? window.DocReaderState.splitIntoSentences : (t => [t]);
            const sentences = splitter(page.text || '');
            if (sentences.length === 0) {
                textStrip.innerHTML = '<span style="opacity:0.4;font-style:italic;font-size:0.85em;">Page contains visual elements or illustrations without extractable text.</span>';
            } else {
                sentences.forEach(sentenceText => {
                    const span = document.createElement('span');
                    span.className = 'docreader-sentence';
                    span.dataset.sentenceIdx = globalIdx;

                    const words = sentenceText.split(/(\s+)/);
                    words.forEach(word => {
                        if (/^\s+$/.test(word)) {
                            span.appendChild(document.createTextNode(word));
                        } else {
                            const wordSpan = document.createElement('span');
                            wordSpan.className = 'docreader-word';
                            wordSpan.textContent = word;
                            wordSpan.onclick = (e) => {
                                e.stopPropagation();
                                if (window.DocReaderAudio) window.DocReaderAudio.readSingleWord(word);
                            };
                            span.appendChild(wordSpan);
                        }
                    });

                    span.onclick = (e) => {
                        e.stopPropagation();
                        if (window.DocReader) window.DocReader.readFromIndex(parseInt(span.dataset.sentenceIdx));
                    };

                    textStrip.appendChild(span);
                    textStrip.appendChild(document.createTextNode(' '));

                    STATE.sentences.push({
                        text: sentenceText,
                        el: span,
                        pageIdx: pageIdx,
                        pageNum: page.pageNum
                    });
                    globalIdx++;
                });
            }

            pageCard.appendChild(textStrip);
            container.appendChild(pageCard);

            if (tocEl) {
                const tocItem = document.createElement('div');
                tocItem.className = 'docreader-toc-item';
                if (pageIdx === 0) tocItem.classList.add('active');
                tocItem.dataset.pageIdx = pageIdx;
                const snippet = (page.text || '').replace(/\s+/g, ' ').trim().substring(0, 38);

                tocItem.innerHTML = `
                    <div class="docreader-toc-thumb-wrap" id="docreader-toc-thumb-wrap-${page.pageNum}">
                        <div class="docreader-toc-thumb-placeholder"><i class="fas fa-image"></i></div>
                    </div>
                    <div class="docreader-toc-info">
                        <div class="docreader-toc-title"><i class="fas fa-file-alt"></i> Page ${page.pageNum}</div>
                        <div class="docreader-toc-snippet">${snippet ? snippet + '…' : 'Visual Page'}</div>
                    </div>
                `;
                tocItem.onclick = () => scrollToPage(pageIdx);
                tocEl.appendChild(tocItem);
            }
        });

        if (pages.length > 1) {
            const sidebar = document.getElementById('docreader-sidebar');
            if (sidebar) {
                sidebar.classList.add('open');
                STATE.sidebarOpen = true;
            }
        }

        updateProgress();

        if (isPdf) {
            (async () => {
                for (let pIdx = 0; pIdx < pages.length; pIdx++) {
                    if (sessionId && STATE._sessionId !== sessionId) return;
                    await renderPdfPageCanvas(pages[pIdx], pIdx, sessionId);
                    if (sessionId && STATE._sessionId !== sessionId) return;
                    renderPdfPageThumb(pages[pIdx], pIdx, sessionId);
                }
            })();
        }
    }

    // ── Render High-DPI PDF Page to Canvas ────────────────────────────────────
    async function renderPdfPageCanvas(pageData, pageIdx, sessionId) {
        const STATE = _getState();
        if (sessionId && STATE._sessionId !== sessionId) return;
        const page = pageData.pdfPage;
        if (!page) return;

        const wrap = document.getElementById(`docreader-canvas-wrap-${pageData.pageNum}`);
        if (!wrap) return;

        try {
            const baseViewport = page.getViewport({ scale: 1.0 });
            const docPane = document.getElementById('docreader-document');
            const availWidth = docPane ? Math.max(500, docPane.clientWidth - 100) : 840;
            const targetWidth = Math.min(880, availWidth);
            const scale = targetWidth / baseViewport.width;
            const viewport = page.getViewport({ scale: scale });
            const dpr = Math.min(window.devicePixelRatio || 1, 2);

            const canvas = document.createElement('canvas');
            canvas.className = 'docreader-pdf-canvas';
            canvas.width = Math.floor(viewport.width * dpr);
            canvas.height = Math.floor(viewport.height * dpr);
            const cssW = Math.floor(viewport.width);
            const cssH = Math.floor(viewport.height);
            canvas.style.width = cssW + 'px';
            canvas.style.height = cssH + 'px';
            canvas.dataset.baseWidth = cssW;
            canvas.dataset.baseHeight = cssH;

            const ctx = canvas.getContext('2d');
            ctx.imageSmoothingEnabled = true;
            ctx.imageSmoothingQuality = 'high';

            const renderContext = {
                canvasContext: ctx,
                transform: dpr !== 1 ? [dpr, 0, 0, dpr, 0, 0] : null,
                viewport: viewport
            };

            await page.render(renderContext).promise;
            if (sessionId && STATE._sessionId !== sessionId) return;

            wrap.innerHTML = '';
            wrap.appendChild(canvas);

            if (STATE.visualZoom && STATE.visualZoom !== 1.0) {
                canvas.style.width = Math.floor(cssW * STATE.visualZoom) + 'px';
                canvas.style.height = Math.floor(cssH * STATE.visualZoom) + 'px';
            }

            canvas.style.cursor = 'pointer';
            canvas.title = `Click to start reading page ${pageData.pageNum}`;
            canvas.onclick = () => {
                document.querySelectorAll('.docreader-page-card.reading-page').forEach(c => c.classList.remove('reading-page'));
                const pc = document.getElementById(`docreader-page-${pageData.pageNum}`);
                if (pc) pc.classList.add('reading-page');
                let sIdx = STATE.sentences.findIndex(s => s.pageNum === pageData.pageNum);
                if (sIdx === -1) {
                    sIdx = STATE.sentences.findIndex(s => s.pageNum >= pageData.pageNum);
                }
                if (sIdx !== -1 && window.DocReader) {
                    window.DocReader.readFromIndex(sIdx);
                }
            };
        } catch (err) {
            if (sessionId && STATE._sessionId !== sessionId) return;
            console.error(`[DocReader] Failed to render page ${pageData.pageNum}:`, err);
            if (wrap) {
                wrap.innerHTML = `<div class="docreader-canvas-loader" style="color:#ef4444;"><i class="fas fa-exclamation-triangle"></i> Error rendering page image</div>`;
            }
        }
    }

    // ── Render Thumbnail in TOC Sidebar ───────────────────────────────────────
    async function renderPdfPageThumb(pageData, pageIdx, sessionId) {
        const STATE = _getState();
        if (sessionId && STATE._sessionId !== sessionId) return;
        const page = pageData.pdfPage;
        if (!page) return;

        const thumbWrap = document.getElementById(`docreader-toc-thumb-wrap-${pageData.pageNum}`);
        if (!thumbWrap) return;

        try {
            const baseViewport = page.getViewport({ scale: 1.0 });
            const thumbScale = 96 / baseViewport.width;
            const thumbViewport = page.getViewport({ scale: thumbScale });

            const canvas = document.createElement('canvas');
            canvas.className = 'docreader-toc-canvas';
            canvas.width = Math.floor(thumbViewport.width);
            canvas.height = Math.floor(thumbViewport.height);

            const ctx = canvas.getContext('2d');
            await page.render({
                canvasContext: ctx,
                viewport: thumbViewport
            }).promise;
            if (sessionId && STATE._sessionId !== sessionId) return;

            thumbWrap.innerHTML = '';
            thumbWrap.appendChild(canvas);
        } catch(e) {}
    }

    // ── Update Karaoke Read-Along HUD ─────────────────────────────────────────
    function updateReadAlongHud(sentenceData, wordIndex = -1) {
        const hud = document.getElementById('docreader-readalong-hud');
        const badge = document.getElementById('docreader-readalong-badge');
        const content = document.getElementById('docreader-readalong-content');
        if (!hud || !content || !sentenceData) return;

        hud.classList.add('visible');
        if (badge) badge.textContent = `Page ${sentenceData.pageNum}`;

        const words = sentenceData.text.split(/(\s+)/);
        let wCount = 0;
        content.innerHTML = '';
        words.forEach(w => {
            if (/^\s+$/.test(w)) {
                content.appendChild(document.createTextNode(w));
            } else {
                const sp = document.createElement('span');
                sp.className = 'docreader-hud-word';
                if (wCount === wordIndex) sp.classList.add('active-word');
                sp.textContent = w;
                content.appendChild(sp);
                wCount++;
            }
        });
    }

    function scrollToPage(pageIdx) {
        const pages = document.querySelectorAll('.docreader-page-card, .docreader-page');
        if (pages[pageIdx]) {
            pages[pageIdx].scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
        document.querySelectorAll('.docreader-toc-item').forEach(el => {
            el.classList.toggle('active', parseInt(el.dataset.pageIdx) === pageIdx);
        });
    }

    function updateProgress() {
        const STATE = _getState();
        const currentEl = document.getElementById('docreader-progress-current');
        const pageEl = document.getElementById('docreader-progress-page');
        const fillEl = document.getElementById('docreader-progress-fill');
        
        if (currentEl) {
            currentEl.textContent = `${STATE.currentIndex + 1} / ${STATE.sentences.length}`;
        }
        if (pageEl && STATE.sentences[STATE.currentIndex]) {
            pageEl.textContent = `Page ${STATE.sentences[STATE.currentIndex].pageNum}`;
        }
        if (fillEl && STATE.sentences.length > 0) {
            const pct = ((STATE.currentIndex + 1) / STATE.sentences.length) * 100;
            fillEl.style.width = pct + '%';
        }
    }

    function updateStatus(status, text) {
        const dot = document.getElementById('docreader-status-dot');
        const txt = document.getElementById('docreader-status-text');
        if (dot) {
            dot.className = 'docreader-status-dot';
            if (status === 'reading') dot.classList.add('reading');
            else if (status === 'paused') dot.classList.add('paused');
            else if (status === 'synthesizing' || status === 'loading') dot.classList.add('synthesizing');
        }
        if (txt) txt.textContent = text || 'Ready';
    }

    function updatePlayBtn() {
        const STATE = _getState();
        const btn = document.getElementById('docreader-play-btn');
        const icon = document.getElementById('docreader-play-icon');
        if (!btn || !icon) return;

        if (STATE.isReading && !STATE.isPaused) {
            icon.className = 'fas fa-pause';
            btn.classList.add('active');
        } else {
            icon.className = 'fas fa-play';
            btn.classList.remove('active');
        }
    }

    function highlightSentence(index, clear = false) {
        const STATE = _getState();
        document.querySelectorAll('.docreader-sentence.reading').forEach(el => {
            el.classList.remove('reading');
        });
        document.querySelectorAll('.docreader-word.active-word').forEach(el => {
            el.classList.remove('active-word');
        });

        if (clear || index < 0 || index >= STATE.sentences.length) {
            const hud = document.getElementById('docreader-readalong-hud');
            if (hud) hud.classList.remove('visible');
            document.querySelectorAll('.docreader-page-card.reading-page').forEach(c => c.classList.remove('reading-page'));
            return;
        }

        const sentenceData = STATE.sentences[index];
        if (sentenceData) {
            if (sentenceData.el) {
                sentenceData.el.classList.add('reading');
                if (STATE.viewMode === 'text') {
                    sentenceData.el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }

            const pageCard = document.getElementById(`docreader-page-${sentenceData.pageNum}`);
            if (pageCard) {
                document.querySelectorAll('.docreader-page-card.reading-page').forEach(c => c.classList.remove('reading-page'));
                pageCard.classList.add('reading-page');
                if (STATE.viewMode !== 'text') {
                    pageCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }
            }

            updateReadAlongHud(sentenceData);
        }
    }

    function ensureCSS() {
        if (document.getElementById('docreader-css')) return;
        const link = document.createElement('link');
        link.id = 'docreader-css';
        link.rel = 'stylesheet';
        link.href = '/hpm_plugin/document_reader/static/css/document_reader.css';
        document.head.appendChild(link);
    }

    ensureCSS();

    window.DocReaderUI = {
        createOverlay,
        loadHecosPresets,
        populatePresetSelect,
        populateEngineSelect,
        populateVoiceAndPresetSelect,
        loadConfig,
        saveConfig,
        updateSpeedUI,
        syncVoiceUI,
        populateVoices,
        handleSelectionTooltip,
        renderContent,
        renderPdfPageCanvas,
        renderPdfPageThumb,
        updateReadAlongHud,
        scrollToPage,
        updateProgress,
        updateStatus,
        updatePlayBtn,
        highlightSentence,
        ensureCSS
    };

})();
