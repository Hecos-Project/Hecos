# 🔌 4. Sistema Modular / Plugins

Hecos está construido sobre una arquitectura **Nativa de Plugins**. Cada capacidad (gestión de archivos, hardware, multimedia) es manejada por un módulo independiente.

- **Flexibilidad**: Los plugins se pueden activar o desactivar en tiempo real a través del Panel de Configuración.
- **Integridad**: Cada plugin opera en su propio espacio aislado, asegurando que un error en un módulo no bloquee todo el sistema.
- **Descubrimiento**: Los nuevos plugins añadidos a la carpeta `plugins/` se detectan automáticamente al iniciar.

### Gestión vía WebUI
En la barra lateral de la WebUI, puedes ver la lista de plugins activos con sus respectivos botones macro para enviar comandos rápidos a la IA.

### Plugins y Capacidades Principales
Hecos incluye de forma nativa varios plugins potentes:
- **Calendario Integrado**: Un módulo de calendario completo con seguimiento de días festivos y visualización de eventos directamente en la WebUI.
- **Recordatorios**: Un planificador de tareas avanzado con interpretación de PNL ("recuérdame en 10 minutos") y notificaciones activas del SO.
- **Motor Reproductor Multimedia**: Un robusto sistema multimedia (VLC 64-bit + fallback FFplay) que soporta gestión de estado, pausa/reanudación y control de volumen.
