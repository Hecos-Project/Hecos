# ⚡ 1. Guía de Inicio Rápido

¡Bienvenido a Hecos! Siga estos pasos para configurar el sistema y comenzar a usar la IA en su PC de inmediato.

## 1. Instalación

> [!TIP]
> **Método Recomendado — ¡Instala con la Tray!** Descarga solo **Hecos Tray** (el paquete ligero), ábrelo y accede a la **Tray Dashboard**. Ve a la pestaña **Updates** y haz clic en *Manage Core*: el sistema descarga e instala todo automáticamente. Es el método más sencillo, guiado y completo.

> [!IMPORTANT]
> **Ruta de Instalación**: Recomendamos encarecidamente extraer e instalar Hecos en un directorio raíz como `C:\Hecos`. Evite instalarlo en `Descargas`, en el `Escritorio` o en carpetas muy profundas, ya que las rutas largas o con espacios pueden causar problemas de inicio o fallos en las funcionalidades. Si descargas **Hecos Tray** por separado, instálala también en una carpeta raíz: `C:\Hecos-Tray`.

> [!WARNING]
> **Dependencias del Sistema**: El ecosistema de Hecos ahora incluye un **External Dependency Manager (EDM)** automático. Durante o después de la instalación, si faltan componentes críticos (como `VC_redist`, `Tesseract OCR` o `Node.js`), la WebUI te notificará y te permitirá descargarlos e instalarlos en segundo plano con un solo clic. Asegúrate de estar conectado a internet para permitir la descarga.

**Método alternativo (avanzado):** Si ya descargaste el paquete Core completo, usa los scripts de configuración automática en la carpeta raíz:
- **Windows:** Haga doble clic en `START_SETUP_HERE_WIN.bat`
- **Linux:** Abra una terminal y ejecute `bash START_SETUP_HERE_LINUX.sh`

Estos scripts instalarán automáticamente las dependencias e iniciarán el **Asistente de Configuración** en su navegador.

## 2. El Asistente de Configuración

El Asistente de Configuración se abrirá automáticamente en su navegador. Le guiará a través de:
- La selección de su modelo de IA (local o basado en la nube).
- La configuración de su idioma y preferencias.
- La configuración de las claves API que tenga.

## 3. Iniciando Hecos

Después de la configuración inicial, el flujo de trabajo diario más rápido es:
- Inicie **Hecos Tray** (doble clic en el `.exe` o ejecute el script de inicio).
- Doble clic en el icono de la bandeja para abrir la **Tray Dashboard**.
- Haga clic en **Iniciar Hecos** para poner el sistema en línea.
- La **WebUI** se abre automáticamente en su navegador (o presione **F11** en cualquier momento).

## 4. Panel de Control (F7)

Para cambiar los parámetros, agregar nuevas claves API o activar complementos:
- Presione **F7** en su teclado o haga clic en el icono de engranaje/logotipo en la WebUI para abrir el **Hecos Hub**.
- Los cambios se guardan instantáneamente.

## 5. Tray — Tu Mando a Distancia Universal

Hecos Tray es mucho más que un simple icono: es el centro de control rápido de todo el sistema.
- El icono se encuentra junto al reloj de Windows, siempre disponible sin ocupar espacio.
- **Doble clic** en el icono para abrir la **Tray Dashboard**, desde donde puedes iniciar/detener Hecos, leer los logs en tiempo real, ver los procesos activos e instalar actualizaciones.
- **Clic derecho** para un menú rápido con las acciones más comunes.

---
*¡Todo listo! Comience a explorar el potencial de su nueva capa operativa de IA soberana local.*
