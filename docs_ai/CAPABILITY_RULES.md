# CAPABILITY RULES & DEFINITIONS

Definizione dei parametri e della struttura del sistema delle capacità.

## Struttura della Capability (JSON)

Ogni entry nei file `capabilities/*.json` deve seguire questo schema rigoroso (architettura Blueprints):

```json
{
  "id": "identificativo_univoco",
  "description": "Spiegazione chiara di cosa fa",
  "risk": "low | medium | high",
  "available_in": ["cli", "web", "ai", "plugin"],
  "implementation": {
    "core_files": ["lista dei file fisici principali, es: app/module.py"],
    "entry_points": ["Come viene invocata l'azione, es: F5 / Plugin Call"],
    "config_keys": ["Chiavi di configurazione associate nel config.json"]
  },
  "verification_step": "Istruzione breve per verificare a mano o via codice se la feature è funzionante.",
  "notes": "Dettagli tecnici o limitazioni"
}
```

> **NOTA PER IA**: Questo livello di dettaglio è OBDLIGATORIO per evitare "regressioni funzionali". Se un file referenziato scompare dal codebase, l'IA deve attivare un avviso di perdita di codice "Documentation/Code Mismatch".

## Livelli di Rischio

### 🔴 HIGH (Alto)
- Capacità che hanno accesso diretto al file system (scrittura/cancellazione).
- Capacità che eseguono comandi shell arbitrari.
- Capacità che gestiscono dati sensibili o credenziali.
*Esempi: EXECUTOR, FILE_MANAGER.*

### 🟡 MEDIUM (Medio)
- Capacità che modificano lo stato del sistema (reboot, reset memoria).
- Capacità che accedono a hardware periferico (Webcam, Microfono).
- Modifica delle configurazioni core.
*Esempi: WEBCAM, reboot_system, config_editor.*

### 🟢 LOW (Basso)
- Capacità puramente informative (Dashboard, Time, Weather).
- Interazioni sociali o di output (Personalità, TTS).
- Operazioni di sola lettura sicura.

## Regole di Sicurezza

1. **Sandboxing**: Le capacità ad alto rischio dovrebbero operare, dove possibile, entro cartelle specifiche (es. `data/`).
2. **User Confirmation**: Comandi distruttivi (Tabula Rasa) o pericolosi (Executor) dovrebbero richiedere una conferma utente, specialmente se invocati via AI.
3. **Visibility**: Lo stato di ogni capacità (Online/Offline) deve essere visibile nel registro centrale.

## Integrità dei Percorsi (v0.17.0)

1. **Hermetic Storage**: È vietata la creazione di cartelle o file al di fuori della directory `zentra/` (eccetto file di configurazione temporanei approvati).
2. **Centralized Paths**: Ogni operazione di I/O su file (Logs, Snapshots, Medie) deve importare e utilizzare le costanti definite in `zentra.core.constants` (`LOGS_DIR`, `SNAPSHOTS_DIR`, ecc.).
3. **Hardcoding Prohibited**: È severamente vietato calcolare percorsi relativi o assoluti tramite `os.path.join(..., "..", "logs")` o simili. Utilizzare sempre la costante dedicata.

---

> [!NOTE]
> Queste regole servono a garantire che Zentra rimanga un assistente potente ma sicuro.
