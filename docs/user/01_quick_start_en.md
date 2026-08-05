# ⚡ 2. Quick Start Guide

Welcome to Hecos! Follow these steps to set up the system and start using AI on your PC immediately.

## 1. Installation

> [!TIP]
> **Recommended Method — Install via the Tray!** Download only **Hecos Tray** (the lightweight package), launch it, and open the **Tray Dashboard**. Go to the **Updates** tab and click *Download / Install Core*: the system downloads and installs everything automatically. It’s the simplest, most guided, and most complete way.

> [!IMPORTANT]
> **Installation Path**: We strongly recommend extracting and installing Hecos in a root directory like `C:\Hecos`. Avoid installing it in `Downloads`, `Desktop`, or deep folders, as long paths or special characters/spaces in the path can cause startup issues or broken functionalities.

> [!WARNING]
> **System Dependencies**: The Hecos ecosystem now includes an automatic **External Dependency Manager (EDM)**. During or after installation, if critical components (like `VC_redist`, `Tesseract OCR`, or `Node.js`) are missing, the WebUI will notify you, allowing you to download and install them in the background with a single click. Ensure you are connected to the internet to allow the downloads.

**Alternative method (advanced):** If you already downloaded the full Core package, you can use the automatic setup scripts in the root folder:
- **Windows:** Double-click `START_SETUP_HERE_WIN.bat`
- **Linux:** Open a terminal and run `bash START_SETUP_HERE_LINUX.sh`

These scripts will automatically install dependencies and launch the **Setup Wizard** in your browser.

## 2. The Setup Wizard
On the first launch, your browser will open to `http://localhost:7070`. Follow the guided steps:
1. **Welcome**: Click "Get Started".
2. **Language**: Select your preferred language.
3. **Choose the Brain (AI Provider)**: 
   - **Cloud (Online)**: Use powerful models like Gemini or GPT-4o. You will need to enter your **API Key**.
   - **Local (Offline)**: If you have Ollama or KoboldCpp installed on your PC, Hecos will connect automatically. **In this case, you DON'T need any API key**, everything runs on your hardware!
4. **Image Generation**: Currently, image creation requires an online provider. The fastest and best way is to create a free account on **HuggingFace**, generate an "Access Token", and enter it in Hecos's settings to use advanced models like **FLUX.1-dev**.
5. **Configure Personality**: Choose the "soul" of your assistant (e.g., Urania or Atlas).
6. **Finish**: Click "Save and Start".

## 3. First Use
Now that Hecos is active, here is how to interact:
- **Chat**: Type in the text bar at the bottom of the WebUI and press Enter.
- **Voice**: 
  - Click the microphone icon in the WebUI.
  - Or use the global shortcut **Ctrl+Shift+Z** (Windows) to talk without even opening the browser.
- **Vision**: Drag an image into the chat to ask Hecos to describe or analyze it.

## 4. Control Panel (F7)
To change parameters, add new API keys, or activate plugins:
- Press **F7** on your keyboard or click the gear/logo icon in the WebUI to open the **Hecos Hub**.
- Changes are saved instantly.

## 5. Tray — Your Universal Remote

Hecos Tray is much more than a simple icon: it’s the quick control center for the entire system.
- The icon sits next to the Windows clock, always available without taking up space.
- **Double-click** the icon to open the **Tray Dashboard**, where you can start/stop Hecos, read live logs, monitor active processes, and install updates.
- **Right-click** for a quick menu with the most common actions.

---
*You’re all set! Start exploring the potential of your new sovereign AI operating layer.*
