# ⚡ Inicio Rápido (Quick Start)

¡Bienvenido a Zentra Core! Siga estos pasos para configurar el sistema y comenzar a usar la IA en su PC de inmediato.

## 1. Instalación (Bootstrap)
La forma más sencilla de comenzar è utilizzare gli script di configurazione automatica nella cartella principale (root):
- **Windows:** Haga doble clic en `START_SETUP_HERE_WIN.bat`
- **Linux:** Abra una terminal y ejecute `bash START_SETUP_HERE_LINUX.sh`

Estos scripts instalarán automáticamente le dipendenze e avvieranno il **Setup Wizard** en su navegador.

## 2. El Asistente de Configuración (Setup Wizard)
En el primer lanzamiento, su navegador se abrirá en `http://localhost:7070`. Siga los pasos guiados:
1. **Bienvenido**: Haga clic en "Get Started".
2. **Idioma**: Seleccione su idioma preferido.
3. **Elija el Cerebro (AI Provider)**: 
   - **Cloud (Online)**: Use modelos potentes como Gemini o GPT-4o. Deberá ingresar su **Clave API**.
   - **Local (Offline)**: Si tiene Ollama o KoboldCpp instalado en su PC, Zentra se conectará automáticamente. **¡En este caso NO necesita ninguna clave API!**, todo se ejecuta localmente.
4. **Generación de Imágenes**: Actualmente, la creación de imágenes requiere un proveedor en línea. La mejor forma es crear una cuenta gratuita en **HuggingFace**, generar un "Access Token" e ingresarlo en la configuración de Zentra para usar modelos avanzados como **FLUX.1-dev**.
5. **Configurar Personalidad**: Elija el "alma" de su asistente (ej. Urania o Atlas).
6. **Finalizar**: Haga clic en "Save and Start".

## 3. Primer Uso
Ahora que Zentra está activo, así es como può interagire:
- **Chat**: Escriba en la barra de texto en la parte inferior de la WebUI y presione Intro.
- **Voz**: 
  - Haga clic en el icono del micrófono en la WebUI.
  - O use el atajo global **Ctrl+Shift+Z** (Windows) para hablar sin siquiera abrir el navegador.
- **Visión**: Arrastre una imagen al chat para pedirle a Zentra que la describa o analice.

## 4. Panel de Control (F7)
Para cambiar parámetros, agregar nuevas claves API o activar complementos:
- Presione **F7** en su teclado o haga clic en el icono del engranaje/logotipo en la WebUI para abrir el **Zentra Hub**.
- Los cambios se guardan instantáneamente.

## 5. Icono de Bandeja (Background)
Zentra permanece activo en la bandeja del sistema (cerca del reloj de Windows). 
- Puede cerrar la pestaña del navegador: el sistema continuará ejecutándose en segundo plano para responder a las teclas de acceso rápido.
- Haga clic con el botón derecho en el icono "Z" per riaprire la WebUI o chiudere definitivamente Zentra.

---
*¡Ya está todo listo! Comience a explorar el potencial de su nuevo sistema operativo de IA soberano.*
