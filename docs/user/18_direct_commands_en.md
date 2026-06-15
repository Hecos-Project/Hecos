# 18. Direct Commands (HDCS)

Imagine having a **magic wand** that lets you give precise orders to Hecos without having to have a long conversation with the Artificial Intelligence. This magic wand is called **HDCS (Hecos Direct Command System)**, or simply: **Direct Commands**.

Normally, when you write to Hecos, the AI has to read your message, think about what you want to do, choose the right tool, and then execute it. Sometimes, however, you know *exactly* what you want to do and you want it to happen **immediately**, in the blink of an eye!

That's what direct commands are for. They all start with a slash **`/`** and tell the system to execute an action right away, completely bypassing the AI's "brain".

---

## 🎩 How to use them in the Chat

Using direct commands in the chat is as easy as using emojis on WhatsApp!

1. Click on the chat bar where you usually type your messages.
2. Type the **`/`** (slash) character.
3. **Magic!** A dropdown menu will appear right above the text box.
4. This menu contains *all* of the commands available in the system, both the user-friendly aliases and the auto-generated plugin tools.
5. You can scroll through the list with your mouse or keyboard arrow keys, or you can keep typing to filter the list. For example, if you type `/weather`, you will see the weather command appear.
6. Press **Tab** or click on the command with your mouse to choose it.
7. If the command needs extra information (like the city for the weather), it will leave a space for you. Type, for example, `/weather London` and press **Enter**. Done!

---

## 🔍 The "Spotlight": Commands always at your fingertips

What if you're not in the chat? Maybe you're looking at the plugins page or reading another screen. Don't worry! You can use direct commands *wherever* you are thanks to the **Spotlight**.

The Spotlight is a special floating search bar. To summon it:
1. Press the secret combination on your keyboard: **`Ctrl + Alt + Space`** (press Control, Alt, and the spacebar together).
2. The screen will slightly dim and a beautiful search bar will appear in the center.
3. Type what you're looking for (e.g. `img` or `weather` or `calendar`).
4. Select the command with the arrow keys and press **Enter**. 
5. Hecos will execute the action instantly in the background and show you a little confirmation message!

---

## 🧩 Using Direct Commands in "Flows"

Flows is the place where you create automatic routines by linking many nodes together as if they were Lego bricks. 
Sometimes, you might want to use a direct command inside a Flow, to ensure an action is executed precisely without asking the AI.

To do this, you just need to use a special node:
1. In the left menu of Flows, open the **SYSTEM** or **EXECUTOR** category.
2. Find the brick called **`execute_slash_command`** and drag it onto your screen.
3. This node has a text field called `command`. That's where you need to write the command you want to execute!
4. **The magician's trick:** If you click on the text box of the node and type `/`, the autocomplete dropdown will open just like in the chat! Select the command, and it will be written for you.
5. Alternatively, you can always press `Ctrl + Alt + Space` to search for the command. If you are inside the node's text box, pressing Enter won't execute the command right away, but will magically **paste** it into the node, ready to be saved!

---

## 📖 Complete Catalog of Direct Commands

Here is the complete list of all direct commands integrated into Hecos, categorized. Each command includes its description, alternative aliases, and 3 practical examples of usage.

### 1. System Commands (CORE Category)

These are the fundamental commands for managing the Hecos application, the chat session, and system configurations.

| Base Command | Alternative Aliases | Description |
| :--- | :--- | :--- |
| `/help` | `/?`, `/comandi` | Shows the list of all available slash commands and active capabilities in the system. |
| `/status` | `/info` | Shows system status (active AI model, loaded plugins, RAM usage, and Hecos version). |
| `/clear` | `/pulisci`, `/reset` | Clears the entire current chat conversation history to free memory. |
| `/config get` | | Reads an internal configuration value using dot notation (e.g., `category.key`). |
| `/config set` | | Temporarily sets a configuration value in RAM memory. |
| `/reload` | `/reload_commands` | Forces a reload of the command registry (useful after installing new plugins). |

#### Practical Examples:
* **`/help`**
  1. `/help` (shows the main command list)
  2. `/?` (shows the quick reference help)
  3. `/comandi` (shows the command list in Italian)
* **`/status`**
  1. `/status` (visualizes active model and resources)
  2. `/info` (shows the running Hecos version info)
  3. `/status` (useful for checking if Ollama/Kobold backend is online)
