# 🌌 Proyecto Hecos
<p align="center">
  <img src="hecos/assets/Hecos_Logo_Banner.png" width="400" alt="Logo de Hecos">
</p>

# Hecos - Versión 0.21.0 (Runtime Alpha)
Idiomas: [English](README.md) | [Italiano](README_ITA.md) | [Español](README_ESP.md)

# 🤖 Hecos
**Helping Companion System (Privado, Rápido, Simple)**

---

> **Estado Runtime Alpha**: Hecos se encuentra actualmente en `v0.21.0`. Es un Helping Companion System local que conecta el razonamiento de alto nivel con la ejecución del sistema a nivel root.

## 🚀 Resumen General
**Hecos** es un **Helping Companion System**: un ecosistema local que une el razonamiento de IA con la ejecución del sistema a nivel root y redes avanzadas. Transforma el hardware local en una entidad digital soberana a través de un tablero profesional y una infraestructura de seguridad avanzada.

Basado en tres pilares fundamentales:
* 🛡️ **Privacidad Primero** — Funcionamiento 100% local, cero dependencia de la nube y arquitectura de privacidad de 3 niveles.
* ⚡ **Velocidad Extrema** — Arquitectura nativa optimizada y sistema de complementos de alto rendimiento para una respuesta instantánea.
* 🧊 **Simplicidad Total** — Tablero profesional y diseño modular que hace intuitiva la orquestación de IA avanzada.

Ahora completamente migrado a una **arquitectura estable de Runtime Alpha**, Hecos 0.21.0 ofrece una interfaz Web dedicada (Chat + Config) e internacionalización completa. Gracias a **LiteLLM**, soporta Ollama, KoboldCpp y los principales proveedores de la nube con streaming en tiempo real y TTS local.

---

## ✨ Características Principales (v0.21.0)
* **📅 Calendario Integrado** — Módulo de calendario completo con seguimiento de días festivos y codificación de colores localizada de los eventos.
* **⏰ Módulo Recordatorio** — Planificador de tareas impulsado por NLP con capacidades de repetición (snooze) y notificaciones activas del SO.
* **💻 Ventana de Acciones (Action Window)** — Consola limpia de estilo terminal directamente dentro de la interfaz de usuario de chat para monitorizar la ejecución nativa del sistema y los procesos en segundo plano.
* **🎵 Nuevo Reproductor Multimedia** — Backend de audio avanzado (VLC 64-bit + fallback FFplay) que soporta un estado de reanudación/pausa resiliente, cálculos dinámicos de listas de reproducción y control de volumen global.
* 🎨 **Flux Prompt Studio** — Ingeniería de prompts en tiempo real para Flux.1 con persistenza automatica di metadati sidecar.
* 🖼️ **Image Metadata Injection** — Los resultados de IA generativa ahora incluyen archivos sidecar JSON (.txt) con prompt, semilla e info del sampler para flujos profesionales.
* 🎭 **Chat UI Mejorada** — Nuevos encabezados de chat con nombres de Usuario/Persona, marcas de tiempo y mejor posición de botones (Copiar/Editar/Regenerate).
* 🔄 **Regeneración Corregida** — Se resolvieron problemas de duplicación de historial y errores de sesión durante la regeneración.
* 🛡️ **Arquitectura de Privacidad de 3 Niveles** — Gestión unificada con modos **Normal**, **Auto-Wipe** (solo RAM) e **Incognito** (sin rastro).
* 🔌 **Universal Tool Hub (MCP Bridge)** — Soporte nativo para el **Model Context Protocol**. Conéctate a miles de herramientas AI con un solo clic.
* 🔭 **Deep MCP Discovery** — Explorador avanzado con búsqueda multi-registro (Smithery, MCPSkills, GitHub) e instalación inmediata.
* 🔒 **Hecos PKI Profesional (HTTPS)** — Certificación Root CA integrada para habilitar Mic/Cámara en toda la LAN de forma segura.
* 🏗️ **Plugin WebUI Nativo** — Interfaz de alto rendimiento optimizada para escritorio y dispositivos móviles.
* 🎛️ **Control Room & Widgets** — Un tablero personalizable estilo masonry para widgets en tiempo real y telemetría del SO.
* 🌐 **Automatización del Navegador** — Plugin nativo para la interacción semántica web y el scraping.
* ⌨️ **Automatización del SO** — Plugin nativo para el control programático del ratón y el teclado.
* 🗂️ **Hecos Drive (File Manager)** — Gestión de archivos y editor integrado con interfaz de doble panel.

