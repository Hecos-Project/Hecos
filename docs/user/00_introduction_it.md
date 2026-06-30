# 🪐 1. Benvenuti in Hecos

> 💡 Hecos è il tuo compagno quotidiano. Puoi parlargli di quello che vuoi; può controllare il tuo computer, inviare messaggi e, grazie alla sua funzione nativa di cambio personalità, può fare da maggiordomo, da amico o persino da partner virtuale. Hai bisogno che funzioni senza l'IA? Nessun problema — Hecos esegue potenti flussi di automazione, risponde ai comandi diretti e gestisce il tuo calendario, i promemoria, le piattaforme di messaggistica, gli account email e le liste in completa autonomia.

🛠️ **Sotto il cofano (Per sviluppatori e utenti avanzati):** Ora in fase di avanzamento verso la `v0.36.0 Alpha`, Hecos si è evoluto in una piattaforma modulare distribuita a tutti gli effetti. L'ecosistema presenta un'architettura **Client-Server disaccoppiata** composta da un Core CLI headless (il server backend) e un'interfaccia WebUI avanzata (il client). Il sistema sincronizza una vista Chat interattiva, una **Control Room** in tempo reale alimentata da widget di telemetria live e **Hecos Flows**—un motore di automazione visiva che esegue flussi di lavoro con o senza il carico computazionale degli LLM.

Le utilità infrastrutturali includono un pannello di configurazione unificato (**Central Hub**), un file manager remoto sicuro, un sistema di routing proxy integrato, **Comandi Diretti** granulari, pipeline vocali dinamiche con VAD e un motore di backup centralizzato. Le estensioni sono gestite nativamente tramite l'**Hecos Package Manager (HPM)**, prelevando componenti `.hpkg` indipendenti direttamente dal nuovo **Hecos Store** integrato.

