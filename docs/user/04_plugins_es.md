# 🔌 4. Sistema Modular / Plugins

Hecos está construido sobre una arquitectura **Nativa de Plugins**. Cada capacidad (gestión de archivos, hardware, multimedia) es manejada por un módulo independiente.

- **Flexibilidad**: Los plugins se pueden activar o desactivar en tiempo real a través del Panel de Configuración.
- **Integridad**: Cada plugin opera en su propio espacio aislado, asegurando que un error en un módulo no bloquee todo el sistema.
- **Descubrimiento**: Los nuevos plugins añadidos a la carpeta `plugins/` se detectan automáticamente al iniciar.

### Gestión vía WebUI
En la barra lateral de la WebUI, puedes ver la lista de plugins activos con sus respectivos botones macro para enviar comandos rápidos a la IA.