---

## 🧠 Cómo Funciona
**Hecos está actualmente en `v0.21.0`.** Este repositorio contiene el motor, el backend, los módulos de razonamiento de IA y la WebUI nativa principal.
* **Plugins** → Acciones y capacidades (sistema, web, multimedia, etc.).
* **Memory** → Identidad y almacenamiento persistente.
* **UI** → Capa de interacción con el usuario.
* **Bridge** → Integraciones externas y APIs.

La IA genera comandos estructurados que son interpretados y ejecutados a través del sistema de plugins.

---

## ⚡ Inicio Rápido (Instalación One-Click)
La forma más sencilla de instalar y configurar Hecos desde cero es utilizar el **Asistente de Configuración Universal**.

### 1. Clonar el repositorio
```bash
git clone https://github.com/Hecos-Project/Hecos.git
cd Hecos
```

### 2. Lanzar el Asistente de Configuración
Ejecuta el script de inicio para tu plataforma. Esto comprobará automáticamente Python, instalará las dependencias e iniciará el asistente de configuración en tu navegador.

**Windows:**
```powershell
.\START_SETUP_HERE_WIN.bat
```

**Linux:**
```powershell
bash START_SETUP_HERE_LINUX.sh
```

### 3. Componentes Manuales y Scripts de Utilidad
Si prefieres gestionar los componentes por separado o realizar tareas de mantenimiento manual, utiliza estos scripts dedicados:

| Plataforma | Script | Descripción |
| :--- | :--- | :--- |
| **Todas** | `main.py` | Inicia el sistema completo (Tray + WebUI + Backend) |
| **Windows** | `RESTART_TRAY_ICON_WIN.bat` | Restaurar el icono de bandeja si se cerró |
| **Linux** | `RESTART_TRAY_ICON_LINUX.sh` | Restaurar el icono de bandeja si se cerró |
| **Windows** | `scripts\windows\run\HECOS_WEB_RUN_WIN.bat` | Inicia SOLO la Interfaz Web y el Servidor |
| **Linux** | `scripts/linux/run/hecos_web_run.sh` | Inicia SOLO la Interfaz Web y el Servidor |
| **Windows** | `scripts\windows\run\HECOS_CONSOLE_RUN_WIN.bat` | Inicia SOLO la Consola de Terminal (TUI) |
| **Linux** | `scripts/linux/run/HECOS_CONSOLE_RUN.sh` | Inicia SOLO la Consola de Terminal (TUI) |
| **Windows** | `scripts\windows\setup\INSTALL_HECOS_WIN.bat` | Instalación manual de dependencias y Piper |
| **Linux** | `scripts/linux/setup/INSTALL_HECOS_LINUX.sh` | Instalación manual de dependencias y Piper |

### 4. Configuración y Primera Ejecución

### 🛡️ Modo Silencioso (Sin Ventanas)
Si desea que Hecos se ejecute completamente en segundo plano sin ventanas de terminal visibles:
1.  **Usar el Icono de Bandeja**: Inicie Hecos a través del icono de la bandeja. Gestionará los componentes del sistema de forma invisible en segundo plano.
3.  **Inicio Silencioso**: Use `START_HECOS_SILENT_WIN.vbs` para un inicio 100% invisible (sin ventanas de consola).
3.  **Recuperación Manual**: Si cierra accidentalmente el icono, use `START_HECOS_TRAY_WIN.bat`.

