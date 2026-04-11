# 🔄 2. Data Flow

1. **Input Stage**: `InputHandler` captures text or audio via `listening.py`.
2. **Context Enrichment**: `personality_manager.py` syncs the soul.
3. **Vision Processing**: Multimodal payload building.
4. **WebRTC Audio**: WebM/OGG to WAV conversion.
5. **Model Resolution**: `LLMManager` resolves capabilities.
6. **Inference**: LiteLLM request unification.
7. **Agentic Loop**: `AgentExecutor` manages Tool Calls.
8. **Output Stage**: Sanitized text to TUI and TTS.
