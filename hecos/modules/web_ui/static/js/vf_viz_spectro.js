/**
 * Voice Forge - Spectrogram & Pitch Contour Visualizer
 * Renders Mel-spectrogram energy heatmaps and F0 pitch trajectory on HTML5 Canvas.
 */

window.VFSpectrogram = class VFSpectrogram {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas ? this.canvas.getContext("2d") : null;
  }

  // Inferno/Magma-style thermal color map: 0.0 (dark blue/purple) -> 0.5 (magenta/amber) -> 1.0 (bright yellow/white)
  getColor(v) {
    v = Math.max(0, Math.min(1, v));
    let r, g, b;
    if (v < 0.25) {
      const t = v / 0.25;
      r = Math.floor(10 + 40 * t);
      g = Math.floor(10 + 20 * t);
      b = Math.floor(30 + 100 * t);
    } else if (v < 0.5) {
      const t = (v - 0.25) / 0.25;
      r = Math.floor(50 + 120 * t);
      g = Math.floor(30 + 30 * t);
      b = Math.floor(130 - 30 * t);
    } else if (v < 0.75) {
      const t = (v - 0.5) / 0.25;
      r = Math.floor(170 + 70 * t);
      g = Math.floor(60 + 90 * t);
      b = Math.floor(100 - 80 * t);
    } else {
      const t = (v - 0.75) / 0.25;
      r = Math.floor(240 + 15 * t);
      g = Math.floor(150 + 105 * t);
      b = Math.floor(20 + 200 * t);
    }
    return `rgb(${r},${g},${b})`;
  }

  render(spectroData) {
    if (!this.ctx || !this.canvas || !spectroData) return;
    const ctx = this.ctx;
    const w = this.canvas.width;
    const h = this.canvas.height;
    ctx.clearRect(0, 0, w, h);

    const melMatrix = spectroData.mel_matrix; // rows = mel bands (low to high), cols = time
    if (!melMatrix || !melMatrix.length) {
      ctx.fillStyle = "#1e293b";
      ctx.fillRect(0, 0, w, h);
      ctx.fillStyle = "#64748b";
      ctx.font = "11px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("No acoustic data analyzed yet", w / 2, h / 2);
      return;
    }

    const nMels = melMatrix.length;
    const nFrames = melMatrix[0].length;
    const cellW = w / nFrames;
    const cellH = h / nMels;

    // 1. Draw Spectrogram Heatmap (Low frequencies at bottom, High frequencies at top)
    for (let m = 0; m < nMels; m++) {
      const y = h - (m + 1) * cellH;
      const row = melMatrix[m];
      for (let t = 0; t < nFrames; t++) {
        const val = row[t] || 0;
        ctx.fillStyle = this.getColor(val);
        ctx.fillRect(t * cellW, y, cellW + 0.6, cellH + 0.6);
      }
    }

    // 2. Draw Pitch Contour Overlay
    const pitch = spectroData.pitch_contour || [];
    if (pitch.length > 1) {
      ctx.beginPath();
      let started = false;
      const stepX = w / (pitch.length - 1);

      for (let i = 0; i < pitch.length; i++) {
        const f0 = pitch[i];
        if (f0 > 40) {
          // Normalize pitch between 50 Hz and 400 Hz for canvas display height
          const normY = Math.max(0, Math.min(1, (f0 - 50) / 350));
          const py = h - (normY * (h * 0.75) + h * 0.1);
          const px = i * stepX;
          if (!started) {
            ctx.moveTo(px, py);
            started = true;
          } else {
            ctx.lineTo(px, py);
          }
        } else {
          started = false;
        }
      }

      ctx.strokeStyle = "#10b981";
      ctx.lineWidth = 2;
      ctx.shadowColor = "rgba(16, 185, 129, 0.8)";
      ctx.shadowBlur = 6;
      ctx.stroke();
      ctx.shadowBlur = 0;
    }
  }
};
