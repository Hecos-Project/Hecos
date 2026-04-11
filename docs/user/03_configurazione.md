## ⚙️ 3. Configurazione Dinamica O-T-F (On-The-Fly)

Zentra mette a disposizione i Tasti Funzione (F1-F7) per interagire e riparametrizzare il `config.json` a caldo, con memoria permanente.

* **[ F1 ] MANUALE AZIONALE (Aiuto):** Richiama i protocolli "root" esposti dai Plugin, mostrando comandi liberi (es. `list:`, `cmd:`, `apri:`).
* **[ F2 ] CAMBIO MODELLO IA:** Seleziona velocemente il modello di rete neurale (Llama, Gemma, Cloud, ecc.) dalla lista indicizzata dal backend connesso in quel momento (Ollama/Kobold/Cloud).
* **[ F3 ] CARICO ANIMA / PERSONALITÀ:** Cambia il tono e la coscienza di sistema. Zentra ora scansiona automaticamente la cartella `/personality/*.txt` ad ogni avvio e accesso al menu.
* **[ F4 ] TOGGLE ASCOLTO (MIC):** Silenzia temporalmente le recezioni acustiche (On/Off).
* **[ F5 ] TOGGLE VOCE (TTS):** Abilita o silenzia la sintesi vocale di risposta. L'IA continuerà ad elaborare solo tramite chat visiva.

### 🎛️ Il PANNELLO DI CONTROLLO [ F7 ]
Tramite grafica Inquirer Curses-based, offre il controllo granulare sull'Engine Zentra Core.
Navigabile tramite Frecce Direzionali (`Su`, `Giù`, `Destra`, `Sinistra`), permette editing di booleani (Vero/Falso), numeri o stringhe (via inserimento testo `Invio`).

**Logica di Sicurezza del Salvataggio e Cold Reboot:**
- Se l'utente preme `ESC` senza modifiche o richiede specificamente l'Uscita senza Salvataggio (`DISCARD`), non viene riscritto alcun settaggio a configurazione intaccando zero file originari. Pieno silente ritorno a terminale.
- Se una qualsivoglia modifica visiva accade, la pressione del comando `RIAVVIA ZENTRA` o l'uscita confermata via `Invio`, scriverà fisicamente il `config.json` e scatenerà un **Cold Reboot (Arresto Terminato + Riavvio Forzato, id 42)** automatico in 1 secondo. Questo garantisce che cache ed impostazioni globali si allineino millimetricamente ad ogni istante.
