# 🌌 Zentra Core Project
<p align="center">
  <img src="https://raw.githubusercontent.com/Zentra-Core/zentra-core.github.io/main/zentra/assets/Zentra_Core_Logo.jpg" width="400" alt="Zentra Logo">
</p>

# Zentra Core - Version 0.19.0 (Runtime Alpha)
Language: [English](README.md) | [Italiano](README_ITA.md) | [Español](README_ESP.md)

# 🤖 Zentra Core
**Native Modular AI Operating System (Private, Fast, Simple)**

---

> [!IMPORTANT]
> **Runtime Alpha Status**: Zentra Core is currently in `v0.18.2`. This is a Local AI Operating Layer that bridges high-level reasoning with root-level system execution.

## 🚀 Overview
**Zentra Core** is a **Native Modular AI Operating System**: a private, local-first ecosystem that bridges AI reasoning with root-level system execution and advanced networking. It transforms local hardware into a sovereign digital entity through an integrated OS-style dashboard and professional-grade security infrastructure.

Built on three core pillars:
* 🛡️ **Privacy First** — 100% local operation, zero cloud dependency, and a 3-tier privacy architecture.
* ⚡ **Extreme Speed** — Optimized native architecture and high-performance plugin system for real-time responsiveness.
* 🧊 **Total Simplicity** — Professional OS-style dashboard and a modular design that makes advanced AI orchestration intuitive.

Now fully migrated to a **stable Runtime Alpha architecture**, Zentra 0.19.0 offers a dedicated Web Interface (Chat + Config) and complete Internationalization. Powered by **LiteLLM**, it supports Ollama, KoboldCpp, and major cloud providers with real-time streaming and local TTS.

---

## ✨ Key Features (v0.18.2)
* 🎨 **Flux Prompt Studio** — Real-time prompt engineering for Flux.1 with automatic sidecar metadata persistence.
* 🖼️ **Image Metadata Injection** — Generative AI results now include hidden JSON sidecars (.txt) containing prompt, seed, and sampler info for professional workflows.
* 🎭 **Enhanced Chat UI** — New Chat headers with visible User/Persona names, timestamps, and improved message action positioning (Copy/Edit/Regenerate).
* 🔄 **Fixed Regeneration** — Resolved critical history duplication and session-mismatch issues during message regeneration.
* 🛡️ **3-Tier Privacy Architecture** — Unified session management with **Normal**, **Auto-Wipe** (RAM-only store, cleared on exit), and **Incognito** (Zero-trace) modes.
* 🔌 **Universal Tool Hub (MCP Bridge)** — Native support for the **Model Context Protocol**. Connect to thousands of external AI tools with a single click.
* 🔭 **Deep MCP Discovery** — Advanced explorer with multi-registry search (Smithery, MCPSkills, GitHub) and one-click installation.
* 🔒 **Professional Zentra PKI (HTTPS)** — Self-signing Root CA for a full "Green Lock" experience on all devices.
* 🏗️ **Native WebUI Plugin** — High-performance, low-latency interface for desktop and mobile.
* 💾 **Zentra Drive (File Manager)** — Integrated dual-panel file management and editor.

---

## 🧠 How It Works
Zentra Core is built around a modular architecture:
* **Core** → AI routing, processing, execution
* **Plugins** → Actions and capabilities (system, web, media, etc.)
* **Memory** → Identity and persistent storage
* **UI** → User interaction layer
* **Bridge** → External integrations and APIs

The AI generates structured commands that are interpreted and executed through the plugin system.

---

## ⚡ Quick Start (One-Click Installation)
The easiest way to install and configure Zentra Core from scratch is using the **Universal Setup Wizard**.

