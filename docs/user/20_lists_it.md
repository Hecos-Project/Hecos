# 19. Gestione Liste

Il modulo **Lists** (Gestione Liste) di Hecos è lo strumento ideale per organizzare le tue attività, appunti, liste della spesa o note di sviluppo direttamente all'interno dell'ecosistema. È progettato per essere leggero, accessibile e veloce, offrendo sia una visualizzazione completa a schermo intero che un pratico widget da inserire nella tua Control Room.

---

## 📋 Dove Trovare le Liste

Puoi accedere alla gestione delle liste in due modi diversi all'interno della WebUI:

1. **Central Hub (Pannello Principale)**: Clicca sulla voce "Lists" nel menu laterale sinistro del Central Hub. Questa schermata a pieno schermo offre una barra laterale con tutte le tue liste e un'area centrale estesa per gestire nel dettaglio gli elementi.
2. **Control Room Widget**: Puoi aggiungere il widget delle liste nella tua Control Room (la bacheca con griglia flessibile). È perfetto per tenere d'occhio i tuoi promemoria mentre monitori altri moduli del sistema.

---

## ⌨️ Navigazione da Tastiera (Keyboard Shortcuts)

Per rendere l'esperienza d'uso velocissima, sia il widget della Control Room che la schermata del Central Hub supportano la **navigazione completa tramite tastiera**. Non c'è bisogno di toccare il mouse!

### 🗺️ Spostarsi tra le Sezioni
* **`Freccia Destra (→)`**: Quando ti trovi sulla barra laterale (lista delle liste), premi la freccia destra per saltare direttamente al primo elemento della lista selezionata.
* **`Freccia Sinistra (←)`**: Quando ti trovi sulla lista degli elementi, premi la freccia sinistra per tornare alla barra laterale delle liste.
* **`Freccia Su (↑)` sul primo elemento**: Se stai scorrendo gli elementi e ti trovi sul primo della lista, premendo la freccia su tornerai automaticamente a focalizzare la lista attiva nella barra laterale.

### 🗂️ Navigare e Gestire le Liste (Sidebar)
* **`Freccia Su (↑)` / `Freccia Giù (↓)`**: Scorri verticalmente le tue liste.
* **`Invio` / `Spazio`**: Seleziona ed apri la lista focalizzata. Il focus si sposterà automaticamente sul primo elemento per consentirti di iniziare subito a lavorarci.

### 📝 Navigare e Gestire gli Elementi (Items)
* **`Freccia Su (↑)` / `Freccia Giù (↓)`**: Scorri l'elenco degli elementi all'interno della lista aperta.
* **`Spazio` / `Invio`**: Segna l'elemento selezionato come completato (depennato) o riattivalo. *(Funziona solo se non stai modificando il testo dell'elemento)*.
* **`Canc (Delete)` / `Backspace`**: Elimina definitivamente l'elemento selezionato. *(Funziona solo se non stai modificando il testo)*.

---

## 📅 Tracciamento Automatico delle Date

Hecos registra automaticamente le date importanti per consentirti di monitorare la cronologia delle tue attività e valutare la produttività:

* **Data di Creazione della Lista**: Salvata automaticamente nel momento in cui crei una nuova lista.
* **Data di Creazione dell'Elemento**: Registrata per ogni singolo elemento aggiunto a una lista.
* **Data di Termine/Completamento**: Quando spunti o completi un elemento, Hecos memorizza l'istante esatto del completamento. Se riattivi l'elemento, la data di completamento viene azzerata.

### 🔍 Dove Visualizzare le Date
A causa della differenza di spazio tra le interfacce, le date vengono mostrate in due modi diversi:
* **Nel Central Hub (Schermo Intero)**: Le date sono visibili direttamente in chiaro. La data di creazione della lista appare accanto al suo nome nella barra laterale. Per gli elementi, le date di creazione e di eventuale completamento sono mostrate sotto il testo di ciascuna riga.
* **Nel Widget della Control Room**: Data lo spazio ridotto del widget, le informazioni sulle date appaiono comodamente sotto forma di **tooltip** (un fumetto informativo) quando passi il mouse sopra il nome di una lista o sopra un elemento.

---

## 💾 Esportazione e Importazione delle Liste

Puoi esportare le tue liste per utilizzarle altrove o condividerle. Hecos supporta l'esportazione in tre formati: **YAML**, **Testo Semplice (.txt)** e **Markdown (.md)**.

> [!NOTE]
> **Nomenclatura Automatica**: Per aiutarti a riconoscere facilmente i tuoi file sul computer, ogni esportazione viene salvata automaticamente con il prefisso `hecos_list_` seguito dal nome della lista (ad esempio: `hecos_list_sviluppo.yaml`).

### Tracciabilità della Versione e delle Date
Tutte le informazioni storiche vengono fedelmente mantenute durante l'esportazione:
* **Compatibilità**: All'interno del file viene inserito in testa un commento che specifica il software e la versione esatta di Hecos utilizzata per generarlo (es. `# List created with Hecos v-0.30.0` in lingua inglese per standardizzazione).
* **Date incluse**: Le date di creazione e di termine vengono scritte e conservate in tutti i formati esportati, consentendoti di non perdere lo storico anche lavorando all'esterno dell'applicazione.
