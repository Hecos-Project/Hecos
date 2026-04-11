## 🔗 4. Infrastruttura Chiave

### LLM Dynamic Routing
Evita l'hardcoding dei modelli. I plugin chiedono "capability tags" e il manager risolve il miglior modello associato nel `system.yaml`.

### Zentra PKI (Native HTTPS)
Built-in CA per generare certificati locali. Essenziale per sbloccare Microfono e Webcam sui browser mobile via HTTPS.

### Cross-Drive Security
Il plugin Drive valida i percorsi tramite `_safe_path` contro attacchi di type traversal, garantendo l'accesso assoluto ai volumi (`C:\`, `D:\`) in sicurezza.
