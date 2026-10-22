/* ⚡ SESSION OVERRIDES: so_kokoro.js */

window.soApplyKokoroPreset = function(presetName) {
    if (!presetName || !window.soState.kokoroPresets || !window.soState.kokoroPresets[presetName]) {
        const infSel = document.getElementById('so-kokoro-inference-preset-select');
        if (infSel) infSel.value = "";
        if (window.soUpdateCloneState) window.soUpdateCloneState();
        window.soDirty();
        return;
    }

    const p = window.soState.kokoroPresets[presetName];

    const setVal = (id, val) => {
        if (val !== undefined && val !== null) {
            const el = document.getElementById(id);
            if (el) {
                el.value = val;
                window.soUpdateSliderVal(el, id.replace('so-', 'so-val-'));
            }
        }
    };

    setVal('so-kokoro-speed', p.speed ?? 1.0);
    setVal('so-kokoro-silence', p.sentence_silence ?? 0.0);
    setVal('so-kokoro-alpha', p.alpha ?? 1.0);
    setVal('so-kokoro-beta', p.beta ?? 1.0);
    setVal('so-kokoro-volume', p.volume ?? 1.0);

    // Try to match or set associated inference preset
    let matchedInf = p.inference_preset || "";
    if (!matchedInf && window.soState.kokoroInferencePresets) {
        for (const [k, inf] of Object.entries(window.soState.kokoroInferencePresets)) {
            if (
                (!p.speed || Math.abs(inf.speed - p.speed) < 0.01) &&
                (!p.alpha || Math.abs(inf.alpha - p.alpha) < 0.01) &&
                (!p.beta || Math.abs(inf.beta - p.beta) < 0.01) &&
                (!p.sentence_silence || Math.abs(inf.sentence_silence - p.sentence_silence) < 0.01) &&
                (!p.volume || Math.abs(inf.volume - p.volume) < 0.01)
            ) {
                matchedInf = k;
                break;
            }
        }
    }
    const infSel = document.getElementById('so-kokoro-inference-preset-select');
    if (infSel) infSel.value = matchedInf;

    if (window.soUpdateCloneState) window.soUpdateCloneState();
    window.soDirty();
};

window.soApplyKokoroInferencePreset = function(presetName) {
    if (!presetName || !window.soState.kokoroInferencePresets || !window.soState.kokoroInferencePresets[presetName]) return;
    const p = window.soState.kokoroInferencePresets[presetName];

    const setVal = (id, val) => {
        if (val !== undefined && val !== null) {
            const el = document.getElementById(id);
            if (el) {
                el.value = val;
                window.soUpdateSliderVal(el, id.replace('so-', 'so-val-'));
            }
        }
    };

    setVal('so-kokoro-speed', p.speed);
    setVal('so-kokoro-silence', p.sentence_silence);
    setVal('so-kokoro-alpha', p.alpha);
    setVal('so-kokoro-beta', p.beta);
    setVal('so-kokoro-volume', p.volume);

    window.soDirty();
};

window.soSaveNewKokoroInferencePreset = function() {
    window.hecosPrompt("Enter the name for the new Kokoro Inference Preset:", async function(name) {
        if (!name || !name.trim()) return;
        name = name.trim();

        const getNum = (id) => { const v = document.getElementById(id)?.value; return v ? parseFloat(v) : null; };
        const p = {
            speed: getNum('so-kokoro-speed') ?? 1.0,
            sentence_silence: getNum('so-kokoro-silence') ?? 0.0,
            alpha: getNum('so-kokoro-alpha') ?? 1.0,
            beta: getNum('so-kokoro-beta') ?? 1.0,
            volume: getNum('so-kokoro-volume') ?? 1.0,
            normalize: true
        };

        if (!window.soState.kokoroInferencePresets) window.soState.kokoroInferencePresets = {};
        window.soState.kokoroInferencePresets[name] = p;

        try {
            const res = await fetch('/api/audio/config', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({ kokoro_inference_presets: window.soState.kokoroInferencePresets })
            });
            if (res.ok) {
                await window.soLoadData();
                const sel = document.getElementById('so-kokoro-inference-preset-select');
                if (sel) sel.value = name;
                if (window.showToast) window.showToast(`Kokoro Inference Preset '${name}' saved!`, "success");
            }
        } catch(e) {}
    });
};

window.soOverwriteKokoroInferencePreset = function() {
    const name = document.getElementById('so-kokoro-inference-preset-select')?.value;
    if (!name) {
        if (window.showToast) window.showToast("No Kokoro Inference Preset selected for overwrite.", "error");
        return;
    }

    window.hecosConfirm(`Do you really want to overwrite the Kokoro Inference Preset "${name}"?`, async function() {
        const getNum = (id) => { const v = document.getElementById(id)?.value; return v ? parseFloat(v) : null; };
        const p = {
            speed: getNum('so-kokoro-speed') ?? 1.0,
            sentence_silence: getNum('so-kokoro-silence') ?? 0.0,
            alpha: getNum('so-kokoro-alpha') ?? 1.0,
            beta: getNum('so-kokoro-beta') ?? 1.0,
            volume: getNum('so-kokoro-volume') ?? 1.0,
            normalize: true
        };

        if (!window.soState.kokoroInferencePresets) window.soState.kokoroInferencePresets = {};
        window.soState.kokoroInferencePresets[name] = p;

        try {
            const res = await fetch('/api/audio/config', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({ kokoro_inference_presets: window.soState.kokoroInferencePresets })
            });
            if (res.ok) {
                await window.soLoadData();
                const sel = document.getElementById('so-kokoro-inference-preset-select');
                if (sel) sel.value = name;
                if (window.showToast) window.showToast(`Kokoro Inference Preset '${name}' updated!`, "success");
            }
        } catch(e) {}
    });
};

window.soDeleteKokoroInferencePreset = function() {
    const name = document.getElementById('so-kokoro-inference-preset-select')?.value;
    if (!name) {
        if (window.showToast) window.showToast("No Kokoro Inference Preset selected to delete.", "error");
        return;
    }

    window.hecosConfirm(`Are you sure you want to delete the Kokoro Inference Preset "${name}"?`, async function() {
        if (window.soState.kokoroInferencePresets) {
            delete window.soState.kokoroInferencePresets[name];
        }

        try {
            const res = await fetch('/api/audio/config', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({ kokoro_inference_presets: window.soState.kokoroInferencePresets })
            });
            if (res.ok) {
                await window.soLoadData();
                const sel = document.getElementById('so-kokoro-inference-preset-select');
                if (sel) sel.value = "";
                if (window.showToast) window.showToast(`Kokoro Inference Preset '${name}' deleted.`, "info");
            }
        } catch(e) {}
    });
};
