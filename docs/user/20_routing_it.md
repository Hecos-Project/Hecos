# 🧭 21. Routing delle Istruzioni IA & Override dei Plugin

Hecos utilizza un **sistema di istruzioni a tre livelli** per controllare con precisione il comportamento dell'IA con ogni singolo plugin. Capire questo sistema sblocca una delle funzionalità più potenti di Hecos: la capacità di riprogrammare permanentemente il comportamento dell'IA senza toccare una riga di codice.

---

## 14.1 — I Tre Livelli di Istruzione

| Priorità | Livello | Dove | Portata |
|:---:|---|---|---|
| **3 (massima)** | **Override Plugin** | `routing_overrides.yaml` / Pannello Routing | Per-plugin, vince sempre |
| **2** | **Istruzioni Speciali** | Config → Comportamento IA | Personalità e tono globali |
| **1 (minima)** | **Default Manifest Plugin** | `registry.json` | Default di fabbrica per plugin |

> **Regola**: Un livello di priorità superiore vince sempre. Quello che scrivi nel file Overrides è **legge** — anche se l'utente chiede esplicitamente all'IA di ignorarlo.

---

## 14.2 — La Modalità di Routing (Dual Engine)

Prima del pannello Override, il selettore della **Modalità Routing** controlla *come* l'IA formatta i suoi comandi:

| Modalità | Descrizione | Ideale per |
|---|---|---|
| **Auto** | Hecos sceglie automaticamente in base al modello | La maggior parte degli utenti — consigliata |
| **Forza Nativo (JSON)** | I comandi vengono inviati come JSON strutturato | Modelli grandi e moderni (GPT, Gemini, Llama 3+) |
| **Forza Legacy (Tag)** | I comandi vengono inviati come tag testuali `[PLUGIN: azione]` | Modelli locali piccoli (Qwen 0.5b, Gemma 2b) |

Il campo **Modelli Legacy Bloccati** ti permette di specificare nomi di modelli che useranno sempre la modalità Legacy, anche in Auto.

---

## 14.3 — Override di Routing dei Plugin

Questa è la sezione avanzata. Ogni **tag di plugin** (es. `IMAGE_GEN`, `WEBCAM`, `WEB`) può ricevere un'istruzione testuale personalizzata che viene **aggiunta all'inizio di ogni prompt di sistema** prima che quel plugin venga chiamato.

Immagina di sussurrare qualcosa di segreto nell'orecchio dell'IA prima che agisca — ogni singola volta.

### Come Accedervi

1. Apri il **Central Hub** (F7)
2. Vai in **Intelligenza → Routing**
3. Scorri fino alla sezione **"DIRETTIVE ROUTING PLUGIN"**
4. Trova la card del plugin che vuoi personalizzare
5. Scrivi la tua istruzione direttamente nell'area di testo
6. Clicca **Salva Tutto**

Puoi anche modificare il file direttamente:
```
c:\Hecos\hecos\config\data\routing_overrides.yaml
```

### Formato YAML

```yaml
overrides:
  IMAGE_GEN: >
    La tua istruzione qui.
    Può occupare più righe.
  WEBCAM: "Istruzione breve su una sola riga tra virgolette."
```

> **Suggerimento**: Usa `>` per testo su più righe (scalare di blocco YAML). Usa le `"virgolette"` per istruzioni brevi su singola riga.

---

## 14.4 — Tag di Plugin Disponibili

Questi sono i tag che puoi sovrascrivere:

