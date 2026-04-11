# 🏗️ 1. Architettura di Sistema

Zentra Core è progettato con un'architettura modulare e scalabile, basata su principi di programmazione orientata agli oggetti (OOP).

- **Core Engine**: Il cuore del sistema che gestisce l'orchestrazione dei plugin, il caricamento delle configurazioni e il ciclo di ragionamento dell'Agente.
- **Plugin System**: Un'infrastruttura dinamica che permette l'estensione delle capacità IA senza modificare il nucleo centrale.
- **OS Adapter**: Uno strato di astrazione che garantisce la compatibilità cross-platform (Windows, Linux, macOS).
- **WebUI Backend**: Un server Flask integrato che espone API REST per l'interfaccia grafica.
