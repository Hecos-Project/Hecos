"""
Safe Git version-control helpers for Hecos coding workflows.
Uses native `git` CLI and non-destructive temporary-index checkpoints so
tracked and untracked work can be snapshotted without mutating HEAD or .git/index.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
import time
from typing import Dict, List, Optional, Tuple

from .file_manager import _is_safe_path

try:
    from hecos.core.logging import logger
except ImportError:
    logger = logging.getLogger(__name__)


def _git_binary() -> Optional[str]:
    return shutil.which("git")


def _parse_bool(val, default: bool = False) -> bool:
    if isinstance(val, bool):
        return val
    if val is None:
        return default
    return str(val).strip().lower() in {"1", "true", "yes", "y", "on"}


def _run_git(
    cwd: str,
    args: List[str],
    timeout: int = 20,
    extra_env: Optional[Dict[str, str]] = None,
) -> Tuple[int, str, str]:
    git_bin = _git_binary()
    if not git_bin:
        return 127, "", "'git' executable was not found on PATH."
    env = os.environ.copy()
    env.setdefault("GIT_TERMINAL_PROMPT", "0")
    if extra_env:
        env.update(extra_env)
    proc = subprocess.run(
        [git_bin, *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        errors="replace",
        timeout=timeout,
    )
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def _is_git_ignored(root: str, target_dir: str) -> bool:
    """Return True if target_dir is ignored by a parent repository's .gitignore or sits inside Hecos media/workspace."""
    if os.path.normcase(root) == os.path.normcase(target_dir):
        return False
    norm_target = os.path.normcase(target_dir).replace("\\", "/")
    norm_root = os.path.normcase(root).replace("\\", "/")
    # Do not let isolated workspace/sandbox projects silently bind to parent Hecos repo
    if ("/hecos/media/workspace" in norm_target or "/hecos/media/sandbox" in norm_target) and (
        "/hecos/media/workspace" not in norm_root and "/hecos/media/sandbox" not in norm_root
    ):
        return True
    rc, _, _ = _run_git(target_dir, ["check-ignore", "-q", "."])
    return rc == 0


def _resolve_repo_root(repo_path: str, auto_init: bool = False) -> Tuple[Optional[str], Optional[str]]:
    raw = os.path.abspath(repo_path or ".")
    target_dir = os.path.dirname(raw) if os.path.isfile(raw) else raw
    if not _is_safe_path(target_dir):
        return None, "[EXECUTOR] ACCESS DENIED: Git operations on system paths are forbidden."
    if not os.path.isdir(target_dir):
        return None, f"[EXECUTOR] Directory not found: {target_dir}"

    rc, out, _ = _run_git(target_dir, ["rev-parse", "--show-toplevel"])
    if rc == 0 and out.strip():
        root = os.path.abspath(out.strip())
        if not _is_safe_path(root):
            return None, "[EXECUTOR] ACCESS DENIED: Repository root points to a protected system path."
        if not _is_git_ignored(root, target_dir):
            return root, None

    if auto_init:
        rc_init, _, err_init = _run_git(target_dir, ["init", "-q"])
        if rc_init != 0:
            return None, f"[EXECUTOR] Failed to initialize Git repository in {target_dir}: {err_init.strip()}"
        return target_dir, None

    return None, f"[EXECUTOR] Not inside a Git repository: {target_dir}"


def git_status_tool(repo_path: str = ".") -> str:
    """Return concise branch and working-tree status for a Git repository."""
    root, err = _resolve_repo_root(repo_path, auto_init=False)
    if err or not root:
        return err or "[EXECUTOR] Git repository not found."

    rc, out, err_txt = _run_git(root, ["status", "--short", "--branch"])
    if rc != 0:
        logger.warning(f"[GIT] git status failed in {root}: {err_txt.strip()}")
        return f"[EXECUTOR] git status failed: {err_txt.strip()}"
    body = out.strip() or "(clean)"
    if len(body) > 4000:
        body = body[:3900] + "\n... [GIT STATUS TRUNCATED]"
    logger.debug(f"[GIT] status checked in {root}")
    return f"[EXECUTOR] Git status ({root}):\n{body}"


