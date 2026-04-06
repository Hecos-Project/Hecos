## 1. System Architecture (v0.12.0)
Zentra Core is built on a **Modular Object-Oriented Architecture** designed for high performance, local first-AI, and extensibility.

### Design Principles:
- **Singleton Pattern**: Core managers (Config, State, I18n) are singletons to ensure consistent state across threads.
- **Asynchronous Execution**: Heavy tasks (STT, LLM inference, TTS) run in dedicated background threads to keep the UI responsive.
- **Backend Agnostic**: The system routes requests through a unified client (`client.py`) supporting Ollama, KoboldCPP, and various cloud providers via LiteLLM.
- **Multimodal Ready**: Version 0.9.9 introduces native vision support via provider-specific adapters.
- **Runtime Alpha Status**: The project is currently in an early development phase. This means the system is subject to frequent changes, debugging, and is not yet considered a stable "production-ready" release.
- **Single-Instance Protection**: To prevent data corruption and resource conflicts, Zentra uses a file-based locking mechanism (`core/system/instance_lock.py`) to ensure only one instance of the core and web interface runs at a time.
- **Centralized Configuration**: Version 0.12.0 abandons legacy JSON for a robust **Pydantic v2 + YAML** ConfigManager (`config/system.yaml`), ensuring strong schema validation natively.
- **OS Agnostic Architecture**: Version 0.11.0 abstracts all operating system dependent workflows via the new `OSAdapter` (`core/system/os_adapter.py`).
- **Mandatory HTTPS & Auth Security**: Version 0.12.0 implements standard Flask-Login authentication over AES sessions and SQLite SQLite PBKDF2 hashing (`core/auth/auth_manager.py`). The Native UI is completely locked from unauthorized accesses.
- **Extension Architecture & Lazy Loading (JIT)**: Plugins can encapsulate complex feature sets (e.g., Code Editors) into `extensions/`. These are lazy-loaded dynamically via `core/system/extension_loader.py` ONLY when accessed, zeroing their RAM/CPU footprint during normal startup operations.

---

## 2. The Execution Pipeline (Data Flow)
1. **Input Stage**: `InputHandler` captures text (keyboard) or processes audio via `listening.py` (STT).
2. **Context Enrichment**: `personality_manager.py` ensures the configuration is synced with the filesystem. `brain.py` then gathers system prompts and retrieves relevant history from `memory/`.
3. **Vision Processing** (v0.9.9): If images are attached, `client.py` selects the correct **VisionAdapter** (Gemini, OpenAI, or Ollama) to build the multimodal payload.
4. **WebRTC Asynchronous Audio Ingestion**: Mobile PTT dictation is recorded client-side via `MediaRecorder` and posted to `/api/audio/transcribe` via `FormData`. The server converts these WebM/OGG blobs to 16kHz WAV locally using `pydub` before piping them into the Google STT engine.
5. **Model Resolution**: `LLMManager` determines the best model based on the active backend and specific plugin requirements.
6. **Inference**: `LiteLLM` unifies the request and calls the local/cloud provider.
7. **Agentic Loop**: The `AgentExecutor` takes control off the prompt. It parses responses for **Tool Calls**, executes plugins (like the `executor` AST python jail), and feeds results back to the LLM in a multi-step "Chain of Thought" loop.
8. **Streaming Traces**: While reasoning, the agent streams live `agent_trace` UI updates (thought bubbles) back to the browser via Server-Sent Events (SSE).
9. **Output Stage**: Final text is sanitized by `filtri.py` and sent to the TUI (`interface.py`) and/or the TTS engine (`voice.py`). Auto-play blocks on mobile are bypassed by pre-blessing a global HTML5 Audio proxy channel upon user interaction.
10. **Web Notification & Sync**: Native WebUI (`plugins/web_ui/`) receives the stream via a unified event bus and updates the browser chat. Global configuration changes are synchronized instantly across all interfaces.

---

## 3. Core Module Reference

### 📁 app/ (Application Layer)
- **`application.py`**: The main orchestrator. Initializes the engine and handles the main TUI loop.
- **`config.py` (`ConfigManager`)**: Handles thread-safe atomic reading and writing of YAML configuration files using Pydantic Validation schemas in `/config/schemas`.
- **`state_manager.py`**: A synchronized object for sharing runtime variables (e.g., `model_active`, `is_listening`).
- **`model_manager.py`**: Handles dynamic model fetching from APIs (Ollama/Groq/OpenAI) and user selection (F2).

### 📁 core/ (Engine Layer)
- **`llm/brain.py`**: The "Router". It builds the complex system prompt and chooses the backend.
- **`llm/manager.py` (`LLMManager`)**: **Automatic Routing Logic.** If a plugin needs a specific model (e.g., a faster one for simple checks), this module manages the fallback and selection.
- **`processing/processore.py`**: The logic dispatcher. It handles both Native Function Calling (JSON) and Legacy Tagging (`[MODULE: CMD]`).
- **`i18n/`**: Centralized internationalization system. Supports English (EN), Italian (IT), and Spanish (ES) with a singleton `translator.py` that manages real-time localization for the entire system (Console + WebUI).
- **`system/instance_lock.py`**: Handles PID-based process locking to maintain a single active instance.

---

## 4. Key Infrastructure Features

### LLM Dynamic Routing
Zentra Core features a built-in routing system. Instead of hardcoding models, plugins can request a "capability tag". The `LLMManager` looks up the best match in `system.yaml` under the `plugins` section or uses the global default backend. This prevents code repetition when switching models.

### Zentra PKI (Native HTTPS)
Version 0.12.0 introduces a built-in Certificate Authority. The `core/security/pki` module handles CA generation and host certificate signing. This infrastructure is vital for bypassing browser security restrictions on remote devices, enabling secure access to the Microphone and Camera APIs across the network.

### Mobile-First UI & Autoplay Bypass
The WebUI implements a responsive grid and an off-canvas navigation pattern. 
- **Swipeable Tabs**: Config tabs use touch-scrolling.
- **Neural Link & AudioContext Blessing**: Mobile browsers mandate a synchronous user gesture to play audio. Zentra binds to the Chat Submit or WebRTC PTT Hold actions to play an empty wav file on a persistent, global `ZentraTTSPlayer`, preserving autoplay rights exclusively for the asynchronous server TTS response seconds later.

### Cross-Drive Absolute Path Security
The Drive plugin enables full bare-metal filesystem traversal bypassing relative symlink jails via absolute path resolving. The custom `_safe_path` function validates against path traversal exploits (e.g., `../`) using `os.path.abspath(os.path.join(base, requested))` ensuring the requested URI physically resides within the chosen volume root (`C:\` vs `D:\`).

---

## 5. Developer Best Practices
- **Always use `logger`**: Direct `print` is discouraged; use `core.logging.logger` to ensure logs are captured in Activity/Technical windows.
- **Synchronous vs Asynchronous**: Ensure that UI calls from background threads use the provided locks to prevent race conditions.
- **Config Persistence**: When updating settings, use `config_manager.set(...)` and `save()` to ensure consistency.

---

*This guide is maintained by the Zentra Core Team. For plugin-specific development, refer to `PLUGINS_DEV.md`.*
