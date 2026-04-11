# ⚙️ 3. Configurazione Dinamica O-T-F (On-The-Fly)

Zentra mette a disposizione i Tasti Funzione (F1-F7) per interagire e riparametrizzare il sistema a caldo, con memoria permanente.

* **[ F1 ] MANUALE AZIONALE (Aiuto):** Richiama i protocolli "root" esposti dai Plugin, mostrando comandi liberi (es. `list:`, `cmd:`, `apri:`).
* **[ F2 ] CAMBIO MODELLO IA:** Seleziona velocemente il modello di rete neurale (Llama, Gemma, Cloud, ecc.) dalla lista indicizzata dal backend.
* **[ F3 ] CARICO ANIMA / PERSONALITÀ:** Cambia il tono e la coscienza di sistema. Zentra scansiona automaticamente la cartella `/personality/` ad ogni avvio.
* **[ F4 ] TOGGLE ASCOLTO (MIC):** Attiva o disattiva l'acquisizione del microfono.
* **[ F5 ] TOGGLE VOCE (TTS):** Abilita o silenzia la sintesi vocale di risposta. 

### 🎛️ Il PANNELLO DI CONTROLLO [ F7 ]
Tramite un'interfaccia grafica basata su menu, offre il controllo granulare su Zentra Core. Permette di modificare impostazioni booleane, numeriche o stringhe.

**Salvataggio e Riavvio:**
I cambiamenti possono essere scartati con `ESC` o salvati con l'uscita confermata. In caso di modifiche, il sistema eseguirà un **Riavvio a Freddo** automatico in 1 secondo per applicare i nuovi parametri.
