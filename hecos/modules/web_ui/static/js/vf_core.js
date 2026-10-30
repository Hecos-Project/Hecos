/**
 * Voice Forge - Studio Core Entry Point
 * Initializes components, binds window lifecycle, and sets up canvas observers.
 */

window.initVoiceForge = async function() {
  const panel = document.getElementById("tab-voice-forge");
  if (!panel) return;

  console.log("[VoiceForge] Initializing Voice Forge Studio...");

  if (window.VFMixer) {
    await window.VFMixer.init();
  }
  if (window.VFPresets) {
    await window.VFPresets.init();
  }

  // Handle high-DPI canvas resizing
  const canvases = ["vf-canvas-radar", "vf-canvas-spectro"];
  canvases.forEach(id => {
    const c = document.getElementById(id);
    if (c) {
      const rect = c.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      const w = rect.width > 0 ? rect.width : (id.includes('radar') ? 280 : 320);
      const h = rect.height > 0 ? rect.height : (id.includes('radar') ? 280 : 120);
      c.width = w * dpr;
      c.height = h * dpr;
      const ctx = c.getContext("2d");
      if (ctx) ctx.scale(dpr, dpr);
    }
  });

  if (window.VFMixer && window.VFMixer.radar) {
    window.VFMixer.radar.render();
  }
};

// Global click listener to catch when user navigates to Voice Forge tab
document.addEventListener("click", (e) => {
  const tabBtn = e.target.closest('[onclick*="voice-forge"], [onclick*="voice_forge"]');
  if (tabBtn) {
    setTimeout(() => {
      if (window.initVoiceForge) window.initVoiceForge();
    }, 150);
  }
});

// Auto-init fallback
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    if (document.getElementById("tab-voice-forge")) {
      window.initVoiceForge();
    }
  });
} else {
  setTimeout(() => {
    if (document.getElementById("tab-voice-forge")) {
      window.initVoiceForge();
    }
  }, 200);
}
