# 🔄 2. Flujo de Datos

El flujo de información en Hecos sigue una ruta estructurada para garantizar velocidad y seguridad.

1.  **Input**: Recepción vía Terminal (texto), Micrófono (audio) o WebUI.
2.  **Processing**: El Agentic Loop analiza la solicitud utilizando el modelo de IA seleccionado.
3.  **Tool Calling**: Si es necesario, la IA activa los plugins requeridos (p. ej., `SYSTEM`, `FILES`, `IMAGES`).
4.  **Sandbox**: Cada operación lógica es validada y filtrada.
5.  **Output**: Respuesta textual en el chat y síntesis de voz síncrona (TTS).
