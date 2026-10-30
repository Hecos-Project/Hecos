/* ⚡ SOUL FORGE: gp_kokoro.js */

window.sfApplyKokoroPreset = function(presetName) {
    if (!presetName || !window.sfState.kokoroPresets || !window.sfState.kokoroPresets[presetName]) {
        const infSel = document.getElementById('sf-kokoro-inference-preset-select');
        if (infSel) infSel.value = "";
        if (window.sfUpdateCloneState) window.sfUpdateCloneState();
        window.sfDirty();
        return;
    }

    const p = window.sfState.kokoroPresets[presetName];

    const setVal = (id, val) => {
        if (val !== undefined && val !== null) {
            const el = document.getElementById(id);
            if (el) {
                el.value = val;
                window.sfUpdateSliderVal(el, id.replace('sf-', 'sf-val-'));
            }
        }
    };

    setVal('sf-kokoro-speed', p.speed ?? 0.95);
    setVal('sf-kokoro-silence', p.sentence_silence ?? 0.15);
    setVal('sf-kokoro-alpha', p.alpha ?? 1.0);
    setVal('sf-kokoro-beta', p.beta ?? 1.0);
    setVal('sf-kokoro-volume', p.volume ?? 1.0);

    // Try to match or set associated inference preset
    let matchedInf = p.inference_preset || "";
    if (!matchedInf && window.sfState.kokoroInferencePresets) {
        for (const [k, inf] of Object.entries(window.sfState.kokoroInferencePresets)) {
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
    const infSel = document.getElementById('sf-kokoro-inference-preset-select');
    if (infSel) infSel.value = matchedInf;

    if (window.sfUpdateCloneState) window.sfUpdateCloneState();
    window.sfDirty();
};

window.sfApplyKokoroInferencePreset = function(presetName) {
    if (!presetName || !window.sfState.kokoroInferencePresets || !window.sfState.kokoroInferencePresets[presetName]) return;
    const p = window.sfState.kokoroInferencePresets[presetName];

    const setVal = (id, val) => {
        if (val !== undefined && val !== null) {
            const el = document.getElementById(id);
            if (el) {
                el.value = val;
                window.sfUpdateSliderVal(el, id.replace('sf-', 'sf-val-'));
            }
        }
    };

    setVal('sf-kokoro-speed', p.speed);
    setVal('sf-kokoro-silence', p.sentence_silence);
    setVal('sf-kokoro-alpha', p.alpha);
    setVal('sf-kokoro-beta', p.beta);
    setVal('sf-kokoro-volume', p.volume);

    window.sfDirty();
};

window.sfSaveNewKokoroInferencePreset = function() {
    window.hecosPrompt("Enter the name for the new Kokoro Inference Preset:", async function(name) {
        if (!name || !name.trim()) return;
        name = name.trim();

        const getNum = (id) => { const v = document.getElementById(id)?.value; return v ? parseFloat(v) : null; };
        const p = {
            speed: getNum('sf-kokoro-speed') ?? 1.0,
            sentence_silence: getNum('sf-kokoro-silence') ?? 0.0,
            alpha: getNum('sf-kokoro-alpha') ?? 1.0,
            beta: getNum('sf-kokoro-beta') ?? 1.0,
            volume: getNum('sf-kokoro-volume') ?? 1.0,
            normalize: true
        };

        if (!window.sfState.kokoroInferencePresets) window.sfState.kokoroInferencePresets = {};
        window.sfState.kokoroInferencePresets[name] = p;

        try {
            const res = await fetch('/api/audio/config', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({ kokoro_inference_presets: window.sfState.kokoroInferencePresets })
            });
            if (res.ok) {
                await window.sfLoadData();
                const sel = document.getElementById('sf-kokoro-inference-preset-select');
                if (sel) sel.value = name;
                if (window.showToast) window.showToast(`Kokoro Inference Preset '${name}' saved!`, "success");
            }
        } catch(e) {}
    });
};

window.sfOverwriteKokoroInferencePreset = function() {
    const name = document.getElementById('sf-kokoro-inference-preset-select')?.value;
    if (!name) {
        if (window.showToast) window.showToast("No Kokoro Inference Preset selected for overwrite.", "error");
        return;
    }

    window.hecosConfirm(`Do you really want to overwrite the Kokoro Inference Preset "${name}"?`, async function() {
        const getNum = (id) => { const v = document.getElementById(id)?.value; return v ? parseFloat(v) : null; };
        const p = {
            speed: getNum('sf-kokoro-speed') ?? 1.0,
            sentence_silence: getNum('sf-kokoro-silence') ?? 0.0,
            alpha: getNum('sf-kokoro-alpha') ?? 1.0,
            beta: getNum('sf-kokoro-beta') ?? 1.0,
            volume: getNum('sf-kokoro-volume') ?? 1.0,
            normalize: true
        };

        if (!window.sfState.kokoroInferencePresets) window.sfState.kokoroInferencePresets = {};
        window.sfState.kokoroInferencePresets[name] = p;

        try {
            const res = await fetch('/api/audio/config', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({ kokoro_inference_presets: window.sfState.kokoroInferencePresets })
            });
            if (res.ok) {
                await window.sfLoadData();
                const sel = document.getElementById('sf-kokoro-inference-preset-select');
                if (sel) sel.value = name;
                if (window.showToast) window.showToast(`Kokoro Inference Preset '${name}' updated!`, "success");
            }
        } catch(e) {}
    });
};

window.sfDeleteKokoroInferencePreset = function() {
    const name = document.getElementById('sf-kokoro-inference-preset-select')?.value;
    if (!name) {
        if (window.showToast) window.showToast("No Kokoro Inference Preset selected to delete.", "error");
        return;
    }

    window.hecosConfirm(`Are you sure you want to delete the Kokoro Inference Preset "${name}"?`, async function() {
        if (window.sfState.kokoroInferencePresets) {
            delete window.sfState.kokoroInferencePresets[name];
        }

        try {
            const res = await fetch('/api/audio/config', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({ kokoro_inference_presets: window.sfState.kokoroInferencePresets })
            });
            if (res.ok) {
                await window.sfLoadData();
                const sel = document.getElementById('sf-kokoro-inference-preset-select');
                if (sel) sel.value = "";
                if (window.showToast) window.showToast(`Kokoro Inference Preset '${name}' deleted.`, "info");
            }
        } catch(e) {}
    });
};
