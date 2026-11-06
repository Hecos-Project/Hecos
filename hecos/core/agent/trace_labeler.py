"""
hecos/core/agent/trace_labeler.py
─────────────────────────────────────────────────────────────────────────────
Automatic & Zero-Touch Tool Labeling Engine for AgentTracer.

Provides a 3-tier system for describing what Hecos is doing across any module
or HPM package without requiring manual edits to every package:
  1. Manifest "trace" template (optional declarative override in manifest.json)
  2. Built-in localized catalog + automatic manifest/registry introspection
  3. Smart argument preview & output outcome summarization
─────────────────────────────────────────────────────────────────────────────
"""

import os
import re
import json
from typing import Tuple, Dict, Any, Optional
from hecos.core.logging import logger

_HECOS_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))

# In-memory cache of package manifests keyed by uppercase tag
_MANIFEST_CACHE: Dict[str, dict] = {}
_MANIFEST_CACHE_LOADED = False

# Sensitive argument keys that must always be masked in UI traces
_SENSITIVE_KEY_RE = re.compile(
    r"(?:passw|secret|token|api_?key|auth|credential|private_?key|bearer)",
    re.IGNORECASE,
)

# Priority order for picking the most informative argument(s) to preview
_PRIORITY_ARG_KEYS = (
    "query",
    "search_query",
    "q",
    "prompt",
    "title",
    "list_name",
    "name",
    "items",
    "item",
    "filename",
    "file_path",
    "path",
    "directory_path",
    "url",
    "command",
    "cmd",
    "module_id",
    "city",
    "location",
    "date",
    "time",
    "event",
    "reminder",
    "target",
    "action",
    "text",
    "message",
)

# Module-level icons (FontAwesome 6 classes used in WebUI)
_MODULE_ICONS: Dict[str, str] = {
    "IMAGE_GEN": "fa-wand-magic-sparkles",
    "NETSEARCH": "fa-globe",
    "WEB_SEARCH": "fa-globe",
    "DOCS": "fa-file-lines",
    "DOCUMENT_MAKER": "fa-file-pdf",
    "DOCUMENT_READER": "fa-book-open",
    "LISTS": "fa-list-check",
    "CALENDAR": "fa-calendar-days",
    "REMINDER": "fa-bell",
    "EXECUTOR": "fa-terminal",
    "SYSTEM": "fa-terminal",
    "SANDBOX": "fa-code",
    "CORE": "fa-microchip",
    "DRIVE": "fa-folder-open",
    "RAG": "fa-database",
    "MEMORY": "fa-brain",
    "PC_AUTOMATION": "fa-desktop",
    "WEBCAM": "fa-camera",
    "WEBCAM_FEED": "fa-video",
    "VOICE_FORGE": "fa-microphone-lines",
    "PLAYBOOKS": "fa-diagram-project",
    "MESSENGER": "fa-comments",
    "REMOTE_ACCESS_PRO": "fa-network-wired",
    "WEATHER_PRO": "fa-cloud-sun",
    "MAP": "fa-map-location-dot",
    "SLASH_COMMAND": "fa-bolt",
    "DIRECT_COMMAND": "fa-bolt",
}