### 1. Clone the repository
```bash
git clone https://github.com/Zentra-Core/zentra-core.github.io.git
cd zentra-core.github.io
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
| **Windows** | `ZENTRA_WEB_RUN_WIN.bat` | Launches ONLY the Web Interface & Server |
| **Linux** | `zentra_web_run.sh` | Launches ONLY the Web Interface & Server |
| **Windows** | `ZENTRA_CONSOLE_RUN_WIN.bat` | Launches ONLY the Terminal Console (TUI) |
| **Linux** | `ZENTRA_CONSOLE_RUN.sh` | Launches ONLY the Terminal Console (TUI) |
| **Windows** | `INSTALL_SERVICE_WIN.bat` | Installs Zentra as a Windows Service |
| **Linux** | `INSTALL_SERVICE_LINUX.sh` | Installs Zentra as a systemd user service |
| **Windows** | `UNINSTALL_SERVICE_WIN.bat` | Safely removes the Zentra Windows Service |
| **Linux** | `UNINSTALL_SERVICE_LINUX.sh` | Safely removes the systemd user service |
| **Windows** | `INSTALL_ZENTRA_WIN.bat` | Manual dependency install & Piper setup |
| **Linux** | `INSTALL_ZENTRA_LINUX.sh` | Manual dependency install & Piper setup |

### 4. Configuration & First Run
Zentra is designed for a professional "download-and-play" experience.
- On your first run, the system will detect that `system.yaml` and `routing_overrides.yaml` are missing.
- It will **automatically generate** these files by copying the templates from `zentra/config/data/*.example`.
- You can find your personal configuration in `zentra/config/data/system.yaml` (main settings) and `routing_overrides.yaml` (AI routing rules).
- **Pro Tip**: Use the built-in [In-WebUI Routing Editor] to safely modify these rules without touching code.

### 🔐 Login & Authentication
Zentra v0.16.0 requires mandatory Auth. The default first-time login is:
- **Username:** `admin`
- **Password:** `zentra`

We strongly recommend changing the password immediately from the **Users Tab** inside the Configuration Panel.

**Password Recovery:**
If you get locked out, run `python scripts/reset_admin.py` from the terminal to force a new password, or manually delete the `memory/users.db` file to reset the system defaults.

---

## 🧠 Supported AI Backends (LLM Engines)

Zentra is completely offline by default and requires a local AI engine to process logic and conversation. During setup, you must install one of the independent backends below. Zentra will automatically detect them.

### 🔹 1. Ollama (Recommended)
Fast, optimized, and easy to run locally as a background service.
- **Download**: 👉 https://ollama.com/download
- **Setup**: Once installed, open your terminal/command prompt and run `ollama run llama3.2` to download and test a lightweight fast model. Zentra will instantly detect it.

### 🔹 2. KoboldCpp (Alternative)
Perfect for GGUF manual models and older hardware without heavy installation.
- **Download**: 👉 https://github.com/LostRuins/koboldcpp/releases
- **Setup**: Download the `.exe` (or Linux binary), double-click it, select any GGUF instruction model downloaded from HuggingFace, and launch. Zentra will connect via port `5001`.

---

## 🔌 Plugin System
Zentra uses a dynamic plugin architecture. Each plugin can register commands, execute system actions, and extend AI capabilities.

Included plugins:
* **System control & File manager**
* **Web automation & Hardware dashboard**
* **Media control & Model switching**
* **Memory management**

---

## 💾 Memory & Voice Systems

### 🗄️ Memory System
Zentra includes a persistent memory layer powered by SQLite for lightweight local storage. It stores conversations, maintains identity, and saves user preferences.

### 🎙️ Voice System
* **Speech-to-text input**
* **Text-to-speech output**
* **Real-time interaction**

---

## 🔗 Integrations & Privacy

### 🤝 Integrations
Zentra can integrate with:
* **Open WebUI** (chat + streaming)
* **Home Assistant** (via bridge)

### 🔐 Privacy First
Zentra is designed with privacy in mind: Runs 100% locally, no mandatory cloud services, and full control over data.

---

## 🛣️ Roadmap
- [ ] 📱 Telegram integration (remote control)
- [ ] 🧠 Advanced memory system
- [ ] 🤖 Multi-agent architecture
- [ ] 🛒 Plugin marketplace
- [ ] 🎨 Improved UI/UX

---

## ⚠️ Disclaimer
Zentra can execute system-level commands and control your environment. Use responsibly. The author is not responsible for misuse or damage.

---

## 📜 License
GPL-3.0 License

---

## 👥 Credits & Contact
Lead Developer: Antonio Meloni (Tony)
Official Email: zentra.core.systems@gmail.com

---

## 📚 Documentation
Zentra Core uses a modular documentation system localized in EN, IT, and ES.

### Local Access (Modular)
Detailed guides are located in the `docs/` folder:
- 📖 **[Unified Guide](docs/UNIFIED_GUIDE_EN.md)**: Everything you need to know about v0.17.0.
- 🏗️ **[Technical Guide](docs/tech/)**: (Admin/Dev) System architecture and OOP details.


### Online Access
The documentation is also synchronized with the **[GitHub Wiki](https://github.com/Zentra-Core/zentra-core.github.io/wiki)**.

---

## 💡 Vision
Zentra Core aims to become a fully autonomous, local AI assistant platform — a private, extensible alternative to cloud-based AI systems.
