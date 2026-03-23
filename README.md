# 🌌 Zentra Core Project
<p align="center">
  <img src="https://raw.githubusercontent.com/Zentra-Core/zentra-core.github.io/main/assets/Zentra_Core_Logo.jpg" width="400" alt="Zentra Logo">
</p>

# Zentra Core - Version 0.9.4 (In Development)
Language: [English](README.md) | [Italiano](README_ITA.md) | [Español](README_ESP.md)

# 🤖 Zentra Core

**Your Personal Offline AI Assistant (Private, Modular, Powerful)**

---

## 🚀 Overview

**Zentra Core** is a local-first AI assistant platform that runs entirely on your machine.

It combines local LLMs, voice interaction, system automation, and a modular plugin architecture to create a fully customizable AI companion.

Unlike cloud-based assistants, Zentra gives you full control:

* No data collection
* No external dependencies (optional)
* No restrictions on behavior (depending on models used)

---

## ✨ Key Features

* 🧠 **Local AI Processing** — Runs entirely on your hardware
* 🔄 **Dual Backend Support** — Compatible with Ollama and KoboldCpp
* 🎙️ **Voice Interaction** — Speech input and output (TTS/STT)
* ⚙️ **System Control** — Execute commands, open apps, manage files
* 🔌 **Plugin System** — Easily extend functionality
* 💾 **Persistent Memory** — SQLite-based long-term memory
* 🌐 **Web Interaction** — Open websites and perform searches
* 🖥️ **Hardware Monitoring** — CPU, RAM, GPU stats
* 🔗 **Integration Ready** — Works with Open WebUI and Home Assistant

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
git clone [https://github.com/Zentra-Core/zentra-core.github.io.git](https://github.com/Zentra-Core/zentra-core.github.io.git)
cd zentra-core.github.io
