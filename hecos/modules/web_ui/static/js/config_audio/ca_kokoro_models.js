/**
 * ca_kokoro_models.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Kokoro Neural Model Management & Folder Browsing.
 * Modularized from ca_tts_utils.js to adhere to Hecos architectural standards (<150 lines).
 * ─────────────────────────────────────────────────────────────────────────────
 */

(function () {
    'use strict';

    async function loadKokoroModelList() {
        const select = document.getElementById('v-kokoro-model-select');
        const hiddenInput = document.getElementById('v-kokoro-model');
        if (!select) return;

        try {
            const res = await fetch('/api/audio/kokoro/models');
            if (!res.ok) return;
            const data = await res.json();
            if (!data.ok || !Array.isArray(data.models)) return;

            const currentVal = hiddenInput ? (hiddenInput.value || '').trim() : '';
            select.innerHTML = '';

            let foundMatch = false;
            data.models.forEach(m => {
                const opt = document.createElement('option');
                opt.value = m.id;
                opt.textContent = m.name;
                opt.dataset.path = m.path;
                opt.dataset.type = m.type;
                if (m.id === currentVal) {
                    opt.selected = true;
                    foundMatch = true;
                }
                select.appendChild(opt);
            });

            if (currentVal && !foundMatch) {
                const opt = document.createElement('option');
                opt.value = currentVal;
                opt.textContent = `Custom: ${currentVal.split('\\').pop().split('/').pop()}`;
                opt.dataset.path = currentVal;
                opt.dataset.type = 'custom';
                opt.selected = true;
                select.appendChild(opt);
            }

            updateKokoroModelUI();
        } catch (e) {
            console.warn("[KokoroModels] Failed to load Kokoro model list:", e);
        }
    }

    function updateKokoroModelUI() {
        const select = document.getElementById('v-kokoro-model-select');
        const hiddenInput = document.getElementById('v-kokoro-model');
        const pathDisplay = document.getElementById('v-kokoro-model-path-display');
        const badge = document.getElementById('v-kokoro-model-badge');
        if (!select) return;

        const val = select.value || '';
        if (hiddenInput) hiddenInput.value = val;

        if (!val) {
            if (pathDisplay) pathDisplay.innerHTML = '📁 Active Path: <code>Default integrated local model</code>';
            if (badge) {
                badge.textContent = 'Kokoro-82M v1.0';
                badge.className = 'badge-pill badge-accent';
            }
        } else {
            if (pathDisplay) pathDisplay.innerHTML = `📁 Active Path: <code>${val}</code>`;
            if (badge) {
                badge.textContent = 'Custom Model';
                badge.className = 'badge-pill badge-ok';
            }
        }
    }

    function onKokoroModelSelectChange() {
        updateKokoroModelUI();
    }

    function setKokoroModelPath(path) {
        const select = document.getElementById('v-kokoro-model-select');
        const hiddenInput = document.getElementById('v-kokoro-model');
        if (hiddenInput) hiddenInput.value = path || '';

        let found = false;
        if (select) {
            for (let i = 0; i < select.options.length; i++) {
                if (select.options[i].value === path) {
                    select.selectedIndex = i;
                    found = true;
                    break;
                }
            }
            if (!found && path) {
                const opt = document.createElement('option');
                opt.value = path;
                opt.textContent = `Custom: ${path.split('\\').pop().split('/').pop()}`;
                opt.selected = true;
                select.appendChild(opt);
            }
        }
        updateKokoroModelUI();
    }

    async function browseKokoroModelPath() {
        const currentVal = document.getElementById('v-kokoro-model')?.value || '';
        const initialPath = currentVal || 'C:\\Hecos\\hecos\\models\\kokoro';
        if (typeof HecosFilePicker !== 'undefined') {
            HecosFilePicker.open({
                title: 'Select Kokoro Model Weights (.pth) or Model Folder',
                initialPath: initialPath,
                onSelect: (path) => {
                    if (path) {
                        setKokoroModelPath(path);
                        if (window.showToast) window.showToast('Selected model: ' + path.split('\\').pop(), 'info');
                    }
                }
            });
        } else {
            const customPath = prompt("Enter full path to Kokoro model (.pth) or directory:", initialPath);
            if (customPath !== null) {
                setKokoroModelPath(customPath.trim());
            }
        }
    }

    async function openKokoroModelsFolder() {
        try {
            const res = await fetch('/api/audio/kokoro/open-folder', { method: 'POST' });
            const data = await res.json();
            if (data.ok) {
                if (window.showToast) window.showToast("Opened Kokoro models folder in File Explorer!", "info");
            } else {
                if (window.showToast) window.showToast("Error opening folder: " + data.error, "error");
            }
        } catch (e) {
            if (window.showToast) window.showToast("Error opening folder: " + e.message, "error");
        }
    }

    function copyKokoroModelsPath() {
        const p = "C:\\Hecos\\hecos\\models\\kokoro";
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(p).then(() => {
                if (window.showToast) window.showToast("Copied path to clipboard: " + p, "success");
            }).catch(() => {
                prompt("Kokoro models directory path:", p);
            });
        } else {
            prompt("Kokoro models directory path:", p);
        }
    }

    window.loadKokoroModelList = loadKokoroModelList;
    window.updateKokoroModelUI = updateKokoroModelUI;
    window.onKokoroModelSelectChange = onKokoroModelSelectChange;
    window.setKokoroModelPath = setKokoroModelPath;
    window.browseKokoroModelPath = browseKokoroModelPath;
    window.openKokoroModelsFolder = openKokoroModelsFolder;
    window.copyKokoroModelsPath = copyKokoroModelsPath;

})();
