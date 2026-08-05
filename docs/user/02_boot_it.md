# 🚀 3. Avvio e Controllo Iniziale

All'avvio dell'eseguibile o dello script Python, Hecos inizia la sua sequenza di **Avvio Sincronizzato**.

### Diagnostica Pre-Volo
Per impostazione predefinita, il sistema controlla:
- Integrità delle cartelle essenziali (`core/`, `plugins/`, `memory/`, ecc.).
- Stato dell'hardware (CPU e RAM entro i limiti).
- Stato di Audio e Voce.
- Reattività del Backend IA.
- Scansione dei Plugin Attivi/Disattivati.

### ⚡ Bootstrap One-Click

> [!TIP]
> **Metodo Consigliato — Installa tramite la Tray!** Scarica solo **Hecos Tray** (il pacchetto leggero), avviala e apri la **Tray Dashboard**. Vai alla scheda **Updates** e clicca su *Download / Install Core*: il sistema scarica e configura tutto in automatico. È il metodo più semplice e completo.

> [!IMPORTANT]
> **Percorso di Installazione**: Consigliamo vivamente di estrarre e installare Hecos in una cartella principale come `C:\Hecos`. Evita di installarlo in `Download`, sul `Desktop` o in percorsi troppo lunghi con spazi, poiché ciò potrebbe causare malfunzionamenti o problemi di avvio dei moduli.

> [!WARNING]
> **Dipendenze di Sistema**: Prima di avviare l'installazione o il setup, assicurati di aver installato i pacchetti redistribuibili (come `VC_redist`) presenti nella cartella **`dependencies`** inclusa nel pacchetto. Se questi file mancano, componenti critici come l'IA e il motore vocale (TTS) non si avvieranno.

**Metodo alternativo (avanzato):** Se hai già scaricato il pacchetto Core, usa gli script di bootstrap universale nella cartella principale:
- **Windows:** `START_SETUP_HERE_WIN.bat`
- **Linux:** `START_SETUP_HERE_LINUX.sh`

Questi script gestiscono automaticamente il controllo dell'ambiente, le dipendenze e lanciano il **Wizard di Setup**.

> [!TIP]
> **Avvii successivi**: Dopo il setup iniziale, il modo più veloce e comodo per usare Hecos ogni giorno è avviare la **Hecos Tray**. Fai doppio clic sulla sua icona nella barra delle applicazioni per aprire la **Tray Dashboard** e gestire tutto il sistema da un unico pannello.

### 🧩 Avvio Componenti Singoli
Per utenti avanzati, i componenti possono essere avviati singolarmente:
- **Interfaccia Web:** `HECOS_WEB_RUN_WIN.bat` (Win) / `hecos_web_run.sh` (Linux)
- **Console Terminale:** `HECOS_CONSOLE_RUN_WIN.bat` (Win) / `HECOS_CONSOLE_RUN.sh` (Linux)
- **Bundle Completo:** `main.py` (Avvia Tray + Backend)

### 🏎️ Avvio Rapido
Puoi attivare l'**Avvio Rapido** nel Pannello di Controllo (**F7**) sotto `SYSTEM` per saltare la diagnostica e ridurre il tempo di avvio a **~0.5 secondi**.
