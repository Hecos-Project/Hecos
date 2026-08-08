# hecos/setup/web_ui/styles.py
# StyleMixin: CSS variables and main stylesheet returned as strings.
# Kept as a Mixin so that render methods can call self.get_css_vars() / self.get_main_styles()
# without any changes.


class StyleMixin:

    def get_css_vars(self) -> str:
        return """
        :root {
            --bg: #0c0e16; --bg2: #111420; --bg3: #181c2e;
            --accent: #5b7dff;
            --accent-dim: rgba(91,125,255,0.15);
            --accent-rgb: 91,125,255;
            --text: #d1d5db; --muted: #6b7280; --border: #1e2235;
            --red-muted: #ef4444;
        }
        """

    def get_main_styles(self) -> str:
        return """
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background: var(--bg); color: var(--text);
            font-family: 'Inter', system-ui, sans-serif;
            font-size: 14px; line-height: 1.6;
            padding: 48px 20px; display: flex; justify-content: center;
        }
        a { color: inherit; text-decoration: none; }

        /* Layout */
        .container { max-width: 620px; width: 100%; }
        .header { text-align: center; margin-bottom: 40px; }
        .logo-img { height: 46px; margin-bottom: 12px; opacity: 0.85; }
        .title-text {
            font-size: 0.68rem; font-weight: 600; letter-spacing: 4px;
            color: var(--accent); text-transform: uppercase; margin: 0;
        }

        /* Card */
        .card {
            background: var(--bg2); border: 1px solid var(--border);
            border-radius: 14px; padding: 36px; margin-bottom: 16px;
        }

        /* Sections */
        .section { margin-bottom: 32px; }
        .section-label {
            font-size: 0.65rem; font-weight: 700; letter-spacing: 3px;
            color: var(--muted); text-transform: uppercase; margin-bottom: 10px;
        }
        .tip { font-size: 0.82rem; color: var(--muted); margin-bottom: 4px; }
        .tip-sub { font-size: 0.72rem; color: var(--accent); opacity: 0.55; font-style: italic; margin-top: 2px; }

        /* Language buttons */
        .btn-lang {
            padding: 8px 18px; border-radius: 7px; font-size: 0.8rem; font-weight: 500;
            border: 1px solid var(--border); background: var(--bg3); color: var(--muted);
            cursor: pointer; font-family: inherit; transition: border-color 0.15s, color 0.15s;
        }
        .btn-lang:hover { border-color: var(--accent); color: var(--text); }
        .btn-lang-active { border-color: var(--accent); color: var(--accent); background: var(--accent-dim); }

        /* Voice list */
        .voice-list {
            max-height: 180px; overflow-y: auto; background: var(--bg);
            border: 1px solid var(--border); border-radius: 8px;
            padding: 12px; margin-top: 12px;
            scrollbar-width: thin; scrollbar-color: var(--border) transparent;
        }
        .voice-lang-label {
            font-size: 0.6rem; font-weight: 700; letter-spacing: 2px;
            color: var(--accent); text-transform: uppercase; margin: 10px 0 6px 0; opacity: 0.7;
        }
        .voice-row {
            display: flex; align-items: center; gap: 10px; padding: 6px 8px;
            border-radius: 6px; cursor: pointer; font-size: 0.8rem; color: var(--text);
            transition: background 0.1s;
        }
        .voice-row:hover { background: var(--bg3); }
        .voice-check { accent-color: var(--accent); }
        .voice-name { flex: 1; }
        .voice-quality { font-size: 0.7rem; color: var(--muted); }

        /* Install block */
        .install-block {
            background: rgba(var(--accent-rgb), 0.04);
            border: 1px solid rgba(var(--accent-rgb), 0.15);
            border-radius: 12px; padding: 28px; margin: 32px 0;
        }
        .btn-primary {
            background: var(--accent); color: #fff; padding: 10px 22px;
            border-radius: 8px; font-weight: 600; border: none;
            cursor: pointer; font-size: 0.85rem; font-family: inherit;
            letter-spacing: 0.3px; transition: opacity 0.15s, transform 0.12s;
            display: inline-block;
        }
        .btn-primary:hover { opacity: 0.88; transform: translateY(-1px); }
        .btn-primary:disabled { opacity: 0.45; cursor: not-allowed; transform: none; }

        /* Next steps / how-to */
        .next-label {
            font-size: 0.65rem; font-weight: 700; letter-spacing: 2px;
            color: var(--accent); text-transform: uppercase; margin-bottom: 14px;
        }
        .step-item {
            display: flex; gap: 14px; padding: 12px 0;
            border-bottom: 1px solid var(--border);
        }
        .step-item:last-of-type { border-bottom: none; }
        .step-num {
            width: 22px; height: 22px; border-radius: 50%;
            border: 1px solid var(--accent); color: var(--accent);
            font-size: 0.7rem; font-weight: 700; flex-shrink: 0;
            display: flex; align-items: center; justify-content: center;
        }
        .step-title { font-size: 0.82rem; font-weight: 600; color: var(--text); margin-bottom: 3px; }
        .step-desc { font-size: 0.77rem; color: var(--muted); line-height: 1.5; }

        /* Diagnostics */
        .diag-item {
            display: flex; gap: 16px; align-items: flex-start;
            padding: 12px 0; border-bottom: 1px solid var(--border);
        }
        .diag-item:last-child { border-bottom: none; }
        .diag-icon { font-size: 1.1rem; font-weight: 700; flex-shrink: 0; width: 22px; text-align: center; margin-top: 2px; }
        .diag-title { font-size: 0.82rem; font-weight: 600; color: var(--text); margin-bottom: 3px; }
        .diag-sub { font-size: 0.78rem; color: var(--muted); }
        .diag-pkgs { display: flex; flex-wrap: wrap; gap: 6px 16px; margin-top: 8px; }
        .diag-pkg { font-size: 0.72rem; color: var(--muted); }

        /* Ghost buttons */
        .btn-ghost {
            padding: 7px 14px; border-radius: 7px; font-size: 0.75rem; font-weight: 500;
            border: 1px solid var(--border); background: transparent; color: var(--muted);
            cursor: pointer; font-family: inherit; transition: border-color 0.15s, color 0.15s, background 0.15s;
            display: inline-block;
        }
        .btn-ghost:hover { border-color: var(--text); color: var(--text); }
        .btn-danger-ghost { border-color: rgba(239,68,68,0.4); color: var(--red-muted); }
        .btn-danger-ghost:hover { border-color: var(--red-muted); background: rgba(239,68,68,0.1); }

        /* Modals */
        .modal-overlay {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.6); backdrop-filter: blur(4px);
            display: none; align-items: center; justify-content: center; z-index: 100;
            opacity: 0; transition: opacity 0.2s;
        }
        .modal-overlay.active { display: flex; opacity: 1; }
        .modal-box {
            background: var(--bg2); border: 1px solid var(--red-muted);
            border-radius: 12px; padding: 32px; width: 90%; max-width: 440px;
            box-shadow: 0 20px 50px rgba(0,0,0,0.5), 0 0 0 1px rgba(239,68,68,0.2) inset;
            transform: scale(0.95); transition: transform 0.2s;
            text-align: center;
        }
        .modal-overlay.active .modal-box { transform: scale(1); }
        .modal-icon { font-size: 2rem; margin-bottom: 16px; }
        .modal-title { font-size: 1.1rem; font-weight: 700; color: var(--red-muted); margin-bottom: 12px; }
        .modal-desc { font-size: 0.85rem; color: var(--text); line-height: 1.6; margin-bottom: 24px; }
        .modal-actions { display: flex; gap: 12px; justify-content: center; }
        .btn-solid-danger {
            background: var(--red-muted); color: #fff; padding: 9px 18px; border-radius: 7px;
            font-weight: 600; border: none; cursor: pointer; transition: opacity 0.15s;
        }
        .btn-solid-danger:hover { opacity: 0.9; }

        /* Console log box */
        .console {
            background: var(--bg); border: 1px solid var(--border); border-radius: 8px;
            padding: 16px; color: #7dd3b0; font-family: 'SF Mono', 'Fira Code', monospace;
            font-size: 0.75rem; max-height: 180px; overflow-y: auto;
            margin-bottom: 24px; line-height: 1.6;
            scrollbar-width: thin; scrollbar-color: var(--border) transparent;
        }
        .error-msg { color: var(--red-muted); font-size: 0.8rem; text-align: center; padding: 20px; }

        /* Done / completion banner */
        .done-banner {
            background: rgba(var(--accent-rgb), 0.06); border: 1px solid rgba(var(--accent-rgb), 0.2);
            border-radius: 12px; padding: 28px; text-align: center; margin-bottom: 24px;
        }
        .done-label { font-size: 1rem; font-weight: 700; color: var(--accent); margin-bottom: 6px; }
        .done-sub { font-size: 0.82rem; color: var(--muted); }

        /* Footer */
        .footer { display: flex; justify-content: center; gap: 10px; margin-top: 20px; }
        .close-note {
            margin-top: 20px; padding: 12px 16px;
            background: var(--bg); border-radius: 8px;
            font-size: 0.75rem; color: var(--muted);
            border: 1px solid var(--border);
        }
        """
