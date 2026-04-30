# AI OPERATIONAL INSTRUCTIONS - HECOS CORE

> [!CAUTION]
> **PROTOCOLLO ZERO ATTIVO.** L'inosservanza di questo protocollo invalida la coerenza del sistema e può portare a regressioni funzionali gravi.

## 🛑 PROTOCOLLO ZERO: Inizializzazione Obbligatoria
**Ogni sessione di lavoro o richiesta di modifica DEVE iniziare con l'esecuzione del PROTOCOLLO ZERO:**

1. **SCANNER:** Eseguire una scansione ricorsiva della cartella `/docs_ai/`.
2. **SYNC:** Sincronizzare la memoria con i file in `capabilities/*.json`.
3. **NO MEMORY:** È vietato procedere basandosi sulla memoria della sessione precedente. La "Verità" risiede solo nei file di documentazione attuali.
4. **CONTEXT CHECK:** Verificare se l'operazione impatta il Kernel (`main.py`) o un plugin specifico (Blueprints).

---

## Protocollo di Interazione (Workflow)

### 1. Fase di Analisi (Compliance Protocol Zero)
- Prima di scrivere codice, l'IA deve confermare all'utente: *"Protocollo Zero eseguito. Stato sistema analizzato."*
- Leggere `/docs_ai/MASTER_CONTEXT.md` per l'orientamento globale.
- Consultare `/docs_ai/DEVELOPMENT_RULES.md` per i vincoli tecnici (es. Lingua Inglese).

### 2. Sviluppo e Modifica
- **Coding Language:** Tutto il codice (logica, variabili, classi) deve essere scritto esclusivamente in **Inglese**.
- **Commenti:** Tutti i commenti nel codice devono essere in **Inglese**.
- **Integrità:** Non eliminare funzioni esistenti a meno che non sia richiesto esplicitamente dal Master Context (Deprecazione).

### 3. Output e Registrazione
- Ogni nuova funzione deve essere aggiunta ai file in `capabilities/*.json`.
- In caso di errori nel codice rilevati durante la scansione, segnalarli immediatamente come "Documentation/Code Mismatch".

### 4. Validazione UX & Scripts
- Verificare sempre che le nuove UI siano **responsive** (Test su viewport mobile).
- Assicurarsi che ogni nuovo script di sistema segua lo standard **I18N English Only**.

---

## 🛠 Comandi Rapidi per l'IA
- `/check_zero`: Esegue istantaneamente il Protocollo Zero e riassume lo stato delle capabilities.
- `/status`: Mostra l'elenco dei Blueprints attivi rilevati nel file system.