* **`/clear`**
  1. `/clear` (empties the current chat screen)
  2. `/pulisci` (clears the conversation context)
  3. `/reset` (starts a conversation from scratch)
* **`/config get`**
  1. `/config get ai.model` (shows the configured AI model)
  2. `/config get reminder.reminder_mode` (shows the current reminder alert mode)
  3. `/config get system.theme` (shows the interface theme)
* **`/config set`**
  1. `/config set ai.model gemini/gemini-2.0-flash` (temporarily sets the model to Gemini 2.0 Flash)
  2. `/config set reminder.max_reminders 30` (limits active reminders to 30)
  3. `/config set system.theme dark` (changes the UI theme to dark)
* **`/reload`**
  1. `/reload` (reloads all registered commands)
  2. `/reload_commands` (updates the autocomplete list)
  3. `/reload` (run if a newly loaded plugin does not appear in autocomplete)

---

### 2. Flow Commands (FLOWS Category)

These commands allow you to list, run, and check the status of automation pipelines created in the **Flows** section.

| Base Command | Alternative Aliases | Description |
| :--- | :--- | :--- |
| `/flow list` | `/flows`, `/flow ls` | Lists all available flows saved in the workspace (`workspace/flows/`). |
| `/flow run` | `/flow exec` | Runs a specific flow immediately by name. |
| `/flow trigger` | `/trigger` | Manually triggers a specific flow (works identically to run). |
| `/flow status` | `/flow log` | Shows the last execution log (the result of the last run) of a flow. |

#### Practical Examples:
* **`/flow list`**
  1. `/flow list` (lists flows with their trigger type and active/inactive status)
  2. `/flows` (lists all flow YAML files quickly)
  3. `/flow ls` (shows a compact list of flows)
* **`/flow run`**
  1. `/flow run morning_routine` (executes the scheduled morning routine immediately)
  2. `/flow run check_weather_alert` (runs the weather checking flow)
  3. `/flow exec turn_off_everything` (runs the system shutdown flow)
* **`/flow status`**
  1. `/flow status morning_routine` (shows if the morning routine succeeded or failed)
  2. `/flow log check_weather_alert` (prints execution logs and errors for the weather check)
  3. `/flow status data_backup` (reads the log of the backup flow)

---

### 3. Plugin Commands (PLUGINS Category)

These commands are exposed by the various optional modules enabled in Hecos.

