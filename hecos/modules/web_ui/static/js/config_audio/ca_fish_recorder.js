/**
 * ca_fish_recorder.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Fish Speech Timbre Studio: Browser Microphone Recording & Voice Clone Management.
 * Modularized from ca_fish_presets.js to adhere to Hecos architectural standards (<300 lines).
 * ─────────────────────────────────────────────────────────────────────────────
 */

(function () {
    'use strict';

    let _fishRecordStream = null;
    let _fishMediaRecorder = null;
    let _fishAudioChunks = [];
    let _fishRecordTimer = null;
    let _fishRecordStartTime = 0;
    let _fishRecordedBlob = null;

    window.openFishRecordTimbreModal = function () {
        const modal = document.getElementById('modal-fish-record-timbre');
        if (!modal) return;
        modal.style.display = 'flex';
        const nameEl = document.getElementById('fish-rec-name');
        const transEl = document.getElementById('fish-rec-transcript');
        const timerEl = document.getElementById('fish-rec-timer');
        const audioEl = document.getElementById('fish-rec-audio');
        const saveBtn = document.getElementById('fish-rec-save-btn');
        const btn = document.getElementById('fish-rec-btn');

        if (nameEl) nameEl.value = '';
        if (transEl) transEl.value = '';
        if (timerEl) timerEl.textContent = '00:00';
        if (audioEl) audioEl.style.display = 'none';
        if (saveBtn) saveBtn.disabled = true;
        if (btn) {
            btn.innerHTML = '<i class="fas fa-circle" style="color:var(--danger, #ff4d4f);"></i> Start Recording';
            btn.className = 'btn btn-secondary';
        }
    };

    window.closeFishRecordTimbreModal = function () {
        const modal = document.getElementById('modal-fish-record-timbre');
        if (modal) modal.style.display = 'none';
        if (_fishMediaRecorder && _fishMediaRecorder.state === 'recording') {
            _fishMediaRecorder.stop();
        }
        if (_fishRecordStream) {
            _fishRecordStream.getTracks().forEach(t => t.stop());
            _fishRecordStream = null;
        }
        if (_fishRecordTimer) {
            clearInterval(_fishRecordTimer);
            _fishRecordTimer = null;
        }
    };

    window.toggleFishTimbreRecording = async function () {
        const btn = document.getElementById('fish-rec-btn');
        const timerEl = document.getElementById('fish-rec-timer');

        if (_fishMediaRecorder && _fishMediaRecorder.state === 'recording') {
            // Stop recording
            _fishMediaRecorder.stop();
            if (_fishRecordTimer) clearInterval(_fishRecordTimer);
            if (btn) {
                btn.innerHTML = '<i class="fas fa-redo"></i> Record Again';
                btn.className = 'btn btn-secondary';
            }
            return;
        }

        // Start recording
        try {
            _fishRecordStream = await navigator.mediaDevices.getUserMedia({ audio: true });
            _fishAudioChunks = [];
            _fishRecordedBlob = null;

            const mimeType = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : '';
            _fishMediaRecorder = mimeType ? new MediaRecorder(_fishRecordStream, { mimeType }) : new MediaRecorder(_fishRecordStream);

            _fishMediaRecorder.ondataavailable = e => {
                if (e.data.size > 0) _fishAudioChunks.push(e.data);
            };

            _fishMediaRecorder.onstop = async () => {
                const rawBlob = new Blob(_fishAudioChunks, { type: _fishMediaRecorder.mimeType || 'audio/webm' });

                // Convert to clean standard 16-bit WAV using browser OfflineAudioContext
                try {
                    const arrayBuffer = await rawBlob.arrayBuffer();
                    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                    const decodedBuffer = await audioCtx.decodeAudioData(arrayBuffer);

                    if (typeof window._audioBufferToWav === 'function') {
                        _fishRecordedBlob = await window._audioBufferToWav(decodedBuffer);
                    } else {
                        _fishRecordedBlob = rawBlob;
                    }
                } catch (err) {
                    console.warn('[FishTimbre] Fallback to raw blob:', err);
                    _fishRecordedBlob = rawBlob;
                }

                const audioEl = document.getElementById('fish-rec-audio');
                if (audioEl && _fishRecordedBlob) {
                    audioEl.src = URL.createObjectURL(_fishRecordedBlob);
                    audioEl.style.display = 'block';
                }
                const saveBtn = document.getElementById('fish-rec-save-btn');
                if (saveBtn) saveBtn.disabled = false;
            };

            _fishMediaRecorder.start();
            _fishRecordStartTime = Date.now();
            if (btn) {
                btn.innerHTML = '<i class="fas fa-stop"></i> Stop Recording';
                btn.className = 'btn btn-danger';
            }

            _fishRecordTimer = setInterval(() => {
                const elapsed = Math.floor((Date.now() - _fishRecordStartTime) / 1000);
                const m = String(Math.floor(elapsed / 60)).padStart(2, '0');
                const s = String(elapsed % 60).padStart(2, '0');
                if (timerEl) timerEl.textContent = `${m}:${s}`;
            }, 200);

        } catch (e) {
            if (window.showToast) window.showToast("Microphone access denied: " + e.message, "error");
            else alert("Microphone access denied: " + e.message);
        }
    };

    window.saveFishRecordedTimbre = async function () {
        if (!_fishRecordedBlob) {
            if (window.showToast) window.showToast("No audio recorded.", "error");
            return;
        }

        const nameInput = document.getElementById('fish-rec-name');
        const txtInput = document.getElementById('fish-rec-transcript');
        const name = (nameInput?.value || '').trim();
        const transcript = (txtInput?.value || '').trim();

        if (!name) {
            if (window.showToast) window.showToast("Please enter a name for this timbre.", "warning");
            if (nameInput) nameInput.focus();
            return;
        }

        const fd = new FormData();
        fd.append('file', _fishRecordedBlob, `${name}.wav`);
        fd.append('name', name);
        fd.append('transcript', transcript);

        try {
            if (window.showToast) window.showToast("Saving custom timbre to library...", "info");
            const r = await fetch('/api/audio/voice-clones/save-recorded', {
                method: 'POST',
                body: fd
            });
            const res = await r.json();

            if (res.ok) {
                if (window.showToast) window.showToast(`Timbre '${res.name}' created and saved!`, "success");
                window.closeFishRecordTimbreModal();

                if (typeof window.loadFishVoiceCloneList === 'function') await window.loadFishVoiceCloneList();
                if (typeof window.loadVoiceCloneList === 'function') await window.loadVoiceCloneList();

                // Auto-select the newly created timbre
                const sel = document.getElementById('v-fish-clone-select');
                const inp = document.getElementById('v-fish-speaker-wav');
                const refTxt = document.getElementById('v-fish-reference-text');

                if (sel && res.path) {
                    sel.value = res.path;
                    if (inp) inp.value = res.path;
                    if (refTxt && res.transcript) refTxt.value = res.transcript;
                    if (typeof window.saveAudioConfig === 'function') window.saveAudioConfig();
                }
            } else {
                if (window.showToast) window.showToast("Failed to save timbre: " + (res.error || "Unknown"), "error");
            }
        } catch (e) {
            if (window.showToast) window.showToast("Error saving timbre: " + e.message, "error");
        }
    };

    window.deleteFishVoiceClone = async function () {
        const sel = document.getElementById('v-fish-clone-select');
        const current = (document.getElementById('v-fish-speaker-wav')?.value || sel?.value || '').trim();

        if (!current) {
            if (window.showToast) window.showToast("Select a custom voice clone from the library to delete.", "warning");
            return;
        }

        const baseName = current.split('\\').pop().split('/').pop();
        window.hecosConfirm(`Are you sure you want to delete the voice timbre '${baseName}'? This will remove the WAV and transcript from disk.`, async function () {
            try {
                const r = await fetch('/api/audio/voice-clones/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ filename: current })
                });
                const res = await r.json();
                if (res.ok) {
                    if (window.showToast) window.showToast(`Timbre '${baseName}' deleted.`, "info");
                    if (document.getElementById('v-fish-speaker-wav')) document.getElementById('v-fish-speaker-wav').value = '';
                    if (document.getElementById('v-fish-reference-text')) document.getElementById('v-fish-reference-text').value = '';
                    if (typeof window.loadFishVoiceCloneList === 'function') await window.loadFishVoiceCloneList();
                    if (typeof window.loadVoiceCloneList === 'function') await window.loadVoiceCloneList();
                    if (typeof window.saveAudioConfig === 'function') window.saveAudioConfig();
                } else {
                    if (window.showToast) window.showToast("Error deleting: " + res.error, "error");
                }
            } catch (e) {
                if (window.showToast) window.showToast("Delete failed: " + e.message, "error");
            }
        });
    };

})();
