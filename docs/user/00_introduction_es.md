# 🪐 Bienvenidos a Hecos

> 💡 Hecos es tu compañero de todos los días. Puedes hablarle de lo que quieras; puede controlar tu computadora, enviar mensajes y, con su función nativa de cambio de personalidad, puede actuar como un mayordomo, un amigo o incluso tu pareja virtual. ¿Necesitas que funcione sin IA? No hay problema — Hecos ejecuta potentes flujos de automatización, responde a comandos directos y gestiona tu calendario, recordatorios, plataformas de mensajería, cuentas de correo electrónico y listas por sí solo de forma totalmente autónoma.

🛠️ **Bajo el capó (Para desarrolladores y usuarios avanzados):** Actualmente avanzando a través de la `v0.36.0 Alpha`, Hecos se ha convertido en una plataforma modular distribuida completa. El ecosistema presenta una arquitectura **Client-Server desacoplada** que consiste en un Core CLI sin interfaz (headless) (el servidor backend) y una WebUI avanzada (el cliente). El sistema sincroniza una vista de chat interactiva, una **Control Room** en tiempo real impulsada por widgets de telemetría en vivo, y **Hecos Flows**—un motor de automatización visual que ejecuta flujos de trabajo con o sin la sobrecarga del LLM.

Las utilidades de infraestructura incluyen un panel de configuración unificado (**Central Hub**), un administrador de archivos remoto seguro, un sistema de enrutamiento proxy integrado, **Comandos Directos** granulares, canales dinámicos de voz/VAD y un motor de copia de seguridad centralizado. Las extensiones se manejan de forma nativa a través del **Hecos Package Manager (HPM)**, obteniendo componentes `.hpkg` independientes directamente de la nueva tienda **Hecos Store** integrada.

![Hecos - Helping Companion System](https://github.com/Hecos-Project/Hecos-Assets/blob/main//Urania_9800_Logo.png?raw=true)

## 👤 ¿Qué es Hecos?
Más que un simple chatbot, Hecos es una **Capa Agéntica** para tu computadora. Siguiendo el paradigma "LLM como CPU" (LLM-as-CPU), Hecos actúa como el orquestador maestro, gestionando la memoria, las herramientas especializadas y los perfiles cognitivos para ayudarte en flujos de trabajo complejos, desde la gestión avanzada de archivos hasta la ejecución de código local.

## 🧠 Architectura Central: Modular y Extensible
El corazón de Hecos radica en su **Modularidad**. Cada función, ya sea un motor de Visión especializado, un buscador web o una herramienta personalizada, es un componente acoplable. Esto permite que Hecos crezca y se adapte al panorama de la IA en rápida evolución sin restricciones de legado.

Las extensiones, aplicaciones y parches se agrupan en paquetes `.hpkg` independientes distribuidos a través del ecosistema.

## 🗣️ Interacción Multimodal y Contexto
Hecos cierra la brecha entre humanos y máquinas a través de interfaces de alta fidelidad y un manejo nativo del contexto:
- **Canal de Voz Neuronal**: Utilizando "Push-to-Talk" de baja latencia y TTS/VAD avanzado, puedes operar el sistema completamente por voz.
- **Personas Cognitivas**: Hecos puede cambiar su "Persona" o perfil cognitivo al instante, adaptando su tono, base de conocimientos y permisos de acceso a herramientas.
- **Memoria Semántica RAG**: Una bóveda avanzada de memoria semántica basada en vectores que permite al sistema almacenar, recordar y contextualizar las interacciones de forma segura y permanente.

## 🖥️ Dos Caras de la Misma Moneda: Consola y WebUI
Hecos es un sistema moderno que ofrece dos formas de interactuar:
1. **Consola Hecos (El Corazón)**: Esta es la ventana de comandos que ves al iniciar el programa. Es donde el sistema "piensa", realiza comprobaciones de seguridad y te permite gestionarlo todo rápidamente con el teclado.

![Hecos - Helping Companion System](https://github.com/Hecos-Project/Hecos-Assets/blob/main///Hecos_Core_001_1.png?raw=true)

2. **WebUI (La Cara)**: Esta es la interfaz moderna que abres en tu navegador. Aquí puedes chatear visualmente, enviar imágenes y configurar cada detalle con una interfaz gráfica sencilla e intuitiva.

![Hecos - Helping Companion System](https://github.com/Hecos-Project/Hecos-Assets/blob/main////001_HecosPortal_001.png?raw=true)

## 🏛️ Los Cinco Pilares de la WebUI
La WebUI de Hecos está elegantemente dividida en cinco áreas principales, cada una con un propósito específico:
- **El Chat** — La interfaz conversacional principal donde hablas con Hecos, envías imágenes y activas comandos.

![Hecos - Helping Companion System](https://github.com/Hecos-Project/Hecos-Assets/blob/main///003_HecosChat_001.png?raw=true)

- **Central Hub** — El centro de configuración y gestión. Instala paquetes, obtén extensiones oficiales de la **Hecos Store**, ajusta la configuración y gestiona usuarios.

![Hecos - Helping Companion System](https://github.com/Hecos-Project/Hecos-Assets/blob/main////008_HecosCentralHub_002.png?raw=true)

- **Control Room** — Un panel interactivo (dashboard) en vivo donde los widgets interactivos se ejecutan simultáneamente para proporcionar telemetría en tiempo real, monitoreo del sistema, visión de hardware e información del calendario al usuario.

![Hecos - Control Room ](https://github.com/Hecos-Project/Hecos-Assets/blob/main////005_HecosChat_Direct_ControlRoom_integrata.png?raw=true)

- **Flows** — El constructor visual de automatización. Crea rutinas, bucles y automatizaciones complejas encadenando nodos funcionales entre sí, ejecutándose con o sin la intervención de la IA.

![Hecos - Helping Companion System](https://github.com/Hecos-Project/Hecos-Assets/blob/main////012_Hecos_Flows_003.png?raw=true)

- **Hecos Drive** — El explorador de archivos remoto, administrador y editor de código integrado, compartido de forma simétrica entre tú y la IA.

![Hecos - Helping Companion System](https://github.com/Hecos-Project/Hecos-Assets/blob/main////016_Hecos_Drive_FileManager_002.png?raw=true)

## 🔌 Módulos de Sistema Integrados
Hecos incluye módulos nativos y robustos listos para usar para controlar tu espacio de trabajo:
- **Automatización de PC y Automatización de Navegador**: Conexión profunda con el sistema operativo y ciclos de ejecución de control del navegador para manejar tareas, extraer datos y programar acciones de forma nativa.
- **Puentes de Mensajería e Integraciones de Correo**: Módulos dedicados para orquestar comunicaciones entrantes y salientes a través de múltiples redes de chat y configuraciones de correo electrónico sin problemas.
- **Copia de Seguridad Centralizada** — Una solución de un solo clic para almacenar de forma segura toda tu configuración, archivos de espacio de trabajo, módulos instalados y recuerdos.
- **Hecos Proxy** — Un proxy de enrutamiento local integrado para evitar restricciones web y conectar módulos aislados de forma segura a Internet.

## 🔒 Privacidad e Inteligencia Local
A diferencia de muchos asistentes populares, Hecos prioriza tu privacidad. Muchas de sus características están diseñadas para ejecutarse directamente en tu computadora (**localmente** a través de herramientas como Ollama o KoboldCpp). Esto significa que tus datos, bóvedas de memoria semántica y conversaciones permanecen contigo, sin necesidad de viajar por Internet.

---
*¿Listo? ¡Comienza explorando el próximo capítulo para dar tus primeros pasos con Hecos!*
