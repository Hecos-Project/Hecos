"""
installer.py
─────────────────────────────────────────────────────────────────────────────
Hecos Package Manager — Atomic Package Installer

Installs a .hpkg package with full rollback on any failure.

Install Pipeline:
  1.  Validate the .hpkg (schema, checksum, security)
  2.  Resolve & install dependencies (pip + inter-package)
  3.  Extract ZIP to a staging temp directory
  4.  Run install_hooks.py::pre_install() if present
  5.  Copy plugin/module code to target directory
  6.  Copy WebUI assets (templates, static JS/CSS)
  7.  Copy widget extensions to web_ui/extensions/
  8.  Copy i18n files
  9.  Register package in the SQLite registry
  10. Hot-reload Hecos capability registry (no restart needed)
  11. Run install_hooks.py::post_install() if present
  12. Emit hpm:package_installed event for frontend live update

On any error between steps 5-11: full rollback (all copied files removed).
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import importlib.util
import io
import os
import shutil
import sys
import tempfile
import zipfile
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Callable

from hecos.core.logging import logger
from .package_schema import HpkgManifest
from .registry import PackageRegistry
from .validator import PackageValidator
from .dependency_resolver import DependencyResolver, DependencyReport
from .signature import SignatureVerifier


@dataclass
class InstallResult:
    success: bool = False
    package_id: str = ""
    error: str = ""
    warnings: List[str] = field(default_factory=list)
    dep_report: Optional[DependencyReport] = None

    @property
    def has_warnings(self) -> bool:
        return bool(self.warnings)


class PackageInstaller:
    """
    Atomic installer for .hpkg packages.

    Usage:
        installer = PackageInstaller(
            hecos_root="/path/to/hecos",
            registry=registry,
            hecos_version="0.35.0",
        )
        result = installer.install_bytes(hpkg_bytes)
        if result.success:
            print(f"Installed {result.package_id}")
    """

    def __init__(
        self,
        hecos_root: str,
        registry: PackageRegistry,
        hecos_version: str = "0.35.0",
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ):
        """
        Args:
            hecos_root:      Absolute path to the hecos/ directory.
            registry:        Initialized PackageRegistry instance.
            hecos_version:   Current Hecos version string.
            event_callback:  Optional function(event_name, payload) for SSE/WS notifications.
        """
        self._hecos_root = hecos_root
        self._registry = registry
        self._version = hecos_version
        self._event_callback = event_callback

        self._validator = PackageValidator(hecos_version)
        
        keys_dir = os.path.join(hecos_root, "data", "trusted_keys")
        self._sig_verifier = SignatureVerifier(keys_dir)

    # ── Public API ───────────────────────────────────────────────────────────

    def install_file(self, hpkg_path: str, require_signature: bool = True) -> InstallResult:
        """Install from a file path."""
        try:
            with open(hpkg_path, "rb") as f:
                data = f.read()
            return self.install_bytes(data, require_signature=require_signature)
        except Exception as e:
            return InstallResult(success=False, error=f"Cannot read file: {e}")

    def install_bytes(self, data: bytes, require_signature: bool = True) -> InstallResult:
        """Install from raw .hpkg bytes. Main entry point."""

        # ── Step 1: Validate ─────────────────────────────────────────────────
        val_result = self._validator.validate_bytes(data)
        if not val_result.valid:
            return InstallResult(
                success=False,
                error=f"Validation failed: {val_result.error_summary}"
            )

        manifest = val_result.manifest
        result = InstallResult(package_id=manifest.id)

        # ── Step 2: Signature check ──────────────────────────────────────────
        # We verify the manifest mathematically against trusted public keys using the RAW json
        # to ensure no Pydantic defaults alter the canonical payload.
        import tomllib
        import json
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            try:
                raw_manifest_bytes = zf.read("hpkg_manifest.toml")
                raw_manifest_dict = tomllib.loads(raw_manifest_bytes.decode("utf-8"))
            except Exception as e:
                return InstallResult(success=False, error=f"Could not read manifest for signature check: {e}")

        is_valid = self._sig_verifier.verify_manifest(raw_manifest_dict, require_signature=require_signature)
        if not is_valid:
            return InstallResult(
                success=False,
                error="Signature verification failed. Package is untrusted or tampered with."
            )

        # ── Step 3: Dependency resolution ────────────────────────────────────
        resolver = DependencyResolver(self._registry)
        dep_report = resolver.resolve(manifest, install_pip=True)
        result.dep_report = dep_report

        if dep_report.missing_packages:
            result.warnings.append(
                f"Missing HPM packages (install them first): "
                f"{dep_report.missing_packages}"
            )

        if dep_report.pip_failures:
            result.warnings.append(
                f"Some pip requirements failed to install: "
                f"{dep_report.pip_failures}"
            )

        # ── Step 4: Extract to staging ───────────────────────────────────────
        staging_dir = tempfile.mkdtemp(prefix="hpm_staging_")
        installed_files: List[str] = []

        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                zf.extractall(staging_dir)

            # ── Step 4.5: File Hashes Verification ───────────────────────────
            # Ensure no files inside the zip were manipulated after signing
            import hashlib
            expected_hashes = manifest.file_hashes or {}
            
            # If the package is required to be signed, but file_hashes is empty, we must reject it
            # because the signature would only protect the manifest itself, not the code!
            if require_signature and not expected_hashes:
                raise RuntimeError("Manifest is missing file_hashes. Cannot guarantee integrity of extracted files.")

            for root, _, files in os.walk(staging_dir):
                for fname in files:
                    # Skip manifest.toml because it's the one containing the hashes and signature
                    if fname == "hpkg_manifest.toml":
                        continue
                        
                    fpath = os.path.join(root, fname)
                    rel_path = os.path.relpath(fpath, staging_dir).replace("\\", "/")
                    
                    if rel_path not in expected_hashes:
                        # Allow harmless files like .DS_Store, but warn. For strictness, we reject unknown files.
                        if fname in [".DS_Store", "Thumbs.db"]:
                            continue
                        if require_signature:
                            raise RuntimeError(f"Unknown file '{rel_path}' found in package. Integrity check failed.")
                        continue
                        
                    # Calculate hash
                    sha256 = hashlib.sha256()
                    with open(fpath, "rb") as bf:
                        for chunk in iter(lambda: bf.read(4096), b""):
                            sha256.update(chunk)
                    
                    if sha256.hexdigest() != expected_hashes[rel_path]:
                        raise RuntimeError(f"Hash mismatch for '{rel_path}'. File corrupted or tampered.")

            # ── Step 5: pre_install hook ─────────────────────────────────────
            self._run_hook(staging_dir, "pre_install", manifest)

            # ── Step 6: Copy plugin/module code ──────────────────────────────
            installed_files.extend(
                self._install_plugin_code(staging_dir, manifest)
            )

            # ── Step 7: Copy WebUI assets ─────────────────────────────────────
            installed_files.extend(
                self._install_webui_assets(staging_dir, manifest)
            )

            # ── Step 8: Copy widget extensions ───────────────────────────────
            installed_files.extend(
                self._install_widgets(staging_dir, manifest)
            )

            # ── Step 9: Copy i18n files ───────────────────────────────────────
            installed_files.extend(
                self._install_i18n(staging_dir, manifest)
            )

            # ── Step 10: Register in DB ───────────────────────────────────────
            install_path = os.path.join(
                self._hecos_root,
                manifest.target_dir,
                manifest.id
            )
            manifest_dict = manifest.model_dump()
            ok = self._registry.register(manifest_dict, install_path, installed_files)
            if not ok:
                raise RuntimeError("Failed to register package in the database.")

            # ── Step 10.5: Inject Config Defaults ─────────────────────────────
            self._inject_config_defaults(manifest)

            # ── Step 11: Hot-reload capability registry ───────────────────────
            self._hot_reload()

            # ── Step 12: post_install hook ────────────────────────────────────
            self._run_hook(staging_dir, "post_install", manifest)

            # ── Step 13: Emit event ───────────────────────────────────────────
            self._emit("hpm:package_installed", {
                "id": manifest.id,
                "name": manifest.name,
                "version": manifest.version,
                "type": manifest.type,
                "config_panel": manifest.config_panel.model_dump() if manifest.config_panel else None,
            })

            result.success = True
            logger.info(
                f"[HPM:Installer] ✅ Package '{manifest.name}' v{manifest.version} "
                f"installed successfully."
            )

        except Exception as e:
            logger.error(f"[HPM:Installer] Installation failed for '{manifest.id}': {e}")
            result.error = str(e)
            # Rollback: remove all files written to disk
            self._rollback(installed_files, manifest.id)

        finally:
            # Always clean up staging directory
            shutil.rmtree(staging_dir, ignore_errors=True)

        return result

    # ── Private: Install Steps ───────────────────────────────────────────────

    def _install_plugin_code(self, staging: str, manifest: HpkgManifest) -> List[str]:
        """Copy plugin/module Python code to the target directory."""
        plugin_dir_in_zip = manifest.plugin_dir or f"{manifest.id}/"
        plugin_src = os.path.join(staging, plugin_dir_in_zip.rstrip("/"))

        if not os.path.isdir(plugin_src):
            # Try fallback: source is named "plugin/" generically
            for candidate in ["plugin", "module", manifest.id]:
                candidate_path = os.path.join(staging, candidate)
                if os.path.isdir(candidate_path):
                    plugin_src = candidate_path
                    break
            else:
                logger.warning(
                    f"[HPM:Installer] No plugin code directory found in package '{manifest.id}'. "
                    f"Skipping code install."
                )
                return []

        target_base = os.path.join(self._hecos_root, manifest.target_dir)
        os.makedirs(target_base, exist_ok=True)
        target_dir = os.path.join(target_base, manifest.id)

        copied_files = self._copy_tree(plugin_src, target_dir)

        # Generate the runtime manifest.json inside the target directory
        runtime_manifest_path = os.path.join(target_dir, "manifest.json")
        runtime_manifest_data = {
            "tag": manifest.tag or manifest.id.upper(),
            "name": manifest.name,
            "version": manifest.version,
            "description": manifest.description,
            "lazy_load": manifest.lazy_load,
            "is_class_based": manifest.is_class_based,
            "commands": manifest.commands,
            "tool_schema": manifest.tool_schema,
            "slash_commands": manifest.slash_commands,
        }
        if manifest.config_panel:
            runtime_manifest_data["icon"] = manifest.config_panel.tab_icon
            
        import json
        with open(runtime_manifest_path, "w", encoding="utf-8") as f:
            json.dump(runtime_manifest_data, f, indent=4)
        
        copied_files.append(runtime_manifest_path)
        return copied_files

    def _install_webui_assets(self, staging: str, manifest: HpkgManifest) -> List[str]:
        """Copy HTML templates and JS/CSS assets to web_ui directories."""
        webui_src = os.path.join(staging, "web_ui")
        if not os.path.isdir(webui_src):
            return []

        webui_base = os.path.join(
            self._hecos_root, "modules", "web_ui"
        )

        installed: List[str] = []

        # templates/
        templates_src = os.path.join(webui_src, "templates")
        if os.path.isdir(templates_src):
            templates_dst = os.path.join(webui_base, "templates", "modules")
            installed.extend(self._copy_tree(templates_src, templates_dst))

        # static/
        static_src = os.path.join(webui_src, "static")
        if os.path.isdir(static_src):
            static_dst = os.path.join(webui_base, "static")
            installed.extend(self._copy_tree(static_src, static_dst))

        return installed

    def _install_widgets(self, staging: str, manifest: HpkgManifest) -> List[str]:
        """Copy widget extensions to web_ui/extensions/<widget_id>/."""
        if not manifest.widgets:
            return []

        installed: List[str] = []
        ext_base = os.path.join(
            self._hecos_root, "modules", "web_ui", "extensions"
        )
        os.makedirs(ext_base, exist_ok=True)

        for w in manifest.widgets:
            src = os.path.join(staging, w.extension_path.rstrip("/"))
            if not os.path.isdir(src):
                logger.warning(
                    f"[HPM:Installer] Widget source '{w.extension_path}' not found in package."
                )
                continue
            widget_name = os.path.basename(src)
            dst = os.path.join(ext_base, widget_name)
            installed.extend(self._copy_tree(src, dst))

        return installed

    def _install_i18n(self, staging: str, manifest: HpkgManifest) -> List[str]:
        """Copy i18n translation files."""
        i18n_src = os.path.join(staging, "i18n")
        if not os.path.isdir(i18n_src):
            return []

        i18n_dst = os.path.join(self._hecos_root, "core", "i18n", "locales")
        os.makedirs(i18n_dst, exist_ok=True)
        return self._copy_tree(i18n_src, i18n_dst)

    # ── Private: Hooks ───────────────────────────────────────────────────────

    @staticmethod
    def _run_hook(staging: str, hook_name: str, manifest: HpkgManifest) -> None:
        """Run pre_install / post_install hooks from install_hooks.py."""
        hooks_path = os.path.join(staging, "install_hooks.py")
        if not os.path.isfile(hooks_path):
            return
        try:
            spec = importlib.util.spec_from_file_location("hpm_hooks", hooks_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            fn = getattr(mod, hook_name, None)
            if callable(fn):
                fn(manifest.model_dump())
                logger.debug(f"[HPM:Installer] Hook '{hook_name}' executed for '{manifest.id}'.")
        except Exception as e:
            logger.warning(f"[HPM:Installer] Hook '{hook_name}' failed for '{manifest.id}': {e}")

    # ── Private: Hot-Reload ──────────────────────────────────────────────────

    def _inject_config_defaults(self, manifest: HpkgManifest) -> None:
        """Inject config defaults into plugins.yaml if not already present."""
        if not manifest.config_defaults:
            return

        try:
            from hecos.app.config import ConfigManager
            cfg_mgr = ConfigManager()
            tag = manifest.tag or manifest.id.upper()
            
            # Check existing config, if empty, inject
            existing = cfg_mgr.get_plugin_config(tag)
            
            needs_save = False
            for k, v in manifest.config_defaults.items():
                if existing.get(k) is None:
                    cfg_mgr.set_plugin_config(tag, k, v)
                    needs_save = True
            
            if needs_save:
                # Setting values inside the dict requires a save call,
                # though set_plugin_config already calls save(), it might be redundant
                # but it ensures the defaults are persisted.
                logger.info(f"[HPM:Installer] Injected default config for '{tag}'.")
        except Exception as e:
            logger.warning(f"[HPM:Installer] Failed to inject config defaults: {e}")

    def _hot_reload(self) -> None:
        """Re-run capability scanner so new module appears immediately."""
        try:
            from hecos.core.system import module_loader
            from hecos.app.config import ConfigManager
            cfg = ConfigManager().config
            module_loader.update_capability_registry(cfg, debug_log=False)
            logger.info("[HPM:Installer] Capability registry hot-reloaded.")
        except Exception as e:
            logger.warning(f"[HPM:Installer] Hot-reload failed (non-critical): {e}")

    # ── Private: Rollback ────────────────────────────────────────────────────

    @staticmethod
    def _rollback(installed_files: List[str], pkg_id: str) -> None:
        """Remove all files written during a failed installation."""
        logger.warning(
            f"[HPM:Installer] Rolling back installation of '{pkg_id}' "
            f"({len(installed_files)} files)..."
        )
        for fp in installed_files:
            try:
                if os.path.isfile(fp):
                    os.remove(fp)
            except Exception as e:
                logger.error(f"[HPM:Installer] Rollback: could not remove '{fp}': {e}")
        logger.info(f"[HPM:Installer] Rollback complete for '{pkg_id}'.")

    # ── Private: Event ────────────────────────────────────────────────────────

    def _emit(self, event_name: str, payload: Dict[str, Any]) -> None:
        if callable(self._event_callback):
            try:
                self._event_callback(event_name, payload)
            except Exception as e:
                logger.debug(f"[HPM:Installer] Event callback failed: {e}")

    # ── Private: File Copy ────────────────────────────────────────────────────

    @staticmethod
    def _copy_tree(src: str, dst: str) -> List[str]:
        """
        Recursively copy all files from src to dst.
        Returns a list of all destination file paths for rollback tracking.
        """
        copied: List[str] = []
        for root, _, files in os.walk(src):
            rel = os.path.relpath(root, src)
            dest_dir = os.path.join(dst, rel) if rel != "." else dst
            os.makedirs(dest_dir, exist_ok=True)
            for fname in files:
                src_file = os.path.join(root, fname)
                dst_file = os.path.join(dest_dir, fname)
                shutil.copy2(src_file, dst_file)
                copied.append(dst_file)
        return copied
