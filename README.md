# 🌌 Hecos Project
<p align="center">
  <img src="hecos/assets/Hecos_Logo_Banner.png" width="400" alt="Hecos Logo">
</p>

# Hecos - Version 0.21.0 (Runtime Alpha)
Language: [English](README.md) | [Italiano](README_ITA.md) | [Español](README_ESP.md)

# 🤖 Hecos
**Helping Companion System (Private, Fast, Simple)**

---

> **Runtime Alpha Status**: Hecos is currently in `v0.21.0`. This is a Helping Companion System that bridges high-level reasoning with root-level system execution.

## 🚀 Overview
**Hecos** is a **Helping Companion System**: a private, local-first ecosystem that bridges AI reasoning with root-level system execution and advanced networking. It transforms local hardware into a sovereign digital entity through an integrated dashboard and professional-grade security infrastructure.

Built on three core pillars:
* 🛡️ **Privacy First** — 100% local operation, zero cloud dependency, and a 3-tier privacy architecture.
* ⚡ **Extreme Speed** — Optimized native architecture and high-performance plugin system for real-time responsiveness.
* 🧊 **Total Simplicity** — Professional dashboard and a modular design that makes advanced AI orchestration intuitive.

Now fully migrated to a **stable Runtime Alpha architecture**, Hecos 0.21.0 offers a dedicated Web Interface (Chat + Config) and complete Internationalization. Powered by **LiteLLM**, it supports Ollama, KoboldCpp, and major cloud providers with real-time streaming and local TTS.

---

## ✨ Key Features (v0.21.0)
* **📅 Integrated Calendar** — Full calendar module with holiday tracking and localized event color coding.
* **⏰ Reminder Module** — NLP-powered task scheduler with snooze capabilities and active OS notifications.
* **💻 Action Window** — Clean, terminal-style console directly inside the chat UI for monitoring native system execution and background processes.
* **🎵 New Media Player** — Advanced audio backend (VLC 64-bit + FFplay fallback) supporting resilient resume/pause state, dynamic playlist calculations, and global volume control.
* 🎨 **Flux Prompt Studio** — Real-time prompt engineering for Flux.1 with automatic sidecar metadata persistence.
* 🖼️ **Image Metadata Injection** — Generative AI results now include hidden JSON sidecars (.txt) containing prompt, seed, and sampler info for professional workflows.
* 🎭 **Enhanced Chat UI** — New Chat headers with visible User/Persona names, timestamps, and improved message action positioning (Copy/Edit/Regenerate).
* 🔄 **Fixed Regeneration** — Resolved critical history duplication and session-mismatch issues during message regeneration.
* 🛡️ **3-Tier Privacy Architecture** — Unified session management with **Normal**, **Auto-Wipe** (RAM-only store, cleared on exit), and **Incognito** (Zero-trace) modes.
* 🔌 **Universal Tool Hub (MCP Bridge)** — Native support for the **Model Context Protocol**. Connect to thousands of external AI tools with a single click.
* 🔭 **Deep MCP Discovery** — Advanced explorer with multi-registry search (Smithery, MCPSkills, GitHub) and one-click installation.
* 🔒 **Professional Hecos PKI (HTTPS)** — Self-signing Root CA for a full "Green Lock" experience on all devices.
* 🏗️ **Native WebUI Plugin** — High-performance, low-latency interface for desktop and mobile.
* 🎛️ **Control Room & Widgets** — A customizable, masonry-style dashboard for real-time widgets and OS telemetry.
* 🌐 **Browser Automation** — Native plugin for semantic web interaction and scraping.
* ⌨️ **OS Automation** — Native plugin for programmatic mouse and keyboard control.
* 💾 **Hecos Drive (File Manager)** — Integrated dual-panel file management and editor.

---

## 🧠 How It Works
Hecos is built around a modular architecture:
* **Core** → AI routing, processing, execution
* **Plugins** → Actions and capabilities (system, web, media, etc.)
* **Memory** → Identity and persistent storage
* **UI** → User interaction layer
* **Bridge** → External integrations and APIs

The AI generates structured commands that are interpreted and executed through the plugin system.

---

## ⚡ Quick Start (One-Click Installation)
The easiest way to install and configure Hecos from scratch is using the **Universal Setup Wizard**.

### 1. Clone the repository
```bash
git clone https://github.com/Hecos-Project/Hecos.git
cd Hecos
```

### 2. Launch the Setup Wizard
Run the bootstrap script for your platform. This will automatically check for Python, install dependencies, and launch the configuration wizard in your browser.

**Windows:**
```powershell
.\START_SETUP_HERE_WIN.bat
```

**Linux:**
```bash
bash START_SETUP_HERE_LINUX.sh
```

### 3. Manual Components & Utility Scripts
If you prefer to run specific components or perform maintenance manually, use these dedicated scripts:

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
| **Linux** | `scripts/linux/setup/INSTALL_HECOS_LINUX.sh` | Manual dependency install & Piper setup |

