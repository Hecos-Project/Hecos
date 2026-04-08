/**
 * neural_link_logic.js
 * Professional Media Unlocker for Zentra Core.
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
        connectBtn.disabled = true;
        connectBtn.textContent = "SYNCHRONIZING...";

        // 1. UNLOCK AUDIO (The main goal)
        // Browsers require a user gesture to resume AudioContext or play audio tags.
        try {
            // Unlock standard AudioContext
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (AudioContext) {
                const ctx = new AudioContext();
                // Safari requires resume to not be awaited if it fails
                ctx.resume().then(() => {
                    console.log("[NeuralLink] AudioContext resumed successfully.");
                    // Play a subtle welcome beep to confirm path is clear
                    const osc = ctx.createOscillator();
                    const gain = ctx.createGain();
                    osc.connect(gain);
                    gain.connect(ctx.destination);
                    osc.type = 'sine';
                    osc.frequency.setValueAtTime(880, ctx.currentTime);
                    gain.gain.setValueAtTime(0, ctx.currentTime);
                    gain.gain.linearRampToValueAtTime(0.05, ctx.currentTime + 0.1);
                    gain.gain.linearRampToValueAtTime(0, ctx.currentTime + 0.5);
                    osc.start();
                    osc.stop(ctx.currentTime + 0.5);
                    
                    // Expose the global audio context to chat_logic if needed
                    window.ZentraAudioCtx = ctx;
                }).catch(e => console.warn("[NeuralLink] AudioContext resume error:", e));
            }
        } catch (e) {
            console.warn("[NeuralLink] Audio unlock warning:", e);
        }

        // 2. UI TRANSITION
        if (stVoice) { stVoice.textContent = "SUCCESS"; stVoice.className = "status-val active"; }
        setTimeout(() => {
            if (stAudio) { stAudio.textContent = "ACTIVE"; stAudio.className = "status-val active"; }
        }, 300);
        setTimeout(() => {
            if (stVideo) { stVideo.textContent = "SYNCED"; stVideo.className = "status-val active"; }
        }, 600);

        // Final Fade Out
        setTimeout(() => {
            overlay.classList.add('connected');
            console.log("[NeuralLink] Connection established. Interface unlocked.");
            
            // Notify chat logic that we are ready
            document.dispatchEvent(new CustomEvent('zentra:neural_linked'));
        }, 1000);
    }

    connectBtn.addEventListener('click', establishConnection);

    // Also auto-hide if we are already in a sub-page that doesn't need it?
    // (Optional: can use localStorage to skip if recently connected)
    
})();
