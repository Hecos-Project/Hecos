# 🔄 2. Data Flow

The flow of information in Zentra follows a structured path to ensure speed and security.

1.  **Input**: Reception via Terminal (text), Microphone (audio), or WebUI.
2.  **Processing**: The Agentic Loop analyzes the request using the selected AI model.
3.  **Tool Calling**: If necessary, the AI activates the required plugins (e.g., `SYSTEM`, `FILES`, `IMAGES`).
4.  **Sandbox**: Every logical operation is validated and filtered.
5.  **Output**: Textual response in chat and synchronous voice synthesis (TTS).
