/**
 * ca_kokoro_clones.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Dedicated frontend module for Kokoro Voice Cloning & Custom Style Management.
 * Completely isolated from ca_tts_utils.js and other monolithic files.
 * ─────────────────────────────────────────────────────────────────────────────
 */

(function () {
    'use strict';

    // ── Helper: Safe Fetch JSON ──────────────────────────────────────────────
    async function fetchJson(url, options = {}) {
        const res = await fetch(url, options);
        if (!res.ok) {
            let msg = `HTTP ${res.status}`;
            try {
                const errData = await res.json();
                if (errData && errData.error) msg = errData.error;
            } catch (_) {}
            throw new Error(msg);
        }
        return await res.json();
    }

    // ── Helper: Format Language Badge ─────────────────────────────────────────
    function getLangBadge(langPrefix) {
        const p = (langPrefix || '').toLowerCase();
        const map = {
            'af': { label: 'EN-US · Female', color: 'rgba(156, 39, 176, 0.2)', text: '#ce93d8' },
            'am': { label: 'EN-US · Male', color: 'rgba(0, 188, 212, 0.2)', text: '#80deea' },
            'bf': { label: 'EN-GB · Female', color: 'rgba(76, 175, 80, 0.2)', text: '#a5d6a7' },
            'bm': { label: 'EN-GB · Male', color: 'rgba(139, 195, 74, 0.2)', text: '#c5e1a5' },
            'if': { label: 'IT · Female', color: 'rgba(233, 30, 99, 0.2)', text: '#f48fb1' },
            'im': { label: 'IT · Male', color: 'rgba(33, 150, 243, 0.2)', text: '#90caf9' },
            'ef': { label: 'ES · Female', color: 'rgba(255, 152, 0, 0.2)', text: '#ffcc80' },
            'em': { label: 'ES · Male', color: 'rgba(255, 87, 34, 0.2)', text: '#ffab91' },
            'ff': { label: 'FR · Female', color: 'rgba(103, 58, 183, 0.2)', text: '#b39ddb' },
            'fm': { label: 'FR · Male', color: 'rgba(63, 81, 181, 0.2)', text: '#9fa8da' },
            'jf': { label: 'JA · Female', color: 'rgba(233, 30, 99, 0.2)', text: '#f48fb1' },
            'jm': { label: 'JA · Male', color: 'rgba(33, 150, 243, 0.2)', text: '#90caf9' },
            'zf': { label: 'ZH · Female', color: 'rgba(244, 67, 54, 0.2)', text: '#ef9a9a' },
            'zm': { label: 'ZH · Male', color: 'rgba(0, 150, 136, 0.2)', text: '#80cbc4' }
        };
        const item = map[p] || { label: p.toUpperCase(), color: 'rgba(255, 255, 255, 0.1)', text: 'var(--text)' };
        return `<span class="badge-pill" style="font-size:10px; background:${item.color}; color:${item.text}; border:1px solid rgba(255,255,255,0.1); padding:2px 6px;">${item.label}</span>`;
    }

    // ── Load Audio Sources (assets/voice_clones) ──────────────────────────────
    window.loadKokoroCloneSources = async function () {
        const select = document.getElementById('kokoro-clone-source-select');
        if (!select) return;

        try {
            select.innerHTML = '<option value="">Loading audio files...</option>';
            const data = await fetchJson('/api/audio/kokoro/clones/sources');
            const sources = data.sources || [];

            select.innerHTML = '';
            if (sources.length === 0) {
                select.innerHTML = '<option value="">No WAV files found in assets/voice_clones</option>';
                return;
            }

            select.innerHTML = '<option value="">-- Select Reference WAV Audio Track --</option>';
            sources.forEach(src => {
                const opt = document.createElement('option');
                opt.value = src.filename;
                const sizeKb = src.size_kb !== undefined ? Math.round(src.size_kb) : Math.round((src.size || src.size_bytes || 0) / 1024);
                opt.textContent = `${src.filename} (${sizeKb} KB)`;
                select.appendChild(opt);
            });
        } catch (err) {
            console.error('[KokoroClones] Error loading sources:', err);
            select.innerHTML = `<option value="">Error: ${err.message}</option>`;
        }
    };

    // ── Handle Source Selection Change ────────────────────────────────────────
    window.onKokoroCloneSourceChange = function () {
        const select = document.getElementById('kokoro-clone-source-select');
        const nameInput = document.getElementById('kokoro-clone-name-input');
        const titleInput = document.getElementById('kokoro-clone-title-input');
        const langSelect = document.getElementById('kokoro-clone-lang-select');
        if (!select || !select.value) return;

        const raw = select.value.replace(/\.[^/.]+$/, ''); // strip .wav
        const cleanName = raw.toLowerCase().replace(/[^a-z0-9_]/g, '_').replace(/^_+|_+$/g, '');

        if (nameInput) {
            nameInput.value = cleanName;
        }

        if (titleInput && (!titleInput.value || titleInput.value.trim() === '')) {
            // Formatted title e.g. "Cine Witch"
            const pretty = cleanName.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
            titleInput.value = pretty;
        }

        // Smart gender detection heuristic
        if (langSelect) {
            const lower = raw.toLowerCase();
            const isMale = lower.includes('man') || lower.includes('male') || lower.includes('deep') || lower.includes('guy') || lower.includes('boy') || lower.includes('uomo');
            const isFemale = lower.includes('woman') || lower.includes('female') || lower.includes('witch') || lower.includes('girl') || lower.includes('lady') || lower.includes('donna');

            if (isMale) {
                if (langSelect.value === 'af') langSelect.value = 'am';
                else if (langSelect.value === 'bf') langSelect.value = 'bm';
                else if (langSelect.value === 'if') langSelect.value = 'im';
                else if (langSelect.value === 'ef') langSelect.value = 'em';
                else if (langSelect.value === 'ff') langSelect.value = 'fm';
            } else if (isFemale) {
                if (langSelect.value === 'am') langSelect.value = 'af';
                else if (langSelect.value === 'bm') langSelect.value = 'bf';
                else if (langSelect.value === 'im') langSelect.value = 'if';
                else if (langSelect.value === 'em') langSelect.value = 'ef';
                else if (langSelect.value === 'fm') langSelect.value = 'ff';
            }
            window.onKokoroCloneLangChange();
        }

        window.updateKokoroCloneVoiceIdPreview();
    };

    // ── Handle Language / Prefix Change ───────────────────────────────────────
    window.onKokoroCloneLangChange = function () {
        const langSelect = document.getElementById('kokoro-clone-lang-select');
        const prefixBadge = document.getElementById('kokoro-clone-prefix-badge');
        if (!langSelect || !prefixBadge) return;

        const val = langSelect.value || 'af';
        prefixBadge.textContent = `${val}_`;
        window.updateKokoroCloneVoiceIdPreview();
    };

    // ── Update Full Voice ID Preview ─────────────────────────────────────────
    window.updateKokoroCloneVoiceIdPreview = function () {
        const langSelect = document.getElementById('kokoro-clone-lang-select');
        const nameInput = document.getElementById('kokoro-clone-name-input');
        const codeEl = document.getElementById('kokoro-clone-target-code');
        if (!codeEl) return;

        const prefix = (langSelect ? langSelect.value : 'af') + '_';
        const rawName = (nameInput ? nameInput.value : '').toLowerCase().replace(/[^a-z0-9_]/g, '_');
        codeEl.textContent = prefix + (rawName || 'voice_name');
    };

    // ── Convert WAV to Kokoro .pt Style Tensor ────────────────────────────────
    window.convertKokoroClone = async function () {
        const select = document.getElementById('kokoro-clone-source-select');
        const nameInput = document.getElementById('kokoro-clone-name-input');
        const langSelect = document.getElementById('kokoro-clone-lang-select');
        const titleInput = document.getElementById('kokoro-clone-title-input');
        const btn = document.getElementById('btn-kokoro-convert');
        const statusEl = document.getElementById('kokoro-clone-status');

        const wavFilename = select ? select.value : '';
        const customName = nameInput ? nameInput.value.trim() : '';
        const langPrefix = langSelect ? langSelect.value : 'af';
        const displayTitle = titleInput ? titleInput.value.trim() : '';
        const prosodySelect = document.getElementById('kokoro-clone-prosody-select');
        const prosodyMode = prosodySelect ? prosodySelect.value : 'auto';

        if (!wavFilename) {
            alert('Please select a reference WAV audio track to clone.');
            return;
        }
        if (!customName) {
            alert('Please enter a valid voice identifier.');
            if (nameInput) nameInput.focus();
            return;
        }

        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Extracting style tensor...';
        }
        if (statusEl) {
            statusEl.innerHTML = '<span style="color:var(--accent);"><i class="fas fa-spinner fa-spin"></i> Processing zero-shot StyleTTS 2 style embedding...</span>';
        }

        try {
            const res = await fetchJson('/api/audio/kokoro/clones/convert', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    wav_filename: wavFilename,
                    custom_name: customName,
                    lang_prefix: langPrefix,
                    display_title: displayTitle,
                    prosody_mode: prosodyMode
                })
            });

            if (res.ok) {
                if (statusEl) {
                    statusEl.innerHTML = `<span style="color:var(--green, #2ecc71);"><i class="fas fa-check-circle"></i> Voice pack <b>${res.voice_id}</b> successfully created!</span>`;
                }

                // Refresh installed list & main dropdown
                await window.loadKokoroInstalledClones();
                await window.reloadKokoroVoicesDropdown(res.voice_id);
            } else {
                throw new Error(res.error || 'Style extraction failed.');
            }
        } catch (err) {
            console.error('[KokoroClones] Conversion failed:', err);
            if (statusEl) {
                statusEl.innerHTML = `<span style="color:var(--danger, #e74c3c);"><i class="fas fa-exclamation-triangle"></i> ${err.message}</span>`;
            }
            alert(`Kokoro style extraction failed: ${err.message}`);
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-bolt"></i> Extract Style Embedding (.pt)';
            }
        }
    };

    // ── Load Installed Custom Kokoro Voices ───────────────────────────────────
    window.loadKokoroInstalledClones = async function () {
        const listEl = document.getElementById('kokoro-clones-list');
        const countEl = document.getElementById('kokoro-clones-count');
        if (!listEl) return;

        try {
            const data = await fetchJson('/api/audio/kokoro/clones/installed');
            const voices = data.voices || [];

            if (countEl) countEl.textContent = voices.length;

            if (voices.length === 0) {
                listEl.innerHTML = `
                    <div style="text-align:center; padding:18px; color:var(--muted); font-size:11px; border:1px dashed var(--border); border-radius:6px; background:rgba(0,0,0,0.1);">
                        <i class="fas fa-info-circle" style="color:var(--accent); font-size:14px; margin-bottom:6px; display:block;"></i>
                        No custom voice packs (.pt) installed yet.<br>
                        Select a reference audio track above and click <b>Extract Style Embedding (.pt)</b>.
                    </div>`;
                return;
            }

            listEl.innerHTML = '';
            const currentActiveVoice = (document.getElementById('v-kokoro-voice')?.value || window.audioConfig?.kokoro?.voice || '').trim();
            const currentBlendVoice = (document.getElementById('v-kokoro-blend-voice')?.value || window.audioConfig?.kokoro?.blend_voice || '').trim();

            voices.forEach(v => {
                const item = document.createElement('div');
                item.className = 'kokoro-clone-item';
                const isActive = (v.voice_id === currentActiveVoice);
                const isBlend = (v.voice_id === currentBlendVoice);

                const activeBorder = isActive ? 'border: 1px solid var(--accent); background: rgba(0, 180, 216, 0.08);' : (isBlend ? 'border: 1px solid rgba(46, 204, 113, 0.6); background: rgba(46, 204, 113, 0.06);' : 'background:var(--bg3); border:1px solid var(--border);');
                item.style.cssText = `${activeBorder} border-radius:6px; padding:10px 12px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; transition:all 0.2s;`;

                const langBadge = getLangBadge(v.lang_prefix);
                const title = v.display_title || v.voice_id;
                const sizeKb = v.size_kb !== undefined ? Math.round(v.size_kb) : Math.round((v.size || v.size_bytes || 0) / 1024);

                let statusBadges = '';
                if (isActive) {
                    statusBadges += '<span class="badge-pill badge-ok" style="font-size:9px; margin-left:4px;"><i class="fas fa-check-circle"></i> Primary Voice</span>';
                }
                if (isBlend) {
                    statusBadges += '<span class="badge-pill badge-accent" style="font-size:9px; margin-left:4px;"><i class="fas fa-layer-group"></i> Blend Voice</span>';
                }

                const primaryBtnHtml = isActive
                    ? `<button type="button" class="btn btn-primary btn-sm" disabled style="padding:4px 10px; font-size:11px; opacity:0.95; background:var(--green, #2ecc71); border-color:var(--green, #2ecc71); cursor:default;"><i class="fas fa-check-circle"></i> Active</button>`
                    : `<button type="button" class="btn btn-secondary btn-sm" onclick="setKokoroActiveVoice('${v.voice_id}')" title="Set as Primary Voice for Kokoro" style="padding:4px 10px; font-size:11px;"><i class="fas fa-check"></i> Set Active</button>`;

                const blendBtnHtml = isBlend
                    ? `<button type="button" class="btn btn-primary btn-sm" disabled style="padding:4px 8px; font-size:11px; opacity:0.95; background:var(--accent); border-color:var(--accent); cursor:default;"><i class="fas fa-layer-group"></i> Blended</button>`
                    : `<button type="button" class="btn btn-secondary btn-sm" onclick="setKokoroBlendVoice('${v.voice_id}')" title="Set as Secondary Voice for Blending / Mix" style="padding:4px 8px; font-size:11px;"><i class="fas fa-layer-group"></i> Blend</button>`;

                item.innerHTML = `
                    <div style="display:flex; align-items:center; gap:10px; min-width:220px; flex:1;">
                        <div style="width:34px; height:34px; border-radius:6px; background:rgba(0,180,216,0.12); border:1px solid rgba(0,180,216,0.25); display:flex; align-items:center; justify-content:center; color:var(--accent);">
                            <i class="fas fa-user-astronaut"></i>
                        </div>
                        <div>
                            <div style="display:flex; align-items:center; gap:6px; flex-wrap:wrap;">
                                <span style="font-weight:600; font-size:12px; color:var(--text);">${title}</span>
                                ${langBadge}
                                ${statusBadges}
                            </div>
                            <div style="font-size:10px; color:var(--muted); font-family:monospace; margin-top:2px;">
                                ID: <span style="color:var(--accent);">${v.voice_id}</span> · From: <span>${v.source_wav || 'Audio'}</span> (${sizeKb} KB)
                            </div>
                        </div>
                    </div>

                    <div style="display:flex; gap:6px; align-items:center;">
                        <button type="button" class="btn btn-secondary btn-sm" id="btn-kokoro-prev-${v.voice_id}" onclick="previewKokoroClone('${v.voice_id}')" title="Synthesize instant speech sample with this voice style" style="padding:4px 10px; font-size:11px;">
                            <i class="fas fa-play"></i> Preview
                        </button>
                        ${primaryBtnHtml}
                        ${blendBtnHtml}
                        <button type="button" class="btn btn-danger btn-sm" onclick="deleteKokoroClone('${v.voice_id}')" title="Delete this voice pack (.pt and .json)" style="padding:4px 8px; font-size:11px;">
                            <i class="fas fa-trash-alt"></i>
                        </button>
                    </div>
                `;

                listEl.appendChild(item);
            });
        } catch (err) {
            console.error('[KokoroClones] Error loading installed voices:', err);
            listEl.innerHTML = `<div style="color:var(--danger); padding:10px; font-size:11px;">Error loading voices: ${err.message}</div>`;
        }
    };

    // ── Preview Custom Voice with Kokoro TTS ──────────────────────────────────
    window.previewKokoroClone = async function (voiceId) {
        if (!voiceId) return;
        const btn = document.getElementById(`btn-kokoro-prev-${voiceId}`);
        const audioEl = document.getElementById('kokoro-preview-audio');

        let origHtml = '';
        if (btn) {
            origHtml = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        }

        try {
            // Text sample based on language prefix
            let text = "Hello! This is a voice test using the new cloned Kokoro custom voice style.";
            if (voiceId.startsWith('i')) {
                text = "Ciao! Questo è un test vocale con il nuovo timbro clonato per Kokoro.";
            } else if (voiceId.startsWith('e')) {
                text = "¡Hola! Esta es una prueba de voz con el nuevo estilo clonado para Kokoro.";
            } else if (voiceId.startsWith('f')) {
                text = "Bonjour! Ceci est un test vocal avec la nouvelle voix clonée pour Kokoro.";
            }

            const data = await fetchJson('/api/audio/kokoro/clones/preview', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ voice_id: voiceId, text: text })
            });

            if (data.ok && data.url) {
                if (audioEl) {
                    audioEl.src = data.url;
                    await audioEl.play();
                } else {
                    const audio = new Audio(data.url);
                    await audio.play();
                }
            } else {
                throw new Error(data.error || 'Preview generation failed.');
            }
        } catch (err) {
            console.error('[KokoroClones] Preview error:', err);
            alert(`Preview error for voice ${voiceId}: ${err.message}`);
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = origHtml || '<i class="fas fa-play"></i> Preview';
            }
        }
    };

    // ── Set Voice as Active Kokoro Default Voice ──────────────────────────────
    window.setKokoroActiveVoice = async function (voiceId) {
        if (!voiceId) return;
        const select = document.getElementById('v-kokoro-voice');
        if (select) {
            let optFound = false;
            for (let i = 0; i < select.options.length; i++) {
                if (select.options[i].value === voiceId) {
                    select.selectedIndex = i;
                    optFound = true;
                    break;
                }
            }

            if (!optFound) {
                const opt = document.createElement('option');
                opt.value = voiceId;
                opt.textContent = `🎭 ${voiceId} (Custom Cloned)`;
                select.appendChild(opt);
                select.value = voiceId;
            }

            // Trigger change event so any listeners pick it up
            select.dispatchEvent(new Event('change', { bubbles: true }));

            // Flash green feedback
            const prevBorder = select.style.borderColor;
            select.style.borderColor = 'var(--green, #2ecc71)';
            setTimeout(() => { select.style.borderColor = prevBorder; }, 1500);
        }

        // Update in-memory audioConfig
        if (!window.audioConfig) window.audioConfig = {};
        if (!window.audioConfig.kokoro) window.audioConfig.kokoro = {};
        window.audioConfig.kokoro.voice = voiceId;
        if (typeof audioConfig !== 'undefined' && audioConfig) {
            if (!audioConfig.kokoro) audioConfig.kokoro = {};
            audioConfig.kokoro.voice = voiceId;
        }

        // Sync blend voice dropdown options and resulting voice display
        if (typeof window.syncKokoroBlendVoiceOptions === 'function') {
            window.syncKokoroBlendVoiceOptions();
        }
        if (typeof window.onKokoroBlendVoiceChange === 'function') {
            window.onKokoroBlendVoiceChange();
        }

        // Persist to disk
        if (typeof window.saveAudioConfig === 'function') {
            await window.saveAudioConfig();
        } else if (typeof window.saveConfig === 'function') {
            await window.saveConfig(true);
        }

        // Refresh installed list to reflect active badge
        await window.loadKokoroInstalledClones();

        if (window.showToast) {
            window.showToast(`Kokoro primary voice set to '${voiceId}'!`, 'success');
        }
    };

    // ── Set Voice as Secondary Kokoro Blend Voice (Mix) ───────────────────────
    window.setKokoroBlendVoice = async function (voiceId) {
        if (!voiceId) return;
        const select = document.getElementById('v-kokoro-blend-voice');
        if (select) {
            let optFound = false;
            for (let i = 0; i < select.options.length; i++) {
                if (select.options[i].value === voiceId) {
                    select.selectedIndex = i;
                    optFound = true;
                    break;
                }
            }

            if (!optFound) {
                const opt = document.createElement('option');
                opt.value = voiceId;
                opt.textContent = `🎭 ${voiceId} (Custom Cloned)`;
                select.appendChild(opt);
                select.value = voiceId;
            }

            select.dispatchEvent(new Event('change', { bubbles: true }));

            const prevBorder = select.style.borderColor;
            select.style.borderColor = 'var(--accent, #00b4d8)';
            setTimeout(() => { select.style.borderColor = prevBorder; }, 1500);
        }

        if (!window.audioConfig) window.audioConfig = {};
        if (!window.audioConfig.kokoro) window.audioConfig.kokoro = {};
        window.audioConfig.kokoro.blend_voice = voiceId;
        if (typeof audioConfig !== 'undefined' && audioConfig) {
            if (!audioConfig.kokoro) audioConfig.kokoro = {};
            audioConfig.kokoro.blend_voice = voiceId;
        }

        if (typeof window.onKokoroBlendVoiceChange === 'function') {
            window.onKokoroBlendVoiceChange();
        }

        if (typeof window.saveAudioConfig === 'function') {
            await window.saveAudioConfig();
        } else if (typeof window.saveConfig === 'function') {
            await window.saveConfig(true);
        }

        await window.loadKokoroInstalledClones();

        if (window.showToast) {
            window.showToast(`Secondary blend voice set to '${voiceId}'!`, 'success');
        }
    };

    // ── Delete Custom Voice (.pt & .json) ─────────────────────────────────────
    window.deleteKokoroClone = async function (voiceId) {
        if (!voiceId) return;
        const confirmMsg = `Are you sure you want to delete custom voice "${voiceId}"?\nThe .pt and .json files will be permanently removed from hecos/models/kokoro/voices.`;
        if (!confirm(confirmMsg)) return;

        try {
            const res = await fetchJson('/api/audio/kokoro/clones/delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ voice_id: voiceId })
            });

            if (res.ok) {
                await window.reloadKokoroVoicesDropdown();
                await window.loadKokoroInstalledClones();
                if (window.showToast) {
                    window.showToast(`Voice '${voiceId}' deleted.`, 'info');
                }
            } else {
                throw new Error(res.error || 'Could not delete voice pack.');
            }
        } catch (err) {
            console.error('[KokoroClones] Delete error:', err);
            alert(`Deletion error: ${err.message}`);
        }
    };

    // ── Open Folders in Windows Explorer ──────────────────────────────────────
    window.openKokoroClonesFolder = async function (target = 'sources') {
        try {
            await fetchJson('/api/audio/kokoro/clones/open-folder', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target: target })
            });
        } catch (err) {
            console.warn('[KokoroClones] Open folder:', err);
        }
    };

    // ── Refresh All Sources & Clones ──────────────────────────────────────────
    window.refreshKokoroClonesAll = async function () {
        await Promise.all([
            window.loadKokoroCloneSources(),
            window.reloadKokoroVoicesDropdown(),
            window.loadKokoroInstalledClones()
        ]);
    };

    // ── Dynamically Reload Main Kokoro Voice Select Dropdown ──────────────────
    window.reloadKokoroVoicesDropdown = async function (selectVoiceId = null) {
        const sel = document.getElementById('v-kokoro-voice');
        if (!sel) return;

        try {
            const res = await fetchJson('/api/audio/voices?engine=kokoro');
            const voiceMap = (!Array.isArray(res) && res.kokoro) ? res.kokoro : res;
            const keys = Array.isArray(voiceMap) ? voiceMap : Object.keys(voiceMap);

            if (keys.length > 0) {
                const currentVal = selectVoiceId || sel.value || (window.audioConfig?.kokoro?.voice) || 'af_heart';
                sel.innerHTML = '';
                keys.forEach(k => {
                    const opt = document.createElement('option');
                    opt.value = k;
                    opt.textContent = (!Array.isArray(voiceMap) && voiceMap[k]) ? voiceMap[k] : k;
                    sel.appendChild(opt);
                });
                if (currentVal) sel.value = currentVal;
            }
            if (typeof window.syncKokoroBlendVoiceOptions === 'function') {
                window.syncKokoroBlendVoiceOptions();
            }
            if (typeof window.onKokoroBlendVoiceChange === 'function') {
                window.onKokoroBlendVoiceChange();
            }
        } catch (err) {
            console.warn('[KokoroClones] Failed to reload voices dropdown:', err);
        }
    };

    // ── Auto-Initialization ───────────────────────────────────────────────────
    async function initKokoroClones() {
        if (document.getElementById('kokoro-cloning-container')) {
            window.loadKokoroCloneSources();
            await window.reloadKokoroVoicesDropdown();
            await window.loadKokoroInstalledClones();
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initKokoroClones);
    } else {
        setTimeout(initKokoroClones, 50);
    }

})();
