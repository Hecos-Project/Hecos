# 🔔 Notifications Center

Il modulo **Notifications Center** di Hecos è un potente router di eventi basato su plugin. Funge da hub centrale per l'invio di avvisi quando si verificano eventi di sistema importanti (ad esempio, l'avvio del sistema, errori, il completamento di task o tentativi di accesso falliti). Delega l'effettiva consegna dei messaggi ai plugin installati, come **MAIL** o **MESSENGER**, il che significa che non richiede l'inserimento di credenziali proprie.

---

## 🛠️ Funzionalità Principali

1. **Routing degli Eventi**: Associa gli eventi di sistema a destinazioni specifiche.
2. **Supporto Multi-Account**: Seleziona automaticamente l'account mittente corretto o ripiega su quello predefinito globale.
3. **Smart Templating**: Invia avvisi in testo semplice o ricchi template HTML con variabili dinamiche.
4. **Integrazione LLM**: Completamente gestibile tramite l'intelligenza artificiale usando il linguaggio naturale.
5. **Direct Commands (HDCS)**: Comandi diretti nativi (slash commands) per un'interazione rapida dall'interfaccia di chat.

---

## 📝 Eventi di Sistema Disponibili

Il Notifications Center può intercettare e gestire i seguenti eventi integrati:
- `system_boot`
- `system_shutdown`
- `system_error`
- `flow_started`
- `flow_completed`
- `flow_failed`
- `package_installed`
- `package_updated`
- `package_removed`
- `security_login_failed`
- `security_new_device`
- `backup_started`
- `backup_completed`
- `backup_failed`
- `custom`

---

## 🤖 Intelligenza Artificiale e Comandi Diretti (HDCS)

Puoi gestire le tue regole di notifica e le destinazioni in modo completamente autonomo attraverso l'interfaccia di chat usando il linguaggio naturale, oppure utilizzando i precisi **Direct Commands**.

### Direct Commands

Digita queste scorciatoie in chat per interagire immediatamente con il Notifications Center:

* **`/notify`**: Il comando di gestione principale. Puoi usarlo per istruire l'AI su cosa fare.
  * *Esempio*: `/notify mostra le regole attive`
  * *Esempio*: `/notify aggiungi una nuova email di destinazione per mario@example.com`
  * *Esempio*: `/notify associa system_error alla mail_di_mario`
  
* **`/alert`**: Invia istantaneamente una notifica ad hoc a tutte le tue destinazioni configurate (o a una specifica).
  * *Esempio*: `/alert Il backup di sistema è terminato con successo!`

### Esempi in Linguaggio Naturale

Poiché tutti gli 8 strumenti principali sono esposti all'LLM, non hai nemmeno bisogno dei comandi diretti se preferisci conversare in modo naturale:
> *"Chi riceve le notifiche in questo momento?"*
> *"Smetti di inviare notifiche a Marco quando il sistema si avvia."*
> *"Crea una nuova destinazione per Telegram e collegala a flow_failed."*
> *"Manda una notifica di test con scritto 'Ciao Mondo'."*

---

## ⚙️ Configurazione via WebUI

Se preferisci un'interfaccia grafica, il Notifications Center offre un pannello di configurazione dedicato nel **Package Manager**:

1. Apri il **Central Hub** e vai su **Packages**.
2. Clicca sull'icona a forma di ingranaggio (⚙️) accanto a **Notifications Center**.
3. **Destinations**: Aggiungi, modifica o rimuovi i destinatari (indirizzi email, contatti o ID Messenger).
4. **Event Rules**: Usa i comodi menu a tendina per associare le tue destinazioni a specifici eventi di sistema.
5. **Templates**: Assegna template HTML agli eventi per inviare bellissime email di avviso personalizzate.

---

## 📋 Cronologia Notifiche (History)

Ogni singola notifica inviata dal sistema viene registrata nella scheda **Notification History** all'interno del pannello di configurazione. 
La cronologia è ordinatamente raggruppata per data (con sezioni espandibili e comprimibili) e mostra il destinatario, l'oggetto e l'orario esatto di consegna.
