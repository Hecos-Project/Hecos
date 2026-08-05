# ⚡ 1. Guida Rapida di Avvio

Benvenuto in Hecos! Segui questi passi per configurare il sistema e iniziare subito a usare l'IA sul tuo PC.

## 1. Installazione

> [!TIP]
> **Metodo Consigliato — Installa tramite la Tray!** Scarica solo **Hecos Tray** (il pacchetto leggero), avvialo e apri la **Tray Dashboard**. Vai nella scheda **Updates** e clicca su *Manage Core*: il sistema scarica e configura tutto automaticamente. È il metodo più semplice, guidato e completo.

> [!IMPORTANT]
> **Percorso di Installazione**: Si consiglia vivamente di estrarre e installare Hecos in una cartella radice come `C:\Hecos`. Evita di installarlo in `Download`, `Desktop` o cartelle molto profonde, poiché percorsi lunghi o con caratteri speciali/spazi possono causare problemi di avvio o funzionalità non operative. Se scarichi **Hecos Tray** separatamente, installala anch'essa in una cartella radice: `C:\Hecos-Tray`.

> [!WARNING]
> **Dipendenze di Sistema**: L'ecosistema di Hecos include ora un **External Dependency Manager (EDM)** automatico. Durante o dopo l'installazione, se mancano componenti critici (come `VC_redist`, `Tesseract OCR` o `Node.js`), la WebUI ti notificherà e ti permetterà di scaricarli e installarli in background con un solo clic. Assicurati di essere connesso a internet per permettere i download.

**Metodo alternativo (avanzato):** Se hai già scaricato il pacchetto Core completo, usa gli script di configurazione automatica nella cartella radice:
- **Windows:** Fai doppio clic su `START_SETUP_HERE_WIN.bat`
- **Linux:** Apri un terminale ed esegui `bash START_SETUP_HERE_LINUX.sh`

Questi script installeranno automaticamente le dipendenze e avvieranno la **Procedura Guidata di Configurazione** nel browser.

## 2. La Procedura Guidata di Configurazione

La Procedura Guidata si aprirà automaticamente nel browser. Ti guiderà attraverso:
- La selezione del modello IA (locale o cloud).
- L'impostazione della lingua e delle preferenze.
- La configurazione delle chiavi API che possiedi.

## 3. Avvio di Hecos

Dopo la configurazione iniziale, il flusso di lavoro giornaliero più veloce è:
- Avvia **Hecos Tray** (doppio clic sull'`.exe` o esegui lo script di avvio).
- Doppio clic sull'icona nella tray per aprire la **Tray Dashboard**.
- Clicca su **Avvia Hecos** per portare il sistema online.
- La **WebUI** si apre automaticamente nel browser (o premi **F11** in qualsiasi momento).

## 4. Pannello di Controllo (F7)

Per modificare i parametri, aggiungere nuove chiavi API o attivare i plugin:
- Premi **F7** sulla tastiera o clicca sull'icona ingranaggio/logo nella WebUI per aprire l'**Hecos Hub**.
- Le modifiche vengono salvate istantaneamente.

## 5. Tray — Il Tuo Telecomando Universale

Hecos Tray è molto più di una semplice icona: è il centro di controllo rapido di tutto il sistema.
- L'icona si trova accanto all'orologio di Windows, sempre disponibile senza occupare spazio.
- **Doppio clic** sull'icona per aprire la **Tray Dashboard**, da cui puoi avviare/fermare Hecos, leggere i log in tempo reale, vedere i processi attivi e installare aggiornamenti.
- **Clic destro** per un menu rapido con le azioni più comuni.

---
*Sei pronto! Inizia ad esplorare il potenziale del tuo nuovo livello operativo IA sovrano e locale.*
