from pathlib import Path

wiki_dir = Path(r"C:\Hecos-Wiki")

# 1. English
en_path = wiki_dir / "00_introduction_en.md"
en_content = en_path.read_text(encoding="utf-8")

old_en_block = """## 🔌 Built-in System Modules
Hecos includes native, robust modules ready out of the box to control your workspace:
- **PC Automation & Browser Automation**: Deep operating system bridging and browser control execution loops to handle tasks, extract data, and script actions natively.
- **Messenger Bridges & Mail Integrations**: Dedicated modules to orchestrate incoming and outgoing communications across multiple chat networks and email setups seamlessly.
- **Centralized Backup** — A one-click solution to safely store your entire configuration, workspace files, installed modules, and memories.
- **Hecos Proxy** — An integrated local routing proxy to bypass web restrictions and securely connect isolated modules to the internet."""

new_en_block = """## 📦 Modular Architecture & The Hecos Store

While essential baseline services such as the **Hecos Proxy** (for secure local routing and module network isolation) and the **Presenter** (real-time voice briefings, event commentary, and live logging) remain natively integrated into the Core engine, Hecos is built around an infinitely extensible modular ecosystem managed by the **Hecos Package Manager (HPM)**.

Nearly all platform capabilities are distributed as standalone, sandboxed `.hpkg` packages:
- **PC & Browser Automation**: Deep operating system bridging, window control, and web scraping loops.
- **Net Search**: Autonomous uncensored retrieval across the clear and dark web.
- **Communications**: Multi-network Messenger bridges and Mail orchestration.
- **Productivity & Office**: Dynamic Lists, Reminders, Calendar, Document Reader, and Document Maker suites.
- **System Tooling**: Centralized Backup snapshots, SysNet tools, and Control Room telemetry widgets.
- **Intelligence & Training**: Interactive Playbooks (guided training, language coaching, roleplays) and custom Soul presets.

👉 **Explore & Update:** For new extensions, community add-ons, and package updates, browse the official **[Hecos Store](https://hecos-project.github.io/store/)** directly inside the WebUI or via the online catalog."""

if old_en_block in en_content:
    en_content = en_content.replace(old_en_block, new_en_block)
    en_path.write_text(en_content, encoding="utf-8")
    print("[OK] Updated 00_introduction_en.md")
else:
    print("[!] Warning: old_en_block not found in 00_introduction_en.md")

# 2. Italian
it_path = wiki_dir / "00_introduction_it.md"
it_content = it_path.read_text(encoding="utf-8")

old_it_block = """## 🔌 Moduli di Sistema Integrati
Hecos include moduli nativi e robusti pronti all'uso per controllare il tuo spazio di lavoro:
- **Automazione PC e Browser**: Integrazione profonda con il sistema operativo ed esecuzione di cicli di controllo del browser per gestire attività, estrarre dati e scrivere script per azioni in modo nativo.
- **Ponti di Messaggistica ed Integrazioni Email**: Moduli dedicati per orchestrare le comunicazioni in entrata e in uscita su più reti di chat e configurazioni email in modo trasparente.
- **Backup Centralizzato** — Una soluzione con un clic per archiviare in sicurezza l'intera configurazione, i file del workspace, i moduli installati e le memorie.
- **Hecos Proxy** — Un proxy di routing locale integrato per aggirare le restrizioni web e connettere in modo sicuro i moduli isolati a Internet."""

