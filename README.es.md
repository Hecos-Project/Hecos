# 🤖 Aura Core

**Tu asistente de IA local (privado, modular y potente)**

---

## 🌍 Idiomas disponibles

* 🇬🇧 Inglés → ver `README.md`
* 🇮🇹 Italiano → ver `README.it.md`
* 🇪🇸 Español (este archivo)

---

## 🚀 ¿Qué es Aura Core?

**Aura Core** es una plataforma de asistente de inteligencia artificial que funciona completamente en local en tu ordenador.

Combina modelos de lenguaje (LLM), automatización del sistema, interacción por voz y un sistema de plugins para crear un asistente totalmente personalizable.

A diferencia de las IA en la nube:

* 🔒 tus datos permanecen en tu dispositivo
* ⚙️ tienes control total
* 🧠 puedes usar modelos sin restricciones (según configuración)

---

## ✨ Características principales

* 🧠 **IA local** — todo se ejecuta en tu hardware
* 🔄 **Soporte de doble backend** — compatible con Ollama y KoboldCpp
* 🎙️ **Interacción por voz** — escucha y responde
* ⚙️ **Control del sistema** — abre aplicaciones, gestiona archivos, ejecuta comandos
* 🔌 **Sistema de plugins** — amplía fácilmente las funcionalidades
* 💾 **Memoria persistente** — almacenamiento con SQLite
* 🌐 **Interacción web** — abre sitios y realiza búsquedas
* 🖥️ **Monitorización del hardware** — CPU, RAM, GPU
* 🔗 **Integraciones** — compatible con Open WebUI y Home Assistant

---

## 🧠 ¿Cómo funciona?

Aura está construida con una arquitectura modular:

* **Core** → lógica principal, gestión de IA y ejecución
* **Plugins** → acciones y capacidades
* **Memoria** → identidad y almacenamiento persistente
* **UI** → interacción con el usuario
* **Bridge** → integraciones externas

La IA genera comandos estructurados que los plugins interpretan y ejecutan.

---

## ⚡ Inicio rápido

### 1. Clonar el repositorio

```bash id="sp1"
git clone https://github.com/your-username/aura-core.git
cd aura-core
```

### 2. Instalar dependencias

```bash id="sp2"
pip install -r requirements.txt
```

### 3. Ejecutar Aura

```bash id="sp3"
python main.py
```

---

## 🧠 Backends de IA soportados

### 🔹 Ollama

* fácil de usar
* rápido
* recomendado para empezar

👉 https://ollama.com

### 🔹 KoboldCpp

* soporta modelos GGUF
* permite modelos sin censura
* mayor flexibilidad

---

## 🔌 Sistema de Plugins

Aura utiliza una arquitectura basada en plugins.

Cada plugin puede:

* añadir comandos
* interactuar con el sistema
* extender las capacidades de la IA

### Plugins incluidos:

* control del sistema
* gestor de archivos
* web
* monitor de hardware
* multimedia
* gestión de modelos
* memoria

---

## 💾 Sistema de memoria

Aura incluye un sistema de memoria persistente:

* guarda conversaciones
* mantiene identidad
* recuerda preferencias del usuario

Basado en SQLite para ser ligero y eficiente.

---

## 🎙️ Sistema de voz

* entrada por voz
* salida por voz
* interacción en tiempo real

---

## 🔗 Integraciones

Aura puede integrarse con:

* Open WebUI
* Home Assistant

---

## 🔐 Privacidad

Aura está diseñada con enfoque en la privacidad:

* funciona 100% en local
* sin servicios en la nube obligatorios
* control total de los datos

---

## 🛣️ Hoja de ruta

* 📱 integración con Telegram
* 🧠 memoria avanzada
* 🤖 sistema multi-agente
* 🛒 marketplace de plugins
* 🎨 mejoras de interfaz

---

## ⚠️ Aviso

Aura puede ejecutar comandos a nivel de sistema.

Úsala con responsabilidad. El autor no se hace responsable de daños o usos indebidos.

---

## 📜 Licencia

MIT (versión inicial)

---

## 👤 Autor

Antonio Meloni (Tony)

---

## 💡 Visión

Aura Core quiere convertirse en una plataforma completa de asistentes de IA locales:

una alternativa privada, modular y potente frente a las soluciones en la nube.

---
