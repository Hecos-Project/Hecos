# Plugin System

Hecos features a dynamic and modular plugin architecture. Every capability is a standalone module that can be enabled or disabled.

## Core Plugins

| Plugin | Description |
|--------|-------------|
| **System** | Execute shell commands, manage processes, and control OS tasks. |
| **Web** | Search the web, open URLs, and automate browser interactions. |
| **File Manager** | Explore and manage local files and directories. |
| **Media** | Control system volume, playback, and audio settings. |
| **Dashboard** | Real-time hardware monitoring (CPU, RAM, GPU usage). |
| **Memory** | Persistent storage of conversations, user preferences, and context. |

## Creating Plugins
Developers can extend Hecos by adding new folders to the `plugins/` directory. Each plugin must follow the standard structure with a `main.py` entry point and register its capabilities with the core.
