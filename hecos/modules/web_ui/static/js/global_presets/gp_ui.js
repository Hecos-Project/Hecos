/* ⚡ SOUL FORGE: gp_ui.js — Unified Panel UI, Diff Engine & Topbar Sync */

window.sfTogglePanel = function(force) {
    const panel = document.getElementById('soul-forge-panel');
    const overlay = document.getElementById('soul-forge-overlay');
    if (!panel || !overlay) return;
    const isOpen = panel.classList.contains('open');
    
    const shouldOpen = force !== undefined ? force : !isOpen;
    
    if (shouldOpen) {
        try {
            const audio = new Audio('/assets/sounds/beep-6.mp3');
            audio.volume = 1.0;
            audio.play().catch(() => {});
        } catch(e) {}

        window.sfUpdateFallbackLabels();
        panel.style.display = 'flex';
        panel.classList.add('open');
        overlay.style.display = 'block';
        window.sfLoadData();
    } else {
        panel.classList.remove('open');
        panel.style.display = 'none';
        overlay.style.display = 'none';
        if (window.sfCloseModelPicker) window.sfCloseModelPicker();
        if (window.sfStopVoicePreview) window.sfStopVoicePreview();
    }
};

// Backwards-compatible alias for any callers invoking window.soTogglePanel
window.soTogglePanel = window.sfTogglePanel;

window.sfToggleDrawer = function(drawerId, btnEl) {
    const drawer = document.getElementById(drawerId);
    if (!drawer) return;
    const isHidden = drawer.style.display === 'none' || !drawer.style.display;
    drawer.style.display = isHidden ? 'block' : 'none';
    if (btnEl) {
        btnEl.classList.toggle('open', isHidden);
    }
};

window.sfUpdateFallbackLabels = async function() {
    try {
        const [cfgRes, audRes] = await Promise.all([
            fetch('/hecos/config'),
            fetch('/api/audio/config')
        ]);
        
        let bType = 'unknown';
        let bModel = 'unknown';
        let pName = 'unknown';
        
        if (cfgRes.ok) {
            const cfg = await cfgRes.json();
            window.HecosSystemConfig = cfg;
            pName = cfg.ai?.active_personality || 'unknown';
            
            bType = cfg.backend?.type || 'ollama';
            if (bType === 'hybrid') {
                bType = cfg.backend?.active_model_source || 'cloud';
            }
            if (cfg.backend) {
                if (bType === 'ollama') bModel = cfg.backend.ollama?.model || 'unknown';
                else if (bType === 'cloud') bModel = cfg.backend.cloud?.model || 'unknown';
                else if (bType === 'kobold') bModel = cfg.backend.kobold?.model || 'unknown';
                else if (bType === 'llama_cpp') bModel = cfg.backend.llama_cpp?.model || 'unknown';
            }
        }
        
        let tEngine = 'unknown';
        let tVoice = 'unknown';
        if (audRes.ok) {
            const audRaw = await audRes.json();
            const aud = audRaw.config || {};
            tEngine = aud.active_engine || 'piper';
            if (tEngine === 'piper') {
                tVoice = aud.onnx_model ? aud.onnx_model.replace('.onnx', '').split(/[\\/]/).pop() : 'unknown';
            } else if (tEngine === 'kokoro') {
                tVoice = aud.kokoro?.voice || 'unknown';
            } else if (tEngine === 'xtts2') {
                tVoice = aud.xtts?.speaker || 'unknown';
            } else if (tEngine === 'fish_speech') {
                tVoice = aud.fish_speech?.reference_audio || 'default';
            }
        }
        
        window.sfSystemFallbacks = {
            persona: pName,
            backend: bType,
            model: bModel,
            tts_engine: tEngine,
            tts_voice: tVoice
        };
        window.soSystemFallbacks = window.sfSystemFallbacks;
        
    } catch (e) {
        console.error("Failed to fetch system fallbacks for Soul Forge UI", e);
    }
};

window.sfComputeDiff = function() {
    const base = window.sfState.baselineState;
    const result = { total: 0, instructions: false, inference: false, voice: false, payload: false, model: false, persona: false };
    if (!base) return result;

    const curr = window.sfCollectUIState();
    const eq = (a, b) => {
        if ((a === null || a === undefined || a === "") && (b === null || b === undefined || b === "")) return true;
        if (typeof a === 'number' && typeof b === 'number') return Math.abs(a - b) < 0.001;
        return a === b;
    };

    if (!eq(curr.persona?.soul_file, base.persona?.soul_file)) { result.persona = true; result.total++; }
    for (const k of ['use_global_direct_instructions', 'use_global_safety_instructions', 'custom_instructions', 'user_notes', 'send_notes_to_ai']) {
        if (!eq(curr.persona?.[k], base.persona?.[k])) { result.instructions = true; result.total++; }
    }
    for (const k of ['backend_type', 'model_name']) {
        if (!eq(curr.model?.[k], base.model?.[k])) { result.model = true; result.total++; }
    }
    for (const k of ['preset_name', 'temperature', 'top_p', 'repeat_penalty', 'num_predict', 'num_ctx', 'n_gpu_layers']) {
        if (!eq(curr.inference?.[k], base.inference?.[k])) { result.inference = true; result.total++; }
    }
    for (const k of ['send_tools', 'send_personality', 'send_memory', 'include_thinking_in_history']) {
        if (!eq(curr.payload?.[k], base.payload?.[k])) { result.payload = true; result.total++; }
    }
    const voiceKeys = [
        'tts_engine', 'tts_voice',
        'xtts_preset', 'xtts_inference_preset', 'xtts_speaker_wav', 'xtts_temperature', 'xtts_speed', 'xtts_top_k', 'xtts_repetition_penalty', 'xtts_top_p', 'xtts_length_penalty',
        'fish_preset', 'fish_inference_preset', 'fish_reference_audio', 'fish_temperature', 'fish_top_p', 'fish_repetition_penalty', 'fish_chunk_length', 'fish_max_new_tokens',
        'kokoro_preset', 'kokoro_inference_preset', 'kokoro_blend_voice', 'kokoro_speed', 'kokoro_silence', 'kokoro_alpha', 'kokoro_beta', 'kokoro_volume'
    ];
    for (const k of voiceKeys) {
        if (!eq(curr.voice?.[k], base.voice?.[k])) { result.voice = true; result.total++; }
    }
    return result;
};

