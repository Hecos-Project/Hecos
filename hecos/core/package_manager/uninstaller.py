"""
uninstaller.py
─────────────────────────────────────────────────────────────────────────────
Hecos Package Manager — Package Uninstaller

Removes all artefacts of an installed package cleanly:
  1. Read the manifest snapshot and file list from the registry
  2. Remove all tracked files from disk
  3. Remove empty directories left behind
  4. Unregister from the SQLite registry
  5. Hot-reload the capability registry
  6. Emit hpm:package_removed event for frontend live update
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Callable

from hecos.core.logging import logger
from .registry import PackageRegistry


@dataclass
class UninstallResult:
    success: bool = False
    package_id: str = ""
    error: str = ""
    removed_files: List[str] = field(default_factory=list)
    skipped_files: List[str] = field(default_factory=list)


class PackageUninstaller:
    """
    Removes a package that was installed via HPM.

    Usage:
        uninstaller = PackageUninstaller(hecos_root, registry)
        result = uninstaller.uninstall("mail")
    """

    def __init__(
        self,
        hecos_root: str,
        registry: PackageRegistry,
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ):
        self._hecos_root = hecos_root
        self._registry = registry
        self._event_callback = event_callback

    # ── Public API ───────────────────────────────────────────────────────────

    def uninstall(self, pkg_id: str) -> UninstallResult:
        """
        Uninstall a package by its id.

        Args:
            pkg_id: The package identifier (e.g. 'mail', 'my_plugin').
        """
        result = UninstallResult(package_id=pkg_id)

        # ── Step 1: Verify it's installed ────────────────────────────────────
        record = self._registry.get(pkg_id)
        if not record:
            result.error = f"Package '{pkg_id}' is not registered in the HPM registry."
            logger.error(f"[HPM:Uninstaller] {result.error}")
            return result

        manifest = record.get("manifest_snapshot") or {}
        pkg_name = record.get("name", pkg_id)

        # ── Step 2: Remove tracked files ─────────────────────────────────────
        tracked_files = self._registry.get_installed_files(pkg_id)
        if tracked_files:
            self._remove_files(tracked_files, result)
        else:
            # Fallback: remove by install_path if no file list (legacy or partial)
            install_path = record.get("install_path", "")
            if install_path and os.path.isdir(install_path):
                logger.warning(
                    f"[HPM:Uninstaller] No file list for '{pkg_id}', "
                    f"removing install dir: {install_path}"
                )
                self._remove_directory(install_path, result)

        # ── Step 3: Remove WebUI assets (templates, static, widgets) ─────────
        self._remove_webui_assets(manifest, result)

        # ── Step 3b: Uninstall pip dependencies ──────────────────────────────
        pip_isolation = manifest.get("pip_isolation", "shared")
        pip_requirements = manifest.get("pip_requirements", [])

        if pip_isolation == "isolated":
            # Isolated packages have a self-contained venv inside install_path.
            # It will be wiped entirely at Step 4 with shutil.rmtree — nothing to do here.
            if pip_requirements:
                logger.info(
                    f"[HPM:Uninstaller] '{pkg_id}' uses isolated venv — "
                    f"pip deps will be removed with the venv directory at Step 4."
                )
                self._emit("hpm:progress", {
                    "step": "pip_remove",
                    "message": "Isolated venv will be removed with package directory..."
                })

        elif pip_isolation == "shared" and pip_requirements:
            import sys
            import subprocess

            self._emit("hpm:progress", {
                "step": "pip_remove",
                "message": "Checking shared pip dependencies to remove..."
            })
            from .dependency_resolver import DependencyResolver
            resolver = DependencyResolver(self._registry)
            safe_to_remove = resolver.get_safe_to_uninstall_pip_deps(pip_requirements, pkg_id)

            # Log what's being kept and why
            kept = [
                req for req in pip_requirements
                if req.strip() and not req.strip().startswith("#")
                and req not in safe_to_remove
            ]
            for req in kept:
                logger.info(
                    f"[HPM:Uninstaller] Keeping pip dep '{req}' "
                    f"(still required by Hecos core or another installed package)."
                )
                self._emit("hpm:progress", {"step": "pip_log", "message": f"Keeping: {req} (in use)"})

            if safe_to_remove:
                logger.info(f"[HPM:Uninstaller] Removing pip dependencies: {safe_to_remove}")
                self._emit("hpm:progress", {
                    "step": "pip_remove",
                    "message": f"Removing {len(safe_to_remove)} pip package(s)..."
                })
                cmd = [sys.executable, "-m", "pip", "uninstall", "-y"] + safe_to_remove
                try:
                    proc = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1
                    )
                    for line in iter(proc.stdout.readline, ""):
                        if line:
                            line_clean = line.strip()
                            if line_clean:
                                logger.debug(f"[HPM:Uninstaller] pip: {line_clean}")
                                self._emit("hpm:progress", {"step": "pip_log", "message": line_clean})
                    proc.stdout.close()
                    retcode = proc.wait(timeout=120)
                    if retcode == 0:
                        logger.info(f"[HPM:Uninstaller] ✅ Removed pip deps: {safe_to_remove}")
                    else:
                        logger.warning(
                            f"[HPM:Uninstaller] pip uninstall exited with code {retcode} for: {safe_to_remove}"
                        )
                except subprocess.TimeoutExpired:
                    proc.kill()
                    logger.warning("[HPM:Uninstaller] pip uninstall timed out.")
                except Exception as e:
                    logger.warning(f"[HPM:Uninstaller] Error uninstalling pip dependencies: {e}")
            else:
                logger.info(
                    f"[HPM:Uninstaller] No pip deps to remove for '{pkg_id}' "
                    f"(all are still required by Hecos core or other packages)."
                )
                self._emit("hpm:progress", {"step": "pip_log", "message": "No pip packages to remove (all in use)"})


        # ── Step 4: Remove empty leftover directories and wipe install_path ──
        install_path = record.get("install_path", "")
        if install_path and os.path.isdir(install_path):
            import shutil
            logger.info(f"[HPM:Uninstaller] Wiping remaining install directory (including venv): {install_path}")
            shutil.rmtree(install_path, ignore_errors=True)
            
        self._cleanup_empty_dirs(result.removed_files)

        # ── Step 5: Unregister from DB ────────────────────────────────────────
        ok = self._registry.unregister(pkg_id)
        if not ok:
            result.error = f"Package '{pkg_id}' unregistered from files but DB removal failed."
            logger.error(f"[HPM:Uninstaller] {result.error}")
            # Don't return False here — the files are already removed.

        # ── Step 6: Hot-reload ────────────────────────────────────────────────
        self._hot_reload()

        # ── Step 7: Emit event ────────────────────────────────────────────────
        config_panel = manifest.get("config_panel") or {}
        self._emit("hpm:package_removed", {
            "id": pkg_id,
            "name": pkg_name,
            "config_panel_tab_id": config_panel.get("tab_id"),
        })

        result.success = True
        logger.info(
            f"[HPM:Uninstaller] ✅ Package '{pkg_name}' uninstalled. "
            f"Removed {len(result.removed_files)} files."
        )
        return result

    # ── Private: File Removal ─────────────────────────────────────────────────

    @staticmethod
    def _remove_files(file_list: List[str], result: UninstallResult) -> None:
        for fp in file_list:
            try:
                if os.path.isfile(fp):
                    os.remove(fp)
                    result.removed_files.append(fp)
                    logger.debug(f"[HPM:Uninstaller] Removed: {fp}")
                else:
                    result.skipped_files.append(fp)
            except Exception as e:
                logger.error(f"[HPM:Uninstaller] Could not remove '{fp}': {e}")
                result.skipped_files.append(fp)

    @staticmethod
    def _remove_directory(path: str, result: UninstallResult) -> None:
        """Remove an entire directory (used as fallback when no file list is available)."""
        import shutil
        try:
            shutil.rmtree(path)
            result.removed_files.append(path)
        except Exception as e:
            logger.error(f"[HPM:Uninstaller] Could not remove directory '{path}': {e}")

    def _remove_webui_assets(self, manifest: dict, result: UninstallResult) -> None:
        """
        Remove WebUI assets not tracked in the file list (e.g. from old installs
        or if the file list is incomplete). Uses manifest config_panel to locate files.
        """
        webui_base = os.path.join(self._hecos_root, "modules", "web_ui")

        config_panel = manifest.get("config_panel") or {}
        template_file = config_panel.get("template_file", "")
        js_file = config_panel.get("js_file", "")
        css_file = config_panel.get("css_file", "")

        # The template_file in the manifest is relative to the zip root
        # (e.g. "web_ui/templates/config_myplugin.html").
        # On disk it maps to modules/web_ui/templates/modules/<filename>
        for asset_path in [template_file, js_file, css_file]:
            if not asset_path:
                continue
            # Extract just the filename — it was copied flat into the target dir
            filename = os.path.basename(asset_path)
            # Search in templates/modules/ and static/js/ and static/css/
            candidates = [
                os.path.join(webui_base, "templates", "modules", filename),
                os.path.join(webui_base, "static", "js", filename),
                os.path.join(webui_base, "static", "css", filename),
            ]
            for candidate in candidates:
                if os.path.isfile(candidate) and candidate not in result.removed_files:
                    try:
                        os.remove(candidate)
                        result.removed_files.append(candidate)
                        logger.debug(f"[HPM:Uninstaller] Removed WebUI asset: {candidate}")
                    except Exception as e:
                        logger.error(f"[HPM:Uninstaller] Could not remove '{candidate}': {e}")

        # Remove widget extension directories
        widgets = manifest.get("widgets") or []
        for w in widgets:
            ext_path = w.get("extension_path", "")
            if ext_path:
                widget_name = os.path.basename(ext_path.rstrip("/"))
                ext_dir = os.path.join(webui_base, "extensions", widget_name)
                if os.path.isdir(ext_dir):
                    self._remove_directory(ext_dir, result)

    @staticmethod
    def _cleanup_empty_dirs(removed_files: List[str]) -> None:
        """Remove any directories that became empty after file removal, including untracked __pycache__."""
        import shutil
        seen_dirs = set()
        
        # Build the set of all ancestor directories for the removed files
        for fp in removed_files:
            curr = os.path.dirname(fp)
            # Walk up a few levels to ensure we clean parent dirs (e.g., hpm/pkg_name)
            # but stop before we hit the root of the filesystem.
            for _ in range(5):
                if curr and os.path.basename(curr):
                    seen_dirs.add(curr)
                    curr = os.path.dirname(curr)
                else:
                    break

        # Sort deepest first so we clean bottom-up
        for d in sorted(seen_dirs, key=len, reverse=True):
            try:
                if os.path.isdir(d):
                    # 1. Purge untracked __pycache__ aggressively
                    pycache = os.path.join(d, "__pycache__")
                    if os.path.isdir(pycache):
                        shutil.rmtree(pycache)
                        
                    # 2. Remove any orphaned .pyc files (e.g. from Python < 3.2 or manual compilation)
                    for f in os.listdir(d):
                        if f.endswith(".pyc"):
                            os.remove(os.path.join(d, f))

                    # 3. If directory is now completely empty, remove it
                    if not os.listdir(d):
                        os.rmdir(d)
                        logger.debug(f"[HPM:Uninstaller] Removed empty dir: {d}")
            except Exception:
                pass  # Non-critical

    # ── Private: Hot-Reload ──────────────────────────────────────────────────

    def _hot_reload(self) -> None:
        try:
            from hecos.core.system import module_loader
            from hecos.app.config import ConfigManager
            cfg = ConfigManager().config
            module_loader.update_capability_registry(cfg, debug_log=False)
            logger.info("[HPM:Uninstaller] Capability registry hot-reloaded.")
        except Exception as e:
            logger.warning(f"[HPM:Uninstaller] Hot-reload failed (non-critical): {e}")

    # ── Private: Event ─────────────────────────────────────────────────────────

    def _emit(self, event_name: str, payload: Dict[str, Any]) -> None:
        if callable(self._event_callback):
            try:
                self._event_callback(event_name, payload)
            except Exception as e:
                logger.debug(f"[HPM:Uninstaller] Event callback failed: {e}")
