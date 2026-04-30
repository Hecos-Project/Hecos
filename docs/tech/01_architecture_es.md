# 🏗️ 1. Arquitectura de Sistema

Hecos está diseñado con una arquitectura modular y escalable, basada en principios de programación orientada a objetos (OOP).

- **Core Engine**: El corazón del sistema que gestiona la orquestación de plugins, la carga de configuraciones y el ciclo de razonamiento del Agente.
- **Plugin System**: Una infraestructura dinámica que permite la extensión de las capacidades de IA sin modificar el núcleo central.
- **OS Adapter**: Una capa de abstracción que garantiza la compatibilidad multiplataforma (Windows, Linux, macOS).
- **WebUI Backend**: Un servidor Flask integrado que expone APIs REST para la interfaz gráfica.
