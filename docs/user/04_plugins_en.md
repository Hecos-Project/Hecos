# 🔌 4. Modular System / Plugins

Hecos is built on a **Plugin-Native** architecture. Every capability (file management, hardware, multimedia) is handled by an independent module.

- **Flexibility**: Plugins can be enabled or disabled in real-time via the Config Panel.
- **Integrity**: Each plugin operates in its own isolated space, ensuring that an error in one module doesn't crash the entire system.
- **Discovery**: New plugins added to the `plugins/` folder are automatically detected at startup.

### WebUI Management
In the WebUI sidebar, you can see the list of active plugins with their respective macro buttons to send quick commands to the AI.

### Core Plugins & Capabilities
Hecos includes several powerful plugins natively:
- **Integrated Calendar**: A full calendar module with holiday tracking and event visualization right in the WebUI.
- **Reminder & Scheduler**: An advanced task scheduler with NLP interpretation ("remind me in 10 minutes") and active OS notifications.
- **Media Player Engine**: A robust multimedia system (VLC 64-bit + FFplay fallback) supporting resilient state management, pause/resume, and volume control.
