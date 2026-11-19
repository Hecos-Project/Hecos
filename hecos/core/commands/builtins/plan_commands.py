"""
hecos/core/commands/builtins/plan_commands.py
Built-in HDCS slash commands for Action Plans (Architect -> Coder workflow) and fast coding execution:
  /plan [<task> | show | mode <mode> | approve | clear | run]
  /code [run | coder | --preset <id> | status | <direct coding instruction>]
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from hecos.core.action_plans import (
    PLAN_MODES,
    build_plan_markdown_document,
    get_action_plan_manager,
    get_action_plans_config,
    save_action_plans_config,
)


def _resolve_sid(session_id: Optional[str] = None) -> str:
    if session_id:
        return str(session_id)
    try:
        from hecos.core.privacy import privacy_manager
        sid = privacy_manager.get_session_id()
        if sid:
            return str(sid)
    except Exception:
        pass
    try:
        from hecos.memory.session_crud import get_sessions
        sessions = get_sessions()
        if sessions:
            return str(sessions[0].get("id") or "")
    except Exception:
        pass
    return "default"


def format_plan_markdown(plan: Optional[Dict[str, Any]], cfg: Optional[Dict[str, Any]] = None) -> str:
    """Format an Action Plan dict as rich Markdown for chat display."""
    ap_cfg = cfg or get_action_plans_config()
    mode_label = str(ap_cfg.get("plan_mode") or "auto").upper()

    if not plan:
        return (
            f"## 📋 Action Plans — Status (`mode: {mode_label}`)\n\n"
            "No active Action Plan for this chat session.\n\n"
            "### 💡 Quick Commands\n"
            "- `/plan <request>` — **Architect Mode (Plan First)**: analyze & generate a rich Implementation Plan without writing code yet\n"
            "- `/plan revise <changes>` — **Revise Plan**: refine the active Implementation Plan based on your feedback\n"
            "- `/code` *(or `/code run`)* — **Execute Plan**: run the active Action Plan step-by-step with the current model\n"
            "- `/code coder` *(or `/coder`)* — **Switch to Coder & Execute**: activate the Coder preset and execute the active plan\n"
            "- `/code <instruction>` — **Fast-Track Code**: execute a coding instruction immediately without stopping for a plan\n"
            "- `/plan mode <auto|confirm|plan_only|manual|off>` — Change default planning mode\n"
            "- `/plan clear` — Cancel/clear the active plan"
        )

    steps = plan.get("steps") or []
    done_cnt = sum(1 for s in steps if s.get("status") in ("done", "skipped"))
    total_cnt = len(steps)
    pct = int(round((done_cnt / total_cnt) * 100)) if total_cnt else 0
    st = str(plan.get("status") or "running").upper()
    rev = int(plan.get("revision") or 1)

    lines = [
        f"## 📋 {plan.get('title', 'Action Plan')} *(v{rev})*",
        f"**ID:** `{plan.get('plan_id')}` · **Status:** `{st}` · **Progress:** `{done_cnt}/{total_cnt} ({pct}%)` · **Default Mode:** `{mode_label}`\n",
    ]

    if str(plan.get("plan_markdown") or "").strip() or str(plan.get("goal") or "").strip():
        lines.append(build_plan_markdown_document(plan, include_step_checklist=True))
    else:
        icons = {
            "done": "✅",
            "running": "🔄",
            "failed": "❌",
            "skipped": "⏭️",
            "pending": "⬜",
        }
        for s in steps:
            ic = icons.get(str(s.get("status") or "pending").lower(), "⬜")
            files_txt = (" — " + ", ".join(f"`{f}`" for f in s["files"][:4])) if s.get("files") else ""
            note = f" — *{s['notes']}*" if s.get("notes") else ""
            lines.append(f"{ic} **Step {s.get('index')}:** {s.get('title')}{files_txt}{note}")

    if plan.get("status") in ("awaiting_approval", "draft", "paused", "interrupted"):
        lines.append(
            "\n---\n"
            "💡 **Ready to review:** Use **✏️ Revise** (or `/plan revise <changes>`) to update the blueprint, "
            "or click **▶️ Execute Plan** / **⚡ Run with Coder** (or `/code` / `/code coder`) to start implementation."
        )
    return "\n".join(lines)


def _cmd_plan(
    raw_args_str: str = "",
    config=None,
    config_manager=None,
    session_id: Optional[str] = None,
    **kwargs,
) -> str:
    """Direct handler for `/plan` management subcommands (show, mode, approve, clear)."""
    sid = _resolve_sid(session_id)
    mgr = get_action_plan_manager()
    ap_cfg = get_action_plans_config(cfg_mgr=config_manager, raw_config=config)

    args = (raw_args_str or "").strip()
    if not args:
        active = mgr.resolve_plan(source_id=sid)
        return format_plan_markdown(active, ap_cfg)

    parts = args.split(maxsplit=1)
    sub = parts[0].lower()
    rest = parts[1].strip() if len(parts) > 1 else ""

    if sub in ("show", "status", "list", "info", "help"):
        active = mgr.resolve_plan(source_id=sid)
        return format_plan_markdown(active, ap_cfg)

    if sub == "mode":
        target = rest.lower().strip().replace("-", "_")
        aliases = {
            "plan": "plan_only",
            "planonly": "plan_only",
            "architect": "plan_only",
            "arch": "plan_only",
            "ask": "confirm",
            "disable": "off",
            "disabled": "off",
        }
        target = aliases.get(target, target)
        if not target:
            cur = ap_cfg.get("plan_mode", "auto")
            return (
                f"📋 **Current Action Plan Mode:** `{cur}`\n\n"
                "**Available modes:**\n"
                "- `/plan mode auto` — Automatic checklist on multi-step tasks\n"
                "- `/plan mode plan_only` — **Architect Mode**: always generate the plan first and stop before coding\n"
                "- `/plan mode confirm` — Pause for user approval before executing\n"
                "- `/plan mode manual` — Only create plans when explicitly requested\n"
                "- `/plan mode off` — Disable LLM plan generation"
            )
        if target not in PLAN_MODES:
            return f"❌ Invalid mode `{rest}`. Choose one of: `auto`, `plan_only`, `confirm`, `manual`, `off`."
        saved = save_action_plans_config({"plan_mode": target}, cfg_mgr=config_manager)
        if isinstance(config, dict):
            config.setdefault("plugins", {}).setdefault("ACTION_PLANS", {})["plan_mode"] = saved["plan_mode"]
        mode_descriptions = {
            "auto": "Automatic on complex multi-step tasks.",
            "plan_only": "**Architect Mode (Plan First)** — generates the plan and stops so you can review or switch to a Coder model.",
            "confirm": "Requests user confirmation before executing plan steps.",
            "manual": "Only creates plans when explicitly requested (`/plan <task>`).",
            "off": "Disabled for automatic LLM calls.",
        }
        return (
            f"✅ **Action Plan Mode updated to:** `{saved['plan_mode']}`\n\n"
            f"{mode_descriptions.get(saved['plan_mode'], '')}"
        )

    if sub in ("clear", "cancel", "reject", "reset", "close"):
        active = mgr.resolve_plan(source_id=sid)
        if not active or active.get("status") in ("completed", "cancelled"):
            return "ℹ️ No active Action Plan to clear in this session."
        mgr.reject_plan(active["plan_id"], reason=rest or "Cleared via /plan clear")
        return f"🗑️ Action Plan **`{active.get('title')}`** (`{active.get('plan_id')}`) cancelled and cleared."

    if sub in ("approve", "accept", "ok"):
        active = mgr.resolve_plan(source_id=sid)
        if not active:
            return "⚠️ No active Action Plan found to approve in this session."
        res = mgr.approve_plan(active["plan_id"])
        updated = res.get("plan") or mgr.get_plan(plan_id=active["plan_id"]) or active
        return (
            f"✅ Action Plan **`{updated.get('title')}`** approved!\n\n"
            "Type `/code` (or `/code coder` to switch to Hecos Coder) or click **▶️ Execute Plan** to run the steps."
        )

    # Fallback when called outside AgentExecutor (e.g. REST /api/commands/run)
    plan = mgr.ensure_fallback_plan_from_text(
        user_text=args,
        assistant_text="",
        source_id=sid,
    )
    return format_plan_markdown(plan, ap_cfg)


def _cmd_code(
    raw_args_str: str = "",
    config=None,
    config_manager=None,
    session_id: Optional[str] = None,
    **kwargs,
) -> str:
    """Direct handler for `/code` status/help or fallback when invoked outside AgentExecutor."""
    sid = _resolve_sid(session_id)
    mgr = get_action_plan_manager()
    active_plan = mgr.resolve_plan(source_id=sid)

    try:
        from hecos.core.global_presets import get_active_soul_id, list_souls
        active_preset = get_active_soul_id(sid) or "system default"
        coder_presets = [
            f"`{s.meta.id}` ({s.meta.name} — `{s.model.model_name or 'default model'}`)"
            for s in list_souls()
            if "coder" in str(s.meta.id).lower() or "coding" in [str(t).lower() for t in (s.meta.tags or [])]
        ]
    except Exception:
        active_preset = "unknown"
        coder_presets = ["`hecos_coder`"]

    presets_md = "\n".join(f"  - {p}" for p in coder_presets) if coder_presets else "  - `hecos_coder`"

    if active_plan and active_plan.get("status") not in ("completed", "cancelled"):
        plan_line = (
            f"📋 **Active Plan Ready:** `{active_plan.get('title')}` (`{active_plan.get('plan_id')}`, status=`{active_plan.get('status')}`)\n\n"
            "👉 Send `/code` or `/code coder` directly in the chat input to execute it step-by-step!"
        )
    else:
        plan_line = "ℹ️ **No active Action Plan** in this chat session. Use `/plan <request>` (or the **📋 Plan First** button) to create one first, or `/code <instruction>` to code immediately."

    return (
        f"## 💻 Hecos Coder — Quick Execution Control\n\n"
        f"**Active Session Preset:** `{active_preset}`\n"
        f"**Available Coder Presets:**\n{presets_md}\n\n"
        f"{plan_line}\n\n"
        "### ⚡ Usage in Chat\n"
        "- `/code` *(or `/code run`)* — Execute the active Action Plan with the current model\n"
        "- `/code coder` *(or `/coder`)* — Switch session to **Hecos Coder** and execute the active plan\n"
        "- `/code --preset <preset_id>` — Switch to a specific preset (e.g. `/code --preset hecos_coder_pro`) and execute\n"
        "- `/code <instruction>` — Execute a coding task immediately in Fast-Track mode (skips planning)"
    )


PLAN_COMMANDS: List[Dict[str, Any]] = [
    {
        "id": "plan",
        "aliases": ["/plan", "/piano"],
        "description": "Architect Mode: create a rich Implementation Plan without writing code yet, or manage/revise plans (/plan revise, /plan show, /plan mode, /plan clear)",
        "usage": "/plan <task | revise <changes> | show | mode | clear>",
        "example": "/plan Build a Flask expense tracker with SQLite and unit tests",
        "icon": "📋",
        "category": "CORE",
        "requires_auth": "any",
        "requires_args": True,
        "save_to_memory": False,
        "_handler": _cmd_plan,
    },
    {
        "id": "plan_revise",
        "aliases": ["/plan revise", "/plan edit", "/piano modifica"],
        "description": "Revise the active Implementation Plan in Architect Mode without editing code files yet",
        "usage": "/plan revise <requested changes>",
        "example": "/plan revise Add Chart.js spending breakdown and CSV import",
        "icon": "✏️",
        "category": "CORE",
        "requires_auth": "any",
        "requires_args": True,
        "save_to_memory": False,
        "_handler": lambda raw_args_str="", **kw: _cmd_plan(f"show", **kw),
    },
    {
        "id": "plan_show",
        "aliases": ["/plan show", "/plan status", "/plan list"],
        "description": "Show the active Action Plan checklist and progress in this chat",
        "usage": "/plan show",
        "example": "/plan show",
        "icon": "📊",
        "category": "CORE",
        "requires_auth": "any",
        "requires_args": False,
        "save_to_memory": False,
        "_handler": lambda raw_args_str="", **kw: _cmd_plan("show", **kw),
    },
    {
        "id": "plan_mode",
        "aliases": ["/plan mode"],
        "description": "Switch Action Plan mode (auto, plan_only, confirm, manual, off)",
        "usage": "/plan mode <auto|plan_only|confirm|manual|off>",
        "example": "/plan mode plan_only",
        "icon": "🎚️",
        "category": "CORE",
        "requires_auth": "any",
        "requires_args": True,
        "save_to_memory": False,
        "_handler": lambda raw_args_str="", **kw: _cmd_plan(f"mode {raw_args_str}".strip(), **kw),
    },
    {
        "id": "plan_clear",
        "aliases": ["/plan clear", "/plan cancel"],
        "description": "Cancel and clear the active Action Plan for this chat session",
        "usage": "/plan clear",
        "example": "/plan clear",
        "icon": "🗑️",
        "category": "CORE",
        "requires_auth": "any",
        "requires_args": False,
        "save_to_memory": False,
        "_handler": lambda raw_args_str="", **kw: _cmd_plan("clear", **kw),
    },
    {
        "id": "code",
        "aliases": ["/code", "/coder", "/sviluppa"],
        "description": "Execute the active Action Plan step-by-step (or run a fast-track coding instruction)",
        "usage": "/code [run | coder | --preset <id> | <instruction>]",
        "example": "/code coder",
        "icon": "💻",
        "category": "CORE",
        "requires_auth": "any",
        "requires_args": False,
        "save_to_memory": False,
        "_handler": _cmd_code,
    },
]
