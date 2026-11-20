"""
hecos/modules/executor/cli_bridge/coding_cli_app.py
Standalone Hecos Coding CLI (Interactive TUI + Direct CLI Flags).
Allows developers to manage workspace projects, launch pre-configured Interactive Aider,
open project PowerShell environments, run tests/apps, inspect live action traces,
and stop locked/orphan workspace processes directly from the terminal.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from typing import Any, Dict, List

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from hecos.core import constants
from hecos.modules.executor.aider_bridge import (
    _write_temp_model_settings,
    get_aider_status,
    resolve_aider_command,
    resolve_aider_runtime_settings,
    run_aider_task_tool,
)
from hecos.modules.executor.git_tools import _resolve_repo_root
from hecos.modules.executor.process_runner import get_process_registry, run_smart
from hecos.modules.executor.test_runner import list_workspace_projects

from .action_feed import get_action_events
from .terminal_launcher import build_coding_env, launch_native_terminal


def get_coding_cli_overview(workspace_dir: str = "") -> Dict[str, Any]:
    """Return structured status of workspace projects, active processes, and Aider runtime."""
    ws_dir = os.path.abspath(workspace_dir or constants.WORKSPACE_DIR)
    os.makedirs(ws_dir, exist_ok=True)
    reg = get_process_registry()
    projects = list_workspace_projects(ws_dir, registry=reg)
    processes = reg.list_all_processes(workspace_dir=ws_dir)
    aider_st = get_aider_status(check_version=False)
    return {
        "ok": True,
        "workspace_dir": ws_dir,
        "projects": projects,
        "processes": processes,
        "aider": aider_st,
    }


def run_interactive_aider_inline(project_dir: str, model: str = "") -> int:
    """Run Aider interactively inside the current console session."""
    base_cmd = resolve_aider_command()
    if not base_cmd:
        print("\n[!] Isolated Aider CLI is not installed in tools/aider_env.")
        return 1

    runtime = resolve_aider_runtime_settings(explicit_model=model)
    repo_root, _ = _resolve_repo_root(project_dir, auto_init=True)
    work_dir = repo_root or project_dir
    chosen_model = runtime["model"]
    num_ctx = runtime["num_ctx"]
    settings_yml = _write_temp_model_settings(chosen_model, num_ctx, runtime["edit_format"])

    cmd = [
        *base_cmd,
        "--model", chosen_model,
        "--model-settings-file", settings_yml,
        "--encoding", "utf-8",
        "--no-check-update",
        "--no-analytics",
        "--no-gitignore",
        "--auto-lint" if runtime["auto_lint"] else "--no-auto-lint",
    ]

    extra_env = dict(runtime.get("env_keys") or {})
    if runtime.get("ollama_base"):
        extra_env["OLLAMA_API_BASE"] = str(runtime["ollama_base"])
    extra_env["AIDER_NO_BROWSER"] = "1"
    env = build_coding_env(extra_env=extra_env)

    print("\n" + "=" * 72)
    print(f"  LAUNCHING INTERACTIVE AIDER CLI — {os.path.basename(work_dir)}")
    print(f"  Model : {chosen_model} (num_ctx={num_ctx})")
    print(f"  Path  : {work_dir}")
    print("=" * 72 + "\n")
    try:
        res = subprocess.run(cmd, cwd=work_dir, env=env)
        return int(res.returncode)
    finally:
        if os.path.exists(settings_yml):
            try:
                os.unlink(settings_yml)
            except OSError:
                pass


def _select_project_interactive(projects: List[Dict[str, Any]], ws_dir: str) -> str:
    if not projects:
        name = input("Enter new project folder name (e.g. my_app): ").strip()
        if not name:
            return ""
        target = os.path.join(ws_dir, os.path.basename(name))
        os.makedirs(target, exist_ok=True)
        return target

    print("\nAvailable Workspace Projects:")
    for idx, p in enumerate(projects, 1):
        runs_tag = f" [RUNNING: {p.get('active_runs')}]" if p.get("active_runs") else ""
        print(f"  {idx}. {p['name']} ({p.get('file_count', 0)} files){runs_tag}")
    print(f"  N. Create a new project folder")

    choice = input("\nSelect project number or 'N': ").strip()
    if choice.lower() == "n":
        name = input("New project folder name: ").strip()
        if not name:
            return ""
        target = os.path.join(ws_dir, os.path.basename(name))
        os.makedirs(target, exist_ok=True)
        return target
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(projects):
            return projects[idx]["path"]
    return ""


def interactive_coding_menu() -> int:
    """Interactive terminal loop for Hecos Coding Studio CLI."""
    while True:
        overview = get_coding_cli_overview()
        ws_dir = overview["workspace_dir"]
        projects = overview["projects"]
        aider_info = overview["aider"]
        active_procs = [p for p in overview["processes"] if p.get("status") == "running"]

        print("\n" + "=" * 74)
        print("                     HECOS CODING & AIDER STUDIO CLI")
        print("=" * 74)
        print(f"  Workspace : {ws_dir}")
        print(
            f"  Aider     : {'READY' if aider_info['installed'] else 'NOT INSTALLED'} "
            f"| Model: {aider_info['model']} (ctx={aider_info['num_ctx']})"
        )
        print(f"  Projects  : {len(projects)} | Active Processes: {len(active_procs)}")
        print("-" * 74)
        print("  1. Launch Interactive Aider CLI in Current Terminal (Fastest Coding)")
        print("  2. Open New Project PowerShell Window (python + pytest + ruff + aider)")
        print("  3. Pop Out Interactive Aider in New Terminal Window")
        print("  4. Open Live Coding Action Trace Window (Real-Time Tool & Aider Feed)")
        print("  5. Run One-Shot Aider Instruction on a Project")
        print("  6. Run Project Tests / App via Hecos Runner")
        print("  7. List / Stop Active & Orphaned Workspace Processes")
        print("  8. View Recent Coding Action Feed")
        print("  0. Exit")
        print("-" * 74)

        try:
            choice = input("Select an option (0-8): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if choice == "0":
            return 0
        if choice == "1":
            proj = _select_project_interactive(projects, ws_dir)
            if proj:
                run_interactive_aider_inline(proj)
        elif choice == "2":
            proj = _select_project_interactive(projects, ws_dir)
            if proj:
                res = launch_native_terminal(mode="shell", target_path=proj, workspace_dir=ws_dir)
                print(f"[*] Opened Coding Shell in: {res.get('cwd')}")
        elif choice == "3":
            proj = _select_project_interactive(projects, ws_dir)
            if proj:
                res = launch_native_terminal(mode="aider", target_path=proj, workspace_dir=ws_dir)
                if res.get("ok"):
                    print(f"[*] Opened Interactive Aider window ({res.get('model')}) in {res.get('cwd')}")
                else:
                    print(f"[!] {res.get('error')}")
        elif choice == "4":
            res = launch_native_terminal(mode="trace", workspace_dir=ws_dir)
            print(f"[*] Opened Live Action Trace Console ({res.get('log_path')})")
        elif choice == "5":
            proj = _select_project_interactive(projects, ws_dir)
            if proj:
                inst = input("Enter coding instruction for Aider: ").strip()
                if inst:
                    out = run_aider_task_tool(proj, inst)
                    print("\n" + out)
        elif choice == "6":
            proj = _select_project_interactive(projects, ws_dir)
            if proj:
                mode = input("Execution mode (auto / app / test / script) [test]: ").strip() or "test"
                res = run_smart(proj, mode=mode, workspace_dir=ws_dir, sandbox_dir=constants.SANDBOX_DIR)
                print(f"\nStatus: {res.get('status')} (ok={res.get('ok')})")
                if res.get("output"):
                    print(res["output"])
        elif choice == "7":
            if not active_procs:
                print("\n[*] No active or orphaned workspace processes running.")
            else:
                print("\nActive / Orphaned Workspace Processes:")
                for p in active_procs:
                    tag = "ORPHAN_OS" if p.get("orphan") else "MANAGED"
                    print(f"  - [{tag}] run_id={p['run_id']} | PID={p.get('pid')} | {p.get('name')} ({p.get('cwd')})")
                sub = input("\nEnter PID / run_id to stop, 'all' to stop all, or Enter to cancel: ").strip()
                reg = get_process_registry()
                if sub.lower() == "all":
                    r_stop = reg.stop_all_runs(include_orphans=True, workspace_dir=ws_dir)
                    print(f"[*] Stopped {r_stop.get('stopped_count', 0)} process(es).")
                elif sub.isdigit():
                    r_stop = reg.stop_pid(int(sub), workspace_dir=ws_dir)
                    print(f"[*] Stop PID {sub}: ok={r_stop.get('ok')}")
                elif sub:
                    r_stop = reg.stop_run(sub)
                    print(f"[*] Stop {sub}: ok={r_stop.get('ok')}")
        elif choice == "8":
            feed = get_action_events(limit=25)
            events = feed.get("events") or []
            if not events:
                print("\n[*] No coding actions recorded in current session yet.")
            else:
                print("\nRecent Coding Actions:")
                for ev in events:
                    print(f"  {ev['iso_time']} [{ev['tool_name'].upper()}] ({ev['status']}) $ {ev['command']}")
                    if ev.get("output"):
                        first_ln = ev["output"].splitlines()[0]
                        print(f"      | {first_ln[:110]}")


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hecos Coding & Aider Studio CLI")
    parser.add_argument("--list-projects", action="store_true", help="Print workspace projects and active processes")
    parser.add_argument("--open-shell", metavar="PATH", help="Open native PowerShell coding window for project")
    parser.add_argument("--open-aider", metavar="PATH", help="Open native Interactive Aider CLI window for project")
    parser.add_argument("--open-trace", action="store_true", help="Open Live Coding Action Trace window")
    parser.add_argument("--inline-aider", metavar="PATH", help="Run Interactive Aider inline in current console")
    parser.add_argument("--model", default="", help="Optional model override for Aider")
    parser.add_argument("--dry-run", action="store_true", help="Inspect command without spawning external window")
    args = parser.parse_args(argv)

    if args.list_projects:
        ov = get_coding_cli_overview()
        print(f"Workspace: {ov['workspace_dir']}")
        print(f"Aider: installed={ov['aider']['installed']} model={ov['aider']['model']} ctx={ov['aider']['num_ctx']}")
        for p in ov["projects"]:
            print(f" - {p['name']}: {p['path']} (files={p.get('file_count', 0)}, active_runs={p.get('active_runs', 0)})")
        return 0

    if args.open_trace:
        res = launch_native_terminal(mode="trace", dry_run=args.dry_run)
        print(res)
        return 0 if res.get("ok") else 1

    if args.open_shell:
        res = launch_native_terminal(mode="shell", target_path=args.open_shell, dry_run=args.dry_run)
        print(res)
        return 0 if res.get("ok") else 1

    if args.open_aider:
        res = launch_native_terminal(
            mode="aider", target_path=args.open_aider, model=args.model, dry_run=args.dry_run
        )
        print(res)
        return 0 if res.get("ok") else 1

    if args.inline_aider:
        return run_interactive_aider_inline(args.inline_aider, model=args.model)

    return interactive_coding_menu()


if __name__ == "__main__":
    raise SystemExit(main())
