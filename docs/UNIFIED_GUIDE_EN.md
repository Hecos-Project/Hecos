# 🌌 Zentra Core - Unified Guide (v0.17.0)
Welcome to the official Zentra Core guide. This document summarizes everything you need to know to install, configure, and use your private, offline AI assistant.

---

## 🚀 1. Introduction
Zentra Core is a local-first AI platform designed for privacy and modularity. It runs entirely on your hardware, allowing you to interact with large language models (LLMs), automate your system, and manage your data without cloud dependency.

## 📥 2. Quick Installation
To start from scratch:
1. **Python**: Install Python 3.11 or higher.
2. **Ollama**: Download Ollama and pull a model (e.g., `ollama pull gemma2`).
3. **Setup**:
   ```bash
   pip install -r requirements.txt
   python scripts/setup_pki.py  # Enables HTTPS and browser microphone
   ```
4. **Launch**: Run `python main.py`.

## 🔐 3. First Login
Zentra requires mandatory authentication to protect your data:
- **Default Username**: `admin`
- **Default Password**: `zentra`
*It is highly recommended to change the password from the Configuration Panel.*

---

### ⚡ Direct Commands (AI Bypass)
To perform fast actions or bypass LLM safety filters for images:
- `/img [prompt]`: Triggers direct image generation via provider (Hugging Face, Pollinations, etc.).

---

## ✨ 4. Key Features (v0.17.0)

### 🔌 MCP Bridge & Discovery (Universal Tool Hub)
The Model Context Protocol (MCP) allows Zentra to use external tools.
- **Multi-Registry Support**: Search and install tools from **Smithery.ai**, **MCPSkills**, **GitHub**, and **Hugging Face**.
- **Dashboard**: Manage your MCP servers in real-time.

### 👥 Multi-User & Vaults
Every user has their own identity, memory, and avatar.
- **Isolated Vaults**: Files and memories are stored in `memory/vaults/username`.
- **Bio Notes**: The AI learns about you and saves important details privately.

### 🛡️ Zentra Code Jail
The AI can write and execute Python code in a secure sandbox (AST) for complex calculations or data manipulation.

### 🔒 Professional PKI (HTTPS)
Zentra generates its own SSL certificates to enable the "Green Lock" on your LAN, unlocking Microphone and Camera usage in the browser.

---

## 📱 5. Mobile Interface
Zentra's interface is fully responsive. You can use it from your smartphone like a native Web App, with off-canvas menus and quick access to "Neural Links".

## 📚 6. Useful Links
- **Chat**: `http://localhost:7070/chat`
- **Configuration**: `http://localhost:7070/zentra/config/ui`
- **File Manager (Drive)**: `http://localhost:7070/drive`
- **Official Wiki**: [GitHub Wiki](https://github.com/Zentra-Core/zentra-core.github.io/wiki)

---
*Zentra Core is in Runtime Alpha stage (v0.17.0). Use responsibly.*
