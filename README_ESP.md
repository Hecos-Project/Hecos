# 🌌 Proyecto Hecos
<p align="center">
  <img src="hecos/assets/Hecos_Logo_Banner.png" width="400" alt="Logo de Hecos">
</p>

# Hecos - Versión 0.50.0 (Fase II: Ghost Fire)
Idioma: [English](README.md) | [Italiano](README_ITA.md) | [Español](README_ESP.md)

# 🤖 Hecos
**Helping Companion System (Privado, Rápido, Simple)**

---

> **Estado: Fase II (Ghost Fire)**: Hecos está actualmente en `v0.50.0`. Este es un Helping Companion System que actúa como puente entre el razonamiento de alto nivel y la ejecución del sistema root.
>
> ⚠️ **Aviso Importante**: A partir de este lanzamiento principal (0.50.0+), el desarrollo principal y el entorno de destino migran oficialmente a **Windows 11**.

## 🚀 Resumen General
**Hecos** es un **Helping Companion System**: un ecosistema local de primera línea diseñado para conectar de manera fluida la tecnología con la vida humana, combinando el razonamiento de IA, la automatización visual y la ejecución directa del sistema. En lugar de perseguir conceptos abstractos como la soberanía digital, Hecos se enfoca en una única misión pragmática: **mejorar la vida humana**, transformando el hardware local en una herramienta práctica y altamente eficiente para el día a día.

Basado en tres pilares fundamentales:
* 🛡️ **Privacidad Primero** — Funcionamiento 100% local, cero dependencia de la nube y arquitectura de privacidad de 3 niveles.
* ⚡ **Velocidad Extrema** — Arquitectura nativa optimizada y sistema de complementos de alto rendimiento para una respuesta instantánea.
* 🧊 **Simplicidad Total** — Tablero profesional y diseño modular que hace intuitiva la orquestación de IA avanzada.

Ahora completamente migrato a una **arquitectura estable Fase II: Ghost Fire**, Hecos 0.50.0 ofrece una Interfaz Web dedicada (Chat + Configuración) y una Internacionalización completa. Desarrollado por **LiteLLM**, soporta Ollama, Llama.cpp, KoboldCpp y los principales proveedores en la nube con streaming en tiempo real y TTS local (Kokoro y Piper).

---

