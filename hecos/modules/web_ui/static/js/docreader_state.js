/**
 * Hecos Document Reader — State Management & Helpers
 * Holds playback state, caches, sentence parsing, and synthesis progress tracking.
 */

(function() {
    'use strict';

    const STATE = {
        isOpen: false,
        isReading: false,
        isPaused: false,
        currentPath: null,
        sentences: [],          // Array of {text, el, pageIdx, pageNum} objects
        currentIndex: 0,        // Currently reading sentence index
        rate: 1.0,
        pitch: 1.0,
        volume: 1.0,
        voiceSource: 'hecos',   // 'hecos' | 'browser'
        hecosPresetId: 'current', // 'current' | specific GP preset ID
        audioEngine: 'auto',    // 'auto' | 'kokoro' | 'piper' | 'xtts2' | 'fish_speech' | 'browser'
        audioPreset: '',        // audio config preset name
        audioVoice: 'default',  // voice id / model name
        audioPresetsMap: {},    // { kokoro: [...], xtts2: [...], fish_speech: [...] }
        audioVoicesMap: {},     // { kokoro: {...}, piper: {...}, xtts2: {...}, fish_speech: {...} }
        systemActiveEngine: 'kokoro',
        selectedVoice: null,    // Browser voice name (when voiceSource === 'browser')
        fontSize: 1.1,          // em (used in text mode)
        visualZoom: 1.0,        // zoom factor for canvas (used in visual mode)
        viewMode: 'visual',     // 'visual' | 'split' | 'text'
        docType: 'pdf',         // 'pdf' | 'html' | 'md' | 'txt'
        utterance: null,
        _currentAudio: null,    // HTML5 Audio instance for Hecos local TTS
        _audioCache: new Map(), // sentenceIndex -> audioUrl
        _prefetchSet: new Set(),// Indices currently being pre-fetched
        _synthesisInterval: null, // Timer interval for cold load TTS progress
        _loadedEngines: new Set(),// Tracks engines/presets already loaded in memory
        _pendingEngineSwitch: false, // Flag when switching to a different preset
        availablePresets: [],   // Hecos GP presets list from backend
        activePresetName: '',   // Name of active preset in chat
        sidebarOpen: false,
        pages: [],              // Page-separated content
        wordHighlight: true,    // Enable word-by-word highlighting
        _sessionId: 0,
        _selectedText: ''
    };

    function splitIntoSentences(text) {
        if (!text) return [];
        const raw = text.match(/[^.!?…]+[.!?…]+[\s]?|[^.!?…]+$/g) || [text];
        return raw
            .map(s => s.trim())
            .filter(s => s.length > 0);
    }

    function formatSpeed(val) {
        const num = parseFloat(val);
        if (isNaN(num)) return '1.00×';
        return num.toFixed(2) + '×';
    }

    function getAudioCacheKey(index, sentenceData) {
        const text = sentenceData && sentenceData.text ? sentenceData.text.trim() : '';
        const path = STATE.currentPath || 'doc';
        const gp = STATE.hecosPresetId || 'current';
        const eng = STATE.audioEngine || 'auto';
        const ap = STATE.audioPreset || '';
        const v = STATE.audioVoice || 'default';
        const rate = STATE.rate || 1.0;
        return `${path}:::${gp}:::${eng}:::${ap}:::${v}:::${rate}:::${index}:::${text}`;
    }

    function getCurrentEngineKey() {
        if (STATE.voiceSource === 'browser') {
            return 'browser:' + (STATE.selectedVoice || 'default');
        }
        const eng = STATE.audioEngine || 'auto';
        const ap = STATE.audioPreset || '';
        const v = STATE.audioVoice || 'default';
        const gp = STATE.hecosPresetId || 'current';
        return `hecos:${eng}:${ap}:${v}:${gp}`;
    }

    function getActiveEngineName() {
        if (STATE.voiceSource === 'browser') {
            return 'Browser Voice (' + (STATE.selectedVoice || 'Default') + ')';
        }
        if (STATE.audioPreset) {
            return `${(STATE.audioEngine || 'TTS').toUpperCase()} · ${STATE.audioPreset}`;
        }
        if (STATE.audioVoice && STATE.audioVoice !== 'default') {
            return `${(STATE.audioEngine || 'TTS').toUpperCase()} · ${STATE.audioVoice}`;
        }
        if (STATE.audioEngine && STATE.audioEngine !== 'auto') {
            return `${STATE.audioEngine.toUpperCase()} Voice`;
        }
        if (STATE.availablePresets && STATE.hecosPresetId && STATE.hecosPresetId !== 'current') {
            const found = STATE.availablePresets.find(p => p.id === STATE.hecosPresetId);
            if (found && found.name) return found.name;
        }
        return STATE.activePresetName || 'Hecos Neural';
    }

    function clearColdLoadTracker() {
        if (STATE._synthesisInterval) {
            clearInterval(STATE._synthesisInterval);
            STATE._synthesisInterval = null;
        }
    }

    function startColdLoadTracker() {
        clearColdLoadTracker();

        const engineLabel = getActiveEngineName();
        const bufferEl = document.getElementById('docreader-audio-buffer-fill');
        const barEl = document.getElementById('docreader-progress-bar');
        if (bufferEl) {
            bufferEl.classList.add('loading-engine');
            bufferEl.style.width = '10%';
        }
        if (barEl) barEl.classList.add('synthesizing');

        if (window.DocReaderUI) {
            window.DocReaderUI.updateStatus('loading', `Caricamento ${engineLabel}...`);
        }

        let currentPct = 10;
        let elapsedMs = 0;
        const intervalMs = 120;

        STATE._synthesisInterval = setInterval(() => {
            elapsedMs += intervalMs;
            if (elapsedMs < 600) {
                currentPct = Math.min(30, currentPct + 4);
                if (window.DocReaderUI) window.DocReaderUI.updateStatus('loading', `Caricamento ${engineLabel}... (${Math.round(currentPct)}%)`);
            } else if (elapsedMs < 4000) {
                currentPct = Math.min(75, currentPct + 2.5);
                if (window.DocReaderUI) window.DocReaderUI.updateStatus('loading', `Inizializzazione modello in RAM... (${Math.round(currentPct)}%)`);
            } else {
                currentPct = Math.min(94, currentPct + 0.8);
                if (window.DocReaderUI) window.DocReaderUI.updateStatus('loading', `Elaborazione ${engineLabel}... (${Math.round(currentPct)}%)`);
            }
            if (bufferEl) bufferEl.style.width = currentPct + '%';
        }, intervalMs);
    }

    function completeColdLoadTracker(onComplete) {
        clearColdLoadTracker();
        const bufferEl = document.getElementById('docreader-audio-buffer-fill');
        const barEl = document.getElementById('docreader-progress-bar');
        if (bufferEl) {
            bufferEl.style.width = '100%';
        }
        if (window.DocReaderUI) {
            window.DocReaderUI.updateStatus('reading', 'Reading...');
        }

        setTimeout(() => {
            if (bufferEl) {
                bufferEl.classList.remove('loading-engine');
                bufferEl.style.width = '0%';
            }
            if (barEl) barEl.classList.remove('synthesizing');
            if (onComplete) onComplete();
        }, 350);
    }

    function errorColdLoadTracker() {
        clearColdLoadTracker();
        const bufferEl = document.getElementById('docreader-audio-buffer-fill');
        const barEl = document.getElementById('docreader-progress-bar');
        if (bufferEl) {
            bufferEl.classList.remove('loading-engine');
            bufferEl.style.width = '0%';
        }
        if (barEl) barEl.classList.remove('synthesizing');
        if (window.DocReaderUI) {
            window.DocReaderUI.updateStatus('error', 'Errore caricamento TTS');
        }
    }

    window.DocReaderState = {
        state: STATE,
        splitIntoSentences,
        formatSpeed,
        getAudioCacheKey,
        getCurrentEngineKey,
        getActiveEngineName,
        clearColdLoadTracker,
        startColdLoadTracker,
        completeColdLoadTracker,
        errorColdLoadTracker
    };

})();