window.sfRefreshUIVisibilityAndSummaries = function() {
    // 1. Toggle TTS Engine controls visibility
    const ttsEngine = document.getElementById('sf-tts-engine-select')?.value || 'piper';
    const showEl = (id, cond) => {
        const el = document.getElementById(id);
        if (el) el.style.display = cond ? 'block' : 'none';
    };
    showEl('sf-xtts-controls', ttsEngine === 'xtts2');
    showEl('sf-xtts-fine', ttsEngine === 'xtts2');
    showEl('sf-fish-controls', ttsEngine === 'fish_speech' || ttsEngine === 'fish');
    showEl('sf-fish-fine', ttsEngine === 'fish_speech' || ttsEngine === 'fish');
    showEl('sf-kokoro-controls', ttsEngine === 'kokoro');
    showEl('sf-kokoro-fine', ttsEngine === 'kokoro');
    showEl('sf-piper-fine', ttsEngine === 'piper');

    // 2. Check and update clone / preset disabled state on voice select
    if (window.sfUpdateCloneState) window.sfUpdateCloneState();

    // 3. Update compact inline summaries
    const infSummary = document.getElementById('sf-inference-summary');
    if (infSummary) {
        const t = document.getElementById('sf-temp')?.value ?? '0.7';
        const tp = document.getElementById('sf-topp')?.value ?? '0.9';
        const ctx = document.getElementById('sf-ctx')?.value;
        const ctxStr = (!ctx || ctx == 0) ? 'Auto' : `${Math.round(ctx / 1024)}k`;
        infSummary.textContent = `Temp ${t} · TopP ${tp} · Ctx ${ctxStr}`;
    }

    const paySummary = document.getElementById('sf-payload-summary');
    if (paySummary) {
        const tOn = document.getElementById('sf-payload-tools')?.checked !== false;
        const sOn = document.getElementById('sf-payload-soul')?.checked !== false;
        const mOn = document.getElementById('sf-payload-memory')?.checked !== false;
        const thOn = document.getElementById('sf-payload-thinking')?.checked === true;
        paySummary.textContent = `Tools ${tOn ? 'ON' : 'OFF'} · Soul ${sOn ? 'ON' : 'OFF'} · Mem ${mOn ? 'ON' : 'OFF'}${thOn ? ' · <think>' : ''}`;
        // Only update the pill if not in the middle of a bulk soul populate,
        // to prevent flickering when sf-payload-tools is momentarily reset.
        if (window.updateToolModeBadge && !window._sfApplyingSoul) {
            window.updateToolModeBadge(tOn ? 'native' : 'direct');
        }
    }

    // 4. Compute diff & update status badges
    const diff = window.sfComputeDiff();
    const presetDiffersFromGlobal = (window.sfState.activeSoulId || null) !== (window.sfState.globalDefaultSoulId || null);
    window.sfState.isDirty = diff.total > 0;
    window.sfState.sessionHasDraft = diff.total > 0 || presetDiffersFromGlobal;

    const getPresetName = (id) => {
        if (!id) return 'Base Configuration';
        const found = (window.sfState.souls || []).find(s => s.meta.id === id);
        return found ? `${found.meta.icon || '⚡'} ${found.meta.name}` : id;
    };

    const chatLabel = document.getElementById('sf-chat-preset-label');
    if (chatLabel) {
        const baseName = getPresetName(window.sfState.activeSoulId);
        chatLabel.textContent = diff.total > 0 ? `${baseName} (modified)` : baseName;
    }
    const globalLabel = document.getElementById('sf-global-preset-label');
    if (globalLabel) {
        globalLabel.textContent = getPresetName(window.sfState.globalDefaultSoulId);
    }

    const badge = document.getElementById('sf-draft-badge');
    if (badge) {
        if (diff.total > 0) {
            badge.textContent = `● Live draft (${diff.total} mod.)`;
            badge.classList.add('dirty');
        } else if (presetDiffersFromGlobal) {
            badge.textContent = `● Session Preset`;
            badge.classList.add('dirty');
        } else {
            badge.textContent = `✓ Synced with Defaults`;
            badge.classList.remove('dirty');
        }
    }

    const setDot = (id, show) => {
        const d = document.getElementById(id);
        if (d) d.style.display = show ? 'inline-block' : 'none';
    };
    setDot('sf-dot-instructions', diff.instructions);
    setDot('sf-dot-inference', diff.inference);
    setDot('sf-dot-voice', diff.voice);
    setDot('sf-dot-payload', diff.payload);

    // Highlight "Aggiorna Preset" button when a preset is selected
    const topSaveBtn = document.getElementById('sf-top-save-btn');
    if (topSaveBtn) {
        topSaveBtn.disabled = !window.sfState.activeSoulId;
        topSaveBtn.style.opacity = window.sfState.activeSoulId ? '1' : '0.45';
    }

    if (window.sfUpdateTooltip) {
        window.sfUpdateTooltip(window.sfCollectUIState(), window.sfState.activeSoulId);
    }
};

window.sfSyncActivePersonaAvatar = function() {
    const pVal = document.getElementById('sf-persona-select')?.value || "";
    if (window._lastSfPersonaVal === pVal) return;
    window._lastSfPersonaVal = pVal;

    const effectivePVal = pVal || (window.sfSystemFallbacks?.persona) || "";
    if (effectivePVal && effectivePVal !== 'unknown') {
        window.HecosPersonaName = effectivePVal.replace('.yaml', '').replace(/_/g, ' ');
        fetch(`/api/persona/avatar?persona=${encodeURIComponent(effectivePVal)}`)
            .then(r => r.json())
            .then(d => { 
                if (d.ok && d.avatar_path) {
                    window.HecosAvatar = d.avatar_path;
                    window.HecosAvatarType = d.avatar_type || 'image';
                }
                if (window.HecosWelcome && window.HecosWelcome.show) window.HecosWelcome.show(true);
            })
            .catch(() => {
                if (window.HecosWelcome && window.HecosWelcome.show) window.HecosWelcome.show(true);
            });
    } else {
        window.HecosPersonaName = 'Hecos System Soul';
        window.HecosAvatar = null;
        window.HecosAvatarType = 'image';
        if (window.HecosWelcome && window.HecosWelcome.show) window.HecosWelcome.show(true);
    }
};

window.sfDirty = function() {
    window.sfRefreshUIVisibilityAndSummaries();
    window.sfSyncActivePersonaAvatar();

    // Live auto-apply to current chat session (debounced 200ms)
    clearTimeout(window._sfDraftSaveTimeout);
    window._sfDraftSaveTimeout = setTimeout(() => {
        if (window.sfSaveDraftToSession) {
            window.sfSaveDraftToSession();
        }
    }, 200);
};

window.soDirty = window.sfDirty;

window.sfSyncToTopbar = function() {
    if (window.sfUpdateTooltip) {
        window.sfUpdateTooltip(window.sfCollectUIState(), window.sfState.activeSoulId);
    }
};

window.sfUpdateSliderVal = function(el, spanId) {
    const span = document.getElementById(spanId);
    if (span && el) span.textContent = el.value;
};

window.soUpdateSliderVal = window.sfUpdateSliderVal;

window.sfPopulateDropdowns = function(optData) {
    const soulSel = document.getElementById('sf-active-soul-select');
    if (soulSel) soulSel.innerHTML = '<option value="">-- Base Configuration (No Preset) --</option>';
    
    (window.sfState.souls || []).forEach(s => {
        if (soulSel) {
            const opt = document.createElement('option');
            opt.value = s.meta.id;
            opt.textContent = `${s.meta.icon || '⚡'} ${s.meta.name}`;
            soulSel.appendChild(opt);
        }
    });
    
    const infSel = document.getElementById('sf-inference-preset-select');
    if (infSel) {
        infSel.innerHTML = '<option value="">-- No preset (Manual values / Default) --</option>';
        Object.keys(window.sfState.inferencePresets || {}).forEach(k => {
            const opt = document.createElement('option');
            opt.value = k;
            opt.textContent = k;
            infSel.appendChild(opt);
        });
    }
    
    const populatePresetSel = (id, placeholder, mapObj) => {
        const el = document.getElementById(id);
        if (!el) return;
        el.innerHTML = `<option value="">${placeholder}</option>`;
        Object.keys(mapObj || {}).forEach(k => {
            const opt = document.createElement('option');
            opt.value = k;
            opt.textContent = k;
            el.appendChild(opt);
        });
    };

    populatePresetSel('sf-xtts-preset-select', '-- No XTTS Preset --', window.sfState.xttsPresets);
    populatePresetSel('sf-fish-preset-select', '-- No Fish Preset --', window.sfState.fishSpeechPresets);
    populatePresetSel('sf-xtts-inference-preset-select', '-- No Inference Preset --', window.sfState.xttsInferencePresets);
    populatePresetSel('sf-fish-inference-preset-select', '-- No Inference Preset --', window.sfState.fishSpeechInferencePresets);
    populatePresetSel('sf-kokoro-preset-select', '-- No Kokoro Preset --', window.sfState.kokoroPresets);
    populatePresetSel('sf-kokoro-inference-preset-select', '-- No Inference Preset --', window.sfState.kokoroInferencePresets);
    
    if (optData && optData.ok) {
        const pSel = document.getElementById('sf-persona-select');
        if (pSel) {
            pSel.innerHTML = '';
            (optData.personas || []).forEach(p => {
                const opt = document.createElement('option');
                opt.value = p;
                opt.textContent = p.replace('.yaml', '');
                pSel.appendChild(opt);
            });
        }
        window.sfState.allModels = optData.models;
        window.sfUpdateModelsDropdown();
    }
};

const _SF_CAP_META = {
    thinking: {
        icon: '💭',
        label: 'Thinking',
        title: 'Thinking / Reasoning',
        desc: 'Supports internal <think> reasoning chains (controllable via Enable Thinking toggle).'
    },
    tools: {
        icon: '⚙️',
        label: 'Tools',
        title: 'Tools / Function Calling',
        desc: 'Supports structured tool calling, web search, memory & Hecos module actions.'
    },
    vision: {
        icon: '👁️',
        label: 'Vision',
        title: 'Vision / Multimodal',
        desc: 'Includes vision projector / multimodal weights for analyzing images and screenshots.'
    }
};