---

## 🧠 Backends de IA Soportados (Motores LLM)

Hecos está completamente fuera de línea por defecto y requiere un motor de IA local para procesar lógica y conversación. Durante la configuración, debes instalar uno de los backends independientes a continuación. Hecos los detectará automáticamente.

### 🔹 1. Ollama (Recomendado)
Fácil de usar, rápido y optimizado para ejecutarse localmente como servicio en segundo plano.
- **Descarga**: 👉 https://ollama.com/download
- **Configuración**: Una vez instalado, abre tu terminal/símbolo del sistema y ejecuta `ollama run llama3.2` para descargar y probar un modelo ligero y rápido. Hecos lo detectará al instante.

### 🔹 2. KoboldCpp (Alternativa)
Perfecto para modelos manuales GGUF y hardware más antiguo sin grandes instalaciones.
- **Descarga**: 👉 https://github.com/LostRuins/koboldcpp/releases
- **Configuración**: Descarga el archivo `.exe` (o el binario de Linux), haz doble clic, selecciona cualquier modelo de instrucciones GGUF descargado de HuggingFace y ejecútalo. Hecos se conectará a través del puerto `5001`.

---

## 🔌 Sistema de Plugins
Hecos utiliza una arquitectura dinámica. Cada plugin puede registrar comandos, ejecutar acciones del sistema y extender las capacidades de la IA.

Plugins incluidos:
* **Control del sistema y Gestor de archivos**
* **Automatización Web y Dashboard de hardware**
* **Control multimedia y Cambio de modelo**
* **Gestión de memoria**

---

## 💾 Sistemas de Memoria y Voz

### 🗄️ Sistema de Memoria
Hecos incluye una capa de memoria persistente impulsada por SQLite para un almacenamiento local ligero. Almacena conversaciones, mantiene la identidad y guarda las preferencias del usuario.

### 🎙️ Sistema de Voz
* **Entrada Speech-to-text** (voz a texto)
* **Salida Text-to-speech** (texto a voz)
* **Interacción en tiempo real**

---

## 🔗 Integraciones y Privacidad

### 🤝 Integraciones
Hecos puede integrarse con:
* **Open WebUI** (chat + streaming)
* **Home Assistant** (vía bridge)

### 🔐 Privacidad Primero
Hecos está diseñado pensando en la privacidad: funciona 100% localmente, sin servicios en la nube obligatorios y con control total sobre los datos.

---

## 🛣️ Hoja de Ruta (Roadmap)
- [ ] 📱 Integración con Telegram (control remoto)
- [ ] 🧠 Sistema de memoria avanzado
- [ ] 🤖 Arquitectura multi-agente
- [ ] 🛒 Marketplace de plugins
- [ ] 🎨 UI/UX mejorada

---

## ⚠️ Descargo de Responsabilidad (Disclaimer)
Hecos puede ejecutar comandos a nivel de sistema y controlar tu entorno. Úsalo con responsabilidad. El autor no se hace responsable del mal uso o de posibles daños.

---

## 📜 Licencia
Licencia GPL-3.0

---

## 👥 Créditos y Contacto
Líder de Desarrollo: Antonio Meloni (Tony)
Email Oficial: hecos.project@gmail.com

---

## 📚 Documentación Técnica
- 🏗️ **[Guía de Arquitectura](docs/TECHNICAL_GUIDE.md)**
- 🔌 **[Desarrollo de Plugins](docs/PLUGINS_DEV.md)**
- 📁 **[Mapa de Estructura](docs/ARCHITECTURE_MAP.md)**

---

## 💡 Visión
Hecos aspira a convertirse en una plataforma de asistencia de IA local totalmente autónoma: una alternativa privada y extensible a los sistemas de IA basados en la nube.