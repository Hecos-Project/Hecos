# 💬 Chat & UI

> *"L'interfaccia conversazionale principale dove parli con Hecos, invii immagini e lanci comandi. Un nesso cibernetico che collega il tuo core locale al cloud."*
> — Tour WebUI Hecos

La **Chat** è l'interfaccia principale della WebUI di Hecos. Fornisce un ambiente ricco e moderno per interagire con la tua IA.

![Hecos Chat Interface](https://github.com/Hecos-Project/Hecos-Assets/blob/main/Hecos_ImageGen_Module_1.png?raw=true)

---

### 🎛️ PANORAMICA DEL SISTEMA

---

## Funzionalità Principali
- **Testo Ricco e Codice:** Supporta il rendering completo di Markdown, tabelle e blocchi di codice con evidenziazione della sintassi.
- **Input Multimodale:** Trascina e rilascia immagini direttamente nella chat per farle analizzare a Hecos usando le sue capacità di Visione.
- **Integrazione Vocale:** Clicca sull'icona del microfono o usa `Ctrl+Shift+Z` per dettare messaggi usando la funzione Push-to-Talk.
- **Cronologia Sessioni:** La barra laterale sinistra ti permette di gestire più conversazioni, rinominarle o eliminarle. Tutte le sessioni sono salvate nel tuo Episodic Memory Vault locale.
- **Modalità Privacy:** Scegli tra Normale (salvata), Auto-Wipe (solo in RAM) o Incognito (nessuna traccia) per ogni conversazione.
- **Comandi Diretti:** Digita `/` nella barra di input per accedere all'HDCS (Hecos Direct Command System) per azioni istantanee senza dialoghi superflui.

---

## 🛠️ Analisi Approfondita: L'Interfaccia Cibernetica

### 1. Barra Laterale Sinistra: Configurazione Neurale
La barra laterale funge da console di telemetria e controllo per la sessione attiva. Muovendosi dall'alto verso il basso:

* **Stato del Sistema**: Diagnostica in tempo reale che mostra il tipo di architettura (backend **Cloud** o **Locale**), il **Nome del Modello** attivo e la matrice della personalità caricata—definita come l'**Anima** (Soul, ad esempio, `Motoko Kusanagi`).
* **Livello di Privacy**: Stati di conversazione blindati dal punto di vista informatico:
    * `Normale`: Operazioni standard, registri persistenti.
    * `Auto-Wipe`: Sessione in memoria volatile; i dati vengono automaticamente eliminati dalla RAM al riavvio del sistema.
    * `Incognito`: Routing oscuro. Nessuna traccia, nessun registro, zero impronte lasciate sul sistema.
* **Griglia Audio**: Pannello di telemetria vocale ad alta fedeltà con tre stati attivabili:
    * `Audio Continuo`: Ascolto persistente in background.
    * `Attivazione Vocale`: Avvia l'elaborazione al rilevamento dell'attività vocale (VAD).
    * `PTT (Push-to-Talk)`: Input a doppia modalità. Clicca sull'icona della chat per passare da standard On/Off a PTT. In alternativa, usa la combinazione di tasti scelta rapida **`Ctrl+Shift`** per attivare una modalità walkie-talkie a livello hardware.
* **Control Room**: Un nodo comprimibile e a comparsa integrato direttamente nella vista chat per gestire i widget attivi, le pipeline dei widget e gli stati ambientali.
* **Link Gestore Pacchetti**: Situato nella parte inferiore della barra laterale, questa scorciatoia bypassa il Central Hub, portandoti direttamente nella matrice di installazione/aggiornamento dei moduli.

![Hecos Chat Interface](https://github.com/Hecos-Project/Hecos-Assets/blob/main/Hecos_Chat_0020.png?raw=true)

### 2. Motore Chat Principale e Terminale Superiore
La vista di elaborazione centrale gestisce il rendering dei dati e il monitoraggio ambientale.

* **Indicatori del Ponte Superiore**: Relè ad accesso rapido che tracciano lo stato del flusso audio insieme ai nodi di macro-navigazione: **Central Hub**, **Drive** (il file manager locale di Hecos) e il **Pannello Flows** per il routing visivo dell'automazione.
* **Indicatore Online**: Un faro di stato centrale che pulsa visivamente per confermare se il core locale o il proxy cloud sta trasmettendo attivamente le risposte.
* **Barra di Input Dinamica e HDCS (Hecos Direct Command System)**: Inizializzando l'input di testo con il carattere **`/`** viene visualizzata istantaneamente la finestra sovrapposta dei Comandi Diretti. 
    
    I comandi possono anche essere attivati tramite sintesi vocale. Dire **"slash"**, **"command"** o **"comando"** seguito dall'identificatore della direttiva attiva immediatamente lo script. 
    
    > *Esempio di Esecuzione:* Pronunciare *"slash souls"* si compila in `/souls`, attivando una stampa diagnostica completa di tutte le personalità dei compagni installate localmente (anime) senza intasare la finestra del contesto di chat.
