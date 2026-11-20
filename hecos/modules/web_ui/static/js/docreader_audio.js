/**
 * Hecos Document Reader — Audio & Speech Synthesis
 * Manages browser Web Speech API and Hecos Neural Local TTS playback, prefetching, and word highlighting.
 */

(function() {
    'use strict';

    function _getState() {
        return (window.DocReaderState && window.DocReaderState.state) ? window.DocReaderState.state : {};
    }

    // ── TTS: Speak a sentence ────────────────────────────────────────────────
    function speakSentence(index, onEnd) {
        const STATE = _getState();
        if (index < 0 || index >= STATE.sentences.length) {
            if (onEnd) onEnd(true); // done = true
            return;
        }

        const sentenceData = STATE.sentences[index];
        STATE.currentIndex = index;
        
        if (window.DocReaderUI) {
            window.DocReaderUI.highlightSentence(index);
            window.DocReaderUI.updateProgress();
        }

        // Update TOC active
        document.querySelectorAll('.docreader-toc-item').forEach(el => {
            el.classList.toggle('active', 
                parseInt(el.dataset.pageIdx) === sentenceData.pageIdx);
        });

        if (STATE.voiceSource === 'browser') {
            speakWithWebSpeech(sentenceData, onEnd);
        } else {
            speakWithHecosLocal(index, sentenceData, onEnd);
        }
    }

    // ── Mode A: Web Speech API (Browser) ─────────────────────────────────────
    function speakWithWebSpeech(sentenceData, onEnd) {
        const STATE = _getState();
        if (window.DocReaderState) {
            window.DocReaderState.clearColdLoadTracker();
        }

        const utterance = new SpeechSynthesisUtterance(sentenceData.text);
        utterance.rate = STATE.rate;
        utterance.pitch = STATE.pitch;
        utterance.volume = STATE.volume;

        if (STATE.selectedVoice) {
            const voices = (typeof speechSynthesis !== 'undefined') ? speechSynthesis.getVoices() : [];
            const v = voices.find(v => v.name === STATE.selectedVoice);
            if (v) utterance.voice = v;
        }

        if (STATE.wordHighlight) {
            utterance.onboundary = (event) => {
                if (event.name === 'word') {
                    const wordElements = sentenceData.el ? sentenceData.el.querySelectorAll('.docreader-word') : [];
                    wordElements.forEach(w => w.classList.remove('active-word'));
                    
                    const charIdx = event.charIndex;
                    const text = sentenceData.text;
                    let wordCount = 0;
                    let i = 0;
                    while (i < charIdx) {
                        if (/\s/.test(text[i])) {
                            while (i < charIdx && /\s/.test(text[i])) i++;
                            wordCount++;
                        } else {
                            i++;
                        }
                    }
                    if (wordElements[wordCount]) {
                        wordElements[wordCount].classList.add('active-word');
                    }
                    if (window.DocReaderUI) {
                        window.DocReaderUI.updateReadAlongHud(sentenceData, wordCount);
                    }
                }
            };
        }

        utterance.onstart = () => {
            if (window.DocReaderUI) {
                window.DocReaderUI.updateStatus('reading', 'Reading (Browser)...');
            }
        };

        utterance.onend = () => {
            STATE.utterance = null;
            if (onEnd) onEnd(false);
        };

        utterance.onerror = (e) => {
            if (e.error !== 'interrupted' && e.error !== 'canceled') {
                console.error('[DocReader] Browser TTS error:', e.error);
            }
            STATE.utterance = null;
            if (onEnd) onEnd(true);
        };

        STATE.utterance = utterance;
        if (typeof speechSynthesis !== 'undefined') {
            speechSynthesis.speak(utterance);
        }
    }

    // ── Mode B: Hecos Neural TTS (Local Kokoro / Piper / XTTS2 / Fish Speech) ─
    async function speakWithHecosLocal(index, sentenceData, onEnd) {
        const STATE = _getState();
        if (!STATE.isReading) return;

        const cacheKey = window.DocReaderState ? window.DocReaderState.getAudioCacheKey(index, sentenceData) : '';
        let audioUrl = STATE._audioCache.get(cacheKey);
        const engineKey = window.DocReaderState ? window.DocReaderState.getCurrentEngineKey() : '';
        const isCold = !STATE._loadedEngines.has(engineKey) || STATE._pendingEngineSwitch;

        if (!audioUrl) {
            if (isCold && window.DocReaderState) {
                window.DocReaderState.startColdLoadTracker();
            } else if (window.DocReaderUI) {
                window.DocReaderUI.updateStatus('reading', 'Reading (Hecos Local)...');
            }

            try {
                const res = await fetch('/hecos/api/plugins/document_reader/tts', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        text: sentenceData.text,
                        preset_id: STATE.hecosPresetId || 'current',
                        engine: STATE.audioEngine || 'auto',
                        audio_preset: STATE.audioPreset || '',
                        voice: STATE.audioVoice || 'default',
                        rate: STATE.rate || 1.0
                    })
                });
                if (!res.ok) throw new Error('TTS server status ' + res.status);
                const data = await res.json();
                if (!data.ok || !data.audio_url) throw new Error(data.error || 'No audio returned');
                audioUrl = data.audio_url;
                STATE._audioCache.set(cacheKey, audioUrl);

                if (isCold && window.DocReaderState) {
                    STATE._loadedEngines.add(engineKey);
                    STATE._pendingEngineSwitch = false;
                    window.DocReaderState.completeColdLoadTracker();
                }
            } catch (err) {
                console.warn('[DocReader] Hecos TTS error:', err);
                if (isCold && window.DocReaderState) {
                    window.DocReaderState.errorColdLoadTracker();
                }
                if (window.DocReaderUI) {
                    window.DocReaderUI.updateStatus('error', 'Voice synthesis error, continuing...');
                }
                setTimeout(() => {
                    if (STATE.isReading && onEnd) onEnd(false);
                }, 1000);
                return;
            }
        } else {
            STATE._loadedEngines.add(engineKey);
            STATE._pendingEngineSwitch = false;
        }

        if (!STATE.isReading) return;

        const audio = new Audio(audioUrl);
        audio.playbackRate = STATE.rate || 1.0;
        audio.volume = STATE.volume !== undefined ? STATE.volume : 1.0;
        STATE._currentAudio = audio;

        audio.onplay = () => {
            if (window.DocReaderUI) {
                window.DocReaderUI.updateStatus('reading', 'Reading (Hecos Local)...');
            }
            // Pre-fetch next sentence in background without invasive UI
            prefetchNextSentence(index + 1);
        };

        audio.onended = () => {
            STATE._currentAudio = null;
            if (onEnd) onEnd(false);
        };

        audio.onerror = (e) => {
            console.warn('[DocReader] Audio play error:', e);
            STATE._currentAudio = null;
            if (onEnd) onEnd(false);
        };

        audio.play().catch(err => {
            console.warn('[DocReader] Play error:', err);
            STATE._currentAudio = null;
            if (onEnd) onEnd(false);
        });
    }

    // ── Pre-fetch Next Sentence Audio in Background ──────────────────────────
    async function prefetchNextSentence(nextIdx) {
        const STATE = _getState();
        if (nextIdx >= STATE.sentences.length) return;
        if (STATE.voiceSource !== 'hecos') return;
        const nextSentence = STATE.sentences[nextIdx];
        if (!nextSentence || !nextSentence.text) return;

        const cacheKey = window.DocReaderState ? window.DocReaderState.getAudioCacheKey(nextIdx, nextSentence) : '';
        if (STATE._audioCache.has(cacheKey)) return;
        if (STATE._prefetchSet.has(cacheKey)) return;

        STATE._prefetchSet.add(cacheKey);

        try {
            const res = await fetch('/hecos/api/plugins/document_reader/tts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: nextSentence.text,
                    preset_id: STATE.hecosPresetId || 'current',
                    engine: STATE.audioEngine || 'auto',
                    audio_preset: STATE.audioPreset || '',
                    voice: STATE.audioVoice || 'default',
                    rate: STATE.rate || 1.0
                })
            });
            if (res.ok) {
                const data = await res.json();
                if (data.ok && data.audio_url) {
                    STATE._audioCache.set(cacheKey, data.audio_url);
                }
            }
        } catch (e) {
            // Silently ignore prefetch errors
        } finally {
            STATE._prefetchSet.delete(cacheKey);
        }
    }

    // ── Read Single Word on Click ────────────────────────────────────────────
    function readSingleWord(word) {
        if (!word) return;
        const STATE = _getState();

        if (STATE.voiceSource === 'browser') {
            if (typeof speechSynthesis !== 'undefined') {
                speechSynthesis.cancel();
                const utterance = new SpeechSynthesisUtterance(word);
                utterance.rate = STATE.rate;
                utterance.pitch = STATE.pitch;
                utterance.volume = STATE.volume;
                if (STATE.selectedVoice) {
                    const voices = speechSynthesis.getVoices();
                    const v = voices.find(v => v.name === STATE.selectedVoice);
                    if (v) utterance.voice = v;
                }
                STATE.isReading = true;
                utterance.onend = () => { STATE.isReading = false; };
                utterance.onerror = () => { STATE.isReading = false; };
                speechSynthesis.speak(utterance);
            }
        } else {
            if (STATE._currentAudio) {
                try { STATE._currentAudio.pause(); } catch (e) {}
                STATE._currentAudio = null;
            }
            STATE.isReading = true;
            fetch('/hecos/api/plugins/document_reader/tts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: word,
                    preset_id: STATE.hecosPresetId || 'current',
                    engine: STATE.audioEngine || 'auto',
                    audio_preset: STATE.audioPreset || '',
                    voice: STATE.audioVoice || 'default',
                    rate: STATE.rate || 1.0
                })
            })
            .then(r => r.json())
            .then(data => {
                if (data.ok && data.audio_url) {
                    const audio = new Audio(data.audio_url);
                    audio.playbackRate = STATE.rate || 1.0;
                    audio.volume = STATE.volume !== undefined ? STATE.volume : 1.0;
                    STATE._currentAudio = audio;
                    audio.onended = () => { STATE._currentAudio = null; STATE.isReading = false; };
                    audio.onerror = () => { STATE._currentAudio = null; STATE.isReading = false; };
                    audio.play().catch(e => { STATE.isReading = false; console.warn(e); });
                } else {
                    STATE.isReading = false;
                }
            })
            .catch(e => {
                STATE.isReading = false;
                console.warn('[DocReader] Word TTS error:', e);
            });
        }
    }

    // ── Read Selected Text ───────────────────────────────────────────────────
    function readSelection() {
        const STATE = _getState();
        const text = STATE._selectedText;
        if (!text) return;

        if (window.DocReader) window.DocReader.stop();
        STATE.isReading = true;

        if (STATE.voiceSource === 'browser') {
            if (typeof speechSynthesis !== 'undefined') {
                const utterance = new SpeechSynthesisUtterance(text);
                utterance.rate = STATE.rate;
                utterance.pitch = STATE.pitch;
                utterance.volume = STATE.volume;
                if (STATE.selectedVoice) {
                    const voices = speechSynthesis.getVoices();
                    const v = voices.find(v => v.name === STATE.selectedVoice);
                    if (v) utterance.voice = v;
                }
                utterance.onstart = () => {
                    if (window.DocReaderUI) window.DocReaderUI.updateStatus('reading', 'Reading selection...');
                };
                utterance.onend = () => {
                    STATE.isReading = false;
                    if (window.DocReaderUI) window.DocReaderUI.updateStatus('ready', 'Ready');
                };
                utterance.onerror = () => {
                    STATE.isReading = false;
                    if (window.DocReaderUI) window.DocReaderUI.updateStatus('ready', 'Ready');
                };
                speechSynthesis.speak(utterance);
            }
        } else {
            const engineKey = window.DocReaderState ? window.DocReaderState.getCurrentEngineKey() : '';
            const isCold = !STATE._loadedEngines.has(engineKey) || STATE._pendingEngineSwitch;
            if (isCold && window.DocReaderState) {
                window.DocReaderState.startColdLoadTracker();
            } else if (window.DocReaderUI) {
                window.DocReaderUI.updateStatus('reading', 'Reading selection (Hecos Local)...');
            }

            fetch('/hecos/api/plugins/document_reader/tts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: text,
                    preset_id: STATE.hecosPresetId || 'current',
                    engine: STATE.audioEngine || 'auto',
                    audio_preset: STATE.audioPreset || '',
                    voice: STATE.audioVoice || 'default',
                    rate: STATE.rate || 1.0
                })
            })
            .then(r => r.json())
            .then(data => {
                if (data.ok && data.audio_url) {
                    if (isCold && window.DocReaderState) {
                        STATE._loadedEngines.add(engineKey);
                        STATE._pendingEngineSwitch = false;
                        window.DocReaderState.completeColdLoadTracker();
                    }
                    const audio = new Audio(data.audio_url);
                    audio.playbackRate = STATE.rate || 1.0;
                    audio.volume = STATE.volume !== undefined ? STATE.volume : 1.0;
                    STATE._currentAudio = audio;
                    audio.onplay = () => {
                        if (window.DocReaderUI) window.DocReaderUI.updateStatus('reading', 'Reading selection (Hecos Local)...');
                    };
                    audio.onended = () => {
                        STATE._currentAudio = null;
                        STATE.isReading = false;
                        if (window.DocReaderUI) window.DocReaderUI.updateStatus('ready', 'Ready');
                    };
                    audio.onerror = () => {
                        STATE._currentAudio = null;
                        STATE.isReading = false;
                        if (window.DocReaderUI) window.DocReaderUI.updateStatus('ready', 'Ready');
                    };
                    audio.play().catch(e => { STATE.isReading = false; console.warn(e); });
                } else {
                    STATE.isReading = false;
                    if (isCold && window.DocReaderState) window.DocReaderState.errorColdLoadTracker();
                    if (window.DocReaderUI) window.DocReaderUI.updateStatus('error', 'Synthesis failed');
                }
            })
            .catch(err => {
                STATE.isReading = false;
                if (isCold && window.DocReaderState) window.DocReaderState.errorColdLoadTracker();
                console.error('[DocReader] Selection TTS error:', err);
                if (window.DocReaderUI) window.DocReaderUI.updateStatus('error', 'Synthesis error');
            });
        }

        const tooltip = document.getElementById('docreader-selection-tooltip');
        if (tooltip) tooltip.classList.remove('visible');
    }

    // ── Stop Audio Playback ───────────────────────────────────────────────────
    function stopAudio() {
        const STATE = _getState();
        if (typeof speechSynthesis !== 'undefined') {
            speechSynthesis.cancel();
        }
        if (STATE._currentAudio) {
            try {
                STATE._currentAudio.pause();
                STATE._currentAudio.currentTime = 0;
            } catch (e) {}
            STATE._currentAudio = null;
        }
        STATE.utterance = null;
    }

    window.DocReaderAudio = {
        speakSentence,
        speakWithWebSpeech,
        speakWithHecosLocal,
        prefetchNextSentence,
        readSingleWord,
        readSelection,
        stopAudio
    };

})();
