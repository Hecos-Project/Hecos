# 🌌 Proyecto Zentra Core
<p align="center">
  <img src="https://raw.githubusercontent.com/Zentra-Core/zentra-core.github.io/main/zentra/assets/Zentra_Core_Logo.jpg" width="400" alt="Logo de Zentra">
</p>

# Zentra Core - Versión 0.18.1 (Runtime Alpha)
Idiomas: [English](README.md) | [Italiano](README_ITA.md) | [Español](README_ESP.md)

# 🤖 Zentra Core
**Tu Asistente de IA Personal Offline (Privado, Modular, Potente)**

---

> [!WARNING]
> **Estado Runtime Alpha**: Zentra Core se encuentra actualmente en una fase temprana **Alpha**. Está bajo desarrollo y depuración activos. Las funciones pueden cambiar y el sistema aún no se considera estable. Usar con precaución.

## 🚀 Resumen General
**Zentra Core** es una plataforma de asistencia de IA "local-first" que se ejecuta íntegramente en tu propia máquina.
Combina LLMs locales, interacción por voz, automatización del sistema y una arquitectura de plugins modulares para crear un compañero digital totalmente personalizable.


---
Ahora completamente migrado a una **arquitectura estable de Plugins Nativos**, Zentra 0.15.2 ofrece una interfaz Web dedicada (Chat + Config) e internacionalización completa. Gracias a **LiteLLM**, soporta Ollama, KoboldCpp y los principales proveedores de la nube con streaming en tiempo real y TTS local.

---

## ✨ Características Principales (v0.18.1)
* 🎨 **Flux Prompt Studio** — Ingeniería de prompts en tiempo real para Flux.1 con persistenza automatica di metadati sidecar.
* 🖼️ **Image Metadata Injection** — Los resultados de IA generativa ahora incluyen archivos sidecar JSON (.txt) con prompt, semilla e info del sampler para flujos profesionales.
* 🎭 **Chat UI Mejorada** — Nuevos encabezados de chat con nombres de Usuario/Persona, marcas de tiempo y mejor posición de botones (Copiar/Editar/Regenerate).
* 🔄 **Regeneración Corregida** — Se resolvieron problemas de duplicación de historial y errores de sesión durante la regeneración.
* 🛡️ **Arquitectura de Privacidad de 3 Niveles** — Gestión unificada con modos **Normal**, **Auto-Wipe** (solo RAM) e **Incognito** (sin rastro).
* 🔌 **Universal Tool Hub (MCP Bridge)** — Soporte nativo para el **Model Context Protocol**. Conéctate a miles de herramientas AI con un solo clic.
* 🔭 **Deep MCP Discovery** — Explorador avanzado con búsqueda multi-registro (Smithery, MCPSkills, GitHub) e instalación inmediata.
* 🔒 **Zentra PKI Profesional (HTTPS)** — Certificación Root CA integrada para habilitar Mic/Cámara en toda la LAN de forma segura.
* 🏗️ **Plugin WebUI Nativo** — Interfaz de alto rendimiento optimizada para escritorio y dispositivos móviles.
* 🗂️ **Zentra Drive (File Manager)** — Gestión de archivos y editor integrado con interfaz de doble panel.

---

## 🧠 Cómo Funciona
**Zentra Core está actualmente en `v0.15.2`.** Este repositorio contiene el motor, el backend, los módulos de razonamiento de IA y la WebUI nativa principal.
* **Plugins** → Acciones y capacidades (sistema, web, multimedia, etc.).
* **Memory** → Identidad y almacenamiento persistente.
* **UI** → Capa de interacción con el usuario.
* **Bridge** → Integraciones externas y APIs.

La IA genera comandos estructurados que son interpretados y ejecutados a través del sistema de plugins.

---

## ⚡ Inicio Rápido

### 1. Clonar el repositorio
```bash
git clone https://github.com/Zentra-Core/zentra-core.github.io.git
cd zentra-core.github.io
```