function _sfEscHtml(str) {
    return String(str ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function _sfFormatSizeBytes(bytes) {
    if (!bytes || bytes <= 0) return '';
    if (bytes >= 1024 * 1024 * 1024) {
        return (bytes / (1024 * 1024 * 1024)).toFixed(1) + ' GB';
    }
    return Math.round(bytes / (1024 * 1024)) + ' MB';
}

function _sfBuildModelDisplay(m) {
    const prefix = (m.type === 'cloud') ? '☁️ ' : (m.type === 'local' ? '🖥️ ' : '');
    const specParts = [];
    if (m.parameter_size) {
        let p = m.parameter_size;
        if (m.quantization_level) p += ' ' + m.quantization_level;
        specParts.push(p);
    } else if (m.quantization_level) {
        specParts.push(m.quantization_level);
    }
    const sizeHuman = _sfFormatSizeBytes(m.size_bytes);
    if (sizeHuman) specParts.push(sizeHuman.replace(' ', ''));

    const sizeTag = specParts.length ? ` [${specParts.join(' | ')}]` : '';
    const caps = Array.isArray(m.capabilities) ? m.capabilities : [];
    const icons = caps.map(c => _SF_CAP_META[c]?.icon).filter(Boolean).join('');
    const descs = caps.map(c => _SF_CAP_META[c]?.title || c).filter(Boolean);

    let tooltipText = `${m.name}${sizeTag}`;
    if (m.family) tooltipText += `\nFamily: ${m.family}`;
    if (sizeHuman) tooltipText += `\nDisk size: ${sizeHuman}`;
    if (descs.length) tooltipText += `\nCapabilities: ${descs.join(', ')}`;
    if (m.description) tooltipText += `\n${m.description}`;

    return {
        prefix,
        sizeTag,
        specCompact: specParts.join(' · '),
        sizeHuman,
        caps,
        icons,
        descs,
        tooltipText,
        optionLabel: prefix + m.name + sizeTag + (icons ? ' ' + icons : '')
    };
}

function _sfFindSelectedModel(modelId) {
    const all = window.sfState.allModels || [];
    if (!modelId) return null;
    const bType = document.getElementById('sf-backend-select')?.value;
    return (
        all.find(m => m.id === modelId && (!bType || (bType === 'cloud' ? m.type === 'cloud' : m.provider === bType))) ||
        all.find(m => m.id === modelId) ||
        null
    );
}

window.sfUpdateModelHoverCard = function(m) {
    const card = document.getElementById('sf-model-hover-card');
    if (!card) return;
    if (!m) {
        card.style.display = 'none';
        return;
    }
    const d = _sfBuildModelDisplay(m);
    const providerLabel = m.type === 'cloud'
        ? `Cloud (${m.provider || 'api'})`
        : `Local (${m.provider || 'ollama'})`;

    const specBits = [];
    if (m.family) specBits.push(`Family: ${m.family}`);
    if (m.parameter_size) specBits.push(`Params: ${m.parameter_size}`);
    if (m.quantization_level) specBits.push(`Quant: ${m.quantization_level}`);
    if (d.sizeHuman) specBits.push(`Disk: ${d.sizeHuman}`);
    if (m.context_length > 0) specBits.push(`Ctx: ${Math.round(m.context_length / 1024)}k`);
    if (m.has_projector) specBits.push('Projector: Multimodal');

    const capBadges = d.caps.map(c => {
        const meta = _SF_CAP_META[c] || { icon: '•', title: c, desc: '' };
        return `<span class="sf-mib-pill cap-${_sfEscHtml(c)}" title="${_sfEscHtml(meta.desc)}">${meta.icon} ${_sfEscHtml(meta.title)}</span>`;
    }).join('');

    card.innerHTML = `
        <div class="sf-mhc-title">
            <span>${d.prefix}${_sfEscHtml(m.name)}</span>
            <span style="font-size:10px; color:#94a3b8; font-weight:500;">${_sfEscHtml(providerLabel)}</span>
        </div>
        ${specBits.length ? `<div class="sf-mhc-specs">${_sfEscHtml(specBits.join(' · '))}</div>` : ''}
        ${capBadges ? `<div class="sf-mhc-caps">${capBadges}</div>` : `<div class="sf-mhc-specs">Standard text generation model</div>`}
    `;
    card.style.display = 'block';
};

window.sfRenderModelPickerList = function(filterText = '') {
    const listEl = document.getElementById('sf-model-picker-list');
    if (!listEl) return;
    const filtered = window.sfState.filteredModels || [];
    const curVal = document.getElementById('sf-model-select')?.value || '';
    const q = (filterText || '').trim().toLowerCase();

    const visible = q
        ? filtered.filter(m =>
            (m.name || '').toLowerCase().includes(q) ||
            (m.family || '').toLowerCase().includes(q) ||
            (m.capabilities || []).some(c => c.toLowerCase().includes(q))
        )
        : filtered;

    listEl.innerHTML = '';
    if (!visible.length) {
        listEl.innerHTML = `<div style="padding:10px; font-size:11.5px; color:var(--text-muted); text-align:center;">No models match filter</div>`;
        window.sfUpdateModelHoverCard(null);
        return;
    }

    visible.forEach(m => {
        const d = _sfBuildModelDisplay(m);
        const item = document.createElement('div');
        item.className = 'sf-mp-item' + (m.id === curVal ? ' selected' : '');
        item.setAttribute('role', 'option');
        item.setAttribute('aria-selected', m.id === curVal ? 'true' : 'false');
        item.title = d.tooltipText;

        const capIconsHtml = d.caps.map(c => {
            const meta = _SF_CAP_META[c];
            if (!meta) return '';
            return `<span title="${_sfEscHtml(meta.title + ' — ' + meta.desc)}">${meta.icon}</span>`;
        }).join('');

        item.innerHTML = `
            <div class="sf-mp-item-left">
                <span>${d.prefix.trim()}</span>
                <span class="sf-mp-item-name">${_sfEscHtml(m.name)}</span>
            </div>
            <div class="sf-mp-item-right">
                ${d.specCompact ? `<span class="sf-mp-spec-tag">${_sfEscHtml(d.specCompact)}</span>` : ''}
                ${capIconsHtml ? `<span class="sf-mp-cap-icons">${capIconsHtml}</span>` : ''}
            </div>
        `;

        item.addEventListener('mouseenter', () => {
            listEl.querySelectorAll('.sf-mp-item.sf-mp-hovered').forEach(el => el.classList.remove('sf-mp-hovered'));
            item.classList.add('sf-mp-hovered');
            window.sfUpdateModelHoverCard(m);
        });

        item.addEventListener('click', (e) => {
            e.stopPropagation();
            const mSel = document.getElementById('sf-model-select');
            if (mSel) {
                mSel.value = m.id;
            }
            window.sfCloseModelPicker();
            if (window.sfSyncModelUI) window.sfSyncModelUI();
            if (window.sfDirty) window.sfDirty();
        });

        listEl.appendChild(item);
    });

    const activeModel = visible.find(m => m.id === curVal) || visible[0];
    window.sfUpdateModelHoverCard(activeModel);
};

window.sfFilterModelPicker = function(val) {
    window.sfRenderModelPickerList(val);
};

window.sfToggleModelPicker = function(force) {
    const menu = document.getElementById('sf-model-picker-menu');
    const btn = document.getElementById('sf-model-picker-btn');
    if (!menu || !btn) return;
    const isOpen = menu.style.display !== 'none';
    const open = force !== undefined ? force : !isOpen;
    if (open) {
        const searchEl = document.getElementById('sf-model-search');
        if (searchEl) searchEl.value = '';
        window.sfRenderModelPickerList('');
        menu.style.display = 'block';
        btn.setAttribute('aria-expanded', 'true');
        if (searchEl) setTimeout(() => searchEl.focus(), 20);
    } else {
        menu.style.display = 'none';
        btn.setAttribute('aria-expanded', 'false');
    }
};

window.sfCloseModelPicker = function() {
    window.sfToggleModelPicker(false);
};

window.sfSyncModelUI = function() {
    const mSel = document.getElementById('sf-model-select');
    const labelEl = document.getElementById('sf-model-picker-label');
    const metaEl = document.getElementById('sf-model-picker-meta');
    const infoBar = document.getElementById('sf-model-info-bar');
    if (!mSel) return;

    const val = mSel.value;
    const m = _sfFindSelectedModel(val);

    if (labelEl && metaEl) {
        if (m) {
            const d = _sfBuildModelDisplay(m);
            labelEl.textContent = d.prefix + m.name;
            labelEl.title = d.tooltipText;
            const metaBadges = [];
            if (d.specCompact) metaBadges.push(`<span class="sf-mp-spec-tag">${_sfEscHtml(d.specCompact)}</span>`);
            if (d.icons) metaBadges.push(`<span class="sf-mp-cap-icons">${d.icons}</span>`);
            metaEl.innerHTML = metaBadges.join('');
        } else {
            const fallbackTxt = mSel.options[mSel.selectedIndex]?.textContent || val || '(Select model)';
            labelEl.textContent = fallbackTxt;
            labelEl.title = fallbackTxt;
            metaEl.innerHTML = '';
        }
    }

    if (infoBar) {
        if (!m) {
            infoBar.style.display = 'none';
            infoBar.innerHTML = '';
        } else {
            const d = _sfBuildModelDisplay(m);
            const pills = [];

            const provTip = m.type === 'local'
                ? `Local offline model executed via ${m.provider || 'ollama'} on your hardware.`
                : `Cloud API model via ${m.provider || 'cloud'}.`;
            const provName = m.type === 'local'
                ? `Local (${m.provider === 'llama_cpp' ? 'GGUF' : (m.provider || 'Ollama')})`
                : `Cloud (${m.provider || 'API'})`;
            pills.push(`<span class="sf-mib-pill" data-sf-tip="${_sfEscHtml(provTip)}" title="${_sfEscHtml(provTip)}">${d.prefix.trim()} ${_sfEscHtml(provName)}</span>`);

            if (m.parameter_size || m.quantization_level) {
                const pqText = [m.parameter_size, m.quantization_level].filter(Boolean).join(' · ');
                const pqTip = `Architecture spec: ${m.parameter_size || 'unknown'} parameters` +
                    (m.quantization_level ? `, ${m.quantization_level} quantization` : '') +
                    (m.family ? ` (${m.family} family)` : '') + '.';
                pills.push(`<span class="sf-mib-pill spec-param" data-sf-tip="${_sfEscHtml(pqTip)}" title="${_sfEscHtml(pqTip)}">🧠 ${_sfEscHtml(pqText)}</span>`);
            }

            if (d.sizeHuman) {
                const diskTip = `Disk footprint: ${d.sizeHuman} (${(m.size_bytes / (1024 * 1024)).toFixed(0)} MB on disk).`;
                pills.push(`<span class="sf-mib-pill spec-disk" data-sf-tip="${_sfEscHtml(diskTip)}" title="${_sfEscHtml(diskTip)}">💾 ${_sfEscHtml(d.sizeHuman)}</span>`);
            }

            if (m.family) {
                const famTip = `Model architecture family: ${m.family}.`;
                pills.push(`<span class="sf-mib-pill" data-sf-tip="${_sfEscHtml(famTip)}" title="${_sfEscHtml(famTip)}">🧬 ${_sfEscHtml(m.family)}</span>`);
            }

            if (m.context_length > 0) {
                const kCtx = m.context_length >= 1024 ? `${Math.round(m.context_length / 1024)}k` : `${m.context_length}`;
                const ctxTip = `Native maximum context window reported by Ollama: ${m.context_length} tokens.`;
                pills.push(`<span class="sf-mib-pill" data-sf-tip="${_sfEscHtml(ctxTip)}" title="${_sfEscHtml(ctxTip)}">📐 ${_sfEscHtml(kCtx)} ctx</span>`);
            }

            d.caps.forEach(c => {
                const meta = _SF_CAP_META[c] || { icon: '•', label: c, title: c, desc: '' };
                const tip = `${meta.title}: ${meta.desc}`;
                pills.push(`<span class="sf-mib-pill cap-${_sfEscHtml(c)}" data-sf-tip="${_sfEscHtml(tip)}" title="${_sfEscHtml(tip)}">${meta.icon} ${_sfEscHtml(meta.label)}</span>`);
            });

            const descLine = m.description
                ? `<div class="sf-mib-desc">${_sfEscHtml(m.description)}</div>`
                : '';

            infoBar.innerHTML = `<div class="sf-mib-pills">${pills.join('')}</div>${descLine}`;
            infoBar.style.display = 'flex';
        }
    }
};

if (!window._sfModelPickerEventsBound) {
    window._sfModelPickerEventsBound = true;
    document.addEventListener('click', (e) => {
        const picker = document.getElementById('sf-model-picker');
        if (picker && !picker.contains(e.target)) {
            if (window.sfCloseModelPicker) window.sfCloseModelPicker();
        }
    });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            const menu = document.getElementById('sf-model-picker-menu');
            if (menu && menu.style.display !== 'none') {
                window.sfCloseModelPicker();
            }
        }
    });
}

