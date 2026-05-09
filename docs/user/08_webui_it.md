# 💻 WebUI Nativa

La WebUI di Hecos è l'interfaccia grafica moderna accessibile tramite il tuo browser.

- **Accesso**: Di default è disponibile all'indirizzo `http://localhost:5000` (o sulla porta configurata).
- **Chat Ricca**: Supporta la visualizzazione di immagini, grassetti, tabelle e blocchi di codice con evidenziazione della sintassi.
- **Configurazione Grafica**: Permette di modificare ogni aspetto di Hecos tramite menu intuitivi, senza dover modificare manualmente i file YAML.
- **Microfono e Camera**: Grazie alla cifratura Hecos PKI, puoi usare il microfono e la webcam del tuo browser per interagire con l'IA anche da remoto sulla tua rete locale.
- **Gestione Utenti (Multi-User)**: Il tab "Users" permette di gestire profili multipli, cambiare avatar e bio note personali. Ogni utente ha un "Vault" isolato.
- **Cronologia Sessioni**: Un nuovo pannello laterale permette di gestire conversazioni multiple. Ogni sessione è salvata in modo persistente nell'Episodic Memory Vault, può essere rinominata o eliminata. È presente un pulsante 🗑️ per la cancellazione rapida di tutte le chat.
- **Sidebar Dinamica**: La barra laterale si adatta istantaneamente caricando solo i plugin configurati e attivi.
- **Modalità Privacy a 3 Livelli (v0.18.0)**: Selettore avanzato che blocca la modalità dopo l'invio del primo messaggio:
  - `☁️ Normale`: Messaggi salvati permanentemente nel database locale.
  - `🔒 Auto-Wipe`: Messaggi conservati in RAM finché il sistema è attivo; cancellati al riavvio.
  - `🕵️ Incognito`: Traccia zero. I messaggi non vengono mai scritti e il contesto viene rimosso al cambio della chat.
- **Finestra Azioni (Action Window)**: Console pulita in stile terminale direttamente all'interno della UI della chat, per monitorare l'esecuzione nativa del sistema e i processi in background.
- **Versione Attuale**: `0.20.0` (Runtime Alpha)
