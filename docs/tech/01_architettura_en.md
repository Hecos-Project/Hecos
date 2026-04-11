# 🏗️ 1. System Architecture

Zentra Core is built on a **Modular Object-Oriented Architecture**.
- **Singleton Pattern**: Core managers (Config, State, I18n) keep consistent state.
- **Asynchronous Execution**: Background threads for heavy tasks (LLM, STT, TTS).
- **Lazy Loading**: Dynamic extension loading via `extensions/`.
