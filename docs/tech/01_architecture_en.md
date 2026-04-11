# 🏗️ 1. System Architecture

Zentra Core is designed with a modular and scalable architecture, based on object-oriented programming (OOP) principles.

- **Core Engine**: The heart of the system that manages plugin orchestration, configuration loading, and the Agent's reasoning cycle.
- **Plugin System**: A dynamic infrastructure that allows the extension of AI capabilities without modifying the central core.
- **OS Adapter**: An abstraction layer that guarantees cross-platform compatibility (Windows, Linux, macOS).
- **WebUI Backend**: An integrated Flask server that exposes REST APIs for the graphical interface.