## ✨ Características Principales (v0.50.0)
* 🎭 **Anulaciones de Chat en Línea y Personalidades Infinitas** — Sobrescribe el modelo de IA, la Persona y la Voz directamente en la interfaz del chat sobre la marcha. Crea infinitas personalidades al instante para cada sesión de conversación.
* 📦 **Arquitectura HPM 0.40** — Migración completa a configuraciones Pydantic+TOML, introduciendo restricciones de versión de dependencias y `pip_requirements` bloqueados.
* 🛠️ **External Dependency Manager (EDM)** — Nuevo sistema automático para la detección, descarga e instalación de dependencias externas (Tesseract, Node.js, VC++ Redistributable) directamente desde la WebUI.
* 🔒 **Hecos SDK (Aislamiento Total)** — Ejecuta los paquetes HPM en procesos aislados dedicados y entornos virtuales independientes (venv) para evitar conflictos de dependencias y bloqueos del hilo principal.
* ⚡ **HDCS (Comandos Directos)** — Ejecuta instantáneamente más de 150 funciones nativas omitiendo el "cerebro" de la IA escribiendo `/` en el chat o con `Ctrl+Alt+Espacio` globalmente.
* ⚙️ **Motor de Automatización Flows** — Editor visual de nodos (drag-and-drop) para la creación de automatizaciones complejas de múltiples pasos, activadores y acciones con integración completa de comandos de voz por NLP.
* **📅 Calendario Integrado** — Módulo de calendario completo con seguimiento de días festivos y codificación de colores localizada para los eventos.
* **⏰ Módulo Recordatorio** — Programador de alarmas y temporizadores impulsado por NLP con funcionalidades de repetición (snooze) y notificaciones activas del SO.
* **💻 Ventana de Acciones (Action Window)** — Consola limpia de estilo terminal directamente dentro de la interfaz de usuario de chat para monitorizar la ejecución nativa del sistema y los procesos en segundo plano.
* **🎵 Nuevo Reproductor Multimedia** — Backend de audio avanzado (VLC 64-bit + fallback FFplay) que soporta un estado de reanudación/pausa resiliente, cálculos dinámicos de listas de reproducción y control de volumen global.
* 🎨 **Flux Prompt Studio** — Ingeniería de prompts en tiempo real para Flux.1 con persistencia automática de metadatos sidecar.
* 🖼️ **Inyección de Metadatos en Imágenes (Image Metadata Injection)** — Los resultados de la IA generativa ahora incluyen archivos sidecar JSON ocultos (.txt) que contienen el prompt, la semilla (seed) e información del sampler para flujos de trabajo profesionales.
* 🎭 **Chat UI Mejorada** — Nuevos encabezados de chat con nombres de Usuario/Persona visibles, marcas de tiempo y un posicionamiento mejorado de las acciones del mensaje (Copiar/Editar/Regenerar).
* 🔄 **Regeneración Corregida** — Se resolvieron los problemas críticos de duplicación de historial y errores de sesión durante la regeneración de mensajes.
* 🗃️ **Archivo de Chat de Modo Dual** — Sistema de archivo contextual con recuperación de chats individuales y funcionalidad de borrado masivo.
* 🧠 **RAG de Alto Rendimiento (FastEmbed)** — Memoria vectorial multiusuario nativa de CPU que utiliza ONNX y LanceDB para una ingesta ultra rápida de documentos.
* 🔐 **Aislamiento de Vault por Usuario** — Arquitectura de memoria consolidada que garantiza una separación absoluta de la privacidad de los datos semánticos y el historial de chat por cada perfil.
* 🛡️ **Arquitectura de Privacidad de 3 Niveles** — Gestión unificada de sesiones con los modos **Normal**, **Auto-Wipe** (almacenamiento solo en RAM, borrado automático al salir) e **Incógnito** (modalidad fantasma sin dejar rastro).
* 📦 **Hecos Package Manager (HPM)** — El componente definitivo para la extensibilidad universal. Un instalador dinámico y centralizado que soporta paquetes independientes `.hpkg`. Instala fácilmente complementos de terceros, widgets y paneles de configuración con arrastrar y soltar, configuraciones aisladas y firmas digitales Ed25519.
* 🔌 **Universal Tool Hub (MCP Bridge)** — Soporte nativo para el **Model Context Protocol**. Conéctate a miles de herramientas de IA externas con un solo clic.
* 🔭 **Deep MCP Discovery** — Explorador avanzado con búsqueda multi-registro (Smithery, MCPSkills, GitHub) e instalación inmediata.
* 🔒 **Hecos PKI Profesional (HTTPS)** — Certificación Root CA autoafirmada (self-signed) integrada para habilitar una experiencia de "Green Lock" (candado verde) segura en todos los dispositivos de la LAN.
* 🏗️ **Plugin WebUI Nativo** — Interfaz de alto rendimiento optimizada y de baja latencia para escritorio y dispositivos móviles.
* 🎛️ **Control Room & Widgets** — Un tablero personalizable estilo masonry para widgets en tiempo real y telemetría del SO.
* 🌐 **Automatización del Navegador** — Plugin nativo para la interacción semántica web y el scraping.
* ⌨️ **Automatización del SO** — Plugin nativo para el control programático del ratón y el teclado.
* 💾 **Hecos Drive (File Manager)** — Gestión de archivos y editor integrado con interfaz de doble panel.

---

