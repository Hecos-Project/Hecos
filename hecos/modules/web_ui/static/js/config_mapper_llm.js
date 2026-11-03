/**
 * config_mapper_llm.js
 * Populates and builds payload for: Backend, LLM providers, Routing,
 * AI/Persona, Bridge, and Text Filters sections.
 * Depends on: config_mapper_utils.js
 */

// ── Rich Models Cache (fetched from /api/chat/options) ─────────────────────
let _richModelsCache = null;
async function _ensureRichModels() {
    if (_richModelsCache) return _richModelsCache;
    try {
        const res = await fetch('/api/chat/options');
        if (res.ok) {
            const data = await res.json();
            _richModelsCache = data.models || [];
        }
    } catch (e) {
        console.warn('[Config] Could not fetch rich model list:', e);
        _richModelsCache = [];
    }
    return _richModelsCache;
}

/**
 * Populate a <select> element with rich model formatting:
 * prefix icons (☁️/🖥️), size tags [7B Q4_0 | 4.7GB], capability badges (⚙️👁️💭).
 * @param {string} id - Element ID
 * @param {string[]} plainList - Plain model names from sysOptions
 * @param {string} currentValue - The currently selected model value
 * @param {string} backendType - 'ollama' | 'cloud' | 'llama_cpp'
 * @param {object[]} richModels - Array of rich model objects from /api/chat/options
 */
function populateRichSelect(id, plainList, currentValue, backendType, richModels) {
    const el = document.getElementById(id);
    if (!el) return;
    el.innerHTML = '';
    if (!plainList || (Array.isArray(plainList) && plainList.length === 0)) return;

    let items = plainList;
    if (plainList && typeof plainList === 'object' && !Array.isArray(plainList)) {
        items = Object.values(plainList);
    }

    const iconMap = { 'tools': '⚙️', 'vision': '👁️', 'thinking': '💭' };
    const descMap = { 'tools': 'Tools/Function Calling', 'vision': 'Vision/Multimodal', 'thinking': 'Thinking/Reasoning' };

    items.forEach(m => {
        const opt = document.createElement('option');
        opt.value = m;

        const richModel = (richModels || []).find(rm => {
            if (backendType === 'cloud') return rm.type === 'cloud' && rm.id === m;
            return rm.provider === backendType && rm.id === m;
        });

        if (richModel) {
            const prefix = richModel.type === 'cloud' ? '☁️ ' : '🖥️ ';
            let suffix = '';
            let sizeTag = '';

            if (richModel.parameter_size || richModel.size_bytes) {
                const parts = [];
                if (richModel.parameter_size) {
                    let p = richModel.parameter_size;
                    if (richModel.quantization_level) p += ' ' + richModel.quantization_level;
                    parts.push(p);
                }
                if (richModel.size_bytes) {
                    parts.push((richModel.size_bytes / (1024*1024*1024)).toFixed(1) + 'GB');
                }
                sizeTag = ' [' + parts.join(' | ') + ']';
            }

            let tooltipText = richModel.name + sizeTag;

            if (richModel.capabilities && richModel.capabilities.length > 0) {
                const icons = richModel.capabilities.map(c => iconMap[c]).filter(Boolean).join('');
                if (icons) suffix = ' ' + icons;
                const descs = richModel.capabilities.map(c => descMap[c]).filter(Boolean).join(', ');
                if (descs) tooltipText += '\nCapabilities: ' + descs;
            }

            opt.textContent = prefix + richModel.name + sizeTag + suffix;
            opt.title = tooltipText;
        } else {
            opt.textContent = m;
            opt.title = m;
        }

        el.appendChild(opt);
    });

    if (currentValue) el.value = currentValue;
}

