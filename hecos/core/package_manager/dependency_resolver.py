"""
dependency_resolver.py
─────────────────────────────────────────────────────────────────────────────
Hecos Package Manager — Dependency Resolver

Handles two types of dependencies:
  1. Inter-package hard deps: checks that other HPM packages are installed.
     Missing hard deps WARN in the result but do NOT block installation.
  2. Inter-package optional deps: checks that optional enhancing packages
     are installed. Missing optional deps produce a lighter info-level notice.
  3. pip: installs Python packages from pip_requirements using the current
     Python interpreter, non-interactively.

Does NOT raise on missing inter-package dependencies — it warns and
continues. The installer decides whether to block based on the result.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from typing import List, TYPE_CHECKING

from hecos.core.logging import logger

if TYPE_CHECKING:
    from .registry import PackageRegistry


@dataclass
class DependencyReport:
    missing_packages: List[str] = field(default_factory=list)
    missing_optional: List[str] = field(default_factory=list)  # Optional deps not installed
    pip_failures: List[str] = field(default_factory=list)

    @property
    def has_issues(self) -> bool:
        return bool(self.missing_packages or self.pip_failures)

    @property
    def summary(self) -> str:
        parts = []
        if self.missing_packages:
            parts.append(f"Missing required HPM packages: {self.missing_packages}")
        if self.missing_optional:
            parts.append(f"Optional HPM packages not installed (non-blocking): {self.missing_optional}")
        if self.pip_failures:
            parts.append(f"pip install failures: {self.pip_failures}")
        return "; ".join(parts) if parts else "OK"


class DependencyResolver:
    """
    Resolves and installs dependencies for a .hpkg package.

    Usage:
        resolver = DependencyResolver(registry)
        report = resolver.resolve(manifest)
        if report.has_issues:
            logger.warning(report.summary)
    """

    def __init__(self, registry: "PackageRegistry"):
        self._registry = registry

    def resolve(self, manifest, install_pip: bool = True) -> DependencyReport:
        """
        Check inter-package deps and optionally install pip requirements.

        Args:
            manifest:    Parsed HpkgManifest object.
            install_pip: If True, pip requirements are installed automatically.
        """
        report = DependencyReport()

        # 1. Hard inter-package dependencies (blocks if missing — warns only)
        for dep_id in manifest.dependencies:
            if not self._registry.is_installed(dep_id):
                logger.warning(
                    f"[HPM:Resolver] Hard dependency '{dep_id}' required by "
                    f"'{manifest.id}' is not installed."
                )
                report.missing_packages.append(dep_id)

        # 2. Optional inter-package dependencies (informational only, never blocks)
        optional_deps = getattr(manifest, "optional_dependencies", []) or []
        for dep_id in optional_deps:
            if not self._registry.is_installed(dep_id):
                logger.info(
                    f"[HPM:Resolver] Optional dependency '{dep_id}' for "
                    f"'{manifest.id}' is not installed — some features may be unavailable."
                )
                report.missing_optional.append(dep_id)

        # 3. pip requirements
        if install_pip and manifest.pip_requirements:
            self._install_pip_requirements(manifest.pip_requirements, report)

        if not report.has_issues:
            logger.info(f"[HPM:Resolver] All dependencies for '{manifest.id}' satisfied.")
        else:
            logger.warning(
                f"[HPM:Resolver] Dependency issues for '{manifest.id}': {report.summary}"
            )

        return report

    # ── Private ──────────────────────────────────────────────────────────────

    @staticmethod
    def _install_pip_requirements(requirements: List[str], report: DependencyReport) -> None:
        """Install pip packages using the running Python interpreter."""
        for req in requirements:
            req = req.strip()
            if not req or req.startswith("#"):
                continue
            logger.info(f"[HPM:Resolver] pip install: {req}")
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", req, "--quiet", "--no-input"],
                    capture_output=True,
                    text=True,
                    timeout=120,  # 2-minute timeout per package
                )
                if result.returncode != 0:
                    logger.error(
                        f"[HPM:Resolver] pip failed for '{req}': {result.stderr.strip()}"
                    )
                    report.pip_failures.append(req)
                else:
                    logger.info(f"[HPM:Resolver] pip: '{req}' installed successfully.")
            except subprocess.TimeoutExpired:
                logger.error(f"[HPM:Resolver] pip timed out for '{req}'.")
                report.pip_failures.append(req)
            except Exception as e:
                logger.error(f"[HPM:Resolver] pip error for '{req}': {e}")
                report.pip_failures.append(req)
