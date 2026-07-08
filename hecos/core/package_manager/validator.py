"""
validator.py
─────────────────────────────────────────────────────────────────────────────
Hecos Package Manager — Package Validator

Validates a .hpkg file BEFORE any extraction or installation.
Checks:
  1. File is a valid ZIP archive
  2. No path-traversal sequences in member names
  3. hpkg_manifest.json exists at the zip root
  4. hpkg_manifest.json conforms to HpkgManifest schema
  5. Hecos version compatibility check
  6. SHA-256 checksum (if declared in the manifest)
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import hashlib
import io
import tomllib
import zipfile
from dataclasses import dataclass, field
from typing import Optional

from hecos.core.logging import logger
from .package_schema import HpkgManifest


MANIFEST_FILENAME = "hpkg_manifest.toml"


@dataclass
class ValidationResult:
    valid: bool = True
    manifest: Optional[HpkgManifest] = None
    errors: list = field(default_factory=list)

    def add_error(self, msg: str) -> None:
        self.valid = False
        self.errors.append(msg)
        logger.error(f"[HPM:Validator] {msg}")

    @property
    def error_summary(self) -> str:
        return "; ".join(self.errors)


class PackageValidator:
    """
    Validates a .hpkg file (provided as a bytes object or a file path).

    Usage:
        validator = PackageValidator(hecos_version="0.35.0")
        result = validator.validate_bytes(hpkg_bytes)
        if not result.valid:
            print(result.error_summary)
        else:
            manifest = result.manifest
    """

    def __init__(self, hecos_version: str = "0.35.0"):
        self._hecos_version = hecos_version

    # ── Public API ───────────────────────────────────────────────────────────

    def validate_file(self, hpkg_path: str) -> ValidationResult:
        """Validate a .hpkg file from disk."""
        try:
            with open(hpkg_path, "rb") as f:
                data = f.read()
            return self.validate_bytes(data)
        except FileNotFoundError:
            result = ValidationResult()
            result.add_error(f"File not found: {hpkg_path}")
            return result
        except Exception as e:
            result = ValidationResult()
            result.add_error(f"Cannot read file '{hpkg_path}': {e}")
            return result

    def validate_bytes(self, data: bytes) -> ValidationResult:
        """
        Validate a .hpkg file from raw bytes.
        Returns a ValidationResult with parsed manifest on success.
        """
        result = ValidationResult()

        # Step 1 — Is it a valid ZIP?
        if not self._is_valid_zip(data, result):
            return result

        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            # Step 2 — No path traversal
            self._check_path_traversal(zf, result)
            if not result.valid:
                return result

            # Step 3 — hpkg_manifest.json must exist at root
            manifest_raw = self._read_manifest(zf, result)
            if not result.valid or manifest_raw is None:
                return result

            # Step 4 — Parse and validate manifest schema
            manifest = self._parse_manifest(manifest_raw, result)
            if not result.valid or manifest is None:
                return result

            # Step 5 — Hecos version compatibility
            self._check_hecos_version(manifest, result)

            # Step 6 — SHA-256 checksum (if declared)
            self._check_checksum(manifest, data, result)

        if result.valid:
            result.manifest = manifest
            logger.info(
                f"[HPM:Validator] Package '{manifest.id}' v{manifest.version} passed validation."
            )

        return result

    # ── Private Steps ─────────────────────────────────────────────────────────

    @staticmethod
    def _is_valid_zip(data: bytes, result: ValidationResult) -> bool:
        if not zipfile.is_zipfile(io.BytesIO(data)):
            result.add_error("File is not a valid ZIP archive (.hpkg).")
            return False
        return True

    @staticmethod
    def _check_path_traversal(zf: zipfile.ZipFile, result: ValidationResult) -> None:
        for name in zf.namelist():
            # Catch absolute paths and traversal sequences
            if name.startswith("/") or ".." in name.split("/"):
                result.add_error(
                    f"Security: path traversal detected in member '{name}'. Installation aborted."
                )
                return

    @staticmethod
    def _read_manifest(zf: zipfile.ZipFile, result: ValidationResult) -> Optional[str]:
        names = zf.namelist()
        if MANIFEST_FILENAME not in names:
            result.add_error(
                f"'{MANIFEST_FILENAME}' not found at zip root. "
                f"Available entries: {names[:10]}"
            )
            return None
        try:
            return zf.read(MANIFEST_FILENAME).decode("utf-8")
        except Exception as e:
            result.add_error(f"Cannot read '{MANIFEST_FILENAME}': {e}")
            return None

    @staticmethod
    def _parse_manifest(raw: str, result: ValidationResult) -> Optional[HpkgManifest]:
        try:
            data = tomllib.loads(raw)
        except tomllib.TOMLDecodeError as e:
            result.add_error(f"'{MANIFEST_FILENAME}' is not valid TOML: {e}")
            return None
        try:
            return HpkgManifest(**data)
        except Exception as e:
            result.add_error(f"Manifest schema validation failed: {e}")
            return None

    def _check_hecos_version(self, manifest: HpkgManifest, result: ValidationResult) -> None:
        try:
            from packaging.version import Version
            from packaging.specifiers import SpecifierSet
            
            current_ver = Version(self._hecos_version)
            
            # Check min version (backwards compatible exact version string)
            min_ver = Version(manifest.hecos_min_version)
            if current_ver < min_ver:
                result.add_error(
                    f"This package requires Hecos >= {manifest.hecos_min_version}, "
                    f"but the current version is {self._hecos_version}."
                )
                
            # Check max version constraint if specified (e.g., "<1.0.0")
            if manifest.hecos_max_version:
                max_spec = SpecifierSet(manifest.hecos_max_version)
                if current_ver not in max_spec:
                    result.add_error(
                        f"This package requires Hecos {manifest.hecos_max_version}, "
                        f"but the current version is {self._hecos_version}."
                    )
        except ImportError:
            # Fallback if packaging is not available
            def _parse(v: str):
                return tuple(int(x) for x in v.split(".")[:3] if x.isdigit())
            
            if _parse(self._hecos_version) < _parse(manifest.hecos_min_version):
                result.add_error(
                    f"This package requires Hecos >= {manifest.hecos_min_version}, "
                    f"but the current version is {self._hecos_version}."
                )
        except Exception as e:
            logger.warning(f"[HPM:Validator] Could not compare versions: {e}")

    @staticmethod
    def _check_checksum(manifest: HpkgManifest, data: bytes, result: ValidationResult) -> None:
        if not manifest.checksum_sha256:
            return  # Checksum is optional
        actual = hashlib.sha256(data).hexdigest()
        if actual.lower() != manifest.checksum_sha256.lower():
            result.add_error(
                f"SHA-256 checksum mismatch. "
                f"Expected: {manifest.checksum_sha256}, got: {actual}"
            )