# Localized module display names (IT / EN)
_MODULE_NAMES: Dict[str, Dict[str, str]] = {
    "IMAGE_GEN": {"it": "Generazione Immagine", "en": "Image Generation"},
    "NETSEARCH": {"it": "Ricerca Web", "en": "Web Search"},
    "WEB_SEARCH": {"it": "Ricerca Web", "en": "Web Search"},
    "DOCS": {"it": "Creazione Documento", "en": "Document Maker"},
    "DOCUMENT_MAKER": {"it": "Creazione Documento", "en": "Document Maker"},
    "DOCUMENT_READER": {"it": "Lettura Documento", "en": "Document Reader"},
    "LISTS": {"it": "Gestione Liste", "en": "Lists Manager"},
    "CALENDAR": {"it": "Calendario", "en": "Calendar"},
    "REMINDER": {"it": "Promemoria", "en": "Reminder"},
    "EXECUTOR": {"it": "Esecutore Sistema", "en": "System Executor"},
    "SYSTEM": {"it": "Sistema", "en": "System"},
    "SANDBOX": {"it": "Sandbox Python", "en": "Python Sandbox"},
    "CORE": {"it": "Nucleo Hecos", "en": "Hecos Core"},
    "DRIVE": {"it": "Archivio File", "en": "File Drive"},
    "RAG": {"it": "Ricerca Conoscenza (RAG)", "en": "Knowledge Search (RAG)"},
    "MEMORY": {"it": "Memoria", "en": "Memory"},
    "PC_AUTOMATION": {"it": "Automazione PC", "en": "PC Automation"},
    "WEBCAM": {"it": "Fotocamera", "en": "Camera"},
    "WEBCAM_FEED": {"it": "Flusso Webcam", "en": "Webcam Feed"},
    "VOICE_FORGE": {"it": "Voice Forge", "en": "Voice Forge"},
    "PLAYBOOKS": {"it": "Playbooks", "en": "Playbooks"},
    "MESSENGER": {"it": "Messenger", "en": "Messenger"},
    "REMOTE_ACCESS_PRO": {"it": "Accesso Remoto", "en": "Remote Access"},
    "WEATHER_PRO": {"it": "Meteo", "en": "Weather"},
    "MAP": {"it": "Mappa", "en": "Map"},
    "SLASH_COMMAND": {"it": "Comando Diretto", "en": "Direct Command"},
    "DIRECT_COMMAND": {"it": "Comando Diretto", "en": "Direct Command"},
}

# Localized method labels (IT / EN) for common actions across packages
_METHOD_LABELS: Dict[str, Dict[str, str]] = {
    # Image Gen
    "generate_image": {"it": "Generazione immagine AI", "en": "Generating AI image"},
    "slash_img": {"it": "Generazione rapida immagine", "en": "Quick image generation"},
    # NetSearch
    "web_search": {"it": "Ricerca sul web", "en": "Searching the web"},
    "deep_search": {"it": "Ricerca approfondita", "en": "Deep web search"},
    "search_images": {"it": "Ricerca immagini sul web", "en": "Searching web images"},
    "search_videos": {"it": "Ricerca video sul web", "en": "Searching web videos"},
    "search_news": {"it": "Ricerca notizie", "en": "Searching news"},
    "fetch_page": {"it": "Lettura pagina web", "en": "Reading web page"},
    # Document Maker & Reader
    "generate_pdf": {"it": "Creazione documento PDF/HTML", "en": "Generating PDF/HTML document"},
    "generate_document": {"it": "Creazione documento", "en": "Generating document"},
    "create_document": {"it": "Creazione documento", "en": "Creating document"},
    "modify_document": {"it": "Modifica documento", "en": "Modifying document"},
    "read_document": {"it": "Lettura documento", "en": "Reading document"},
    "analyze_document": {"it": "Analisi documento", "en": "Analyzing document"},
    # Lists
    "create_list": {"it": "Creazione nuova lista", "en": "Creating new list"},
    "list_lists": {"it": "Lettura elenco liste", "en": "Listing active lists"},
    "show_list": {"it": "Apertura contenuto lista", "en": "Showing list items"},
    "add_to_list": {"it": "Aggiunta elementi alla lista", "en": "Adding items to list"},
    "check_item": {"it": "Completamento elemento lista", "en": "Checking off list item"},
    "uncheck_item": {"it": "Ripristino elemento lista", "en": "Unchecking list item"},
    "remove_from_list": {"it": "Rimozione elemento dalla lista", "en": "Removing item from list"},
    "clear_done": {"it": "Pulizia elementi completati", "en": "Clearing completed items"},
    "delete_list": {"it": "Eliminazione lista", "en": "Deleting list"},
    "archive_list": {"it": "Archiviazione lista", "en": "Archiving list"},
    # Calendar & Reminder
    "add_event": {"it": "Aggiunta evento in calendario", "en": "Adding calendar event"},
    "create_event": {"it": "Creazione evento in calendario", "en": "Creating calendar event"},
    "list_events": {"it": "Consultazione calendario", "en": "Checking calendar events"},
    "get_events": {"it": "Consultazione calendario", "en": "Checking calendar events"},
    "delete_event": {"it": "Rimozione evento dal calendario", "en": "Deleting calendar event"},
    "update_event": {"it": "Aggiornamento evento", "en": "Updating calendar event"},
    "add_reminder": {"it": "Impostazione promemoria", "en": "Setting reminder"},
    "set_reminder": {"it": "Impostazione promemoria", "en": "Setting reminder"},
    "create_reminder": {"it": "Impostazione promemoria", "en": "Setting reminder"},
    "list_reminders": {"it": "Controllo promemoria attivi", "en": "Checking active reminders"},
    "delete_reminder": {"it": "Cancellazione promemoria", "en": "Deleting reminder"},
    # Executor / Files / System
    "read_file": {"it": "Lettura file", "en": "Reading file"},
    "write_file": {"it": "Scrittura file", "en": "Writing file"},
    "patch_file": {"it": "Modifica file", "en": "Patching file"},
    "delete_file": {"it": "Eliminazione file", "en": "Deleting file"},
    "create_dir": {"it": "Creazione cartella", "en": "Creating directory"},
    "list_dir": {"it": "Esplorazione cartella", "en": "Listing directory"},
    "run_command": {"it": "Esecuzione comando di sistema", "en": "Running system command"},
    "execute_command": {"it": "Esecuzione comando di sistema", "en": "Running system command"},
    "execute_python": {"it": "Esecuzione script Python", "en": "Running Python script"},
    "open_media_file": {"it": "Apertura file multimediale", "en": "Opening media file"},
    "describe_module": {"it": "Ispezione scheda modulo", "en": "Inspecting module card"},
    "get_author": {"it": "Verifica identità autore", "en": "Checking author identity"},
    # Webcam
    "take_snapshot": {"it": "Acquisizione foto da webcam", "en": "Capturing webcam photo"},
    "capture": {"it": "Acquisizione foto da webcam", "en": "Capturing webcam photo"},
}


