# 📖 OPERATING MANUAL - Zentra Core

*System documentation for the Administrator (Admin).*
**Version:** 0.16.0 (3-Tier Hybrid Configuration)

---

## 🚀 1. Startup and Initial Control

When you run the executable (or Python startup script), Zentra starts its **Synchronized Boot** sequence.

### Pre-Flight Diagnostics
By default, the system checks:
- Integrity of vital folders (`core/`, `plugins/`, `memory/`, etc.).
- Hardware Status (CPU and RAM within acceptable limits).
- Audio and Voice Module status (Configured energy threshold).
- AI backend response verification (local ping to Ollama/Kobold or Cloud check).
- Active/Disabled Plugin scan indicating `ONLINE` or `DISABLED` for each.

During this boot phase, you can always press **ESC** to bypass any specific forced loading.

### ⚡ Fast Boot
If the Admin desires a lightning-fast startup, the **Fast Boot (Skip Diagnostics)** functionality has been implemented.
- By disabling diagnostics (activatable from the **F7** Control Panel under `SYSTEM`), Zentra Core will ignore all hardware text checks on screen.
- The useful terminal loading time drops to **~0.5 seconds**, returning interaction to the fixed prompt immediately.

### 🏁 1.1 First Run & Auto-Setup
When Zentra starts for the first time or if essential configuration files are deleted:
- The system automatically detects missing `.yaml` files in `zentra/config/data/`.
- It copies the factory-default templates from `*.yaml.example` to create active `.yaml` files.
- **Admin Note**: If you want to reset your configuration to factory defaults, simply delete `system.yaml` or `routing_overrides.yaml` and restart Zentra — it will handle the redeployment automatically.

---

## 🖥 2. Fixed User Interface (Safe Scrolling UI)

Zentra's terminal interface is built on an anchored architecture (`DECSTBM Scrolling Region`):
- **Dashboard (First Row - Plugin Dashboard):** If enabled, a background hardware plugin informs the user every 2 seconds about `CPU, RAM, VRAM and GPU STATUS` (no flickering generated).
- **Blue Bar (Third Row - System Status):** Dynamically shows central information:
  - **STATUS:**
    - 🟢 `READY` -> Zentra is listening or waiting for text commands.
    - 🟡 `THINKING...` -> Processing neural tree via LLM.
    - 🔵 `SPEAKING...` -> Voice playback via TTS engine (Piper).
    - 🔴 `ERROR/OFFLINE` -> AI provider failure or system lock.
  - **MODEL:** LLM currently in use.
  - **SOUL:** Active system prompt/personality module (roleplay or assistant).
  - **MIC / VOICE:** Shows if `ON` or `OFF`.

**Chat Area:** The interaction history (or STT translations) scrolls **only from row 7 downwards**, leaving the hardware and system "Dashboard" untouched.

---

## ⚙️ 3. Dynamic O-T-F (On-The-Fly) Configuration

## 💻 Native WebUI (v0.15.2)
Zentra 0.9.9 features a powerful native web interface accessible at `http://localhost:7070` (by default).
- **Real-time Chat**: Experience the AI stream directly in the browser.
- **Config Dashboard**: Change system settings via a modern GUI with instant synchronization to the core.
- **Audio Sync**: WebUI audio state is automatically synced with the terminal (F4/F5 status).
- **Dynamic Personalities**: The WebUI now automatically reflects any new `.txt` files added to the `personality/` folder without manual entries in `config.json`.

Zentra provides Function Keys (F1-F7) to interact with and reparameterize `config.json` live, with permanent memory.

