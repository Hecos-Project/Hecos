"""
hecos/modules/executor/cli_bridge/terminal_launcher.py
Spawns native Windows PowerShell / Terminal windows pre-configured for Hecos Coding:
- `mode="shell"`: Project PowerShell with `python_env` + `tools/aider_env` on PATH.
- `mode="aider"`: Interactive Aider CLI connected to Hecos's active LLM/Ollama settings & project Git.
- `mode="trace"`: Live color-coded Action Trace console tailing `logs/hecos_actions.log`.
"""

from __future__ import annotations

import datetime
import os
import subprocess
from typing import Any, Dict, List, Optional

from hecos.core import constants

from ..aider_bridge import (
    _hecos_root,
    _write_temp_model_settings,
    resolve_aider_command,
    resolve_aider_runtime_settings,
)
from ..git_tools import _resolve_repo_root
from .action_feed import get_actions_log_path, record_action_event


def _ps_quote(val: str) -> str:
    """Single-quote a string safely for PowerShell `-Command`."""
    return "'" + str(val or "").replace("'", "''") + "'"


def resolve_project_cwd(target_path: str = "", workspace_dir: str = "") -> str:
    """Resolve a valid directory path for launching a coding terminal."""
    ws_root = os.path.abspath(workspace_dir or constants.WORKSPACE_DIR)
    os.makedirs(ws_root, exist_ok=True)
    if not target_path or not str(target_path).strip():
        return ws_root
    cand = os.path.abspath(str(target_path).strip())
    if os.path.isfile(cand):
        cand = os.path.dirname(cand)
    if os.path.isdir(cand):
        return cand
    return ws_root