## 🧠 Cómo Funciona
Hecos está construido alrededor de una estructura altamente modular de 8 niveles. Todo es un **módulo**:
* **Core Modules** → Funciones integradas del sistema y del SO no extraíbles.
* **Plugins** → Herramientas reactivas y capacidades llamadas por la IA (sistema, web, multimedia, etc.).
* **Apps** → Miniaplicaciones autónomas con su propia interfaz de usuario y ciclo de vida independientes.
* **Personas** → Perfiles de comportamiento y personalidades de IA instalables.
* **Widgets** → Componentes interactivos de interfaz para el panel de la Control Room.
* **Themes** → Paquetes de CSS personalizado y estilos para la interfaz de usuario.
* **Skill Packs** → Paquetes de comandos slash (`/`) adicionales para la interfaz de chat.
* **MCP Servers** → Puentes universales de herramientas externas a través del Model Context Protocol.

La IA genera comandos estructurados que son interpretados y ejecutados a través del sistema de plugins.

---

### 🎭 El Alma de la Máquina: Personas Nativas

Una capacidad fundamental de Hecos es su cambio nativo de personalidad (**Personality Switching**). Hecos no es un asistente frío y rígido: adapta su comportamiento, tono y carácter según la persona que cargues. Cada personalidad está programada para actuar de manera diferente y cumplir un rol único en tu vida diaria.

<p align="center">
  <img src="https://raw.githubusercontent.com/Hecos-Project/hecos/main/hecos/assets/Urania_9800_Logo.png" width="400">
  <br>
  <em>Urania 9800, la mascota oficial de Hecos y tu compañera fiel de todos los días.</em>
</p>

De forma predeterminada, Hecos incluye varias personalidades preconfiguradas:
* **Hecos System Soul** — El sistema central neutro, rígido y distante. Perfecto para la automatización pura y tareas de precisión.
* **Urania 9800** — La mascota vivaz. Una verdadera amiga para el día a día, diseñada para una interacción empática, alegre e informal.
* **Sebastian Pro** — El mayordomo perfecto y altamente profesional. Educado, eficiente y listo para servir.
* **Atlas** — El imponente y autoritario guardián digital.
* **Nova X-01** — Una precisión analítica robótica para quienes prefieren interacciones puramente lógicas.

Puedes intercambiar estas personalidades en cualquier momento, cambiando no solo la voz y el tono, sino el alma misma del sistema.

---

## ⚡ Inicio Rápido (Instalación One-Click)
La forma más sencilla de instalar y configurar Hecos desde cero es utilizar el **Asistente de Configuración Universal**.

### 1. Clonar el repositorio
```bash
git clone [https://github.com/Hecos-Project/Hecos.git](https://github.com/Hecos-Project/Hecos.git)
cd Hecos
```

### 2. Lanzar el Asistente de Configuración
Ejecuta el script de inicio para tu plataforma. Esto comprobará automáticamente Python, instalará las dependencias e iniciará el asistente de configuración en tu navegador.

**Windows:**
```powershell
.\START_SETUP_HERE_WIN.bat
```

