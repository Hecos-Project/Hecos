# 🚀 1. Avvio e Controllo Iniziale

Alla pressione dell'eseguibile (o script avvio Python), Zentra avvia la sua sequenza di **Boot Sincronizzato**.

### Diagnostica Pre-Volo
Il sistema di default controlla:
- Integrità delle cartelle vitali (`core/`, `plugins/`, `memory/`, ecc.).
- Stato Hardware (CPU e RAM entro limiti accettabili).
- Stato del Modulo Ascolto e Voce (Soglia d'energia configurata).
- Verifica di risposta backend IA (ping locale a Ollama/Kobold o controllo Cloud).
- Scansione Plugin Attivi/Disattivati indicando per ciascuno `ONLINE` o `DISATTIVATO`.

Durante questa fase di boot è sempre possibile premere **ESC** per bypassare ogni singolo caricamento forzato.

### ⚡ Avvio Rapido (Fast Boot)
Ove l'Admin desideri un avvio fulmineo, è stata implementata la funzionalità **Avvio Rapido (Salta Diagnostica)**. 
- Disabilitando la diagnostica (attivabile dal Pannello di Controllo **F7** sotto la voce `SYSTEM`), Zentra Core ignorerà ogni controllo testuale hardware a schermo.
- Il tempo di caricamento del terminale utile scende a **~0.5 secondi**, riportando l'interazione al prompt fisso immediatamente.