new_it_block = """## 📦 Architettura Modulare & L'Ecosistema dello Store

Mentre i servizi essenziali di base come l'**Hecos Proxy** (per il routing locale sicuro e l'isolamento di rete dei moduli) e il **Presenter** (briefing vocali in tempo reale, commento eventi e logging) rimangono nativamente integrati nel motore Core, Hecos è progettato attorno a un ecosistema infinitamente estendibile gestito dall'**Hecos Package Manager (HPM)**.

La quasi totalità delle capacità della piattaforma è distribuita sotto forma di pacchetti autonomi e isolati in formato `.hpkg`:
- **Automazione PC & Browser**: Integrazione profonda con il sistema operativo, controllo finestre e flussi di automazione web.
- **Net Search**: Motore autonomo di ricerca e recupero file senza censure su clear e dark web.
- **Comunicazione**: Ponti Messenger multi-network e orchestrazione della posta elettronica.
- **Produttività & Ufficio**: Liste dinamiche, Promemoria, Calendario, Document Reader e suite Document Maker.
- **Strumenti di Sistema**: Backup centralizzato con un clic, utility SysNet e widget di telemetria per la Control Room.
- **Intelligenza & Training**: Playbook interattivi (simulazioni guidate, personal coach, roleplay) e preset Soul personalizzati.

👉 **Esplora & Aggiorna:** Per scoprire nuovi moduli, temi, estensioni e aggiornamenti ufficiali, consulta l'**[Hecos Store](https://hecos-project.github.io/store/)** direttamente dalla WebUI o tramite il catalogo online."""

if old_it_block in it_content:
    it_content = it_content.replace(old_it_block, new_it_block)
    it_path.write_text(it_content, encoding="utf-8")
    print("[OK] Updated 00_introduction_it.md")
else:
    print("[!] Warning: old_it_block not found in 00_introduction_it.md")

# 3. Spanish
es_path = wiki_dir / "00_introduction_es.md"
es_content = es_path.read_text(encoding="utf-8")

old_es_block = """## 🔌 Módulos de Sistema Integrados
Hecos incluye módulos nativos y robustos listos para usar para controlar tu espacio de trabajo:
- **Automatización de PC y Automatización de Navegador**: Conexión profunda con el sistema operativo y ciclos de ejecución de control del navegador para manejar tareas, extraer datos y programar acciones de forma nativa.
- **Puentes de Mensajería e Integraciones de Correo**: Módulos dedicados para orquestar comunicaciones entrantes y salientes a través de múltiples redes de chat y configuraciones de correo electrónico sin problemas.
- **Copia de Seguridad Centralizada** — Una solución de un solo clic para almacenar de forma segura toda tu configuración, archivos de espacio de trabajo, módulos instalados y recuerdos.
- **Hecos Proxy** — Un proxy de enrutamiento local integrado para evitar restricciones web y conectar módulos aislados de forma segura a Internet."""

new_es_block = """## 📦 Arquitectura Modular y el Ecosistema de la Store

Mientras que los servicios esenciales del sistema como el **Hecos Proxy** (para el enrutamiento local seguro y el aislamiento de red) y el **Presenter** (informes de voz en tiempo real, comentarios de eventos y registro) permanecen integrados de forma nativa en el motor Core, Hecos está diseñado en torno a un ecosistema infinitamente extensible gestionado por el **Hecos Package Manager (HPM)**.

La gran mayoría de las capacidades de la plataforma se distribuyen como paquetes `.hpkg` autónomos y aislados:
- **Automatización de PC y Navegador**: Conexión profunda con el sistema operativo, control de ventanas y flujos de automatización web.
- **Net Search**: Motor autónomo de búsqueda y recuperación de archivos sin censura en la web abierta y dark web.
- **Comunicaciones**: Puentes de Messenger multirred y orquestación de correo electrónico.
- **Productividad y Oficina**: Listas dinámicas, Recordatorios, Calendario, Document Reader y suite Document Maker.
- **Herramientas del Sistema**: Copia de seguridad centralizada con un solo clic, utilidades SysNet y widgets de telemetría para la Control Room.
- **Inteligencia y Entrenamiento**: Playbooks interactivos (simulaciones guiadas, coaching, roleplay) y perfiles Soul personalizados.

👉 **Explora y Actualiza:** Para descubrir nuevos paquetes, extensiones y actualizaciones oficiales, visita la **[Hecos Store](https://hecos-project.github.io/store/)** directamente desde la WebUI o a través del catálogo web."""

if old_es_block in es_content:
    es_content = es_content.replace(old_es_block, new_es_block)
    es_path.write_text(es_content, encoding="utf-8")
    print("[OK] Updated 00_introduction_es.md")
else:
    print("[!] Warning: old_es_block not found in 00_introduction_es.md")
