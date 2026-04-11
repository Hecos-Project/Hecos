# ⚙️ 3. Configuración Dinámica (O-T-F)

Zentra proporciona teclas de función (F1-F7) para interactuar y re-parametrizar el sistema en tiempo real, con memoria permanente.

* **[ F1 ] MANUAL DE ACCIÓN (Ayuda):** Llama a los protocolos "root" de los Plugins, mostrando comandos libres (p. ej., `list:`, `cmd:`, `abrir:`).
* **[ F2 ] CAMBIAR MODELO DE IA:** Selecciona rápidamente el modelo de red neuronal (Llama, Gemma, Cloud, etc.) de la lista del backend.
* **[ F3 ] CARGAR ALMA / PERSONALIDAD:** Cambia el tono y la conciencia del sistema. Zentra escanea automáticamente la carpeta `/personality/` al iniciar.
* **[ F4 ] SILENCIAR MICRÓFONO (MIC):** Activa o desactiva la captura del micrófono.
* **[ F5 ] SILENCIAR VOZ (TTS):** Habilita o silencia la síntesis de voz de respuesta.

### 🎛️ EL PANEL DE CONTROL [ F7 ]
A través de una interfaz gráfica basada en menús, ofrece control granular sobre Zentra Core. Permite editar parámetros booleanos, numéricos o de texto.

**Guardado y Reinicio:**
Los cambios se pueden descartar con `ESC` o guardar al confirmar la salida. Si se modifican, el sistema realizará un **Reinicio en Frío** automático en 1 segundo para aplicar los nuevos parámetros.
