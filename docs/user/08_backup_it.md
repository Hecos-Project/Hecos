# 💾 9. Backup Centralizzato

> *"Una soluzione con un clic per conservare al sicuro l'intera configurazione e le memorie di Hecos."*

Il **Backup Centralizzato** è un modulo fondamentale della WebUI di Hecos progettato per darti tranquillità. Poiché Hecos funziona interamente in locale e salva i tuoi dati sul tuo disco rigido, è fondamentale avere un modo semplice per fare il backup del sistema.

## Cosa viene salvato
Quando avvii un Backup Centralizzato, Hecos pacchettizza i seguenti elementi in un singolo archivio compresso:
- **`config/`**: Tutte le tue impostazioni personalizzate, chiavi API e parametri di sistema.
- **`workspace/`**: I tuoi flussi, personas e dati personalizzati.
- **`memory/`**: Il database SQLite contenente tutte le cronologie delle tue chat (Episodic Memory Vault).
- **`plugins/`**: Qualsiasi pacchetto personalizzato o scaricato che hai installato.

## Come si usa
1. Apri il **Central Hub** (F7).
2. Naviga nella categoria **Sistema** o **Dati** (a seconda del tuo layout).
3. Clicca sul pulsante **Genera Backup**.
4. Hecos compilerà il file ZIP in background e avvierà automaticamente il download tramite il tuo browser.

## Ripristino
Per ripristinare un backup, estrai semplicemente l'archivio ZIP scaricato sopra la tua cartella di installazione esistente di Hecos, sovrascrivendo le cartelle. Il tuo sistema tornerà esattamente allo stato in cui si trovava al momento del backup.