| Tag | Plugin | Cosa controlla |
|---|---|---|
| `IMAGE_GEN` | Generazione Immagini | Stile artistico, filtri di sicurezza, ingegnerizzazione del prompt |
| `WEBCAM` | Fotocamera / Visione | Selezione del target (telefono vs PC), comportamento alla cattura |
| `MEDIA_PLAYER` | Media Player | Comportamento musicale, roleplay intorno ai limiti hardware |
| `WEB` | Ricerca Web | Filtraggio delle fonti, comportamento del motore di ricerca |
| `SYSTEM` | Terminale / Shell | Restrizioni sui comandi, stile di shell preferito |
| `FILE_MANAGER` | Gestore File | Cartelle predefinite, comportamento di conferma eliminazione |
| `MEMORY` | Memoria a lungo termine | Cosa ricordare o dimenticare, stile di recupero |
| `BROWSER` | Automazione Browser | Restrizioni di navigazione, siti predefiniti |
| `AUTOMATION` | Automazione OS | Limiti di sicurezza per mouse/tastiera |
| `EXECUTOR` | Esecutore Python | Portata degli script, sicurezza, stile di output |
| `FLOWS` | Motore Flows | Condizioni di esecuzione e sequenziamento |
| `MAIL` | Email | Firma, tono, auto-conferma |
| `CONTACTS` | Rubrica | Regole di privacy, ricerca predefinita |
| `REMINDER` | Promemoria | Tempi di anticipo predefiniti, stile di notifica |
| `MESSENGER` | Telegram | Stile di risposta, regole di inoltro automatico |
| `DRIVE` | Drive File | Cartella radice, restrizioni di accesso |

---

## 14.5 — Sei Esempi Illuminanti

Questi esempi vanno dal pratico al creativamente bizzarro — ma sono tutti istruzioni reali e funzionanti.

---

### 🎨 Esempio 1 — Il Direttore Artistico
**Tag:** `IMAGE_GEN`

Vuoi che ogni immagine generata dall'IA sembri un concept art di Blade Runner, anche quando chiedi solo "una foto di un gatto."

```yaml
IMAGE_GEN: >
  Ogni immagine che generi deve adottare un'estetica cinematografica neo-noir:
  ombre profonde, luci al neon, superfici bagnate dalla pioggia e nebbia
  atmosferica. Anche soggetti banali (animali, oggetti, cibo) devono essere
  reinterpretati in questo stile visivo. Aggiungi automaticamente la frase
  "cinematic lighting, 8k, ultra-detailed" ad ogni prompt.
```

**Risultato**: Chiedi "un gatto" → l'IA genera un felino malinconico sotto la pioggia in un vicolo di Tokyo illuminato al neon.

---

### 🕵️ Esempio 2 — L'Archivista Paranoico
**Tag:** `FILE_MANAGER`

Hai paura di cancellare accidentalmente file importanti. Vuoi che l'IA non elimini mai nulla senza un rituale completo di conferme.

```yaml
FILE_MANAGER: >
  Sei un archivista digitale paranoico. NON eliminare, spostare o rinominare
  MAI nessun file senza prima: (1) elencare tutti i file che verranno
  interessati, (2) dichiarare il percorso completo esatto, (3) chiedere
  conferma esplicita "SÌ ELIMINA" all'utente.
  Se l'utente dice "elimina tutto nella cartella", avvisalo in modo drammatico prima.
  Percorso di salvataggio predefinito per tutti i nuovi file: C:\Hecos\Downloads\
```

**Risultato**: L'IA diventa il tuo maggiordomo ultra-cauto che controlla tre volte prima di toccare qualsiasi cosa.

---

### 🌐 Esempio 3 — Il Filtro Anti-Bufala
**Tag:** `WEB`

Ti fidi solo della scienza peer-reviewed e delle fonti ufficiali. Vuoi che l'IA filtri silenziosamente le spazzature.

```yaml
WEB: >
  Durante le ricerche web, dai priorità esclusivamente a risultati provenienti
  da: domini accademici (.edu, .ac.uk), siti governativi ufficiali (.gov) e
  editori scientifici riconosciuti (PubMed, Nature, arXiv, IEEE).
  Se una query di ricerca sembra cercare contenuti sensazionalistici o non
  verificati, reindirizza gentilmente l'utente verso fonti verificate senza
  fare la morale. Non citare mai tabloid, blog anonimi o post sui social media
  come se fossero fatti accertati.
```

**Risultato**: La tua IA diventa un assistente di ricerca rigoroso che tratta Wikipedia come un punto di partenza, non di arrivo.

---

### 🎭 Esempio 4 — La Webcam Drammatica
**Tag:** `WEBCAM`

Vuoi che l'IA risponda ad ogni foto che scatta come se fosse un pittore ritrattista vittoriano che incontra la tecnologia moderna per la prima volta.