window.sfUpdateModelsDropdown = function() {
    const bType = document.getElementById('sf-backend-select')?.value;
    const mSel = document.getElementById('sf-model-select');
    if (!mSel || !window.sfState.allModels) return;
    const prevModel = mSel.value;
    mSel.innerHTML = '';
    
    const filtered = window.sfState.allModels.filter(m => {
        if (!bType) return true;
        if (bType === 'cloud' && m.type === 'cloud') return true;
        if (bType === 'ollama' && m.type === 'local' && !m.id.includes('.gguf')) return true;
        if (bType === 'llama_cpp' && m.id.includes('.gguf')) return true;
        if (bType === 'kobold' && m.provider === 'kobold') return true;
        return false;
    });

    window.sfState.filteredModels = filtered;
    
    filtered.forEach(m => {
        const opt = document.createElement('option');
        opt.value = m.id;
        const d = _sfBuildModelDisplay(m);
        opt.textContent = d.optionLabel;
        opt.title = d.tooltipText;
        mSel.appendChild(opt);
    });

    if (prevModel && Array.from(mSel.options).some(o => o.value === prevModel)) {
        mSel.value = prevModel;
    }

    if (window.sfSyncModelUI) window.sfSyncModelUI();
};

window.sfUpdateVoicesDropdown = async function() {
    const engine = document.getElementById('sf-tts-engine-select')?.value;
    const vSel = document.getElementById('sf-tts-voice-select');
    if (!vSel) return;
    vSel.innerHTML = '';
    if (!engine) return;
    
    try {
        const res = await fetch(`/api/audio/voices?engine=${engine}`);
        if (res.ok) {
            const voices = await res.json();
            const voiceMap = (!Array.isArray(voices) && voices[engine]) ? voices[engine] : voices;
            const keys = Array.isArray(voiceMap) ? voiceMap : Object.keys(voiceMap);
            keys.forEach(v => {
                const opt = document.createElement('option');
                opt.value = v;
                opt.textContent = (!Array.isArray(voiceMap) && voiceMap[v]) ? voiceMap[v] : v;
                vSel.appendChild(opt);
            });

            if (engine === 'kokoro') {
                const bSel = document.getElementById('sf-kokoro-blend-voice');
                if (bSel) {
                    const prevVal = bSel.value;
                    bSel.innerHTML = '<option value="">None (Pure Voice)</option>';
                    keys.forEach(v => {
                        const opt = document.createElement('option');
                        opt.value = v;
                        opt.textContent = (!Array.isArray(voiceMap) && voiceMap[v]) ? voiceMap[v] : v;
                        bSel.appendChild(opt);
                    });
                    bSel.value = prevVal;
                }
            }
        }
    } catch(e) {}
};

