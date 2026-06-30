# 💻 The Console (CLI)

> *"The command window where the system thinks, performs security checks, and lets you manage everything."*

The **Hecos Console** is the raw, native terminal window that opens when you first launch Hecos. It is the beating heart of the system.

![Hecos - Helping Companion System](https://github.com/Hecos-Project/Hecos-Assets/blob/main//Hecos_Core_002.png?raw=true)


## Why a Console?
While the WebUI is the "face" of Hecos, the Console is the "brain". It guarantees absolute transparency. Every action the AI takes, every tool it invokes, and every API call it makes is logged here in real-time.

## Key Features
- **Real-time Telemetry:** Displays hardware usage, backend loading status, and active module states.
- **Security Auditing:** Watch the system execute commands. If a flow or plugin triggers a local process (like opening a file or running a Python script), the exact command is printed here.
- **Server Hub:** The Console acts as the local server host for the WebUI. Closing this window shuts down the entire Hecos system.
- **Fast Input:** You can type text directly into the console to chat with the AI if you prefer a distraction-free, terminal-only experience.
