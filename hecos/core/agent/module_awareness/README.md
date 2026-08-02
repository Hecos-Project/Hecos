# Module Awareness

This package gives Hecos self-awareness of its module ecosystem.

## Features
- **Introspection**: Knows exactly what modules are installed, their status, and versions.
- **Store Awareness**: Reads from all configured HPM stores to know what's available.
- **Web Search**: Can search the internet for Hecos modules using `browser_automation` or built-in HTTP fallback.
- **Readme Parsing**: Downloads and reads the `README.md` of packages to understand their features and usage.
- **Auto-Installation**: Can autonomously propose and install modules from the store (respecting trust policies).

## Architecture
This plugin exposes AI tools (`MODULE_AWARENESS__*`) that the Brain can use to reason about the system's capabilities and expand them on the fly.
