# 💻 Native WebUI

Zentra's WebUI is the modern graphical interface accessible through your browser.

- **Access**: By default, it is available at `http://localhost:5000` (or on the configured port).
- **Rich Chat**: Supports display of images, bold text, tables, and code blocks with syntax highlighting.
- **Graphical Configuration**: Allows you to modify every aspect of Zentra through intuitive menus, without having to manually edit YAML files.
- **Microphone and Camera**: Thanks to Zentra PKI encryption, you can use your browser's microphone and webcam to interact with the AI even remotely on your local network.
- **User Management (Multi-User)**: The "Users" tab allows for managing multiple profiles, changing personal avatars and bio notes. Each user has an isolated "Vault".
- **Session History**: A new sidebar panel allows for managing multiple conversations. Each session is persistently saved in the Episodic Memory Vault and can be renamed or deleted. A 🗑️ button is available for quick deletion of all chats.
- **Dynamic Sidebar**: The sidebar adjusts instantly, loading only the configured and active plugins.
- **3-Tier Privacy Mode (v0.18.2)**: Advanced selector that locks the mode after the first message is sent:
  - `☁️ Normal`: Messages saved permanently in the local database.
  - `🔒 Auto-Wipe`: Messages kept in RAM while the system is active; cleared on restart.
  - `🕵️ Incognito`: Zero-trace. Messages are never written and context is removed when switching chats.
- **Enhanced Chat Headers (v0.18.2)**: New visual headers showing User/Persona names, exact timestamps, and a more accessible button bar for quick message actions (Copy, Edit, Regenerate).
- **Flux Prompt Studio (v0.18.2)**: Dedicated imaging interface for Flux.1 with real-time prompt optimization and automatic generation of `.txt` sidecars containing metadata.
- **Current Version**: `0.18.2` (Runtime Alpha)
