# ⚙️ 3. Dynamic Configuration (O-T-F)

Hecos provides Function Keys (F1-F7) to interact and re-parameterize the system in real-time, with permanent memory.

* **[ F1 ] ACTION MANUAL (Help):** Calls "root" protocols exposed by Plugins, showing free commands (e.g., `list:`, `cmd:`, `open:`).
* **[ F2 ] CHANGE AI MODEL:** Quickly select the neural network model (Llama, Gemma, Cloud, etc.) from the indexed backend list.
* **[ F3 ] LOAD SOUL / PERSONALITY:** Changes the system's tone and consciousness. Hecos automatically scans the `/personality/` folder at startup.
* **[ F4 ] TOGGLE LISTENING (MIC):** Activates or deactivates microphone capture.
* **[ F5 ] TOGGLE VOICE (TTS):** Enables or silences visual voice synthesis.

### 🎛️ Hecos Hub (Config Panel)
Accessible via **F7** or the WebUI, the Hub is Hecos's command center. Recently redesigned with a **Premium Symmetrical aesthetic**, it offers:
- **Tabbed Navigation**: Organized categories (Backend, LLM, Persona, Voice, etc.) for streamlined management.
- **Dynamic Switcher**: Toggle instantly between Tab View and "Wall" View for a total system overview.
- **Real-time Sync**: Many settings (like persona or voice swaps) apply instantly without a full reboot.

**Saving and Restarting:**
Critical changes (e.g., port changes or HTTPS) trigger an automatic **Cold Reboot** handled by the system Watchdog to ensure service integrity.
