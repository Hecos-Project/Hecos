# ⚡ Guida Rapida di Avvio

Benvenuto in Hecos! Segui questi passaggi per configurare il sistema e iniziare subito a utilizzare l'IA sul tuo PC.

## 1. Installazione (Bootstrap)

> [!IMPORTANT]
> **Percorso di Installazione**: Consigliamo vivamente di estrarre e installare Hecos in una cartella principale come `C:\Hecos`. Evita di installarlo in `Download`, sul `Desktop` o in percorsi troppo lunghi con spazi, poiché ciò potrebbe causare malfunzionamenti o problemi di avvio dei moduli.

> [!WARNING]
> **Dipendenze di Sistema**: Prima di avviare l'installazione o il setup, assicurati di aver installato i pacchetti redistribuibili (come `VC_redist`) presenti nella cartella **`dependencies`** inclusa nel pacchetto. Se questi file mancano, componenti critici come l'IA e il motore vocale (TTS) non si avvieranno.

Il modo più semplice per iniziare è utilizzare gli script di setup automatico nella cartella principale:
- **Windows:** Fai doppio clic su `START_SETUP_HERE_WIN.bat`
- **Linux:** Apri un terminale ed esegui `bash START_SETUP_HERE_LINUX.sh`

Questi script installeranno automaticamente le dipendenze e avvieranno la **Procedura Guidata di Setup** nel tuo browser.

## 2. La Procedura Guidata di Setup

Al primo avvio, il tuo browser si aprirà su `http://localhost:7070`. Segui i passaggi guidati:
1. **Benvenuto**: Clicca su "Inizia".
2. **Lingua**: Seleziona la tua lingua preferita.
3. **Scegli il Cervello (AI Provider)**: 
   - **Cloud (Online)**: Usa modelli potenti come Gemini o GPT-4o. Dovrai inserire la tua **Chiave API**.
   - **Locale (Offline)**: Se hai Ollama o KoboldCpp installati sul tuo PC, Hecos si connetterà automaticamente. **In questo caso, NON hai bisogno di alcuna chiave API**, tutto viene eseguito sul tuo hardware!
4. **Generazione Immagini**: Attualmente, la creazione di immagini richiede un provider online. Il modo migliore e più rapido è creare un account gratuito su **HuggingFace**, generare un "Access Token" e inserirlo nelle impostazioni di Hecos per utilizzare modelli avanzati come **FLUX.1-dev**.
5. **Configura la Personalità**: Scegli l'"anima" del tuo assistente (es. Urania o Atlas).
6. **Fine**: Clicca su "Salva e Avvia".

## 3. Primo Utilizzo

Ora che Hecos è attivo, ecco come interagire:
- **Chat**: Digita nella barra di testo in fondo alla WebUI e premi Invio.
- **Voce**: 
  - Clicca sull'icona del microfono nella WebUI.
  - Oppure usa la scorciatoia globale **Ctrl+Shift+Z** (Windows) per parlare senza nemmeno aprire il browser.
- **Visione**: Trascina un'immagine nella chat per chiedere a Hecos di descriverla o analizzarla.

## 4. Pannello di Controllo (F7)

Per modificare i parametri, aggiungere nuove chiavi API o attivare plugin:
- Premi **F7** sulla tastiera o fai clic sull'icona ingranaggio/logo nella WebUI per aprire l'**Hecos Hub**.
- Le modifiche vengono salvate all'istante.

## 5. Icona della barra delle applicazioni (Tray - Background)

Hecos rimane attivo nella barra delle applicazioni (vicino all'orologio di Windows). 
- Puoi chiudere la scheda del browser: il sistema continuerà a funzionare in background per rispondere ai tasti di scelta pragmatica.
- Fai clic con il tasto destro sull'icona "Z" per riaprire la WebUI o uscire da Hecos.

---
*È tutto pronto! Inizia a esplorare il potenziale del tuo nuovo sistema operativo agentico locale.*