def get_lang() -> str:
    """Returns 'it' or 'en' based on active Hecos translator."""
    try:
        from hecos.core.i18n import translator
        lang = getattr(translator.get_translator(), "language", "it") or "it"
        return "it" if str(lang).lower().startswith("it") else "en"
    except Exception:
        return "it"


def tr(it_text: str, en_text: str) -> str:
    """Helper for quick bilingual core trace messages."""
    return it_text if get_lang() == "it" else en_text


def _ensure_manifest_cache() -> None:
    """Loads manifest metadata from hpm/, modules/, plugins/, and core/registry.json once."""
    global _MANIFEST_CACHE_LOADED
    if _MANIFEST_CACHE_LOADED:
        return
    _MANIFEST_CACHE_LOADED = True

    # 1. Load core/registry.json if present
    reg_path = os.path.join(_HECOS_ROOT, "core", "registry.json")
    if os.path.isfile(reg_path):
        try:
            with open(reg_path, "r", encoding="utf-8") as f:
                reg_data = json.load(f)
            if isinstance(reg_data, dict):
                for tag, info in reg_data.items():
                    if isinstance(info, dict):
                        _MANIFEST_CACHE[tag.upper()] = {
                            "tag": tag.upper(),
                            "name": info.get("name") or tag.replace("_", " ").title(),
                            "description": info.get("description", ""),
                            "commands": info.get("commands", {}),
                            "trace": info.get("trace", {}),
                        }
        except Exception as e:
            logger.debug(f"[TraceLabeler] Failed reading registry.json: {e}")

    # 2. Scan manifest.json files across hpm, modules, plugins
    for sub in ("hpm", "modules", "plugins"):
        base = os.path.join(_HECOS_ROOT, sub)
        if not os.path.isdir(base):
            continue
        try:
            for entry in os.listdir(base):
                m_path = os.path.join(base, entry, "manifest.json")
                if not os.path.isfile(m_path):
                    continue
                try:
                    with open(m_path, "r", encoding="utf-8") as f:
                        m = json.load(f)
                    if not isinstance(m, dict):
                        continue
                    tag = (m.get("tag") or entry).upper()
                    existing = _MANIFEST_CACHE.get(tag, {})
                    commands = dict(existing.get("commands") or {})
                    if isinstance(m.get("commands"), dict):
                        commands.update(m["commands"])
                    # Also extract descriptions from tool_schema if commands dict is sparse
                    if isinstance(m.get("tool_schema"), list):
                        for ts in m["tool_schema"]:
                            fn = ts.get("function") if isinstance(ts, dict) else None
                            if isinstance(fn, dict) and fn.get("name"):
                                fn_name = fn["name"]
                                m_name = fn_name.split("__", 1)[1] if "__" in fn_name else fn_name
                                if m_name not in commands and fn.get("description"):
                                    # Take first sentence of description
                                    first_sent = fn["description"].strip().split(".")[0].strip()
                                    if first_sent:
                                        commands[m_name] = first_sent
                    _MANIFEST_CACHE[tag] = {
                        "tag": tag,
                        "name": m.get("name") or existing.get("name") or entry.replace("_", " ").title(),
                        "description": m.get("description") or existing.get("description") or "",
                        "commands": commands,
                        "trace": m.get("trace") or existing.get("trace") or {},
                        "icon": m.get("icon") or existing.get("icon") or "",
                    }
                except Exception:
                    pass
        except Exception:
            pass