window.sfApplySoulToUI = async function(soul) {
    if (!soul) return;
    window._sfApplyingSoul = true;  // suppress pill update during bulk-populate
    
    const fallbacks = window.sfSystemFallbacks || {};
    
    // Persona
    const pSel = document.getElementById('sf-persona-select');
    const targetPersona = soul.persona?.soul_file || fallbacks.persona || "";
    if (pSel && targetPersona && targetPersona !== 'unknown') {
        let opt = Array.from(pSel.options).find(o => o.value === targetPersona || o.value === targetPersona + '.yaml');
        if (!opt) {
            opt = document.createElement('option');
            opt.value = targetPersona;
            opt.textContent = targetPersona.replace('.yaml', '');
            pSel.appendChild(opt);
        }
        pSel.value = opt.value;
    }
    
    document.getElementById('sf-use-global-direct').checked = soul.persona?.use_global_direct_instructions !== false;
    document.getElementById('sf-use-global-safety').checked = soul.persona?.use_global_safety_instructions !== false;
    document.getElementById('sf-custom-instructions').value = soul.persona?.custom_instructions || "";
    document.getElementById('sf-user-notes').value = soul.persona?.user_notes || "";
    document.getElementById('sf-send-notes-ai').checked = soul.persona?.send_notes_to_ai === true;
    
    // Payload & Tools Control
    const payloadTools = document.getElementById('sf-payload-tools');
    if (payloadTools) payloadTools.checked = soul.payload?.send_tools !== false;
    const payloadSoul = document.getElementById('sf-payload-soul');
    if (payloadSoul) payloadSoul.checked = soul.payload?.send_personality !== false;
    const payloadMem = document.getElementById('sf-payload-memory');
    if (payloadMem) payloadMem.checked = soul.payload?.send_memory !== false;
    const payloadThinking = document.getElementById('sf-payload-thinking');
    if (payloadThinking) payloadThinking.checked = soul.payload?.include_thinking_in_history === true;
    const payloadEnableThinking = document.getElementById('sf-payload-enable-thinking');
    if (payloadEnableThinking) payloadEnableThinking.checked = soul.payload?.enable_thinking !== false;

    // Model
    document.getElementById('sf-backend-select').value = soul.model?.backend_type || fallbacks.backend || "ollama";
    window.sfUpdateModelsDropdown();
    document.getElementById('sf-model-select').value = soul.model?.model_name || fallbacks.model || "";
    if (window.sfSyncModelUI) window.sfSyncModelUI();
    
    // Voice
    const currentEng = (soul.voice?.tts_engine && soul.voice.tts_engine !== 'unknown')
        ? soul.voice.tts_engine
        : ((fallbacks.tts_engine && fallbacks.tts_engine !== 'unknown') ? fallbacks.tts_engine : "piper");
    document.getElementById('sf-tts-engine-select').value = currentEng;
    await window.sfUpdateVoicesDropdown();
    
    let targetVoice = soul.voice?.tts_voice || fallbacks.tts_voice || "";
    if (currentEng === 'fish_speech' || currentEng === 'fish') {
        const refAudio = soul.voice?.fish_reference_audio || soul.voice?.fish_speaker_wav;
        if (refAudio) {
            targetVoice = refAudio.split(/[/\\]/).pop();
        }
    }
    const voiceSel = document.getElementById('sf-tts-voice-select');
    if (voiceSel) {
        if (targetVoice && targetVoice !== 'unknown') {
            let match = Array.from(voiceSel.options).find(o => o.value === targetVoice || o.value.split(/[/\\]/).pop() === targetVoice);
            voiceSel.value = match ? match.value : targetVoice;
        } else if (voiceSel.options.length > 0) {
            voiceSel.selectedIndex = 0;
        }
    }
    
    // Inference
    document.getElementById('sf-inference-preset-select').value = soul.inference?.preset_name || "";
    
    const setVal = (id, val) => {
        if (val !== undefined && val !== null) {
            const el = document.getElementById(id);
            if (el) { el.value = val; window.sfUpdateSliderVal(el, id.replace('sf-', 'sf-val-')); }
        }
    };
    
    setVal('sf-temp', soul.inference?.temperature ?? 0.7);
    setVal('sf-topp', soul.inference?.top_p ?? 0.9);
    setVal('sf-reppen', soul.inference?.repeat_penalty ?? 1.1);
    setVal('sf-predict', soul.inference?.num_predict ?? 1024);

    const ctxEl = document.getElementById('sf-ctx');
    if (ctxEl) {
        ctxEl.value = (soul.inference?.num_ctx !== undefined && soul.inference?.num_ctx !== null) ? soul.inference.num_ctx : 0;
        const valEl = document.getElementById('sf-val-ctx');
        if (valEl) valEl.textContent = ctxEl.value == 0 ? 'Auto' : ctxEl.value;
    }
    
    const gpuEl = document.getElementById('sf-gpu');
    if (gpuEl) {
        gpuEl.value = (soul.inference?.n_gpu_layers !== undefined && soul.inference?.n_gpu_layers !== null) ? soul.inference.n_gpu_layers : -2;
        const valEl = document.getElementById('sf-val-gpu');
        if (valEl) {
            let txt = gpuEl.value;
            if (gpuEl.value == -2) txt = 'Auto';
            else if (gpuEl.value == -1) txt = 'Max (-1)';
            valEl.textContent = txt;
        }
    }
    
    document.getElementById('sf-xtts-preset-select').value = soul.voice?.xtts_preset || "";
    const xttsInfSel = document.getElementById('sf-xtts-inference-preset-select');
    if (xttsInfSel) xttsInfSel.value = soul.voice?.xtts_inference_preset || "";
    document.getElementById('sf-xtts-speaker-wav').value = soul.voice?.xtts_speaker_wav || "";
    setVal('sf-xtts-temp', soul.voice?.xtts_temperature ?? 0.75);
    setVal('sf-xtts-speed', soul.voice?.xtts_speed ?? 1.0);
    setVal('sf-xtts-topk', soul.voice?.xtts_top_k ?? 50);
    setVal('sf-xtts-reppen', soul.voice?.xtts_repetition_penalty ?? 5.0);
    setVal('sf-xtts-topp', soul.voice?.xtts_topp ?? 0.85);
    setVal('sf-xtts-length-penalty', soul.voice?.xtts_length_penalty ?? 1.0);

    const sfFishPresetSel = document.getElementById('sf-fish-preset-select');
    if (sfFishPresetSel) sfFishPresetSel.value = soul.voice?.fish_preset || "";
    const sfFishInfSel = document.getElementById('sf-fish-inference-preset-select');
    if (sfFishInfSel) sfFishInfSel.value = soul.voice?.fish_inference_preset || "";
    if (document.getElementById('sf-fish-speaker-wav')) document.getElementById('sf-fish-speaker-wav').value = soul.voice?.fish_reference_audio || soul.voice?.fish_speaker_wav || "";
    if (document.getElementById('sf-fish-ref-text')) document.getElementById('sf-fish-ref-text').value = soul.voice?.fish_reference_text || "";
    setVal('sf-fish-temp', soul.voice?.fish_temperature ?? 0.7);
    setVal('sf-fish-topp', soul.voice?.fish_top_p ?? 0.7);
    setVal('sf-fish-reppen', soul.voice?.fish_repetition_penalty ?? 1.2);
    setVal('sf-fish-chunk-length', soul.voice?.fish_chunk_length ?? 200);
    setVal('sf-fish-max-tokens', soul.voice?.fish_max_new_tokens ?? 1024);

    const sfKokoroPresetSel = document.getElementById('sf-kokoro-preset-select');
    if (sfKokoroPresetSel) {
        const kp = soul.voice?.kokoro_preset || "";
        sfKokoroPresetSel.value = (kp && Array.from(sfKokoroPresetSel.options).some(o => o.value === kp)) ? kp : "";
    }
    const sfKokoroInfSel = document.getElementById('sf-kokoro-inference-preset-select');
    if (sfKokoroInfSel) sfKokoroInfSel.value = soul.voice?.kokoro_inference_preset || "";
    const sfKokoroBlendSel = document.getElementById('sf-kokoro-blend-voice');
    if (sfKokoroBlendSel) sfKokoroBlendSel.value = soul.voice?.kokoro_blend_voice || "";
    setVal('sf-kokoro-speed', soul.voice?.kokoro_speed ?? 1.0);
    setVal('sf-kokoro-silence', soul.voice?.kokoro_silence ?? 0.0);
    setVal('sf-kokoro-alpha', soul.voice?.kokoro_alpha ?? 1.0);
    setVal('sf-kokoro-beta', soul.voice?.kokoro_beta ?? 1.0);
    setVal('sf-kokoro-volume', soul.voice?.kokoro_volume ?? 1.0);
    
    window._sfApplyingSoul = false;
    window.sfRefreshUIVisibilityAndSummaries();
};