* **[ F1 ] ACTION MANUAL (Help):** Calls the "root" protocols exposed by Plugins, showing free commands (e.g., `list:`, `cmd:`, `open:`).
* **[ F2 ] CHANGE AI MODEL:** Quickly select the neural network model (Llama, Gemma, Cloud, etc.) from the list indexed by the currently connected backend (Ollama/Kobold/Cloud).
* **[ F3 ] LOAD SOUL / PERSONALITY:** Changes the tone and system awareness. Zentra now automatically scans the `/personality/*.txt` folder at every launch and menu access.
* **[ F4 ] TOGGLE LISTENING (MIC):** Temporarily mutes acoustic reception (On/Off).
* **[ F5 ] TOGGLE VOICE (TTS):** Enables or mutes the response voice synthesis. The AI will continue to process only via visual chat.

### 🎛️ THE CONTROL PANEL [ F7 ]
Using Inquirer Curses-based graphics, it offers granular control over the Zentra Core Engine.
Navigable via Arrow Keys (`Up`, `Down`, `Right`, `Left`), it allows editing of booleans (True/False), numbers, or strings (via `Enter` text input).

**Save and Cold Reboot Safety Logic:**
- If the user presses `ESC` without changes or specifically requests Exit without Saving (`DISCARD`), no settings are rewritten to the configuration, affecting zero original files. Full silent return to terminal.
- If any visual change occurs, pressing the `RESTART ZENTRA` command or confirmed exit via `Enter` will physically write the `config.json` and trigger an automatic **Cold Reboot (Terminated Stop + Forced Restart, id 42)** in 1 second. This ensures that cache and global settings align perfectly at every moment.

---

## 🔌 4. Modular System / Plugins

Zentra is infinitely expandable by placing folders in `plugins/`.
All plugins respond to unified interfaces that export `shell commands` and update Zentra's dynamic configuration (Config Syncing).

- **Extension Architecture (JIT)**: Plugins can now have "sub-plugins" called Extensions, loaded in real-time (Lazy Loading). An example is the **Zentra Code Editor**, an extension of the Drive plugin based on the Visual Studio Code engine (Monaco) to edit code and text files directly from the WebUI.
- **Drive Pro (Absolute Navigation)**: The Drive plugin allows you to navigate the entire filesystem of the host server starting from the `C:\` root and allows switching drives (e.g. `D:`, USB drives) thanks to the Absolute Drive Selector.
- **Native WebUI Plugin**: The browser interface (`plugins/web_ui`) is a native component (Port 7070), managing chat, configuration, and multimodal data in real-time.
- **Clean Disabling**: If a plugin or module is faulty but essentially non-blocking, disabling it from F7 (`Plugins` section) or the WebUI Dashboard will move the code to memory fallback, bypassing it.

---

## 👁️ 5. Vision & Multimodal Interaction (v0.15.2)

Zentra 0.9.9 introduces the **Vision Support System**, allowing the AI to "see" and analyze visual data.
- **Image Upload**: Drag & drop files directly into the web chat or paste images from your clipboard (**Ctrl+V**).
- **Multimodal AI**: Supported backends (Gemini 1.5/2.0, OpenAI GPT-4o, Ollama LLaVA) can describe, reason about, and extract text from images.
- **Visual Feedback**: Thumbnails are rendered in both your message bubble (sent) and the attachment toolbar (pending).

---

## 🔄 6. Response Management

- **Regenerate Response**: Use the circular arrow button next to any AI message to ask Zentra to try again. The system will remove the previous response and re-run the inference.
- **Internal Messaging**: Regenerating doesn't require re-typing; the UI uses a direct API channel to resend the previous prompt with its original context.

---

## 🎨 7. Image Generation (v0.15.2)

Zentra can create visual content using the `IMAGE_GEN` plugin.
- **How to use**: Simply ask Zentra to "Generate an image of..." or "Draw a...".
- **External Servers**: By default, it uses **Pollinations.ai** for high-speed, filter-free generation.
- **Interaction**: The generated image will appear directly in the chat with options to download or zoom.

---

## 🗂️ 8. Zentra Drive (HTTP File Manager)

Zentra 0.15.2 integrates a native and secure file manager, accessible at `http://localhost:7070/drive` (or by clicking the Drive link in the Config Panel Navbar).