def _truncate(val: Any, max_len: int = 64) -> str:
    s = str(val).strip()
    s = re.sub(r"\s+", " ", s)
    if len(s) > max_len:
        return s[: max_len - 1].rstrip() + "…"
    return s


def format_args_preview(action_or_args: Any, max_len: int = 80) -> str:
    """
    Extracts a concise, privacy-safe human preview of tool arguments.
    Masks any secret/token/key fields automatically.
    """
    if action_or_args is None:
        return ""

    if isinstance(action_or_args, str):
        clean = action_or_args.strip()
        if not clean or clean == "{}":
            return ""
        # Try parsing if it looks like JSON
        if clean.startswith("{") and clean.endswith("}"):
            try:
                action_or_args = json.loads(clean)
            except Exception:
                return _truncate(clean, max_len)
        else:
            return _truncate(clean, max_len)

    if isinstance(action_or_args, dict):
        if not action_or_args:
            return ""
        parts = []
        used_keys = set()

        # First pick priority keys if present
        for pk in _PRIORITY_ARG_KEYS:
            if pk in action_or_args and action_or_args[pk] not in (None, "", [], {}):
                used_keys.add(pk)
                val = action_or_args[pk]
                if _SENSITIVE_KEY_RE.search(pk):
                    parts.append(f"{pk}=•••")
                elif isinstance(val, (list, tuple)):
                    joined = ", ".join(_truncate(x, 25) for x in val[:4])
                    if len(val) > 4:
                        joined += f" (+{len(val) - 4})"
                    parts.append(f"[{joined}]" if len(action_or_args) == 1 else f"{pk}: [{joined}]")
                elif pk in ("query", "search_query", "q", "prompt", "command", "cmd"):
                    parts.append(f"“{_truncate(val, 55)}”")
                elif pk in ("path", "file_path", "filename", "directory_path"):
                    bname = os.path.basename(str(val).rstrip("/\\")) or str(val)
                    parts.append(_truncate(bname, 45))
                else:
                    parts.append(
                        _truncate(val, 45)
                        if len(action_or_args) == 1
                        else f"{pk}: {_truncate(val, 35)}"
                    )
                if len(parts) >= 2:
                    break

        # Fallback to any remaining keys if none matched priority
        if not parts:
            for k, val in action_or_args.items():
                if k in used_keys or val in (None, "", [], {}):
                    continue
                if _SENSITIVE_KEY_RE.search(str(k)):
                    parts.append(f"{k}=•••")
                else:
                    parts.append(f"{k}: {_truncate(val, 35)}")
                if len(parts) >= 2:
                    break

        return _truncate(" · ".join(parts), max_len)

    return _truncate(action_or_args, max_len)


