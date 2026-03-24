# 🌌 Proyecto Zentra Core
<p align="center">
  <img src="https://raw.githubusercontent.com/Zentra-Core/zentra-core.github.io/main/assets/Zentra_Core_Logo.jpg" width="400" alt="Logo de Zentra">
</p>

# Zentra Core - Versión 0.9.5 (Desarrollo Activo)
Idiomas: [English](README.md) | [Italiano](README_ITA.md) | [Español](README_ESP.md)

# 🤖 Zentra Core
**Tu Asistente de IA Personal Offline (Privado, Modular, Potente)**

---

## 🚀 Resumen General
**Zentra Core** es una plataforma de asistencia de IA "local-first" que se ejecuta íntegramente en tu propia máquina.
Combina LLMs locales, interacción por voz, automatización del sistema y una arquitectura de plugins modulares para crear un compañero digital totalmente personalizable.

A diferencia de las IA en la nube:
* 🔒 **Tus datos permanecen en tu dispositivo**
* ⚙️ **Tienes control total**
* 🧠 **Puedes usar modelos sin restricciones** (según configuración)

Con la integración de **LiteLLM**, Zentra ahora soporta no solo Ollama y KoboldCpp, sino también los principales proveedores de la nube (OpenAI, Anthropic, Gemini, Groq) para la máxima flexibilidad.

---

## ✨ Características Principales
* 🧠 **Procesamiento de IA Local y Cloud** — Soporta Ollama, KoboldCpp y LiteLLM (OpenAI, Groq, etc.).
* 🔄 **Soporte de Multi-Backend** — Cambia sin problemas entre modelos locales y en la nube.
* 🎙️ **Interacción por Voz Multilingüe** — Entrada y salida de voz con selección automática de idioma (ES/EN/IT).
* ⚙️ **Control del Sistema** — Ejecuta comandos, abre aplicaciones, gestiona archivos.
* 🔌 **Sistema de Plugins** — Funcionalidades fácilmente extensibles.
* 💾 **Memoria Persistente** — Memoria a largo plazo basada en SQLite.
* 🖥️ **Telemetría Avanzada** — Estadísticas de hardware (CPU, RAM, GPU) y registro mejorado.
* 🔗 **Listo para Integración** — Funciona con Open WebUI y Home Assistant.

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

## 💡 Visión
Zentra Core aspira a convertirse en una plataforma de asistencia de IA local totalmente autónoma: una alternativa privada y extensible a los sistemas de IA basados en la nube.