### Key Features
- **Dual-Panel Layout**: Left navigation tree (for expanding directories) and detailed list on the right (name, size, modified date).
- **Path Traversal Protection**: Backend security layer that strictly prevents users from navigating above or outside the configured `Root Directory`.
- **Drag & Drop Support**: Simplified file uploading by dragging files directly into the "Dropzone".
- **Streaming Multi-Upload**: Capable of handling large file uploads bypassing standard RAM limits, showing a real-time progress bar that explicitly indicates the target directory.

### Configuration
The Drive Module can be configured via the WebUI Panel (**Drive** tab):
- **Root Directory**: The base path (e.g., `C:\Users\Admin`). If left empty, it defaults to the current system user's Home directory.
- **Max Upload Size**: Sets the server's acceptance limit (in MB).
- **Allowed Extensions**: CSV field to restrict uploads to specific formats (e.g., `pdf, jpg`). If empty, no restrictions apply.

---

## 🛡️ 9. Advanced Security (Zentra PKI)

Zentra 0.15.2 introduces an integrated **PKI (Public Key Infrastructure)** to ensure secure HTTPS connections across your entire local network.

### Certificates and Root CA
To unlock features like the **Microphone** and **Webcam** on mobile browsers (which require secure contexts), Zentra acts as its own Certificate Authority:
1. **Root CA**: Automatically generated on first boot in `certs/ca/`.
2. **Installation**: You must download and install the `Root CA` certificate on your device (Mobile or remote PC) and set it as "Trusted".
3. **Download**: The certificate can be downloaded directly from the **Security** tab in the Config Panel or from the **Neural Link** modal in the chat.

---

## 📱 10. Mobile-First Interface & WebRTC Audio

Zentra is optimized for use on smartphones and tablets.
- **Hamburger Menu**: On small screens, the sidebar is hidden and replaced by a sliding menu (accessible via the `☰` icon at the top left).
- **Push-to-Talk (PTT) Audio**: From PC you use `Ctrl+Shift` globally, while **from phone or browser** you use the Microphone button next to the chat box.
  - **Walkie-Talkie (Hold)**: Hold the 🎙️ button, speak, release to send the audio.
  - **Hands-Free (Tap-To-Toggle)**: Do a quick click on the 🎙️ button. The padlock will appear (🔴 🔓) and recording will continue while you put your phone down. Press again to stop and convert to text using the native client-side WebRTC API and local server-side Pydub converter.
- **Neural TTS Autoplay**: Despite Apple/Android media blocks, the TTS voice synthesis will always start automatically upon response using an ingenious HTML5 proxy player integrated into the framework.

---

## 🛠️ 11. Troubleshooting & Security

1. **Graphic Interference Bug (Dashboard):** Zentra's engine asynchronously joins UI threads. Any text overlap is resolved by the total block `(Thread Join)` at the start of the F7 menu call.
2. **Logs:** Zentra logs are kept in the `/logs` directory. From F7 Config, it's possible to hide log reports from the chat.
3. **Audio Trigger Loop:** Adjust the `Energy Threshold` parameter in **F7 → Listening** to calibrate ambient background noise if the physical microphone acts up.

---

## 🤖 12. Autonomous Agent and Sandbox (Code Jail)

From version 0.9.9 Zentra integrates a **Cognitive Loop (Agentic Loop)**. This transforms the system from a simple chatbot to an agent capable of complex multi-step reasoning (Chain of Thought).

- **Thought Bubbles (Live Traces)**: When you ask for a complex operation (e.g. "Take a photo of this file"), you will see an animated live trace appear in the WebUI. Zentra is actively developing an action plan calling hardware Tools or network plugins before answering you completely.
- **Zentra Code Jail (Sandbox)**: Zentra can write Python code snippets on the fly and execute them (in the secure folder `/workspace/sandbox/`) to solve long arithmetic calculations, build algorithms or manipulate complex data with absolute precision. A special security AST machine intervenes before execution: if the AI tries to use dangerous system commands, the action is blocked instantly, keeping the computer always protected.

