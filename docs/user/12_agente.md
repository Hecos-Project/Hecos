## 🤖 12. Agente Autonomo e Sandbox (Code Jail)

Dalla versione 0.9.9 Zentra integra un **Loop Cognitivo (Agentic Loop)**. Questo trasforma il sistema da un semplice chatbot a un agente capace di ragionamento complesso su più step (Chain of Thought).

- **Nuvolette di Pensiero (Live Traces)**: Quando chiedi un'operazione elaborata (es. "Scatta una foto a questo file"), nella WebUI vedrai apparire una trace live animata. Zentra sta elaborando attivamente un piano d'azione chiamando Tool hardware o plugin di rete prima di risponderti in modo compiuto.
- **Zentra Code Jail (Sandbox)**: Zentra può scrivere frammenti di codice Python al volo ed eseguirli (nella cartella sicura `/workspace/sandbox/`) per risolvere calcoli aritmetici lunghi, costruire algoritmi o manipolare dati complessi con precisione assoluta. Una speciale macchina AST di sicurezza interviene prima dell'esecuzione: se l'IA prova a usare comandi di sistema pericolosi, l'azione viene bloccata all'istante, mantenendo il computer sempre protetto.
