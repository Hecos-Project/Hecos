## 1. System Architecture (v0.9.7)
Zentra Core is built on a **Modular Object-Oriented Architecture** designed for high performance, local first-AI, and extensibility.

### Design Principles:
- **Singleton Pattern**: Core managers (Config, State, I18n) are singletons to ensure consistent state across threads.
- **Asynchronous Execution**: Heavy tasks (STT, LLM inference, TTS) run in dedicated background threads to keep the UI responsive.
- **Backend Agnostic**: The system routes requests through a unified client (`client.py`) supporting Ollama, KoboldCPP, and various cloud providers via LiteLLM.
- **Multimodal Ready**: Version 0.9.7 introduces native vision support via provider-specific adapters.

---

## 2. The Execution Pipeline (Data Flow)
1. **Input Stage**: `InputHandler` captures text (keyboard) or processes audio via `listening.py` (STT).
2. **Context Enrichment**: `brain.py` gathers system prompts, personality files, and retrieves relevant history from `memory/`.
3. **Vision Processing** (v0.9.7): If images are attached, `client.py` selects the correct **VisionAdapter** (Gemini, OpenAI, or Ollama) to build the multimodal payload.
4. **Model Resolution**: `LLMManager` determines the best model based on the active backend and specific plugin requirements.
5. **Inference**: `LiteLLM` unifies the request and calls the local/cloud provider.
6. **Post-Processing**: `Processor` parses the AI response for **Tool Calls** (Function Calling) or legacy tags.
7. **Action Stage**: If a tool is detected, the corresponding plugin in `plugins/` is executed.
8. **Output Stage**: Final text is sanitized by `filtri.py` and sent to the TUI (`interface.py`) and/or the TTS engine (`voice.py`).
9. **Web Notification**: Native WebUI (`plugins/web_ui/`) receives the stream and updates the browser chat in real-time.

---

## 3. Core Module Reference

### 📁 app/ (Application Layer)
- **`application.py`**: The main orchestrator. Initializes the engine and handles the main TUI loop.
- **`config.py` (`ConfigManager`)**: Handles thread-safe atomic reading and writing of `config.json`.
- **`state_manager.py`**: A synchronized object for sharing runtime variables (e.g., `model_active`, `is_listening`).
- **`model_manager.py`**: Handles dynamic model fetching from APIs (Ollama/Groq/OpenAI) and user selection (F2).

### 📁 core/ (Engine Layer)
- **`llm/brain.py`**: The "Router". It builds the complex system prompt and chooses the backend.
- **`llm/manager.py` (`LLMManager`)**: **Automatic Routing Logic.** If a plugin needs a specific model (e.g., a faster one for simple checks), this module manages the fallback and selection.
- **`processing/processore.py`**: The logic dispatcher. It handles both Native Function Calling (JSON) and Legacy Tagging (`[MODULE: CMD]`).
- **`i18n/translator.py`**: Singleton for real-time localization of the entire interface.

---

## 4. Key Infrastructure Features

### LLM Dynamic Routing
Zentra Core features a built-in routing system. Instead of hardcoding models, plugins can request a "capability tag". The `LLMManager` looks up the best match in `config.json` under the `plugins` section or uses the global default backend. This prevents code repetition when switching models.

### Hardware-Aware Dashboard
The `plugins/dashboard` module uses a background thread (`ui_updater.py`) to bypass the standard scroll buffer and write directly to the top of the terminal, providing a real-time HUD without flickering.

---

## 5. Developer Best Practices
- **Always use `logger`**: Direct `print` is discouraged; use `core.logging.logger` to ensure logs are captured in Activity/Technical windows.
- **Synchronous vs Asynchronous**: Ensure that UI calls from background threads use the provided locks to prevent race conditions.
- **Config Persistence**: When updating settings, use `config_manager.set(...)` and `save()` to ensure consistency.

---

*This guide is maintained by the Zentra Core Team. For plugin-specific development, refer to `PLUGINS_DEV.md`.*
