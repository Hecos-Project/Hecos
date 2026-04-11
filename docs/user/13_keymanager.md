## 🔑 13. Gestione API Keys e Failover (v0.15.2)

Zentra introduce un sistema avanzato per la gestione delle chiavi API, eliminando la necessità di riavvii manuali in caso di esaurimento dei crediti.

### Funzionamento del Key Manager
Il sistema gestisce un **Pool di chiavi** per ogni provider (Groq, Gemini, OpenAI, ecc.):
- **Failover Automatico**: Se una chiave restituisce un errore di autenticazione (401, 403, 400 su Gemini) o di quota (429), Zentra la marca come "Invalida" o "In Pausa" e passa istantaneamente alla successiva disponibile nel pool.
- **Cooldown**: Le chiavi che vanno in "Rate Limit" vengono messe in attesa per 60 secondi prima di essere riprovate.

### Pannello WebUI [Key Manager]
Dalla WebUI è possibile monitorare in tempo reale lo stato delle chiavi. È possibile aggiungere nuove chiavi al pool e scegliere se salvarle permanentemente nel file `.env` o nel file di configurazione interno.
