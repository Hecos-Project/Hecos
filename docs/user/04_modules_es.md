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

### 📦 Gestor de Paquetes Hecos (HPM)
A partir de la versión 0.35.0, Hecos introduce el **Gestor de Paquetes Hecos**, un sistema centralizado que hace que la plataforma sea potencialmente universal.
- **Paquetes Independientes (`.hpkg`)**: Puedes instalar nuevos módulos core, plugins, extensiones, widgets y personalidades simplemente arrastrando y soltando archivos `.hpkg` en el Gestor de Paquetes dentro de la WebUI.
- **Seguridad Avanzada**: Todos los paquetes de terceros son verificados utilizando firmas digitales criptográficas (Ed25519) para asegurar la absoluta integridad del código.
- **Aislamiento**: Los módulos mantienen su propia lógica y configuración de manera autónoma, previniendo conflictos con el Sistema Core.
