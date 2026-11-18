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
    norm_target = os.path.normcase(target_dir).replace("\\", "/").rstrip("/")
    norm_root = os.path.normcase(root).replace("\\", "/").rstrip("/")
    # Do not let isolated workspace/sandbox projects silently bind to parent Hecos repo or container root
    if ("/hecos/media/workspace/" in norm_target or "/hecos/media/sandbox/" in norm_target) and (
        ("/hecos/media/workspace" not in norm_root and "/hecos/media/sandbox" not in norm_root)
        or norm_root.endswith(("/hecos/media/workspace", "/hecos/media/sandbox"))
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
        norm_td = os.path.normcase(target_dir).replace("\\", "/").rstrip("/")
        if norm_td.endswith(("/hecos/media/workspace", "/hecos/media/sandbox")):
            return None, f"[EXECUTOR] Select a project subfolder rather than initializing Git on workspace root: {target_dir}"
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


_SKIP_STATUS_PARTS = {".git", ".aider.tags.cache.v4", "__pycache__", ".pytest_cache", "node_modules", ".venv", "venv"}


def _map_porcelain_code(xy: str) -> str:
    """Maps 2-char `git status --porcelain` XY code to compact IDE letter."""
    if xy == "??":
        return "U"
    if "D" in xy:
        return "D"
    if "R" in xy:
        return "R"
    if "M" in xy:
        return "M"
    if "A" in xy:
        return "A"
    return "M"


def _parse_porcelain_z(repo_root: str, raw_stdout: str) -> Dict[str, str]:
    """Parses `git status --porcelain=v1 -uall -z` into {abs_forward_path: code}."""
    result: Dict[str, str] = {}
    if not raw_stdout:
        return result
    tokens = raw_stdout.split("\0")
    i = 0
    while i < len(tokens):
        entry = tokens[i]
        i += 1
        if len(entry) < 4:
            continue
        xy = entry[:2]
        rel_path = entry[3:]
        # Renamed/copied entries carry an extra NUL-separated source path token
        if xy and xy[0] in ("R", "C") and i < len(tokens):
            i += 1
        parts = rel_path.replace("\\", "/").split("/")
        if any(p in _SKIP_STATUS_PARTS or p.startswith(".aider.tags") for p in parts):
            continue
        abs_p = os.path.abspath(os.path.join(repo_root, rel_path)).replace("\\", "/")
        result[abs_p] = _map_porcelain_code(xy)
    return result


def collect_git_file_statuses(target_dir: str) -> Dict[str, str]:
    """
    Returns {abs_forward_path: 'M'|'U'|'A'|'D'|'R'} for a Git repo directory OR
    all immediate Git project subdirectories when `target_dir` is a workspace container.
    """
    if not target_dir or not os.path.isdir(target_dir) or not _git_binary():
        return {}
    if not _is_safe_path(target_dir):
        return {}

    repos: List[str] = []
    root, _ = _resolve_repo_root(target_dir, auto_init=False)
    if root:
        repos.append(root)
    else:
        try:
            for name in sorted(os.listdir(target_dir)):
                if name.startswith(".") or name in _SKIP_STATUS_PARTS:
                    continue
                sub = os.path.join(target_dir, name)
                if os.path.isdir(sub) and os.path.isdir(os.path.join(sub, ".git")):
                    sub_root, _ = _resolve_repo_root(sub, auto_init=False)
                    if sub_root:
                        repos.append(sub_root)
                if len(repos) >= 25:
                    break
        except OSError:
            pass

    statuses: Dict[str, str] = {}
    for repo in repos:
        rc, out, _ = _run_git(
            repo,
            ["-c", "core.quotePath=false", "status", "--porcelain=v1", "-uall", "-z"],
            timeout=10,
        )
        if rc == 0 and out:
            statuses.update(_parse_porcelain_z(repo, out))
    return statuses


def get_git_file_baseline(file_path: str, max_bytes: int = 524288) -> Dict[str, object]:
    """
    Resolves Git status letter (`M`/`U`/`A`/`D`/`R`/`""`) and baseline content
    (`HEAD`, staged index `:0:`, or latest Hecos checkpoint) for inline Monaco diff highlighting.
    """
    empty: Dict[str, object] = {"has_git": False, "status": "", "base_content": None, "base_label": ""}
    if not file_path or not os.path.exists(file_path) or not _git_binary():
        return empty
    repo_root, err = _resolve_repo_root(file_path, auto_init=False)
    if err or not repo_root:
        return empty

    try:
        rel_git = os.path.relpath(os.path.abspath(file_path), repo_root).replace("\\", "/")
    except ValueError:
        return empty

    rc_st, out_st, _ = _run_git(
        repo_root,
        ["-c", "core.quotePath=false", "status", "--porcelain=v1", "-uall", "-z", "--", rel_git],
        timeout=8,
    )
    status_code = ""
    if rc_st == 0 and out_st:
        parsed = _parse_porcelain_z(repo_root, out_st)
        norm_self = os.path.abspath(file_path).replace("\\", "/").lower()
        for k, v in parsed.items():
            if k.lower() == norm_self:
                status_code = v
                break

    candidates: List[Tuple[str, str]] = [
        (f"HEAD:{rel_git}", "HEAD"),
        (f":0:{rel_git}", "Staged"),
    ]
    cp_ref = _resolve_checkpoint_ref(repo_root, "latest")
    if cp_ref and cp_ref != "latest":
        candidates.append((f"{cp_ref}:{rel_git}", "Checkpoint"))

    base_content: Optional[str] = None
    base_label = ""
    for spec, label in candidates:
        rc_b, out_b, _ = _run_git(repo_root, ["show", spec], timeout=8)
        if rc_b == 0:
            if len(out_b.encode("utf-8", errors="ignore")) <= max_bytes:
                base_content = out_b
                base_label = label
            break

    return {
        "has_git": True,
        "status": status_code,
        "base_content": base_content,
        "base_label": base_label,
    }


def git_commit_tool(repo_path: str, message: str = "chore: commit from Hecos IDE") -> Dict[str, object]:
    """
    Stages all working-tree changes and creates a clean Git commit inside an existing
    or newly initialized project repository.
    """
    root, err = _resolve_repo_root(repo_path, auto_init=True)
    if err or not root:
        return {"ok": False, "message": err or "Git repository unavailable."}

    clean_msg = (message or "").strip()[:200] or "chore: commit from Hecos IDE"
    rc_add, _, err_add = _run_git(root, ["add", "-A"], timeout=15)
    if rc_add != 0:
        return {"ok": False, "message": f"git add failed: {err_add.strip()}"}

    # Check if there is anything staged (or empty repo)
    rc_diff, _, _ = _run_git(root, ["diff", "--cached", "--quiet"], timeout=8)
    rc_head, _, _ = _run_git(root, ["rev-parse", "--verify", "HEAD"], timeout=8)
    if rc_diff == 0 and rc_head == 0:
        return {"ok": True, "nothing_to_commit": True, "message": "Working tree clean — nothing to commit."}

    commit_env = {}
    rc_un, un_out, _ = _run_git(root, ["config", "user.name"], timeout=5)
    if rc_un != 0 or not un_out.strip():
        commit_env["GIT_AUTHOR_NAME"] = "Hecos Developer"
        commit_env["GIT_COMMITTER_NAME"] = "Hecos Developer"
    rc_ue, ue_out, _ = _run_git(root, ["config", "user.email"], timeout=5)
    if rc_ue != 0 or not ue_out.strip():
        commit_env["GIT_AUTHOR_EMAIL"] = "developer@hecos.local"
        commit_env["GIT_COMMITTER_EMAIL"] = "developer@hecos.local"

    rc_cm, out_cm, err_cm = _run_git(root, ["commit", "-m", clean_msg], timeout=15, extra_env=commit_env)
    if rc_cm != 0:
        return {"ok": False, "message": f"git commit failed: {(err_cm or out_cm).strip()}"}

    rc_sha, sha_out, _ = _run_git(root, ["rev-parse", "--short", "HEAD"], timeout=5)
    short_sha = sha_out.strip() if rc_sha == 0 else ""
    logger.info(f"[GIT] Committed {short_sha or 'HEAD'} in {root}: {clean_msg}")
    return {"ok": True, "sha": short_sha, "message": f"Committed {short_sha}: {clean_msg}"}
