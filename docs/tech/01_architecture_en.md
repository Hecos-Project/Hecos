# 🏗️ 1. System Architecture

Hecos is designed with a modular and scalable architecture, based on object-oriented programming (OOP) principles and an ecosystem of independent packages.

- **Core Engine**: The heart of the system that manages module orchestration, encrypted configuration loading, and the Agent's reasoning cycle via the LLM adapter.
- **Hecos Package Manager (HPM)**: The fundamental dynamic infrastructure that allows the system to expand. Through HPM, Hecos installs **Modules** (`.hpkg` packages signed with Ed25519 keys). A module can be:
  - **Plugins & Core Modules**: Native AI integrations (OS automation, image generation, etc).
  - **Autonomous Apps**: Full web applications running entirely locally within the ecosystem.
  - **Control Room Widgets**: Tools for the system dashboard and real-time telemetry.
  - **Personas & Themes**: Packages to customize the visual appearance and behavior of the agent.
- **OS Adapter**: An abstraction layer that guarantees cross-platform compatibility (Windows, Linux, macOS).
- **WebUI Backend**: An integrated Flask server that hosts the native interface, the Central Hub, and dynamically routes APIs and assets of HPM packages.
