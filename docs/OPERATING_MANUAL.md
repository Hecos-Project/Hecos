# 📖 OPERATING MANUAL - Zentra Core

*System documentation for the Administrator (Admin).*
**Version:** 0.12.0 (Zentra Drive & Standalone WebUI)

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

## 💻 Native WebUI (v0.9.9)
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

- **Clean Disabling:** If a plugin or module is faulty but essentially non-blocking, disabling it from F7 (`Plugins` section) will move the code to memory fallback, bypassing it at startup.

*(e.g.: Hiding the top HW bar only requires setting `Plugin Dashboard Enabled` to "False" in F7 and restarting)*

---

## 👁️ 5. Vision & Multimodal Interaction (v0.9.9)

Zentra 0.9.9 introduces the **Vision Support System**, allowing the AI to "see" and analyze visual data.
- **Image Upload**: Drag & drop files directly into the web chat or paste images from your clipboard (**Ctrl+V**).
- **Multimodal AI**: Supported backends (Gemini 1.5/2.0, OpenAI GPT-4o, Ollama LLaVA) can describe, reason about, and extract text from images.
- **Visual Feedback**: Thumbnails are rendered in both your message bubble (sent) and the attachment toolbar (pending).

---

## 🔄 6. Response Management

- **Regenerate Response**: Use the circular arrow button next to any AI message to ask Zentra to try again. The system will remove the previous response and re-run the inference.
- **Internal Messaging**: Regenerating doesn't require re-typing; the UI uses a direct API channel to resend the previous prompt with its original context.

---

## 🎨 7. Image Generation (v0.9.9)

Zentra can create visual content using the `IMAGE_GEN` plugin.
- **How to use**: Simply ask Zentra to "Generate an image of..." or "Draw a...".
- **External Servers**: By default, it uses **Pollinations.ai** for high-speed, filter-free generation.
- **Interaction**: The generated image will appear directly in the chat with options to download or zoom.

---

## 🗂️ 8. Zentra Drive (HTTP File Manager)

Zentra 0.12.0 integrates a native and secure file manager, accessible at `http://localhost:7070/drive` (or by clicking the Drive link in the Config Panel Navbar).

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

Zentra 0.12.0 introduces an integrated **PKI (Public Key Infrastructure)** to ensure secure HTTPS connections across your entire local network.

### Certificates and Root CA
To unlock features like the **Microphone** and **Webcam** on mobile browsers (which require secure contexts), Zentra acts as its own Certificate Authority:
1. **Root CA**: Automatically generated on first boot in `certs/ca/`.
2. **Installation**: You must download and install the `Root CA` certificate on your device (Mobile or remote PC) and set it as "Trusted".
3. **Download**: The certificate can be downloaded directly from the **Security** tab in the Config Panel or from the **Neural Link** modal in the chat.

---

## 📱 10. Mobile-First Interface

Zentra is now optimized for use on smartphones and tablets.
- **Hamburger Menu**: On small screens, the sidebar is hidden and replaced by a sliding menu (accessible via the `☰` icon at the top left).
- **Safe Area & Gestures**: Headers and configuration tabs are optimized for touch and horizontal scrolling.
- **Neural Link**: On mobile, the first interaction requires tapping the "Establish Connection" button to unlock the browser's AudioContext and allow the AI to speak and listen.

---

## 🛡️ 11. Security and Troubleshooting

1. **Graphic Interference Bug (Dashboard):** Zentra's engine asynchronously joins UI threads. Any text overlap is resolved by the total block `(Thread Join)` at the start of the F7 menu call.
2. **Logs:** Zentra logs are kept in the `/logs` directory. From F7 Config, it's possible to hide log reports from the chat to favor text readability (exclusive visual routing to parallel log `Console` or `File Only` recommended).
3. **Audio Trigger Loop:** Adjust the `Energy Threshold` parameter in **F7 → Listening** to calibrate ambient background noise that triggers Zentra into "THINKING" mode without any real input.

---
*End of documentation report v0.12.0.*
