# Zentra Core v0.9.7 - Architecture Map

A visual guide to the Zentra Core folder structure and system components as of version 0.9.7.

```text
Zentra-Core/
│
├── app/                  # Application runtime environment
│   ├── application.py    # Main boot sequence and event loop
│   ├── input_handler.py  # User keyboard and microphone unified input
│   ├── model_manager.py  # Global AI model state management (F2/F7 logic)
│   ├── state_manager.py  # Tracks internal status (Thinking, Speaking, Ready)
│   └── threads.py        # Background asynchronous workers (e.g. listening)
│
├── core/                 # Low-level core engines
│   ├── audio/            # TTS (Piper) and STT voice systems
│   ├── i18n/             # Internationalization dictionaries (IT/EN/ES)
│   ├── llm/              # Unified AI backends (Ollama, Kobold, Cloud clients)
│   │   └── vision/       # Multimodal adapters (Gemini, OpenAI, LLaVA)
│   ├── processing/       # Token streaming and text output filters
│   └── system/           # Core bootstrap, versioning, and diagnostics
│
├── docs/                 # Operational manuals and technical documentation
│   ├── OPERATING_MANUAL.md
│   ├── TECHNICAL_GUIDE.md
│   └── zentra_core_structure_v0.9.7.md
│
├── logs/                 # Active system runtime and technical logs
│
├── memory/               # Persistent AI storage
│   ├── caveau/           # Database environment for long-term memories
│   └── history/          # Short-term active conversation histories
│
├── personality/          # Text injects for AI persona and system prompts
│
├── plugins/              # NEW Modular Plugin System (v0.9.7)
│   ├── dashboard/        # Hardware telemetry HUD
│   ├── domotica/         # IoT and home automation control
│   ├── executor/         # Shell command execution engine
│   ├── file_manager/     # OS file system operations
│   ├── help/             # Integrated documentation assistant
│   ├── media/            # Audio/Video playback control
│   ├── memory/           # Manual memory injection tools
│   ├── models/           # Real-time model switching macros
│   ├── roleplay/         # Advanced persona and context injectors
│   ├── system/           # Core OS management (reboot, shutdown)
│   ├── web/              # Internet search and browsing
│   ├── web_ui/           # Native Web Interface (Vue/Vanilla JS)
│   ├── webcam/           # Vision sensor integration
│   └── plugins_disabled/ # Sandbox for inactive modules
│
├── ui/                   # Legacy TUI components
│   ├── config_editor/    # F7 Interactive Configuration Panel
│   └── interface.py      # ANSI Scrolling Region rendering
│
├── .env                  # Environment Variables (API Keys, etc.)
├── config.json           # Master Global Configuration File
├── main.py               # Executable Point of Entry
└── monitor.py            # Watchdog Daemon for auto-reloading configuration
```

### Component Overview
* **`app/`** regulates the loop. If it crashes, the application dies.
* **`core/llm/vision/`** (New in v0.9.7) handles the translation of images to provider-specific multimodal payloads.
* **`plugins/`** is the modular heart. v0.9.7 features 15 distinct functional modules. `web_ui` is now a fully integrated native plugin.
* **`ui/`** handles terminal rendering, while `plugins/web_ui` handles the browser-based interaction.
