# 18. Comandi Diretti (HDCS)

Immagina di avere una **bacchetta magica** che ti permette di dare ordini precisi ad Hecos senza dover fare lunghi discorsi con l'Intelligenza Artificiale. Questa bacchetta magica si chiama **HDCS (Hecos Direct Command System)**, o più semplicemente: i **Comandi Diretti**.

Normalmente, quando scrivi ad Hecos, l'AI deve leggere il tuo messaggio, pensare a cosa vuoi fare, scegliere lo strumento giusto e poi eseguirlo. A volte, però, tu sai *esattamente* cosa vuoi fare e vuoi che accada **subito**, in un batter d'occhio!

Ecco a cosa servono i comandi diretti. Iniziano tutti con una barra `/` (lo *slash*) e dicono al sistema di eseguire immediatamente un'azione, saltando completamente il "cervello" dell'AI.

---

## 🎩 Come si usano nella Chat

Usare i comandi diretti nella chat è facilissimo, proprio come usare le emoji su WhatsApp!

1. Clicca sulla barra della chat dove di solito scrivi i tuoi messaggi.
2. Digita il carattere **`/`** (la barra obliqua).
3. **Magia!** Apparirà un menu a tendina proprio sopra la casella di testo.
4. Questo menu contiene *tutti* i poteri segreti di Hecos (più di 150 comandi!). 
5. Puoi scorrere la lista con il mouse, oppure puoi continuare a scrivere per filtrare la lista. Ad esempio, se scrivi `/meteo`, vedrai apparire il comando del meteo.
6. Premi **Tab** o clicca con il mouse sul comando per sceglierlo.
7. Se il comando ha bisogno di informazioni aggiuntive (come la città per il meteo), ti lascerà uno spazio. Scrivi ad esempio `/meteo Roma` e premi **Invio**. Fatto!

### Esempi Pratici in Chat:
- **Vuoi il meteo di Milano?** Scrivi `/meteo Milano` e premi Invio.
- **Vuoi generare un'immagine?** Scrivi `/img un gattino spaziale` e premi Invio.
- **Vuoi riavviare il sistema?** Scrivi `/reboot_system` e premi Invio.

---

## 🔍 La "Spotlight": I comandi sempre a portata di mano

E se non ti trovi nella chat? Magari stai guardando la pagina dei plugin o stai leggendo un'altra schermata. Non preoccuparti! Puoi usare i comandi diretti *ovunque* ti trovi grazie alla **Spotlight**.

La Spotlight è una speciale barra di ricerca fluttuante. Per evocarla:
1. Premi la combinazione segreta sulla tastiera: **`Ctrl + Alt + Spazio`** (premi Control, Alt e la barra spaziatrice insieme).
2. Lo schermo si scurirà leggermente e apparirà una bellissima barra di ricerca al centro.
3. Scrivi quello che stai cercando (es. `img` o `meteo` o `calendar`).
4. Seleziona il comando con le freccette e premi **Invio**. 
5. Hecos eseguirà l'azione istantaneamente in sottofondo e ti mostrerà un messaggino di conferma!

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

### Esempio Pratico in Flows:
Vuoi creare un flusso che ogni mattina alle 8:00 ti accende un dispositivo tramite una richiesta Web, e poi ti genera una foto del buongiorno?
1. Metti un nodo `TIME__cron_trigger` impostato per le 8:00.
2. Metti un nodo `execute_slash_command` e nel parametro *command* scrivi: `/browser.open_url https://accendi-la-luce.com`.
3. Collega un altro nodo `execute_slash_command` e scrivi: `/img Un bellissimo sole che sorge`.
4. Salva il flusso! 
Ora hai creato una routine super-affidabile perché non dipende dall'immaginazione dell'AI, ma esegue esattamente gli ordini diretti.

---

## 💡 Ricapitolando: Perché usare i comandi diretti?

- **Sono veloci come un fulmine:** Saltano il "cervello" pensante e passano subito all'azione.
- **Sono precisi:** Fanno sempre e solo quello che gli dici di fare.
- **Ti aiutano a scoprire Hecos:** Scorrendo la lista premendo `/`, potrai scoprire tantissimi poteri di Hecos che magari non sapevi nemmeno che avesse!
