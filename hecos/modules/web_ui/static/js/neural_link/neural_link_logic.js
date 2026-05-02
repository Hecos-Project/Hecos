/**
 * neural_link_logic.js
 * Professional Media Unlocker for Hecos.
 * Handles AudioContext resumption and UI transitions.
 */

(function() {
    console.log("[NeuralLink] Module loaded. Waiting for activation...");

    const overlay = document.getElementById('neural-link-overlay');
    const connectBtn = document.getElementById('establish-link-btn');
    const stVoice = document.getElementById('st-voice');
    const stAudio = document.getElementById('st-audio');
    const stVideo = document.getElementById('st-video');

    if (!overlay || !connectBtn) {
        console.error("[NeuralLink] Essential UI elements not found.");
        return;
    }

    async function establishConnection() {
        console.log("[NeuralLink] Establishing Neural Connection...");
        if (connectBtn.disabled) return;
        
        connectBtn.disabled = true;
        connectBtn.className = "connect-btn btn btn-primary loading";
        connectBtn.textContent = "SYNCHRONIZING...";

        // 1. UNLOCK AUDIO (Attempt)
        try {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (AudioContext) {
                const ctx = new AudioContext();
                ctx.resume().then(() => {
                    console.log("[NeuralLink] AudioContext active.");
                    window.HecosAudioCtx = ctx;
                }).catch(e => console.warn("[NeuralLink] Audio init skipped:", e));
            }
        } catch (e) {
            console.warn("[NeuralLink] Audio unlock skipped:", e);
        }

        // 2. UI TRANSITION (Forced proceed)
        if (stVoice) { stVoice.textContent = "SUCCESS"; stVoice.className = "status-val active"; }
        
        setTimeout(() => {
            if (stAudio) { stAudio.textContent = "ACTIVE"; stAudio.className = "status-val active"; }
            if (stVideo) { stVideo.textContent = "SYNCED"; stVideo.className = "status-val active"; }
        }, 300);

        // Final Fade Out - Force hide overlay regardless of audio state
        setTimeout(() => {
            overlay.classList.add('connected');
            console.log("[NeuralLink] Interface unlocked.");
            document.dispatchEvent(new CustomEvent('hecos:neural_linked'));
        }, 800);
    }

    connectBtn.addEventListener('click', establishConnection);

    // Emergency Bypass if user is stuck
    overlay.addEventListener('dblclick', () => {
        console.log("[NeuralLink] Emergency bypass triggered.");
        establishConnection();
    });
    
})();
