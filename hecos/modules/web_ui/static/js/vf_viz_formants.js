/**
 * Voice Forge - Vocal Tract & Formant Visualizer
 * Displays dominant formants (F1, F2, F3, F4) and the acoustic vocal tract resonance profile.
 */

window.VFFormantVisualizer = class VFFormantVisualizer {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
  }

  render(formants = [500, 1500, 2500, 3500], tractRatio = 1.0) {
    if (!this.container) return;

    const fNames = ["F1 (Throat)", "F2 (Mouth)", "F3 (Cavity)", "F4 (Sheen)"];
    const colors = ["#8b5cf6", "#06b6d4", "#10b981", "#f59e0b"];

    let html = `<div style="display:flex; flex-direction:column; gap:6px; width:100%;">`;
    for (let i = 0; i < 4; i++) {
      const fHz = formants[i] || (500 * (i + 1));
      const pct = Math.min(100, Math.max(5, (fHz / 4500) * 100));
      html += `
        <div style="display:flex; flex-direction:column; gap:2px;">
          <div style="display:flex; justify-content:space-between; font-size:0.68rem;">
            <span style="color:#94a3b8; font-weight:600;">${fNames[i]}</span>
            <span style="color:${colors[i]}; font-family:monospace; font-weight:700;">${Math.round(fHz)} Hz</span>
          </div>
          <div style="width:100%; height:4px; background:rgba(255,255,255,0.08); border-radius:2px; overflow:hidden;">
            <div style="width:${pct}%; height:100%; background:${colors[i]}; transition:width 0.3s ease;"></div>
          </div>
        </div>
      `;
    }
    html += `</div>`;
    this.container.innerHTML = html;
  }
};
