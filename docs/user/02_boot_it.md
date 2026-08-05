# 🚀 2. Avvio e Controllo Iniziale

All'avvio dell'eseguibile o dello script Python, Hecos inizia la sua sequenza di **Avvio Sincronizzato**.

### Diagnostica Pre-Avvio
Il sistema verifica di default:
- Integrità delle cartelle vitali (`core/`, `plugins/`, `memory/`, ecc.).
- Stato dell'hardware (CPU e RAM entro i limiti).
- Stato dei moduli Audio e Voce.
- Risposta del server IA (Backend).
- Scansione dei Plugin attivi/disattivati.

### ⚡ Bootstrap One-Click

> [!TIP]
> **Metodo Consigliato — Installa tramite la Tray!** Scarica solo **Hecos Tray** (il pacchetto leggero), avvialo e apri la **Tray Dashboard**. Vai nella scheda **Updates** e clicca su *Manage Core*: il sistema scarica e configura tutto automaticamente. È il metodo più semplice e completo.

> [!IMPORTANT]
> **Percorso di Installazione**: Si consiglia vivamente di estrarre e installare Hecos in una cartella radice come `C:\Hecos`. Evita di installarlo in `Download`, `Desktop` o cartelle molto profonde, poiché percorsi lunghi o con caratteri speciali/spazi possono causare problemi di avvio o funzionalità non operative.

> [!WARNING]
> **Dipendenze di Sistema**: Prima di eseguire la configurazione, assicurarsi di aver installato i redistributable richiesti (come `VC_redist`) presenti nella cartella **`dependencies`**. Se mancano, i componenti principali come i modelli IA e il motore Text-To-Speech non si avvieranno.

**Metodo alternativo (avanzato):** Se hai già il pacchetto Core, usa gli script di avvio universali nella cartella radice:
- **Windows:** `START_SETUP_HERE_WIN.bat`
- **Linux:** `START_SETUP_HERE_LINUX.sh`

Questi script gestiscono automaticamente la verifica dell'ambiente, le dipendenze e avviano la **Procedura Guidata di Configurazione**.

> [!TIP]
> **Avvii Successivi**: Dopo la configurazione iniziale, il modo più veloce e comodo per usare Hecos ogni giorno è avviare la **Hecos Tray**. Fai doppio clic sulla sua icona nella tray di sistema per aprire la **Tray Dashboard** e gestire tutto il sistema da un unico pannello.

### 🧩 Avvio dei Singoli Componenti
Per gli utenti avanzati, i componenti possono essere avviati singolarmente:
- **Interfaccia Web:** `HECOS_WEB_RUN_WIN.bat` (Win) / `hecos_web_run.sh` (Linux)
- **Console Terminale:** `HECOS_CONSOLE_RUN_WIN.bat` (Win) / `HECOS_CONSOLE_RUN.sh` (Linux)
- **Pacchetto Completo:** `main.py` (Avvia Tray + Backend)

### 🏎️ Avvio Rapido (Fast Boot)
Puoi attivare il **Fast Boot** nel Pannello di Controllo (**F7**) sotto `SYSTEM` per saltare il controllo iniziale e ridurre il tempo di caricamento a **~0,5 secondi**.
