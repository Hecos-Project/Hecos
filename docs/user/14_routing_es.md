# 🧭 14. Enrutamiento de Instrucciones de IA (3 Niveles)

Zentra utiliza un sistema de enrutamiento de tres niveles para decidir cómo debe responder la IA a cada comando.

1.  **Defaults del Plugin**: Instrucciones básicas proporcionadas por el desarrollador del plugin.
2.  **Overrides de Usuario**: Tus personalizaciones guardadas en el archivo `routing_overrides.yaml`. Estas tienen prioridad sobre los valores por defecto.
3.  **Core Fallback**: Reglas del sistema que garantizan estabilidad y seguridad.

- **Editor Integrado**: En la pestaña "Routing" de la WebUI, puedes modificar estas reglas sin tocar el código, añadiendo instrucciones específicas para cada plugin.
- **Flexibilidad Total**: Puedes cambiar el comportamiento de cualquier comando de la IA con un simple clic.
