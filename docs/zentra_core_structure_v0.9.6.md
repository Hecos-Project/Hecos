# Zentra Core Architecture Map - v0.9.5

## Project Root Overview
Detailed mapping of the project's folder and file structure following the OOP and Internationalization migration.

- **main.py**: The primary entry point. Launches the application and handles lifecycle events.
- **monitor.py**: Background watchdog that monitors processes and ensures automatic restart in case of failure.
- **config.json**: Central configuration file (JSON) containing all system, model, and plugin settings.
- **config_tool.py**: Standalone editor for manual configuration via command line.
- **version_tool.py**: Quick utility to display the current system version and build info.
- **zentra_webui_bridge.py**: The API and streaming bridge that allows integration with Open WebUI and other external frontends.
- **ZENTRA_Run_Nvidia.bat**: Specialized startup script optimized for systems with Nvidia GPUs.
- **requirements.txt**: List of all Python dependencies required for the project.
- **LICENSE**: Legal license (AGPL v3).
- **README_ITA.md**, **README_ESP.md**, **README.md**: Multilingual documentation for the repository.

---

## 📁 app/ - Application State & Bridge
*Handles the high-level application logic and communication between components using OOP patterns.*

- **application.py**: The main `ZentraApplication` class that initializes all subsystems.
- **config.py**: `ConfigManager` class – Centralized object for reading/writing settings.
- **state_manager.py**: `StateManager` – Thread-safe global state tracker (Active model, Voice ON/OFF, etc.).
- **input_handler.py**: `InputHandler` – Processes keyboard (TUI) and voice input events.
- **threads.py**: Managed background threads for listening and UI updates.

---

## 📁 core/ - The "Central Nervous System"
*The core engine divided into specific domains of interest.*

### 📁 audio/ - Input/Output Management
- **ascolto.py**: Voice activity detection (VAD) and STT (Speech-to-Text) bridge.
- **voce.py**: Local text-to-speech engine powered by Piper (ONNX).

### 📁 i18n/ - Internationalization
- **locales/**: Dictionary files (JSON) for IT, EN, ES, etc.
- **translator.py**: Singleton manager for real-time translation and locale switching.

### 📁 llm/ - Artificial Intelligence Engines
- **brain.py**: Unified dispatcher that routes prompts to the correct backend.
- **client.py**: Standardized client for LiteLLM integration.
- **manager.py**: `LLMManager` – Dynamic model resolution for plugins and core features.

### 📁 logging/ - Tracking & Debugging
- **logger.py**: Multi-stream logger (Console, File, Activity, Technical Debug) with rotation support.

### 📁 processing/ - Data Transformation
- **filtri.py**: Text sanitization filters for video (TUI) and voice.
- **processore.py**: The core logic engine that parses AI responses and executes plugin actions.

### 📁 system/ - Utils & Boot
- **diagnostica.py**: Integrity checks and environment verification during startup.
- **plugin_loader.py**: Dynamic loader and registry for action modules.
- **version.py**: Version metadata control.

---

## 📁 ui/ - Interface & Dashboard
*Handles everything related to the user presentation layer.*

- **interface.py**: The main Terminal User Interface (TUI) – Dashboard, State bars, and Footer.
- **graphics.py**: Aesthetic utilities for generating bars, HUDs, and colored terminal outputs.
- **ui_updater.py**: Real-time non-blocking updater for hardware telemetry.
- **📁 config_editor/**: Dedicated GUI-like TUI for interactive configuration editing (F7).

---

## 📁 plugins/ - Action Modules (Extensions)
*Modular extensions that provide specific tools to the AI.*

- **dashboard**: Real-time hardware monitoring (CPU, RAM, GPU/VRAM).
- **file_manager**: Secure file system operations (read, list, copy).
- **media**: Control for volume, music, and system sounds.
- **roleplay**: Integration for advanced character-based scenarios and scenes.
- **system**: Direct shell instruction execution and program launching.
- **web**: Capability for internet searching and data retrieval.
- **memory**: Tools for long-term cognitive database access.

---

## 📁 memory/ - Cognition & Persistence
*Handles the long-term memory and identity of the system.*

- **archivio_chat.db**: SQLite database storing the full history and knowledge.
- **brain_interface.py**: The cognitive bridge between the LLM and the database.
- **identita_core.json**: JSON definition of Zentra's core identity.
- **profilo_utente.json**: Stored user preferences and interaction history.

---

## 📁 personality/ - AI "Soul" Profiles
*Plaintext files containing the high-level system prompts for different personas.*

- **Zentra.txt**: The standard helpful assistant personality.
- **Zentra_dark.txt**: A specialized nocturnal/dark mode persona.

---

## 📁 docs/ - Web Documentation & Assets
*Source for the project's documentation site (GitHub Pages).*

- **index.html**: Main landing page.
- **features.html**: Detailed feature breakdown page.
- **Mappa...v0.9.5.txt**: (Old map - deprecated)
- **zentra_core_structure_v0.9.5.md**: This document.

---

## 📁 logs/ - Session Logs
- Rotating text files for technical and activity logs.
