## 🛡️ 9. Sicurezza Avanzata (Zentra PKI)

Zentra 0.15.2 introduce un'infrastruttura **PKI (Public Key Infrastructure)** integrata per garantire connessioni HTTPS sicure in tutta la rete locale.

### Certificati e Root CA
Per sbloccare funzionalità come il **Microfono** e la **Webcam** sui browser mobile (che richiedono contesti sicuri), Zentra agisce come una propria Autorità di Certificazione:
1. **Root CA**: Generata automaticamente al primo avvio in `certs/ca/`.
2. **Installazione**: È necessario scaricare e installare il certificato `Root CA` sul proprio dispositivo (Mobile o PC remoto) e impostarlo come "Attendibile".
3. **Download**: Il certificato è scaricabile direttamente dalla tab **Security** nel Pannello di Configurazione o dal modal **Neural Link** nella chat.
