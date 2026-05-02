# MASTER CONTEXT - Hecos

Questo documento stabilisce le regole d'oro per l'evoluzione e la manutenzione di Hecos-Core. Deve essere consultato prima di ogni modifica strutturale.

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
> Hecos-Core è in una fase stabile di **v0.18.0 (Alpha)**. La sicurezza PKI (Root CA), l'interfaccia mobile-first, l'**Architettura Privacy a 3 Livelli** (Normal, Auto-Wipe, Incognito), l'autenticazione Multi-Utente, i Vault isolati, il **Multi-Registry MCP Discovery Hub** e il sandbox AST Code Jail sono standard di sistema operativi che devono essere rigorosamente documentati e preservati in ogni modifica.

