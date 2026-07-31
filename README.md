# 🌌 Hecos Project
<p align="center">
  <img src="hecos/assets/Hecos_Logo_Banner.png" width="400" alt="Hecos Logo">
</p>

# Hecos - Version 0.45.0 (Runtime Alpha)
Language: [English](README.md) | [Italiano](README_ITA.md) | [Español](README_ESP.md)

# 🤖 Hecos
**Helping Companion System (Private, Fast, Simple)**[cite: 1]

---

> **Runtime Alpha Status**: Hecos is currently in `v0.45.0`[cite: 1]. This is a Helping Companion System acting as a bridge between high-level reasoning and root system execution[cite: 1].

## 🚀 Overview
**Hecos** is a **Helping Companion System**: a private, local-first ecosystem designed to seamlessly bridge technology and human life by combining AI reasoning, visual automation, and direct system execution[cite: 1]. Rather than chasing abstract concepts like digital sovereignty, Hecos focuses on a single, pragmatic mission: **improving human life** by turning local hardware into a highly efficient, practical everyday tool[cite: 1].

Built on three core pillars:
* 🛡️ **Privacy First** — 100% local operation, zero cloud dependency, and a 3-tier privacy architecture[cite: 1].
* ⚡ **Extreme Speed** — Optimized native architecture and high-performance plugin system for real-time responsiveness[cite: 1].
* 🧊 **Total Simplicity** — Professional dashboard and a modular design that makes advanced orchestration intuitive[cite: 1].

Now fully migrated to a **stable Runtime Alpha architecture**, Hecos 0.45.0 brings a dedicated Web Interface (Chat + Config) and full internationalization[cite: 1]. Powered by **LiteLLM**, it supports Ollama, KoboldCpp, and major cloud providers with real-time streaming and local TTS[cite: 1].

---