async function populateBackendUI() {
    const c = window.cfg;
    const sysOptions = window.sysOptions || {};

    // 1. Backend type selector
    const bt = c.backend?.type || 'ollama';
    const btEl = document.getElementById('backend-type');
    if (btEl) {
        btEl.value = bt;
        // Apply card visibility directly — avoids triggering the universal auto-save listener
        if (typeof _applyBackendCardVisibility === 'function') {
            _applyBackendCardVisibility(bt);
        }
    }

    // 2. Cloud / Ollama / Kobold model selectors — rich formatting
    const richModels = await _ensureRichModels();
    populateRichSelect('cloud-model',  sysOptions.all_cloud     || [], c.backend?.cloud?.model,  'cloud',     richModels);
    populateRichSelect('ollama-model', sysOptions.ollama_models || [], c.backend?.ollama?.model, 'ollama',    richModels);

    setVal('cloud-temp',     c.backend?.cloud?.temperature   ?? 0.7);
    setVal('ollama-temp',         c.backend?.ollama?.temperature    ?? 0.3);
    setVal('ollama-gpu',          c.backend?.ollama?.num_gpu        ?? 99);
    setVal('ollama-predict',      c.backend?.ollama?.num_predict    ?? 4096);
    setVal('ollama-ctx',          c.backend?.ollama?.num_ctx        ?? 4096);
    setVal('ollama-top-p',        c.backend?.ollama?.top_p          ?? 0.95);
    setVal('ollama-repeat',       c.backend?.ollama?.repeat_penalty ?? 1.1);
    setVal('ollama-probe-timeout',c.backend?.ollama?.probe_timeout_sec ?? 3);
    setVal('ollama-url',          c.backend?.ollama?.url            || 'http://localhost:11434');
    setVal('ollama-bin-path',     c.backend?.ollama?.binary_path    || '');
    setCheck('ollama-auto-start', c.backend?.ollama?.auto_start_server ?? false);
    if (typeof checkOllamaStatus === 'function') checkOllamaStatus();
    setCheck('ollama-warmup',     c.backend?.ollama?.warmup_model ?? false);
    setVal('ollama-warmup-keepalive', c.backend?.ollama?.warmup_keep_alive || '120m');
    setCheck('ollama-auto-stop',  c.backend?.ollama?.auto_stop_server ?? true);

    setVal('kobold-url',   c.backend?.kobold?.url         || 'http://localhost:5001');
    setVal('kobold-model', c.backend?.kobold?.model       || '');
    setVal('kobold-temp',  c.backend?.kobold?.temperature ?? 0.8);
    setVal('kobold-max',   c.backend?.kobold?.max_length  ?? 512);
    setVal('kobold-top-p', c.backend?.kobold?.top_p       ?? 0.92);
    setVal('kobold-rep',   c.backend?.kobold?.rep_pen     ?? 1.1);

    populateRichSelect('llama-cpp-model', sysOptions.llamacpp_models || [], c.backend?.llama_cpp?.model, 'llama_cpp', richModels);
    setVal('llama-cpp-temp',    c.backend?.llama_cpp?.temperature  ?? 0.7);
    setVal('llama-cpp-gpu',     c.backend?.llama_cpp?.n_gpu_layers ?? -1);
    setVal('llama-cpp-ctx',     c.backend?.llama_cpp?.n_ctx        ?? 32768);
    setVal('llama-cpp-threads', c.backend?.llama_cpp?.threads      ?? 4);
    setVal('llama-cpp-top-p',   c.backend?.llama_cpp?.top_p        ?? 0.95);
    setCheck('llama-cpp-native-tools',  c.backend?.llama_cpp?.native_tool_calling ?? true);
    setCheck('llama-cpp-text-commands', c.backend?.llama_cpp?.text_commands_enabled ?? true);

    // 3. LLM global switches + providers
    const llm = c.llm || {};
    setCheck('llm-allow-cloud', llm.allow_cloud ?? true);
    setCheck('llm-debug',       llm.debug_llm   ?? true);
    const prov = llm.providers || {};
    ['openai','anthropic','groq','gemini'].forEach(p => {
        setVal('models-' + p, (prov[p]?.models || []).join('\n'));
    });

    // 4. Routing engine — reasoning settings
    const rm = c.routing_engine || {};
    setCheck('reasoning-show',      rm.show_reasoning      ?? true);
    setCheck('reasoning-collapsed', rm.reasoning_collapsed ?? true);

    // 5. AI / Persona
    populateSelect('ia-personality-main', sysOptions.personalities || [], c.ai?.active_personality, true);
    const ai = c.ai || {};
    const instrEl   = document.getElementById('ia-instructions');
    const safetyEl  = document.getElementById('ia-safety-instructions');
    const saveInstEl = document.getElementById('ia-save-instructions');
    if (instrEl)    instrEl.value    = ai.special_instructions  || '';
    if (safetyEl)   safetyEl.value   = ai.safety_instructions   || '';
    if (saveInstEl) saveInstEl.checked = ai.save_special_instructions || false;
    setCheck('ia-enable-safety-instructions', ai.enable_safety_instructions ?? true);
    setVal('ia-avatar-size', c.ai?.avatar_size || 'medium');

    if (typeof window.loadPersonaAvatar === 'function') {
        const personaEl = document.getElementById('ia-personality-main');
        if (personaEl && personaEl.value) window.loadPersonaAvatar(personaEl.value);
    }

    // 7. Text Filters
    const fi = c.filters || {};
    const _boolStr = (v, def) => v === true ? 'both' : v === false ? 'none' : v || def;
    setVal('fl-ast',    _boolStr(fi.remove_asterisks,       'both'));
    setVal('fl-tonde',  _boolStr(fi.remove_round_brackets,  'voice'));
    setVal('fl-quadre', _boolStr(fi.remove_square_brackets, 'none'));
    if (window.HecosTextFilters) window.HecosTextFilters.populate(fi.custom_filters || []);

    // Ensure all backend sliders and labels are in sync with loaded config
    if (typeof window.syncOllamaSliders === 'function') {
        window.syncOllamaSliders();
    } else if (typeof syncOllamaSliders === 'function') {
        syncOllamaSliders();
    }
    if (typeof window.syncLlamaCppSliders === 'function') {
        window.syncLlamaCppSliders();
    } else if (typeof syncLlamaCppSliders === 'function') {
        syncLlamaCppSliders();
    }
}

