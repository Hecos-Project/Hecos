/**
 * Voice Forge - Voice DNA Radar Chart Visualizer
 * Renders an interactive 6-dimensional polygon with glow effects on HTML5 Canvas.
 */

window.VFRadarChart = class VFRadarChart {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas ? this.canvas.getContext("2d") : null;
    this.axes = [
      { key: "pitch", label: "Pitch" },
      { key: "dynamics", label: "Dynamics" },
      { key: "vocal_tract", label: "Vocal Tract" },
      { key: "brightness", label: "Brightness" },
      { key: "breath", label: "Breath" },
      { key: "roughness", label: "Roughness" }
    ];
    this.currentScores = {
      pitch: 50,
      dynamics: 50,
      vocal_tract: 50,
      brightness: 50,
      breath: 20,
      roughness: 10
    };
    this.targetScores = Object.assign({}, this.currentScores);
    this.animating = false;
  }

  setScores(newScores, animate = true) {
    this.targetScores = Object.assign({}, this.targetScores, newScores);
    if (!animate) {
      this.currentScores = Object.assign({}, this.targetScores);
      this.render();
    } else if (!this.animating) {
      this.animating = true;
      this.animateStep();
    }
  }

  animateStep() {
    let diff = 0;
    for (const key of Object.keys(this.targetScores)) {
      const d = this.targetScores[key] - this.currentScores[key];
      this.currentScores[key] += d * 0.2;
      diff += Math.abs(d);
    }
    this.render();
    if (diff > 0.5) {
      requestAnimationFrame(() => this.animateStep());
    } else {
      this.currentScores = Object.assign({}, this.targetScores);
      this.render();
      this.animating = false;
    }
  }

  render() {
    if (!this.ctx || !this.canvas) return;
    const ctx = this.ctx;
    const w = this.canvas.width;
    const h = this.canvas.height;
    const cx = w / 2;
    const cy = h / 2;
    const radius = Math.min(cx, cy) - 34;

    ctx.clearRect(0, 0, w, h);

    const numAxes = this.axes.length;
    const angleStep = (Math.PI * 2) / numAxes;

    // 1. Draw Concentric Grid Rings
    const rings = [0.2, 0.4, 0.6, 0.8, 1.0];
    ctx.strokeStyle = "rgba(255, 255, 255, 0.08)";
    ctx.lineWidth = 1;

    for (const ring of rings) {
      ctx.beginPath();
      for (let i = 0; i < numAxes; i++) {
        const angle = i * angleStep - Math.PI / 2;
        const x = cx + Math.cos(angle) * (radius * ring);
        const y = cy + Math.sin(angle) * (radius * ring);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.closePath();
      ctx.stroke();
    }

    // 2. Draw Axis Spokes & Labels
    ctx.font = "bold 10px sans-serif";
    ctx.fillStyle = "#94a3b8";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";

    for (let i = 0; i < numAxes; i++) {
      const angle = i * angleStep - Math.PI / 2;
      const x = cx + Math.cos(angle) * radius;
      const y = cy + Math.sin(angle) * radius;

      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(x, y);
      ctx.strokeStyle = "rgba(255, 255, 255, 0.12)";
      ctx.stroke();

      // Label position slightly outside radius
      const lx = cx + Math.cos(angle) * (radius + 18);
      const ly = cy + Math.sin(angle) * (radius + 18);
      ctx.fillText(this.axes[i].label, lx, ly);
    }

    // 3. Draw Polygon Data Fill & Stroke
    ctx.beginPath();
    const points = [];
    for (let i = 0; i < numAxes; i++) {
      const angle = i * angleStep - Math.PI / 2;
      const key = this.axes[i].key;
      const score = Math.max(5, Math.min(100, this.currentScores[key] || 0));
      const valRadius = (score / 100) * radius;
      const px = cx + Math.cos(angle) * valRadius;
      const py = cy + Math.sin(angle) * valRadius;
      points.push({ x: px, y: py, val: score });
      if (i === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }
    ctx.closePath();

    // Fill with glowing gradient
    const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius);
    grad.addColorStop(0, "rgba(139, 92, 246, 0.45)");
    grad.addColorStop(1, "rgba(6, 182, 212, 0.18)");
    ctx.fillStyle = grad;
    ctx.fill();

    // Outline
    ctx.strokeStyle = "#8b5cf6";
    ctx.lineWidth = 2.5;
    ctx.shadowColor = "rgba(139, 92, 246, 0.7)";
    ctx.shadowBlur = 10;
    ctx.stroke();
    ctx.shadowBlur = 0; // Reset shadow

    // 4. Draw Vertex Dots
    for (const pt of points) {
      ctx.beginPath();
      ctx.arc(pt.x, pt.y, 4, 0, Math.PI * 2);
      ctx.fillStyle = "#fff";
      ctx.shadowColor = "#06b6d4";
      ctx.shadowBlur = 8;
      ctx.fill();
      ctx.strokeStyle = "#06b6d4";
      ctx.lineWidth = 1.5;
      ctx.stroke();
      ctx.shadowBlur = 0;
    }
  }
};