def describe_tool_call(
    tag: str,
    method_name: Optional[str] = None,
    action_or_args: Any = None,
    show_args: bool = True,
) -> Dict[str, str]:
    """
    Returns structured display metadata for a tool invocation:
      {
        "module_tag": "LISTS",
        "module_name": "Gestione Liste",
        "action_label": "Aggiunta elementi alla lista",
        "full_label": "Gestione Liste · Aggiunta elementi alla lista",
        "args_preview": "Spesa · [pane, latte]",
        "icon": "fa-list-check"
      }
    """
    _ensure_manifest_cache()
    lang = get_lang()
    raw_tag = (tag or "SYSTEM").upper().strip()

    # Handle direct_command / slash command nicely
    if raw_tag in ("DIRECT_COMMAND", "SLASH_COMMAND"):
        cmd_str = str(action_or_args or "").strip()
        cmd_verb = cmd_str.split()[0] if cmd_str else "/cmd"
        mod_name = _MODULE_NAMES["SLASH_COMMAND"][lang]
        act_label = tr(f"Esecuzione comando {cmd_verb}", f"Running command {cmd_verb}")
        args_prev = format_args_preview(cmd_str[len(cmd_verb):].strip(), 60) if show_args else ""
        return {
            "module_tag": "SLASH_COMMAND",
            "module_name": mod_name,
            "action_label": act_label,
            "full_label": f"{mod_name} · {act_label}",
            "args_preview": args_prev,
            "icon": "fa-bolt",
        }

    # Handle MCP_* tools
    if raw_tag.startswith("MCP_"):
        server_name = raw_tag[4:].replace("_", " ").title()
        mod_name = f"MCP ({server_name})"
        human_method = (method_name or "tool").replace("_", " ").title()
        args_prev = format_args_preview(action_or_args) if show_args else ""
        return {
            "module_tag": raw_tag,
            "module_name": mod_name,
            "action_label": human_method,
            "full_label": f"{mod_name} · {human_method}",
            "args_preview": args_prev,
            "icon": "fa-plug",
        }

    manifest_info = _MANIFEST_CACHE.get(raw_tag, {})
    icon = (
        manifest_info.get("icon")
        or _MODULE_ICONS.get(raw_tag)
        or "fa-puzzle-piece"
    )
    mod_name = (
        _MODULE_NAMES.get(raw_tag, {}).get(lang)
        or manifest_info.get("name")
        or raw_tag.replace("_", " ").title()
    )

    clean_method = (method_name or "").strip()

    # If method_name was not explicitly separated (e.g. legacy string "web_search(query=...)"), extract it
    if not clean_method and isinstance(action_or_args, str):
        m_call = re.match(r"^([a-zA-Z0-9_]+)\s*[\(:](.*)$", action_or_args.strip(), re.DOTALL)
        if m_call:
            clean_method = m_call.group(1).strip()
            action_or_args = m_call.group(2).strip().rstrip(")")

    # ── Tier 2: Check declarative "trace" template in manifest.json ──────────
    trace_templates = manifest_info.get("trace") or {}
    if clean_method and clean_method in trace_templates:
        tpl_entry = trace_templates[clean_method]
        tpl_str = None
        if isinstance(tpl_entry, str):
            tpl_str = tpl_entry
        elif isinstance(tpl_entry, dict):
            tpl_str = tpl_entry.get(lang) or tpl_entry.get("en") or tpl_entry.get("it")
            if tpl_entry.get("icon"):
                icon = tpl_entry["icon"]
        if tpl_str:
            try:
                if isinstance(action_or_args, dict):
                    safe_kwargs = {
                        k: ("•••" if _SENSITIVE_KEY_RE.search(str(k)) else _truncate(v, 40))
                        for k, v in action_or_args.items()
                    }
                    rendered = tpl_str.format(**safe_kwargs)
                else:
                    rendered = tpl_str
                return {
                    "module_tag": raw_tag,
                    "module_name": mod_name,
                    "action_label": rendered,
                    "full_label": f"{mod_name} · {rendered}",
                    "args_preview": "",
                    "icon": icon,
                }
            except Exception:
                pass

    # ── Tier 1: Built-in catalog -> Manifest command description -> Humanized method
    act_label = ""
    if clean_method:
        if clean_method in _METHOD_LABELS:
            act_label = _METHOD_LABELS[clean_method][lang]
        else:
            cmd_desc = (manifest_info.get("commands") or {}).get(clean_method, "")
            if cmd_desc and len(cmd_desc) <= 65:
                act_label = cmd_desc.rstrip(".")
            else:
                act_label = clean_method.replace("_", " ").capitalize()
    else:
        act_label = tr("Esecuzione modulo", "Running module")

    args_prev = format_args_preview(action_or_args) if show_args else ""
    full_label = f"{mod_name} · {act_label}" if act_label and act_label.lower() != mod_name.lower() else mod_name

    return {
        "module_tag": raw_tag,
        "module_name": mod_name,
        "action_label": act_label,
        "full_label": full_label,
        "args_preview": args_prev,
        "icon": icon,
    }


