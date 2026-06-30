# 💬 4. Chat Interface & UI

> *"The main conversational interface where you talk with Hecos, send images, and trigger commands. A cybernetic nexus connecting your local core to the cloud."*

The **Chat** is the primary interface of the Hecos WebUI. It provides a rich, modern environment for interacting with your AI.

![Hecos Chat Interface](https://github.com/Hecos-Project/Hecos-Assets/blob/main/Hecos_ImageGen_Module_1.png?raw=true)

---

### 🎛️ SYSTEM OVERVIEW


---

## Key Features
- **Rich Text & Code:** Supports full Markdown rendering, tables, and code blocks with syntax highlighting.
- **Multimodal Input:** Drag and drop images directly into the chat to have Hecos analyze them using its Vision capabilities.
- **Voice Integration:** Click the microphone icon or use `Ctrl+Shift+Z` to dictate messages using the Push-to-Talk feature.
- **Session History:** The left sidebar allows you to manage multiple conversations, rename them, or delete them. All sessions are saved in your local Episodic Memory Vault.
- **Privacy Modes:** Choose between Normal (saved), Auto-Wipe (RAM only), or Incognito (no trace) for each conversation.
- **Direct Commands:** Type `/` in the input bar to access the HDCS (Hecos Direct Command System) for instant actions without conversational overhead.

---

## 🛠️ Deep Dive: The Cybernetic Interface

### 1. Left Sidebar: Neural Configuration
The sidebar acts as the telemetry and control deck for the active companion session. Moving from top to bottom:

* **System Status:** Real-time diagnostics displaying the architecture type (**Cloud** or **Local** backend), the active **Model Name**, and the loaded personality matrix—referred to as the **Soul** (e.g., `Motoko Kusanagi`).
* **Privacy Layer:** Cyber-hardened conversation states:
    * `Normal`: Standard operations, persistent logs.
    * `Auto-Wipe`: Volatile memory session; data automatically purges from RAM upon system reboot.
    * `Incognito`: Dark routing. Zero footprint, zero logs, zero traces left behind.
* **Audio Grid:** High-fidelity voice telemetry panel featuring three toggle states:
    * `Continuous Audio`: Persistent background listening.
    * `Voice Activation`: Triggers processing upon voice activity detection.
    * `PTT (Push-to-Talk)`: Dual-mode input. Click the chat icon to switch between standard On/Off or PTT. Alternatively, use the **`Ctrl+Shift`** hotkey combo to engage a hardware-level walkie-talkie mode.
* **Control Room:** A collapsible, slide-out node integrated directly within the chat view to manage active widgets, widgets pipelines, and environmental states.
* **Packet Manager Link:** Located at the absolute bottom of the sidebar, this terminal shortcut bypasses the Central Hub, dropping you straight into the module installer/updater matrix.

![Hecos Chat Interface](https://github.com/Hecos-Project/Hecos-Assets/blob/main/Hecos_Chat_0020.png?raw=true)


### 2. Main Chat Engine & Top Terminal
The central processing view handles data rendering and environmental monitoring.

* **Top Deck Indicators:** Quick-access relays tracking audio stream status alongside macro-navigation nodes: **Central Hub**, **Drive** (The Hecos localized file manager), and the **Flows Panel** for visual automation routing.
* **Online Indicator:** A central status beacon pulsing visually to confirm whether the localized core or cloud proxy is actively streaming responses.
* **Dynamic Input Bar & HDCS (Hecos Direct Command System):** Initializing your string input with the **`/`** character instantly deploys the Direct Commands overlay window. 
    
    Commands can also be hot-linked via voice synthesis. Saying **"slash"**, **"command"**, or **"comando"** followed by the directive identifier activates the script immediately. 
    
    > *Execution Example:* Voicing *"slash souls"* compiles into `/souls`, triggering a complete diagnostic printout of all locally installed companion personalities (souls) without clogging the chat context window.