### 4. Configuration & First Run
Hecos is designed for a professional "download-and-play" experience.
- On your first run, the system will detect that `system.yaml` and `routing_overrides.yaml` are missing.
- It will **automatically generate** these files by copying the templates from `hecos/config/data/*.example`.
- You can find your personal configuration in `hecos/config/data/system.yaml` (main settings) and `routing_overrides.yaml` (AI routing rules).
- **Pro Tip**: Use the built-in [In-WebUI Routing Editor] to safely modify these rules without touching code.

### 🔐 Login & Authentication
Hecos v0.16.0 requires mandatory Auth. The default first-time login is:
- **Username:** `admin`
- **Password:** `hecos`

We strongly recommend changing the password immediately from the **Users Tab** inside the Configuration Panel.

**Password Recovery:**
If you get locked out, run `python scripts/reset_admin.py` from the terminal to force a new password, or manually delete the `memory/users.db` file to reset the system defaults.

### 🛡️ Stealth Mode (No Windows)
If you want Hecos to run completely in the background without any visible terminal windows:
1.  **Use the Tray Icon**: Launch Hecos via the tray icon. It will manage the system components invisibly in the background.
3.  **Silent Startup**: Use `START_HECOS_SILENT_WIN.vbs` for a 100% invisible launch (no console window).
3.  **Manual Recovery**: If you accidentally close the tray icon, use `START_HECOS_TRAY_WIN.bat`.

---

## 🧠 Supported AI Backends (LLM Engines)

Hecos is completely offline by default and requires a local AI engine to process logic and conversation. During setup, you must install one of the independent backends below. Hecos will automatically detect them.

### 🔹 1. Ollama (Recommended)
Fast, optimized, and easy to run locally as a background service.
- **Download**: 👉 https://ollama.com/download
- **Setup**: Once installed, open your terminal/command prompt and run `ollama run llama3.2` to download and test a lightweight fast model. Hecos will instantly detect it.

### 🔹 3. VLC Media Player (Optional, for Multimedia)
Required for high-fidelity media playback, volume control, and seeking.
- **IMPORTANT**: If using 64-bit Python (default), you **MUST** install the **64-bit version** of VLC.
- **Download**: 👉 https://www.videolan.org/vlc/

### 🔹 2. KoboldCpp (Alternative)
Perfect for GGUF manual models and older hardware without heavy installation.
- **Download**: 👉 https://github.com/LostRuins/koboldcpp/releases
- **Setup**: Download the `.exe` (or Linux binary), double-click it, select any GGUF instruction model downloaded from HuggingFace, and launch. Hecos will connect via port `5001`.

---

## 🔌 Plugin System
Hecos uses a dynamic plugin architecture. Each plugin can register commands, execute system actions, and extend AI capabilities.

Included plugins:
* **System control & File manager**
* **Web automation & Hardware dashboard**
* **Media control & Model switching**
* **Memory management**

---

## 💾 Memory & Voice Systems

### 🗄️ Memory System
Hecos includes a persistent memory layer powered by SQLite for lightweight local storage. It stores conversations, maintains identity, and saves user preferences.

### 🎙️ Voice System
* **Speech-to-text input**
* **Text-to-speech output**
* **Real-time interaction**

---

## 🔗 Integrations & Privacy

### 🤝 Integrations
Hecos can integrate with:
* **Open WebUI** (chat + streaming)
* **Home Assistant** (via bridge)

### 🔐 Privacy First
Hecos is designed with privacy in mind: Runs 100% locally, no mandatory cloud services, and full control over data.

---

## 🛣️ Roadmap
- [ ] 📱 Telegram integration (remote control)
- [ ] 🧠 Advanced memory system
- [ ] 🤖 Multi-agent architecture
- [ ] 🛒 Plugin marketplace
- [ ] 🎨 Improved UI/UX

---

## ⚠️ Disclaimer
Hecos can execute system-level commands and control your environment. Use responsibly. The author is not responsible for misuse or damage.

---

## 📜 License
GPL-3.0 License

---

## 👥 Credits & Contact
Lead Developer: Antonio Meloni (Tony)
Official Email: hecos.project@gmail.com

---

## 📚 Documentation
Hecos uses a modular documentation system localized in EN, IT, and ES.

### Local Access (Modular)
Detailed guides are located in the `docs/` folder:
- 📖 **[Unified Guide](docs/UNIFIED_GUIDE_EN.md)**: Everything you need to know about v0.21.0.
- 🏗️ **[Technical Guide](docs/tech/)**: (Admin/Dev) System architecture and OOP details.


### Online Access
The documentation is also synchronized with the **[GitHub Wiki](https://github.com/Hecos-Project/Hecos/wiki)**.

---

## 💡 Vision
Hecos aims to become a fully autonomous, local AI assistant platform — a private, extensible alternative to cloud-based AI systems.
