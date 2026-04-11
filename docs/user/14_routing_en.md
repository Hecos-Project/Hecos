# 🧭 14. AI Instruction Routing (3-Tier)

Advanced hybrid architecture for controlling plugin behavior.

| Level | Where | Scope | Purpose |
|---|---|---|---|
| **1. Special Instructions** | Config → Personality | Global | Style and tone |
| **2. Routing Overrides** | Config → Routing | Per-plugin | Force specific tool constraints |
| **3. Plugin Manifest** | `registry.json` | Default | Factory settings |

> **Note**: Level 2 (YAML) has total priority over other levels.
