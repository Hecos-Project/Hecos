/**
 * config_mapper_llm.js
 * Populates and builds payload for: Backend, LLM providers, Routing,
 * AI/Persona, Bridge, and Text Filters sections.
 * Depends on: config_mapper_utils.js
 */

function populateBackendUI() {
    const c = window.cfg;
    const sysOptions = window.sysOptions || {};

    // 1. Backend type selector
    const bt = c.backend?.type || 'ollama';
    const btEl = document.getElementById('backend-type');
    if (btEl) {
        btEl.value = bt;
        btEl.dispatchEvent(new Event('change'));
    }

    // 2. Cloud / Ollama / Kobold model selectors
    populateSelect('cloud-model',  sysOptions.all_cloud       || [], c.backend?.cloud?.model);
    populateSelect('ollama-model', sysOptions.ollama_models   || [], c.backend?.ollama?.model);

    setVal('cloud-temp',     c.backend?.cloud?.temperature   ?? 0.7);
    setVal('ollama-temp',    c.backend?.ollama?.temperature  ?? 0.3);
    setVal('ollama-gpu',     c.backend?.ollama?.num_gpu      ?? 25);
    setVal('ollama-predict', c.backend?.ollama?.num_predict  ?? 250);
    setVal('ollama-ctx',     c.backend?.ollama?.num_ctx      ?? 4096);
    setVal('ollama-top-p',   c.backend?.ollama?.top_p        ?? 0.9);
    setVal('ollama-repeat',  c.backend?.ollama?.repeat_penalty ?? 1.1);

    setVal('kobold-url',   c.backend?.kobold?.url         || 'http://localhost:5001');
    setVal('kobold-model', c.backend?.kobold?.model       || '');
    setVal('kobold-temp',  c.backend?.kobold?.temperature ?? 0.8);
    setVal('kobold-max',   c.backend?.kobold?.max_length  ?? 512);
    setVal('kobold-top-p', c.backend?.kobold?.top_p       ?? 0.92);
    setVal('kobold-rep',   c.backend?.kobold?.rep_pen     ?? 1.1);

    // 3. LLM global switches + providers
    const llm = c.llm || {};
    setCheck('llm-allow-cloud', llm.allow_cloud ?? true);
    setCheck('llm-debug',       llm.debug_llm   ?? true);
    const prov = llm.providers || {};
    ['openai','anthropic','groq','gemini'].forEach(p => {
        setVal('models-' + p, (prov[p]?.models || []).join('\n'));
    });

    // 4. Routing engine
    const rm = c.routing_engine || {};
    setVal('route-mode',   rm.mode          || 'auto');
    setVal('route-models', rm.legacy_models || '');

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

    // 6. Bridge
    const br = c.bridge || {};
    setCheck('br-processor',    br.use_processor       ?? false);
    setCheck('br-think-tags',   br.remove_think_tags   ?? true);
    setCheck('br-debug',        br.debug_log            ?? true);
    setCheck('br-tools',        br.enable_tools         ?? true);
    setCheck('br-voice-stt',    br.webui_voice_stt      ?? true);
    setCheck('br-voice-enabled',br.webui_voice_enabled  ?? false);
    setVal('br-delay',          br.chunk_delay_ms       ?? 0);

    // 7. Text Filters
    const fi = c.filters || {};
    const _boolStr = (v, def) => v === true ? 'both' : v === false ? 'none' : v || def;
    setVal('fl-ast',    _boolStr(fi.remove_asterisks,       'both'));
    setVal('fl-tonde',  _boolStr(fi.remove_round_brackets,  'voice'));
    setVal('fl-quadre', _boolStr(fi.remove_square_brackets, 'none'));
    if (window.HecosTextFilters) window.HecosTextFilters.populate(fi.custom_filters || []);
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

    out.backend.type                  = getV('backend-type',   out.backend.type || 'cloud');
    out.backend.cloud.model           = getV('cloud-model',    out.backend.cloud.model);
    out.backend.cloud.temperature     = parseFloat(getV('cloud-temp',    out.backend.cloud.temperature))     || 0.7;
    out.backend.ollama.model          = getV('ollama-model',   out.backend.ollama.model);
    out.backend.ollama.temperature    = parseFloat(getV('ollama-temp',   out.backend.ollama.temperature))    || 0.3;
    out.backend.ollama.num_gpu        = parseInt(getV('ollama-gpu',      out.backend.ollama.num_gpu))        || 33;
    out.backend.ollama.num_predict    = parseInt(getV('ollama-predict',  out.backend.ollama.num_predict))    || 1024;
    out.backend.ollama.num_ctx        = parseInt(getV('ollama-ctx',      out.backend.ollama.num_ctx))        || 4096;
    out.backend.ollama.top_p          = parseFloat(getV('ollama-top-p',  out.backend.ollama.top_p))          || 0.95;
    out.backend.ollama.repeat_penalty = parseFloat(getV('ollama-repeat', out.backend.ollama.repeat_penalty)) || 1.1;
    out.backend.kobold.url            = getV('kobold-url',   out.backend.kobold.url);
    out.backend.kobold.model          = getV('kobold-model', out.backend.kobold.model);
    out.backend.kobold.temperature    = parseFloat(getV('kobold-temp',  out.backend.kobold.temperature))    || 0.7;
    out.backend.kobold.max_length     = parseInt(getV('kobold-max',     out.backend.kobold.max_length))     || 512;
    out.backend.kobold.top_p          = parseFloat(getV('kobold-top-p', out.backend.kobold.top_p))          || 0.95;
    out.backend.kobold.rep_pen        = parseFloat(getV('kobold-rep',   out.backend.kobold.rep_pen))        || 1.1;

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
    out.routing_engine.mode          = getV('route-mode',   out.routing_engine.mode || 'auto');
    out.routing_engine.legacy_models = getV('route-models', out.routing_engine.legacy_models);

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

    out.bridge = out.bridge || {};
    out.bridge.use_processor       = getC('br-processor',    out.bridge.use_processor      ?? false);
    out.bridge.remove_think_tags   = getC('br-think-tags',   out.bridge.remove_think_tags  ?? true);
    out.bridge.debug_log           = getC('br-debug',        out.bridge.debug_log          ?? true);
    out.bridge.enable_tools        = getC('br-tools',        out.bridge.enable_tools       ?? true);
    out.bridge.webui_voice_stt     = getC('br-voice-stt',    out.bridge.webui_voice_stt    ?? true);
    out.bridge.webui_voice_enabled = getC('br-voice-enabled',out.bridge.webui_voice_enabled ?? false);
    out.bridge.chunk_delay_ms      = parseInt(getV('br-delay', out.bridge.chunk_delay_ms)) || 0;

    out.filters = out.filters || {};
    out.filters.remove_asterisks       = getV('fl-ast',    out.filters.remove_asterisks       || 'both');
    out.filters.remove_round_brackets  = getV('fl-tonde',  out.filters.remove_round_brackets  || 'voice');
    out.filters.remove_square_brackets = getV('fl-quadre', out.filters.remove_square_brackets || 'none');
    if (window.HecosTextFilters) out.filters.custom_filters = window.HecosTextFilters.extract();
}