## ✨ Key Features (v0.45.0)
* 📦 **HPM 0.40 Architecture** — Fully migrated to Pydantic+TOML configurations, introducing dependency version constraints and locked `pip_requirements`.
* 🛠️ **External Dependency Manager (EDM)** — New system that auto-detects missing core dependencies (Node, Tesseract, VC++), enabling one-click downloads directly from the WebUI.
* 🛡️ **HPM Integrity Verification** — New `/verify` API and Control Room UI to cryptographically validate installed package files against their Ed25519-signed manifest hashes.
* 🔒 **Hecos SDK (Total Isolation)** — Run HPM packages in dedicated, isolated subprocesses and independent virtual environments (venv) to prevent dependency hell and main event loop blocking.
* ⚡ **HDCS (Direct Commands)** — Instantly execute 150+ native functions bypassing the AI brain via `/` in chat or `Ctrl+Alt+Space` globally[cite: 1].
* ⚙️ **Flows Automation Engine** — Visual drag-and-drop node editor for creating complex, multi-step triggers and actions, fully integrated with NLP voice commands[cite: 1].
* **📅 Integrated Calendar** — Full calendar module with holiday tracking and localized event color coding[cite: 1].
* **⏰ Reminder Module** — NLP-powered task scheduler with snooze capabilities and active OS notifications[cite: 1].
* **💻 Action Window** — Clean, terminal-style console directly inside the chat UI for monitoring native system execution and background processes[cite: 1].
* **🎵 New Media Player** — Advanced audio backend (VLC 64-bit + FFplay fallback) supporting resilient resume/pause state, dynamic playlist calculations, and global volume control[cite: 1].
* 🎨 **Flux Prompt Studio** — Real-time prompt engineering for Flux.1 with automatic sidecar metadata persistence[cite: 1].
* 🖼️ **Image Metadata Injection** — Generative AI results now include hidden JSON sidecars (.txt) containing prompt, seed, and sampler info for professional workflows[cite: 1].
* 🎭 **Enhanced Chat UI** — New Chat headers with visible User/Persona names, timestamps, and improved message action positioning (Copy/Edit/Regenerate)[cite: 1].
* 🔄 **Fixed Regeneration** — Resolved critical history duplication and session-mismatch issues during message regeneration[cite: 1].
* 🗃️ **Dual-Mode Chat Archive** — Context-aware archiving system with individual chat restore and bulk-delete capabilities[cite: 1].
* 🧠 **High-Performance RAG (FastEmbed)** — CPU-native, multi-tenant vector memory utilizing ONNX and LanceDB for blazing-fast document ingestion[cite: 1].
* 🔐 **Per-User Vault Isolation** — Consolidated memory architecture ensuring absolute privacy separation for semantic data and chat history per profile[cite: 1].
* 🛡️ **3-Tier Privacy Architecture** — Unified session management with **Normal**, **Auto-Wipe** (RAM-only store, cleared on exit), and **Incognito** (Zero-trace) modes[cite: 1].
* 📦 **Hecos Package Manager (HPM)** — The ultimate piece for universal extensibility. A centralized, dynamic installer that supports standalone `.hpkg` bundles. Easily install third-party plugins, widgets, and config panels with drag-and-drop, isolated configurations, and Ed25519 digital signatures[cite: 1].
* 🔌 **Universal Tool Hub (MCP Bridge)** — Native support for the **Model Context Protocol**. Connect to thousands of external AI tools with a single click[cite: 1].
* 🔭 **Deep MCP Discovery** — Advanced explorer with multi-registry search (Smithery, MCPSkills, GitHub) and one-click installation[cite: 1].
* 🔒 **Professional Hecos PKI (HTTPS)** — Self-signing Root CA for a full "Green Lock" experience on all devices[cite: 1].
* 🏗️ **Native WebUI Plugin** — High-performance, low-latency interface for desktop and mobile[cite: 1].
* 🎛️ **Control Room & Widgets** — A customizable, masonry-style dashboard for real-time widgets and OS telemetry[cite: 1].
* 🌐 **Browser Automation** — Native plugin for semantic web interaction and scraping[cite: 1].
* ⌨️ **OS Automation** — Native plugin for programmatic mouse and keyboard control[cite: 1].
* 💾 **Hecos Drive (File Manager)** — Integrated dual-panel file management and editor[cite: 1].

---

## 🧠 How It Works
Hecos is built around a highly modular, 8-layer architecture. Everything is a **module**[cite: 1]:
* **Core Modules** → Built-in, non-removable OS/system functions[cite: 1]
* **Plugins** → Reactive tools and capabilities called by the AI (system, web, media, etc.)[cite: 1]
* **Apps** → Autonomous mini-applications with their own standalone UI and lifecycle[cite: 1]
* **Personas** → Installable AI personalities and behavioral profiles[cite: 1]
* **Widgets** → Interactive frontend components for the Control Room dashboard[cite: 1]
* **Themes** → Custom CSS and styling packages for the UI[cite: 1]
* **Skill Packs** → Additional slash-command packs for the chat interface[cite: 1]
* **MCP Servers** → Universal external tool bridges via the Model Context Protocol[cite: 1]

The AI generates structured commands that are interpreted and executed through the plugin system[cite: 1].

---

### 🎭 The Soul of the Machine: Native Personas

A fundamental capability of Hecos is its native **Personality Switching**. Hecos isn't just a cold, rigid assistant — it adapts its behavior, tone, and character based on the persona you load. Each persona is programmed to act differently and fulfill a unique role in your daily life[cite: 1].

<p align="center">
  <img src="https://raw.githubusercontent.com/Hecos-Project/hecos/main/hecos/assets/Urania_9800_Logo.png" width="400">
  <br>
  <em>Urania 9800, the official Hecos Mascot and your everyday friendly companion.</em>[cite: 1]
</p>

