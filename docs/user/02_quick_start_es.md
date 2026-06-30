# ⚡ 2. Guía de Inicio Rápido

¡Bienvenido a Hecos! Siga estos pasos para configurar el sistema y comenzar a usar la IA en su PC de inmediato.

## 1. Instalación (Bootstrap)

> [!IMPORTANT]
> **Ruta de Instalación**: Recomendamos encarecidamente extraer e instalar Hecos en un directorio raíz como `C:\Hecos`. Evite instalarlo en `Descargas`, en el `Escritorio` o en carpetas muy profundas, ya que las rutas largas o con espacios pueden causar problemas de inicio o fallos en las funcionalidades.

> [!WARNING]
> **Dependencias del Sistema**: Antes de ejecutar la instalación o configuración, asegúrese de haber instalado los paquetes redistribuibles (como `VC_redist`) que se encuentran en la carpeta **`dependencies`** incluida en el paquete. Si faltan estos archivos, componentes críticos como la IA y el motor de voz (TTS) no se iniciarán.

La forma más fácil de comenzar es utilizando los scripts de configuración automática en la carpeta raíz:
- **Windows:** Haga doble clic en `START_SETUP_HERE_WIN.bat`
- **Linux:** Abra una terminal y ejecute `bash START_SETUP_HERE_LINUX.sh`

Estos scripts instalarán automáticamente las dependencias e iniciarán el **Asistente de Configuración** en su navegador.

## 2. El Asistente de Configuración

En el primer inicio, su navegador se abrirá en `http://localhost:7070`. Siga los pasos guiados:
1. **Bienvenido**: Haga clic en "Comenzar".
2. **Idioma**: Seleccione su idioma preferido.
3. **Elija el Cerebro (Proveedor de IA)**: 
   - **Cloud (En línea)**: Use modelos potentes como Gemini o GPT-4o. Deberá ingresar su **Clave API**.
   - **Local (Sin conexión)**: Si tiene Ollama o KoboldCpp instalado en su PC, Hecos se conectará automáticamente. **En este caso, ¡NO necesita ninguna clave API!**, todo se ejecuta en su hardware.
4. **Generación de Imágenes**: Actualmente, la creación de imágenes requiere un proveedor en línea. La forma mejor y más rápida es crear una cuenta gratuita en **HuggingFace**, generar un "Access Token" e ingresarlo en la configuración de Hecos para utilizar modelos avanzados como **FLUX.1-dev**.
5. **Configurar Personalidad**: Elija el "alma" de su asistente (por ejemplo, Urania o Atlas).
6. **Terminar**: Haga clic en "Guardar e Iniciar".

## 3. Primer Uso

Ahora que Hecos está activo, así es como puede interactuar:
- **Chat**: Escriba en la barra de texto en la parte inferior de la WebUI y presione Enter.
- **Voz**: 
  - Haga clic en el icono del micrófono en la WebUI.
  - O use el acceso directo global **Ctrl+Shift+Z** (Windows) para hablar sin siquiera abrir el navegador.
- **Visión**: Arrastre una imagen al chat para pedirle a Hecos que la describa o la analice.

## 4. Panel de Control (F7)

Para cambiar los parámetros, agregar nuevas claves API o activar complementos:
- Presione **F7** en su teclado o haga clic en el icono de engranaje/logotipo en la WebUI para abrir el **Hecos Hub**.
- Los cambios se guardan instantáneamente.

## 5. Icono de la Bandeja del Sistema (Segundo Plano)

Hecos permanece activo en la bandeja del sistema (cerca del reloj de Windows). 
- Puede cerrar la pestaña del navegador: el sistema seguirá ejecutándose en segundo plano para responder a las teclas de acceso rápido.
- Haga clic derecho en el icono "Z" para volver a abrir la WebUI o salir de Hecos.

---
*¡Todo listo! Comience a explorar el potencial de su nueva capa operativa de IA soberana local.*
