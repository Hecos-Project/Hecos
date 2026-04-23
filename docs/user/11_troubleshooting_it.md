# 🛠️ 11. Risoluzione dei Problemi

Se incontri difficoltà, segui questi passaggi rapidi per ripristinare il corretto funzionamento di Zentra Core.

- **Reset Console**: Se l'interfaccia terminale appare bloccata, prova a premere `CTRL+C` per forzare l'arresto e riavviare il programma.
- **Problemi Audio**: Verifica che il microfono sia selezionato correttamente nel pannello **F7** sotto `AUDIO`. Se usi la WebUI, assicurati di aver accettato i certificati di sicurezza Zentra PKI.
- **Errori Backend IA**: Assicurati che Ollama o il tuo fornitore cloud siano attivi e raggiungibili.
- **Loop Innesco Audio:** Regola l'`Energy Threshold` in **F7 → Listening** per calibrare il rumore di fondo.

### 🆘 Pannello Manutenzione e Ripristino
Se riscontri problemi con i percorsi (es. Piper non trovato) o devi gestire il servizio in background:
1. Apri il **Pannello di Controllo di Zentra** (F7 o `/zentra/config/ui`).
2. Vai alla scheda **Aiuto**.
3. Trova la sezione **🔧 MANUTENZIONE E RIPARAZIONE**.
4. Da qui puoi eseguire un **Controllo di Sistema Completo**, **Riparare i Percorsi Interrotti** o **Disinstallare il Servizio**.

- **LOG di Sistema**: Per problemi persistenti, consulta i file nella cartella `logs/` per un'analisi dettagliata.
