# 🔀 7. Flows: Automazioni Visive

Il modulo **Flows** di Hecos è il "direttore d'orchestra" del sistema. Ti permette di creare automazioni, routine e comportamenti complessi concatenando azioni in modo logico e sequenziale. 

![Hecos - Flows Automations](https://github.com/Hecos-Project/Hecos-Assets/blob/main/////010_Hecos_Flows_001.png?raw=true)

Puoi creare un flusso usando il linguaggio naturale (ci penserà l'IA a scriverlo per te), disegnandolo tramite il **Canvas Visuale** (Node Palette), o scrivendolo direttamente in formato **YAML**.

---

## 1. Come Funziona (Concetti Chiave)

Un Flow è composto da una serie di **Nodi** (o *Steps*). Ogni nodo esegue un'unica operazione specifica (ad esempio: attendere 5 secondi, inviare un'email, leggere una stringa).
- **Esecuzione Lineare o Parallela**: I nodi possono essere collegati tra loro. Se il *Nodo B* ha una dipendenza (`depends_on`) dal *Nodo A*, il *Nodo B* verrà eseguito solo quando il *Nodo A* avrà terminato con successo. Due nodi senza dipendenze partiranno in parallelo!
- **Condivisione Variabili**: Un nodo può salvare il suo risultato usando l'opzione `output_as`. Ad esempio, un nodo che controlla il meteo può salvare il risultato come `weather_data` ed un nodo successivo può leggere quel dato.
- **Trigger**: Ogni flusso ha un *innesco*. Può essere manuale (attivato da un clic), temporale (es. CRON "ogni lunedì") o basato su un evento di sistema (es. ricezione di un messaggio).

---

## 2. Il Formato YAML e il parametro `key`

Dietro le quinte (o nell'editor YAML integrato), ogni flusso è descritto in formato YAML (uno standard estremamente leggibile e diffuso). 
A differenza del `JSON` (che utilizza rigide parentesi graffe e virgolette continue `{"chiave": "valore"}`), lo **YAML** usa la semplice indentazione (spazi) e la sintassi `chiave: valore` (in inglese, "key-value").

![Hecos - Flows Automations](https://github.com/Hecos-Project/Hecos-Assets/blob/main//////011_Hecos_Flows_002.png?raw=true)

### 💡 Risolvere il dubbio sulla "key"
Quando ti trovi nel Node Editor (doppio clic su un nodo) e leggi "Parameters (YAML)", oppure quando vedi un parametro chiamato `key` in informatica, significa semplicemente il **nome identificativo di quel parametro**.

Ad esempio, se il sistema aspetta un parametro YAML fatto in questo modo:
```yaml
text: Buongiorno, sei pronto per iniziare la giornata?
sound: alarm_1
```
In questo esempio:
- `text` è la **key** (la chiave/nome del parametro).
- `Buongiorno, sei pronto...` è il **value** (il contenuto/valore assegnato).
Non devi mai scrivere esplicitamente la parola `{key: qualcosa}`, ma devi usare i nomi corretti previsti dal nodo (es. `text: ...`, `seconds: ...`).

---

## 3. Node Editor: I parametri spiegati

Quando fai doppio clic su un nodo nel Canvas, si apre il **Node Editor**. Ecco a cosa servono i vari campi visualizzati:

- **Step ID (Unique)**: L'identificativo univoco di questo specifico nodo (es. `notifica_telegram`). Non può contenere spazi. Serve per permettere ad altri nodi di indicare _questo specifico nodo_ come dipendenza.
- **Action**: Il modulo da eseguire (es. `AUDIO__speak`, `LOGIC__delay`, `MAIL__send`). Determina quale funzione specifica farà il nodo.
- **Parameters (YAML)**: Qui si inserisce la configurazione del nodo, impiegando la sintassi YAML. È dove passi alla macchina i dati di cui ha bisogno. Esempio per `AUDIO__speak`: 
  ```yaml
  text: Ciao Universo, sono Hecos.
  ```

  > [!IMPORTANT]
  > **Ogni nodo accetta solo i propri parametri specifici!**
  > Ad esempio, scrivere `text: Ciao` funziona **solo** per i nodi che parlano o scrivono (come `AUDIO__speak` o `SYSTEM__chat_message`). Se lo scrivi dentro un `LOGIC__delay`, il nodo lo ignorerà o darà errore, perché il delay accetta esclusivamente la chiave `seconds: 10`. 
  > Da adesso, quando trascini un nodo nella tela, **i suoi parametri obbligatori ti appariranno già pre-compilati in automatico** (con valori come `<string>` o `0`). Dovrai solo sovrascrivere il valore di esempio con i tuoi dati reali!

- **Output As (Variable)**: Molti nodi generano un risultato (es. la lettura dell'orario, l'esito di un calcolo, la risposta di una API). Se inserisci un nome in questo campo (es. `valore_meteo`), il risultato prodotto by questo nodo diventerà una **Variabile**. I nodi successivi potranno usare questa variabile nei propri Parametri scrivendo `{{ valore_meteo }}` (grazie alla sintassi Jinja2).

![Hecos - Flows Automations](https://github.com/Hecos-Project/Hecos-Assets/blob/main///////012_Hecos_Flows_003.png?raw=true)

  Ecco 3 esempi pratici completi per farti capire esattamente come "far viaggiare" i dati tra i blocchi:

  **Esempio 1: Passaggio di Testo (Notifica Meteo)**
  Immagina di avere un nodo API che scarica il meteo e di volerlo far leggere ad alta voce. 
  1. Nel nodo API (`LOGIC__http_request`), imposta il campo *Output As* su `risultato_meteo`. Questo salva la risposta di internet in una variabile.
  2. Collega questo nodo in avanti a un nuovo nodo di Sintesi Vocale (`AUDIO__speak`).
  3. Fai doppio clic sul nodo vocale per aprirne i Parametri. Alla voce *text*, scrivi esattamente: `Attenzione, le previsioni dicono: {{ risultato_meteo }}`.
  Quando il flusso verrà eseguito dal vivo, Hecos non leggerà le graffe ma le sostituirà al volo col vero bollettino! Questo significa comunicare tra blocchi.

  **Esempio 2: Operazioni Matematiche e Scelte (Logica Condizionale)**
  Le Variabili possono trasportare numeri, ideali per stabilire percorsi alternativi.
  1. Aggiungi un nodo configurato per estrarre l'orario di sistema e chiama l'*Output As* `orario_attuale`.
  2. Collega questo nodo ad un vero e proprio "Bivio" decisionale usando un blocco `LOGIC__if_else`.
  3. Nel parametro *condition* (Condizione) scrivi: `{{ orario_attuale.ora }} > 12`. 
  L'espressione viene letta matematicamente. Ora il sistema sa che deve prendere la strada *True* (Vero) quando sono passate le ore 12, portando le automazioni a diramarsi intelligentemente su basi create pochi millisecondi prima dai blocchi superiori.

  **Esempio 3: Fondere Varie Cose (AI e Catene Lunghe)**
  Niente ti vieta di combinare e mescolare tantissime parentesi graffe nello stesso campo!
  1. Ipotizza di aver già fatto fluire un output che rappresenta lo stato della casa `luci_spente` e un altro che rappresenta il `nome_utente`.
  2. Metti in lavagna un potentissimo nodo "Cervello", l'`AI__prompt`.
  3. Nel campo del *prompt* libero, scrivi: `"Caro agente, fai un riepilogo ironico sullo stato di {{ luci_spente }} e saluta il mio capo che si chiama {{ nome_utente }}."`
  4. Imposta l'*Output As* di questo grande nodo testuale appena inserito su `traduzione_finita`. Potrai a tua volta passare il risultato a una `MAIL__send` infilando semplicemente `{{ traduzione_finita }}` dentro al contenuto (Body) della e-mail!
- **Depends On (Comma-separated IDs)**: Un elenco separato da virgola con gli **Step ID** di tutti i nodi che devono concludersi _con successo_ prima che questo nodo possa anche solo iniziare (es. `step1, step_download`). Permette di forzare l'esecuzione sequenziale.

---

## 4. Catalogo Completo dei Nodi (Core Actions)

Il modulo Flows integra in maniera nativa **19 azioni**. Oltre a queste, Hecos importa automaticamente tutte le azioni relative ai Plugin di sistema attivi (ad esempio la fotocamera `WEBCAM__capture`, o la mail `MAIL__send`). 

Di seguito l'elenco dei blocchi fondamentali di Hecos Flows:

### 🛠️ Categoria LOGIC
Registi e vigili del traffico: servono per ritardare, sdoppiare, unire e valutare le decisioni all'interno del flusso.

---

#### 1. `LOGIC__delay` — Pausa cronometrata
Mette in pausa l'esecuzione del flusso per un numero preciso di secondi prima di passare al nodo successivo.

| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| `seconds` | numero | Secondi di attesa (es. `5`, `30`, `120`) |

```yaml
- id: pausa_5_secondi
  action: LOGIC__delay
  params:
    seconds: 5
```

---

#### 2. `LOGIC__set_variable` — Imposta una variabile
Crea o sovrascrive una variabile nel contesto del flusso con un valore statico o dinamico (Jinja2). A differenza di `output_as`, questa variabile è disponibile per **tutti** i nodi successivi senza dipendenze esplicite.

| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| `name` | stringa | Nome della variabile da creare (es. `nome_utente`) |
| `value` | qualsiasi | Valore da assegnare. Può contenere `{{ variabili }}` |

```yaml
- id: imposta_soglia
  action: LOGIC__set_variable
  params:
    name: soglia_temperatura
    value: 25

- id: saluto_personalizzato
  action: LOGIC__set_variable
  params:
    name: messaggio
    value: "Buongiorno {{ nome_utente }}, la soglia è {{ soglia_temperatura }}°C"
```

---

#### 3. `LOGIC__if_else` — Bivio condizionale _(il più usato!)_
Valuta un'espressione logica/matematica Jinja2 e **esegue uno solo** dei due rami: `true_branch` se la condizione è vera, `false_branch` se è falsa.

> [!IMPORTANT]
> **Perché il nodo esegue entrambi i rami?** Se lasci `condition` vuoto o non lo compili, il motore usa `false` come valore predefinito e sceglie sempre il ramo `false_branch`. Se lasci vuoto sia `true_branch` che `false_branch`, non succede nulla. Assicurati di compilare tutti e tre i campi!

| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| `condition` | stringa Jinja2 | L'espressione da valutare. **Deve restituire vero o falso.** Usa `{{ variabile }}` per i dati dinamici. |
| `true_branch` | dict | Il nodo da eseguire se la condizione è **vera**. Contiene `action` e `params`. |
| `false_branch` | dict | Il nodo da eseguire se la condizione è **falsa**. Contiene `action` e `params`. |

**Esempi di condizioni valide:**
```yaml
# Confronto numerico
condition: "{{ temperatura | int }} > 30"

# Confronto di stringhe
condition: "{{ stato }} == 'attivo'"

# Valore booleano diretto da API
condition: "{{ sensore.rilevato == true }}"

# Confronto dell'ora (notazione a punto per dizionari)
condition: "{{ orario.ora | int }} > 12"
```

**Esempio completo — Termostato intelligente:**
```yaml
- id: controlla_temperatura
  action: LOGIC__if_else
  params:
    condition: "{{ temp_attuale | int }} > 28"
    true_branch:
      action: AUDIO__speak
      params:
        text: "Fa caldo! La temperatura è {{ temp_attuale }} gradi. Accendo il condizionatore."
    false_branch:
      action: SYSTEM__chat_message
      params:
        text: "Temperatura nella norma: {{ temp_attuale }}°C."
  depends_on:
    - leggi_sensore
```

**Esempio con più azioni in un ramo (lista):**
```yaml
- id: check_allarme
  action: LOGIC__if_else
  params:
    condition: "{{ movimento_rilevato == true }}"
    true_branch:
      - action: AUDIO__speak
        params:
          text: "Attenzione! Movimento rilevato!"
      - action: AUDIO__play_alarm
        params:
          sound: alarm_urgent
    false_branch:
      action: SYSTEM__chat_message
      params:
        text: "Nessun movimento. Casa al sicuro."
```

---

#### 4. `LOGIC__switch` — Selettore multiplo
Routing avanzato: valuta un'espressione e la usa come **chiave** per scegliere quale azione eseguire tra più possibilità. È come un if/else con tanti rami.

| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| `expression` | stringa Jinja2 | L'espressione il cui risultato (stringa) viene usato come chiave di ricerca |
| `branches` | dict | Mappa `chiave: azione` — ogni chiave corrisponde a un possibile valore dell'espressione |
| `default` | dict | Azione di fallback se nessuna chiave corrisponde (opzionale) |

```yaml
- id: scegli_saluto
  action: LOGIC__switch
  params:
    expression: "{{ momento_giornata }}"
    branches:
      mattina:
        action: AUDIO__speak
        params:
          text: "Buongiorno! Pronti per una giornata produttiva?"
      pomeriggio:
        action: AUDIO__speak
        params:
          text: "Buon pomeriggio! Come procede il lavoro?"
      sera:
        action: AUDIO__speak
        params:
          text: "Buonasera! Ora puoi rilassarti."
    default:
      action: AUDIO__speak
      params:
        text: "Ciao! Non so che ora sia, ma sono qui per te."
```

---

#### 5. `LOGIC__loop` — Ciclo su lista
Itera su ogni elemento di una lista (salvata in una variabile) ed esegue un'azione per ciascuno.

| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| `over` | stringa | Il nome della variabile che contiene la lista (es. `destinatari`) |
| `as_var` | stringa | Il nome della variabile temporanea per l'elemento corrente (es. `email`) |
| `body` | dict | L'azione da eseguire per ogni elemento. Puoi usare `{{ as_var }}` nei params. |

```yaml
# Esempio: manda un messaggio vocale a ogni membro della lista
- id: init_lista
  action: LOGIC__set_variable
  params:
    name: stanze
    value:
      - cucina
      - salotto
      - camera

- id: annuncia_in_ogni_stanza
  action: LOGIC__loop
  params:
    over: stanze
    as_var: stanza
    body:
      action: SYSTEM__chat_message
      params:
        text: "Controllo completato per: {{ stanza }}"
  depends_on:
    - init_lista
```

---

#### 6. `LOGIC__template` — Costruttore di testo Jinja2
Rende (interpola) un template Jinja2 combinando variabili e lo salva come nuova variabile. Perfetto per comporre messaggi complessi prima di inviarli.

| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| `template` | stringa Jinja2 | Il testo con le variabili da sostituire (usa `{{ variabile }}`) |
| `output_as` | stringa | Nome della variabile in cui salvare il risultato finale |

```yaml
- id: componi_report
  action: LOGIC__template
  params:
    template: |
      Report del {{ data_oggi }}
      Temperatura: {{ temp }}°C
      Stato: {{ 'OK' if temp|int < 30 else 'CRITICO' }}
    output_as: testo_report
  depends_on:
    - leggi_dati

- id: invia_report
  action: MAIL__send
  params:
    to: admin@casa.it
    subject: Report giornaliero
    body: "{{ testo_report }}"
  depends_on:
    - componi_report
```

---

#### 7. `LOGIC__and_gate` — Porta AND (tutte le condizioni)
Esegue `on_success` **solo se TUTTE** le condizioni nella lista sono vere. Se anche solo una è falsa, esegue `on_fail`.

| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| `conditions` | lista di stringhe | Lista di espressioni Jinja2 da valutare. Tutte devono essere vere. |
| `on_success` | dict | Azione da eseguire se **tutte** le condizioni passano |
| `on_fail` | dict | Azione da eseguire se **almeno una** condizione fallisce (opzionale) |

```yaml
- id: verifica_sicurezza
  action: LOGIC__and_gate
  params:
    conditions:
      - "{{ serratura.chiusa == true }}"
      - "{{ allarme.attivo == true }}"
      - "{{ temperatura.celsius | int }} < 40"
    on_success:
      action: SYSTEM__chat_message
      params:
        text: "✅ Casa sicura: serratura chiusa, allarme attivo, temperatura OK."
    on_fail:
      action: AUDIO__speak
      params:
        text: "Attenzione! Almeno una condizione di sicurezza non è soddisfatta!"
  depends_on:
    - check_lock
    - check_alarm
    - check_temp
```

---

#### 8. `LOGIC__or_gate` — Porta OR (almeno una condizione)
Esegue `on_success` se **ALMENO UNA** delle condizioni è vera. Esegue `on_fail` solo se **nessuna** condizione è vera.

| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| `conditions` | lista di stringhe | Lista di espressioni Jinja2. Basta che una sia vera. |
| `on_success` | dict | Azione se almeno una condizione è vera |
| `on_fail` | dict | Azione se nessuna condizione è vera (opzionale) |

```yaml
- id: notifica_se_anomalia
  action: LOGIC__or_gate
  params:
    conditions:
      - "{{ cpu_usage | int }} > 90"
      - "{{ ram_usage | int }} > 85"
      - "{{ disco_pieno == true }}"
    on_success:
      action: AUDIO__speak
      params:
        text: "Attenzione: il sistema sta esaurendo le risorse! Controlla subito."
    on_fail:
      action: SYSTEM__chat_message
      params:
        text: "Sistema in salute. Nessuna anomalia rilevata."
```

---

#### 9. `LOGIC__http_request` — Chiamata API/Web
Esegue una richiesta HTTP verso qualsiasi URL e salva la risposta JSON (o testo) in una variabile. È il nodo con cui colleghi Hecos al mondo esterno.

| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| `method` | stringa | Metodo HTTP: `GET`, `POST`, `PUT`, `DELETE` |
| `url` | stringa | URL di destinazione. Supporta Jinja2 (es. `https://api.esempio.it/{{ id }}`) |
| `headers` | dict | Headers opzionali (es. `Authorization: Bearer TOKEN`) |
| `body` | dict o stringa | Corpo della richiesta per POST/PUT (opzionale) |
| `output_as` | stringa | Nome variabile in cui salvare la risposta JSON parsata |

```yaml
# GET semplice — meteo attuale
- id: scarica_meteo
  action: LOGIC__http_request
  params:
    method: GET
    url: "https://api.open-meteo.com/v1/forecast?latitude=41.9&longitude=12.5&current_weather=true"
    output_as: dati_meteo

# Leggi il risultato nel nodo successivo
- id: annuncia_meteo
  action: AUDIO__speak
  params:
    text: "La temperatura attuale a Roma è {{ dati_meteo.current_weather.temperature }} gradi."
  depends_on:
    - scarica_meteo

# POST con autenticazione — notifica webhook
- id: notifica_webhook
  action: LOGIC__http_request
  params:
    method: POST
    url: "https://hooks.esempio.it/notify"
    headers:
      Authorization: "Bearer il-mio-token-segreto"
      Content-Type: "application/json"
    body:
      evento: "flow_completato"
      messaggio: "{{ risultato }}"
    output_as: risposta_webhook
```

### ⏰ Categoria TRIGGER
Indicano il modo in cui questa automazione "prenderà vita" (anche se questi campi modificano la root del flusso e non semplici blocchi standard).
10. **TRIGGER__cron**: Il flusso parte automaticamente ad orari prestabiliti seguendo lo standard UNIX Cron (es. `0 7 * * *`). _[Parametri: `expression`]_
11. **TRIGGER__interval**:  Il flusso continua a ripetersi costantemente ogni "N" tempo (es. ogni 10 `minutes`). _[Parametri: `every`, `unit`]_
12. **TRIGGER__manual**: Questo flusso è configurato unicamente per essere lanciato con l'uso manuale dal pulsante "Play". Nessuna esecuzione autonoma nascosta. _[Nessun Parametro]_

### 🔊 Categoria AUDIO
Interessano gli eventi multimediali base all'interno del dispositivo primario.
13. **AUDIO__speak**: Attiva il sintetizzatore vocale Text-to-Speech per farti parlare direttamente dall'AI. _[Parametri: `text`]_
14. **AUDIO__play_alarm**: Avvia una delle suonerie o sirene pre-memorizzate all'interno di Hecos. _[Parametri: `sound`]_

### 💬 Categoria SYSTEM
Interagiscono direttamente con il nucleo e l'interfaccia dell'AI primaria.
15. **SYSTEM__chat_message**: Salva e stampa visivamente un messaggio nella cronologia della Chat classica di Hecos, come se l'assistente ti stesse scrivendo. _[Parametri: `text`]_

### 🧠 Categoria AI
Permette ai Flows di interagire **bidirezionalmente** con il cervello dell'AI: non solo di scrivere messaggi, ma di inviare veri e propri prompt all'AI e catturarne la risposta come variabile.
16. **AI__prompt**: Invia un prompt testuale all'AgentExecutor di Hecos (il cervello completo, inclusi routing, plugin e tool calls). Il flusso si **blocca** fino a quando l'AI non ha terminato di rispondere, poi il testo della risposta viene restituito e salvabile tramite `output_as`. _[Parametri: `prompt` (string), `save_to_chat` (bool, default: true)]_
   > Nota: con `save_to_chat: true`, la coppia prompt+risposta viene scritta nella cronologia chat come `[Flow] testo del prompt` (ruolo utente) e la risposta dell'AI (ruolo assistente), così puoi sempre rivedere cosa ha pensato il flusso.

---

### 🧭 Categoria CONTROL
Nodi di controllo dell'esecuzione dei flussi.

#### 17. `CONTROL__start` — Punto d'Ingresso del Flusso
Funge da punto d'ingresso obbligatorio per l'esecuzione del flusso. Qualsiasi nodo non collegato (direttamente o indirettamente tramite dipendenze `depends_on`) a `CONTROL__start` non verrà eseguito. Questo previene l'esecuzione accidentale di rami fluttuanti o isolati.

Se un flusso contiene uno o più nodi `CONTROL__start`, l'esecuzione inizierà esclusivamente da essi. Se il nodo `CONTROL__start` è disabilitato (con `disable_mode: stop`), l'esecuzione dell'intero flusso fallirà immediatamente.

| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| `priority` | numero intero | Ordine di priorità di avvio (default: `0`). I nodi start con valore inferiore partono prima (es. `0` prima di `1`). |

**Esempio 1: Avvio lineare semplice**
Un flusso base che parte esplicitamente da Start e dice ciao.
```yaml
- id: start_1
  action: CONTROL__start
  params:
    priority: 0

- id: notifica_ciao
  action: AUDIO__speak
  params:
    text: "Sistema pronto e avviato."
  depends_on:
    - start_1
```

**Esempio 2: Esecuzione ordinata di rami multipli**
Due nodi di avvio eseguiti in sequenza temporale grazie alla priorità. `inizializza` parte per primo, poi parte `avvio_operazione`.
```yaml
- id: inizializza
  action: CONTROL__start
  params:
    priority: 0

- id: set_var
  action: LOGIC__set_variable
  params:
    name: stato_sistema
    value: "pronto"
  depends_on:
    - inizializza

- id: avvio_operazione
  action: CONTROL__start
  params:
    priority: 1

- id: esegui_task
  action: SYSTEM__chat_message
  params:
    text: "Esecuzione avviata. Stato del sistema: {{ stato_sistema }}"
  depends_on:
    - avvio_operazione
```

**Esempio 3: Flusso di sicurezza all'avvio**
All'avvio, il flusso verifica una condizione prima di proseguire, fermandosi se necessario.
```yaml
- id: start_sicurezza
  action: CONTROL__start
  params:
    priority: 0

- id: controlla_connessione
  action: LOGIC__http_request
  params:
    method: GET
    url: "https://api.ipify.org?format=json"
    output_as: ip_data
  depends_on:
    - start_sicurezza

- id: verifica_ip
  action: LOGIC__if_else
  params:
    condition: "{{ ip_data is defined and ip_data.ip != '' }}"
    true_branch:
      action: SYSTEM__chat_message
      params:
        text: "Verifica completata. IP: {{ ip_data.ip }}"
    false_branch:
      action: LOGIC__abort
      params:
        reason: "Nessuna connessione internet all'avvio."
  depends_on:
    - controlla_connessione
```

---

### 🔄 Categoria FLOWS
Nodi dedicati alla gestione e all'orchestrazione di altri flussi.

#### 18. `FLOWS__run_flow` — Esegui Flusso Esterno
Consente di chiamare ed eseguire un altro flusso salvato all'interno di Hecos, permettendo di strutturare le automazioni in modo modulare (come sub-routine o librerie).

| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| `flow_id` | stringa | L'ID del flusso esterno da eseguire (es. lo slug/nome file, `morning_routine`) |
| `wait` | booleano | Se `true` (default), attende che il sotto-flusso finisca prima di procedere. Se `false`, lo avvia in background in parallelo. |
| `pass_context` | booleano | Se `true` (default), passa tutte le variabili correnti del flusso chiamante al sotto-flusso. |

**Esempio 1: Esecuzione modulare sincrona (Attesa)**
Il flusso principale esegue il sotto-flusso di spegnimento luci, aspetta che finisca, e poi annuncia la buonanotte.
```yaml
- id: start_1
  action: CONTROL__start

- id: spegni_casa
  action: FLOWS__run_flow
  params:
    flow_id: "spegnimento_luci_totale"
    wait: true
    pass_context: false
  depends_on:
    - start_1

- id: saluto_finale
  action: AUDIO__speak
  params:
    text: "Tutte le luci sono state spente. Buonanotte!"
  depends_on:
    - spegni_casa
```

**Esempio 2: Esecuzione asincrona (Background - Fire and Forget)**
Il flusso avvia in background una sincronizzazione dati pesante senza bloccare l'interazione con l'utente o il resto del flusso corrente.
```yaml
- id: start_1
  action: CONTROL__start

- id: avvia_backup
  action: FLOWS__run_flow
  params:
    flow_id: "backup_giornaliero_nas"
    wait: false
    pass_context: true
  depends_on:
    - start_1

- id: notifica_immediata
  action: SYSTEM__chat_message
  params:
    text: "Il backup è stato avviato in background. Puoi continuare a usare Hecos liberamente."
  depends_on:
    - start_1
```

**Esempio 3: Passaggio di parametri dinamici**
Imposta delle variabili nel flusso chiamante e le passa al flusso figlio per personalizzarne l'output.
```yaml
- id: start_1
  action: CONTROL__start

- id: imposta_dati
  action: LOGIC__set_variable
  params:
    name: destinatario_notifica
    value: "Tony"
  depends_on:
    - start_1

- id: invia_notifica_personalizzata
  action: FLOWS__run_flow
  params:
    flow_id: "invia_notifica_telegram"
    wait: true
    pass_context: true
  depends_on:
    - imposta_dati
```

---

### 👤 Categoria USER
Nodi dedicati alle interazioni interattive dirette con l'utente.

#### 19. `USER__ask_input` — Richiesta Input Utente
Mette in pausa l'esecuzione del flusso e attende che l'utente fornisca un input tramite chat (scritto) o voce. La risposta ricevuta viene salvata nella variabile definita nel campo *Output As* del nodo (es. `input_utente`) per essere usata dai blocchi successivi.

In caso di interruzione o annullamento del flusso (tramite il pulsante "Stop"), il nodo rileva l'annullamento, interrompe l'attesa e termina in modo pulito.

| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| `prompt` | stringa | La domanda da inviare in chat e facoltativamente leggere a voce. |
| `speak` | booleano | Se `true` (default), legge il prompt ad alta voce tramite sintesi vocale (TTS). |
| `intercept_mode` | scelta (`auto`\|`explicit`\|`api_only`) | **auto**: qualsiasi messaggio in chat viene preso come risposta.<br>**explicit**: risponde solo se il messaggio inizia con `@flow` (es. `@flow 22`). Consigliato se si usano più chat contemporaneamente.<br>**api_only**: risponde solo tramite chiamata API POST a `/api/flows/<run_id>/input`. |
| `multi_run_priority`| scelta (`first`\|`all`) | Se ci sono più flussi in attesa di input:<br>**first**: assegna la risposta solo al flusso più vecchio.<br>**all**: invia la stessa risposta a tutti i flussi in attesa. |
| `timeout_seconds` | numero intero | Tempo massimo di attesa in secondi prima di scadere (default: `0` = attesa infinita). |
| `on_timeout_continue`| booleano | Se `true` (default: `false`), in caso di timeout continua l'esecuzione passando una stringa vuota (`""`) invece di mandare in errore il flusso. |

**Esempio 1: Decisione interattiva (Sì/No)**
Chiede all'utente se vuole sentire una barzelletta, intercetta qualsiasi risposta in chat e biforca l'esecuzione.
```yaml
- id: start_1
  action: CONTROL__start

- id: chiedi_scelta
  action: USER__ask_input
  params:
    prompt: "Ti va di ascoltare una barzelletta?"
    speak: true
    intercept_mode: "auto"
    timeout_seconds: 60
  output_as: risposta_barzelletta
  depends_on:
    - start_1

- id: valuta_risposta
  action: LOGIC__if_else
  params:
    condition: "'si' in {{ risposta_barzelletta | lower }} or 'ok' in {{ risposta_barzelletta | lower }}"
    true_branch:
      action: AUDIO__speak
      params:
        text: "Perché i computer non vanno mai in vacanza? Perché hanno troppe finestre da chiudere!"
    false_branch:
      action: SYSTEM__chat_message
      params:
        text: "Nessun problema, sarà per la prossima volta."
  depends_on:
    - chiedi_scelta
```

**Esempio 2: Setpoint numerico sicuro con timeout**
Chiede di inserire una temperatura target in modo esplicito (usando `@flow <temperatura>`). Se l'utente non risponde entro 15 secondi, prosegue usando il valore di default.
```yaml
- id: start_1
  action: CONTROL__start

- id: chiedi_temperatura
  action: USER__ask_input
  params:
    prompt: "A quanti gradi vuoi impostare il termostato? Rispondi scrivendo '@flow <gradi>'"
    speak: false
    intercept_mode: "explicit"
    timeout_seconds: 15
    on_timeout_continue: true
  output_as: gradi_scelti
  depends_on:
    - start_1

- id: verifica_e_imposta
  action: LOGIC__if_else
  params:
    condition: "{{ gradi_scelti != '' }}"
    true_branch:
      action: SYSTEM__chat_message
      params:
        text: "Imposto la temperatura a {{ gradi_scelti }} gradi."
    false_branch:
      action: SYSTEM__chat_message
      params:
        text: "Nessuna risposta. Mantengo la temperatura di default a 20 gradi."
  depends_on:
    - chiedi_temperatura
```

**Esempio 3: Sentiment Analysis dell'input**
Chiede all'utente come si sente, passa l'input all'AI per analizzarne l'umore e risponde di conseguenza.
```yaml
- id: start_1
  action: CONTROL__start

- id: chiedi_umore
  action: USER__ask_input
  params:
    prompt: "Ciao! Come sta andando la tua giornata oggi?"
    speak: true
    intercept_mode: "auto"
    timeout_seconds: 0
  output_as: umore_utente
  depends_on:
    - start_1

- id: analizza_sentiment
  action: AI__prompt
  params:
    prompt: "L'utente ha risposto: '{{ umore_utente }}'. Analizza l'umore (positivo/negativo/neutro) e rispondi con una sola frase di supporto o felicità adatta al suo umore."
    save_to_chat: true
  depends_on:
    - chiedi_umore
```

---

## 5. Esempi Pratici e Completi

Di seguito tre esempi di flussi YAML completi, perfetti per analizzare l'uso della root YAML e di come i nodi si comportano con le variabili (`output_as`), le dipendenze, e in parallelo.

### Esempio 1: Routine del Mattino con Variabili Dinamiche
Questo flusso introduce il concatenamento di parametri: Hecos acquisisce l'orario attuale ponendolo nella variabile `orario_attuale` grazie all'uso pratico di `output_as`, per poi farglielo recitare nello step successivo interpolandolo nelle parentesi graffe `{{ orario_attuale }}`.

```yaml
name: Morning Routine Avanzata
trigger:
  type: manual
pipeline:
  - id: step_sveglia
    action: AUDIO__play_alarm
    params:
      sound: gentle_wake

  - id: step_pausa
    action: LOGIC__delay
    params:
      seconds: 5
    depends_on:
      - step_sveglia

  - id: get_current_time
    action: EXECUTOR__get_time
    # Salviamo l'output nella variabile chiamata 'orario_attuale'
    output_as: orario_attuale
    depends_on:
      - step_pausa

  - id: step_buongiorno
    action: AUDIO__speak
    params:
      # Usiamo l'output generato dal blocco "get_current_time"
      text: "Buongiorno! Si sono fatte le ore {{ orario_attuale }}, devi alzarti da letto."
    depends_on:
      - get_current_time
```

### Esempio 2: Alert Sicurezza Domestico Multiplo (Parallelismo)
In questo flusso vedremo il **parallelismo in azione**. I due blocchi `notify_voice` e `send_email_alert` possiedono la stessa identica dipendenza (`wait_for_arming`). Questo significa che, una volta esaurito il blocco LOGIC__delay, Hecos eseguirà le due notifiche contemporaneamente assecondando il vero multitasking asincrono!

```yaml
name: Security Alert Multiplo
trigger:
  type: manual
pipeline:
  - id: wait_for_arming
    action: LOGIC__delay
    params:
      seconds: 30

  - id: notify_voice
    action: AUDIO__speak
    params:
      text: "Attenzione, è stato avviato e attivato il sistema di sicurezza automatico."
    depends_on:
      - wait_for_arming

  - id: send_email_alert
    action: MAIL__send
    params:
      to: admin@myhouse.com
      subject: "Allarme Hecos"
      body: "Ti notifichiamo che il sistema di sicurezza è stato armato alle tue spalle con successo."
    depends_on:
      - wait_for_arming
```

### Esempio 3: Controllo Dispositivo con API ed Eventi Sequenziali
Questo blocco chiama i server di un API per ottenere dei ritorni e, solo dopo una pausa, produce la chiusura. Immaginalo come una macro domotica verso Philips Hue o Home Assistant!

```yaml
name: Macchina del Caffè Intelligente
trigger:
  type: interval
  every: 6
  unit: hours
pipeline:
  - id: call_coffee_api
    action: LOGIC__http_request
    params:
      method: "POST"
      url: "http://192.168.1.50/api/coffee_maker/start"
      body:
        mode: "espresso_macchiato"

  - id: announce_start
    action: AUDIO__speak
    params:
      text: "L'operazione per fare un fantastico espresso è in corso."
    depends_on:
      - call_coffee_api

  - id: wait_brewing
    action: LOGIC__delay
    params:
      seconds: 40
    depends_on:
      - announce_start

  - id: announce_ready
    action: AUDIO__speak
    params:
      text: "Il tuo profumatissimo caffè è pronto in sala."
    depends_on:
      - wait_brewing
```

> Nota Bene: Tutti questi file di esempio rappresentano testualmente in modo esatto la struttura che viene gestita dal sistema quando colleghi, stacchi o scrivi i parametri all'interno della tua comoda Canvas grafica!

---

## 6. Esempi Avanzati: Scenari Reali e Bizzarri

Questi tre esempi dimostrano le vere potenzialità di Flows: algoritmi condizionali, catene di eventi temporizzate, e integrazioni in stile fantascienza. Usali come ispirazione e modifica i parametri per adattarli al tuo ambiente.

---

### 🧮 Esempio A — L'Algoritmo del Guardiano Bitcoin
*Scenario: ogni 10 minuti, Hecos interroga l'API di CoinGecko, recupera il prezzo corrente del Bitcoin, e prende una decisione: se il prezzo è crollato sotto i 60.000 €, urla come un forsennato e ti manda un'email urgente; se invece ha superato i 100.000 €, brinda esultando con te in chat. In caso contrario, registra silenziosamente il prezzo nel log.*

Questa è la forma più pura di un algoritmo: dati in entrata → elaborazione → azione condizionale.

```yaml
name: Bitcoin Watchdog Algorithm
trigger:
  type: interval
  every: 10
  unit: minutes
pipeline:
  # STEP 1: Chiama l'API pubblica di CoinGecko (zero API key, zero costi)
  - id: get_bitcoin_price
    action: LOGIC__http_request
    params:
      method: GET
      url: "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=eur"
      output_as: api_response

  # STEP 2: Estrai il valore numerico grezzo dalla risposta JSON
  - id: extract_price
    action: LOGIC__template
    params:
      template: "{{ api_response.bitcoin.eur }}"
      output_as: btc_price
    depends_on:
      - get_bitcoin_price

  # STEP 3: Costruisci un messaggio leggibile per l'utente
  - id: format_message
    action: LOGIC__template
    params:
      template: "Bitcoin ora vale {{ btc_price }} euro."
      output_as: price_summary
    depends_on:
      - extract_price

  # STEP 4: BIFORCAZIONE — Valuta il prezzo con if_else
  - id: check_crash
    action: LOGIC__if_else
    params:
      condition: "{{ btc_price | int }} < 60000"
      true_branch:
        action: AUDIO__speak
        params:
          text: "ALLERTA ROSSO! Bitcoin è crollato a {{ btc_price }} euro! Apri Coinbase ADESSO!"
      false_branch:
        action: SYSTEM__chat_message
        params:
          text: "📊 {{ price_summary }} — situazione nella norma."
    depends_on:
      - format_message

  # STEP 5 (parallelo al 4): Controlla anche l'ipotesi MOON
  - id: check_moon
    action: LOGIC__if_else
    params:
      condition: "{{ btc_price | int }} > 100000"
      true_branch:
        action: AUDIO__speak
        params:
          text: "AAAA! Abbiamo superato i centomila euro! Siamo su Marte! 🚀"
      false_branch:
        action: LOGIC__delay
        params:
          seconds: 1  # nessuna azione, attesa simbolica
    depends_on:
      - format_message

  # STEP 6: Se siamo in crash, manda anche un'email urgente
  - id: emergency_mail
    action: MAIL__send
    params:
      to: me@myemail.com
      subject: "⚠️ Bitcoin Crash Alert — Hecos Watchdog"
      body: "{{ price_summary }} — Il prezzo è sotto soglia critica. Controlla subito."
    depends_on:
      - check_crash
```

---

### 🍮 Esempio B — Il Cuoco Robotico: Soufflé al Cioccolato Step-by-Step
*Scenario: una ricetta interattiva che sostituisce il timer del telefono con Hecos che ti guida vocalmente passo-passo, con countdown precisi, allarmi, e promemoria in chat per ogni fase critica. Seguila e il tuo soufflé sarà perfetto.*

Questa è la forma di un flusso-ricetta procedurale: puro pipettaggio sequenziale con delay chirurgici.

```yaml
name: Ricetta Soufflé al Cioccolato
trigger:
  type: manual
pipeline:
  # FASE 1 - Preparazione: annuncio e impostazione variabili
  - id: begin_recipe
    action: AUDIO__speak
    params:
      text: "Benvenuto nella ricetta del soufflé al cioccolato. Prepara 200 grammi di cioccolato fondente, 4 uova e il burro."

  - id: set_oven_temp
    action: SYSTEM__chat_message
    params:
      text: "🍫 **RICETTA ATTIVA** — Preriscalda il forno a 190°C. Imburra e inzucchera 4 stampini da soufflé."
    depends_on:
      - begin_recipe

  # FASE 2 - Sciogliere il cioccolato (7 minuti bagnomaria)
  - id: announce_melt
    action: AUDIO__speak
    params:
      text: "Ora sciogli il cioccolato a bagnomaria. Avviserò tra 7 minuti."
    depends_on:
      - set_oven_temp

  - id: wait_melt
    action: LOGIC__delay
    params:
      seconds: 420  # 7 minuti
    depends_on:
      - announce_melt

  - id: alarm_melt_done
    action: AUDIO__play_alarm
    params:
      sound: chime_success
    depends_on:
      - wait_melt

  - id: say_melt_done
    action: AUDIO__speak
    params:
      text: "Il cioccolato è pronto. Togli dal fuoco e aggiungi il burro. Poi separa i tuorli dagli albumi."
    depends_on:
      - alarm_melt_done

  # FASE 3 - Montare gli albumi (stima 4 minuti con fruste elettriche)
  - id: announce_whip
    action: AUDIO__speak
    params:
      text: "Inizia a montare gli albumi a neve ferma. Ti avviso tra 4 minuti quando saranno pronti."
    depends_on:
      - say_melt_done

  - id: wait_whip
    action: LOGIC__delay
    params:
      seconds: 240  # 4 minuti
    depends_on:
      - announce_whip

  - id: say_whip_done
    action: AUDIO__speak
    params:
      text: "Albumi pronti! Incorporali delicatamente al cioccolato con movimenti dal basso verso l'alto. Poi riempi gli stampini per tre quarti."
    depends_on:
      - wait_whip

  # FASE 4 - Cottura in forno (12 minuti ESATTI, non aprire il forno!)
  - id: announce_baking
    action: AUDIO__speak
    params:
      text: "Metti in forno. Attenzione: tra dodici minuti precisi estraili. NON aprire il forno prima — esplodono!"
    depends_on:
      - say_whip_done

  - id: chat_baking_warning
    action: SYSTEM__chat_message
    params:
      text: "⏱️ **Cottura soufflé avviata** — Non aprire il forno! Timer: 12 minuti. Fine cottura prevista tra poco."
    depends_on:
      - say_whip_done

  - id: wait_baking
    action: LOGIC__delay
    params:
      seconds: 720  # 12 minuti esatti
    depends_on:
      - announce_baking

  - id: final_alarm
    action: AUDIO__play_alarm
    params:
      sound: alarm_urgent
    depends_on:
      - wait_baking

  - id: final_announcement
    action: AUDIO__speak
    params:
      text: "SUBITO! Estrai i soufflé dal forno ADESSO e servili immediatamente! Buon appetito!"
    depends_on:
      - final_alarm

  - id: final_chat
    action: SYSTEM__chat_message
    params:
      text: "✅ **Soufflé completato!** Servi entro 60 secondi dalla sfornata. Buon appetito, chef!"
    depends_on:
      - final_alarm
```

---

### 🤖 Esempio C — Il Sentinella della Notte (Fantascienza Domestica)
*Scenario: ogni notte a mezzanotte, Hecos si sveglia come un guardiano robotico silenzioso. Interroga tre API smart-home (serratura, camera di sorveglianza, sensore temperatura), valida i risultati con una AND-gate logica, e solo se tutto va bene ti manda un rapporto in chat. Se qualcosa è anomalo, lancia un allarme voce + un'email di allerta formattata su misura. Un vero sistema di sicurezza programmato in YAML.*

```yaml
name: Midnight Home Sentinel
trigger:
  type: cron
  expression: "0 0 * * *"  # ogni notte alle 00:00
pipeline:
  # FASE 1 - Annuncio silenzioso in chat (nessun audio - è notte!)
  - id: begin_patrol
    action: SYSTEM__chat_message
    params:
      text: "🌙 **Ronda Notturna Avviata** — Hecos sta verificando lo stato della casa..."

  # FASE 2 (parallelo) - Interroga 3 API smart-home contemporaneamente
  - id: check_lock
    action: LOGIC__http_request
    params:
      method: GET
      url: "http://192.168.1.10/api/smart_lock/status"
      output_as: lock_status
    depends_on:
      - begin_patrol

  - id: check_camera
    action: LOGIC__http_request
    params:
      method: GET
      url: "http://192.168.1.11/api/camera/motion_detected"
      output_as: camera_status
    depends_on:
      - begin_patrol

  - id: check_temperature
    action: LOGIC__http_request
    params:
      method: GET
      url: "http://192.168.1.12/api/thermostat/current_temp"
      output_as: temp_data
    depends_on:
      - begin_patrol

  # FASE 3 - AND GATE: procedi solo se serratura chiusa e nessun movimento
  - id: security_gate
    action: LOGIC__and_gate
    params:
      conditions:
        - "{{ lock_status.locked == true }}"
        - "{{ camera_status.motion == false }}"
      on_success:
        action: SYSTEM__chat_message
        params:
          text: "✅ **Casa SICURA** — Serratura: chiusa | Camera: nessun movimento | Temp: {{ temp_data.celsius }}°C"
      on_fail:
        action: AUDIO__speak
        params:
          text: "ATTENZIONE! La ronda notturna ha rilevato un'anomalia! Controlla immediatamente la casa!"
    depends_on:
      - check_lock
      - check_camera
      - check_temperature

  # FASE 4 - Componi un report formattato e mandalo via mail
  - id: compose_report
    action: LOGIC__template
    params:
      template: |
        RAPPORTO NOTTURNO HECOS — Mezzanotte
        Serratura: {{ lock_status.locked | ternary('CHIUSA', 'APERTA!!') }}
        Movimento Camera: {{ camera_status.motion | ternary('RILEVATO!!', 'Nessuno') }}
        Temperatura interna: {{ temp_data.celsius }}°C
        Stato generale: {{ 'TUTTO OK' if lock_status.locked and not camera_status.motion else 'ANOMALIA RILEVATA' }}
      output_as: night_report
    depends_on:
      - security_gate

  - id: send_night_report
    action: MAIL__send
    params:
      to: me@myemail.com
      subject: "🌙 Rapporto Notturno Hecos — Casa Monitorata"
      body: "{{ night_report }}"
    depends_on:
      - compose_report
```

> 💡 **Sfida bonus**: collega questo flow al modulo `WEBCAM__capture` per allegare uno scatto della camera interna al report notturno. Basta aggiungere un nodo tra `check_camera` e `compose_report`.

---

## 7. L'Executor e i Comandi di Sistema (Shell e Python)

Tra i nodi più potenti di Hecos ci sono quelli legati al modulo **EXECUTOR**. Questi nodi ti permettono di uscire dai confini dell'automazione standard e di impartire veri e propri ordini al tuo sistema operativo (Windows o Linux).

### 7.1 Esecuzione Visibile vs Invisibile (Background)

Quando usi la riga di comando (Shell) tramite Hecos, devi decidere se vuoi che l'utente veda cosa succede o se deve avvenire tutto di nascosto.

- **`EXECUTOR__execute_background_command`**: Questo nodo è progettato per eseguire comandi in modalità *silenziosa* (headless). Nessuna finestra nera si aprirà sul desktop. Il comando lavorerà nell'ombra e l'output verrà salvato in un file di log. È perfetto per scaricare file, avviare server o fare operazioni di manutenzione senza disturbarti. 
  *Attenzione*: Se scrivi semplicemente `cmd` o `bash` qui dentro, il nodo creerà un terminale invisibile che aspetterà all'infinito un tuo input, bloccando il flusso!
- **`EXECUTOR__execute_shell_command`**: Se desideri **aprire visibilmente** un programma o una finestra del prompt dei comandi sul desktop, devi "staccare" il processo usando il comando nativo del tuo sistema operativo, come `start` (su Windows) o `gnome-terminal` (su Linux).

> [!TIP]
> **Come eseguire più comandi di fila?** Non serve usare un nodo per ogni comando! Puoi usare l'operatore `&&` per concatenarli in un'unica stringa. Hecos li eseguirà rigorosamente in sequenza. Esempio: `ipconfig && mkdir nuova_cartella && echo "Finito!"`

#### Esempio 1: Creare una cartella silenziosamente (Background)
*Scenario: Un flusso crea una directory di backup senza mostrare nulla a schermo.*
```yaml
  - id: crea_backup_silenzioso
    action: EXECUTOR__execute_background_command
    params:
      command: "mkdir C:\backup_hecos && echo Backup folder created"
```

#### Esempio 2: Aprire un Prompt dei Comandi Visibile (Solo Windows)
*Scenario: Vuoi che Hecos apra una finestra nera del CMD, faccia un PING a Google, e mantenga la finestra aperta per farti leggere il risultato.*
```yaml
  - id: apri_cmd_visibile
    action: EXECUTOR__execute_shell_command
    params:
      # Il parametro /k ("keep") mantiene la finestra aperta. Usa /c ("close") per chiuderla.
      command: "start cmd /k \"ping 8.8.8.8 && echo Ping completato!\""
```

### 7.2 Il Problema della Multipiattaforma (Windows vs Linux)

Se scrivi `start cmd` in un nodo shell, hai appena reso il tuo flusso **incompatibile con Linux o Mac**. Su Linux, `cmd` non esiste e il flusso genererà un errore. Come si risolve questo problema se vuoi creare automazioni universali?

Hai due soluzioni:
1. **Usa i nodi nativi di Hecos**: Invece di usare `execute_shell_command` e scrivere `mkdir` o `taskkill`, usa i nodi dedicati dell'executor! Ad esempio: `EXECUTOR__create_dir`, `EXECUTOR__read_file` o `EXECUTOR__kill_process`. Hecos capirà da solo se sei su Windows o Linux ed eseguirà il comando giusto.
2. **Usa lo Script Maker definitivo: Python!**

### 7.3 `EXECUTOR__run_python_code`: Il vero Script Maker Universale

Invece di impazzire con comandi concatenati da `&&` o file `.bat`, puoi usare il nodo `EXECUTOR__run_python_code`. Questo nodo ti mette a disposizione un vero e proprio editor in cui puoi inserire uno script Python.

**Perché usare Python invece della Shell?**
- **È Multipiattaforma**: Lo stesso script Python funziona identico su Windows, Linux e Raspberry Pi.
- **È Potente**: Puoi usare cicli logici complessi, calcoli matematici, o formattare i dati molto meglio che in un prompt dei comandi.
- **Variabili**: Puoi restituire il risultato del tuo script (tramite `print`) per salvarlo in una variabile `output_as` e passarlo ai nodi successivi!

#### Esempio 3: Uno Script Python Multipiattaforma Universale
*Scenario: Uno script Python che capisce da solo su quale sistema operativo si trova, crea una cartella nella scrivania dell'utente in modo sicuro e restituisce l'esito a Hecos per farglielo pronunciare a voce.*
```yaml
  - id: script_python_universale
    action: EXECUTOR__run_python_code
    params:
      code: |
        import os
        from pathlib import Path
        
        # Trova la cartella Desktop sia su Windows che su Linux
        desktop_dir = Path.home() / "Desktop"
        nuova_cartella = desktop_dir / "Hecos_Magic_Folder"
        
        if not nuova_cartella.exists():
            nuova_cartella.mkdir()
            print("Ho creato la cartella magica sul desktop!")
        else:
            print("La cartella esisteva già, nessun problema.")
    output_as: esito_script

  - id: annuncia_esito
    action: AUDIO__speak
    params:
      text: "{{ esito_script }}"
    depends_on:
      - script_python_universale
```

In questo modo hai creato un'automazione che puoi condividere con chiunque, indipendentemente dal PC o dal sistema operativo che usano!