/**
 * Returns backend/LLM/AI/bridge/filters portion of the payload.
 * Merges directly into the `out` object passed by buildPayload().
 */
function buildBackendPayload(out) {
    out.backend        = out.backend        || {};
    out.backend.cloud  = out.backend.cloud  || {};
    out.backend.ollama = out.backend.ollama || {};
    out.backend.kobold = out.backend.kobold || {};

    out.backend.type                  = getV('backend-type',   out.backend.type || 'ollama');

    // Safe retrieval for dynamically populated dropdowns (prevents overwriting with '' if options aren't loaded yet)
    const getSelectV = (id, cfgFallback) => {
        const el = document.getElementById(id);
        if (el && el.options && el.options.length > 0 && el.value !== 'Loading...') return el.value;
        return cfgFallback || '';
    };

    const parseNum = (v, def) => {
        const n = parseInt(v, 10);
        return isNaN(n) ? def : n;
    };
    const parseFloatNum = (v, def) => {
        const n = parseFloat(v);
        return isNaN(n) ? def : n;
    };

    out.backend.cloud.model           = getSelectV('cloud-model', window.cfg.backend?.cloud?.model);
    out.backend.cloud.temperature     = parseFloatNum(getV('cloud-temp',    window.cfg.backend?.cloud?.temperature),     0.7);
    out.backend.ollama.model          = getSelectV('ollama-model', window.cfg.backend?.ollama?.model);
    out.backend.ollama.temperature    = parseFloatNum(getV('ollama-temp',    window.cfg.backend?.ollama?.temperature),    0.3);
    out.backend.ollama.num_gpu        = parseNum(getV('ollama-gpu',        window.cfg.backend?.ollama?.num_gpu),        99);
    out.backend.ollama.num_predict    = parseNum(getV('ollama-predict',    window.cfg.backend?.ollama?.num_predict),    4096);
    out.backend.ollama.num_ctx        = parseNum(getV('ollama-ctx',        window.cfg.backend?.ollama?.num_ctx),        4096);
    out.backend.ollama.top_p          = parseFloatNum(getV('ollama-top-p',   window.cfg.backend?.ollama?.top_p),          0.95);
    out.backend.ollama.repeat_penalty = parseFloatNum(getV('ollama-repeat',  window.cfg.backend?.ollama?.repeat_penalty), 1.1);
    out.backend.ollama.probe_timeout_sec = parseNum(getV('ollama-probe-timeout', window.cfg.backend?.ollama?.probe_timeout_sec), 3);
    out.backend.ollama.url            = getV('ollama-url', window.cfg.backend?.ollama?.url || 'http://localhost:11434');
    out.backend.ollama.binary_path    = getV('ollama-bin-path', window.cfg.backend?.ollama?.binary_path || '');
    out.backend.ollama.auto_start_server = getC('ollama-auto-start', window.cfg.backend?.ollama?.auto_start_server ?? false);
    out.backend.ollama.warmup_model      = getC('ollama-warmup',     window.cfg.backend?.ollama?.warmup_model ?? false);
    out.backend.ollama.warmup_keep_alive = getV('ollama-warmup-keepalive', window.cfg.backend?.ollama?.warmup_keep_alive || '120m');
    out.backend.ollama.auto_stop_server  = getC('ollama-auto-stop',  window.cfg.backend?.ollama?.auto_stop_server ?? true);
    out.backend.kobold.url            = getV('kobold-url',   window.cfg.backend?.kobold?.url);
    out.backend.kobold.model          = getSelectV('kobold-model', window.cfg.backend?.kobold?.model);
    out.backend.kobold.temperature    = parseFloatNum(getV('kobold-temp',  window.cfg.backend?.kobold?.temperature),    0.7);
    out.backend.kobold.max_length     = parseNum(getV('kobold-max',     window.cfg.backend?.kobold?.max_length),     512);
    out.backend.kobold.top_p          = parseFloatNum(getV('kobold-top-p', window.cfg.backend?.kobold?.top_p),          0.95);
    out.backend.kobold.rep_pen        = parseFloatNum(getV('kobold-rep',   window.cfg.backend?.kobold?.rep_pen),        1.1);
    
    out.backend.llama_cpp = out.backend.llama_cpp || {};
    out.backend.llama_cpp.model        = getSelectV('llama-cpp-model', window.cfg.backend?.llama_cpp?.model);
    out.backend.llama_cpp.temperature  = parseFloatNum(getV('llama-cpp-temp',   window.cfg.backend?.llama_cpp?.temperature),  0.7);
    out.backend.llama_cpp.n_gpu_layers = parseNum(getV('llama-cpp-gpu',      window.cfg.backend?.llama_cpp?.n_gpu_layers), -1);
    out.backend.llama_cpp.n_ctx        = parseNum(getV('llama-cpp-ctx',      window.cfg.backend?.llama_cpp?.n_ctx),        32768);
    out.backend.llama_cpp.threads      = parseNum(getV('llama-cpp-threads',  window.cfg.backend?.llama_cpp?.threads),      4);
    out.backend.llama_cpp.top_p        = parseFloatNum(getV('llama-cpp-top-p',  window.cfg.backend?.llama_cpp?.top_p),        0.95);
    out.backend.llama_cpp.native_tool_calling   = getC('llama-cpp-native-tools', window.cfg.backend?.llama_cpp?.native_tool_calling ?? true);
    out.backend.llama_cpp.text_commands_enabled = getC('llama-cpp-text-commands', window.cfg.backend?.llama_cpp?.text_commands_enabled ?? true);

    out.llm = out.llm || {};
    out.llm.allow_cloud = getC('llm-allow-cloud', out.llm.allow_cloud ?? true);
    out.llm.debug_llm   = getC('llm-debug',       out.llm.debug_llm  ?? true);
    out.llm.providers   = out.llm.providers || {};
    ['openai','anthropic','groq','gemini'].forEach(p => {
        out.llm.providers[p] = out.llm.providers[p] || {};
        const currentModels = (out.llm.providers[p].models || []).join('\n');
        const rawM = getV('models-' + p, currentModels).trim();
        if (rawM) out.llm.providers[p].models = rawM.split('\n').map(s => s.trim()).filter(Boolean);
    });

    out.routing_engine = out.routing_engine || {};
    out.routing_engine.show_reasoning      = getC('reasoning-show',      out.routing_engine.show_reasoning      ?? true);
    out.routing_engine.reasoning_collapsed = getC('reasoning-collapsed', out.routing_engine.reasoning_collapsed ?? true);

    out.ai = out.ai || {};
    const personaEl = document.getElementById('ia-personality-main');
    if (personaEl) {
        out.ai.active_personality = personaEl.value;
    } else {
        const emergency = document.querySelector('select[id*="personality"]');
        if (emergency) {
            out.ai.active_personality = emergency.value;
        } else if (window.cfg?.ai?.active_personality) {
            out.ai.active_personality = window.cfg.ai.active_personality;
        } else {
            out.ai.active_personality = 'Hecos_System_Soul.yaml';
        }
    }
    out.ai.avatar_size               = getV('ia-avatar-size', out.ai.avatar_size || 'medium');
    out.ai.special_instructions      = getV('ia-instructions', out.ai.special_instructions);
    if (document.getElementById('ia-safety-instructions')) {
        out.ai.safety_instructions   = getV('ia-safety-instructions', out.ai.safety_instructions);
    }
    if (document.getElementById('ia-enable-safety-instructions')) {
        out.ai.enable_safety_instructions = getC('ia-enable-safety-instructions', out.ai.enable_safety_instructions ?? true);
    }
    out.ai.save_special_instructions = getC('ia-save-instructions', out.ai.save_special_instructions ?? false);

    out.privacy = out.privacy || {};
    out.privacy.default_mode       = getV('pr-default-mode',        out.privacy.default_mode       || 'normal');
    out.privacy.auto_wipe_enabled  = getC('pr-auto-wipe',           out.privacy.auto_wipe_enabled  ?? false);
    out.privacy.incognito_shortcut = getC('pr-incognito-shortcut',  out.privacy.incognito_shortcut ?? true);

    out.filters = out.filters || {};
    out.filters.remove_asterisks       = getV('fl-ast',    out.filters.remove_asterisks       || 'both');
    out.filters.remove_round_brackets  = getV('fl-tonde',  out.filters.remove_round_brackets  || 'voice');
    out.filters.remove_square_brackets = getV('fl-quadre', out.filters.remove_square_brackets || 'none');
    if (window.HecosTextFilters) out.filters.custom_filters = window.HecosTextFilters.extract();
}