window.sfApplySessionOverridesToUI = async function(cfg) {
    if (!cfg) return;

    const pFile = cfg.persona?.soul_file || cfg.ai?.active_personality;
    if (pFile) {
        const pSel = document.getElementById('sf-persona-select');
        if (pSel) pSel.value = pFile;
    }

    const pObj = cfg.persona || {};
    if (pObj.use_global_direct_instructions !== undefined) {
        document.getElementById('sf-use-global-direct').checked = pObj.use_global_direct_instructions !== false;
    }
    if (pObj.use_global_safety_instructions !== undefined) {
        document.getElementById('sf-use-global-safety').checked = pObj.use_global_safety_instructions !== false;
    }
    if (pObj.custom_instructions !== undefined && pObj.custom_instructions !== null) {
        document.getElementById('sf-custom-instructions').value = pObj.custom_instructions;
    }
    if (pObj.user_notes !== undefined && pObj.user_notes !== null) {
        document.getElementById('sf-user-notes').value = pObj.user_notes;
    }
    if (pObj.send_notes_to_ai !== undefined && pObj.send_notes_to_ai !== null) {
        document.getElementById('sf-send-notes-ai').checked = pObj.send_notes_to_ai === true;
    }

    // Payload Control (check both payload_control and payload)
    const pCtrl = Object.assign({}, cfg.payload || {}, cfg.payload_control || {});
    if (pCtrl.send_tools !== undefined) document.getElementById('sf-payload-tools').checked = pCtrl.send_tools !== false;
    if (pCtrl.send_personality !== undefined) document.getElementById('sf-payload-soul').checked = pCtrl.send_personality !== false;
    if (pCtrl.send_memory !== undefined) document.getElementById('sf-payload-memory').checked = pCtrl.send_memory !== false;
    if (pCtrl.include_thinking_in_history !== undefined) document.getElementById('sf-payload-thinking').checked = pCtrl.include_thinking_in_history === true;

    // Model / Backend
    const bType = cfg.model?.backend_type || cfg.backend?.type;
    if (bType) {
        document.getElementById('sf-backend-select').value = bType;
        window.sfUpdateModelsDropdown();
        const mName = cfg.model?.model_name || cfg.backend?.[bType]?.model;
        if (mName) document.getElementById('sf-model-select').value = mName;
        if (window.sfSyncModelUI) window.sfSyncModelUI();
    }

    // TTS Engine & Voice
    const ttsEng = cfg.voice?.tts_engine || cfg.ai?.tts_engine;
    if (ttsEng) {
        document.getElementById('sf-tts-engine-select').value = ttsEng;
        await window.sfUpdateVoicesDropdown();
    }
    const ttsV = cfg.voice?.tts_voice || cfg.ai?.tts_voice;
    if (ttsV) {
        const voiceSel = document.getElementById('sf-tts-voice-select');
        if (voiceSel) {
            const match = Array.from(voiceSel.options).find(o => o.value === ttsV || o.value.split(/[/\\]/).pop() === ttsV);
            voiceSel.value = match ? match.value : ttsV;
        }
    }

    // Inference
    const setVal = (id, val) => {
        if (val !== undefined && val !== null) {
            const el = document.getElementById(id);
            if (el) { el.value = val; window.sfUpdateSliderVal(el, id.replace('sf-', 'sf-val-')); }
        }
    };
    if (cfg.inference) {
        if (cfg.inference.preset_name !== undefined) document.getElementById('sf-inference-preset-select').value = cfg.inference.preset_name || "";
        setVal('sf-temp', cfg.inference.temperature);
        setVal('sf-topp', cfg.inference.top_p);
        setVal('sf-reppen', cfg.inference.repeat_penalty);
        setVal('sf-predict', cfg.inference.num_predict);
        if (cfg.inference.num_ctx !== undefined) {
            const ctxEl = document.getElementById('sf-ctx');
            if (ctxEl) {
                ctxEl.value = cfg.inference.num_ctx || 0;
                const valEl = document.getElementById('sf-val-ctx');
                if (valEl) valEl.textContent = ctxEl.value == 0 ? 'Auto' : ctxEl.value;
            }
        }
        if (cfg.inference.n_gpu_layers !== undefined) {
            const gpuEl = document.getElementById('sf-gpu');
            if (gpuEl) {
                gpuEl.value = (cfg.inference.n_gpu_layers !== null && cfg.inference.n_gpu_layers !== undefined) ? cfg.inference.n_gpu_layers : -2;
                const valEl = document.getElementById('sf-val-gpu');
                if (valEl) {
                    let txt = gpuEl.value;
                    if (gpuEl.value == -2) txt = 'Auto';
                    else if (gpuEl.value == -1) txt = 'Max (-1)';
                    valEl.textContent = txt;
                }
            }
        }
    }

    // Voice fine parameters
    if (cfg.voice) {
        if (cfg.voice.xtts_preset !== undefined) document.getElementById('sf-xtts-preset-select').value = cfg.voice.xtts_preset || "";
        if (cfg.voice.xtts_inference_preset !== undefined) document.getElementById('sf-xtts-inference-preset-select').value = cfg.voice.xtts_inference_preset || "";
        if (cfg.voice.xtts_speaker_wav !== undefined) document.getElementById('sf-xtts-speaker-wav').value = cfg.voice.xtts_speaker_wav || "";
        setVal('sf-xtts-temp', cfg.voice.xtts_temperature);
        setVal('sf-xtts-speed', cfg.voice.xtts_speed);
        setVal('sf-xtts-topk', cfg.voice.xtts_top_k);
        setVal('sf-xtts-reppen', cfg.voice.xtts_repetition_penalty);
        setVal('sf-xtts-topp', cfg.voice.xtts_top_p);
        setVal('sf-xtts-length-penalty', cfg.voice.xtts_length_penalty);

        if (cfg.voice.fish_preset !== undefined) document.getElementById('sf-fish-preset-select').value = cfg.voice.fish_preset || "";
        if (cfg.voice.fish_inference_preset !== undefined) document.getElementById('sf-fish-inference-preset-select').value = cfg.voice.fish_inference_preset || "";
        if (cfg.voice.fish_reference_audio || cfg.voice.fish_speaker_wav) {
            document.getElementById('sf-fish-speaker-wav').value = cfg.voice.fish_reference_audio || cfg.voice.fish_speaker_wav;
        }
        if (cfg.voice.fish_reference_text !== undefined) document.getElementById('sf-fish-ref-text').value = cfg.voice.fish_reference_text || "";
        setVal('sf-fish-temp', cfg.voice.fish_temperature);
        setVal('sf-fish-topp', cfg.voice.fish_top_p);
        setVal('sf-fish-reppen', cfg.voice.fish_repetition_penalty);
        setVal('sf-fish-chunk-length', cfg.voice.fish_chunk_length);
        setVal('sf-fish-max-tokens', cfg.voice.fish_max_new_tokens);

        if (cfg.voice.kokoro_preset !== undefined) document.getElementById('sf-kokoro-preset-select').value = cfg.voice.kokoro_preset || "";
        if (cfg.voice.kokoro_inference_preset !== undefined) document.getElementById('sf-kokoro-inference-preset-select').value = cfg.voice.kokoro_inference_preset || "";
        if (cfg.voice.kokoro_blend_voice !== undefined) document.getElementById('sf-kokoro-blend-voice').value = cfg.voice.kokoro_blend_voice || "";
        setVal('sf-kokoro-speed', cfg.voice.kokoro_speed);
        setVal('sf-kokoro-silence', cfg.voice.kokoro_silence);
        setVal('sf-kokoro-alpha', cfg.voice.kokoro_alpha);
        setVal('sf-kokoro-beta', cfg.voice.kokoro_beta);
        setVal('sf-kokoro-volume', cfg.voice.kokoro_volume);
    }
};

window.sfUpdateTooltip = function(soul, explicitSoulId) {
    if (!soul) return;
    const sbGD = document.getElementById('sb-global-defaults');
    const sbGDLabel = document.getElementById('sb-global-defaults-label');
    const sbGDBtn = sbGD ? sbGD.closest('.status-pill') : null;
    const soulId = explicitSoulId !== undefined ? explicitSoulId : window.sfState.globalDefaultSoulId;
    
    if (sbGD && sbGDLabel) {
        const isPreset = !!soulId;
        const foundSoul = isPreset ? (window.sfState.souls || []).find(s => s.meta.id === soulId) : null;
        const presetDisplayName = (soul.meta && soul.meta.name)
            ? soul.meta.name
            : (foundSoul?.meta?.name || soulId || 'Preset');
        const isModified = !!(window.sfState && window.sfState.isDirty);
        let lines = [];
        
        if (isPreset) {
            lines.push(`🎭 Global Preset: ${presetDisplayName}${isModified ? ' (modified)' : ''}`);
        } else {
            lines.push(`🎭 Active Configuration (${isModified ? 'Modified Draft' : 'Default'})`);
        }
        
        const modelName = soul.model?.model_name || 'System Default';
        const backendName = soul.model?.backend_type || 'unknown';
        lines.push(`🤖 Model: ${modelName} (${backendName})`);
        
        const soulFile = soul.persona?.soul_file || window.sfSystemFallbacks?.persona || 'System Default';
        lines.push(`👤 Soul: ${soulFile}`);
        
        const temp = soul.inference?.temperature ?? '?';
        const topP = soul.inference?.top_p ?? '?';
        const repPen = soul.inference?.repeat_penalty ?? '?';
        lines.push(`⚙ Temp: ${temp} | Top P: ${topP} | Rep Pen: ${repPen}`);
        
        if (soul.voice?.tts_engine) {
            lines.push(`🔊 TTS: ${soul.voice.tts_engine} / ${soul.voice.tts_voice || 'Default'}`);
        }
        
        let shortcutKey = 'F3';
        if (window.HKS_BINDINGS && typeof window.HKS_BINDINGS.get === 'function') {
            const raw = window.HKS_BINDINGS.get('ui.global_defaults') || window.HKS_BINDINGS.get('ui.chat_overrides');
            if (raw) shortcutKey = raw.toUpperCase();
        }
        lines.push(`\n⚡ Click to open Quick Config / Soul Forge (${shortcutKey})`);
        
        const titleText = lines.join('\n');
        const modSuffix = isModified ? ' ●' : '';
        
        if (isPreset) {
            sbGDLabel.innerHTML = '<i class="fas fa-cog"></i> Global Preset';
            sbGD.textContent = presetDisplayName + modSuffix;
            if (sbGDBtn) sbGDBtn.title = titleText;
        } else {
            sbGDLabel.innerHTML = '<i class="fas fa-cog"></i> Quick Config';
            sbGD.textContent = 'Configure' + modSuffix;
            if (sbGDBtn) sbGDBtn.title = titleText;
        }
    }
};

