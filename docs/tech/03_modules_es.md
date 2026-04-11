# 📁 3. Módulos Core

Zentra Core se divide en distintos paquetes lógicos:

- `zentra.core.agent`: Gestiona el ciclo de razonamiento y la interacción con LiteLLM.
- `zentra.core.config`: Maneja la carga y validación de archivos YAML (Pydantic v2).
- `zentra.core.memory`: Base de datos SQLite y gestión de la persistencia de la arquitectura.
- `zentra.core.security`: Motor PKI para HTTPS y Sandbox AST para la ejecución segura de código.
- `zentra.plugins`: Directorio raíz para todas las extensiones y capacidades del sistema.