| Base Command | Alternative Aliases | Description |
| :--- | :--- | :--- |
| `/soul` | `/persona`, `/personality` | Changes the active AI soul/personality (e.g., professional, playful, etc.). |
| `/souls` | `/personas` | Lists all installed souls/personalities in the system. |
| `/calendar` | `/calendario`, `/appuntamenti` | Lists upcoming events from the Hecos Calendar. |
| `/img` | `/image`, `/photo`, `/foto` | Generates an AI image from a text description. |
| `/list` | `/lists`, `/liste` | Lists all active lists (Shopping, Todo, etc.). |
| `/lista` | | Shows all items inside a specific list. |
| `/list add` | `/lista aggiungi` | Adds an item to a list (creates the list if it doesn't exist). |
| `/list done` | `/lista spunta` | Marks an item as checked/completed in a list. |
| `/reminder` | `/ricorda`, `/promemoria` | Schedules a new reminder using natural language time expressions. |
| `/reminders` | `/promemoria list` | Lists all active reminders along with their unique IDs. |
| `/weather` | `/meteo`, `/tempo` | Shows current weather conditions or forecasts for a city. |

#### Practical Examples:
* **`/soul`**
  1. `/soul Motoko` (switches active personality to "Motoko")
  2. `/persona 2` (switches to the second personality in the list)
  3. `/personality Jarvis` (switches personality to "Jarvis" style)
* **`/calendar`**
  1. `/calendar` (shows the agenda for the next few days)
  2. `/calendario` (shows upcoming events)
  3. `/appuntamenti` (lists today's appointments)
* **`/img`**
  1. `/img a little space kitten wearing an astronaut helmet` (generates the image)
  2. `/photo cyberpunk portrait of a girl, neon lights, 8k` (generates a photo-style render)
  3. `/foto oil painting of a sunset over the sea` (generates an art style render)
* **`/list` / `/lista` / `/list add` / `/list done`**
  1. `/list add Shopping Eggs` (adds "Eggs" to "Shopping" list)
  2. `/lista Shopping` (shows items inside the "Shopping" list)
  3. `/list done Shopping Eggs` (marks "Eggs" as completed/purchased)
* **`/reminder` / `/reminders`**
  *(See the dedicated section below for detailed usage details)*
  1. `/reminder buy milk at 18:30` (sets a reminder for 18:30 today)
  2. `/reminders` (lists active reminders and their short IDs)
  3. `/ricorda call mom in 15 minutes` (sets a relative reminder)
* **`/weather`**
  1. `/weather London` (shows the weather for London)
  2. `/meteo Milan` (shows the weather for Milan in Italian)
  3. `/weather` (shows the weather for the default configured home city)

---

## ⏰ Deep Dive: Using Reminders (`/reminder` vs `/reminder.set_reminder`)

The reminder plugin exposes two ways to be invoked via direct commands. Understanding the difference is key to avoiding syntax errors.

### 1. The Friendly Command: `/reminder`
This command is built for human interaction. It uses a smart natural language parser that analyzes your input string, extracts the time/date and the reminder text, and registers it.

* **Syntax:** `/reminder <what to remind> at/in/on <time/date>`
* **How it works:** The system reads everything after the command, looks for prepositions like "at", "in", "on", "alle", "tra", "il", and calculates the correct trigger date automatically.

#### Correct Examples:
1. **`/reminder pick up dry cleaning at 17:45`** (sets a reminder for 17:45 today)
2. **`/ricorda turn off the oven in 20 minutes`** (sets a relative reminder expiring in exactly 20 minutes)
3. **`/promemoria call doctor on 25/08 at 09:00`** (sets a reminder for a specific future date and time)
4. **`/reminder take the cake out of the oven in 30 minutes --interactive`** (append `--interactive` or `-i` to force an interactive reminder that loops the alarm until explicitly stopped or snoozed)

> [!TIP]
> If you want to check active reminders or cancel one of them, type `/reminders`. It will show all active reminders with their 8-character IDs. You can cancel a reminder using the auto-generated `/reminder.cancel_reminder <ID>` command (e.g., `/reminder.cancel_reminder a1b2c3d4`).

---

### 2. The Technical/Auto-Generated Command: `/reminder.set_reminder`
This command belongs to the auto-generated commands category (see below) and maps directly to the internal Python function signature.

* **Why it fails in Chat:** The Python function expects separate parameters: `title` and `when`. If you type `/reminder.set_reminder buy milk at 18:30`, the command executor assigns the entire string `"buy milk at 18:30"` to the first parameter (`title`), leaving the second required parameter (`when`) empty. This results in a syntax error:
  `❌ Incorrect arguments for /reminder.set_reminder` (missing required argument 'when').
* **When to use it:** It is extremely useful in **Flows**, where parameters are explicitly mapped into separate fields, or for calling tools that only accept a single argument.

---

## ⚙️ Advanced Auto-Generated Commands (`/<tag>.<method>`)

Hecos features a special capability: **it automatically generates a direct command for every tool method exposed by any plugin or module**, in the format:
`/<plugin_tag>.<method_name>`

These commands are intended for developers and automation flows, but are available to use in chat or the Spotlight.

### How do they work?
When you type a command like `/<tag>.<method> <arguments>`, Hecos takes the text following the command and passes it as the **first positional argument** to the underlying Python method. If the method requires only one parameter, it will work immediately.

#### Popular Auto-Generated Commands:
* **`/executor.reboot_system`** (restarts Hecos)
  * Example 1: `/executor.reboot_system` (restarts immediately, no arguments required)
  * Example 2: `/executor.reboot_system`
  * Example 3: `/executor.reboot_system`
* **`/executor.kill_process`** (kills a Windows process by name)
  * Example 1: `/executor.kill_process chrome.exe` (terminates Google Chrome)
  * Example 2: `/executor.kill_process notepad` (closes Notepad)
  * Example 3: `/executor.kill_process vlc` (closes VLC player)
* **`/browser.open_url`** (opens a page in the AI-controlled browser)
  * Example 1: `/browser.open_url https://www.google.com` (opens Google)
  * Example 2: `/browser.open_url https://wikipedia.org` (opens Wikipedia)
  * Example 3: `/browser.open_url localhost:7070` (opens the local Hecos WebUI)
