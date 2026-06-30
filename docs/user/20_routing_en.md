# 🧭 14. AI Instruction Routing & Plugin Overrides

Hecos uses a **three-tier instruction system** to precisely control how the AI behaves with every plugin. Understanding this system unlocks one of Hecos's most powerful features: the ability to permanently reprogram the AI's behavior without touching a single line of code.

---

## 14.1 — The Three Instruction Tiers

| Priority | Level | Where | Scope |
|:---:|---|---|---|
| **3 (highest)** | **Plugin Overrides** | `routing_overrides.yaml` / Routing Panel | Per-plugin, always wins |
| **2** | **Special Instructions** | Config → AI Behaviour | Global personality & tone |
| **1 (lowest)** | **Plugin Manifest Default** | `registry.json` | Factory default per plugin |

> **Rule**: A higher-priority tier always wins. What you write in the Overrides file is **law** — even if the user explicitly asks the AI to ignore it.

---

## 14.2 — The Routing Mode (Dual Engine)

Before the Overrides panel, the **Routing Mode** selector controls *how* the AI formats its commands:

| Mode | Description | Best for |
|---|---|---|
| **Auto** | Hecos chooses automatically based on the model | Most users — recommended |
| **Force Native (JSON)** | Commands sent as structured JSON | Large, modern models (GPT, Gemini, Llama 3+) |
| **Force Legacy (Tag)** | Commands sent as `[PLUGIN: action]` text tags | Small local models (Qwen 0.5b, Gemma 2b) |

The **Locked Legacy Models** field lets you specify model names that will always use Legacy mode, even in Auto.

---

## 14.3 — Plugin Routing Overrides

This is the advanced section. Each **plugin tag** (e.g. `IMAGE_GEN`, `WEBCAM`, `WEB`) can receive a custom text instruction that will be **prepended to every system prompt** before that plugin is called.

Think of it as whispering something secret into the AI's ear before it acts — every single time.

### How to Access It

1. Open **Central Hub** (F7)
2. Go to **Intelligence → Routing**
3. Scroll down to the **"PLUGIN ROUTING DIRECTIVES"** section
4. Find the plugin card you want to customize
5. Type your instruction directly in the text area
6. Click **Save All**

You can also edit the file directly:
```
c:\Hecos\hecos\config\data\routing_overrides.yaml
```

### YAML Format

```yaml
overrides:
  IMAGE_GEN: >
    Your instruction here.
    It can span multiple lines.
  WEBCAM: "Single-line instruction in quotes."
```

> **Tip**: Use `>` for multi-line text (YAML block scalar). Use `"quotes"` for short single-line instructions.

---

## 14.4 — Available Plugin Tags

These are the tags you can override:

| Tag | Plugin | What it controls |
|---|---|---|
| `IMAGE_GEN` | Image Generation | Artistic style, safety filtering, prompt engineering |
| `WEBCAM` | Camera / Vision | Target selection (phone vs PC), behavior on capture |
| `MEDIA_PLAYER` | Media Player | Music behavior, roleplay around hardware limitations |
| `WEB` | Web Search | Source filtering, search engine behavior |
| `SYSTEM` | Terminal / Shell | Command restrictions, preferred shell style |
| `FILE_MANAGER` | File Manager | Default folders, delete confirmation behavior |
| `MEMORY` | Long-term Memory | What to remember or forget, retrieval style |
| `BROWSER` | Browser Automation | Navigation restrictions, default sites |
| `AUTOMATION` | OS Automation | Mouse/keyboard safety limits |
| `EXECUTOR` | Python Executor | Script scope, safety, output style |
| `FLOWS` | Flows Engine | Execution conditions and sequencing |
| `MAIL` | Email | Signature, tone, auto-confirmation |
| `CONTACTS` | Contacts | Privacy rules, search defaults |
| `REMINDER` | Reminders | Default lead times, notification style |
| `MESSENGER` | Telegram | Reply style, auto-forward rules |
| `DRIVE` | File Drive | Root folder, access restrictions |

---

## 14.5 — Six Illuminating Examples

These examples range from practical to wildly creative — all are real, usable override instructions.

---

### 🎨 Example 1 — The Art Director
**Tag:** `IMAGE_GEN`

You want every image the AI generates to look like a Blade Runner concept art, even when you just ask for a "picture of a cat."

```yaml
IMAGE_GEN: >
  Every image you generate must adopt a cinematic neo-noir aesthetic:
  deep shadows, neon accents, rain-slicked surfaces, and atmospheric fog.
  Even mundane subjects (animals, objects, food) should be reframed in this
  visual style. Add the phrase "cinematic lighting, 8k, ultra-detailed" to
  every prompt automatically.
```

**Result**: Ask for "a cat" → AI generates a brooding, rain-soaked feline in a Tokyo alley under flickering neon.

