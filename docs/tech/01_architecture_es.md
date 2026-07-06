# 🏗️ 1. Arquitectura de Sistema

Hecos está diseñado con una arquitectura modular y escalable, basada en principios de programación orientada a objetos (OOP) y en un ecosistema de paquetes independientes.

- **Core Engine**: El corazón del sistema que gestiona la orquestación de módulos, la carga de configuraciones encriptadas y el ciclo de razonamiento del Agente a través del adaptador LLM.
- **Hecos Package Manager (HPM)**: La infraestructura dinámica fundamental que permite la expansión del sistema. A través de HPM, Hecos instala **Módulos** (paquetes `.hpkg` firmados con claves Ed25519). Un módulo puede ser:
  - **Plugins y Módulos Core**: Integraciones nativas de IA (automatización de SO, generación de imágenes, etc).
  - **Apps Autónomas**: Aplicaciones web completas que se ejecutan totalmente en local dentro del ecosistema.
  - **Control Room Widgets**: Herramientas para el panel de control del sistema y telemetría en tiempo real.
  - **Personas y Temas**: Paquetes para personalizar el aspecto visual y el comportamiento del agente.
- **OS Adapter**: Una capa de abstracción que garantiza la compatibilidad multiplataforma (Windows, Linux, macOS).
- **WebUI Backend**: Un servidor Flask integrado que aloja la interfaz nativa, el Central Hub, y enruta dinámicamente APIs y recursos de los paquetes HPM.
