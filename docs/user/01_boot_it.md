# 🚀 1. Avvio e Controllo Iniziale

All'avvio dell'eseguibile o dello script Python, Zentra inizia la sua sequenza di **Avvio Sincronizzato**.

### Diagnostica Pre-Volo
Per impostazione predefinita, il sistema controlla:
- Integrità delle cartelle essenziali (`core/`, `plugins/`, `memory/`, ecc.).
- Stato dell'hardware (CPU e RAM entro i limiti).
- Stato di Audio e Voce.
- Reattività del Backend IA.
- Scansione dei Plugin Attivi/Disattivati.

### ⚡ Bootstrap One-Click
Il modo consigliato per avviare Zentra è utilizzare gli script di bootstrap universale nella cartella principale:
- **Windows:** `START_SETUP_HERE_WIN.bat`
- **Linux:** `START_SETUP_HERE_LINUX.sh`

Questi script gestiscono automaticamente il controllo dell'ambiente, le dipendenze e lanciano il **Wizard di Setup**.

### 🧩 Avvio Componenti Singoli
Per utenti avanzati, i componenti possono essere avviati singolarmente:
- **Interfaccia Web:** `ZENTRA_WEB_RUN_WIN.bat` (Win) / `zentra_web_run.sh` (Linux)
- **Console Terminale:** `ZENTRA_CONSOLE_RUN_WIN.bat` (Win) / `ZENTRA_CONSOLE_RUN.sh` (Linux)
- **Bundle Completo:** `main.py` (Avvia Tray + Backend)

### 🏎️ Avvio Rapido
Puoi attivare l'**Avvio Rapido** nel Pannello di Controllo (**F7**) sotto `SYSTEM` per saltare la diagnostica e ridurre il tempo di avvio a **~0.5 secondi**.
