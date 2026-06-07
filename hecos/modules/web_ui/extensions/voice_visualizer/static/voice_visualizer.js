/**
 * Voice Visualizer Widget — JavaScript Engine v3
 * ─────────────────────────────────────────────────────────────────
 * Mouth renderers now use bezier curves drawn at 1/3 resolution
 * then scaled up 3x with imageSmoothingEnabled=false, giving a
 * natural "chunky pixel" 80s look with realistic lip shapes.
 * ─────────────────────────────────────────────────────────────────
 */

(function () {
    "use strict";

    /* ── DOM refs ────────────────────────────────────────────── */
    const modeSelect  = document.getElementById("vv-mode-select");
    const stageKitt   = document.getElementById("vv-kitt");
    const stageEq     = document.getElementById("vv-audio-bars");
    const stageSine   = document.getElementById("vv-sine-wave");
    const stageOrb    = document.getElementById("vv-pulsing-orb");
    const stageMouth  = document.getElementById("vv-mouth");
    const statusDiv   = document.getElementById("vv-status-bar");
    const statusLabel = document.getElementById("vv-status-label");

    /* ── State ───────────────────────────────────────────────── */
    let currentMode  = localStorage.getItem("hecos-vv-mode") || "kitt";
    let isSpeaking   = false;
    let pollInterval = null;

    /* ════════════════════════════════════════════════════════════
       KITT RENDERER
       ════════════════════════════════════════════════════════════ */
    const KITTRenderer = (() => {
        const bars    = document.querySelectorAll(".kitt-bar");
        const scanner = document.getElementById("kitt-scanner");
        const label   = document.getElementById("kitt-label");
        const N       = bars.length;
        let heights   = new Float32Array(N).fill(6);
        let targets   = new Float32Array(N).fill(6);
        let active    = false;
        let tickId    = null;

        function tick() {
            if (active) {
                for (let i = 0; i < N; i++) {
                    if (Math.random() < 0.5) {
                        const mid  = N / 2;
                        const dist = Math.abs(i - mid) / mid;
                        targets[i] = Math.random() * 70 * (1 - dist * 0.4) + 6;
                    }
                }
            } else {
                for (let i = 0; i < N; i++) targets[i] = 6;
            }
            for (let i = 0; i < N; i++) {
                heights[i] += (targets[i] - heights[i]) * 0.35;
                bars[i].style.height = heights[i] + "px";
                bars[i].classList.toggle("active", active && heights[i] > 10);
            }
            if (label) label.classList.toggle("active", active);
            tickId = setTimeout(tick, active ? 70 : 200);
        }
        return {
            start() { active = true;  if (scanner) scanner.classList.add("running");    if (!tickId) tick(); },
            stop()  { active = false; if (scanner) scanner.classList.remove("running"); setTimeout(() => { clearTimeout(tickId); tickId = null; }, 1000); if (!tickId) tick(); },
            init()  { tick(); }
        };
    })();

    /* ════════════════════════════════════════════════════════════
       EQ BARS RENDERER
       ════════════════════════════════════════════════════════════ */
    const EQBarsRenderer = (() => {
        const bars  = document.querySelectorAll(".eq-bar");
        const N     = bars.length;
        let heights = new Float32Array(N).fill(10);
        let targets = new Float32Array(N).fill(10);
        let active  = false;
        let tickId  = null;

        function tick() {
            if (active) {
                for (let i = 0; i < N; i++) targets[i] = Math.random() * 80 + 10;
            } else {
                for (let i = 0; i < N; i++) targets[i] = 10;
            }
            for (let i = 0; i < N; i++) {
                heights[i] += (targets[i] - heights[i]) * 0.4;
                bars[i].style.height = heights[i] + "px";
                bars[i].classList.toggle("active", active && heights[i] > 20);
            }
            tickId = setTimeout(tick, active ? 60 : 200);
        }
        return {
            start() { active = true;  if (!tickId) tick(); },
            stop()  { active = false; setTimeout(() => { clearTimeout(tickId); tickId = null; }, 1000); if (!tickId) tick(); },
            init()  { tick(); }
        };
    })();

    /* ════════════════════════════════════════════════════════════
       SINE WAVE RENDERER
       ════════════════════════════════════════════════════════════ */
    const SineRenderer = (() => {
        const canvas = document.getElementById("sine-canvas");
        const ctx    = canvas.getContext("2d");
        let active   = false;
        let phase    = 0;
        let amp      = 2;
        let ampT     = 2;
        let animId   = null;

        function draw() {
            ampT = active ? (Math.random() * 30 + 10) : 2;
            amp += (ampT - amp) * 0.15;
            phase += active ? 0.2 : 0.04;

            ctx.clearRect(0, 0, canvas.width, canvas.height);
            // Baseline
            ctx.strokeStyle = "rgba(0,255,0,0.15)";
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(0, canvas.height / 2);
            ctx.lineTo(canvas.width, canvas.height / 2);
            ctx.stroke();

            // Wave
            ctx.beginPath();
            const cy = canvas.height / 2;
            for (let x = 0; x < canvas.width; x++) {
                const noise = active ? (Math.random() - 0.5) * amp * 0.25 : 0;
                const y = cy + Math.sin(x * 0.05 + phase) * amp + noise;
                x === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
            }
            ctx.strokeStyle = active ? "#00ff00" : "rgba(0,255,0,0.3)";
            ctx.lineWidth   = active ? 3 : 2;
            ctx.shadowBlur  = active ? 10 : 0;
            ctx.shadowColor = "#00ff00";
            ctx.stroke();
            ctx.shadowBlur  = 0;

            if (active || amp > 2.1) animId = requestAnimationFrame(draw);
            else animId = null;
        }
        return {
            start() { active = true;  if (!animId) draw(); },
            stop()  { active = false; if (!animId) draw(); },
            init()  { draw(); }
        };
    })();

    /* ════════════════════════════════════════════════════════════
       PULSING ORB RENDERER
       ════════════════════════════════════════════════════════════ */
    const OrbRenderer = (() => {
        const core  = document.getElementById("orb-core");
        const rings = [
            document.getElementById("orb-ring1"),
            document.getElementById("orb-ring2"),
            document.getElementById("orb-ring3"),
        ];
        let active = false;
        let tickId = null;
        let idx    = 0;

        function tick() {
            if (active) {
                const s = 1 + Math.random() * 0.6;
                core.style.transform = `scale(${s})`;
                if (Math.random() < 0.4) {
                    const r = rings[idx];
                    r.classList.remove("ripple-anim");
                    void r.offsetWidth;
                    r.classList.add("ripple-anim");
                    idx = (idx + 1) % rings.length;
                }
            } else {
                core.style.transform = "scale(1)";
            }
            tickId = setTimeout(tick, active ? 100 : 200);
        }
        return {
            start() { active = true;  if (core) core.classList.add("active");    if (!tickId) tick(); },
            stop()  { active = false; if (core) core.classList.remove("active"); setTimeout(() => { clearTimeout(tickId); tickId = null; }, 1000); if (!tickId) tick(); },
            init()  { tick(); }
        };
    })();

    /* ════════════════════════════════════════════════════════════
       MOUTH RENDERER  — Bezier curves, pixelated 3x scale-up
       ════════════════════════════════════════════════════════════ */
    const MouthRenderer = (() => {
        const canvas  = document.getElementById("mouth-canvas");
        const ctx     = canvas.getContext("2d");

        /* Low-res offscreen canvas: drawn at 1/3 size then scaled 3x
           for chunky "pixel art from bezier curves" 80s look         */
        const SCALE   = 3;
        const OFF_W   = Math.round(canvas.width  / SCALE); // ≈78
        const OFF_H   = Math.round(canvas.height / SCALE); // ≈36
        const off     = document.createElement("canvas");
        off.width     = OFF_W;
        off.height    = OFF_H;
        const octx    = off.getContext("2d");
        octx.imageSmoothingEnabled = false;

        /* ── Palettes ─────────────────────────────────────────── */
        const PAL = {
            mouth_male: {
                bg:      "#050505",
                inside:  "#1a0000",
                lipOut:  "#7a3030",
                lip:     "#b55050",
                shine:   "#e09090",
                seam:    "#400010",
                teeth:   "#e8e6e0",
                tongue:  "#bb3333",
            },
            mouth_female: {
                bg:      "#050505",
                inside:  "#2a0008",
                lipOut:  "#880020",
                lip:     "#dd1144",
                shine:   "#ff80a0",
                seam:    "#550015",
                teeth:   "#f5f5ee",
                tongue:  "#e04060",
            },
            mouth_robot: {
                bg:      "#000511",
                inside:  "#000a18",
                lipOut:  "#004466",
                lip:     "#0088bb",
                shine:   "#00eeff",
                seam:    "#002233",
                teeth:   "#00ffff",
                tongue:  "#0044aa",
            },
            mouth_anime: {
                bg:      "#110a11",
                inside:  "#330011",
                lipOut:  "#882244",
                lip:     "#ff6688",
                shine:   "#ffbbcc",
                seam:    "#660022",
                teeth:   "#ffffff",
                tongue:  "#ff4477",
            },
        };

        /* ── Animation sequences (0=closed … 1=wide open) ─────── */
        const SPEAK_SEQ = [0.3, 0.7, 0.9, 0.6, 0.3, 0.8, 0.4, 0.1, 0.5, 0.8, 0.3, 0.0];
        const IDLE_SEQ  = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.05, 0.0, 0.0, 0.0];

        let style      = "mouth_male";
        let openAmt    = 0.0;
        let openTarget = 0.0;
        let seqPos     = 0;
        let active     = false;
        let tickId     = null;

        /* ── Drawing helpers ──────────────────────────────────── */

        /** Draw organic human/anime mouth using bezier curves */
        function drawOrganic(open, pal, female) {
            const W = OFF_W, H = OFF_H;
            const cx = W / 2;
            const cy = H / 2 + 1; // slightly below center

            /* Mouth is 92% of canvas width — fills the frame */
            const mW   = W * 0.92;
            const ml   = cx - mW / 2;      // left corner  ≈ 3
            const mr   = cx + mW / 2;      // right corner ≈ 75
            const maxH = H * 0.55;         // max opening height
            const oH   = maxH * open;      // current opening height
            const lipT = female ? 5 : 4;   // lip thickness (low-res px)

            const uTop = cy - oH / 2 - lipT; // top of upper lip
            const lBot = cy + oH / 2 + lipT + (female ? 2 : 1); // bottom of lower lip

            /* — Interior (inner mouth) — */
            if (open > 0.04) {
                octx.fillStyle = pal.inside;
                octx.beginPath();
                octx.ellipse(cx, cy + oH * 0.15, mW / 2 - 2, oH * 0.5 + 1, 0, 0, Math.PI * 2);
                octx.fill();

                /* Teeth strip (upper) */
                if (open > 0.18) {
                    octx.fillStyle = pal.teeth;
                    const tH = Math.min(oH * 0.28, 5);
                    octx.beginPath();
                    octx.rect(ml + 5, cy - oH * 0.4, mW - 10, tH);
                    octx.fill();
                }

                /* Tongue */
                if (open > 0.5) {
                    octx.fillStyle = pal.tongue;
                    octx.beginPath();
                    octx.ellipse(cx, cy + oH * 0.28, mW * 0.26, oH * 0.18, 0, 0, Math.PI * 2);
                    octx.fill();
                }
            }

            /* ── UPPER LIP ─────────────────────────────────────── */
            octx.fillStyle = pal.lip;
            octx.beginPath();
            octx.moveTo(ml, cy);

            if (female) {
                /* Cupid's bow: two peaks with central dip */
                const bowDip = 4; // how deep the V-dip is
                // left corner → left peak
                octx.bezierCurveTo(ml + mW * 0.18, uTop + 3, ml + mW * 0.36, uTop, ml + mW * 0.42, uTop + bowDip);
                // left peak → center dip
                octx.bezierCurveTo(ml + mW * 0.46, uTop + bowDip + 3, cx - 2, uTop + bowDip + 5, cx, uTop + bowDip + 4);
                // center dip → right peak
                octx.bezierCurveTo(cx + 2, uTop + bowDip + 5, mr - mW * 0.46, uTop + bowDip + 3, mr - mW * 0.42, uTop + bowDip);
                // right peak → right corner
                octx.bezierCurveTo(mr - mW * 0.36, uTop, mr - mW * 0.18, uTop + 3, mr, cy);
            } else {
                /* Male: flatter, subtle arch — no strong cupid's bow */
                octx.bezierCurveTo(ml + mW * 0.2, uTop + 3, ml + mW * 0.42, uTop + 1, cx - mW * 0.04, uTop + 3);
                octx.bezierCurveTo(cx + mW * 0.04, uTop + 3, mr - mW * 0.42, uTop + 1, mr - mW * 0.2, uTop + 3);
                octx.bezierCurveTo(mr - mW * 0.08, uTop + 4, mr, cy - oH * 0.1, mr, cy);
            }

            /* Bottom edge of upper lip (toward seam / opening) */
            octx.bezierCurveTo(mr - mW * 0.1, cy - oH * 0.22, ml + mW * 0.1, cy - oH * 0.22, ml, cy);
            octx.closePath();
            octx.fill();

            /* Upper lip outline */
            octx.strokeStyle = pal.lipOut;
            octx.lineWidth   = female ? 0.8 : 0.7;
            octx.stroke();

            /* Upper lip shine (horizontal highlight near top of lip) */
            octx.fillStyle   = pal.shine;
            octx.globalAlpha = 0.65;
            octx.beginPath();
            octx.ellipse(cx, uTop + lipT * 0.45, mW * 0.28, female ? 1.3 : 1.0, 0, 0, Math.PI);
            octx.fill();
            octx.globalAlpha = 1;

            /* ── LOWER LIP ─────────────────────────────────────── */
            octx.fillStyle = pal.lip;
            octx.beginPath();
            octx.moveTo(ml, cy);
            /* Lower lip is fuller/rounder than upper */
            octx.bezierCurveTo(ml + mW * 0.12, cy + oH * 0.38, ml + mW * 0.28, lBot, cx, lBot);
            octx.bezierCurveTo(mr - mW * 0.28, lBot, mr - mW * 0.12, cy + oH * 0.38, mr, cy);
            /* close back along top of lower lip */
            octx.bezierCurveTo(mr - mW * 0.1, cy + oH * 0.18, ml + mW * 0.1, cy + oH * 0.18, ml, cy);
            octx.closePath();
            octx.fill();

            /* Lower lip outline */
            octx.strokeStyle = pal.lipOut;
            octx.lineWidth   = female ? 0.8 : 0.7;
            octx.stroke();

            /* Lower lip shine (highlight near bottom centre of lower lip) */
            octx.fillStyle   = pal.shine;
            octx.globalAlpha = 0.55;
            octx.beginPath();
            octx.ellipse(cx, lBot - lipT * 0.7, mW * 0.22, female ? 1.5 : 1.1, 0, Math.PI, 0);
            octx.fill();
            octx.globalAlpha = 1;

            /* ── SEAM (closed-mouth dividing line) ─────────────── */
            if (open < 0.06) {
                octx.strokeStyle = pal.seam;
                octx.lineWidth   = 0.8;
                octx.beginPath();
                octx.moveTo(ml + 4, cy + 0.5);
                octx.bezierCurveTo(cx - mW * 0.3, cy + 2.5, cx + mW * 0.3, cy + 2.5, mr - 4, cy + 0.5);
                octx.stroke();
            }
        }

        /** Draw robot mouth: angular LED-segment aesthetic */
        function drawRobot(open, pal) {
            const W = OFF_W, H = OFF_H;
            const cx = W / 2, cy = H / 2 + 1;
            const mW = W * 0.90;
            const ml = cx - mW / 2, mr = cx + mW / 2;
            const maxH = H * 0.5;
            const oH  = maxH * open;
            const barH = 3 + oH * 0.3;

            /* Outer frame */
            octx.strokeStyle = pal.lipOut;
            octx.lineWidth   = 1.5;
            octx.strokeRect(ml, cy - oH / 2 - barH, mW, oH + barH * 2);

            /* Top bar (always shown) */
            octx.fillStyle = pal.lip;
            octx.fillRect(ml + 1, cy - oH / 2 - barH + 1, mW - 2, barH - 1);
            octx.fillStyle = pal.shine;
            octx.fillRect(ml + 1, cy - oH / 2 - barH + 1, mW - 2, 1);

            /* Bottom bar */
            octx.fillStyle = pal.lip;
            octx.fillRect(ml + 1, cy + oH / 2, mW - 2, barH - 1);
            octx.fillStyle = pal.shine;
            octx.fillRect(ml + 1, cy + oH / 2, mW - 2, 1);

            /* Inner columns (only when opening) */
            if (open > 0.05) {
                const cols   = 10;
                const colW   = (mW - 4) / cols;
                const innerH = oH - 1;
                for (let i = 0; i < cols; i++) {
                    const bx = ml + 2 + i * colW;
                    octx.fillStyle = i % 2 === 0 ? pal.inside : "rgba(0,136,187,0.12)";
                    octx.fillRect(bx, cy - oH / 2, colW - 1, innerH);
                }
                /* Teeth-like row */
                if (open > 0.25) {
                    octx.fillStyle = pal.teeth;
                    octx.fillRect(ml + 2, cy - oH / 2, mW - 4, 1.5);
                }
            }

            /* Glow outline */
            octx.shadowBlur  = 6;
            octx.shadowColor = pal.shine;
            octx.strokeStyle = pal.shine;
            octx.lineWidth   = 0.7;
            octx.strokeRect(ml, cy - oH / 2 - barH, mW, oH + barH * 2);
            octx.shadowBlur  = 0;
        }

        /* ── Main draw dispatcher ─────────────────────────────── */
        function draw(open) {
            const pal = PAL[style] || PAL.mouth_male;

            /* Clear offscreen */
            octx.fillStyle = pal.bg;
            octx.fillRect(0, 0, OFF_W, OFF_H);

            if (style === "mouth_robot") {
                drawRobot(open, pal);
            } else if (style === "mouth_anime") {
                /* Anime = organic mouth but smaller + cuter */
                drawOrganic(open, {
                    ...pal,
                    /* scale down the mouth width slightly for chibi look */
                    _anime: true
                }, false);
            } else {
                drawOrganic(open, pal, style === "mouth_female");
            }

            /* Scale-up to main canvas (pixelated) */
            ctx.imageSmoothingEnabled = false;
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(off, 0, 0, OFF_W, OFF_H, 0, 0, canvas.width, canvas.height);
        }

        /* ── Tick loop ────────────────────────────────────────── */
        function tick() {
            const seq = active ? SPEAK_SEQ : IDLE_SEQ;
            openTarget = seq[seqPos % seq.length];
            seqPos++;

            /* Smooth interpolation toward target */
            openAmt += (openTarget - openAmt) * (active ? 0.3 : 0.2);

            draw(openAmt);
            const delay = active ? ((60 + Math.random() * 65) | 0) : 320 + (Math.random() < 0.08 ? 500 : 0);
            tickId = setTimeout(tick, delay);
        }

        return {
            setStyle(s) { style = s; openAmt = 0; },
            start()  { active = true;  seqPos = 0; if (!tickId) tick(); },
            stop()   { active = false; seqPos = 0; if (!tickId) tick(); },
            init()   { tick(); }
        };
    })();

    /* ════════════════════════════════════════════════════════════
       MODE SWITCHING
       ════════════════════════════════════════════════════════════ */
    const ALL_STAGES = { kitt: stageKitt, audio_bars: stageEq, sine_wave: stageSine, pulsing_orb: stageOrb };
    function isMouthMode(m) { return m.startsWith("mouth_"); }

    function applyMode(mode) {
        [stageKitt, stageEq, stageSine, stageOrb, stageMouth].forEach(s => { if (s) s.style.display = "none"; });
        if (isMouthMode(mode)) {
            if (stageMouth) stageMouth.style.display = "";
            MouthRenderer.setStyle(mode);
        } else {
            const s = ALL_STAGES[mode];
            if (s) s.style.display = "";
        }
    }

    function onModeChange() {
        currentMode = modeSelect.value;
        localStorage.setItem("hecos-vv-mode", currentMode);
        applyMode(currentMode);
    }

    /* ════════════════════════════════════════════════════════════
       STATUS
       ════════════════════════════════════════════════════════════ */
    function setStatus(speaking) {
        statusDiv.classList.toggle("active", speaking);
        statusLabel.textContent = speaking ? "SPEAKING" : "IDLE";
    }

    /* ════════════════════════════════════════════════════════════
       POLLING
       ════════════════════════════════════════════════════════════ */
    const ALL_RENDERERS = [KITTRenderer, EQBarsRenderer, SineRenderer, OrbRenderer, MouthRenderer];
    let   consecutiveFails = 0;

    async function poll() {
        try {
            const data = await (await fetch("/api/widgets/voice_visualizer/status")).json();
            const speaking = !!data.speaking;
            consecutiveFails = 0;
            if (speaking !== isSpeaking) {
                isSpeaking = speaking;
                setStatus(speaking);
                if (speaking) ALL_RENDERERS.forEach(r => r.start());
                else          ALL_RENDERERS.forEach(r => r.stop());
            }
        } catch {
            consecutiveFails++;
            if (consecutiveFails > 5 && pollInterval) {
                clearInterval(pollInterval);
                pollInterval = setInterval(poll, 2000);
            }
        }
    }

    /* ════════════════════════════════════════════════════════════
       INIT
       ════════════════════════════════════════════════════════════ */
    function init() {
        modeSelect.value = currentMode;
        applyMode(currentMode);
        ALL_RENDERERS.forEach(r => r.init());
        modeSelect.addEventListener("change", onModeChange);
        poll();
        pollInterval = setInterval(poll, 120);
    }

    document.readyState === "loading"
        ? document.addEventListener("DOMContentLoaded", init)
        : init();

})();
