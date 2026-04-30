# 🔄 2. Flusso di Dati

Il flusso di informazioni in Hecos segue un percorso strutturato per garantire velocità e sicurezza.

1.  **Input**: Ricezione tramite Terminale (testo), Microfono (audio) o WebUI.
2.  **Processing**: L'Agentic Loop analizza la richiesta usando il modello IA selezionato.
3.  **Tool Calling**: Se necessario, l'IA attiva i plugin richiesti (es. `SISTEMA`, `FILES`, `IMMAGINI`).
4.  **Sandbox**: Ogni operazione logica viene validata e filtrata.
5.  **Output**: Risposta testuale in chat e sintesi vocale sincrona (TTS).
