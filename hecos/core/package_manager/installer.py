"""
installer.py
─────────────────────────────────────────────────────────────────────────────
Hecos Package Manager — Atomic Package Installer
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import io
import os
import shutil
import tempfile
import zipfile
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Callable

from hecos.core.logging import logger
from .registry import PackageRegistry
from .validator import PackageValidator
from .dependency_resolver import DependencyResolver, DependencyReport
from .signature import SignatureVerifier

from .installer_hooks import run_hook, inject_config_defaults, hot_reload
from .installer_steps import (
    install_plugin_code,
    install_webui_assets,
    install_widgets,
    install_i18n,
    install_docs,
    rollback,
    _resolve_target_dir
)

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
    """

    def __init__(
        self,
        hecos_root: str,
        registry: PackageRegistry,
        hecos_version: str = "0.35.0",
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        cfg_mgr = None,
    ):
        self._hecos_root = hecos_root
        self._registry = registry
        self._version = hecos_version
        self._event_callback = event_callback
        self._cfg_mgr = cfg_mgr

        # Read HPM config or fallback
        hpm_cfg = {}
        if cfg_mgr and hasattr(cfg_mgr, "config"):
            hpm_cfg = cfg_mgr.config.get("hpm", {})
            
        self._allow_unsigned_global = hpm_cfg.get("allow_unsigned_packages", False)

        self._validator = PackageValidator(hecos_version)
        
        # Override trusted_keys_dir if specified in config
        keys_dir = hpm_cfg.get("trusted_keys_dir")
        if not keys_dir:
            keys_dir = os.path.join(hecos_root, "data", "trusted_keys")
        self._sig_verifier = SignatureVerifier(keys_dir)

    def install_file(self, hpkg_path: str, require_signature: bool = True, skip_dep_check: bool = False) -> InstallResult:
        try:
            with open(hpkg_path, "rb") as f:
                data = f.read()
            return self.install_bytes(data, require_signature=require_signature, skip_dep_check=skip_dep_check)
        except Exception as e:
            return InstallResult(success=False, error=f"Cannot read file: {e}")

    def install_bytes(self, data: bytes, require_signature: bool = True, skip_dep_check: bool = False) -> InstallResult:
        # ── Step 1: Validate ─────────────────────────────────────────────────
        self._emit("hpm:progress", {"step": "validation", "message": "Validating package schema..."})
        val_result = self._validator.validate_bytes(data)
        if not val_result.valid:
            return InstallResult(success=False, error=f"Validation failed: {val_result.error_summary}")

        manifest = val_result.manifest
        result = InstallResult(package_id=manifest.id)

        # ── Step 2: Signature check ──────────────────────────────────────────
        self._emit("hpm:progress", {"step": "signature", "message": "Verifying package signature..."})
        import tomllib
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            try:
                raw_manifest_bytes = zf.read("hpkg_manifest.toml")
                raw_manifest_dict = tomllib.loads(raw_manifest_bytes.decode("utf-8"))
            except Exception as e:
                return InstallResult(success=False, error=f"Could not read manifest for signature check: {e}")

        req_sig = require_signature and not self._allow_unsigned_global
        is_valid = self._sig_verifier.verify_manifest(raw_manifest_dict, require_signature=req_sig)
        if not is_valid:
            return InstallResult(success=False, error="Signature verification failed. Package is untrusted or tampered with.")

        # ── Step 3: Dependency resolution ────────────────────────────────────
        self._emit("hpm:progress", {"step": "dependencies", "message": "Resolving dependencies..."})
        
        # Calculate install path early to pass to the resolver (needed for venv creation)
        target_dir_name = _resolve_target_dir(manifest) or manifest.target_dir
        install_path = os.path.join(self._hecos_root, target_dir_name, manifest.id)
        
        resolver = DependencyResolver(self._registry)
        dep_report = resolver.resolve(manifest, install_pip=not skip_dep_check, install_path=install_path)
        result.dep_report = dep_report

        if dep_report.missing_packages:
            if not skip_dep_check:
                return InstallResult(
                    success=False,
                    error=f"Missing required HPM packages: {', '.join(dep_report.missing_packages)}. Please install them first.",
                    dep_report=dep_report,
                )
            else:
                result.warnings.append(f"Installed without required HPM packages: {dep_report.missing_packages}")
                logger.warning(f"[HPM:Installer] Forced install — missing HPM deps: {dep_report.missing_packages}")
            
        if dep_report.pip_failures:
            result.warnings.append(f"Some pip requirements failed to install: {dep_report.pip_failures}")

        # ── Step 4: Extract to staging ───────────────────────────────────────
        self._emit("hpm:progress", {"step": "extract", "message": "Extracting package files..."})
        staging_dir = tempfile.mkdtemp(prefix="hpm_staging_")
        installed_files: List[str] = []

        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                zf.extractall(staging_dir)

            # ── Step 4.5: File Hashes Verification ───────────────────────────
            self._emit("hpm:progress", {"step": "hash_check", "message": "Verifying file integrity..."})
            import hashlib
            expected_hashes = manifest.file_hashes or {}
            
            if req_sig and not expected_hashes:
                raise RuntimeError("Manifest is missing file_hashes. Cannot guarantee integrity of extracted files.")

            for root, _, files in os.walk(staging_dir):
                for fname in files:
                    if fname == "hpkg_manifest.toml":
                        continue
                        
                    fpath = os.path.join(root, fname)
                    rel_path = os.path.relpath(fpath, staging_dir).replace("\\", "/")
                    
                    if rel_path not in expected_hashes:
                        if fname in [".DS_Store", "Thumbs.db"]:
                            continue
                        if req_sig:
                            raise RuntimeError(f"Unknown file '{rel_path}' found in package. Integrity check failed.")
                        continue
                        
                    sha256 = hashlib.sha256()
                    with open(fpath, "rb") as bf:
                        for chunk in iter(lambda: bf.read(4096), b""):
                            sha256.update(chunk)
                    
                    if sha256.hexdigest() != expected_hashes[rel_path]:
                        raise RuntimeError(f"Hash mismatch for '{rel_path}'. File corrupted or tampered.")

            # ── Step 5: pre_install hook ─────────────────────────────────────
            self._emit("hpm:progress", {"step": "hooks", "message": "Running pre-install hook..."})
            run_hook(staging_dir, "pre_install", manifest)

            # ── Step 6: Copy plugin/module code ──────────────────────────────
            self._emit("hpm:progress", {"step": "copy_code", "message": "Installing core logic..."})
            installed_files.extend(install_plugin_code(staging_dir, manifest, self._hecos_root))

            # ── Step 7: Copy WebUI assets ─────────────────────────────────────
            installed_files.extend(install_webui_assets(staging_dir, manifest, self._hecos_root))

            # ── Step 8: Copy widget extensions ───────────────────────────────
            installed_files.extend(install_widgets(staging_dir, manifest, self._hecos_root))

            # ── Step 9: Copy i18n files ───────────────────────────────────────
            installed_files.extend(install_i18n(staging_dir, manifest, self._hecos_root))

            # ── Step 9.5: Copy documentation files ────────────────────────────
            installed_files.extend(install_docs(staging_dir, manifest, self._hecos_root))

            # ── Step 10: Register in DB ───────────────────────────────────────
            self._emit("hpm:progress", {"step": "register", "message": "Registering in database..."})
            manifest_dict = manifest.model_dump()
            ok = self._registry.register(manifest_dict, install_path, installed_files)
            if not ok:
                raise RuntimeError("Failed to register package in the database.")

            # ── Step 10.5: Inject Config Defaults ─────────────────────────────
            inject_config_defaults(manifest)

            # ── Step 11: Hot-reload capability registry ───────────────────────
            hot_reload(self._hecos_root)

            # ── Step 12: post_install hook ────────────────────────────────────
            self._emit("hpm:progress", {"step": "hooks", "message": "Running post-install hook..."})
            run_hook(staging_dir, "post_install", manifest)

            # ── Step 13: Emit event ───────────────────────────────────────────
            self._emit("hpm:package_installed", {
                "id": manifest.id,
                "name": manifest.name,
                "version": manifest.version,
                "type": manifest.type,
                "config_panel": manifest.config_panel.model_dump() if manifest.config_panel else None,
            })

            result.success = True
            logger.info(f"[HPM:Installer] ✅ Package '{manifest.name}' v{manifest.version} installed successfully.")

        except Exception as e:
            logger.error(f"[HPM:Installer] Installation failed for '{manifest.id}': {e}")
            result.error = str(e)
            rollback(installed_files, manifest.id)
            # Also deregister from DB to avoid ghost packages
            try:
                self._registry.unregister(manifest.id)
                logger.info(f"[HPM:Installer] DB entry removed for '{manifest.id}' (rollback).")
            except Exception as db_e:
                logger.debug(f"[HPM:Installer] Could not deregister '{manifest.id}' from DB (may not have been registered): {db_e}")

        finally:
            shutil.rmtree(staging_dir, ignore_errors=True)

        return result

    def _emit(self, event_name: str, payload: Dict[str, Any]) -> None:
        if callable(self._event_callback):
            try:
                self._event_callback(event_name, payload)
            except Exception as e:
                logger.debug(f"[HPM:Installer] Event callback failed: {e}")
