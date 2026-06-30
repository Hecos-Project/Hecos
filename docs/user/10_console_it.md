# 💻 11. La Console (CLI)

> *"La finestra di comando in cui il sistema pensa, esegue i controlli di sicurezza e ti permette di gestire tutto."*

![Hecos - Helping Companion System](https://github.com/Hecos-Project/Hecos-Assets/blob/main//Hecos_Core_002.png?raw=true)


La **Console di Hecos** è la finestra terminale grezza e nativa che si apre quando avvii Hecos. È il cuore pulsante del sistema.

## Perché una Console?
Mentre la WebUI è il "volto" di Hecos, la Console è il "cervello". Garantisce una trasparenza assoluta. Ogni azione intrapresa dall'IA, ogni strumento che invoca e ogni chiamata API che effettua viene registrata qui in tempo reale.

## Funzionalità Principali
- **Telemetria in Tempo Reale:** Mostra l'uso dell'hardware, lo stato di caricamento del backend e gli stati dei moduli attivi.
- **Audit di Sicurezza:** Guarda il sistema eseguire i comandi. Se un flusso o un plugin innesca un processo locale (come l'apertura di un file o l'esecuzione di uno script Python), il comando esatto viene stampato qui.
- **Server Hub:** La Console funge da server host locale per la WebUI. Chiudendo questa finestra si spegne l'intero sistema Hecos.
- **Input Veloce:** Puoi digitare il testo direttamente nella console per chattare con l'IA se preferisci un'esperienza solo terminale e senza distrazioni.
