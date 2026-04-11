## 🔌 4. Sistema Modulare / Plugins

Zentra è espandibile all'infinito posizionando cartelle in `plugins/`.
Tutti i plugin rispondono ad interfacce unificate che esportano `comandi shell` e aggiornano la configurazione dinamica di Zentra (Config Syncing).
- **Architettura a Estensioni (JIT)**: I plugin possono avere a loro volta "sub-plugin" chiamati Extensions, caricati in tempo reale (Lazy Loading). Un esempio è lo **Zentra Code Editor**, un'estensione del plugin Drive basata sul motore di Visual Studio Code (Monaco) per editare codice e file di testo direttamente dal WebUI.
- **Drive Pro (Navigazione Assoluta)**: Il plugin Drive permette di navigare l'intero filesystem del server host partendo dalla root `C:\` e permette di cambiare disco (es. `D:`, pennette USB) grazie all'Absolute Drive Selector.
- **Plugin WebUI Nativo**: L'interfaccia browser (`plugins/web_ui`) è un componente nativo (Porta 7070), gestendo chat, configurazione e dati multimodali in tempo reale con sincronizzazione automatica delle personalità.
- **Disabilitazione Pulita**: Se un plugin o modulo è difettoso ma in essenza non bloccante, disattivandolo dal F7 o dalla Dashboard WebUI lo disattiverà in memoria aggirandolo.
