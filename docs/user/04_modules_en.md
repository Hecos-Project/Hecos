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

---

### 🎭 The Soul of the Machine: Native Personas

A fundamental capability of the modular system is its native **Personality Switching**. Hecos isn't just a rigid assistant — it adapts its behavior, tone, and character based on the persona you load. Each persona is programmed to fulfill a unique role in your daily life.

<p align="center">
  <img src="https://raw.githubusercontent.com/Hecos-Project/hecos/main/hecos/assets/Urania_9800_Logo.png" width="400">
  <br>
  <em>Urania 9800, the official Hecos Mascot and your everyday friendly companion.</em>
</p>

Out of the box, Hecos includes several pre-configured personalities:
* **Hecos System Soul** — The neutral, rigid, and detached core system. Perfect for raw automation and precise tasks.
* **Urania 9800** — The lively mascot. A true, everyday friend designed for casual, empathetic, and cheerful interaction.
* **Sebastian Pro** — The perfect, highly professional butler. Polite, efficient, and eager to serve.
* **Atlas** — The imposing, authoritative digital guardian.
* **Nova X-01** — A precise, analytical robotic entity for those who prefer purely logical interactions.

You can hot-swap these personas at any time, changing not just the voice and tone, but the very "soul" of the system.