window.sfCollectUIState = function() {
    const getVal = (id) => { const el = document.getElementById(id); return el ? (el.value === "" ? null : el.value) : null; };
    const getNum = (id) => { const el = document.getElementById(id); return (el && el.value !== "") ? parseFloat(el.value) : null; };
    const getCheck = (id) => { const el = document.getElementById(id); return el ? el.checked : false; };
    
    const resolvedVoice = (() => {
        const eng = getVal('sf-tts-engine-select');
        const rawVoice = getVal('sf-tts-voice-select');
        const cleanVoice = (rawVoice === 'CLONE' || rawVoice === 'MIXED' || rawVoice === 'KOKORO_PRESET') ? '' : rawVoice;
        if (eng === 'fish_speech' || eng === 'fish') {
            return getVal('sf-fish-speaker-wav') || cleanVoice || 'default';
        }
        if (eng === 'xtts2' && getVal('sf-xtts-speaker-wav')) {
            return getVal('sf-xtts-speaker-wav');
        }
        if (eng === 'kokoro') {
            const pName = getVal('sf-kokoro-preset-select');
            if (pName && window.sfState?.kokoroPresets?.[pName]) {
                const p = window.sfState.kokoroPresets[pName];
                return p.voice || cleanVoice;
            }
        }
        return cleanVoice;
    })();

    const bType = getVal('sf-backend-select');
    const mName = getVal('sf-model-select');
    const payloadObj = {
        send_tools: getCheck('sf-payload-tools'),
        send_personality: getCheck('sf-payload-soul'),
        send_memory: getCheck('sf-payload-memory'),
        include_thinking_in_history: getCheck('sf-payload-thinking'),
        enable_thinking: getCheck('sf-payload-enable-thinking')
    };

    const backendObj = bType ? { type: bType, [bType]: { model: mName } } : {};

    return {
        active_global_preset: window.sfState ? window.sfState.activeSoulId : null,
        ai: {
            tts_engine: getVal('sf-tts-engine-select'),
            tts_voice: resolvedVoice,
            active_personality: getVal('sf-persona-select')
        },
        backend: backendObj,
        payload_control: Object.assign({}, payloadObj),
        persona: { 
            soul_file: getVal('sf-persona-select'),
            use_global_direct_instructions: getCheck('sf-use-global-direct'),
            use_global_safety_instructions: getCheck('sf-use-global-safety'),
            custom_instructions: getVal('sf-custom-instructions'),
            user_notes: getVal('sf-user-notes'),
            send_notes_to_ai: getCheck('sf-send-notes-ai')
        },
        model: { backend_type: bType, model_name: mName },
        payload: payloadObj,
        inference: {
            preset_name: getVal('sf-inference-preset-select'),
            temperature: getNum('sf-temp'),
            top_p: getNum('sf-topp'),
            repeat_penalty: getNum('sf-reppen'),
            num_predict: parseInt(getNum('sf-predict')),
            num_ctx: getNum('sf-ctx') === 0 ? null : parseInt(getNum('sf-ctx')),
            n_gpu_layers: getNum('sf-gpu') === -2 ? null : parseInt(getNum('sf-gpu'))
        },
        voice: {
            tts_engine: getVal('sf-tts-engine-select'),
            tts_voice: resolvedVoice,
            xtts_preset: getVal('sf-xtts-preset-select'),
            xtts_inference_preset: getVal('sf-xtts-inference-preset-select'),
            xtts_speaker_wav: getVal('sf-xtts-speaker-wav'),
            xtts_temperature: getNum('sf-xtts-temp'),
            xtts_speed: getNum('sf-xtts-speed'),
            xtts_top_k: parseInt(getNum('sf-xtts-topk')),
            xtts_repetition_penalty: getNum('sf-xtts-reppen'),
            xtts_top_p: getNum('sf-xtts-topp'),
            xtts_length_penalty: getNum('sf-xtts-length-penalty'),
            fish_preset: getVal('sf-fish-preset-select'),
            fish_inference_preset: getVal('sf-fish-inference-preset-select'),
            fish_reference_audio: getVal('sf-fish-speaker-wav'),
            fish_reference_text: getVal('sf-fish-ref-text'),
            fish_temperature: getNum('sf-fish-temp'),
            fish_top_p: getNum('sf-fish-topp'),
            fish_repetition_penalty: getNum('sf-fish-reppen'),
            fish_chunk_length: getNum('sf-fish-chunk-length'),
            fish_max_new_tokens: getNum('sf-fish-max-tokens'),
            kokoro_preset: getVal('sf-kokoro-preset-select'),
            kokoro_inference_preset: getVal('sf-kokoro-inference-preset-select'),
            kokoro_blend_voice: (() => {
                const pName = getVal('sf-kokoro-preset-select');
                if (pName && window.sfState?.kokoroPresets?.[pName]) {
                    return window.sfState.kokoroPresets[pName].blend_voice || '';
                }
                return getVal('sf-kokoro-blend-voice') || '';
            })(),
            kokoro_speed: getNum('sf-kokoro-speed'),
            kokoro_silence: getNum('sf-kokoro-silence'),
            kokoro_alpha: getNum('sf-kokoro-alpha'),
            kokoro_beta: getNum('sf-kokoro-beta'),
            kokoro_volume: getNum('sf-kokoro-volume')
        }
    };
};

window.soCollectUIState = window.sfCollectUIState;

window.sfApplyInferencePreset = function(presetName) {
    if (!presetName || !window.sfState.inferencePresets[presetName]) {
        window.sfDirty();
        return;
    }
    const p = window.sfState.inferencePresets[presetName];
    
    const setVal = (id, val) => {
        if (val !== undefined && val !== null) {
            const el = document.getElementById(id);
            if (el) { el.value = val; window.sfUpdateSliderVal(el, id.replace('sf-', 'sf-val-')); }
        }
    };
    
    setVal('sf-temp', p.temperature);
    setVal('sf-topp', p.top_p);
    setVal('sf-reppen', p.repeat_penalty);
    setVal('sf-predict', p.num_predict);
    
    window.sfDirty();
};

window.sfApplyXttsPreset = function(presetName) {
    if (!presetName || !window.sfState.xttsPresets || !window.sfState.xttsPresets[presetName]) {
        document.getElementById('sf-xtts-speaker-wav').value = "";
        const xttsInfSel = document.getElementById('sf-xtts-inference-preset-select');
        if (xttsInfSel) xttsInfSel.value = "";
        window.sfUpdateCloneState();
        window.sfDirty();
        return;
    }
    const p = window.sfState.xttsPresets[presetName];
    
    const setVal = (id, val) => {
        if (val !== undefined && val !== null) {
            const el = document.getElementById(id);
            if (el) { el.value = val; window.sfUpdateSliderVal(el, id.replace('sf-', 'sf-val-')); }
        }
    };
    
    setVal('sf-xtts-temp', p.temperature);
    setVal('sf-xtts-speed', p.speed);
    setVal('sf-xtts-topk', p.top_k);
    setVal('sf-xtts-reppen', p.repetition_penalty);
    setVal('sf-xtts-topp', p.top_p);
    
    document.getElementById('sf-xtts-speaker-wav').value = p.speaker_wav || "";

    let matchedInf = "";
    if (window.sfState.xttsInferencePresets) {
        for (const [k, inf] of Object.entries(window.sfState.xttsInferencePresets)) {
            if (
                (!p.temperature || Math.abs(inf.temperature - p.temperature) < 0.01) &&
                (!p.speed || Math.abs(inf.speed - p.speed) < 0.01) &&
                (!p.top_k || inf.top_k === p.top_k) &&
                (!p.repetition_penalty || Math.abs(inf.repetition_penalty - p.repetition_penalty) < 0.01)
            ) {
                matchedInf = k;
                break;
            }
        }
    }
    const xttsInfSel = document.getElementById('sf-xtts-inference-preset-select');
    if (xttsInfSel) xttsInfSel.value = matchedInf;
    
    window.sfUpdateCloneState();
    window.sfDirty();
};

window.sfApplyXttsInferencePreset = function(presetName) {
    if (!presetName || !window.sfState.xttsInferencePresets[presetName]) return;
    const p = window.sfState.xttsInferencePresets[presetName];
    
    const setVal = (id, val) => {
        if (val !== undefined && val !== null) {
            const el = document.getElementById(id);
            if (el) { el.value = val; window.sfUpdateSliderVal(el, id.replace('sf-', 'sf-val-')); }
        }
    };
    
    setVal('sf-xtts-temp', p.temperature);
    setVal('sf-xtts-speed', p.speed);
    setVal('sf-xtts-topk', p.top_k);
    setVal('sf-xtts-reppen', p.repetition_penalty);
    setVal('sf-xtts-topp', p.top_p);
    setVal('sf-xtts-length-penalty', p.length_penalty);
    
    window.sfDirty();
};

