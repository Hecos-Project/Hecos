# Zentra Core v0.9.6 - Architecture Map

A visual guide to the Zentra Core folder structure and system components.

```text
Zentra-Core/
│
├── app/                  # Application runtime environment
│   ├── application.py    # Main boot sequence and event loop
│   ├── input_handler.py  # User keyboard and microphone unified input
│   ├── model_manager.py  # Global AI model state management
│   ├── state_manager.py  # Tracks internal status (Thinking, Speaking, Ready)
│   └── threads.py        # Background asynchronous workers (e.g. listening)
│
├── core/                 # Low-level core engines
│   ├── audio/            # TTS (Piper) and STT voice systems
│   ├── i18n/             # Internationalization dictionaries (IT/EN)
│   ├── llm/              # Unified AI backends (Ollama, Kobold, Cloud clients)
│   ├── processing/       # Token streaming and text output filters
│   └── system/           # Core bootstrap, versioning, and diagnostics
│
├── docs/                 # Operational manuals and technical documentation
│   ├── MANUALE_OPERATIVO.md
│   └── zentra_core_structure.md
│
├── logs/                 # Active system runtime and technical logs
│
├── memory/               # Persistent AI storage
│   ├── caveau/           # Database environment for long-term memories
│   └── history/          # Short-term active conversation histories
│
├── personality/          # Text injects for AI persona and system prompts
│   ├── default.txt
│   └── (custom_souls).txt
│
├── plugins/              # Modular root capabilities and tools
│   ├── dashboard/        # Background hardware monitoring telemetry
│   ├── media/            # Audio output controls
│   ├── system_admin/     # OS root access (shell access, file manager)
│   ├── web_search/       # Internet browsing and API queries
│   └── webcam/           # PC optical sensor interface
│
├── ui/                   # Visual output and menus
│   ├── config_editor/    # F7 Interactive Configuration Panel (Inquirer)
│   ├── interface.py      # ANSI Scrolling Region rendering
│   └── ui_updater.py     # Background dashboard GUI synchronizer
│
├── zentra_bridge/        # Tools for bridging the terminal to WebUI
│
├── .env                  # Environment Variables (API Keys, etc.)
├── config.json           # Master Global Configuration File
├── main.py               # Executable Point of Entry
└── monitor.py            # Watchdog Daemon for auto-reloading configuration
```

### Component Overview
* **`app/`** regulates the loop. If it crashes, the application dies.
* **`core/`** provides the heavy lifting (LLM connections, audio engine).
* **`plugins/`** is purely dynamic. Every subfolder acts as an independent tool the AI can physically use. Removing a plugin does not crash the system.
* **`ui/`** is exclusively drawing pixels and catching terminal keystrokes.