Out of the box, Hecos includes several pre-configured personalities:
* **Hecos System Soul** — The neutral, rigid, and detached core system. Perfect for raw automation and precise tasks[cite: 1].
* **Urania 9800** — The lively mascot. A true, everyday friend designed for casual, empathetic, and cheerful interaction[cite: 1].
* **Sebastian Pro** — The perfect, highly professional butler. Polite, efficient, and eager to serve[cite: 1].
* **Atlas** — The imposing, authoritative digital guardian[cite: 1].
* **Nova X-01** — A precise, analytical robotic entity for those who prefer purely logical interactions[cite: 1].

You can hot-swap these personas at any time, changing not just the voice and tone, but the very "soul" of the system[cite: 1].

---

## ⚡ Quick Start (One-Click Installation)
The easiest way to install and configure Hecos from scratch is using the **Universal Setup Wizard**[cite: 1].

### 1. Clone the repository
```bash
git clone [https://github.com/Hecos-Project/Hecos.git](https://github.com/Hecos-Project/Hecos.git)
cd Hecos
```[cite: 1]

### 2. Launch the Setup Wizard
Run the bootstrap script for your platform. This will automatically check for Python, install dependencies, and launch the configuration wizard in your browser[cite: 1].

**Windows:**
```powershell
.\START_SETUP_HERE_WIN.bat
```[cite: 1]

**Linux:**
```bash
bash START_SETUP_HERE_LINUX.sh
```[cite: 1]

### 3. Manual Components & Utility Scripts
If you prefer to run specific components or perform maintenance manually, use these dedicated scripts[cite: 1]:

| Platform | Script | Description |
| :--- | :--- | :--- |
| **All** | `main.py` | Starts the full system (Tray + WebUI + Backend) |
| **Windows** | `RESTART_TRAY_ICON_WIN.bat` | Restore the tray icon if accidentally closed |
| **Linux** | `RESTART_TRAY_ICON_LINUX.sh` | Restore the tray icon if accidentally closed |
| **Windows** | `scripts\windows\run\HECOS_WEB_RUN_WIN.bat` | Launches ONLY the Web Interface & Server |
| **Linux** | `scripts/linux/run/hecos_web_run.sh` | Launches ONLY the Web Interface & Server |
| **Windows** | `scripts\windows\run\HECOS_CONSOLE_RUN_WIN.bat` | Launches ONLY the Terminal Console (TUI) |
| **Linux** | `scripts/linux/run/HECOS_CONSOLE_RUN.sh` | Launches ONLY the Terminal Console (TUI) |
| **Windows** | `scripts\windows\setup\INSTALL_HECOS_WIN.bat` | Manual dependency install & Piper setup |
| **Linux** | `scripts/linux/setup/INSTALL_HECOS_LINUX.sh` | Manual dependency install & Piper setup |[cite: 1]

### 4. Configuration & First Run
Hecos is designed for a professional "download-and-play" experience[cite: 1].
- On your first run, the system will detect that `system.yaml` and `routing_overrides.yaml` are missing[cite: 1].
- It will **automatically generate** these files by copying the templates from `hecos/config/data/*.example`[cite: 1].
- You can find your personal configuration in `hecos/config/data/system.yaml` (main settings) and `routing_overrides.yaml` (AI routing rules)[cite: 1].
- **Pro Tip**: Use the built-in [In-WebUI Routing Editor] to safely modify these rules without touching code[cite: 1].

### 🔐 Login & Authentication
Hecos requires mandatory Auth[cite: 1]. The default first-time login is:
- **Username:** `admin`
- **Password:** `hecos`[cite: 1]

We strongly recommend changing the password immediately from the **Users Tab** inside the Configuration Panel[cite: 1].

**Password Recovery:**
If you get locked out, run `python scripts/reset_admin.py` from the terminal to force a new password, or manually delete the `memory/users.db` file to reset the system defaults[cite: 1].

