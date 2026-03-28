# 📖 OPERATING MANUAL - Zentra Core

*System documentation for the Administrator (Admin).*
**Version:** 0.9.7 (Stable WebUI & I18N)

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

Zentra provides Function Keys (F1-F7) to interact with and reparameterize `config.json` live, with permanent memory.

* **[ F1 ] ACTION MANUAL (Help):** Calls the "root" protocols exposed by Plugins, showing free commands (e.g., `list:`, `cmd:`, `open:`).
* **[ F2 ] CHANGE AI MODEL:** Quickly select the neural network model (Llama, Gemma, Cloud, etc.) from the list indexed by the currently connected backend (Ollama/Kobold/Cloud).
* **[ F3 ] LOAD SOUL / PERSONALITY:** Changes the tone and system awareness by reading new text contexts (in `/personality/*.txt`).
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

## 👁️ 5. Vision & Multimodal Interaction (v0.9.7)

Zentra 0.9.7 introduces the **Vision Support System**, allowing the AI to "see" and analyze visual data.
- **Image Upload**: Drag & drop files directly into the web chat or paste images from your clipboard (**Ctrl+V**).
- **Multimodal AI**: Supported backends (Gemini 1.5/2.0, OpenAI GPT-4o, Ollama LLaVA) can describe, reason about, and extract text from images.
- **Visual Feedback**: Thumbnails are rendered in both your message bubble (sent) and the attachment toolbar (pending).

---

## 🔄 6. Response Management

- **Regenerate Response**: Use the circular arrow button next to any AI message to ask Zentra to try again. The system will remove the previous response and re-run the inference.
- **Internal Messaging**: Regenerating doesn't require re-typing; the UI uses a direct API channel to resend the previous prompt with its original context.

--- 

## 🛡️ 7. Security and Troubleshooting

1. **Graphic Interference Bug (Dashboard):** Zentra's engine asynchronously joins UI threads. Any text overlap is resolved by the total block `(Thread Join)` at the start of the F7 menu call.
2. **Logs:** Zentra logs are kept in the `/logs` directory. From F7 Config, it's possible to hide log reports from the chat to favor text readability (exclusive visual routing to parallel log `Console` or `File Only` recommended).
3. **Audio Trigger Loop:** Adjust the `Energy Threshold` parameter in **F7 → Listening** to calibrate ambient background noise that triggers Zentra into "THINKING" mode without any real input.

---
*End of documentation report v0.9.7.*
