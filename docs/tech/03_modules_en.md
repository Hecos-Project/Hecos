# 📁 3. Core Modules

Zentra Core is divided into distinct logical packages:

- `zentra.core.agent`: Manages the reasoning cycle and interaction with LiteLLM.
- `zentra.core.config`: Handles loading and validation of YAML files (Pydantic v2).
- `zentra.core.memory`: SQLite database and persistence architecture management.
- `zentra.core.security`: PKI engine for HTTPS and AST Sandbox for secure code execution.
- `zentra.plugins`: Root directory for all system extensions and capabilities.