window.sfApplyFishPreset = function(presetName) {
    if (!presetName || !window.sfState.fishSpeechPresets || !window.sfState.fishSpeechPresets[presetName]) {
        if (document.getElementById('sf-fish-speaker-wav')) document.getElementById('sf-fish-speaker-wav').value = "";
        if (document.getElementById('sf-fish-ref-text')) document.getElementById('sf-fish-ref-text').value = "";
        const fishInfSel = document.getElementById('sf-fish-inference-preset-select');
        if (fishInfSel) fishInfSel.value = "";
        window.sfUpdateCloneState();
        window.sfDirty();
        return;
    }
    const p = window.sfState.fishSpeechPresets[presetName];
    if (document.getElementById('sf-fish-speaker-wav')) document.getElementById('sf-fish-speaker-wav').value = p.reference_audio || "";
    if (document.getElementById('sf-fish-ref-text')) document.getElementById('sf-fish-ref-text').value = p.reference_text || "";

    if (p.temperature !== undefined) {
        const el = document.getElementById('sf-fish-temp');
        if (el) { el.value = p.temperature; window.sfUpdateSliderVal(el, 'sf-val-fish-temp'); }
    }
    if (p.top_p !== undefined) {
        const el = document.getElementById('sf-fish-topp');
        if (el) { el.value = p.top_p; window.sfUpdateSliderVal(el, 'sf-val-fish-topp'); }
    }
    if (p.repetition_penalty !== undefined) {
        const el = document.getElementById('sf-fish-reppen');
        if (el) { el.value = p.repetition_penalty; window.sfUpdateSliderVal(el, 'sf-val-fish-reppen'); }
    }

    let matchedInf = p.inference_preset || "";
    if (!matchedInf && window.sfState.fishSpeechInferencePresets) {
        for (const [k, inf] of Object.entries(window.sfState.fishSpeechInferencePresets)) {
            if (
                (!p.temperature || Math.abs(inf.temperature - p.temperature) < 0.01) &&
                (!p.top_p || Math.abs(inf.top_p - p.top_p) < 0.01) &&
                (!p.repetition_penalty || Math.abs(inf.repetition_penalty - p.repetition_penalty) < 0.01)
            ) {
                matchedInf = k;
                break;
            }
        }
    }
    const fishInfSel = document.getElementById('sf-fish-inference-preset-select');
    if (fishInfSel) fishInfSel.value = matchedInf;

    window.sfUpdateCloneState();
    window.sfDirty();
};

window.sfApplyFishInferencePreset = function(presetName) {
    if (!presetName || !window.sfState.fishSpeechInferencePresets || !window.sfState.fishSpeechInferencePresets[presetName]) return;
    const p = window.sfState.fishSpeechInferencePresets[presetName];
    
    const setVal = (id, val) => {
        if (val !== undefined && val !== null) {
            const el = document.getElementById(id);
            if (el) { el.value = val; window.sfUpdateSliderVal(el, id.replace('sf-', 'sf-val-')); }
        }
    };
    
    setVal('sf-fish-temp', p.temperature);
    setVal('sf-fish-topp', p.top_p);
    setVal('sf-fish-reppen', p.repetition_penalty);
    setVal('sf-fish-chunk-length', p.chunk_length ?? 200);
    setVal('sf-fish-max-tokens', p.max_new_tokens ?? 1024);
    
    window.sfDirty();
};

window.sfUpdateCloneState = function() {
    const engine = document.getElementById('sf-tts-engine-select')?.value;
    const voiceSelect = document.getElementById('sf-tts-voice-select');
    if (!voiceSelect) return;
    
    let isCloneOrPreset = false;
    let titleDesc = "";
    let customOptionLabel = "-- Voice Clone Active --";
    let customOptionValue = "CLONE";

    if (engine === 'xtts2') {
        const wavInput = document.getElementById('sf-xtts-speaker-wav');
        const presetSel = document.getElementById('sf-xtts-preset-select');
        if ((wavInput && wavInput.value.trim() !== '') || (presetSel && presetSel.value.trim() !== '')) {
            isCloneOrPreset = true;
            titleDesc = "Using XTTS Preset / Voice Clone (.wav)";
            customOptionLabel = "-- Voice Clone Active --";
            customOptionValue = "CLONE";
        }
    } else if (engine === 'fish_speech' || engine === 'fish') {
        const fishWav = document.getElementById('sf-fish-speaker-wav');
        const fishPresetSel = document.getElementById('sf-fish-preset-select');
        if ((fishPresetSel && fishPresetSel.value.trim() !== '') || (fishWav && fishWav.value.trim() !== '')) {
            isCloneOrPreset = true;
            titleDesc = "Using Fish Speech Preset / Voice Clone (.wav)";
            customOptionLabel = "-- Voice Clone Active --";
            customOptionValue = "CLONE";
        }
    } else if (engine === 'kokoro') {
        const kokoroPresetSel = document.getElementById('sf-kokoro-preset-select');
        const presetName = kokoroPresetSel ? kokoroPresetSel.value.trim() : '';
        if (presetName !== '') {
            isCloneOrPreset = true;
            const p = (window.sfState && window.sfState.kokoroPresets) ? window.sfState.kokoroPresets[presetName] : null;
            const hasBlend = p && p.blend_voice && p.blend_voice.trim() !== '';
            if (hasBlend) {
                const primary = p.voice || 'Primary';
                const blend = p.blend_voice;
                titleDesc = `Kokoro Preset '${presetName}' (Mixed Voice: ${primary} + ${blend})`;
                customOptionLabel = `-- Mixed Voice (${primary} + ${blend}) --`;
                customOptionValue = "MIXED";
            } else {
                const vName = (p && p.voice) ? p.voice : 'Preset Voice';
                titleDesc = `Kokoro Preset '${presetName}' (Voice: ${vName})`;
                customOptionLabel = `-- Preset Voice (${vName}) --`;
                customOptionValue = "KOKORO_PRESET";
            }
        }
    }

    if (isCloneOrPreset) {
        if (voiceSelect.value && !['CLONE', 'MIXED', 'KOKORO_PRESET'].includes(voiceSelect.value)) {
            voiceSelect.dataset.prevRealVoice = voiceSelect.value;
        }
        voiceSelect.disabled = true;
        voiceSelect.title = titleDesc;
        let opt = Array.from(voiceSelect.options).find(o => o.dataset?.virtual === "true" || ['CLONE', 'MIXED', 'KOKORO_PRESET'].includes(o.value));
        if (!opt) {
            opt = document.createElement('option');
            opt.dataset.virtual = "true";
            voiceSelect.appendChild(opt);
        }
        opt.value = customOptionValue;
        opt.textContent = customOptionLabel;
        voiceSelect.value = customOptionValue;
    } else {
        const wasVirtual = ['CLONE', 'MIXED', 'KOKORO_PRESET'].includes(voiceSelect.value);
        voiceSelect.disabled = false;
        voiceSelect.title = "";
        Array.from(voiceSelect.options).forEach(o => {
            if (o.dataset?.virtual === "true" || o.value === "CLONE" || o.value === "MIXED" || o.value === "KOKORO_PRESET") {
                o.remove();
            }
        });
        if (wasVirtual) {
            const fallbackVoice = voiceSelect.dataset.prevRealVoice || window.sfSystemFallbacks?.tts_voice || "";
            if (fallbackVoice && Array.from(voiceSelect.options).some(o => o.value === fallbackVoice)) {
                voiceSelect.value = fallbackVoice;
            } else if (voiceSelect.options.length > 0) {
                voiceSelect.selectedIndex = 0;
            }
        }
    }
};



window.sfOnToolsToggle = function(isChecked) {
    if (window.updateToolModeBadge) {
        window.updateToolModeBadge(isChecked ? 'native' : 'direct');
    }
    if (window.Presenter && typeof window.Presenter.notify === 'function') {
        if (isChecked) {
            window.Presenter.notify({
                type: 'action_confirm',
                title: 'Payload Control',
                text: '🛠️ Native Tool Calling Mode: Function schemas loaded into model payload.',
                duration: 4000
            });
        } else {
            window.Presenter.notify({
                type: 'action_confirm',
                title: 'Payload Control',
                text: '⚡ Direct Commands Mode: Tool schemas stripped for maximum speed (~8,000 tokens saved). Direct /img and /search active.',
                duration: 4000
            });
        }
    }
};
