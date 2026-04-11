## 🔄 2. Data Flow (Flusso Esecutivo)

1. **Input Stage**: `InputHandler` cattura testo o audio via `listening.py` (STT).
2. **Context Enrichment**: `personality_manager.py` sincronizza la coscienza. `brain.py` raccoglie prompt e memoria.
3. **Vision Processing**: Se ci sono immagini, `client.py` builda il payload multimodale.
4. **WebRTC Audio**: Il client invia blob WebM/OGG, il server li converte in WAV via `pydub`.
5. **Model Resolution**: `LLMManager` decide il modello in base a capacità e backend.
6. **Inference**: LiteLLM unifica la richiesta al provider.
7. **Agentic Loop**: `AgentExecutor` gestisce Tool Calls e Chain of Thought.
8. **Output Stage**: Testo filtrato inviato a TUI e TTS.
9. **Streaming**: Gli eventi arrivano al WebUI via SSE.