### 2. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 3. Ejecutar Zentra
```bash
python main.py
```

---

## 🧠 Backends de IA Soportados (Motores LLM)

Zentra está completamente fuera de línea por defecto y requiere un motor de IA local para procesar lógica y conversación. Durante la configuración, debes instalar uno de los backends independientes a continuación. Zentra los detectará automáticamente.

### 🔹 1. Ollama (Recomendado)
Fácil de usar, rápido y optimizado para ejecutarse localmente como servicio en segundo plano.
- **Descarga**: 👉 https://ollama.com/download
- **Configuración**: Una vez instalado, abre tu terminal/símbolo del sistema y ejecuta `ollama run llama3.2` para descargar y probar un modelo ligero y rápido. Zentra lo detectará al instante.

### 🔹 2. KoboldCpp (Alternativa)
Perfecto para modelos manuales GGUF y hardware más antiguo sin grandes instalaciones.
- **Descarga**: 👉 https://github.com/LostRuins/koboldcpp/releases
- **Configuración**: Descarga el archivo `.exe` (o el binario de Linux), haz doble clic, selecciona cualquier modelo de instrucciones GGUF descargado de HuggingFace y ejecútalo. Zentra se conectará a través del puerto `5001`.

---

## 🔌 Sistema de Plugins
Zentra utiliza una arquitectura dinámica. Cada plugin puede registrar comandos, ejecutar acciones del sistema y extender las capacidades de la IA.

Plugins incluidos:
* **Control del sistema y Gestor de archivos**
* **Automatización Web y Dashboard de hardware**
* **Control multimedia y Cambio de modelo**
* **Gestión de memoria**

---

## 💾 Sistemas de Memoria y Voz

### 🗄️ Sistema de Memoria
Zentra incluye una capa de memoria persistente impulsada por SQLite para un almacenamiento local ligero. Almacena conversaciones, mantiene la identidad y guarda las preferencias del usuario.

### 🎙️ Sistema de Voz
* **Entrada Speech-to-text** (voz a texto)
* **Salida Text-to-speech** (texto a voz)
* **Interacción en tiempo real**

---

## 🔗 Integraciones y Privacidad

### 🤝 Integraciones
Zentra puede integrarse con:
* **Open WebUI** (chat + streaming)
* **Home Assistant** (vía bridge)

### 🔐 Privacidad Primero
Zentra está diseñado pensando en la privacidad: funciona 100% localmente, sin servicios en la nube obligatorios y con control total sobre los datos.

---

## 🛣️ Hoja de Ruta (Roadmap)
- [ ] 📱 Integración con Telegram (control remoto)
- [ ] 🧠 Sistema de memoria avanzado
- [ ] 🤖 Arquitectura multi-agente
- [ ] 🛒 Marketplace de plugins
- [ ] 🎨 UI/UX mejorada

---

## ⚠️ Descargo de Responsabilidad (Disclaimer)
Zentra puede ejecutar comandos a nivel de sistema y controlar tu entorno. Úsalo con responsabilidad. El autor no se hace responsable del mal uso o de posibles daños.

---

## 📜 Licencia
Licencia GPL-3.0

---

## 👥 Créditos y Contacto
Líder de Desarrollo: Antonio Meloni (Tony)
Email Oficial: zentra.core.systems@gmail.com

---

## 📚 Documentación Técnica
- 🏗️ **[Guía de Arquitectura](docs/TECHNICAL_GUIDE.md)**
- 🔌 **[Desarrollo de Plugins](docs/PLUGINS_DEV.md)**
- 📁 **[Mapa de Estructura](docs/ARCHITECTURE_MAP.md)**

---

## 💡 Visión
Zentra Core aspira a convertirse en una plataforma de asistencia de IA local totalmente autónoma: una alternativa privada y extensible a los sistemas de IA basados en la nube.