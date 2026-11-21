# hecos/setup/web_ui/styles.py
# Cyber OS-style installer stylesheet for the Hecos Unified Setup Wizard.
# 100% self-contained (zero external CDN requirements; works offline).


class StyleMixin:

    def get_css_vars(self) -> str:
        return """
        :root {
            --bg: #080a12;
            --bg-panel: #0e1220;
            --bg-card: #13182a;
            --bg-card-hover: #181f36;
            --bg-input: #0a0d18;
            --border: #222944;
            --border-bright: #32406b;
            --cyan: #00e5ff;
            --cyan-dim: rgba(0, 229, 255, 0.12);
            --accent: #5b7dff;
            --accent-dim: rgba(91, 125, 255, 0.16);
            --magenta: #d946ef;
            --green: #22c55e;
            --green-dim: rgba(34, 197, 94, 0.12);
            --yellow: #f59e0b;
            --yellow-dim: rgba(245, 158, 11, 0.12);
            --red: #ef4444;
            --red-dim: rgba(239, 68, 68, 0.12);
            --text: #e5e7eb;
            --muted: #8b95b0;
            --font-sans: 'Segoe UI', system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
            --font-mono: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
        }
        """

    def get_main_styles(self) -> str:
        return """
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        html, body {
            height: 100%; width: 100%;
            background: var(--bg);
            color: var(--text);
            font-family: var(--font-sans);
            font-size: 14px;
            line-height: 1.5;
            overflow: hidden;
            user-select: none;
        }

        /* Subtle cyber grid glow backdrop */
        body::before {
            content: "";
            position: fixed; inset: 0; pointer-events: none; z-index: 0;
            background:
                radial-gradient(circle at 12% 15%, rgba(0,229,255,0.08), transparent 40%),
                radial-gradient(circle at 88% 85%, rgba(217,70,239,0.07), transparent 42%);
        }

        .app-shell {
            position: relative; z-index: 1;
            display: flex; height: 100vh; width: 100vw;
        }

        /* ── Left Sidebar Stepper ── */
        .sidebar {
            width: 248px; flex-shrink: 0;
            background: var(--bg-panel);
            border-right: 1px solid var(--border);
            display: flex; flex-direction: column;
            padding: 24px 18px 18px;
        }
        .brand {
            display: flex; align-items: center; gap: 12px;
            padding-bottom: 20px; margin-bottom: 20px;
            border-bottom: 1px solid var(--border);
        }
        .brand img {
            width: 36px; height: 36px; border-radius: 8px;
            filter: drop-shadow(0 0 8px rgba(0,229,255,0.35));
        }
        .brand-title {
            font-size: 0.95rem; font-weight: 700; letter-spacing: 2px;
            color: #fff;
        }
        .brand-sub {
            font-size: 0.68rem; letter-spacing: 1.5px; color: var(--cyan);
            text-transform: uppercase;
        }

        .stepper { list-style: none; display: flex; flex-direction: column; gap: 6px; flex: 1; }
        .step-nav {
            display: flex; align-items: center; gap: 11px;
            padding: 10px 10px; border-radius: 9px;
            color: var(--muted); font-size: 0.84rem; font-weight: 500;
            border: 1px solid transparent; transition: all 0.2s;
        }
        .step-nav .dot {
            width: 24px; height: 24px; border-radius: 50%; flex-shrink: 0;
            display: flex; align-items: center; justify-content: center;
            font-size: 0.74rem; font-weight: 700;
            background: var(--bg-card); border: 1px solid var(--border);
            color: var(--muted);
        }
        .step-nav.active {
            background: var(--cyan-dim); border-color: rgba(0,229,255,0.35); color: #fff;
        }
        .step-nav.active .dot {
            background: var(--cyan); color: #051018; border-color: var(--cyan);
            box-shadow: 0 0 10px rgba(0,229,255,0.5);
        }
        .step-nav.done { color: var(--text); }
        .step-nav.done .dot {
            background: var(--green-dim); border-color: var(--green); color: var(--green);
        }

        .sidebar-tools {
            border-top: 1px solid var(--border);
            padding-top: 14px; display: flex; flex-direction: column; gap: 6px;
        }
        .tool-btn {
            background: transparent; border: 1px solid var(--border);
            color: var(--muted); border-radius: 8px;
            padding: 8px 10px; font-size: 0.78rem; font-family: inherit;
            cursor: pointer; text-align: left; display: flex; align-items: center; gap: 8px;
            transition: all 0.15s;
        }
        .tool-btn:hover { border-color: var(--border-bright); color: var(--text); background: var(--bg-card); }
        .tool-btn.danger:hover { border-color: rgba(239,68,68,0.5); color: var(--red); background: var(--red-dim); }

        /* ── Main Stage ── */
        .main-col {
            flex: 1; display: flex; flex-direction: column; min-width: 0;
        }
        .stage {
            flex: 1; overflow-y: auto; padding: 30px 36px 24px;
        }
        .stage::-webkit-scrollbar { width: 7px; }
        .stage::-webkit-scrollbar-thumb { background: var(--border-bright); border-radius: 4px; }

        .step-pane { display: none; animation: fadeIn 0.2s ease-out; }
        .step-pane.active { display: block; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }

        .eyebrow {
            font-size: 0.7rem; font-weight: 700; letter-spacing: 2.5px;
            color: var(--cyan); text-transform: uppercase; margin-bottom: 6px;
        }
        h1 { font-size: 1.55rem; font-weight: 700; color: #fff; margin-bottom: 8px; }
        .subtitle { font-size: 0.88rem; color: var(--muted); margin-bottom: 24px; max-width: 640px; }

        /* Cards & Status Boxes */
        .panel {
            background: var(--bg-card); border: 1px solid var(--border);
            border-radius: 12px; padding: 18px 20px; margin-bottom: 16px;
        }
        .panel-title {
            font-size: 0.74rem; font-weight: 700; letter-spacing: 1.6px;
            text-transform: uppercase; color: var(--muted); margin-bottom: 12px;
        }

        .status-grid {
            display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px;
        }
        .status-box {
            background: var(--bg-input); border: 1px solid var(--border);
            border-radius: 10px; padding: 12px 14px;
        }
        .status-box .label { font-size: 0.72rem; color: var(--muted); text-transform: uppercase; letter-spacing: 1px; }
        .status-box .val { font-size: 0.9rem; font-weight: 600; color: #fff; margin-top: 3px; word-break: break-all; }
        .badge {
            display: inline-block; padding: 2px 8px; border-radius: 999px;
            font-size: 0.7rem; font-weight: 700; letter-spacing: 0.5px;
        }
        .badge-ok { background: var(--green-dim); color: var(--green); border: 1px solid rgba(34,197,94,0.35); }
        .badge-warn { background: var(--yellow-dim); color: var(--yellow); border: 1px solid rgba(245,158,11,0.35); }
        .badge-fail { background: var(--red-dim); color: var(--red); border: 1px solid rgba(239,68,68,0.35); }
        .badge-cyan { background: var(--cyan-dim); color: var(--cyan); border: 1px solid rgba(0,229,255,0.35); }

        /* Language Pills */
        .lang-row { display: flex; flex-wrap: wrap; gap: 10px; }
        .lang-pill {
            padding: 10px 18px; border-radius: 9px; cursor: pointer;
            background: var(--bg-input); border: 1px solid var(--border);
            color: var(--text); font-weight: 600; font-size: 0.86rem;
            font-family: inherit; transition: all 0.15s;
        }
        .lang-pill:hover { border-color: var(--border-bright); }
        .lang-pill.selected {
            background: var(--cyan-dim); border-color: var(--cyan); color: #fff;
            box-shadow: 0 0 12px rgba(0,229,255,0.2);
        }

        /* Mode Cards */
        .mode-cards { display: flex; flex-direction: column; gap: 12px; }
        .mode-card {
            display: flex; align-items: flex-start; gap: 16px;
            background: var(--bg-card); border: 1.5px solid var(--border);
            border-radius: 12px; padding: 16px 18px; cursor: pointer;
            transition: all 0.18s;
        }
        .mode-card:hover { background: var(--bg-card-hover); border-color: var(--border-bright); }
        .mode-card.selected {
            background: linear-gradient(135deg, rgba(0,229,255,0.09), rgba(91,125,255,0.08));
            border-color: var(--cyan);
            box-shadow: 0 0 18px rgba(0,229,255,0.12);
        }
        .mode-icon {
            width: 40px; height: 40px; border-radius: 10px; flex-shrink: 0;
            display: flex; align-items: center; justify-content: center;
            font-size: 1.25rem; background: var(--bg-input); border: 1px solid var(--border);
        }
        .mode-card.selected .mode-icon { border-color: var(--cyan); background: var(--cyan-dim); }
        .mode-body { flex: 1; }
        .mode-title { font-size: 0.96rem; font-weight: 700; color: #fff; display: flex; align-items: center; gap: 8px; }
        .mode-desc { font-size: 0.82rem; color: var(--muted); margin-top: 4px; }

        /* Inputs & Path Picker */
        .field { margin-bottom: 14px; }
        .field label { display: block; font-size: 0.8rem; font-weight: 600; color: var(--text); margin-bottom: 6px; }
        .input-row { display: flex; gap: 8px; }
        .text-input {
            flex: 1; background: var(--bg-input); border: 1px solid var(--border);
            color: #fff; border-radius: 8px; padding: 10px 12px;
            font-family: var(--font-mono); font-size: 0.84rem; user-select: text;
        }
        .text-input:focus { outline: none; border-color: var(--cyan); }
        .path-feedback { font-size: 0.76rem; margin-top: 5px; min-height: 18px; }
        .path-feedback.ok { color: var(--green); }
        .path-feedback.warn { color: var(--yellow); }
        .path-feedback.err { color: var(--red); }

        /* Checkboxes */
        .opt-list { display: flex; flex-direction: column; gap: 10px; }
        .opt-row {
            display: flex; align-items: flex-start; gap: 11px; cursor: pointer;
            padding: 10px 12px; border-radius: 9px;
            background: var(--bg-input); border: 1px solid var(--border);
        }
        .opt-row input[type="checkbox"] {
            margin-top: 3px; width: 16px; height: 16px; accent-color: var(--cyan); cursor: pointer;
        }
        .opt-title { font-size: 0.86rem; font-weight: 600; color: #fff; }
        .opt-desc { font-size: 0.76rem; color: var(--muted); }

        /* Live Install Progress */
        .progress-wrap {
            background: var(--bg-input); border: 1px solid var(--border);
            border-radius: 999px; height: 12px; overflow: hidden; margin: 12px 0 8px;
        }
        .progress-bar {
            height: 100%; width: 0%;
            background: linear-gradient(90deg, var(--cyan), var(--accent), var(--magenta));
            transition: width 0.35s ease;
            box-shadow: 0 0 12px rgba(0,229,255,0.5);
        }
        .progress-meta {
            display: flex; justify-content: space-between; font-size: 0.8rem; color: var(--muted);
            margin-bottom: 16px;
        }

        .phase-list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin-bottom: 16px; }
        .phase-item {
            display: flex; align-items: center; gap: 10px;
            background: var(--bg-input); border: 1px solid var(--border);
            border-radius: 8px; padding: 9px 12px; font-size: 0.82rem;
        }
        .phase-item.active { border-color: var(--cyan); color: #fff; }
        .phase-item.ok { border-color: rgba(34,197,94,0.4); }
        .phase-item.warn { border-color: rgba(245,158,11,0.4); }
        .phase-item.fail { border-color: rgba(239,68,68,0.5); }

        .log-toggle {
            background: transparent; border: 1px solid var(--border); color: var(--cyan);
            padding: 6px 12px; border-radius: 7px; font-size: 0.76rem; cursor: pointer;
            font-family: inherit; margin-bottom: 8px;
        }
        .log-box {
            background: #05070d; border: 1px solid var(--border); border-radius: 10px;
            padding: 12px 14px; height: 220px; overflow-y: auto;
            font-family: var(--font-mono); font-size: 0.75rem; line-height: 1.55;
            user-select: text;
        }
        .log-line { white-space: pre-wrap; word-break: break-word; color: #b8c2d9; }
        .log-line.ok { color: var(--green); }
        .log-line.warn { color: var(--yellow); }
        .log-line.error { color: var(--red); }

        /* Doctor Table */
        .diag-table { width: 100%; border-collapse: collapse; font-size: 0.8rem; }
        .diag-table td { padding: 8px 10px; border-bottom: 1px solid var(--border); vertical-align: top; }
        .diag-table tr:last-child td { border-bottom: none; }
        .diag-name { font-weight: 600; color: #fff; width: 145px; }
        .diag-detail { color: var(--muted); font-family: var(--font-mono); font-size: 0.74rem; word-break: break-word; }

        /* Footer Bar */
        .footer-bar {
            display: flex; align-items: center; justify-content: space-between;
            padding: 14px 36px; border-top: 1px solid var(--border);
            background: var(--bg-panel);
        }
        .btn {
            padding: 10px 20px; border-radius: 9px; font-family: inherit;
            font-size: 0.85rem; font-weight: 600; cursor: pointer;
            border: 1px solid transparent; transition: all 0.15s;
        }
        .btn:disabled { opacity: 0.4; cursor: not-allowed; }
        .btn-primary {
            background: linear-gradient(135deg, var(--cyan), var(--accent));
            color: #04101a; font-weight: 700;
            box-shadow: 0 0 14px rgba(0,229,255,0.25);
        }
        .btn-primary:hover:not(:disabled) { filter: brightness(1.1); transform: translateY(-1px); }
        .btn-secondary {
            background: var(--bg-card); border-color: var(--border-bright); color: var(--text);
        }
        .btn-secondary:hover:not(:disabled) { background: var(--bg-card-hover); }
        .btn-danger {
            background: var(--red-dim); border-color: rgba(239,68,68,0.5); color: var(--red);
        }
        .btn-danger:hover:not(:disabled) { background: rgba(239,68,68,0.22); }

        /* Modal */
        .modal-overlay {
            display: none; position: fixed; inset: 0; z-index: 50;
            background: rgba(4, 6, 12, 0.78); backdrop-filter: blur(4px);
            align-items: center; justify-content: center; padding: 20px;
        }
        .modal-overlay.open { display: flex; }
        .modal-card {
            background: var(--bg-panel); border: 1px solid var(--border-bright);
            border-radius: 14px; width: 100%; max-width: 620px; max-height: 82vh;
            display: flex; flex-direction: column; overflow: hidden;
            box-shadow: 0 20px 60px rgba(0,0,0,0.65);
        }
        .modal-head {
            display: flex; align-items: center; justify-content: space-between;
            padding: 16px 20px; border-bottom: 1px solid var(--border);
        }
        .modal-head h2 { font-size: 1rem; color: #fff; }
        .modal-body { padding: 18px 20px; overflow-y: auto; flex: 1; }
        .modal-foot {
            padding: 12px 20px; border-top: 1px solid var(--border);
            display: flex; justify-content: flex-end; gap: 10px;
        }
        """
