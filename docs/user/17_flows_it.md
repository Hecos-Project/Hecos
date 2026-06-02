# Modulo Flows: Automazioni Visive

Il modulo **Flows** di Hecos è il "direttore d'orchestra" del sistema. Ti permette di creare automazioni, routine e comportamenti complessi concatenando azioni in modo logico e sequenziale. 

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

- **Output As (Variable)**: Molti nodi generano un risultato (es. la lettura dell'orario, l'esito di un calcolo, la risposta di una API). Se inserisci un nome in questo campo (es. `valore_meteo`), il risultato prodotto da questo nodo diventerà una **Variabile**. I nodi successivi potranno usare questa variabile nei propri Parametri scrivendo `{{ valore_meteo }}` (grazie alla sintassi Jinja2).
- **Depends On (Comma-separated IDs)**: Un elenco separato da virgola con gli **Step ID** di tutti i nodi che devono concludersi _con successo_ prima che questo nodo possa anche solo iniziare (es. `step1, step_download`). Permette di forzare l'esecuzione sequenziale.

---

## 4. Catalogo Completo dei Nodi (Core Actions)

Il modulo Flows integra in maniera nativa **15 azioni**. Oltre a queste, Hecos importa automaticamente tutte le azioni relative ai Plugin di sistema attivi (ad esempio la fotocamera `WEBCAM__capture`, o la mail `MAIL__send`). 

Di seguito l'elenco dei 15 blocchi fondamentali di Hecos Flows:

### 🛠️ Categoria LOGIC
Registi e vigili del traffico: servono per ritardare, sdoppiare, unire e valutare le decisioni all'interno del flusso.
1. **LOGIC__delay**: Mette in pausa l'esecuzione del flusso. _[Parametri: `seconds` (numero)]_
2. **LOGIC__set_variable**: Assegna un valore esplicito a una nuova variabile nel flusso. _[Parametri: `name`, `value`]_
3. **LOGIC__if_else**: Valuta un'espressione matematica/logica e biforca il flusso. _[Parametri: `condition`, `true_branch`, `false_branch`]_
4. **LOGIC__switch**: Esegue comandi diversi in base a una specifica condizione. _[Parametri: `expression`, `branches`, `default`]_
5. **LOGIC__loop**: Passa in rassegna ed elabora un un elenco ripetutamente. _[Parametri: `over`, `as_var`, `body`]_
6. **LOGIC__template**: Genera o modifica un testo Jinja2 interpolando le variabili. _[Parametri: `template`, `output_as`]_
7. **LOGIC__and_gate**: Porta a termine il flusso *SOLO SE* svariate condizioni sono tutte contemporaneamente vere. _[Parametri: `conditions`, `on_success`, `on_fail`]_
8. **LOGIC__or_gate**: Esegue se *ALMENO UNA* condizione è vera. _[Parametri: `conditions`, `on_success`, `on_fail`]_
9. **LOGIC__http_request**: Chiama le API o i servizi su internet e converte e salva la risposta in una variabile per te. _[Parametri: `method`, `url`, `headers`, `body`, `output_as`]_

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
