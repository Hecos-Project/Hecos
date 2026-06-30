# ⌨️ 12. Comandi Diretti (HDCS)

Immagina di avere una **bacchetta magica** che ti permette di dare ordini precisi ad Hecos senza dover fare lunghi discorsi con l'Intelligenza Artificiale. Questa bacchetta magica si chiama **HDCS (Hecos Direct Command System)**, o più semplicemente: i **Comandi Diretti**.

Normalmente, quando scrivi ad Hecos, l'AI deve leggere il tuo messaggio, pensare a cosa vuoi fare, scegliere lo strumento giusto e poi eseguirlo. A volte, però, tu sai *esattamente* cosa vuoi fare e vuoi che accada **subito**, in un batter d'occhio!

Ecco a cosa servono i comandi diretti. Iniziano tutti con una barra `/` (lo *slash*) e dicono al sistema di eseguire immediatamente un'azione, saltando completamente il "cervello" dell'AI.

![Hecos - Direct Comands](https://github.com/Hecos-Project/Hecos-Assets/blob/main///004_HecosChat_Direct_Commands.png?raw=true)


---

## 🎩 Come si usano nella Chat

Usare i comandi diretti nella chat è facilissimo, proprio come usare le emoji su WhatsApp!

1. Clicca sulla barra della chat dove di solito scrivi i tuoi messaggi.
2. Digita il carattere **`/`** (la barra obliqua).
3. **Magia!** Apparirà un menu a tendina proprio sopra la casella di testo.
4. Questo menu contiene *tutti* i comandi disponibili nel sistema, sia quelli predefiniti (friendly) che quelli auto-generati dai plugin.
5. Puoi scorrere la lista con il mouse o con le frecce della tastiera, oppure puoi continuare a scrivere per filtrare la lista. Ad esempio, se scrivi `/meteo`, vedrai apparire il comando del meteo.
6. Premi **Tab** o clicca con il mouse sul comando per sceglierlo.
7. Se il comando ha bisogno di informazioni aggiuntive (come la città per il meteo), ti lascerà uno spazio. Scrivi ad esempio `/meteo Roma` e premi **Invio**. Fatto!

---

## 🔍 La "Spotlight": I comandi sempre a portata di mano

E se non ti trovi nella chat? Magari stai guardando la pagina dei plugin o stai leggendo un'altra schermata. Non preoccuparti! Puoi usare i comandi diretti *ovunque* ti trovi grazie alla **Spotlight**.

La Spotlight è una speciale barra di ricerca fluttuante. Per evocarla:
1. Premi la combinazione segreta sulla tastiera: **`Ctrl + Alt + Spazio`** (premi Control, Alt e la barra spaziatrice insieme).
2. Lo schermo si scurirà leggermente e apparirà una barra di ricerca al centro.
3. Scrivi quello che stai cercando (es. `img` o `meteo` o `calendar`).
4. Seleziona il comando con le freccette e premi **Invio**. 
5. Hecos eseguirà l'azione istantaneamente in sottofondo e ti mostrerà un messaggino di conferma!

---

## 🎤 Comandi Vocali (Dettatura)

Puoi lanciare i comandi diretti anche semplicemente **parlando**! Se utilizzi la funzione di dettatura vocale, il sistema è in grado di capire quando vuoi eseguire un comando invece di inviare un normale messaggio di testo.

Per attivarlo, ti basta iniziare la frase (come primissima parola) con uno dei seguenti "trigger" vocali:
* **"Comando"** (es. *"Comando meteo Roma"*)
* **"Command"** (es. *"Command clear"*)
* **"Slash"** (es. *"Slash help"*)

Il sistema intercetterà automaticamente la parola chiave, la trasformerà nel simbolo `/` e invierà l'istruzione direttamente al motore dei comandi! È estremamente comodo se non hai le mani libere sulla tastiera.

---

## 🧩 Usare i Comandi Diretti in "Flows" (Flussi)

Flows è il posto dove crei routine automatiche (i "Flussi") unendo tanti nodi come se fossero mattoncini Lego. 
A volte, potresti voler usare un comando diretto dentro un Flusso, per far sì che un'azione venga eseguita in modo precisissimo senza interpellare l'AI.

Per farlo, ti basta usare un nodo speciale:
1. Nel menu a sinistra di Flows, apri la categoria **SYSTEM** o **EXECUTOR**.
2. Trova il mattoncino chiamato **`execute_slash_command`** e trascinalo nel tuo schermo.
3. Questo nodo ha un campo di testo chiamato `command`. Lì dentro devi scriverci il comando che vuoi eseguire!
4. **Il trucco del prestigiatore:** Se fai clic sulla casella di testo del nodo e digiti `/`, si aprirà la tendina dell'autocompletamento proprio come nella chat! Seleziona il comando, e verrà scritto per te.
5. In alternativa, puoi sempre premere `Ctrl + Alt + Spazio` per cercare il comando. Se sei dentro la casella di testo del nodo, premendo Invio il comando non verrà eseguito subito, ma verrà **incollato** magicamente nel nodo, pronto per essere salvato!

---

## 📖 Catalogo Completo dei Comandi Diretti

Ecco l'elenco completo di tutti i comandi diretti integrati in Hecos, divisi per categoria. Ciascun comando include la descrizione, i suoi sinonimi (alias) e 3 esempi pratici d'uso.

### 1. Comandi di Sistema (Categoria CORE)

Questi sono i comandi fondamentali per gestire l'applicazione Hecos, la chat e le configurazioni.

| Comando Base | Alias Alternativi | Descrizione |
| :--- | :--- | :--- |
| `/help` | `/?`, `/comandi` | Mostra l'elenco di tutti i comandi slash e le funzionalità attive nel sistema. |
| `/status` | `/info` | Mostra lo stato del sistema (modello AI in uso, plugin caricati, utilizzo RAM e versione). |
| `/clear` | `/pulisci`, `/reset` | Cancella l'intera cronologia della conversazione corrente della chat per liberare memoria. |
| `/config get` | | Legge un valore di configurazione interno usando la notazione a punti (es. `categoria.chiave`). |
| `/config set` | | Imposta temporaneamente in memoria RAM un valore di configurazione. |
| `/reload` | `/reload_commands` | Forza il ricaricamento del registro di tutti i comandi (utile dopo l'aggiunta di nuovi plugin). |

#### Esempi pratici:
* **`/help`**
  1. `/help` (mostra l'elenco generale dei comandi)
  2. `/?` (mostra l'elenco rapido)
  3. `/comandi` (mostra l'elenco in italiano)
* **`/status`**
  1. `/status` (visualizza il modello AI attivo e le risorse usate)
  2. `/info` (mostra la versione di Hecos in esecuzione)
  3. `/status` (utile per verificare se il backend Ollama/Kobold è online)
* **`/clear`**
  1. `/clear` (svuota la chat corrente)
  2. `/pulisci` (riazzera il contesto della conversazione)
  3. `/reset` (inizia una conversazione da zero)
* **`/config get`**
  1. `/config get ai.model` (mostra il modello AI configurato)
  2. `/config get reminder.reminder_mode` (mostra come vengono riprodotti i promemoria)
  3. `/config get system.theme` (mostra il tema dell'interfaccia)
* **`/config set`**
  1. `/config set ai.model gemini/gemini-2.0-flash` (imposta temporaneamente il modello a Gemini 2.0 Flash)
  2. `/config set reminder.max_reminders 30` (limita i promemoria massimi attivi a 30)
  3. `/config set system.theme dark` (cambia il tema dell'interfaccia in scuro)
* **`/reload`**
  1. `/reload` (ricarica tutti i comandi registrati)
  2. `/reload_commands` (aggiorna la lista dell'autocompletamento)
  3. `/reload` (da usare se un nuovo plugin non viene visualizzato)

---

### 2. Comandi dei Flussi (Categoria FLOWS)

Questi comandi consentono di visualizzare, avviare e monitorare i flussi di automazione creati nella sezione **Flows**.

| Comando Base | Alias Alternativi | Descrizione |
| :--- | :--- | :--- |
| `/flow list` | `/flows`, `/flow ls` | Elenca tutti i flussi disponibili salvati nel workspace (`workspace/flows/`). |
| `/flow run` | `/flow exec` | Esegue immediatamente un flusso specifico cercandolo per nome. |
| `/flow trigger` | `/trigger` | Attiva manualmente il trigger di un flusso specifico (funziona esattamente come run). |
| `/flow status` | `/flow log` | Mostra l'ultimo log di esecuzione (il risultato dell'avvio) di un determinato flusso. |

#### Esempi pratici:
* **`/flow list`**
  1. `/flow list` (mostra la lista con trigger e stato attivo/disattivo)
  2. `/flows` (elenco rapido dei file YAML)
  3. `/flow ls` (mostra l'elenco sintetico)
* **`/flow run`**
  1. `/flow run morning_routine` (avvia la routine mattutina programmata)
  2. `/flow run check_weather_alert` (avvia il controllo meteo pianificato)
  3. `/flow exec spegni_tutto` (esegue il flusso di spegnimento dei dispositivi)
* **`/flow status`**
  1. `/flow status morning_routine` (mostra se l'esecuzione della routine è andata a buon fine)
  2. `/flow log check_weather_alert` (mostra i dettagli di debug dell'ultimo controllo meteo)
  3. `/flow status backup_dati` (legge il log del flusso di backup)

---

### 3. Comandi dei Plugin (Categoria PLUGINS)

Questi comandi sono esposti dai vari moduli aggiuntivi abilitati all'interno di Hecos.

| Comando Base | Alias Alternativi | Descrizione |
| :--- | :--- | :--- |
| `/soul` | `/persona`, `/personality` | Cambia al volo la personalità attiva di Hecos (es. risposte serie, giocose, ecc.). |
| `/souls` | `/personas` | Elenca tutte le anime/personalità installate nel sistema. |
| `/calendar` | `/calendario`, `/appuntamenti` | Mostra i prossimi eventi salvati sul calendario di Hecos. |
| `/img` | `/image`, `/photo`, `/foto` | Genera un'immagine tramite l'AI partendo da una descrizione testuale. |
| `/list` | `/lists`, `/liste` | Mostra tutte le liste attive salvate (Spesa, Da fare, ecc.). |
| `/lista` | | Mostra tutti gli elementi all'interno di una lista specifica. |
| `/list add` | `/lista aggiungi` | Aggiunge un elemento a una lista (la crea automaticamente se non esiste). |
| `/list done` | `/lista spunta` | Segna un elemento come completato (spuntato) in una lista. |
| `/reminder` | `/ricorda`, `/promemoria` | Imposta un promemoria con data/ora in linguaggio naturale. |
| `/reminders` | `/promemoria list` | Elenca tutti i promemoria attivi con i relativi identificativi ID. |
| `/meteo` | `/weather`, `/tempo` | Mostra le condizioni meteo attuali o le previsioni per una città. |

#### Esempi pratici:
* **`/soul`**
  1. `/soul Motoko` (passa alla personalità "Motoko")
  2. `/persona 2` (passa alla seconda personalità della lista)
  3. `/personality Jarvis` (imposta l'assistente sullo stile "Jarvis")
* **`/calendar`**
  1. `/calendar` (mostra l'agenda dei prossimi giorni)
  2. `/calendario` (visualizza i prossimi appuntamenti)
  3. `/appuntamenti` (elenca gli impegni odierni)
* **`/img`**
  1. `/img un gattino nello spazio con un casco da astronauta` (genera l'immagine corrispondente)
  2. `/photo ritratto cyberpunk di una ragazza, luci al neon, 8k` (genera una foto artistica)
  3. `/foto tramonto sul mare stile dipinto a olio` (genera un quadro digitale)
* **`/list` / `/lista` / `/list add` / `/list done`**
  1. `/list add Spesa Pane` (aggiunge "Pane" alla lista "Spesa")
  2. `/lista Spesa` (mostra gli elementi presenti nella lista "Spesa")
  3. `/list done Spesa Pane` (spunta l'elemento "Pane" come acquistato)
* **`/reminder` / `/reminders`**
  *(Vedi la sezione dedicata qui sotto per tutti i dettagli sul funzionamento)*
  1. `/reminder comprare il latte alle 18:30` (imposta un promemoria per le 18:30)
  2. `/reminders` (mostra i promemoria attivi con i loro ID per poterli annullare)
  3. `/ricorda telefonare a Marco tra 15 minuti` (imposta un promemoria relativo)
* **`/meteo`**
  1. `/meteo Roma` (mostra il meteo per Roma)
  2. `/weather Milano` (mostra la situazione meteorologica di Milano)
  3. `/tempo` (mostra il meteo per la città predefinita configurata nel sistema)

---

## ⏰ Focus: Come usare i Promemoria (`/reminder` vs `/reminder.set_reminder`)

Il plugin dei promemoria ha due modi per essere invocato tramite i comandi diretti. Comprendere la differenza è fondamentale per evitare errori di sintassi.

### 1. Il comando amichevole: `/reminder`
Questo è il comando progettato per gli esseri umani. Utilizza un parser intelligente (in linguaggio naturale) che analizza la tua frase, estrae la data/ora e il titolo del promemoria e imposta tutto correttamente.

* **Sintassi:** `/reminder <titolo del promemoria> alle <ora/data>`
* **Come funziona:** Il sistema legge il testo dopo il comando, cerca parole chiave come "alle", "il", "tra", "in" e calcola automaticamente il momento corretto.

#### Esempi di utilizzo corretto:
1. **`/reminder ritirare i vestiti in lavanderia alle 17:45`** (imposta un promemoria per oggi alle 17:45)
2. **`/ricorda spegnere il forno tra 20 minuti`** (imposta un promemoria relativo che scadrà esattamente tra 20 minuti)
3. **`/promemoria compleanno della mamma il 25/08 alle 09:00`** (imposta un promemoria per una data specifica futura)
4. **`/reminder togliere la torta dal forno tra 30 minuti --interactive`** (usa il flag `--interactive` o `-i` alla fine per forzare un promemoria interattivo che suona in loop finché non viene stoppato o posticipato)

> [!TIP]
> Se vuoi vedere i promemoria salvati o devi annullarne uno, digita `/reminders`. Ti mostrerà una lista con degli identificativi ID da 8 caratteri. A quel punto puoi eliminare un promemoria usando il comando auto-generato `/reminder.cancel_reminder <ID>` (es. `/reminder.cancel_reminder a1b2c3d4`).

---

### 2. Il comando tecnico/auto-generato: `/reminder.set_reminder`
Questo comando fa parte dei comandi auto-generati dal sistema (vedi sotto) ed è associato direttamente alla funzione Python interna del plugin. 

* **Perché NON usarlo direttamente in chat:** La funzione Python si aspetta argomenti ben precisi e strutturati. Se scrivi semplicemente `/reminder.set_reminder comprare il latte alle 18:30`, il sistema assegnerà l'intera stringa `"comprare il latte alle 18:30"` al primo parametro (`title`), lasciando vuoto il secondo parametro richiesto (`when`). Questo provocherà un errore del tipo:
  `❌ Argomenti errati per /reminder.set_reminder` (missing required argument 'when').
* **Quando usarlo:** È utilissimo all'interno dei **Flussi (Flows)** dove i dati e i parametri vengono passati in modo esplicito tramite campi separati, oppure se si passa un singolo argomento strutturato per funzioni che richiedono solo quello.

---

## ⚙️ Comandi Avanzati Auto-generati (`/<tag>.<method>`)

Hecos ha una caratteristica speciale: **genera automaticamente un comando diretto per ogni singolo strumento (tool) di ogni plugin o modulo caricato**, nel formato:
`/<tag_plugin>.<nome_metodo>`

Questi comandi sono pensati principalmente per programmatori o per essere inseriti nei nodi dei Flussi, ma sono a tua disposizione anche nella chat o nella Spotlight.

### Come funzionano?
Quando esegui un comando del tipo `/<tag>.<method> <argomenti>`, Hecos prende tutto il testo che scrivi dopo lo spazio e lo passa come **primo argomento** alla funzione del plugin. Se la funzione richiede un solo parametro, funzionerà perfettamente al primo colpo!

#### Esempi di comandi auto-generati comuni:
* **`/executor.reboot_system`** (riavvia il sistema Hecos)
  * Esempio 1: `/executor.reboot_system` (riavvia immediatamente senza parametri)
  * Esempio 2: `/executor.reboot_system`
  * Esempio 3: `/executor.reboot_system`
* **`/executor.kill_process`** (termina un processo di Windows per nome)
  * Esempio 1: `/executor.kill_process chrome.exe` (termina Google Chrome)
  * Esempio 2: `/executor.kill_process notepad` (chiude il Blocco Note)
  * Esempio 3: `/executor.kill_process vlc` (chiude il lettore multimediale VLC)
* **`/browser.open_url`** (apre una pagina web nel browser controllato dall'AI)
  * Esempio 1: `/browser.open_url https://www.google.com` (naviga su Google)
  * Esempio 2: `/browser.open_url https://wikipedia.org` (apre Wikipedia)
  * Esempio 3: `/browser.open_url localhost:7070` (apre la WebUI locale)
