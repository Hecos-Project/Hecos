# Hecos - GitHub Wiki Template

This document provides a template for the GitHub Wiki, synchronized with the internal documentation system.

## 📖 User Guide (Manuale Operativo)
Access the latest version of the Operating Manual for day-to-day usage.

### Core Features
- **Neural Cognitive Engine**: Powered by local LLMs (Ollama/Kobold) or Cloud APIs.
- **Voice Interaction**: Piper TTS and continuous listening support.
- **Web UI**: Modern dashboard for chat and system configuration.

### Common Commands
- "Show me system stats"
- "Search the web for..."
- "Open Notepad"

---

## 💻 Tech Guide (Architectural Overview)
*Note: This section contains sensitive details about the internal pipeline and security.*

### System Architecture
Hecos follows a modular "Black Box" architecture. Plugins are loaded dynamically from the `plugins/` directory.

### Execution Pipeline
1. **Input Handling**: Audio/Text capture.
2. **Cognitive Loop**: Intent recognition and Tool use (Tags/JSON).
3. **Action Execution**: Subprocess/API calls.
4. **Response Generation**: Text and Speech synthesis.

---

## 🛠 Developer Resources
- **Plugin Development**: See `docs/TECHNICAL_GUIDE.md` for API reference.
- **I18n**: Localization files found in `hecos/core/i18n/locales/`.
- **UI Styling**: Vanilla CSS components in `hecos/plugins/web_ui/static/css/`.

> [!TIP]
> Always use the latest version from the main branch for the most stable experience.