def git_diff_tool(repo_path: str = ".", file_path: str = "", staged: bool = False) -> str:
    """Return a size-capped unified diff for the repository or a specific file."""
    root, err = _resolve_repo_root(repo_path, auto_init=False)
    if err or not root:
        return err or "[EXECUTOR] Git repository not found."

    args = ["diff", "--no-color"]
    if _parse_bool(staged, False):
        args.append("--staged")

    rel_target = ""
    if file_path and str(file_path).strip():
        abs_file = os.path.abspath(file_path if os.path.isabs(file_path) else os.path.join(root, file_path))
        if not _is_safe_path(abs_file):
            return "[EXECUTOR] ACCESS DENIED: Protected file path."
        try:
            rel_target = os.path.relpath(abs_file, root)
        except ValueError:
            rel_target = file_path
        args.extend(["--", rel_target])

    rc, out, err_txt = _run_git(root, args)
    if rc != 0:
        return f"[EXECUTOR] git diff failed: {err_txt.strip()}"

    diff_text = out.strip()
    if not diff_text:
        scope = rel_target or "working tree"
        mode = "staged" if _parse_bool(staged, False) else "unstaged"
        return f"[EXECUTOR] No {mode} diff for {scope} in {root}."

    if len(diff_text) > 8000:
        diff_text = diff_text[:7800] + "\n... [DIFF TRUNCATED — pass a specific file_path to view full hunks]"
    return f"[EXECUTOR] Git diff ({root}):\n{diff_text}"


def git_checkpoint_tool(repo_path: str, message: str = "hecos checkpoint", auto_init: bool = True) -> str:
    """
    Create a non-destructive snapshot ref under refs/hecos-checkpoints/<timestamp>
    covering both tracked and untracked (non-ignored) files without altering HEAD or .git/index.
    """
    root, err = _resolve_repo_root(repo_path, auto_init=_parse_bool(auto_init, True))
    if err or not root:
        return err or "[EXECUTOR] Git repository not found."

    rc_head, head_out, _ = _run_git(root, ["rev-parse", "--verify", "HEAD"])
    has_head = rc_head == 0 and bool(head_out.strip())

    fd, tmp_index = tempfile.mkstemp(prefix="hecos_git_idx_")
    os.close(fd)
    # Remove empty file so git creates a valid binary index from scratch
    try:
        os.unlink(tmp_index)
    except OSError:
        pass

    env = {
        "GIT_INDEX_FILE": tmp_index,
        "GIT_AUTHOR_NAME": "Hecos Coder",
        "GIT_AUTHOR_EMAIL": "hecos-coder@local",
        "GIT_COMMITTER_NAME": "Hecos Coder",
        "GIT_COMMITTER_EMAIL": "hecos-coder@local",
    }

    try:
        if has_head:
            rc_rt, _, err_rt = _run_git(root, ["read-tree", "HEAD"], extra_env=env)
            if rc_rt != 0:
                return f"[EXECUTOR] Checkpoint read-tree failed: {err_rt.strip()}"

        rc_add, _, err_add = _run_git(root, ["add", "-A"], extra_env=env)
        if rc_add != 0:
            return f"[EXECUTOR] Checkpoint add failed: {err_add.strip()}"

        rc_tree, tree_out, err_tree = _run_git(root, ["write-tree"], extra_env=env)
        if rc_tree != 0:
            return f"[EXECUTOR] Checkpoint write-tree failed: {err_tree.strip()}"
        tree_sha = tree_out.strip()

        clean_msg = (message or "hecos checkpoint").strip()[:160]
        commit_args = ["commit-tree", tree_sha]
        if has_head:
            commit_args.extend(["-p", head_out.strip()])
        commit_args.extend(["-m", clean_msg])

        rc_cm, cm_out, err_cm = _run_git(root, commit_args, extra_env=env)
        if rc_cm != 0:
            return f"[EXECUTOR] Checkpoint commit-tree failed: {err_cm.strip()}"
        commit_sha = cm_out.strip()

        ts_ref = f"refs/hecos-checkpoints/{time.strftime('%Y%m%d_%H%M%S')}_{commit_sha[:7]}"
        rc_ref, _, err_ref = _run_git(root, ["update-ref", ts_ref, commit_sha])
        if rc_ref != 0:
            return f"[EXECUTOR] Checkpoint update-ref failed: {err_ref.strip()}"

        logger.info(f"[GIT] Checkpoint saved: {ts_ref} -> {commit_sha[:10]} in {root}")
        return f"[EXECUTOR] Git checkpoint created: {ts_ref} ({commit_sha[:10]}) in {root}"
    finally:
        for leftover in (tmp_index, tmp_index + ".lock"):
            if os.path.exists(leftover):
                try:
                    os.unlink(leftover)
                except OSError:
                    pass


