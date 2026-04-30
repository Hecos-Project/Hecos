# 📁 3. Core Modules

Hecos is divided into distinct logical packages:

- `hecos.core.agent`: Manages the reasoning cycle and interaction with LiteLLM.
- `hecos.core.config`: Handles loading and validation of YAML files (Pydantic v2).
- `hecos.core.memory`: SQLite database and persistence architecture management.
- `hecos.core.security`: PKI engine for HTTPS and AST Sandbox for secure code execution.
- `hecos.plugins`: Root directory for all system extensions and capabilities.
