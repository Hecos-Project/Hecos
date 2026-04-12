# 🌌 Zentra Core - Guida Unificata (v0.17.0)
Benvenuto nella guida ufficiale di Zentra Core. Questo documento riassume tutto ciò che devi sapere per installare, configurare e utilizzare il tuo assistente AI personale offline.

---

## 🚀 1. Introduzione
Zentra Core è una piattaforma AI local-first progettata per la privacy e la modularità. Funziona interamente sul tuo hardware, permettendoti di interagire con modelli linguistici (LLM), automatizzare il sistema e gestire i tuoi dati senza passare per il cloud.

## 📥 2. Installazione Rapida
Per iniziare da zero:
1. **Python**: Installa Python 3.11 o superiore.
2. **Ollama**: Scarica Ollama e carica un modello (es. `ollama pull gemma2`).
3. **Setup**:
   ```bash
   pip install -r requirements.txt
   python scripts/setup_pki.py  # Abilita HTTPS e il microfono nel browser
   ```
4. **Avvio**: Esegui `python main.py`.

## 🔐 3. Primo Accesso
Zentra richiede un'autenticazione obbligatoria per proteggere i tuoi dati:
- **Username default**: `admin`
- **Password default**: `zentra`
*Si consiglia vivamente di cambiare la password dal Pannello di Configurazione.*

---

## ✨ 4. Funzionalità Principali (v0.17.0)

### 🔌 MCP Bridge & Discovery (Hub Universale)
Il Model Context Protocol (MCP) permette a Zentra di usare strumenti esterni.
- **Supporto Multi-Registry**: Cerca e installa tool da **Smithery.ai**, **MCPSkills**, **GitHub** e **Hugging Face**.
- **Dashboard**: Gestisci i tuoi server MCP in tempo reale.

### 👥 Multi-Utente & Vault
Ogni utente ha la propria identità, memoria e avatar.
- **Vault Isolati**: I file e le memorie sono salvati in `memory/vaults/username`.
- **Bio Notes**: L'IA impara a conoscerti e salva dettagli importanti su di te in modo privato.

### 🛡️ Zentra Code Jail
L'IA può scrivere ed eseguire codice Python in una sandbox sicura (AST) per calcoli complessi o manipolazione dati.

### 🔒 PKI Professionale (HTTPS)
Zentra genera i propri certificati SSL per abilitare il "Lucchetto Verde" sulla tua LAN, sbloccando l'uso di Microfono e Fotocamera sul browser.

### ⚡ Comandi Diretti (Bypass IA)
Se vuoi eseguire azioni rapide o generare immagini saltando i filtri morali/sicurezza dell'IA (es. Gemini):
- `/img [descrizione]`: Genera un'immagine direttamente tramite il provider (HuggingFace/Flux, ecc.).
- `/foto [descrizione]`: Versione italiana del comando d'immagine.

---

## 📱 5. Interfaccia Mobile
L'interfaccia di Zentra è completamente responsive. Puoi usarla dal tuo smartphone come una vera Web App nativa, con menu a scomparsa e accesso rapido ai "Neural Link".

## 📚 6. Link Utili
- **Chat**: `http://localhost:7070/chat`
- **Configurazione**: `http://localhost:7070/zentra/config/ui`
- **File Manager (Drive)**: `http://localhost:7070/drive`
- **Wiki Ufficiale**: [GitHub Wiki](https://github.com/Zentra-Core/zentra-core.github.io/wiki)

---
*Zentra Core è in fase Runtime Alpha (v0.17.0). Usa con responsabilità.*
