# 🌐 Hecos Proxy

> *"Un proxy di routing locale integrato per aggirare le restrizioni e connettere in modo sicuro i tuoi moduli al web."*

L'**Hecos Proxy** è un modulo di backend specializzato integrato direttamente nell'infrastruttura della WebUI. Agisce come intermediario sicuro tra la tua istanza locale di Hecos e l'internet esterno.

## A cosa serve?
I browser web moderni applicano rigide regole di sicurezza (come il CORS - Cross-Origin Resource Sharing) che impediscono a una pagina web locale (`localhost`) di recuperare dati direttamente da API esterne.
Ad esempio, se un Widget Meteo in esecuzione nella tua Control Room cerca di recuperare dati da un'API meteo, il browser potrebbe bloccare la richiesta.

## Come funziona
Invece di far fare ai widget richieste dirette ai siti esterni, essi inviano la richiesta al Proxy Hecos locale:
`http://localhost:5000/api/proxy?url=https://external-api.com`

Il backend di Hecos (Python) recupera quindi i dati in modo sicuro e li restituisce al widget della WebUI, aggirando completamente le restrizioni CORS del browser.

## Funzionalità
- **CORS Bypass:** Essenziale per i widget dinamici che devono estrarre dati in tempo reale da Internet.
- **Routing Sicuro:** Hecos sanitizza e controlla le richieste proxy in uscita.
- **Iniezione di Autenticazione:** Il proxy può essere configurato per iniettare in modo sicuro le tue chiavi API nelle richieste senza mai esporle al browser frontend (prevenendo i leak).
