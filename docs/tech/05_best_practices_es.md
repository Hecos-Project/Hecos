# 🛠️ 5. Mejores Prácticas para Desarrolladores

Al desarrollar nuevos plugins o ampliar Zentra Core, sigue estas pautas:

1.  **Modularidad**: Mantén la lógica del plugin aislada y utiliza las APIs del sistema proporcionadas (p. ej., `self.core.speak()`).
2.  **Validación**: Utiliza siempre Pydantic para definir nuevos esquemas de configuración.
3.  **Seguridad**: Nunca ejecutes comandos del sistema directamente; utiliza siempre el `SubprocessAdapter`.
4.  **Logging**: Utiliza `logger.debug()` e `logger.info()` para rastrear las operaciones de tu plugin.
5.  **Documentación**: Siempre añade una breve descripción técnica de tu código para facilitar el mantenimiento futuro.
