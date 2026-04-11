# ⚙️ 3. Dynamic Configuration (O-T-F)

Zentra provides Function Keys (F1-F7) to interact and re-parameterize the system in real-time, with permanent memory.

* **[ F1 ] ACTION MANUAL (Help):** Calls "root" protocols exposed by Plugins, showing free commands (e.g., `list:`, `cmd:`, `open:`).
* **[ F2 ] CHANGE AI MODEL:** Quickly select the neural network model (Llama, Gemma, Cloud, etc.) from the indexed backend list.
* **[ F3 ] LOAD SOUL / PERSONALITY:** Changes the system's tone and consciousness. Zentra automatically scans the `/personality/` folder at startup.
* **[ F4 ] TOGGLE LISTENING (MIC):** Activates or deactivates microphone capture.
* **[ F5 ] TOGGLE VOICE (TTS):** Enables or silences visual voice synthesis.

### 🎛️ THE [ F7 ] CONTROL PANEL
Through a menu-based graphical interface, it offers granular control over Zentra Core. It allows editing of boolean, numeric, or string parameters.

**Saving and Rebooting:**
Changes can be discarded with `ESC` or saved upon confirmed exit. If modified, the system will perform an automatic **Cold Reboot** in 1 second to apply the new parameters.