def build_coding_env(extra_env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Build environment dictionary with Hecos `python_env` and `aider_env` prepended to PATH."""
    root = _hecos_root()
    py_scripts = os.path.join(root, "python_env", "Scripts")
    py_root = os.path.join(root, "python_env")
    aider_scripts = os.path.join(root, "tools", "aider_env", "Scripts")

    env = os.environ.copy()
    path_parts = [p for p in (py_scripts, py_root, aider_scripts) if os.path.isdir(p)]
    old_path = env.get("PATH", "")
    env["PATH"] = os.pathsep.join([*path_parts, old_path]) if path_parts else old_path
    env["PYTHONPATH"] = root + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    env["PYTHONIOENCODING"] = "utf-8"
    if extra_env:
        for k, v in extra_env.items():
            if v is not None:
                env[str(k)] = str(v)
    return env


def _spawn_windows_powershell(title: str, ps_script: str, cwd: str, env: Dict[str, str], dry_run: bool = False) -> bool:
    if dry_run:
        return True
    if os.name == "nt":
        subprocess.Popen(
            ["cmd.exe", "/c", "start", "", "powershell.exe", "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            cwd=cwd,
            env=env,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return True
    return False


def launch_native_terminal(
    mode: str = "shell",
    target_path: str = "",
    files: Optional[List[str]] = None,
    model: str = "",
    workspace_dir: str = "",
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Launch a native Windows CLI window for coding:
    - `shell`: PowerShell inside the project with Hecos Python + Aider on PATH
    - `aider`: Interactive Aider CLI pre-configured with Hecos LLM/Ollama model & num_ctx
    - `trace`: Live color-coded Hecos Coding Action Trace console
    """
    clean_mode = str(mode or "shell").strip().lower()
    root = _hecos_root()
    cwd = resolve_project_cwd(target_path, workspace_dir=workspace_dir)
    proj_name = os.path.basename(cwd.rstrip("\\/")) or "workspace"

    py_scripts = os.path.join(root, "python_env", "Scripts")
    aider_scripts = os.path.join(root, "tools", "aider_env", "Scripts")

    if clean_mode == "trace":
        log_file = get_actions_log_path()
        if not os.path.isfile(log_file):
            with open(log_file, "a", encoding="utf-8") as fh:
                now_str = datetime.datetime.now().strftime("%H:%M:%S")
                fh.write(f"{now_str} [ACTION:SYSTEM] [OK] $ Hecos Coding Action Trace Initialized\n")

        title = "Hecos - Coding Action Trace"
        ps_script = (
            f"$host.ui.RawUI.WindowTitle = {_ps_quote(title)}; "
            "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
            "Write-Host '================================================================' -ForegroundColor Cyan; "
            "Write-Host '  HECOS LIVE CODING ACTION TRACE (Real-Time Tool & Aider Feed)  ' -ForegroundColor Cyan; "
            "Write-Host '================================================================' -ForegroundColor Cyan; "
            f"Write-Host ('Log file: ' + {_ps_quote(log_file)}) -ForegroundColor DarkGray; "
            "Write-Host ''; "
            f"Get-Content -Encoding utf8 -Path {_ps_quote(log_file)} -Wait -Tail 35 | ForEach-Object {{ "
            "if ($_ -match '\\[ERROR\\]') { Write-Host $_ -ForegroundColor Red } "
            "elseif ($_ -match '\\[ACTION:AIDER\\]') { Write-Host $_ -ForegroundColor Magenta } "
            "elseif ($_ -match '\\[ACTION:') { Write-Host $_ -ForegroundColor Green } "
            "elseif ($_ -match '^\\s*\\|') { Write-Host $_ -ForegroundColor Gray } "
            "else { Write-Host $_ -ForegroundColor White } "
            "}"
        )
        env = build_coding_env()
        _spawn_windows_powershell(title, ps_script, cwd=cwd, env=env, dry_run=dry_run)
        record_action_event("cli_launch", f"Open Live Action Trace ({proj_name})", f"Tailing {log_file}")
        return {
            "ok": True,
            "mode": "trace",
            "title": title,
            "cwd": cwd.replace("\\", "/"),
            "log_path": log_file.replace("\\", "/"),
            "ps_command": ps_script,
            "dry_run": dry_run,
        }

    if clean_mode == "aider":
        runtime = resolve_aider_runtime_settings(explicit_model=model)
        base_cmd = resolve_aider_command()
        if not base_cmd:
            return {
                "ok": False,
                "error": "Isolated Aider CLI is not installed in tools/aider_env yet.",
            }

        ws_abs = os.path.abspath(workspace_dir or constants.WORKSPACE_DIR)
        allow_git_init = os.path.normcase(cwd) != os.path.normcase(ws_abs)
        repo_root, repo_err = _resolve_repo_root(cwd, auto_init=allow_git_init)
        work_dir = repo_root if (repo_root and not repo_err) else cwd
        chosen_model = runtime["model"]
        num_ctx = runtime["num_ctx"]
        settings_yml = _write_temp_model_settings(chosen_model, num_ctx, runtime["edit_format"])

        aider_exe = base_cmd[0]
        aider_args: List[str] = [
            "--model", chosen_model,
            "--model-settings-file", settings_yml,
            "--encoding", "utf-8",
            "--no-check-update",
            "--no-analytics",
            "--no-gitignore",
            "--auto-lint" if runtime["auto_lint"] else "--no-auto-lint",
        ]
        rel_files: List[str] = []
        for f in files or []:
            if not f:
                continue
            abs_f = os.path.abspath(f if os.path.isabs(f) else os.path.join(work_dir, f))
            if os.path.isfile(abs_f):
                try:
                    rel_files.append(os.path.relpath(abs_f, work_dir))
                except ValueError:
                    rel_files.append(abs_f)
        aider_args.extend(rel_files)

        extra_env = dict(runtime.get("env_keys") or {})
        if runtime.get("ollama_base"):
            extra_env["OLLAMA_API_BASE"] = str(runtime["ollama_base"])
        extra_env["AIDER_NO_BROWSER"] = "1"
        env = build_coding_env(extra_env=extra_env)

        title = f"Hecos Aider CLI - {proj_name} [{chosen_model}]"
        ps_args_str = " ".join(_ps_quote(a) for a in aider_args)
        env_inject_lines = [
            f"$env:PATH = {_ps_quote(py_scripts + os.pathsep + aider_scripts)} + ';' + $env:PATH",
            f"$env:PYTHONPATH = {_ps_quote(root)}",
            "$env:PYTHONIOENCODING = 'utf-8'",
            "$env:AIDER_NO_BROWSER = '1'",
        ]
        if runtime.get("ollama_base"):
            env_inject_lines.append(f"$env:OLLAMA_API_BASE = {_ps_quote(str(runtime['ollama_base']))}")
        for k, v in (runtime.get("env_keys") or {}).items():
            if v:
                env_inject_lines.append(f"$env:{k} = {_ps_quote(str(v))}")

        ps_script = (
            f"$host.ui.RawUI.WindowTitle = {_ps_quote(title)}; "
            "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
            + "; ".join(env_inject_lines) + "; "
            f"Set-Location -LiteralPath {_ps_quote(work_dir)}; "
            "Write-Host '================================================================' -ForegroundColor Magenta; "
            f"Write-Host ('  HECOS INTERACTIVE AIDER CLI — ' + {_ps_quote(proj_name)}) -ForegroundColor Magenta; "
            f"Write-Host ('  Model: ' + {_ps_quote(chosen_model)} + ' | Context: ' + '{num_ctx}' + ' tokens') -ForegroundColor Cyan; "
            f"Write-Host ('  Repo : ' + {_ps_quote(work_dir)}) -ForegroundColor DarkGray; "
            "Write-Host '  Tip  : Type /help, /add <file>, /architect <prompt>, /diff, /undo' -ForegroundColor Gray; "
            "Write-Host '================================================================' -ForegroundColor Magenta; "
            f"& {_ps_quote(aider_exe)} {ps_args_str}"
        )
        _spawn_windows_powershell(title, ps_script, cwd=work_dir, env=env, dry_run=dry_run)
        record_action_event(
            "cli_launch",
            f"Launch Interactive Aider CLI ({proj_name})",
            f"model={chosen_model}, num_ctx={num_ctx}, cwd={work_dir}",
        )
        return {
            "ok": True,
            "mode": "aider",
            "title": title,
            "cwd": work_dir.replace("\\", "/"),
            "model": chosen_model,
            "num_ctx": num_ctx,
            "settings_file": settings_yml.replace("\\", "/"),
            "command": [aider_exe, *aider_args],
            "ps_command": ps_script,
            "dry_run": dry_run,
        }

    # Default: mode == "shell"
    title = f"Hecos Coding Shell - {proj_name}"
    env = build_coding_env()
    ps_script = (
        f"$host.ui.RawUI.WindowTitle = {_ps_quote(title)}; "
        "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
        f"$env:PATH = {_ps_quote(py_scripts + os.pathsep + aider_scripts)} + ';' + $env:PATH; "
        f"$env:PYTHONPATH = {_ps_quote(root)}; "
        "$env:PYTHONIOENCODING = 'utf-8'; "
        f"Set-Location -LiteralPath {_ps_quote(cwd)}; "
        "Write-Host '================================================================' -ForegroundColor Green; "
        f"Write-Host ('  HECOS CODING SHELL — ' + {_ps_quote(proj_name)}) -ForegroundColor Green; "
        f"Write-Host ('  Working Dir : ' + {_ps_quote(cwd)}) -ForegroundColor Gray; "
        "Write-Host '  Tools Ready : python, pytest, ruff, aider, git' -ForegroundColor Cyan; "
        "Write-Host '================================================================' -ForegroundColor Green; "
        "Write-Host ''"
    )
    _spawn_windows_powershell(title, ps_script, cwd=cwd, env=env, dry_run=dry_run)
    record_action_event("cli_launch", f"Open Native Coding Shell ({proj_name})", f"cwd={cwd}")
    return {
        "ok": True,
        "mode": "shell",
        "title": title,
        "cwd": cwd.replace("\\", "/"),
        "ps_command": ps_script,
        "dry_run": dry_run,
    }