**Linux:**
```bash
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
Hecos está diseñado para una experiencia profesional de "descargar y jugar".
- En tu primera ejecución, el sistema detectará que faltan los archivos `system.yaml` y `routing_overrides.yaml`.
- **Generará automáticamente** estos archivos copiando las plantillas desde `hecos/config/data/*.example`.
- Encontrarás tu configuración personal en `hecos/config/data/system.yaml` (ajustes principales) y `routing_overrides.yaml` (reglas de enrutamiento de IA).
- **Consejo profesional**: Usa el [Editor de Enrutamiento] integrado en la WebUI para modificar de forma segura estas reglas sin tocar el código.

### 🔐 Login & Autenticación
Hecos requiere autenticación obligatoria. El inicio de sesión predeterminado por primera vez es:
- **Username:** `admin`
- **Password:** `hecos`

Recomendamos encarecidamente cambiar la contraseña de inmediato desde la pestaña **Usuarios** dentro del Panel de Configuración.

**Recuperación de Contraseña:**
Si te quedas fuera, ejecuta `python scripts/reset_admin.py` desde la terminal para forzar una nueva contraseña, o elimina manualmente el archivo `memory/users.db` para restablecer los valores predeterminados del sistema.

### 🛡️ Modo Silencioso (Sin Ventanas)
Si desea que Hecos se ejecute completamente en segundo plano sin ventanas de terminal visibles:
1. **Usar el Icono de Bandeja**: Inicie Hecos a través del icono de la barra de sistema. Gestionará los componentes del sistema de forma invisible en segundo plano.
2. **Inicio Silencioso**: Use `START_HECOS_SILENT_WIN.vbs` para un inicio 100% invisible (sin ventanas de consola).
3. **Recuperación Manual**: Si cierra accidentalmente el icono, use `START_HECOS_TRAY_WIN.bat`.

---

## 💻 Compatibilidad de Plataforma y Sistemas Operativos

Aunque muchos paquetes de extensión en el ecosistema Hecos (como **Browser Automation**, **Messenger**, **Calendar**, **Weather Pro**, **Mail**, **Image Gen**, **Reminder**, **Lists**, **Maps** y **Quick Links**) son completamente multiplataforma y están diseñados para funcionar en Linux y macOS, **el sistema central de Hecos actualmente solo se ha probado de forma exclusiva en Windows 10 y 11**.

Ejecutar el sistema central en Linux o macOS es posible, pero puede requerir ajustes manuales, y ciertas funciones nativas avanzadas (como la inspección de la interfaz de usuario en PC Automation) son exclusivas de Windows por diseño.

---

## 🛠️ Requisitos del Sistema Esenciales (Windows)
Si acabas de reinstalar Windows o estás configurando Hecos por primera vez, debes asegurarte de que estos paquetes de sistema **fundamentales** estén presentes para que todos los módulos funcionen correctamente.

💡 **NUEVO (v0.45.0 - EDM)**: ¡Hecos ahora integra un **External Dependency Manager (EDM)**! Si faltan Tesseract, Node.js o VC++ Redistributable, el EDM los detectará automáticamente y te permitirá descargarlos en segundo plano con un solo clic desde la WebUI, directamente desde el repositorio de GitHub `Hecos-Dependencies`. Alternativamente, puedes instalarlos manualmente:

1. ⚙️ **Microsoft Visual C++ Redistributable (Obligatorio)**
   - *Para qué sirve*: Requerido por el motor de Memoria RAG (ONNX/FastEmbed). Sin este paquete recibirás errores de DLL faltantes y la búsqueda de documentos no funcionará.
   - *Descarga*: 👉 [Descargar VC++ Redist x64](https://aka.ms/vs/17/release/vc_redist.x64.exe)

2. 🎵 **VLC Media Player 64-bit (Obligatorio)**
   - *Para qué sirve*: El motor de Audio y el Reproductor de Medios integrado de Hecos utilizan las librerías de VLC en segundo plano para reproducir música, alarmas y salida de voz TTS.
   - *Descarga*: 👉 [Descargar VLC 64-bit](https://www.videolan.org/vlc/download-windows.html)

3. 👁️ **Tesseract OCR (Recomendado para la Visión)**
   - *Para qué sirve*: Necesario para las capacidades visuales avanzadas y para leer texto en la pantalla a través de OCR (`pytesseract`).
   - *Descarga*: 👉 [Descargar Tesseract OCR para Windows](https://github.com/UB-Mannheim/tesseract/wiki)

4. 🟢 **Node.js (Recomendado / Requerido para el desarrollo y compilación del Canvas)**
   - *Para qué sirve*: Necesario para compilar y gestionar las dependencias del módulo del Editor Visual de Flujos (ReactFlow/Vite). Si necesitas recompilar el frontend del canvas (`npm run build`), se requiere Node.js.
   - *Descarga*: 👉 [Descargar Node.js LTS](https://nodejs.org/)

---

### 📦 Instalación Offline (Carpeta `dependencies`)
Para tu comodidad, todos los paquetes de instalación necesarios están incluidos offline directamente en la carpeta `dependencies/` en la raíz del proyecto:
* `dependencies/VC_redist.x64.exe` -> Microsoft Visual C++ Redistributable (ONNX/RAG)
* `dependencies/node-v24.16.0-x64.msi` -> Node.js LTS (Canvas / Frontend Build)
* `dependencies/tesseract-ocr-w64-setup-5.5.0.20241111.exe` -> Tesseract OCR (Visión)

*Note: Recomendamos encarecidamente instalar estos componentes antes de iniciar la configuración automática de Hecos.*

---

## 🧠 Backends de IA Soportados (Motores LLM)

Hecos está completamente fuera de línea por defecto y requiere un motor de IA local para procesar lógica y conversación. Durante la configuración, debes instalar uno de los backends independientes a continuación. Hecos los detectará automáticamente.

### 🔹 1. Ollama (Recomendado)
Fácil de usar, rápido y optimizado para ejecutarse localmente como servicio en segundo plano.
- **Descarga**: 👉 https://ollama.com/download
- **Configuración**: Once instalado, abre tu terminal/símbolo del sistema y ejecuta `ollama run llama3.2` para descargar y probar un modelo ligero y rápido. Hecos lo detectará al instante.

### 🔹 2. Llama.cpp (Alternativa)
El estándar de oro para ejecutar modelos locales sin procesar con máxima eficiencia y personalización.
- **Configuración**: Inicie su servidor `llama.cpp` en su puerto predeterminado. Hecos es totalmente compatible y enrutará las solicitudes a través de su proxy interno.

### 🔹 3. KoboldCpp (Alternativa)
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

Puedes instalar nuevos paquetes dinámicamente arrastrando y soltando archivos `.hpkg` en el **Package Manager** dentro de la WebUI. Estos paquetes independientes contienen su propia lógica, paneles de interfaz de usuario y esquemas de configuración, haciendo que Hecos sea infinita y universalmente extensible. Todos los paquetes se verifican mediante firmas digitales Ed25519 para una seguridad absoluta.

---

## 💾 Sistemas de Memoria y Voz

### 🗄️ Sistema de Memoria
Hecos incluye una capa de memoria persistente impulsada por SQLite para un almacenamiento local ligero. Almacena conversaciones, mantiene la identidad y guarda las preferencias del usuario.

### 🎙️ Sistema de Voz
* **Entrada Speech-to-text** (voz a texto)
* **Salida Text-to-speech Avanzado** (Con Kokoro TTS y Piper TTS para generar voces locales naturales y de alta fidelidad)
* **Interacción en tiempo real**

---

## 🔗 Integraciones y Privacidad

### 🤝 Integraciones
Hecos puede integrarse con:
* **Open WebUI** (chat + streaming)
* **Home Assistant** (vía bridge)

### 🔐 Privacidad Primero
Hecos está diseñado con un enfoque estricto en la utilidad y la discreción: funciona 100% localmente, no cuenta con servicios en la nube obligatorios y ofrece un control total sobre tus datos.

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
Hecos utiliza un sistema de documentación modular localizado en EN, IT y ES.

### Acceso Local (Modular)
Las guías detalladas se encuentran en la carpeta `docs/`:
- 📖 **[Guía Unificada (ESP)](docs/UNIFIED_GUIDE_ESP.md)**: Todo lo que necesitas saber sobre la v0.44.0.
- 🏗️ **[Guía Técnica](docs/tech/)**: (Admin/Dev) Detalles de la arquitectura del sistema y OOP.

### Acceso Online
La documentación también se sincroniza con la **[GitHub Wiki](https://github.com/Hecos-Project/Hecos/wiki)**.

---

## 💡 Visión
Hecos aspira a convertirse en una plataforma de asistencia de IA local totalmente autónoma: una alternativa privada y extensible a los sistemas de IA basados en la nube, enfocada exclusivamente en servir y mejorar la vida humana.