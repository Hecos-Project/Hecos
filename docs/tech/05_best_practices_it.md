# 🛠️ 5. Best Practices per Sviluppatori

Quando sviluppi nuovi plugin o estendi Hecos, segui queste linee guida:

1.  **Modularità**: Mantieni la logica del plugin isolata e usa le API di sistema fornite (es. `self.core.speak()`).
2.  **Validazione**: Usa sempre Pydantic per definire nuovi schemi di configurazione.
3.  **Sicurezza**: Non eseguire mai comandi di sistema direttamente; usa sempre il `SubprocessAdapter`.
4.  **Logging**: Usa `logger.debug()` e `logger.info()` per tracciare le operazioni del tuo plugin.
5.  **Documentazione**: Aggiungi sempre una breve descrizione tecnica del tuo codice per facilitare la manutenzione futura.
