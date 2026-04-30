# 🚀 1. Arranque y Controles Iniciales

Al iniciar el ejecutable o el script de Python, Hecos comienza su secuencia de **Arranque Sincronizado**.

### Diagnóstico Previo
Por defecto, el sistema verifica:
- Integridad de carpetas vitales (`core/`, `plugins/`, `memory/`, etc.).
- Estado del hardware (CPU y RAM dentro de los límites).
- Estado de los módulos de Audio y Voz.
- Respuesta del servidor de IA (Backend).
- Escaneo de Plugins activos/desactivados.

### ⚡ Bootstrap One-Click
La forma recomendada de iniciar Hecos es utilizar los scripts de inicio universales en la carpeta raíz:
- **Windows:** `START_SETUP_HERE_WIN.bat`
- **Linux:** `START_SETUP_HERE_LINUX.sh`

Estos scripts gestionan automáticamente la comprobación del entorno, las dependencias e inician el **Asistente de Configuración**.

### 🧩 Inicio de Componentes Individuales
Para usuarios avanzados, los componentes se pueden iniciar por separado:
- **Interfaz Web:** `HECOS_WEB_RUN_WIN.bat` (Win) / `hecos_web_run.sh` (Linux)
- **Consola de Terminal:** `HECOS_CONSOLE_RUN_WIN.bat` (Win) / `HECOS_CONSOLE_RUN.sh` (Linux)
- **Paquete Completo:** `main.py` (Inicia el Tray + Backend)

### 🏎️ Inicio Rápido (Fast Boot)
Puedes activar el **Inicio Rápido** en el Panel de Control (**F7**) bajo `SYSTEM` para omitir el chequeo inicial y reducir el tiempo de carga a **~0.5 segundos**.
