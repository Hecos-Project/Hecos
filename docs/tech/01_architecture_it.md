# 🏗️ 1. Architettura di Sistema

Hecos è progettato con un'architettura modulare e scalabile, basata su principi di programmazione orientata agli oggetti (OOP) e su un ecosistema di pacchetti indipendenti.

- **Core Engine**: Il cuore del sistema che gestisce l'orchestrazione dei moduli, il caricamento delle configurazioni crittografate e il ciclo di ragionamento dell'Agente tramite l'adapter LLM.
- **Hecos Package Manager (HPM)**: L'infrastruttura dinamica fondamentale che permette l'espansione del sistema. Tramite HPM, Hecos installa **Moduli** (pacchetti in formato `.hpkg` firmati con chiavi Ed25519). Un modulo può essere:
  - **Plugins & Core Modules**: Integrazioni IA native (automazione OS, generazione immagini, ecc).
  - **Autonomous Apps**: Applicazioni web complete che girano interamente in locale dentro l'ecosistema.
  - **Control Room Widgets**: Strumenti per la dashboard di sistema e la telemetria in tempo reale.
  - **Personas & Themes**: Pacchetti per personalizzare l'aspetto visivo e il comportamento dell'agente.
- **OS Adapter**: Uno strato di astrazione che garantisce la compatibilità cross-platform (Windows, Linux, macOS).
- **WebUI Backend**: Un server Flask integrato che ospita l'interfaccia nativa, il Central Hub e instrada dinamicamente le API e gli asset dei pacchetti HPM.