---

## 🧭 13. Tiered AI Instruction System (v0.16.0)

Zentra v0.16.0 introduces a **3-Tier Hybrid Configuration** architecture to control how the AI routes and handles specific plugin commands. Understand which layer to use:

### Tier overview

| Layer | Where | Scope | Use For |
|---|---|---|---|
| **1. Special AI Instructions** | Config Panel → Persona tab | Global | General behavior, tone, communication style |
| **2. Routing Overrides (YAML)** | Config Panel → Routing tab | Per-plugin | Forcing specific tool actions, parameter constraints |
| **3. Plugin Manifest** | `zentra/core/registry.json` | Default | Factory defaults (set by developers) |

> **[!NOTE]**: Layer 1 (Special AI Instructions) defeats Layer 3 but Layer 2 (YAML overrides) defeats **all** layers for its specific plugin.

### How to use the Routing Editor (Browser)
1. Open the Config Panel at `https://localhost:7070/zentra/config/ui`.
2. Click the **Routing** tab.
3. You'll see the **Custom Plugin Overrides** section at the bottom.
4. Click **+ Add Override** to add a new rule. The tag must match the plugin name exactly (e.g. `WEBCAM`, `IMAGE_GEN`).
5. Write your instruction in plain language — the AI receives it verbatim with each prompt.
6. Click **Save Overrides** to persist to disk.

### How to edit the YAML directly (Drive Editor)
1. In the Routing tab, click **📝 Edit in Drive**.
2. The Monaco Code Editor will open `routing_overrides.yaml` directly for full editing.
3. Save with `Ctrl+S`.

### Practical examples
```yaml
overrides:
  # Always use the user's phone camera instead of the server webcam
  WEBCAM: "When the user says 'phone', 'mobile', or 'browser', ALWAYS use target='client'."

  # Restrict image generation to explicit requests only
  IMAGE_GEN: "Only call generate_image if the user explicitly asks to 'create', 'draw', or 'generate' an image."

  # Make web searches prefer technical sources
  WEB: "Prioritize technical documentation, Wikipedia, and official sources. Avoid gossip or news aggregators."
```

---

## 📱 14. Remote PTT & Hardware Triggers
Version 0.16.0 introduces the **Remote Triggers** plugin, allowing you to activate Zentra's microphone from external devices or hardware keys.

### 🎧 MediaSession Integration (Bluetooth/Headphones)
Zentra can hijack the **Play/Pause** buttons on your Bluetooth headphones or smartphone (iPhone/Android).
- **How it works**: When the WebUI is open, Zentra starts a silent audio stream to claim priority over your device's media buttons.
- **Controls**: Press "Play" to start recording, "Pause" to stop.
- **Visual Feedback**: On Android/iOS lock screens, you will see a "Zentra — Remote Trigger Enabled" notification.
- **Settings**: If the "tututu" startup sound or the media overlay is bothersome, you can disable `Enable MediaSession` in the **Remote Triggers** tab of the Config Panel.

### 🕹️ Hardware Webhooks (Arduino/ESP32/USB)
You can build your own physical PTT button using an Arduino or ESP32 by sending HTTP requests to the Zentra server:
- **PTT Start**: `GET /api/remote-triggers/ptt/start`
- **PTT Stop**: `GET /api/remote-triggers/ptt/stop`
- **PTT Toggle**: `GET /api/remote-triggers/ptt/toggle`

### 🛠️ Configuration
Manage these features from the WebUI:
- **Enable MediaSession**: Toggles Bluetooth/Media key interception.
- **Enable Volume Keys**: Toggles volume key PTT on Android devices.

---
*End of documentation report v0.16.0.*
