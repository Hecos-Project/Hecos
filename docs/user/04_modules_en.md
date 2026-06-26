# 🔌 4. Modular System / Modules

Hecos is built on a **Module-Native** architecture. Every capability (file management, hardware, multimedia) is handled by an independent module.

- **Flexibility**: Modules can be enabled or disabled in real-time via the Config Panel.
- **Integrity**: Each module operates in its own isolated space, ensuring that an error doesn't crash the entire system.
- **Discovery**: New modules and packages added to the system are automatically detected.

### WebUI Management
In the WebUI sidebar, you can see the list of active modules with their respective macro buttons to send quick commands to the AI.

### Core Modules & Capabilities
Hecos natively includes several powerful modules:
- **Integrated Calendar**: A full calendar module with holiday tracking and event visualization right in the WebUI.
- **Reminder & Scheduler**: An advanced task scheduler with NLP interpretation ("remind me in 10 minutes") and active OS notifications.
- **Media Player Engine**: A robust multimedia system (VLC 64-bit + FFplay fallback) supporting resilient state management, pause/resume, and volume control.
- **Browser Automation**: A module to semantically interact with and navigate web pages.
- **OS Automation**: A module to automate operating system tasks through programmatic mouse and keyboard control.

### Module Types
Hecos supports an 8-layer architecture where everything is defined as a module:
- **Core Modules**: Built-in, non-removable OS and system functions.
- **Plugins**: Reactive tools and capabilities called by the AI.
- **Apps**: Autonomous mini-applications with their own standalone UI and lifecycle.
- **Widgets**: Interactive frontend components for the Control Room dashboard.
- **Personas**: Installable AI personalities and behavioral profiles.
- **Themes**: Custom CSS and styling packages to customize the UI.
- **Skill Packs**: Additional slash-command packs for the chat interface.
- **MCP Servers**: Universal external tool bridges via the Model Context Protocol.

### 📦 Hecos Package Manager (HPM)
Starting with version 0.35.0, Hecos introduces the **Hecos Package Manager**, a centralized system that makes the platform potentially universal.
- **Standalone Packages (`.hpkg`)**: You can install new core modules, plugins, extensions, widgets, and personas simply by dragging and dropping `.hpkg` bundles into the Package Manager inside the WebUI.
- **Advanced Security**: All third-party packages are verified using cryptographic digital signatures (Ed25519) to ensure absolute code integrity.
- **Isolation**: Modules maintain their own isolated logic and configuration autonomously, preventing conflicts with the Core System.