![Hecos - Helping Companion System](https://github.com/Hecos-Project/Hecos-Assets/blob/main//Urania_9800_Logo.png?raw=true)

## 👤 Cos'è Hecos?
Molto più di un semplice chatbot, Hecos è un **Layer Agentico** per il tuo computer. Seguendo il paradigma "LLM come CPU" (LLM-as-CPU), Hecos agisce come l'orchestratore principale, gestendo la memoria, strumenti specializzati e profili cognitivi per assisterti in flussi di lavoro complessi—dalla gestione avanzata dei file all'esecuzione di codice locale.

## 🧠 Architettura Core: Modulare ed Estensibile
Il cuore di Hecos risiede nella sua **Modularità**. Ogni funzione—che sia un motore di Visione specializzato, un motore di ricerca Web o uno strumento personalizzato—è un componente collegabile. Questo permette a Hecos di crescere e adattarsi al panorama dell'IA in rapida evoluzione senza vincoli legacy.

Le estensioni, le app e le patch sono pacchettizzate in pacchetti `.hpkg` indipendenti distribuiti attraverso l'ecosistema.

## 🗣️ Interazione Multi-Modale e Contesto
Hecos colma il divario tra uomo e macchina attraverso interfacce ad alta fedeltà e una gestione nativa del contesto:
- **Pipeline Vocale Neurale**: Utilizzando il "Push-to-Talk" a bassa latenza e TTS/VAD avanzati, puoi utilizzare il sistema interamente tramite la voce.
- **Personas Cognitive**: Hecos può scambiare la sua "Persona" o profilo cognitivo all'istante, adattando il suo tono, la sua base di conoscenza e i permessi di accesso agli strumenti.
- **Memoria Semantica RAG**: Un caveau avanzato di memoria semantica basato su vettori che consente al sistema di memorizzare, richiamare e contestualizzare le interazioni in modo sicuro e permanente.

## 🖥️ Due Facce della Stessa Medaglia: Console e WebUI
Hecos è un sistema moderno che offre due modi per interagire:
1. **Hecos Console (Il Cuore)**: Questa è la finestra di comando che vedi quando avvii il programma. È dove il sistema "pensa", esegue i controlli di sicurezza e ti permette di gestire tutto rapidamente usando la tastiera.

![Hecos - Helping Companion System](https://github.com/Hecos-Project/Hecos-Assets/blob/main///Hecos_Core_001_1.png?raw=true)

2. **WebUI (Il Volto)**: Questa è l'interfaccia moderna che apri nel tuo browser. Qui puoi chattare visivamente, inviare immagini e configurare ogni dettaglio con una semplice e intuitiva interfaccia grafica.

![Hecos - Helping Companion System](https://github.com/Hecos-Project/Hecos-Assets/blob/main////001_HecosPortal_001.png?raw=true)

## 🏛️ I Cinque Pilastri della WebUI
La WebUI di Hecos è elegantemente suddivisa in cinque aree principali, ciascuna con uno scopo specifico:
- **La Chat** — L'interfaccia conversazionale principale dove parli con Hecos, invii immagini e lanci comandi.

![Hecos - Helping Companion System](https://github.com/Hecos-Project/Hecos-Assets/blob/main///003_HecosChat_001.png?raw=true)

- **Central Hub** — Il centro di configurazione e gestione. Installa pacchetti, preleva estensioni ufficiali dall'**Hecos Store**, regola le impostazioni e gestisci gli utenti.

![Hecos - Helping Companion System](https://github.com/Hecos-Project/Hecos-Assets/blob/main////008_HecosCentralHub_002.png?raw=true)

- **Control Room** — Una dashboard live in cui i widget interattivi vengono eseguiti fianco a fianco per fornire telemetria in tempo reale, monitoraggio del sistema, visione hardware e informazioni sul calendario all'utente.

![Hecos - Control Room ](https://github.com/Hecos-Project/Hecos-Assets/blob/main////005_HecosChat_Direct_ControlRoom_integrata.png?raw=true)

- **Flows** — Il builder visuale di automazioni. Crea routine, cicli e automazioni complesse concatenando nodi funzionali tra loro, con esecuzione con o senza l'ausilio dell'IA.

![Hecos - Helping Companion System](https://github.com/Hecos-Project/Hecos-Assets/blob/main////012_Hecos_Flows_003.png?raw=true)

- **Hecos Drive** — Il file explorer remoto, gestore e editor di codice integrato, condiviso simmetricamente tra te e l'IA.

![Hecos - Helping Companion System](https://github.com/Hecos-Project/Hecos-Assets/blob/main////016_Hecos_Drive_FileManager_002.png?raw=true)

## 🔌 Moduli di Sistema Integrati
Hecos include moduli nativi e robusti pronti all'uso per controllare il tuo spazio di lavoro:
- **Automazione PC e Browser**: Integrazione profonda con il sistema operativo ed esecuzione di cicli di controllo del browser per gestire attività, estrarre dati e scrivere script per azioni in modo nativo.
- **Ponti di Messaggistica ed Integrazioni Email**: Moduli dedicati per orchestrare le comunicazioni in entrata e in uscita su più reti di chat e configurazioni email in modo trasparente.
- **Backup Centralizzato** — Una soluzione con un clic per archiviare in sicurezza l'intera configurazione, i file del workspace, i moduli installati e le memorie.
- **Hecos Proxy** — Un proxy di routing locale integrato per aggirare le restrizioni web e connettere in modo sicuro i moduli isolati a Internet.

## 🔒 Privacy e Intelligenza Locale
A differenza di molti assistenti popolari, Hecos mette la tua privacy al primo posto. Molte delle sue funzionalità sono progettate per essere eseguite direttamente sul tuo computer (**localmente** tramite strumenti come Ollama o KoboldCpp). Questo significa che i tuoi dati, i tuoi caveau di memoria semantica e le tue conversazioni rimangono con te, senza viaggiare necessariamente su Internet.

---
*Pronto? Inizia esplorando il capitolo successivo per muovere i tuoi primi passi con Hecos!*
