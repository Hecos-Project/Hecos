# Hecos Coder — Software Development, AI Coding & Workspace Suite

**Hecos Coder** (`id = "coder"`, `type = "system_app"`, `tag = "CODER"`) is the modular software development and code execution suite for Hecos.

## Key Capabilities
- **Workspace Runner (`/workspace`)**: Interactive modal and standalone dashboard to run, test, inspect, and stop generated Python/web projects in `hecos/media/workspace`.
- **Aider Sidecar Engine**: Invisible multi-file code generation and refactoring delegated to an isolated `tools/aider_env` environment, bound to Global Presets (e.g., `hecos_coder`).
- **AST & Tree-Sitter Repository Map**: Compact multi-language symbol and line-number extraction (`CODER__repo_map`, `CODER__project_tree`, `CODER__search_code`).
- **Git Checkpoints & Diff**: Non-destructive snapshots and rollback (`CODER__git_status`, `CODER__git_diff`, `CODER__git_checkpoint`, `CODER__git_restore`).
- **Automated Verification & Process Watchdog**: Deterministic syntax verification (`CODER__check_syntax`), test runner (`CODER__run_project_test`), HTTP probe (`CODER__probe_url`), and orphan process watchdog (`CODER__stop_app`, `CODER__stop_project_processes`).
- **Native Windows CLI Bridge**: Integrated PowerShell, Live Action Trace console, and Interactive Aider CLI (`CODER__open_coding_cli`).
