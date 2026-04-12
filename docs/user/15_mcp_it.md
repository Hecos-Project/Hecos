# 🔌 Universal Tool Hub (MCP Bridge)
Trasforma Zentra in una superpotenza multi-tool collegando server esterni tramite il **Model Context Protocol**.

## Cos'è l'MCP?
Il Model Context Protocol (MCP) è uno standard che permette agli agenti IA di collegarsi in modo sicuro a strumenti esterni come:
- **Ricerca Web**: Brave Search, Google Search.
- **Strumenti Dev**: GitHub, GitLab, Terminale.
- **Database**: PostgreSQL, SQLite.
- **Conoscenza**: Google Maps, Wikipedia.

## Configurazione
Vai in **Configurazione -> MCP Bridge** per gestire i tuoi server.
- **Preset**: Scegli da un elenco di server popolari per una configurazione rapida.
- **Server Personalizzati**: Aggiungi i tuoi specificando il comando (solitamente `npx`) e gli argomenti.
- **Auto-Discovery**: Zentra scansiona automaticamente i server connessi e elenca i tool disponibili in tempo reale.

## Utilizzare i Tool MCP
Una volta che un server è collegato e risulta "connected" nell'inventario:
1. L'IA rileverà automaticamente le nuove capacità.
2. Puoi chiedere a Zentra di eseguire azioni come "Cerca su Brave" o "Controlla i miei issue su GitHub".
3. Zentra inoltrerà la richiesta al server MCP esterno e ti restituirà i risultati.
