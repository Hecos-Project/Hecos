# 🔑 13. Key Manager e Failover

Il Key Manager è il modulo centrale per la gestione delle licenze e delle chiavi API in Hecos.

- **Gestione Chiavi**: Puoi aggiungere, rimuovere o modificare le tue chiavi API (OpenAI, Gemini, Anthropic) direttamente dal Pannello Config.
- **Sicurezza**: Le chiavi vengono memorizzate in modo sicuro e non vengono mai esposte nei log di sistema.
- **Failover Automatico**: Se un fornitore di servizi non risponde, Hecos può tentare automaticamente di usare un modello o un fornitore alternativo per completare la tua richiesta.
- **Monitoraggio Token**: Visualizza il consumo dei token in tempo reale per ogni sessione di chat.