def summarize_tool_output(tag: str, method_name: Optional[str], output: Any) -> Tuple[str, str]:
    """
    Inspects the raw return value of a tool and returns:
      (status: "ok" | "error", result_preview: str)
    """
    out_str = str(output or "").strip()
    if not out_str:
        return "ok", tr("Completato", "Completed")

    # 1. Detect explicit error markers
    if (
        out_str.startswith("Error:")
        or out_str.startswith("❌")
        or "FATAL_BACKEND_ERROR" in out_str
        or "[IMAGE_GEN_ERROR]" in out_str
        or "[SYSTEM ERROR:" in out_str
        or "[[IGEN_ALERT]]" in out_str
    ):
        # Extract clean error summary
        clean_err = re.sub(r"\[\[/?IGEN_ALERT\]\]", "", out_str)
        clean_err = re.sub(r"\[SYSTEM:.*?\]", "", clean_err, flags=re.DOTALL).strip()
        first_line = next((l.strip() for l in clean_err.splitlines() if l.strip()), clean_err)
        return "error", _truncate(first_line, 85)

    # 2. Detect generated images [[IMG:...]]
    img_matches = re.findall(r"\[\[IMG:([^\]]+)\]\]", out_str)
    if img_matches:
        count = len(img_matches)
        if count == 1:
            fname = os.path.basename(img_matches[0].split("|")[0].strip())
            return "ok", tr(f"Immagine generata ({_truncate(fname, 36)})", f"Image generated ({_truncate(fname, 36)})")
        return "ok", tr(f"{count} immagini generate", f"{count} images generated")

    # 3. Detect search session tokens [[HSEARCH:...]] / [[HMEDIA:...]]
    if "[[HSEARCH:" in out_str or "[[HMEDIA:" in out_str:
        # Count result items if present in text
        url_count = len(re.findall(r"https?://", out_str))
        if url_count > 0:
            return "ok", tr(f"{url_count} fonti web trovate", f"{url_count} web sources found")
        return "ok", tr("Risultati di ricerca acquisiti", "Search results acquired")

    # 4. Detect generated PDF / HTML documents
    pdf_m = re.search(r"PDF:\s*([^\r\n]+)", out_str)
    html_m = re.search(r"HTML:\s*([^\r\n]+)", out_str)
    if pdf_m:
        bname = os.path.basename(pdf_m.group(1).strip())
        return "ok", tr(f"PDF creato: {bname}", f"PDF created: {bname}")
    if html_m:
        bname = os.path.basename(html_m.group(1).strip())
        return "ok", tr(f"Documento HTML creato: {bname}", f"HTML document created: {bname}")

    # 5. Detect camera snapshot request
    if "[CAMERA_SNAPSHOT_REQUEST]" in out_str:
        return "ok", tr("Richiesta fotocamera inviata al browser", "Camera request sent to browser")

    # 6. Generic clean 1-line summary
    clean_lines = [
        l.strip()
        for l in out_str.splitlines()
        if l.strip() and not l.strip().startswith("[[") and not l.strip().startswith("[SYSTEM")
    ]
    if clean_lines:
        return "ok", _truncate(clean_lines[0], 80)

    return "ok", tr("Completato", "Completed")

