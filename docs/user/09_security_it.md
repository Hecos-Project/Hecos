# 🛡️ 9. Sicurezza Avanzata (Zentra PKI)

Zentra mette la sicurezza al centro, specialmente quando si accede all'interfaccia da altri dispositivi.

- **Zentra CA**: Il sistema funge da propria Autorità di Certificazione (Root CA), generando certificati HTTPS sicuri e unici per la tua macchina.
- **Connessione Protetta**: Questo abilita il "lucchetto verde" nel browser, permettendo l'uso di funzioni protette come il microfono (WebRTC) su tutta la tua rete locale (LAN).
- **Autenticazione Obbligatoria**: L'accesso alla WebUI richiede sempre un login. Puoi gestire utenti e password dal pannello di controllo.
- **Isolamento Dati (User Vaults)**: Memorie, file personali e avatar sono isolati in cartelle protette (`memory/vaults/username`).
- **Privacy a 3 Livelli (v0.18.0)**: La WebUI offre controlli granulari sulla persistenza dei dati:
  - `Normale`: Persistenza completa su disco.
  - `Auto-Wipe`: Messaggi solo in RAM, cancellati al riavvio del sistema.
  - `Incognito`: Traccia zero. Zentra opera esclusivamente in RAM e il contesto viene rimosso al cambio della chat, garantendo che nessuna traccia della conversazione rimanga sul server fisico.
- **Sandbox**: Il codice generato dall'IA viene eseguito in un ambiente protetto (Sandbox AST) per evitare operazioni dannose sul tuo sistema operativo.