### 🛡️ Stealth Mode (Windowless)
If you want Hecos to run completely in the background without any visible terminal windows[cite: 1]:
1. **Use the Tray Icon**: Start Hecos using the system tray icon. It will manage the system components invisibly in the background[cite: 1].
2. **Silent Boot**: Use `START_HECOS_SILENT_WIN.vbs` for a 100% invisible start (no console windows)[cite: 1].
3. **Manual Recovery**: If you close the icon by mistake, use `START_HECOS_TRAY_WIN.bat`[cite: 1].

---

## 💻 Platform Compatibility & OS Support

While many extension packages in the Hecos ecosystem (such as **Browser Automation**, **Messenger**, **Calendar**, **Weather Pro**, **Mail**, **Image Gen**, **Reminder**, **Lists**, **Maps**, and **Quick Links**) are completely cross-platform and designed to run on Linux and macOS, **the core Hecos system itself is currently tested exclusively on Windows 10 and 11**.

Running the core system on Linux or macOS is possible but may require manual adjustments, and certain native OS features (like advanced PC Automation UI inspection) are Windows-only by design.

---

## 🛠️ Essential System Requirements (Windows)
If you have just reinstalled Windows or are setting up Hecos for the first time, you must ensure these **fundamental** system packages are present for all modules to work correctly.

💡 **NEW (v0.45.0 - EDM)**: Hecos now integrates an **External Dependency Manager (EDM)**! If Tesseract, Node.js, or VC++ Redistributable are missing, the EDM will automatically detect them and allow you to download them in the background with a single click from the WebUI, directly from the `Hecos-Dependencies` GitHub repository. Alternatively, you can install them manually:

