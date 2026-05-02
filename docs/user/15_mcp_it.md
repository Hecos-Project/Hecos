# 🔌 Universal Tool Hub (MCP Bridge)
Trasforma Hecos in una superpotenza multi-tool collegando server esterni tramite il **Model Context Protocol**.

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
- **Auto-Discovery**: Hecos scansiona automaticamente i server connessi e elenca i tool disponibili in tempo reale.

## 🔎 Multi-Registry Discovery
Hecos rende facile trovare nuovi strumenti senza lasciare l'applicazione. Vai nella tab **Discovery** dell'MCP Bridge per cercare tra più registri:
- **Smithery.ai**: Sfoglia migliaia di server MCP verificati dalla community.
- **MCPSkills**: Scopri agenti e set di strumenti specializzati.
- **GitHub**: Installa direttamente i server ospitati su GitHub.
- **Hugging Face**: Accedi a strumenti e modelli pronti per l'IA.

Basta cliccare su **"Install"** per qualsiasi strumento trovato, e Hecos gestirà automaticamente l'impostazione dell'ambiente e la configurazione.

## Utilizzare i Tool MCP
Una volta che un server è collegato e risulta "connected" nell'inventario:
1. L'IA rileverà automaticamente le nuove capacità.
2. Puoi chiedere a Hecos di eseguire azioni come "Cerca su Brave" o "Controlla i miei issue su GitHub".
3. Hecos inoltrerà la richiesta al server MCP esterno e ti restituirà i risultati.
