# Hecos SDK (Isolated Subprocesses)

Hecos SDK (Software Development Kit) introduce una modalità di esecuzione chiamata **Total Isolation** (Isolamento Totale) per i pacchetti HPM (Hecos Package Manager).

## A cosa serve
L'architettura classica dei plugin Hecos li esegue nello stesso thread ed environment principale di Hecos (`hecos.core`). Questo approccio è molto performante per script leggeri (es. un gestore di e-mail, un messenger), ma ha un grande svantaggio: **il Dependency Hell**.

Se un pacchetto HPM richiede versioni specifiche di librerie (es. PyTorch, ONNX, OpenCV, Selenium) che vanno in conflitto con quelle del core di Hecos o con quelle di un altro plugin, l'intero sistema crasha. 

L'**Hecos SDK** risolve questo problema permettendo ai pacchetti HPM di girare all'interno di un processo isolato (`subprocess`) e in un **ambiente virtuale (venv)** separato, dialogando con il core di Hecos esclusivamente tramite **IPC (Inter-Process Communication) via JSON in stdin/stdout**.

## Vantaggi della Total Isolation
1. **Ambiente Isolato (venv)**: Ogni plugin può avere il suo `requirements.txt` con librerie specifiche (anche vecchie o in conflitto con il core) senza "sporcare" il resto di Hecos.
2. **Robustezza**: Se il plugin crasha per un errore critico in una libreria C (es. CUDA out of memory), non trascina giù con sé Hecos, che rimane attivo e può riavviare il plugin.
3. **Nessun Conflitto di Event Loop**: Utile per librerie come Playwright o FastAPI che si aspettano di avere il controllo del main thread.

## Svantaggi
1. **Risorse (RAM/CPU)**: Ogni plugin isolato lancia un nuovo eseguibile Python (`hecos_sdk.runner`), il che consuma decine di MB di RAM in più per ciascun processo, rendendo Hecos più pesante su hardware datato (es. CPU pre-2018).
2. **Ritardo nelle Chiamate**: Essendo un IPC tramite JSON serializzato, passare grandi moli di dati binari (es. video) tra Hecos e il plugin è inefficiente.

## Come attivare l'SDK
Dalla versione 2.0+, l'Hecos SDK è **disabilitato di default** per preservare risorse hardware.
Se desideri installare e utilizzare pacchetti HPM che richiedono isolamento, devi esplicitamente attivare l'interruttore **"Enable Hecos SDK Isolated Processes"** nel pannello WebUI (`Impostazioni -> Sistema -> Performance`). 
Se l'SDK è spento, il core di Hecos *ignorerà* l'avvio dei subprocessi e manterrà offline i pacchetti HPM che ne necessitano.

## Come Hecos capisce se usare l'SDK
Quando Hecos rileva un pacchetto in `hecos/hpm/nome_pacchetto`, analizza due fattori:
- Se trova la directory `venv/` (o un file `runner.py`), sa che il pacchetto è di tipo **isolato**. 
- Avvia quindi il proxy (`ModuleBus` -> `core/ipc/proxy.py`), che innesca il comando `python -m hecos_sdk.runner` passando il `tag` come variabile d'ambiente (`HECOS_MODULE_TAG`).

Il pacchetto deve implementare l'interfaccia classica di un plugin (es. `main.py` con una classe `tools`), e il runner SDK farà automaticamente il routing tra le chiamate del core Hecos e il `main.py` isolato.