1. ⚙️ **Microsoft Visual C++ Redistributable (Mandatory)**
   - *What it's for*: Required by the RAG Memory engine (ONNX/FastEmbed). Without this package, you will get missing DLL errors and document search will not work[cite: 1].
   - *Download*: 👉 [Download VC++ Redist x64](https://aka.ms/vs/17/release/vc_redist.x64.exe)[cite: 1]

2. 🎵 **VLC Media Player 64-bit (Mandatory)**
   - *What it's for*: The Audio engine and integrated Media Player of Hecos use VLC libraries in the background to play music, alarms, and TTS voice output[cite: 1].
   - *Download*: 👉 [Download VLC 64-bit](https://www.videolan.org/vlc/download-windows.html)[cite: 1]

3. 👁️ **Tesseract OCR (Recommended for Vision)**
   - *What it's for*: Necessary for advanced visual capabilities and to read text on the screen via OCR (`pytesseract`)[cite: 1]. 
   - *Download*: 👉 [Download Tesseract OCR for Windows](https://github.com/UB-Mannheim/tesseract/wiki)[cite: 1]

4. 🟢 **Node.js (Recommended / Required for Canvas & UI Development)**
   - *What it's for*: Required to compile, build, and manage dependencies for the Flows Visual Node Editor module (ReactFlow/Vite). If you need to rebuild the canvas frontend (`npm run build`), Node.js is required[cite: 1].
   - *Download*: 👉 [Download Node.js LTS](https://nodejs.org/)[cite: 1]

---

### 📦 Offline Installation (The `dependencies` Folder)
For your convenience, all required installation packages are included offline directly inside the `dependencies/` folder at the root of the project[cite: 1]:
* `dependencies/VC_redist.x64.exe` -> Microsoft Visual C++ Redistributable (ONNX/RAG)[cite: 1]
* `dependencies/node-v24.16.0-x64.msi` -> Node.js LTS (Canvas / Frontend Build)[cite: 1]
* `dependencies/tesseract-ocr-w64-setup-5.5.0.20241111.exe` -> Tesseract OCR (Vision)[cite: 1]

*Note: We highly recommend installing these components before launching the automatic Hecos setup.*[cite: 1]

---

## 🧠 Supported AI Backends (LLM Engines)

Hecos is completely offline by default and requires a local AI engine to process logic and conversation[cite: 1]. During setup, you must install one of the independent backends below[cite: 1]. Hecos will automatically detect them[cite: 1].

### 🔹 1. Ollama (Recommended)
Fast, optimized, and easy to run locally as a background service[cite: 1].
- **Download**: 👉 https://ollama.com/download[cite: 1]
- **Setup**: Once installed, open your terminal/command prompt and run `ollama run llama3.2` to download and test a lightweight fast model[cite: 1]. Hecos will instantly detect it[cite: 1].

### 🔹 2. KoboldCpp (Alternative)
Perfect for GGUF manual models and older hardware without heavy installation[cite: 1].
- **Download**: 👉 https://github.com/LostRuins/koboldcpp/releases[cite: 1]
- **Setup**: Download the `.exe` (or Linux binary), double-click it, select any GGUF instruction model downloaded from HuggingFace, and launch[cite: 1]. Hecos will connect via port `5001`[cite: 1].

---

## 🔌 Plugin System
Hecos uses a dynamic plugin architecture[cite: 1]. Each plugin can register commands, execute system actions, and extend AI capabilities[cite: 1].

Included plugins:
* **System control & File manager**[cite: 1]
* **Web automation & Hardware dashboard**[cite: 1]
* **Media control & Model switching**[cite: 1]
* **Memory management**[cite: 1]

You can install new packages dynamically by dragging and dropping `.hpkg` bundles into the **Package Manager** inside the WebUI[cite: 1]. These standalone bundles contain their own logic, UI panels, and configuration schemas, making Hecos infinitely and universally extensible[cite: 1]. All packages are verified via Ed25519 digital signatures for absolute security[cite: 1].

---

## 💾 Memory & Voice Systems

### 🗄️ Memory System
Hecos includes a persistent memory layer powered by SQLite for lightweight local storage[cite: 1]. It stores conversations, maintains identity, and saves user preferences[cite: 1].

### 🎙️ Voice System
* **Speech-to-text input**[cite: 1]
* **Text-to-speech output**[cite: 1]
* **Real-time interaction**[cite: 1]

---

## 🔗 Integrations & Privacy

### 🤝 Integrations
Hecos can integrate with:
* **Open WebUI** (chat + streaming)[cite: 1]
* **Home Assistant** (via bridge)[cite: 1]

### 🔐 Privacy First
Hecos is designed with a strict focus on utility and discretion: Runs 100% locally, features no mandatory cloud services, and provides full control over data[cite: 1].

---

## 🛣️ Roadmap
- [ ] 📱 Telegram integration (remote control)[cite: 1]
- [ ] 🧠 Advanced memory system[cite: 1]
- [ ] 🤖 Multi-agent architecture[cite: 1]
- [ ] 🛒 Plugin marketplace[cite: 1]
- [ ] 🎨 Improved UI/UX[cite: 1]

---

## ⚠️ Disclaimer
Hecos can execute system-level commands and control your environment[cite: 1]. Use responsibly[cite: 1]. The author is not responsible for misuse or damage[cite: 1].

---

## 📜 License
GPL-3.0 License[cite: 1]

---

## 👥 Credits & Contact
Lead Developer: Antonio Meloni (Tony)[cite: 1]
Official Email: hecos.project@gmail.com[cite: 1]

---

## 📚 Documentation
Hecos uses a modular documentation system localized in EN, IT, and ES[cite: 1].

### Local Access (Modular)
Detailed guides are located in the `docs/` folder[cite: 1]:
- 📖 **[Unified Guide](docs/UNIFIED_GUIDE_EN.md)**: Everything you need to know about v0.44.0[cite: 1].
- 🏗️ **[Technical Guide](docs/tech/)**: (Admin/Dev) System architecture and OOP details[cite: 1].

### Online Access
The documentation is also synchronized with the **[GitHub Wiki](https://github.com/Hecos-Project/Hecos/wiki)**[cite: 1].

---

## 💡 Vision
Hecos aims to become a fully autonomous, local AI assistant platform — a private, extensible alternative to cloud-based AI systems, focused exclusively on serving and improving human life[cite: 1].