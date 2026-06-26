# 🔌 4. Sistema Modular / Módulos

Hecos está construido sobre una arquitectura **Nativa de Módulos**. Cada capacidad (gestión de archivos, hardware, multimedia) es manejada por un módulo independiente.

- **Flexibilidad**: Los módulos se pueden activar o desactivar en tiempo real a través del Panel de Configuración.
- **Integridad**: Cada módulo opera en su propio espacio aislado, asegurando que un error no bloquee todo el sistema.
- **Descubrimiento**: Los nuevos paquetes y módulos añadidos al sistema se detectan automáticamente.

### Gestión vía WebUI
En la barra lateral de la WebUI, puedes ver la lista de módulos activos con sus respectivos botones macro para enviar comandos rápidos a la IA.

### Módulos y Capacidades Principales
Hecos incluye de forma nativa varios módulos potentes:
- **Calendario Integrado**: Un módulo de calendario completo con seguimiento de días festivos y visualización de eventos directamente en la WebUI.
- **Recordatorios**: Un planificador de tareas avanzado con interpretación de PNL ("recuérdame en 10 minutos") y notificaciones activas del SO.
- **Motor Reproductor Multimedia**: Un robusto sistema multimedia (VLC 64-bit + fallback FFplay) que soporta gestión de estado, pausa/reanudación y control de volumen.
- **Automatización del Navegador**: Un módulo para interactuar semánticamente con páginas web y extraer información.
- **Automatización del SO**: Un módulo para automatizar tareas del sistema operativo mediante el control del ratón y el teclado.

### Tipos de Módulos
Hecos soporta una arquitectura de 8 capas donde todo se define como un módulo:
- **Core Modules**: Funciones del SO y del sistema integradas y no extraíbles.
- **Plugins**: Herramientas y capacidades reactivas llamadas por la IA.
- **Apps**: Mini-aplicaciones autónomas con su propia UI y ciclo de vida.
- **Widgets**: Componentes frontend interactivos para el panel (Control Room).
- **Personas**: Personalidades de IA y perfiles de comportamiento instalables.
- **Themes**: Paquetes de estilos y CSS personalizados para la UI.
- **Skill Packs**: Paquetes de comandos slash adicionales para el chat.
- **MCP Servers**: Puentes universales para herramientas externas vía el Model Context Protocol.

### 📦 Gestor de Paquetes Hecos (HPM)
A partir de la versión 0.35.0, Hecos introduce el **Gestor de Paquetes Hecos**, un sistema centralizado que hace que la plataforma sea potencialmente universal.
- **Paquetes Independientes (`.hpkg`)**: Puedes instalar nuevos módulos core, plugins, extensiones, widgets y personalidades simplemente arrastrando y soltando archivos `.hpkg` en el Gestor de Paquetes dentro de la WebUI.
- **Seguridad Avanzada**: Todos los paquetes de terceros son verificados utilizando firmas digitales criptográficas (Ed25519) para asegurar la absoluta integridad del código.
- **Aislamiento**: Los módulos mantienen su propia lógica y configuración de manera autónoma, previniendo conflictos con el Sistema Core.

---

### 🎭 El Alma del Sistema: Personas Nativas

Una capacidad fundamental del sistema modular es el **Cambio de Personalidad** nativo. Hecos no es solo un asistente rígido: adapta su comportamiento, tono y carácter según la personalidad (persona) que cargues. Cada persona está programada para actuar de manera diferente y cumplir un rol único en tu vida diaria.

<p align="center">
  <img src="https://raw.githubusercontent.com/Hecos-Project/hecos/main/hecos/assets/Urania_9800_Logo.png" width="400">
  <br>
  <em>Urania 9800, la Mascota oficial de Hecos y tu compañera amigable del día a día.</em>
</p>

Por defecto, Hecos incluye varias personalidades preconfiguradas:
* **Hecos System Soul** — El sistema central neutral, rígido y distante. El verdadero Hecos, perfecto para la automatización pura y tareas precisas.
* **Urania 9800** — La mascota animada. Una verdadera amiga para el día a día, diseñada para una interacción casual, empática y alegre.
* **Sebastian Pro** — El perfecto mayordomo de estilo británico. Educado, eficiente y siempre dispuesto a servir.
* **Atlas** — El imponente y autoritario guardián digital.
* **Nova X-01** — Una entidad robótica precisa y analítica, para quienes prefieren interacciones puramente lógicas.

Puedes intercambiar estas personalidades en cualquier momento, cambiando no solo la voz y el tono, sino el verdadero "alma" del sistema.
