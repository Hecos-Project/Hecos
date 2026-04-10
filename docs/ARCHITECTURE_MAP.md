# Zentra Core v0.15.2 - Architecture Map

A visual guide to the Zentra Core folder structure and system components as of version 0.15.2.

```text
Zentra-Core/
│
├── app/                  # Application runtime environment
│   ├── application.py    # Main boot sequence and event loop
│   ├── bootstrapper.py   # System initialization (Console & Web access info)
│   ├── config.py         # YAML ConfigManager (Pydantic v2 validation)
│   ├── input_handler.py  # User keyboard and microphone unified input
│   ├── model_manager.py  # Global AI model state management
│   ├── personality_manager.py # F3 Selection & Dynamic Sync logic
│   ├── state_manager.py  # Tracks internal status (Thinking, Speaking, Ready)
│   └── threads.py        # Background asynchronous workers
│
├── core/                 # Low-level core engines
│   ├── agent/            # Agentic Loop (Chain of Thought, SSE Traces)
│   ├── audio/            # TTS (Piper) and STT voice systems
│   ├── auth/             # AES Session & SQLite Auth Manager
│   ├── i18n/             # Internationalization (IT/EN/ES)
│   ├── llm/              # Unified AI backends (Ollama, Kobold, Cloud)
│   │   └── vision/       # Multimodal adapters
│   ├── processing/       # Token streaming and filters
│   ├── security/         # Zentra PKI (Root CA & Cert Management)
│   └── system/           # Bootstrap, versioning, and diagnostics
│
├── docs/                 # Operational manuals and technical documentation
│   ├── OPERATING_MANUAL.md
│   ├── TECHNICAL_GUIDE.md
│   └── ARCHITECTURE_MAP.md
│
├── logs/                 # Active system runtime and technical logs
│   ├── zentra.log        # Core logging output
│   └── webui_heartbeat.json # Frontend status tracking
│
├── memory/               # Persistent AI storage (SQLite)
│   ├── caveau/           # Long-term semantic memories
│   └── history/          # Conversation context
│
├── personality/          # AI Persona and Dynamic Prompts (.txt files)
│
├── plugins/              # Modular Plugin System
│   ├── dashboard/        # Hardware HUD
│   ├── domotica/         # IoT control
│   ├── drive/            # Zentra Drive (HTTP File Manager)
│   ├── executor/         # AST Code Sandbox (Zentra Code Jail)
│   ├── file_manager/     # OS file operations (AI tools)
│   ├── help/             # Documentation assistant
│   ├── image_gen/        # AI Image Generation
│   ├── media/            # Audio/Video playback
│   ├── memory/           # Memory tools
│   ├── models/           # Real-time model macros
│   ├── system/           # OS management
│   ├── web/              # Internet browsing
│   ├── web_ui/           # Native Web Interface (Chat + Config)
│   ├── webcam/           # Vision sensor
│   └── plugins_disabled/ # Inactive modules
│
├── config/               # Centralized YAML Configuration
│   ├── system.yaml       # Core system settings
│   └── audio.yaml        # Audio & Voice settings
│
├── .env                  # API Keys & Sensitive Data
├── main.py               # Application Entry Point
├── monitor.py            # Configuration Watchdog
└── zentra_proc_manager.py # Optional Process Manager
```

### Component Overview
* **`app/`**: Regulates the execution flow. Powered by a YAML-first configuration system for stability.
* **`core/`**: The engine room. Version 0.15.2 introduces native Auth systems, **Zentra PKI** for self-hosted HTTPS, and Agentic reasoning.
* **`plugins/`**: Modular heart. Now includes **Lazy Loading** for zero-boot impact, **Zentra Drive** for file management, and **Remote Client Camera** support for mobile devices.
* **`config/`**: Centralized repository for all system parameters, replacing old scattered JSONs.
* **`scripts/`**: Internationalized launchers (.bat/.sh) in standard English.
