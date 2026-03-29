# 🌌 Proyecto Zentra Core
<p align="center">
  <img src="https://raw.githubusercontent.com/Zentra-Core/zentra-core.github.io/main/assets/Zentra_Core_Logo.jpg" width="400" alt="Logo de Zentra">
</p>

# Zentra Core - Versión 0.9.7 (Runtime Alpha)
Idiomas: [English](README.md) | [Italiano](README_ITA.md) | [Español](README_ESP.md)

# 🤖 Zentra Core
**Tu Asistente de IA Personal Offline (Privado, Modular, Potente)**

---

> [!WARNING]
> **Estado Runtime Alpha**: Zentra Core se encuentra actualmente en una fase inicial **Alpha**. Está en desarrollo activo y depuración. Las funciones pueden cambiar y el sistema aún no se considera estable. Usar con precaución.

## 🚀 Resumen General
**Zentra Core** es una plataforma de asistencia de IA "local-first" que se ejecuta íntegramente en tu propia máquina.
Combina LLMs locales, interacción por voz, automatización del sistema y una arquitectura de plugins modulares para crear un compañero digital totalmente personalizable.

Ahora completamente migrado a una **arquitectura estable de Plugins Nativos**, Zentra 0.9.7 ofrece una interfaz Web dedicada (Chat + Config) e internacionalización completa. Gracias a **LiteLLM**, soporta Ollama, KoboldCpp y los principales proveedores de la nube con streaming en tiempo real y TTS local.

---

## ✨ Características Principales (v0.9.7)
* 👁️ **Soporte de Visión Nativa** — Capacidades de IA multimodal para Gemini, OpenAI y Ollama (LLaVA). Analizza immagini, foto e captures de pantalla directamente en el chat.
* 🎨 **Generación de Imágenes** — Genera contenido visual a partir de prompts de texto mediante servidores de IA externos (Integrado vía Pollinations.ai).
* 🏗️ **Plugin WebUI Nativo** — Migrado de un bridge a un plugin core (`plugins/web_ui/`) para máximo rendimiento y estabilidad.
* 🌐 **I18N Global (Multilingüe)** — Soporte completo para Inglés (default) e Italiano en Terminal e interfaz Web con cambio en tiempo real.
* 🧠 **Streaming Multi-Nube** — Soporte nativo para Groq, OpenAI, Gemini e Anthropic con efecto "máquina de escribir".
* 🔄 **Live-Sync Config** — Cambia cualquier ajuste en el Panel Web y aplícalo al instante sin reiniciar el sistema.
* 🎙️ **Chat de Voz Integrado** — Interfaz de Chat nativa con integración de Piper TTS y reproducción de audio automática.
* 🔌 **Botones Macro de Plugins** — La lista de plugins lateral ahora incluye macros clicables para inyectar comandos especializados al instante.
* 💾 **Memoria Persistente** — Memoria SQLite con contexto compartido entre WebUI y Terminal.
* 🚀 **Lanzador Standalone** — Archivo `run_zentra_web.bat` dedicado para iniciar el servidor Web de forma independiente.

---

## 🧠 Cómo Funciona
Zentra Core está construido en torno a una arquitectura modular:
* **Core** → Enrutamiento de IA, procesamiento y ejecución.
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

## 🧠 Backends de IA Soportados

### 🔹 Ollama
Fácil de usar, rápido y optimizado. Recomendado para la mayoría de los usuarios.

👉 https://ollama.com

### 🔹 KoboldCpp
Soporta modelos GGUF, puede ejecutar modelos sin censura, más flexible.

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
Licencia MIT (lanzamiento inicial)

---

## 👥 Créditos y Contacto
Líder de Desarrollo: Antonio Meloni (Tony)
Email Oficial: zentra.core.systems@gmail.com

---

## 📚 Documentación Técnica
- 🏗️ **[Guía de Arquitectura](docs/TECHNICAL_GUIDE.md)**
- 🔌 **[Desarrollo de Plugins](docs/PLUGINS_DEV.md)**
- 📁 **[Mapa de Estructura](docs/zentra_core_structure_v0.9.7.md)**

---

## 💡 Visión
Zentra Core aspira a convertirse en una plataforma de asistencia de IA local totalmente autónoma: una alternativa privada y extensible a los sistemas de IA basados en la nube.