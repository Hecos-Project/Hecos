"""
Isolated sidecar bridge for invoking Aider CLI (`aider-chat`) without polluting
Hecos's main Python environment (aider-chat pins older litellm/pydantic/scipy versions).
Supports:
- Isolated venv at <repo>/tools/aider_env (or global `aider` on PATH)
- uv-based bootstrap & external update (`install_or_update_aider`)
- Isolated Git root initialization inside workspace projects
- Dynamic Ollama `num_ctx` model settings generation (preventing 2048-token truncation)
- Real-time stdout streaming into Hecos AgentTracer (WebUI) and logger (CLI)
- Post-run syntax/web checks and verified `| URI: file:///...` output for chat cards
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

from .code_intel import resolve_python_tool_binary
from .dev_tools import check_syntax_tool, inspect_web_project_issues
from .file_manager import AgentTracer, _is_safe_path
from .git_tools import _resolve_repo_root, _run_git

try:
    from hecos.core.logging import logger
except ImportError:
    logger = logging.getLogger(__name__)

_KNOWN_LITELLM_PREFIXES = (
    "ollama_chat/",
    "ollama/",
    "openai/",
    "anthropic/",
    "gemini/",
    "vertex_ai/",
    "openrouter/",
    "groq/",
    "deepseek/",
    "azure/",
    "bedrock/",
    "mistral/",
    "cohere/",
    "xai/",
    "together_ai/",
    "fireworks_ai/",
    "perplexity/",
)

_VERIFY_EXTS = frozenset({
    ".py", ".json", ".yaml", ".yml", ".js", ".mjs", ".cjs",
    ".ts", ".tsx", ".jsx", ".css", ".html", ".htm",
})


def _hecos_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def resolve_aider_command() -> Optional[List[str]]:
    """
    Locate an isolated Aider launcher command without relying on python_env packages.
    Priority:
      1. <repo>/tools/aider_env/(Scripts|bin)/aider(.exe)
      2. `aider` on PATH
    """
    root = _hecos_root()
    candidates = (
        os.path.join(root, "tools", "aider_env", "Scripts", "aider.exe"),
        os.path.join(root, "tools", "aider_env", "Scripts", "aider"),
        os.path.join(root, "tools", "aider_env", "bin", "aider"),
    )
    for cand in candidates:
        if os.path.isfile(cand):
            return [cand]
    global_aider = shutil.which("aider")
    if global_aider:
        return [global_aider]
    return None


def _read_executor_cfg(key: str, default: Any) -> Any:
    try:
        cfg_mgr = getattr(sys, "hecos_config_manager", None)
        if cfg_mgr:
            return cfg_mgr.get_plugin_config("EXECUTOR", key, default)
    except Exception:
        pass
    return default


def normalize_aider_model(model_name: str, backend_type: str = "ollama") -> str:
    """
    Normalize a model name for LiteLLM inside Aider.
    Crucial on Ollama where community tags include slashes (e.g. `huihui_ai/qwen2.5-coder:14b`):
    checks known LiteLLM provider prefixes rather than `\"/\" not in name`.
    """
    clean = str(model_name or "").strip()
    if not clean:
        return ""
    low = clean.lower()
    if low.startswith(_KNOWN_LITELLM_PREFIXES):
        return clean

    btype = str(backend_type or "ollama").strip().lower()
    if btype in ("ollama", "local", ""):
        return f"ollama_chat/{clean}"
    if btype == "cloud":
        if "/" in clean:
            return clean
        if low.startswith(("claude-",)):
            return f"anthropic/{clean}"
        if low.startswith(("gemini-",)):
            return f"gemini/{clean}"
        if low.startswith(("deepseek-",)):
            return f"deepseek/{clean}"
        if low.startswith(("gpt-", "o1", "o3", "o4", "chatgpt-")):
            return f"openai/{clean}"
        return clean
    if btype == "openai":
        return f"openai/{clean}"
    if btype == "anthropic":
        return f"anthropic/{clean}"
    if btype in ("gemini", "google"):
        return f"gemini/{clean}"
    if btype == "openrouter":
        return f"openrouter/{clean}"
    return f"{btype}/{clean}"


def _read_global_preset_defaults(preset_id: str) -> Tuple[str, str, Optional[int]]:
    """Read (backend_type, model_name, num_ctx) for a configured Global Preset ID."""
    clean_id = str(preset_id or "").strip()
    if not clean_id:
        return "", "", None

    try:
        from hecos.core.global_presets import get_soul

        soul = get_soul(clean_id)
        if soul is not None:
            b_type = str(getattr(soul.model, "backend_type", "") or "").strip()
            m_name = str(getattr(soul.model, "model_name", "") or "").strip()
            raw_ctx = getattr(soul.inference, "num_ctx", None)
            ctx_val = int(raw_ctx) if raw_ctx else None
            return b_type, m_name, ctx_val
    except Exception:
        pass

    preset_path = os.path.join(
        _hecos_root(), "hecos", "config", "data", "global_presets", f"{clean_id}.global_preset.yaml"
    )
    if not os.path.isfile(preset_path):
        return "", "", None
    try:
        with open(preset_path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        m_cfg = data.get("model") or {}
        b_type = str(m_cfg.get("backend_type") or "").strip()
        m_name = str(m_cfg.get("model_name") or "").strip()
        raw_ctx = (data.get("inference") or {}).get("num_ctx")
        ctx_val = int(raw_ctx) if raw_ctx else None
        return b_type, m_name, ctx_val
    except Exception:
        return "", "", None


def resolve_aider_runtime_settings(explicit_model: str = "") -> Dict[str, Any]:
    """
    Resolve effective LiteLLM model, Ollama URL, API keys, num_ctx, edit_format, and auto_lint
    from explicit argument -> EXECUTOR.aider_model -> EXECUTOR.aider_global_preset -> active Hecos model.
    """
    active_model = ""
    backend_type = "ollama"
    ollama_base = "http://127.0.0.1:11434"
    active_ctx: Optional[int] = None
    env_keys: Dict[str, str] = {}

    try:
        from hecos.config.config import Config

        cfg = Config().config or {}
        model_cfg = cfg.get("model", {}) if isinstance(cfg.get("model"), dict) else {}
        ai_cfg = cfg.get("ai", {}) if isinstance(cfg.get("ai"), dict) else {}
        backend_cfg = cfg.get("backend", {}) if isinstance(cfg.get("backend"), dict) else {}

        backend_type = str(
            model_cfg.get("backend_type")
            or backend_cfg.get("type")
            or "ollama"
        ).strip().lower()
        active_model = str(
            model_cfg.get("model_name")
            or (backend_cfg.get(backend_type, {}) or {}).get("model")
            or ai_cfg.get("ollama_model")
            or ""
        ).strip()
        ollama_base = str(
            model_cfg.get("ollama_url")
            or model_cfg.get("base_url")
            or (backend_cfg.get("ollama", {}) or {}).get("url")
            or ai_cfg.get("ollama_url")
            or "http://127.0.0.1:11434"
        ).strip()
        raw_ctx = (cfg.get("inference", {}) or {}).get("num_ctx") or model_cfg.get("num_ctx")
        if raw_ctx:
            try:
                active_ctx = int(raw_ctx)
            except (TypeError, ValueError):
                pass

        cloud_cfg = backend_cfg.get("cloud", {}) if isinstance(backend_cfg.get("cloud"), dict) else {}
        for env_key, cfg_paths in (
            ("OPENAI_API_KEY", ((backend_cfg.get("openai") or {}).get("api_key"), cloud_cfg.get("openai_api_key"))),
            ("ANTHROPIC_API_KEY", ((backend_cfg.get("anthropic") or {}).get("api_key"), cloud_cfg.get("anthropic_api_key"))),
            ("GEMINI_API_KEY", ((backend_cfg.get("gemini") or {}).get("api_key"), cloud_cfg.get("gemini_api_key"), cloud_cfg.get("api_key"))),
            ("OPENROUTER_API_KEY", ((backend_cfg.get("openrouter") or {}).get("api_key"), cloud_cfg.get("openrouter_api_key"))),
        ):
            for val in cfg_paths:
                if val and str(val).strip() and not os.environ.get(env_key):
                    env_keys[env_key] = str(val).strip()
    except Exception:
        pass

    raw_gp_id = _read_executor_cfg("aider_global_preset", "hecos_coder")
    gp_id = str("" if raw_gp_id is None else raw_gp_id).strip()
    gp_backend, gp_model, gp_ctx = _read_global_preset_defaults(gp_id)
    cfg_aider_model = str(_read_executor_cfg("aider_model", "") or "").strip()

    chosen_backend = backend_type
    if (explicit_model or "").strip():
        raw_choice = explicit_model.strip()
    elif cfg_aider_model:
        raw_choice = cfg_aider_model
        if cfg_aider_model.lower().startswith(("gemini/", "openai/", "anthropic/", "openrouter/", "deepseek/")):
            chosen_backend = "cloud"
    elif gp_model:
        raw_choice = gp_model
        if gp_backend:
            chosen_backend = gp_backend.lower()
    else:
        # When an interactive persona (e.g. Urania) uses a non-coder Ollama model and GP is cleared,
        # prefer Hecos_Coder fallback only if active model is missing.
        raw_choice = active_model or "qwen2.5-coder:14b"

    normalized_model = normalize_aider_model(raw_choice, backend_type=chosen_backend)

    raw_cfg_ctx = _read_executor_cfg("aider_num_ctx", 0)
    try:
        cfg_ctx_int = int(raw_cfg_ctx or 0)
    except (TypeError, ValueError):
        cfg_ctx_int = 0

    try:
        num_ctx = max(2048, cfg_ctx_int if cfg_ctx_int > 0 else int(gp_ctx or active_ctx or 16384))
    except (TypeError, ValueError):
        num_ctx = 16384

    edit_format = str(_read_executor_cfg("aider_edit_format", "") or "").strip()
    auto_lint = bool(_read_executor_cfg("aider_auto_lint", True))
    enabled = bool(_read_executor_cfg("aider_enabled", True))

    return {
        "enabled": enabled,
        "global_preset": gp_id,
        "model": normalized_model,
        "backend_type": chosen_backend,
        "ollama_base": ollama_base,
        "num_ctx": num_ctx,
        "edit_format": edit_format,
        "auto_lint": auto_lint,
        "env_keys": env_keys,
    }


def _probe_aider_version(cmd: Optional[List[str]]) -> Optional[str]:
    if not cmd:
        return None
    try:
        proc = subprocess.run(
            [*cmd, "--version"],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=10,
        )
        if proc.returncode == 0:
            line = (proc.stdout or proc.stderr or "").strip().splitlines()
            return line[0].strip() if line else "installed"
    except Exception:
        pass
    return None


def get_aider_status(check_version: bool = False) -> Dict[str, Any]:
    """Inspect whether isolated Aider execution is ready or can be bootstrapped/updated via uv."""
    cmd = resolve_aider_command()
    uv_bin = resolve_python_tool_binary("uv")
    install_target = os.path.join(_hecos_root(), "tools", "aider_env")
    runtime = resolve_aider_runtime_settings()
    version = _probe_aider_version(cmd) if check_version and cmd else None
    return {
        "installed": cmd is not None,
        "enabled": runtime["enabled"],
        "version": version,
        "command": cmd,
        "install_dir": install_target,
        "uv_available": uv_bin is not None,
        "uv_binary": uv_bin,
        "global_preset": runtime.get("global_preset", ""),
        "model": runtime["model"],
        "num_ctx": runtime["num_ctx"],
        "ollama_base": runtime["ollama_base"],
        "recommended_setup": (
            f'"{uv_bin or "uv"}" venv "{install_target}" --python 3.11 && '
            f'"{uv_bin or "uv"}" pip install --python "{install_target}" -U aider-chat'
        ),
    }


def install_or_update_aider(timeout_seconds: int = 300) -> Dict[str, Any]:
    """Create (if missing) and update the isolated tools/aider_env environment via uv."""
    uv_bin = resolve_python_tool_binary("uv")
    if not uv_bin:
        return {"ok": False, "error": "'uv' executable was not found in python_env or PATH."}

    root = _hecos_root()
    env_dir = os.path.join(root, "tools", "aider_env")
    os.makedirs(os.path.dirname(env_dir), exist_ok=True)
    py_in_env = (
        os.path.join(env_dir, "Scripts", "python.exe")
        if os.name == "nt"
        else os.path.join(env_dir, "bin", "python")
    )

    try:
        if not os.path.isfile(py_in_env):
            r_venv = subprocess.run(
                [uv_bin, "venv", env_dir, "--python", sys.executable],
                cwd=root,
                capture_output=True,
                text=True,
                errors="replace",
                timeout=60,
            )
            if r_venv.returncode != 0:
                return {"ok": False, "error": f"Failed creating aider_env: {(r_venv.stderr or r_venv.stdout).strip()}"}

        r_pip = subprocess.run(
            [uv_bin, "pip", "install", "--python", py_in_env, "-U", "aider-chat"],
            cwd=root,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=max(60, int(timeout_seconds)),
        )
        if r_pip.returncode != 0:
            err = (r_pip.stderr or r_pip.stdout or "").strip()[-1500:]
            return {"ok": False, "error": f"uv pip install aider-chat failed: {err}"}

        st = get_aider_status(check_version=True)
        return {
            "ok": st["installed"],
            "status": st,
            "message": f"Isolated Aider ready ({st.get('version') or 'installed'}) in {env_dir}.",
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _snapshot_git_dirty_state(repo_root: str) -> Dict[str, str]:
    """Capture a lightweight snapshot of modified/untracked files before running Aider."""
    rc, out, _ = _run_git(repo_root, ["status", "--porcelain", "-uall"])
    state: Dict[str, str] = {}
    if rc != 0 or not out:
        return state
    for line in out.splitlines():
        if len(line) < 4:
            continue
        status_code = line[:2]
        raw_path = line[3:].strip().strip('"')
        if " -> " in raw_path:
            raw_path = raw_path.split(" -> ", 1)[1].strip().strip('"')
        abs_file = os.path.abspath(os.path.join(repo_root, raw_path))
        try:
            mtime = str(os.path.getmtime(abs_file)) if os.path.exists(abs_file) else ""
        except OSError:
            mtime = ""
        state[raw_path] = f"{status_code}:{mtime}"
    return state


def _collect_touched_files(
    repo_root: str,
    before_state: Dict[str, str],
    explicit_files: List[str],
) -> List[str]:
    """Return absolute paths of files created or modified by the Aider run."""
    after_state = _snapshot_git_dirty_state(repo_root)
    touched: List[str] = []
    seen: Set[str] = set()

    for rel_path, sig in after_state.items():
        if rel_path.startswith(".aider"):
            continue
        if rel_path not in before_state or before_state[rel_path] != sig:
            abs_p = os.path.abspath(os.path.join(repo_root, rel_path))
            if os.path.isfile(abs_p) and abs_p.lower() not in seen:
                seen.add(abs_p.lower())
                touched.append(abs_p)

    # Also include recently changed files inside HEAD diff if auto-committed or unchanged status markers
    if not touched:
        for cand in explicit_files:
            if os.path.isfile(cand) and cand.lower() not in seen:
                seen.add(cand.lower())
                touched.append(cand)

    return touched


def _write_temp_model_settings(model_name: str, num_ctx: int, edit_format: str) -> str:
    entry: Dict[str, Any] = {
        "name": model_name,
        "use_repo_map": True,
        "extra_params": {"num_ctx": int(num_ctx)},
    }
    if edit_format:
        entry["edit_format"] = edit_format
    fd, tmp_yml = tempfile.mkstemp(prefix="hecos_aider_models_", suffix=".yml")
    os.close(fd)
    with open(tmp_yml, "w", encoding="utf-8") as fh:
        yaml.safe_dump([entry], fh, sort_keys=False)
    return tmp_yml


def _spawn_aider_process(cmd: List[str], cwd: str, env: Dict[str, str]):
    popen_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    return subprocess.Popen(
        cmd,
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        creationflags=popen_flags,
    )


def run_aider_task_tool(
    repo_path: str,
    instruction: str,
    files: str = "",
    model: str = "",
    timeout_seconds: int = 180,
) -> str:
    """
    Delegate a multi-file coding edit/creation task to isolated Aider CLI.
    Automatically initializes isolated project Git, passes Ollama `num_ctx` settings,
    streams progress to Hecos AgentTracer, verifies syntax/HTML assets, and returns
    verified `| URI: file:///...` links so chat cards render automatically.
    """
    abs_target = os.path.abspath(repo_path or ".")
    if not _is_safe_path(abs_target):
        return "[EXECUTOR] ACCESS DENIED: Protected repository path."
    if not instruction or not str(instruction).strip():
        return "[EXECUTOR] Aider instruction cannot be empty."

    if not os.path.exists(abs_target):
        try:
            os.makedirs(abs_target, exist_ok=True)
        except OSError as exc:
            return f"[EXECUTOR] Could not create target directory {abs_target}: {exc}"

    runtime = resolve_aider_runtime_settings(explicit_model=model)
    if not runtime["enabled"]:
        return "[EXECUTOR] Aider sidecar delegation is disabled in EXECUTOR plugin settings."

    base_cmd = resolve_aider_command()
    if base_cmd is None:
        status = get_aider_status()
        return (
            "[EXECUTOR] Isolated Aider CLI is not installed yet.\n"
            f"Install Aider in tools/aider_env with:\n  {status['recommended_setup']}"
        )

    repo_root, repo_err = _resolve_repo_root(abs_target, auto_init=True)
    if repo_err or not repo_root:
        return repo_err or f"[EXECUTOR] Failed to prepare Git repository at {abs_target}."

    before_state = _snapshot_git_dirty_state(repo_root)
    explicit_file_paths: List[str] = []
    if files and str(files).strip():
        for raw_file in str(files).split(","):
            f_clean = raw_file.strip()
            if not f_clean:
                continue
            cand = os.path.abspath(f_clean if os.path.isabs(f_clean) else os.path.join(repo_root, f_clean))
            if not _is_safe_path(cand):
                return f"[EXECUTOR] ACCESS DENIED: Unsafe file argument '{f_clean}'."
            explicit_file_paths.append(cand)

    chosen_model = runtime["model"]
    tmp_settings = _write_temp_model_settings(chosen_model, runtime["num_ctx"], runtime["edit_format"])
    tmp_hist_dir = tempfile.mkdtemp(prefix="hecos_aider_hist_")
    input_hist = os.path.join(tmp_hist_dir, "input.history")
    chat_hist = os.path.join(tmp_hist_dir, "chat.history.md")

    cmd: List[str] = [
        *base_cmd,
        "--yes-always",
        "--no-auto-commits",
        "--no-pretty",
        "--no-stream",
        "--no-analytics",
        "--no-check-update",
        "--no-restore-chat-history",
        "--no-gitignore",
        "--no-suggest-shell-commands",
        "--disable-playwright",
        "--encoding", "utf-8",
        "--input-history-file", input_hist,
        "--chat-history-file", chat_hist,
        "--model-settings-file", tmp_settings,
        "--auto-lint" if runtime["auto_lint"] else "--no-auto-lint",
        "--model", chosen_model,
        "--message", str(instruction).strip(),
        *explicit_file_paths,
    ]

    env = os.environ.copy()
    if runtime["ollama_base"]:
        env.setdefault("OLLAMA_API_BASE", runtime["ollama_base"])
    for k, v in (runtime.get("env_keys") or {}).items():
        env.setdefault(k, v)
    env.setdefault("AIDER_NO_BROWSER", "1")
    env.setdefault("GIT_TERMINAL_PROMPT", "0")
    env.setdefault("PYTHONIOENCODING", "utf-8")

    try:
        t_limit = max(15, min(int(timeout_seconds), 600))
    except (TypeError, ValueError):
        t_limit = 180

    AgentTracer.emit_action("aider", f"[{chosen_model}] {os.path.basename(repo_root)}", "Starting isolated Aider task...")
    logger.info(f"[AIDER] Launching (model={chosen_model}, ctx={runtime['num_ctx']}, cwd={repo_root})")

    output_lines: List[str] = []
    timed_out = threading.Event()

    try:
        proc = _spawn_aider_process(cmd, cwd=repo_root, env=env)

        def _kill_on_timeout():
            timed_out.set()
            try:
                proc.kill()
            except OSError:
                pass

        timer = threading.Timer(t_limit, _kill_on_timeout)
        timer.daemon = True
        timer.start()
        last_trace_ts = 0.0
        try:
            assert proc.stdout is not None
            for raw_line in proc.stdout:
                line = raw_line.rstrip("\r\n")
                output_lines.append(line)
                now = time.monotonic()
                stripped = line.strip()
                if stripped:
                    is_milestone = stripped.startswith((
                        "Applied edit", "Wrote ", "Error", "Warning", "Tokens:",
                        "Added ", "Commit ", "Model:", "Git repo:",
                    ))
                    if is_milestone:
                        logger.info(f"[AIDER] {stripped[:260]}")
                    else:
                        logger.debug(f"[AIDER] {stripped[:260]}")
                    if now - last_trace_ts >= 1.2 or is_milestone:
                        last_trace_ts = now
                        AgentTracer.emit_action("aider", f"[{chosen_model}]", stripped[:220])
            proc.wait(timeout=5)
        finally:
            timer.cancel()

        if timed_out.is_set():
            logger.warning(f"[AIDER] Timed out after {t_limit}s in {repo_root}")
            return f"[EXECUTOR] Aider timed out after {t_limit}s in {repo_root}."

        combined = "\n".join(output_lines).strip()
        if len(combined) > 5500:
            combined = combined[:1500] + "\n... [TRUNCATED] ...\n" + combined[-3800:]

        if proc.returncode != 0:
            logger.warning(f"[AIDER] Exited with code {proc.returncode} (repo={repo_root})")
            return f"[EXECUTOR] Aider exited with code {proc.returncode} (repo={repo_root}):\n{combined}"

        touched_files = _collect_touched_files(repo_root, before_state, explicit_file_paths)
        logger.info(f"[AIDER] Completed cleanly (model={chosen_model}, touched={len(touched_files)}, repo={repo_root})")
        verify_notes: List[str] = []
        verified_lines: List[str] = []
        for fpath in touched_files[:20]:
            rel = os.path.relpath(fpath, repo_root).replace("\\", "/")
            uri = "file:///" + fpath.replace("\\", "/")
            verified_lines.append(f"- {rel} | URI: {uri}")
            ext = os.path.splitext(fpath)[1].lower()
            if ext in _VERIFY_EXTS:
                syn = check_syntax_tool(fpath)
                if "SYNTAX ERROR" in syn:
                    verify_notes.append(f"[AUTO-CHECK] {syn}")
                if ext in (".py", ".html", ".htm"):
                    for w in inspect_web_project_issues(fpath):
                        verify_notes.append(f"[WEB-DIAGNOSTIC] {w}")

        sections = [
            f"[EXECUTOR] Aider task completed (model={chosen_model}, ctx={runtime['num_ctx']}, repo={repo_root})",
        ]
        if verified_lines:
            sections.append("Verified files touched by Aider:\n" + "\n".join(verified_lines))
        if verify_notes:
            sections.append("\n".join(verify_notes))
        if combined:
            sections.append(f"--- AIDER LOG ---\n{combined}")
        result = "\n\n".join(sections)
        AgentTracer.emit_action("aider", f"Completed in {os.path.basename(repo_root)}", f"{len(touched_files)} file(s) touched")
        return result
    except Exception as exc:
        logger.error(f"[EXECUTOR] Aider execution error: {exc}")
        return f"[EXECUTOR] Aider execution error: {exc}"
    finally:
        if os.path.exists(tmp_settings):
            try:
                os.unlink(tmp_settings)
            except OSError:
                pass
        if os.path.exists(tmp_hist_dir):
            shutil.rmtree(tmp_hist_dir, ignore_errors=True)
