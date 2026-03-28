# Zentra Core - Architecture Map
**Version:** 0.9.7 (Stable English Standard)

A visual guide to the Zentra Core folder structure and system components.

```text
Zentra-Core/
│
├── app/                  # Application runtime environment
│   ├── application.py    # Main boot sequence and event loop
│   ├── config.py         # Global configuration manager & I18N loader
│   ├── diagnostica.py    # Hardware and system health checks
│   ├── input_handler.py  # User keyboard and microphone unified input
│   ├── model_manager.py  # Global AI model state management
│   ├── state_manager.py  # Tracks internal status (Thinking, Speaking, Ready)
│   └── threads.py        # Background asynchronous workers (e.g. listening)
│
├── core/                 # Low-level core engines
│   ├── audio/            # TTS (Piper) and STT voice systems
│   ├── i18n/             # Internationalization dictionaries (JSON locales)
│   ├── llm/              # Unified AI backends (Ollama, Kobold, Cloud clients)
│   ├── processing/       # Token streaming and text output filters
│   └── system/           # Core bootstrap, versioning, and plugin loading
│
├── docs/                 # Operational manuals and technical documentation
│   ├── OPERATING_MANUAL.md
│   ├── ARCHITECTURE_MAP.md
│   ├── installation_guide.md
│   └── PLUGINS_DEV.md
│
├── logs/                 # Active system runtime and technical logs
│
├── memory/           # Brain Interface & Long-term storage
│   ├── chat_history.db   # SQLite database for long-term episodic memory
│   ├── core_identity.json # AI identity and personality traits
│   └── user_profile.json  # User profile and biographical notes
│
├── personality/          # Text injects for AI persona and system prompts
│
├── plugins/              # Modular root capabilities and tools
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
* **`app/`**: Regulates the main loop. Manages the transition between thinking, speaking, and listening states.
* **`core/`**: Provides the functional foundation (LLM connections, audio engine, translation layer).
* **`plugins/`**: Purely dynamic. Every subfolder acts as an independent tool the AI can use via Function Calling or legacy tags.
* **`memory/`**: Centralized vault for everything the AI "knows" and "remembers" about itself and the user.
* **`ui/`**: Responsible for rendering the TUI and handling interactive console menus.