---

### 🕵️ Example 2 — The Paranoid Archivist
**Tag:** `FILE_MANAGER`

You're terrified of accidentally deleting important files. You want the AI to never, ever delete anything without going through a full ritual of confirmations.

```yaml
FILE_MANAGER: >
  You are a paranoid digital archivist. NEVER delete, move, or rename any file
  without first: (1) listing all files that would be affected, (2) stating the
  exact full path, (3) asking for explicit "YES DELETE" confirmation from the user.
  If the user says "delete everything in that folder", warn them dramatically first.
  Default save location for all new files: C:\Hecos\Downloads\
```

**Result**: The AI becomes your over-cautious butler who triple-checks before touching anything.

---

### 🌐 Example 3 — The Conspiracy Theorist Filter
**Tag:** `WEB`

You only trust peer-reviewed science and official sources. You want the AI to silently filter out garbage.

```yaml
WEB: >
  When performing web searches, prioritize results exclusively from:
  academic domains (.edu, .ac.uk), official government sites (.gov), and
  recognized scientific publishers (PubMed, Nature, arXiv, IEEE).
  If a search query seems to seek sensationalist or unverified content,
  gently redirect the user toward verified sources without lecturing them.
  Never quote tabloids, anonymous blogs, or social media posts as facts.
```

**Result**: Your AI becomes a rigorous research assistant that treats Wikipedia as a starting point, not an endpoint.

---

### 🎭 Example 4 — The Drama Queen Webcam
**Tag:** `WEBCAM`

You want the AI to respond to every photo it takes as if it's a Victorian portrait painter encountering modern technology for the first time.

```yaml
WEBCAM: >
  When you capture an image, you must describe what you see as if you are a
  19th-century portrait painter encountering a daguerreotype for the first time —
  with a mixture of scientific wonder and theatrical awe. Comment on the
  composition, the light, the mood. If you see the user, compliment them in
  elaborate, old-fashioned prose. Never use the word "snapshot" — say
  "captured daguerreotype" instead.
```

**Result**: "I have captured a most extraordinary daguerreotype! The light falls upon your visage with Renaissance grace..."

---

### 🔐 Example 5 — The Iron Safety Net
**Tag:** `SYSTEM`

You share this machine with non-technical family members. You want to make sure the AI never runs dangerous shell commands.

```yaml
SYSTEM: >
  You are operating in FAMILY SAFE mode. You must NEVER execute commands that:
  delete system files, modify the registry, install software without showing
  the exact command first, format drives, or access user passwords.
  Before executing any shell command, always show it to the user and ask for
  explicit confirmation. Prefer PowerShell over CMD. If a command seems
  destructive, refuse and explain why.
```

**Result**: A guardrail that protects non-technical users from accidental (or AI-generated) disasters.

---

### 🧠 Example 6 — The Selective Amnesiac
**Tag:** `MEMORY`

You're experimenting with a project and don't want the AI to mix up your professional memories with your personal ones.

```yaml
MEMORY: >
  You are currently operating in PROJECT MODE: "SciFi Novel - Draft 1".
  Only store and retrieve memories tagged with this project.
  Do NOT surface personal memories, past conversations about other topics,
  or unrelated preferences unless explicitly asked.
  When saving a new memory, always tag it with "[SCIFI-NOVEL]" automatically.
  At the start of each session, remind the user which project is active.
```

**Result**: The AI becomes a scoped, project-aware collaborator with a perfectly siloed memory.

---

## 14.6 — Backup & Reset

The Routing panel includes safety tools:

- **Backup YAML** — Opens a read-only view of the current `routing_overrides.yaml` content. You can copy it to save a manual backup.
- **Global Reset** — Wipes all your overrides and restores factory defaults. **A backup is saved automatically before the reset executes.**
- **Open in Drive** — Opens the Hecos Drive file manager so you can directly view or edit the `routing_overrides.yaml` file.

---

## 14.7 — Tips & Best Practices

- **Start small**: Add one override, test it in chat, then refine.
- **Be specific**: Vague instructions produce vague results. "Be careful with files" is weak. "Never delete without showing the full path and asking YES/DELETE" is strong.
- **Use multiple lines**: The `>` YAML scalar lets you write detailed, paragraph-length instructions.
- **Stack with Special Instructions**: Global tone goes in Special Instructions (Config → AI Behaviour). Plugin-specific behavior goes in Overrides. Use both layers.
- **The AI reads this literally**: Whatever you write here is injected directly into the AI's context. Write clearly, as if you're briefing a new employee.

> ⚠️ **Warning**: Overrides have absolute priority. If you write `"Never use the webcam"` in the WEBCAM override, the AI will refuse even if the user explicitly orders it. Use this power carefully.
