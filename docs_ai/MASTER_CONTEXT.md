# MASTER CONTEXT - Zentra Core

Questo documento stabilisce le regole d'oro per l'evoluzione e la manutenzione di Zentra-Core. Deve essere consultato prima di ogni modifica strutturale.

## Regole Globali

### 1. Integrità delle Funzionalità
- **DIVIETO ASSOLUTO** di rimuovere funzionalità esistenti senza una discussione documentata.
- Ogni modifica deve preservare la retrocompatibilità con la CLI, la WebUI e i Plugin esistenti.

### 2. Fonte di Verità
- I file in `capabilities/*.json` sono la fonte di verità ufficiale per ciò che il sistema "sa fare".
- Ogni volta che viene aggiunta una funzione (nuovo plugin, nuova rotta API, nuovo comando CLI), essa **DEVE** essere registrata nei file delle capabilities.

### 3. Allineamento e Mismatch
- Se durante l'analisi del codice si riscontra una discrepanza tra il codice reale e i file in `capabilities/*.json`, la priorità è segnalare il mismatch e aggiornare la documentazione.
- Non implementare mai soluzioni "fantasma" che non siano tracciate nel sistema di documentazione.

### 4. Sicurezza e Rischio
- Le capacità marcate come `risk: high` (es. `EXECUTOR`, `FILE_MANAGER`) richiedono estrema cautela. 
- Non allentare mai i vincoli di sicurezza di queste capacità senza autorizzazione esplicita.

---

> [!IMPORTANT]
> Zentra-Core è in una fase stabile di **v0.12.0 (Alpha)**. La sicurezza PKI, l'interfaccia mobile-first e l'internazionalizzazione degli script sono ora standard di sistema che devono essere preservati in ogni modifica futura.