def _resolve_checkpoint_ref(root: str, target_ref: str) -> str:
    ref = (target_ref or "HEAD").strip()
    if ref.lower() in ("latest", "last", "checkpoint"):
        rc, out, _ = _run_git(
            root,
            ["for-each-ref", "--sort=-committerdate", "--count=1", "--format=%(refname)", "refs/hecos-checkpoints"],
        )
        if rc == 0 and out.strip():
            return out.strip().splitlines()[0]
    return ref


def git_restore_tool(
    repo_path: str,
    file_path: str = "",
    target_ref: str = "HEAD",
    confirm_all: bool = False,
) -> str:
    """
    Restore a specific file (or the entire working tree when confirm_all=True) from target_ref
    (e.g. 'HEAD', 'latest' checkpoint ref, or a checkpoint SHA/ref).
    """
    root, err = _resolve_repo_root(repo_path, auto_init=False)
    if err or not root:
        return err or "[EXECUTOR] Git repository not found."

    ref = _resolve_checkpoint_ref(root, target_ref)
    rc_v, _, err_v = _run_git(root, ["rev-parse", "--verify", ref])
    if rc_v != 0:
        return f"[EXECUTOR] Target ref '{ref}' could not be resolved: {err_v.strip()}"

    clean_file = (file_path or "").strip()
    if not clean_file:
        if not _parse_bool(confirm_all, False):
            return (
                "[EXECUTOR] Refusing to restore entire working tree without explicit file_path or "
                "confirm_all=True."
            )
        rc, _, err_r = _run_git(root, ["checkout", ref, "--", "."])
        if rc != 0:
            logger.warning(f"[GIT] Restore all failed from '{ref}' in {root}: {err_r.strip()}")
            return f"[EXECUTOR] git restore failed: {err_r.strip()}"
        logger.info(f"[GIT] Restored all tracked files from '{ref}' in {root}")
        return f"[EXECUTOR] Restored all tracked files from '{ref}' in {root}"

    abs_file = os.path.abspath(clean_file if os.path.isabs(clean_file) else os.path.join(root, clean_file))
    if not _is_safe_path(abs_file):
        return "[EXECUTOR] ACCESS DENIED: Protected file path."
    try:
        rel_file = os.path.relpath(abs_file, root)
    except ValueError:
        rel_file = clean_file

    rc, _, err_r = _run_git(root, ["checkout", ref, "--", rel_file])
    if rc != 0:
        logger.warning(f"[GIT] Restore failed for '{rel_file}' from '{ref}': {err_r.strip()}")
        return f"[EXECUTOR] git restore failed for '{rel_file}' from '{ref}': {err_r.strip()}"
    logger.info(f"[GIT] Restored '{rel_file}' from '{ref}' in {root}")
    return f"[EXECUTOR] Restored '{rel_file}' from '{ref}' in {root}"
