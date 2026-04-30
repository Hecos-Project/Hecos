# ⚙️ 3. Configurazione Dinamica O-T-F (On-The-Fly)

Hecos mette a disposizione i Tasti Funzione (F1-F7) per interagire e riparametrizzare il sistema a caldo, con memoria permanente.

* **[ F1 ] MANUALE AZIONALE (Aiuto):** Richiama i protocolli "root" esposti dai Plugin, mostrando comandi liberi (es. `list:`, `cmd:`, `apri:`).
* **[ F2 ] CAMBIO MODELLO IA:** Seleziona velocemente il modello di rete neurale (Llama, Gemma, Cloud, ecc.) dalla lista indicizzata dal backend.
* **[ F3 ] CARICO ANIMA / PERSONALITÀ:** Cambia il tono e la coscienza di sistema. Hecos scansiona automaticamente la cartella `/personality/` ad ogni avvio.
* **[ F4 ] TOGGLE ASCOLTO (MIC):** Attiva o disattiva l'acquisizione del microfono.
* **[ F5 ] TOGGLE VOCE (TTS):** Abilita o silenzia la sintesi vocale di risposta. 

### 🎛️ Hecos Hub (Config Panel)
Accessibile tramite **F7** o via WebUI, l'Hub è il centro di comando di Hecos. Recentemente ridisegnato con un'estetica **Premium e Simmetrica**, offre:
- **Navigazione a Tab**: Impostazioni organizzate (Backend, LLM, Persona, Voice, etc.) per una gestione ordinata.
- **Dynamic Switcher**: Passa istantaneamente dalla vista a schede alla vista "Wall" (griglia) per una panoramica totale.
- **Sync in tempo reale**: Molte impostazioni (come il cambio personalità o voce) vengono applicate istantaneamente senza riavvio.

**Salvataggio e Riavvio:**
Le modifiche critiche (es. cambio porta o HTTPS) richiedono un **Riavvio a Freddo** automatico gestito dal Watchdog di sistema per garantire l'integrità dei servizi.
