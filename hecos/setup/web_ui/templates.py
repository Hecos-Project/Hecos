# hecos/setup/web_ui/templates.py
# Unified 5-Step Cyber Installer Wizard (HTML + Vanilla JS, zero CDN dependencies).

from __future__ import annotations

import json

from .. import i18n
from .state import SESSION_TOKEN
from .styles import StyleMixin


class TemplateMixin(StyleMixin):

    def render_unified_wizard(self, initial_status: dict) -> None:
        status_json = json.dumps(initial_status)
        token_json = json.dumps(SESSION_TOKEN)
        initial_lang = i18n.UI_LANG if i18n.UI_LANG in ("it", "en", "es", "fr", "de") else "en"
        initial_lang_json = json.dumps(initial_lang)

        html = f"""<!DOCTYPE html>
<html lang="{initial_lang}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Hecos — Official Setup Wizard</title>
  <style>
    {self.get_css_vars()}
    {self.get_main_styles()}
  </style>
</head>
<body>
  <div class="app-shell">
    <!-- Left Sidebar Stepper -->
    <aside class="sidebar">
      <div class="brand">
        <img src="/logo.png" alt="Hecos" onerror="this.style.display='none'">
        <div>
          <div class="brand-title">HECOS</div>
          <div class="brand-sub" data-i18n="brand_sub">UNIFIED SETUP</div>
        </div>
      </div>

      <ul class="stepper" id="stepper">
        <li class="step-nav active" data-step="1"><span class="dot">1</span><span data-i18n="nav_1">Welcome</span></li>
        <li class="step-nav" data-step="2"><span class="dot">2</span><span data-i18n="nav_2">Components</span></li>
        <li class="step-nav" data-step="3"><span class="dot">3</span><span data-i18n="nav_3">Location &amp; Options</span></li>
        <li class="step-nav" data-step="4"><span class="dot">4</span><span data-i18n="nav_4">Installing</span></li>
        <li class="step-nav" data-step="5"><span class="dot">5</span><span data-i18n="nav_5">Ready</span></li>
      </ul>

      <div class="sidebar-tools">
        <button class="tool-btn" onclick="openDoctorModal()">&#128269; <span data-i18n="tool_doctor">System Diagnostics</span></button>
        <button class="tool-btn danger" onclick="openUninstallModal()">&#128465; <span data-i18n="tool_uninstall">Uninstall / Wipe</span></button>
      </div>
    </aside>

    <!-- Main Stage -->
    <div class="main-col">
      <main class="stage">

        <!-- STEP 1: Welcome & Language -->
        <section class="step-pane active" id="pane-1">
          <div class="eyebrow" data-i18n="s1_eyebrow">STEP 1 OF 5</div>
          <h1 data-i18n="s1_title">Welcome to Hecos Setup</h1>
          <p class="subtitle" data-i18n="s1_sub">
            This wizard installs Hecos Core, Hecos Tray, isolated Python runtimes, and all required dependencies automatically.
          </p>

          <div class="panel">
            <div class="panel-title" data-i18n="s1_lang_label">Setup &amp; Interface Language</div>
            <div class="lang-row" id="lang-pills">
              <button class="lang-pill" data-lang="it" onclick="setLang('it')">Italiano</button>
              <button class="lang-pill" data-lang="en" onclick="setLang('en')">English</button>
              <button class="lang-pill" data-lang="es" onclick="setLang('es')">Espa&ntilde;ol</button>
              <button class="lang-pill" data-lang="fr" onclick="setLang('fr')">Fran&ccedil;ais</button>
              <button class="lang-pill" data-lang="de" onclick="setLang('de')">Deutsch</button>
            </div>
          </div>

          <div class="panel">
            <div class="panel-title" data-i18n="s1_detected">Detected on This Machine</div>
            <div class="status-grid" id="env-status-grid"></div>
          </div>
        </section>

        <!-- STEP 2: Installation Mode -->
        <section class="step-pane" id="pane-2">
          <div class="eyebrow" data-i18n="s2_eyebrow">STEP 2 OF 5</div>
          <h1 data-i18n="s2_title">Choose What to Install</h1>
          <p class="subtitle" data-i18n="s2_sub">
            Install the complete Hecos suite in one click, or pick only Core or Tray. Each component stays isolated and resilient.
          </p>

          <div class="mode-cards">
            <div class="mode-card selected" data-mode="full" onclick="selectMode('full')">
              <div class="mode-icon">&#9889;</div>
              <div class="mode-body">
                <div class="mode-title">
                  <span data-i18n="mode_full_title">Hecos Complete (Core + Tray)</span>
                  <span class="badge badge-cyan" data-i18n="badge_rec">RECOMMENDED</span>
                </div>
                <div class="mode-desc" data-i18n="mode_full_desc">
                  Full experience: downloads/verifies both Hecos Core and Hecos Tray, provisions isolated Python 3.11, installs dependencies, links Core &harr; Tray, and enables autostart.
                </div>
              </div>
            </div>

            <div class="mode-card" data-mode="core" onclick="selectMode('core')">
              <div class="mode-icon">&#129504;</div>
              <div class="mode-body">
                <div class="mode-title" data-i18n="mode_core_title">Hecos Core Only</div>
                <div class="mode-desc" data-i18n="mode_core_desc">
                  Installs only the AI engine, WebUI, and CLI tools without the system tray app. Ideal for servers or standalone usage via Global Launcher.
                </div>
              </div>
            </div>

            <div class="mode-card" data-mode="tray" onclick="selectMode('tray')">
              <div class="mode-icon">&#128421;</div>
              <div class="mode-body">
                <div class="mode-title" data-i18n="mode_tray_title">Hecos Tray Only</div>
                <div class="mode-desc" data-i18n="mode_tray_desc">
                  Installs or repairs only the Hecos System Tray &amp; Dashboard (with bundled tkinter Python) and links it to your existing Core.
                </div>
              </div>
            </div>
          </div>

          <div class="panel" id="redownload-panel" style="margin-top:16px; display:none;">
            <label class="opt-row" style="border:none; padding:2px 0; background:transparent;">
              <input type="checkbox" id="opt-redownload">
              <div>
                <div class="opt-title" data-i18n="opt_redl_title">Download latest release files from GitHub (update existing folder)</div>
                <div class="opt-desc" data-i18n="opt_redl_desc">Leave unchecked to keep your current local files and only verify/repair Python, dependencies, and links. User configs &amp; databases are always preserved.</div>
              </div>
            </label>
          </div>
        </section>

        <!-- STEP 3: Location & Options -->
        <section class="step-pane" id="pane-3">
          <div class="eyebrow" data-i18n="s3_eyebrow">STEP 3 OF 5</div>
          <h1 data-i18n="s3_title">Destination &amp; Options</h1>
          <p class="subtitle" data-i18n="s3_sub">
            Install Hecos on any drive or folder. Avoid spaces, accents, or special shell characters.
          </p>

          <div class="panel">
            <div class="panel-title" data-i18n="s3_folders">Installation Folders</div>

            <div class="field" id="field-core-path">
              <label for="input-core-path" data-i18n="lbl_core_path">Hecos Core Folder</label>
              <div class="input-row">
                <input type="text" id="input-core-path" class="text-input" oninput="schedulePathValidation()">
                <button type="button" class="btn btn-secondary" onclick="browseFolder('core')" data-i18n="btn_browse">Browse&hellip;</button>
              </div>
              <div class="path-feedback" id="fb-core-path"></div>
            </div>

            <div class="field" id="field-tray-path" style="margin-bottom:0;">
              <label for="input-tray-path" data-i18n="lbl_tray_path">Hecos Tray Folder</label>
              <div class="input-row">
                <input type="text" id="input-tray-path" class="text-input" oninput="schedulePathValidation()">
                <button type="button" class="btn btn-secondary" onclick="browseFolder('tray')" data-i18n="btn_browse">Browse&hellip;</button>
              </div>
              <div class="path-feedback" id="fb-tray-path"></div>
            </div>
          </div>

          <div class="panel">
            <div class="panel-title" data-i18n="s3_opts">Options</div>
            <div class="opt-list">
              <label class="opt-row" id="row-opt-autostart">
                <input type="checkbox" id="opt-autostart" checked>
                <div>
                  <div class="opt-title" data-i18n="opt_auto_title">Start Hecos Tray automatically at login</div>
                  <div class="opt-desc" data-i18n="opt_auto_desc">Creates a native Windows Startup / Linux XDG autostart entry.</div>
                </div>
              </label>

              <label class="opt-row" id="row-opt-piper">
                <input type="checkbox" id="opt-piper" checked>
                <div>
                  <div class="opt-title" data-i18n="opt_piper_title">Install local Piper TTS voice engine</div>
                  <div class="opt-desc" data-i18n="opt_piper_desc">Enables fast offline speech synthesis (additional voices can be downloaded anytime inside Hecos WebUI).</div>
                </div>
              </label>

              <label class="opt-row">
                <input type="checkbox" id="opt-shortcut" checked>
                <div>
                  <div class="opt-title" data-i18n="opt_sc_title">Create Desktop shortcut</div>
                  <div class="opt-desc" data-i18n="opt_sc_desc">Adds a Hecos launcher icon to your Desktop.</div>
                </div>
              </label>

              <label class="opt-row">
                <input type="checkbox" id="opt-force-deps">
                <div>
                  <div class="opt-title" data-i18n="opt_force_title">Force dependency verification / repair</div>
                  <div class="opt-desc" data-i18n="opt_force_desc">Leave unchecked for fast smart check (skips pip when all tested packages are already installed).</div>
                </div>
              </label>
            </div>
          </div>
        </section>

        <!-- STEP 4: Live Installation -->
        <section class="step-pane" id="pane-4">
          <div class="eyebrow" data-i18n="s4_eyebrow">STEP 4 OF 5</div>
          <h1 id="install-heading" data-i18n="s4_title">Installing Hecos&hellip;</h1>
          <p class="subtitle" id="install-sub" data-i18n="s4_sub">
            Please keep this window open until the installation finishes.
          </p>

          <div class="panel">
            <div class="progress-wrap"><div class="progress-bar" id="progress-bar"></div></div>
            <div class="progress-meta">
              <span id="progress-phase">Initializing&hellip;</span>
              <span id="progress-pct">0%</span>
            </div>

            <div class="phase-list">
              <div class="phase-item" id="ph-paths"><span class="badge badge-cyan">&#8226;</span> <span data-i18n="ph_paths">Path Validation</span></div>
              <div class="phase-item" id="ph-download"><span class="badge badge-cyan">&#8226;</span> <span data-i18n="ph_download">Core &amp; Tray Files</span></div>
              <div class="phase-item" id="ph-python"><span class="badge badge-cyan">&#8226;</span> <span data-i18n="ph_python">Python 3.11 Runtime</span></div>
              <div class="phase-item" id="ph-core"><span class="badge badge-cyan">&#8226;</span> <span data-i18n="ph_core">Core Dependencies &amp; TTS</span></div>
              <div class="phase-item" id="ph-tray"><span class="badge badge-cyan">&#8226;</span> <span data-i18n="ph_tray">Tray GUI Dependencies</span></div>
              <div class="phase-item" id="ph-finalize"><span class="badge badge-cyan">&#8226;</span> <span data-i18n="ph_finalize">Registry, Autostart &amp; Doctor</span></div>
            </div>

            <button type="button" class="log-toggle" id="log-toggle-btn" onclick="toggleLogBox()">&#9660; <span data-i18n="btn_hide_log">Hide technical log</span></button>
            <div class="log-box" id="log-box"></div>
          </div>
        </section>

        <!-- STEP 5: Ready / Summary -->
        <section class="step-pane" id="pane-5">
          <div class="eyebrow" data-i18n="s5_eyebrow">STEP 5 OF 5</div>
          <h1 id="done-title" data-i18n="s5_title">Hecos is Ready!</h1>
          <p class="subtitle" id="done-sub" data-i18n="s5_sub">
            Installation completed successfully. You can launch Hecos right now.
          </p>

          <div class="panel" id="done-summary-panel"></div>

          <div class="panel" id="done-doctor-panel" style="display:none;">
            <div class="panel-title" data-i18n="s5_doctor">System Verification (Doctor)</div>
            <table class="diag-table" id="done-doctor-table"></table>
          </div>
        </section>
      </main>

      <!-- Bottom Navigation Bar -->
      <footer class="footer-bar">
        <div>
          <button type="button" class="btn btn-secondary" id="btn-back" onclick="prevStep()" style="display:none;" data-i18n="btn_back">&larr; Back</button>
        </div>
        <div style="display:flex; gap:10px;">
          <button type="button" class="btn btn-secondary" id="btn-close" onclick="shutdownInstaller()" style="display:none;" data-i18n="btn_close">Close</button>
          <button type="button" class="btn btn-primary" id="btn-next" onclick="nextStep()" data-i18n="btn_next">Next &rarr;</button>
          <button type="button" class="btn btn-primary" id="btn-launch" onclick="launchHecosNow()" style="display:none;" data-i18n="btn_launch">&#9654; Launch Hecos Now</button>
        </div>
      </footer>
    </div>
  </div>

  <!-- Doctor Modal -->
  <div class="modal-overlay" id="doctor-modal">
    <div class="modal-card">
      <div class="modal-head">
        <h2>&#128269; <span data-i18n="tool_doctor">System Diagnostics</span></h2>
        <button class="btn btn-secondary" style="padding:5px 12px;" onclick="closeModal('doctor-modal')">&#10005;</button>
      </div>
      <div class="modal-body" id="doctor-modal-body">Loading&hellip;</div>
      <div class="modal-foot">
        <button class="btn btn-secondary" onclick="runDoctorIntoModal()" data-i18n="btn_recheck">Re-check</button>
        <button class="btn btn-primary" onclick="closeModal('doctor-modal')" data-i18n="btn_close">Close</button>
      </div>
    </div>
  </div>

  <!-- Uninstall Modal -->
  <div class="modal-overlay" id="uninstall-modal">
    <div class="modal-card">
      <div class="modal-head">
        <h2 style="color:var(--red);">&#128465; <span data-i18n="tool_uninstall">Uninstall / Wipe</span></h2>
        <button class="btn btn-secondary" style="padding:5px 12px;" onclick="closeModal('uninstall-modal')">&#10005;</button>
      </div>
      <div class="modal-body">
        <p style="color:var(--muted); margin-bottom:14px; font-size:0.84rem;" data-i18n="uni_desc">
          Remove Hecos Python packages and autostart shortcuts. Local folders can be deleted afterwards.
        </p>
        <div class="panel" style="margin-bottom:12px;">
          <div class="opt-title" data-i18n="uni_smart_title">Remove Hecos Packages Only (Safe)</div>
          <div class="opt-desc" style="margin:4px 0 12px;" data-i18n="uni_smart_desc">Uninstalls only packages declared in Hecos pyproject.toml and disables autostart.</div>
          <button class="btn btn-danger" onclick="runUninstall('smart')" data-i18n="uni_smart_btn">Remove Hecos Only</button>
        </div>
        <div class="panel" style="border-color:rgba(239,68,68,0.4);">
          <div class="opt-title" style="color:var(--red);" data-i18n="uni_wipe_title">Full Python Environment Wipe</div>
          <div class="opt-desc" style="margin:4px 0 12px;" data-i18n="uni_wipe_desc">Removes ALL pip packages from this Python interpreter. Use only if Python is dedicated to Hecos.</div>
          <button class="btn btn-danger" onclick="runUninstall('wipe')" data-i18n="uni_wipe_btn">Full Environment Wipe</button>
        </div>
        <div class="log-box" id="uninstall-log" style="display:none; height:140px; margin-top:12px;"></div>
      </div>
      <div class="modal-foot">
        <button class="btn btn-secondary" onclick="closeModal('uninstall-modal')" data-i18n="btn_close">Close</button>
      </div>
    </div>
  </div>

<script>
const CSRF_TOKEN = {token_json};
const ENV_STATUS = {status_json};
let CURRENT_LANG = {initial_lang_json};
let CURRENT_STEP = 1;
let SELECTED_MODE = 'full';
let PATHS_VALID = true;
let INSTALL_RESULT = null;
let pathTimer = null;

const I18N = {{
  en: {{
    brand_sub: "UNIFIED SETUP",
    nav_1: "Welcome", nav_2: "Components", nav_3: "Location & Options", nav_4: "Installing", nav_5: "Ready",
    tool_doctor: "System Diagnostics", tool_uninstall: "Uninstall / Wipe",
    s1_eyebrow: "STEP 1 OF 5", s1_title: "Welcome to Hecos Setup",
    s1_sub: "This official wizard installs Hecos Core, Hecos Tray, isolated Python 3.11 runtimes, and all tested dependencies automatically.",
    s1_lang_label: "Setup & Interface Language", s1_detected: "Detected on This Machine",
    s2_eyebrow: "STEP 2 OF 5", s2_title: "Choose What to Install",
    s2_sub: "Install the complete Hecos suite in one click, or pick only Core or Tray. Each component is isolated and resilient.",
    mode_full_title: "Hecos Complete (Core + Tray)", badge_rec: "RECOMMENDED",
    mode_full_desc: "Full experience: installs/verifies both Hecos Core and Hecos Tray, provisions isolated Python 3.11, installs tested dependencies, links Core <-> Tray, and enables autostart.",
    mode_core_title: "Hecos Core Only",
    mode_core_desc: "Installs only the AI engine, WebUI, and CLI tools without the system tray app. Ideal for servers or standalone usage.",
    mode_tray_title: "Hecos Tray Only",
    mode_tray_desc: "Installs or repairs only the Hecos System Tray & Dashboard (with bundled tkinter Python) and links it to your Core.",
    opt_redl_title: "Re-download latest release files from GitHub",
    opt_redl_desc: "Leave unchecked to keep existing local files and only verify/repair Python, dependencies, and links. User configs & DBs are always preserved.",
    s3_eyebrow: "STEP 3 OF 5", s3_title: "Destination & Options",
    s3_sub: "Install Hecos on any drive or folder. Avoid spaces, accents, or special shell characters.",
    s3_folders: "Installation Folders", lbl_core_path: "Hecos Core Folder", lbl_tray_path: "Hecos Tray Folder",
    btn_browse: "Browse...", s3_opts: "Options",
    opt_auto_title: "Start Hecos Tray automatically at login",
    opt_auto_desc: "Creates a native Windows Startup / Linux XDG autostart shortcut.",
    opt_piper_title: "Install local Piper TTS voice engine",
    opt_piper_desc: "Enables fast offline speech synthesis (you can download voices anytime inside Hecos WebUI).",
    opt_sc_title: "Create Desktop shortcut",
    opt_sc_desc: "Adds a Hecos launcher icon directly to your Desktop.",
    opt_force_title: "Force full dependency verification / repair",
    opt_force_desc: "Leave unchecked for instant smart check (skips pip when all tested packages are already installed).",
    s4_eyebrow: "STEP 4 OF 5", s4_title: "Installing Hecos...",
    s4_sub: "Please keep this window open while Hecos sets up your environment.",
    ph_paths: "Path Validation", ph_download: "Core & Tray Files", ph_python: "Python 3.11 Runtime",
    ph_core: "Core Dependencies & TTS", ph_tray: "Tray GUI Dependencies", ph_finalize: "Registry, Autostart & Doctor",
    btn_hide_log: "Hide technical log", btn_show_log: "Show technical log",
    s5_eyebrow: "STEP 5 OF 5", s5_title: "Hecos is Ready!",
    s5_sub: "Setup completed cleanly. You can launch Hecos right now.",
    s5_title_warn: "Completed with Warnings",
    s5_sub_warn: "Core installation completed, with one or more optional items needing attention.",
    s5_title_fail: "Setup Encountered Errors",
    s5_sub_fail: "Review the details below or open System Diagnostics.",
    s5_doctor: "System Verification (Doctor)",
    btn_back: "← Back", btn_next: "Next →", btn_install: "▶ Start Installation",
    btn_launch: "▶ Launch Hecos Now", btn_close: "Close", btn_recheck: "Re-check",
    uni_desc: "Remove Hecos Python packages and autostart shortcuts. Local folders can be deleted manually afterwards.",
    uni_smart_title: "Remove Hecos Packages Only (Safe)",
    uni_smart_desc: "Uninstalls only packages declared in Hecos pyproject.toml and disables autostart.",
    uni_smart_btn: "Remove Hecos Only",
    uni_wipe_title: "Full Python Environment Wipe",
    uni_wipe_desc: "Removes ALL pip packages from this Python interpreter. Use only if Python is dedicated to Hecos.",
    uni_wipe_btn: "Full Environment Wipe",
    st_installed: "Installed", st_not_installed: "Not installed yet", st_free_disk: "Free Disk Space",
  }},
  it: {{
    brand_sub: "SETUP UNIFICATO",
    nav_1: "Benvenuto", nav_2: "Componenti", nav_3: "Percorso e Opzioni", nav_4: "Installazione", nav_5: "Pronto",
    tool_doctor: "Diagnostica (Doctor)", tool_uninstall: "Disinstalla",
    s1_eyebrow: "STEP 1 DI 5", s1_title: "Benvenuto nel Setup di Hecos",
    s1_sub: "Questo installer ufficiale configura automaticamente Hecos Core, Hecos Tray, gli ambienti Python 3.11 isolati e tutte le dipendenze testate.",
    s1_lang_label: "Lingua del Setup e dell'Interfaccia", s1_detected: "Rilevato su questo PC",
    s2_eyebrow: "STEP 2 DI 5", s2_title: "Scegli cosa installare",
    s2_sub: "Installa l'intera suite Hecos con un clic, oppure scegli solo Core o solo Tray. Ogni componente resta isolato e resiliente.",
    mode_full_title: "Hecos Completo (Core + Tray)", badge_rec: "CONSIGLIATO",
    mode_full_desc: "Esperienza completa: scarica/verifica sia Hecos Core che Hecos Tray, configura Python 3.11 isolato, installa le dipendenze bloccate, collega Core <-> Tray e attiva l'avvio automatico.",
    mode_core_title: "Solo Hecos Core",
    mode_core_desc: "Installa solo motore AI, WebUI e strumenti CLI senza icona Tray. Ideale per server o utilizzo standalone.",
    mode_tray_title: "Solo Hecos Tray",
    mode_tray_desc: "Installa o ripara solo la System Tray e Dashboard (con Python + tkinter integrato) collegandola al tuo Core.",
    opt_redl_title: "Riscarica l'ultima release da GitHub (aggiorna file locali)",
    opt_redl_desc: "Lascia deselezionato per mantenere i file attuali e verificare/riparare solo Python, dipendenze e collegamenti. Configurazioni e database vengono sempre preservati.",
    s3_eyebrow: "STEP 3 DI 5", s3_title: "Cartella di Installazione e Opzioni",
    s3_sub: "Puoi installare Hecos su qualsiasi disco o cartella. Evita spazi, accenti o caratteri speciali.",
    s3_folders: "Cartelle di Destinazione", lbl_core_path: "Cartella Hecos Core", lbl_tray_path: "Cartella Hecos Tray",
    btn_browse: "Sfoglia...", s3_opts: "Opzioni",
    opt_auto_title: "Avvia Hecos Tray automaticamente all'accensione",
    opt_auto_desc: "Crea il collegamento nativo nella cartella Esecuzione Automatica / XDG Autostart.",
    opt_piper_title: "Installa motore vocale locale Piper TTS",
    opt_piper_desc: "Abilita sintesi vocale offline veloce (potrai scaricare altre voci in qualsiasi momento dalla WebUI).",
    opt_sc_title: "Crea collegamento sul Desktop",
    opt_sc_desc: "Aggiunge un'icona di avvio rapido di Hecos sul Desktop.",
    opt_force_title: "Forza verifica / riparazione completa dipendenze",
    opt_force_desc: "Lascia deselezionato per il controllo rapido (salta pip se i pacchetti testati sono già installati).",
    s4_eyebrow: "STEP 4 DI 5", s4_title: "Installazione di Hecos in corso...",
    s4_sub: "Tieni aperta questa finestra fino al completamento della configurazione.",
    ph_paths: "Validazione Percorsi", ph_download: "File Core e Tray", ph_python: "Runtime Python 3.11",
    ph_core: "Dipendenze Core e TTS", ph_tray: "Dipendenze Tray GUI", ph_finalize: "Registro, Autostart e Doctor",
    btn_hide_log: "Nascondi log tecnico", btn_show_log: "Mostra log tecnico",
    s5_eyebrow: "STEP 5 DI 5", s5_title: "Hecos è Pronto!",
    s5_sub: "Installazione completata con successo. Puoi avviare Hecos subito.",
    s5_title_warn: "Completato con Avvisi",
    s5_sub_warn: "Il Core è pronto, ma uno o più componenti opzionali richiedono attenzione.",
    s5_title_fail: "Errore durante il Setup",
    s5_sub_fail: "Controlla i dettagli qui sotto oppure apri la Diagnostica.",
    s5_doctor: "Verifica di Sistema (Doctor)",
    btn_back: "← Indietro", btn_next: "Avanti →", btn_install: "▶ Avvia Installazione",
    btn_launch: "▶ Avvia Hecos adesso", btn_close: "Chiudi", btn_recheck: "Ricontrolla",
    uni_desc: "Rimuove i pacchetti Python di Hecos e i collegamenti di avvio automatico. Potrai poi eliminare manualmente le cartelle.",
    uni_smart_title: "Rimuovi solo pacchetti Hecos (Sicuro)",
    uni_smart_desc: "Disinstalla solo i pacchetti elencati in pyproject.toml e disabilita l'autostart.",
    uni_smart_btn: "Rimuovi solo Hecos",
    uni_wipe_title: "Pulizia completa ambiente Python",
    uni_wipe_desc: "Rimuove TUTTI i pacchetti pip da questo interprete Python. Usalo solo se Python è dedicato a Hecos.",
    uni_wipe_btn: "Pulisci tutto l'ambiente",
    st_installed: "Installato", st_not_installed: "Non ancora installato", st_free_disk: "Spazio libero su disco",
  }}
}};

function tr(key) {{
  const dict = I18N[CURRENT_LANG] || I18N.en;
  return dict[key] || I18N.en[key] || key;
}}

function applyTranslations() {{
  document.querySelectorAll('[data-i18n]').forEach(el => {{
    const k = el.getAttribute('data-i18n');
    if (k) el.textContent = tr(k);
  }});
  document.querySelectorAll('.lang-pill').forEach(btn => {{
    btn.classList.toggle('selected', btn.dataset.lang === CURRENT_LANG);
  }});
  renderEnvStatus();
  updateFooterButtons();
}}

function setLang(lang) {{
  CURRENT_LANG = lang;
  applyTranslations();
}}

function renderEnvStatus() {{
  const grid = document.getElementById('env-status-grid');
  const coreBadge = ENV_STATUS.core_installed
    ? `<span class="badge badge-ok">${{tr('st_installed')}} v${{ENV_STATUS.core_version}}</span>`
    : `<span class="badge badge-warn">${{tr('st_not_installed')}}</span>`;
  const trayBadge = ENV_STATUS.tray_installed
    ? `<span class="badge badge-ok">${{tr('st_installed')}} v${{ENV_STATUS.tray_version}}</span>`
    : `<span class="badge badge-warn">${{tr('st_not_installed')}}</span>`;

  grid.innerHTML = `
    <div class="status-box">
      <div class="label">Hecos Core</div>
      <div class="val">${{coreBadge}}</div>
      <div style="font-size:0.74rem; color:var(--muted); margin-top:4px; font-family:var(--font-mono);">${{ENV_STATUS.core_path}}</div>
    </div>
    <div class="status-box">
      <div class="label">Hecos Tray</div>
      <div class="val">${{trayBadge}}</div>
      <div style="font-size:0.74rem; color:var(--muted); margin-top:4px; font-family:var(--font-mono);">${{ENV_STATUS.tray_path}}</div>
    </div>
    <div class="status-box">
      <div class="label">System / Bootstrap Python</div>
      <div class="val">${{ENV_STATUS.os}} (${{ENV_STATUS.arch}}) &bull; Py ${{ENV_STATUS.python_version}}</div>
    </div>
    <div class="status-box">
      <div class="label">${{tr('st_free_disk')}}</div>
      <div class="val">${{ENV_STATUS.free_gb != null ? ENV_STATUS.free_gb + ' GB' : 'N/A'}}</div>
    </div>
  `;
}}

function selectMode(mode) {{
  SELECTED_MODE = mode;
  document.querySelectorAll('.mode-card').forEach(c => c.classList.toggle('selected', c.dataset.mode === mode));
  const showRedl = (mode !== 'tray' && ENV_STATUS.core_installed) || (mode !== 'core' && ENV_STATUS.tray_installed);
  document.getElementById('redownload-panel').style.display = showRedl ? 'block' : 'none';
  updateStep3Visibility();
}}

function updateStep3Visibility() {{
  const wantCore = SELECTED_MODE === 'full' || SELECTED_MODE === 'core';
  const wantTray = SELECTED_MODE === 'full' || SELECTED_MODE === 'tray';
  document.getElementById('field-core-path').style.display = wantCore ? 'block' : 'none';
  document.getElementById('field-tray-path').style.display = wantTray ? 'block' : 'none';
  document.getElementById('row-opt-piper').style.display = wantCore ? 'flex' : 'none';
  document.getElementById('row-opt-autostart').style.display = wantTray ? 'flex' : 'none';
}}

function goToStep(step) {{
  CURRENT_STEP = step;
  document.querySelectorAll('.step-pane').forEach(p => p.classList.remove('active'));
  document.getElementById('pane-' + step).classList.add('active');
  document.querySelectorAll('.step-nav').forEach(li => {{
    const s = parseInt(li.dataset.step, 10);
    li.classList.toggle('active', s === step);
    li.classList.toggle('done', s < step);
  }});
  if (step === 3) {{
    updateStep3Visibility();
    validatePathsNow();
  }}
  updateFooterButtons();
}}

function updateFooterButtons() {{
  const btnBack = document.getElementById('btn-back');
  const btnNext = document.getElementById('btn-next');
  const btnLaunch = document.getElementById('btn-launch');
  const btnClose = document.getElementById('btn-close');

  btnBack.style.display = (CURRENT_STEP > 1 && CURRENT_STEP < 4) ? 'inline-block' : 'none';
  btnNext.style.display = (CURRENT_STEP <= 3) ? 'inline-block' : 'none';
  btnLaunch.style.display = (CURRENT_STEP === 5 && INSTALL_RESULT && (INSTALL_RESULT.core_path || INSTALL_RESULT.tray_path)) ? 'inline-block' : 'none';
  btnClose.style.display = (CURRENT_STEP === 5) ? 'inline-block' : 'none';

  if (CURRENT_STEP === 3) {{
    btnNext.textContent = tr('btn_install');
    btnNext.disabled = !PATHS_VALID;
  }} else {{
    btnNext.textContent = tr('btn_next');
    btnNext.disabled = false;
  }}
}}

function prevStep() {{
  if (CURRENT_STEP > 1 && CURRENT_STEP < 4) goToStep(CURRENT_STEP - 1);
}}

function nextStep() {{
  if (CURRENT_STEP < 3) {{
    goToStep(CURRENT_STEP + 1);
  }} else if (CURRENT_STEP === 3) {{
    startInstallation();
  }}
}}

async function apiPost(url, bodyObj) {{
  const resp = await fetch(url, {{
    method: 'POST',
    headers: {{ 'Content-Type': 'application/json', 'X-CSRF-Token': CSRF_TOKEN }},
    body: JSON.stringify({{ ...bodyObj, csrf_token: CSRF_TOKEN }}),
  }});
  return await resp.json();
}}

function schedulePathValidation() {{
  clearTimeout(pathTimer);
  pathTimer = setTimeout(validatePathsNow, 220);
}}

async function validatePathsNow() {{
  const wantCore = SELECTED_MODE === 'full' || SELECTED_MODE === 'core';
  const wantTray = SELECTED_MODE === 'full' || SELECTED_MODE === 'tray';
  let allOk = true;

  if (wantCore) {{
    const p = document.getElementById('input-core-path').value.trim();
    const res = await apiPost('/api/validate_path', {{ path: p }});
    allOk = allOk && renderPathFeedback('fb-core-path', res);
  }}
  if (wantTray) {{
    const p = document.getElementById('input-tray-path').value.trim();
    const res = await apiPost('/api/validate_path', {{ path: p }});
    allOk = allOk && renderPathFeedback('fb-tray-path', res);
  }}
  PATHS_VALID = allOk;
  updateFooterButtons();
}}

function renderPathFeedback(elId, res) {{
  const el = document.getElementById(elId);
  if (!res.ok) {{
    el.className = 'path-feedback err';
    el.textContent = '[FAIL] ' + (res.errors || []).join('; ');
    return false;
  }}
  const diskTxt = res.free_gb != null ? ` (${{res.free_gb}} GB free)` : '';
  if (res.warnings && res.warnings.length) {{
    el.className = 'path-feedback warn';
    el.textContent = '[WARN] ' + res.warnings.join('; ') + diskTxt;
  }} else {{
    el.className = 'path-feedback ok';
    el.textContent = '[ OK ] Safe installation path' + diskTxt;
  }}
  return true;
}}

async function browseFolder(which) {{
  const inputId = which === 'core' ? 'input-core-path' : 'input-tray-path';
  const cur = document.getElementById(inputId).value.trim();
  const res = await apiPost('/api/browse_folder', {{ initial_dir: cur }});
  if (res.path) {{
    const chosen = res.path.replace(/[\\/]+$/, '');
    const sep = chosen.includes('\\\\') ? '\\\\' : '/';
    if (which === 'core') {{
      const base = chosen.split(/[\\/]/).pop().toLowerCase();
      document.getElementById('input-core-path').value = (base === 'hecos') ? chosen : (chosen + sep + 'Hecos');
      if (SELECTED_MODE === 'full') {{
        const parent = (base === 'hecos') ? chosen.replace(/[\\/][^\\/]+$/, '') : chosen;
        document.getElementById('input-tray-path').value = parent + sep + 'Hecos-Tray';
      }}
    }} else {{
      const base = chosen.split(/[\\/]/).pop().toLowerCase();
      document.getElementById('input-tray-path').value = base.startsWith('hecos-tray') ? chosen : (chosen + sep + 'Hecos-Tray');
    }}
    validatePathsNow();
  }}
}}

let logVisible = true;
function toggleLogBox() {{
  logVisible = !logVisible;
  document.getElementById('log-box').style.display = logVisible ? 'block' : 'none';
  document.getElementById('log-toggle-btn').innerHTML = (logVisible ? '&#9660; ' : '&#9654; ') + tr(logVisible ? 'btn_hide_log' : 'btn_show_log');
}}

function appendLog(msg, level) {{
  const box = document.getElementById('log-box');
  const div = document.createElement('div');
  div.className = 'log-line ' + (level || 'info');
  div.textContent = msg;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}}

function setPhaseBadge(id, status) {{
  const el = document.getElementById('ph-' + id);
  if (!el) return;
  el.className = 'phase-item ' + status;
  const b = el.querySelector('.badge');
  if (status === 'active') {{ b.className = 'badge badge-cyan'; b.textContent = '...'; }}
  else if (status === 'ok') {{ b.className = 'badge badge-ok'; b.textContent = 'OK'; }}
  else if (status === 'warn') {{ b.className = 'badge badge-warn'; b.textContent = 'WARN'; }}
  else if (status === 'fail') {{ b.className = 'badge badge-fail'; b.textContent = 'FAIL'; }}
  else if (status === 'skip') {{ b.className = 'badge'; b.textContent = 'SKIP'; }}
}}

async function startInstallation() {{
  goToStep(4);
  document.getElementById('log-box').innerHTML = '';
  document.getElementById('progress-bar').style.width = '3%';
  document.getElementById('progress-pct').textContent = '3%';
  ['paths','download','python','core','tray','finalize'].forEach(id => {{
    const el = document.getElementById('ph-' + id);
    el.className = 'phase-item';
    const b = el.querySelector('.badge');
    b.className = 'badge badge-cyan';
    b.textContent = '•';
  }});

  const payload = {{
    mode: SELECTED_MODE,
    core_path: document.getElementById('input-core-path').value.trim(),
    tray_path: document.getElementById('input-tray-path').value.trim(),
    redownload: document.getElementById('opt-redownload').checked,
    system_lang: (CURRENT_LANG === 'it') ? 'it' : 'en',
    install_piper: document.getElementById('opt-piper').checked,
    enable_autostart: document.getElementById('opt-autostart').checked,
    create_shortcut: document.getElementById('opt-shortcut').checked,
    force_deps: document.getElementById('opt-force-deps').checked,
  }};

  const startRes = await apiPost('/api/install', payload);
  if (!startRes.started) {{
    appendLog('[FAIL] ' + (startRes.error || 'Could not start installation'), 'error');
    return;
  }}

  const es = new EventSource('/api/events');
  es.onmessage = (ev) => {{
    const data = JSON.parse(ev.data);
    if (data.type === 'log') {{
      appendLog(data.message, data.level);
    }} else if (data.type === 'progress') {{
      document.getElementById('progress-bar').style.width = data.percent + '%';
      document.getElementById('progress-pct').textContent = data.percent + '%';
      document.getElementById('progress-phase').textContent = data.phase + (data.detail ? ' — ' + data.detail : '');
    }} else if (data.type === 'step') {{
      setPhaseBadge(data.id, data.status);
    }} else if (data.type === 'done') {{
      es.close();
      INSTALL_RESULT = data;
      renderFinalStep(data);
      setTimeout(() => goToStep(5), 450);
    }}
  }};
  es.onerror = () => {{
    es.close();
  }};
}}

function renderFinalStep(data) {{
  const title = document.getElementById('done-title');
  const sub = document.getElementById('done-sub');
  if (!data.ok) {{
    title.textContent = tr('s5_title_fail');
    title.style.color = 'var(--red)';
    sub.textContent = tr('s5_sub_fail');
  }} else if (data.warnings && data.warnings.length) {{
    title.textContent = tr('s5_title_warn');
    title.style.color = 'var(--yellow)';
    sub.textContent = tr('s5_sub_warn');
  }} else {{
    title.textContent = tr('s5_title');
    title.style.color = 'var(--green)';
    sub.textContent = tr('s5_sub');
  }}

  let html = '<div class="status-grid">';
  for (const [name, info] of Object.entries(data.components || {{}})) {{
    const cls = info.status === 'ok' ? 'badge-ok' : (info.status === 'warn' ? 'badge-warn' : 'badge-fail');
    html += `<div class="status-box"><div class="label">${{name.toUpperCase()}}</div><div class="val"><span class="badge ${{cls}}">${{info.status.toUpperCase()}}</span></div><div style="font-size:0.74rem; color:var(--muted); margin-top:4px;">${{info.detail}}</div></div>`;
  }}
  html += '</div>';
  if (data.errors && data.errors.length) {{
    html += `<div style="margin-top:12px; color:var(--red); font-size:0.82rem;"><strong>Errors:</strong><ul>${{data.errors.map(e => '<li>' + e + '</li>').join('')}}</ul></div>`;
  }}
  if (data.warnings && data.warnings.length) {{
    html += `<div style="margin-top:12px; color:var(--yellow); font-size:0.82rem;"><strong>Warnings:</strong><ul>${{data.warnings.map(w => '<li>' + w + '</li>').join('')}}</ul></div>`;
  }}
  document.getElementById('done-summary-panel').innerHTML = html;

  if (data.doctor && data.doctor.length) {{
    document.getElementById('done-doctor-panel').style.display = 'block';
    document.getElementById('done-doctor-table').innerHTML = renderDoctorRows(data.doctor);
  }}
}}

function renderDoctorRows(checks) {{
  return checks.map(c => {{
    const cls = c.status === 'ok' ? 'badge-ok' : (c.status === 'warn' ? 'badge-warn' : 'badge-fail');
    return `<tr><td class="diag-name">${{c.name}}</td><td style="width:72px;"><span class="badge ${{cls}}">${{c.status.toUpperCase()}}</span></td><td class="diag-detail">${{c.detail}}</td></tr>`;
  }}).join('');
}}

async function launchHecosNow() {{
  const res = await apiPost('/api/launch', {{
    core_path: (INSTALL_RESULT && INSTALL_RESULT.core_path) || ENV_STATUS.core_path,
    tray_path: (INSTALL_RESULT && INSTALL_RESULT.tray_path) || ENV_STATUS.tray_path,
  }});
  if (res.ok) {{
    await shutdownInstaller();
  }} else {{
    alert(res.message || 'Could not launch Hecos.');
  }}
}}

async function shutdownInstaller() {{
  try {{ await apiPost('/api/shutdown', {{}}); }} catch (e) {{}}
  window.close();
  document.body.innerHTML = '<div style="display:flex;height:100vh;align-items:center;justify-content:center;color:#8b95b0;font-family:Segoe UI,sans-serif;">Setup server stopped. You can close this window.</div>';
}}

function openDoctorModal() {{
  document.getElementById('doctor-modal').classList.add('open');
  runDoctorIntoModal();
}}

async function runDoctorIntoModal() {{
  const body = document.getElementById('doctor-modal-body');
  body.innerHTML = '<div style="color:var(--muted);">Running diagnostics...</div>';
  const res = await apiPost('/api/doctor', {{}});
  if (res.checks && res.checks.length) {{
    body.innerHTML = `<table class="diag-table">${{renderDoctorRows(res.checks)}}</table>`;
  }} else {{
    body.innerHTML = `<div style="color:var(--yellow);">${{res.message || 'Core is not installed yet.'}}</div>`;
  }}
}}

function openUninstallModal() {{
  document.getElementById('uninstall-modal').classList.add('open');
}}

function closeModal(id) {{
  document.getElementById(id).classList.remove('open');
}}

async function runUninstall(kind) {{
  const msg = kind === 'wipe'
    ? 'WIPE ALL Python packages in this environment? This cannot be undone.'
    : 'Remove Hecos packages and autostart shortcuts?';
  if (!confirm(msg)) return;
  const logEl = document.getElementById('uninstall-log');
  logEl.style.display = 'block';
  logEl.textContent = 'Running uninstaller... please wait...';
  const url = kind === 'wipe' ? '/api/uninstall_wipe' : '/api/uninstall_hecos';
  const res = await apiPost(url, {{}});
  logEl.textContent = res.output || (res.ok ? 'Done.' : 'Error.');
}}

// Initialize default fields & language on page load
document.getElementById('input-core-path').value = ENV_STATUS.default_core_path || '';
document.getElementById('input-tray-path').value = ENV_STATUS.default_tray_path || '';
selectMode('full');
applyTranslations();
</script>
</body>
</html>"""
        self.send_html(html)
