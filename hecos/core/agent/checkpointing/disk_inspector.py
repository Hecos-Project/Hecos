"""
hecos/core/agent/checkpointing/disk_inspector.py
Ground-truth disk scanner for interrupted AgentExecutor checkpoints.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List

from hecos.core.agent.hallucination_guards import extract_verified_files_from_results

_DIR_CREATED_RE = re.compile(r"\[EXECUTOR\]\s+Directory created:\s*([^\r\n]+)", re.IGNORECASE)
_WORKSPACE_MARKER_RE = re.compile(
    r"([A-Za-z]:[/\\][^\r\n\"'<>|]+?[/\\]media[/\\]workspace[/\\][A-Za-z0-9_.-]+)",
    re.IGNORECASE,
)


def _infer_project_dir(
    accumulated_tool_results: List[Dict[str, Any]],
    verified_paths: List[str],
    user_text: str = "",
) -> str:
    """Infer primary project root directory touched by prior steps or prompt text."""
    for vp in verified_paths:
        m = _WORKSPACE_MARKER_RE.search(vp)
        if m and os.path.isdir(m.group(1)):
            return os.path.abspath(m.group(1))

    for res in accumulated_tool_results or []:
        out = str(res.get("output") or "")
        for dm in _DIR_CREATED_RE.finditer(out):
            cand = os.path.abspath(dm.group(1).strip())
            m = _WORKSPACE_MARKER_RE.search(cand)
            if m and os.path.isdir(m.group(1)):
                return os.path.abspath(m.group(1))
            if os.path.isdir(cand):
                return cand

    rel_match = re.search(r"hecos[/\\]media[/\\]workspace[/\\]([A-Za-z0-9_.-]+)", user_text or "", re.IGNORECASE)
    if rel_match:
        here = os.path.dirname(os.path.abspath(__file__))
        hecos_root = os.path.abspath(os.path.join(here, "..", "..", ".."))
        cand = os.path.join(hecos_root, "media", "workspace", rel_match.group(1))
        if os.path.isdir(cand):
            return cand

    if verified_paths:
        return os.path.dirname(verified_paths[0])
    return ""


def _list_project_snapshot(project_dir: str, max_entries: int = 35) -> List[str]:
    """List actual non-cache files currently existing under `project_dir`."""
    if not project_dir or not os.path.isdir(project_dir):
        return []
    skip_dirs = {"__pycache__", ".git", "node_modules", ".pytest_cache", ".venv", "venv"}
    entries: List[str] = []
    for root_dir, dirnames, filenames in os.walk(project_dir):
        dirnames[:] = sorted(d for d in dirnames if d not in skip_dirs and not d.startswith(".aider"))
        for fname in sorted(filenames):
            full = os.path.join(root_dir, fname)
            rel = os.path.relpath(full, project_dir).replace("\\", "/")
            try:
                sz = os.path.getsize(full)
                entries.append(f"{rel} ({sz}B)")
            except OSError:
                entries.append(rel)
            if len(entries) >= max_entries:
                return entries
    return entries


def inspect_workspace_progress(
    accumulated_tool_results: List[Dict[str, Any]],
    *,
    user_text: str = "",
) -> Dict[str, Any]:
    """
    Reconcile checkpoint tool history against what actually exists on disk right now.
    """
    verified = extract_verified_files_from_results(accumulated_tool_results or [])
    verified_paths = [abs_p for abs_p, _, _ in verified]
    verified_items: List[Dict[str, Any]] = []
    for abs_p, file_uri, fname in verified:
        try:
            sz = os.path.getsize(abs_p)
        except OSError:
            sz = 0
        verified_items.append({
            "path": abs_p,
            "file_uri": file_uri,
            "name": fname,
            "size": sz,
        })

    project_dir = _infer_project_dir(accumulated_tool_results or [], verified_paths, user_text=user_text)
    dir_entries = _list_project_snapshot(project_dir)

    return {
        "project_dir": project_dir,
        "verified_files": verified_items,
        "directory_entries": dir_entries,
    }
