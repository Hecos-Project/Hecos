"""
Hecos Setup - Dependency Guard, Fast Pre-Check & Reproducible Constraints Lockfile
Prevents unnecessary pip runs and surprise upstream upgrades on already-configured
machines while keeping fresh installations reproducible via constraints.txt.
"""

from __future__ import annotations

import datetime
import glob
import importlib.metadata as md
import os
import re
import subprocess
import sys
from typing import List, Optional, Tuple

from .utils import CWD, parse_pyproject_dependencies

CONSTRAINTS_PATH = os.path.join(CWD, "constraints.txt")

# Key transitive runtime libraries pinned alongside direct deps in constraints.txt
# (only clean PyPI versions — never local CUDA tags like +cu128).
KEY_TRANSITIVE_PINS = (
    "httpx",
    "openai",
    "werkzeug",
    "jinja2",
    "greenlet",
    "pyee",
    "onnxruntime",
    "huggingface-hub",
    "transformers",
    "tokenizers",
    "pyarrow",
    "tiktoken",
    "typing-extensions",
    "pydantic-core",
)


def _eval_marker_fallback(marker_str: str) -> bool:
    """Minimal fallback evaluator for simple sys_platform markers when `packaging` is absent."""
    m = marker_str.strip()
    if "sys_platform" in m:
        match = re.search(r"sys_platform\s*(==|!=)\s*['\"]([^'\"]+)['\"]", m)
        if match:
            op, target = match.group(1), match.group(2)
            return (sys.platform == target) if op == "==" else (sys.platform != target)
    return True


def _parse_version_tuple(ver_str: str) -> Tuple[int, ...]:
    nums = re.findall(r"\d+", ver_str.split("+")[0])
    return tuple(int(x) for x in nums[:4]) if nums else (0,)


def _check_spec_installed(spec: str) -> Tuple[bool, str]:
    """Return (is_satisfied, reason).

    Evaluates environment markers (e.g. `; sys_platform=='win32'`) and version
    specifiers using `packaging` when available, with a safe stdlib fallback.
    """
    try:
        from packaging.requirements import Requirement
        from packaging.version import Version

        req = Requirement(spec)
        if req.marker and not req.marker.evaluate():
            return True, "marker-skipped"
        try:
            installed_ver = md.version(req.name)
        except md.PackageNotFoundError:
            return False, "missing"
        if req.specifier and not req.specifier.contains(Version(installed_ver), prereleases=True):
            return False, f"version {installed_ver} outside {req.specifier}"
        return True, installed_ver
    except ImportError:
        # Fallback when `packaging` is not installed yet
        parts = spec.split(";", 1)
        req_part = parts[0].strip()
        if len(parts) == 2 and not _eval_marker_fallback(parts[1]):
            return True, "marker-skipped"
        name = re.split(r"[\[\]>=<~!@]", req_part)[0].strip()
        try:
            installed_ver = md.version(name)
            return True, installed_ver
        except md.PackageNotFoundError:
            return False, "missing"
    except Exception:
        name = re.split(r"[\[\];>=<~!@]", spec)[0].strip()
        try:
            return True, md.version(name)
        except md.PackageNotFoundError:
            return False, "missing"


def find_missing_dependencies(
    toml_path: Optional[str] = None,
    extras: Tuple[str, ...] = ("service",),
) -> Tuple[List[str], List[str]]:
    """Fast (<0.2s) pre-pip check of all dependencies declared in pyproject.toml.

    Returns:
        (satisfied_specs, missing_or_incompatible_specs)
    """
    path = toml_path or os.path.join(CWD, "pyproject.toml")
    specs = parse_pyproject_dependencies(path, extras=extras)
    satisfied: List[str] = []
    missing: List[str] = []

    for spec in specs:
        ok, _ = _check_spec_installed(spec)
        if ok:
            satisfied.append(spec)
        else:
            missing.append(spec)

    return satisfied, missing


