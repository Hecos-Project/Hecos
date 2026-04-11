## 🖥 2. Interfaccia Utente Fissa (Safe Scrolling UI)

L'interfaccia a terminale di Zentra è costruita su architettura ancorata (`DECSTBM Scrolling Region`):
- **Dashboard (Prima Riga - Plugin Dashboard):** Se abilitato, un plugin hardware residente in background terrà informato l'utente ogni 2 secondi sullo stato della `CPU, RAM, VRAM e STATO GPU`. (Nessun flickering generato).
- **Barra Blu (Terza Riga - Status System):** Mostra dinamicamente le informazioni centrali:
  - **STATO:**
    - 🟢 `PRONTO` -> Zentra è in ascolto o aspetta ordini testuali.
    - 🟡 `PENSANDO...` -> Elaborazione albero neurale tramite LLM.
    - 🔵 `PARLANDO...` -> Riproduzione vocale tramite motore TTS (Piper).
    - 🔴 `ERRORE/OFFLINE` -> Caduta del provider IA o blocco sistema.
  - **MODELLO:** LLM attualmente in uso.
  - **ANIMA:** Modulo del system prompt/personalità attiva (roleplay o assistente).
  - **MIC / VOCE:** Mostra se `ON` o `OFF`.

**Area Chat:** Lo storico dell'iterazione scritta (o delle traduzioni STT) scorre **solo dalla riga 7 in giù**, lasciando il "Cruscotto" hardware e di sistema intoccati.
