# 🔑 23. Key Manager e Failover

Il Key Manager è il modulo centrale per la gestione delle licenze e delle chiavi API in Hecos.

- **Gestione Chiavi**: Puoi aggiungere, rimuovere o modificare le tue chiavi API (OpenAI, Gemini, Anthropic) direttamente dal Pannello Config.
- **Sicurezza**: Le chiavi vengono memorizzate in modo sicuro e non vengono mai esposte nei log di sistema.
- **Failover Automatico**: Se un fornitore di servizi non risponde, Hecos può tentare automaticamente di usare un modello o un fornitore alternativo per completare la tua richiesta.
- **Monitoraggio Token**: Visualizza il consumo dei token in tempo reale per ogni sessione di chat.

### ⚙️ Impostazioni Avanzate e Comportamento del Failover

Il Key Manager dispone di una sezione **Impostazioni Avanzate** per permetterti di ottimizzare il modo in cui Hecos gestisce le richieste alle API e il passaggio da una chiave all'altra (Failover).

Ecco nel dettaglio a cosa servono i parametri:

1. **⏱️ Timeout richiesta cloud (secondi)**
   * **Cosa fa**: Imposta il tempo massimo che Hecos attenderà per ricevere una risposta dal provider cloud prima di arrendersi con la chiave attuale.
   * **Perché modificarlo**: Se l'API è sovraccarica e non risponde, un timeout troppo alto blocca Hecos in "thinking" per molto tempo. Un valore più basso (es: 20-30s) permette a Hecos di accorgersi subito del problema e passare a una chiave di riserva.
   * **Consigliato**: 30 secondi.

2. **🔄 Cooldown chiave in errore (secondi)**
   * **Cosa fa**: Quando una chiave riceve un errore di limite rateale (HTTP 429) o un timeout, Hecos la mette "in pausa" (cooldown) per il tempo specificato, evitando di sprecarci altri tentativi.
   * **Perché modificarlo**: Se usi API gratuite che si bloccano per un minuto dopo 10 messaggi, 60s è l'ideale. Se hai poche chiavi, potresti volerlo ridurre per ritentare prima con le stesse chiavi.
   * **Consigliato**: 60 secondi.

3. **🔁 Max tentativi failover**
   * **Cosa fa**: Determina il numero massimo di *chiavi diverse* che Hecos proverà a contattare in successione per un singolo messaggio dell'utente prima di restituire un messaggio d'errore.
   * **Perché modificarlo**: Per evitare loop infiniti o richieste troppo lunghe. Impostalo a un numero pari a quante chiavi di riserva hai per quel provider.
   * **Consigliato**: 5.

#### 💡 Come funziona il failover:
1. Hecos tenta la **chiave #1** con il timeout impostato.
2. Se l'API risponde con errore (429 rate limit o 401 unauthorized) o scatta il **timeout**, Hecos marca quella chiave come in "cooldown".
3. Hecos passa automaticamente alla **chiave #2** e tenta di nuovo.
4. Questo si ripete finché una chiave non funziona, oppure fino al raggiungimento del limite "Max tentativi failover".
5. Le chiavi in cooldown tornano automaticamente attive una volta scaduto il tempo impostato.