def is_playwright_chromium_installed() -> bool:
    """Fast (<10ms) check for whether Playwright Chromium binaries already exist on disk."""
    custom_dir = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    candidates: List[str] = []
    if custom_dir and custom_dir != "0":
        candidates.append(custom_dir)

    if os.name == "nt":
        local_app = os.environ.get("LOCALAPPDATA") or os.path.join(
            os.path.expanduser("~"), "AppData", "Local"
        )
        candidates.append(os.path.join(local_app, "ms-playwright"))
    elif sys.platform == "darwin":
        candidates.append(os.path.expanduser("~/Library/Caches/ms-playwright"))
    else:
        candidates.append(os.path.expanduser("~/.cache/ms-playwright"))

    for base in candidates:
        if not os.path.isdir(base):
            continue
        for folder in glob.glob(os.path.join(base, "chromium-*")):
            if not os.path.isdir(folder):
                continue
            # Check typical Playwright Chromium executable locations
            for rel in (
                os.path.join("chrome-win", "chrome.exe"),
                os.path.join("chrome-win64", "chrome.exe"),
                os.path.join("chrome-linux", "chrome"),
                os.path.join("chrome-linux64", "chrome"),
                os.path.join("chrome-mac", "Chromium.app"),
                os.path.join("chrome-mac-arm64", "Chromium.app"),
            ):
                if os.path.exists(os.path.join(folder, rel)):
                    return True
    return False


def ensure_build_tools(quiet: bool = False) -> None:
    """Ensure pip, setuptools (<82), and wheel exist WITHOUT blindly upgrading working versions."""
    pip_base = [sys.executable, "-m", "pip", "install"]
    if quiet:
        pip_base.append("--quiet")

    to_install: List[str] = []

    # Only upgrade pip if it is very old (< 23.0)
    try:
        pip_ver = _parse_version_tuple(md.version("pip"))
        if pip_ver < (23, 0):
            to_install.append("pip>=24.0")
    except md.PackageNotFoundError:
        pass

    # Only install setuptools if missing (capped <82 to preserve pkg_resources compatibility)
    try:
        md.version("setuptools")
    except md.PackageNotFoundError:
        to_install.append("setuptools>=68,<82")

    # Only install wheel if missing
    try:
        md.version("wheel")
    except md.PackageNotFoundError:
        to_install.append("wheel")

    if to_install:
        try:
            subprocess.check_call(pip_base + to_install)
        except Exception as e:
            print(f"[WARN] Could not ensure build tools ({', '.join(to_install)}): {e}")


def generate_constraints_lock(
    toml_path: Optional[str] = None,
    output_path: Optional[str] = None,
    extras: Tuple[str, ...] = ("service",),
) -> Tuple[int, str]:
    """Snapshot currently tested, clean PyPI versions into constraints.txt.

    Preserves platform markers (e.g. `pywin32==312; sys_platform == 'win32'`)
    and excludes local CUDA builds (versions containing `+`, e.g. `+cu128`) so
    the lockfile stays portable across CPU, CUDA, Windows, and Linux installs.
    """
    tpath = toml_path or os.path.join(CWD, "pyproject.toml")
    opath = output_path or CONSTRAINTS_PATH

    specs = parse_pyproject_dependencies(tpath, extras=extras)
    lines: List[str] = [
        "# Hecos Core - Tested Dependency Constraints Lockfile",
        f"# Generated: {datetime.datetime.now().replace(microsecond=0).isoformat()} "
        f"(Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro})",
        "# Regenerate after testing library updates: python hecos/setup_wizard.py lock",
        "# Used automatically via `pip install -c constraints.txt` (with graceful fallback",
        "# to pyproject.toml safe ranges if a pinned wheel is unavailable on another OS).",
        "",
        "# Build tooling safety cap (keeps pkg_resources available for legacy deps)",
        "setuptools>=68,<82",
        "",
        "# Direct Hecos Core & Service dependencies",
    ]

    seen = {"setuptools"}
    pin_count = 1

    for spec in specs:
        parts = spec.split(";", 1)
        marker = f"; {parts[1].strip()}" if len(parts) == 2 else ""
        name = re.split(r"[\[\]>=<~!@]", parts[0])[0].strip()
        key = name.lower().replace("_", "-")
        if not name or key in seen:
            continue
        try:
            ver = md.version(name)
        except md.PackageNotFoundError:
            continue
        # Skip local/CUDA-suffixed versions (e.g. 2.11.0+cu128) for cross-platform safety
        if "+" in ver:
            continue
        seen.add(key)
        lines.append(f"{name}=={ver}{marker}")
        pin_count += 1

    lines.append("")
    lines.append("# Key transitive runtime libraries")
    for name in KEY_TRANSITIVE_PINS:
        key = name.lower().replace("_", "-")
        if key in seen:
            continue
        try:
            ver = md.version(name)
        except md.PackageNotFoundError:
            continue
        if "+" in ver:
            continue
        seen.add(key)
        lines.append(f"{name}=={ver}")
        pin_count += 1

    content = "\n".join(lines) + "\n"
    with open(opath, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)

    return pin_count, opath