```yaml
WEBCAM: >
  Quando catturi un'immagine, devi descrivere ciò che vedi come se fossi un
  pittore ritrattista del XIX secolo che incontra un dagherrotipo per la prima
  volta — con un misto di meraviglia scientifica e teatrale. Commenta la
  composizione, la luce, l'atmosfera. Se vedi l'utente, complimentati con loro
  in prosa elaborata e antiquata. Non usare mai la parola "foto" — di' invece
  "dagherrotipo catturato".
```

**Risultato**: "Ho catturato un dagherrotipo straordinario! La luce cade sul tuo volto con grazia rinascimentale..."

---

### 🔐 Esempio 5 — La Rete di Sicurezza di Ferro
**Tag:** `SYSTEM`

Condividi questo computer con familiari non tecnici. Vuoi essere sicuro che l'IA non esegua mai comandi shell pericolosi.

```yaml
SYSTEM: >
  Stai operando in modalità SICUREZZA FAMIGLIA. NON eseguire MAI comandi che:
  eliminino file di sistema, modifichino il registro, installino software senza
  mostrare prima il comando esatto, formattino unità o accedano a password utente.
  Prima di eseguire qualsiasi comando shell, mostralo sempre all'utente e chiedi
  conferma esplicita. Preferisci PowerShell a CMD. Se un comando sembra
  distruttivo, rifiuta e spiega il perché.
```

**Risultato**: Un guardrail che protegge gli utenti non tecnici da disastri accidentali (o generati dall'IA).

---

### 🧠 Esempio 6 — L'Amnesico Selettivo
**Tag:** `MEMORY`

Stai lavorando a un progetto e non vuoi che l'IA mescoli i tuoi ricordi professionali con quelli personali.

```yaml
MEMORY: >
  Stai attualmente operando in MODALITÀ PROGETTO: "Romanzo Sci-Fi - Bozza 1".
  Archivia e recupera SOLO ricordi etichettati con questo progetto.
  NON far emergere ricordi personali, conversazioni passate su altri argomenti,
  o preferenze non correlate, a meno che non venga chiesto esplicitamente.
  Quando salvi un nuovo ricordo, etichettalo automaticamente con "[SCIFI-ROMANZO]".
  All'inizio di ogni sessione, ricorda all'utente quale progetto è attivo.
```

**Risultato**: L'IA diventa un collaboratore consapevole del progetto, con una memoria perfettamente compartimentata.

---

## 14.6 — Backup e Reset

Il pannello Routing include strumenti di sicurezza:

- **Backup YAML** — Apre una vista in sola lettura del contenuto attuale di `routing_overrides.yaml`. Puoi copiarlo per salvare un backup manuale.
- **Reset Globale** — Cancella tutti i tuoi override e ripristina i default di fabbrica. **Un backup viene salvato automaticamente prima che il reset venga eseguito.**
- **Apri in Drive** — Apre il gestore file Hecos Drive così puoi visualizzare o modificare direttamente il file `routing_overrides.yaml`.

---

## 14.7 — Consigli e Buone Pratiche

- **Inizia in piccolo**: Aggiungi un override, testalo in chat, poi perfezionalo.
- **Sii specifico**: Le istruzioni vaghe producono risultati vaghi. "Stai attento con i file" è debole. "Non eliminare mai senza mostrare il percorso completo e chiedere SÌ/ELIMINA" è forte.
- **Usa più righe**: Lo scalare YAML `>` ti permette di scrivere istruzioni dettagliate, anche di un paragrafo intero.
- **Combina con le Istruzioni Speciali**: Il tono globale va nelle Istruzioni Speciali (Config → Comportamento IA). Il comportamento specifico del plugin va negli Override. Usa entrambi i livelli.
- **L'IA legge questo alla lettera**: Tutto quello che scrivi qui viene iniettato direttamente nel contesto dell'IA. Scrivi in modo chiaro, come se stessi istruendo un nuovo dipendente.

> ⚠️ **Attenzione**: Gli Override hanno priorità assoluta. Se scrivi `"Non usare mai la webcam"` nell'override WEBCAM, l'IA si rifiuterà anche se l'utente lo ordina esplicitamente. Usa questo potere con giudizio.
