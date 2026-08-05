# 🚀 3. Arranque y Controles Iniciales

Al iniciar el ejecutable o el script de Python, Hecos comienza su secuencia de **Arranque Sincronizado**.

### Diagnóstico Previo
Por defecto, el sistema verifica:
- Integridad de carpetas vitales (`core/`, `plugins/`, `memory/`, etc.).
- Estado del hardware (CPU y RAM dentro de los límites).
- Estado de los módulos de Audio y Voz.
- Respuesta del servidor de IA (Backend).
- Escaneo de Plugins activos/desactivados.

### ⚡ Bootstrap One-Click

> [!TIP]
> **Método Recomendado — ¡Instala con la Tray!** Descarga solo **Hecos Tray** (el paquete ligero), ábrelo y accede a la **Tray Dashboard**. Ve a la pestaña **Updates** y haz clic en *Download / Install Core*: el sistema descarga y configura todo automáticamente. Es el método más sencillo y completo.

> [!IMPORTANT]
> **Ruta de Instalación**: Recomendamos encarecidamente extraer e instalar Hecos en un directorio raíz como `C:\Hecos`. Evite instalarlo en `Descargas`, en el `Escritorio` o en carpetas muy profundas, ya que las rutas largas o con espacios pueden causar problemas de inicio o fallos en las funcionalidades.

> [!WARNING]
> **Dependencias del Sistema**: Antes de ejecutar la instalación o configuración, asegúrese de haber instalado los paquetes redistribuibles (como `VC_redist`) que se encuentran en la carpeta **`dependencies`** incluida en el paquete. Si faltan estos archivos, componentes críticos como la IA y el motor de voz (TTS) no se iniciarán.

**Método alternativo (avanzado):** Si ya tienes el paquete Core, usa los scripts de inicio universales en la carpeta raíz:
- **Windows:** `START_SETUP_HERE_WIN.bat`
- **Linux:** `START_SETUP_HERE_LINUX.sh`

Estos scripts gestionan automáticamente la comprobación del entorno, las dependencias e inician el **Asistente de Configuración**.

> [!TIP]
> **Inicios Posteriores**: Después de la configuración inicial, la forma más rápida y cómoda de usar Hecos cada día es iniciar la **Hecos Tray**. Haz doble clic en su icono en la bandeja del sistema para abrir la **Tray Dashboard** y gestionar todo el sistema desde un único panel.

### 🧩 Inicio de Componentes Individuales
Para usuarios avanzados, los componentes se pueden iniciar por separado:
- **Interfaz Web:** `HECOS_WEB_RUN_WIN.bat` (Win) / `hecos_web_run.sh` (Linux)
- **Consola de Terminal:** `HECOS_CONSOLE_RUN_WIN.bat` (Win) / `HECOS_CONSOLE_RUN.sh` (Linux)
- **Paquete Completo:** `main.py` (Inicia el Tray + Backend)

### 🏎️ Inicio Rápido (Fast Boot)
Puedes activar el **Inicio Rápido** en el Panel de Control (**F7**) bajo `SYSTEM` para omitir el chequeo inicial y reducir el tiempo de carga a **~0.5 segundos**.
