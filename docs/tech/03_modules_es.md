# 📁 3. Módulos Core

Hecos se divide en distintos paquetes lógicos:

- `hecos.core.agent`: Gestiona el ciclo de razonamiento y la interacción con LiteLLM.
- `hecos.core.config`: Maneja la carga y validación de archivos YAML (Pydantic v2).
- `hecos.core.memory`: Base de datos SQLite y gestión de la persistencia de la arquitectura.
- `hecos.core.security`: Motor PKI para HTTPS y Sandbox AST para la ejecución segura de código.
- `hecos.plugins`: Directorio raíz para todas las extensiones y capacidades del sistema.
