# 🌌 Zentra Core Project
<p align="center">
  <img src="https://raw.githubusercontent.com/Zentra-Core/zentra-core.github.io/main/zentra/assets/Zentra_Core_Logo.jpg" width="400" alt="Zentra Logo">
</p>

# Zentra Core - Version 0.15.2 (Runtime Alpha)
Language: [English](README.md) | [Italiano](README_ITA.md) | [Español](README_ESP.md)

# 🤖 Zentra Core
**Your Personal Offline AI Assistant (Private, Modular, Powerful)**

---

> [!WARNING]
> **Runtime Alpha Status**: Zentra Core is currently in `v0.15.2`. This repository contains the engine, backend, AI reasoning modules, and the main native WebUI. Features may change, and the system is not yet considered stable. Use with caution.

## 🚀 Overview
**Zentra Core** is a local-first AI assistant platform that runs entirely on your machine.
It combines local LLMs, voice interaction, system automation, and a modular plugin architecture to create a fully customizable AI companion.

Now fully migrated to a **stable Native Plugin architecture**, Zentra 0.15.2 offers a dedicated Web Interface (Chat + Config) and complete Internationalization. Powered by **LiteLLM**, it supports Ollama, KoboldCpp, and major cloud providers with real-time streaming and local TTS.

---

## ✨ Key Features (v0.15.2)
* 🤖 **Autonomous Agentic Loop** — Zentra can now reason step-by-step (Chain of Thought), dynamically select tools, and solve complex multi-step problems autonomously.
* 🛡️ **Zentra Code Jail (AST Sandbox)** — A native, highly secure Python sandbox that allows the AI to execute algorithms, math, and data logic safely.
* 👁️ **Native Vision Support** — Multimodal AI capabilities for Gemini, OpenAI, and Ollama (LLaVA). Analyze images, photos, and screenshots directly in chat.
* 🏗️ **Native WebUI Plugin** — Migrated from a bridge to a core plugin (`plugins/web_ui/`) for maximum performance and stability.
* 🔒 **Professional Zentra PKI (HTTPS)** — Zentra now acts as its own **Certificate Authority (Root CA)**. It automatically generates and signs host-specific certificates, enabling a full "Green Lock" experience on all devices. This unlocks browser-restricted features like Microphone and Camera across your LAN.
* 📱 **Mobile-First Responsive UI** — A completely redesigned mobile interface featuring an off-canvas hamburger menu, swipeable configuration tabs, and an optimized "Neural Link" for seamless media access on iOS and Android.
* ⚙️ **YAML Configuration** — Clean, validated `system.yaml`, `audio.yaml` powered by Pydantic v2 schemas.
* 📊 **Token Payload Inspector** — Live transparency on context window usage per-plugin via the WebUI Dashboard.
* 🖥️ **Native Multi-OS Support** — Deep OS-agnostic architecture via `OSAdapter` (Fully supports Windows, Linux, and MacOS).
* 🌐 **Global I18N (Multilingual)** — Complete support for English (default) and Italian across Terminal and WebUI with real-time switching.
* 🧠 **Multi-Cloud Streaming** — Native support for Groq, OpenAI, Gemini, and Anthropic with real-time "typewriter" effect.
* 🔄 **Live-Sync Config** — Change any setting in the Web Panel and see it applied instantly to the core without restarts.
* 🎭 **Dynamic Personality Discovery** — Personalities added to the `personality/` folder are automatically detected and synced with `config.yaml`.
* 🎙️ **Integrated Voice Chat** — Native Chat UI with Piper TTS integration and automatic audio playback.
* 🔌 **Plugin Macro Buttons** — Sidebar plugin list now features clickable macros to inject specialized commands instantly.
* 💾 **Persistent Memory** — SQLite-based long-term memory with shared context across WebUI and Terminal.
* 🗂️ **Zentra Drive (File Manager)** — Native HTTP file manager integrated into the WebUI to upload, download, and organize your system files through a seamless dual-panel interface.
* 🚀 **Professional English Launchers** — All startup scripts (`.bat` and `.sh`) are now fully internationalized in English, providing clear instructions for Windows and Linux users alike.

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

## ⚡ Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/Zentra-Core/zentra-core.github.io.git
cd zentra-core.github.io
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Zentra:
```bash
python main.py
```
2. Open your browser and navigate to the local HTTPS/HTTP port highlighted in the console (usually `https://127.0.0.1:7070`).

### 🔐 First Login & Authentication
Zentra v0.15.2 introduced mandatory Auth. On your very first access, the system generates a default Master Admin:
- **Username:** `admin`
- **Password:** `zentra`

We strongly recommend changing the password immediately from the **Users Tab** inside the Configuration Panel.

**Password Recovery:**
If you get locked out, run `python scripts/reset_admin.py` from the terminal to force a new password, or manually delete the `memory/users.db` file to reset the system defaults.

---

## 🧠 Supported AI Backends

### 🔹 Ollama
Easy to use, fast and optimized. Recommended for most users.

👉 https://ollama.com

### 🔹 KoboldCpp
Supports GGUF models, can run uncensored models, more flexible.

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

## 📚 Technical Documentation
Detailed technical guides for developers and advanced users:
- 🏗️ **[Technical Architecture Guide](docs/TECHNICAL_GUIDE.md)**: Deep dive into the OOP structure, data flow, and core engines.
- 🔌 **[Plugin Development Guide](docs/PLUGINS_DEV.md)**: How to create and register new tools using Native Function Calling.
- 📁 **[Project Structure Map](docs/ARCHITECTURE_MAP.md)**: Complete file-by-file breakdown of the repository.

---

## 💡 Vision
Zentra Core aims to become a fully autonomous, local AI assistant platform — a private, extensible alternative to cloud-based AI systems.
