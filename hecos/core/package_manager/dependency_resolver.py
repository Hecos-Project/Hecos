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
    pip_installed: List[str] = field(default_factory=list)

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

        # Helper to check constraints
        def _check_constraint(dep_id: str, constraint: str, is_optional: bool) -> bool:
            record = self._registry.get(dep_id)
            if not record:
                if is_optional:
                    logger.info(f"[HPM:Resolver] Optional dependency '{dep_id}' for '{manifest.id}' is not installed.")
                    report.missing_optional.append(dep_id)
                else:
                    logger.warning(f"[HPM:Resolver] Hard dependency '{dep_id}' required by '{manifest.id}' is not installed.")
                    report.missing_packages.append(dep_id)
                return False
                
            if constraint:
                try:
                    from packaging.specifiers import SpecifierSet
                    from packaging.version import Version
                    installed_version = Version(record.get("version", "0.0.0"))
                    spec = SpecifierSet(constraint)
                    if installed_version not in spec:
                        msg = f"Dependency '{dep_id}' {constraint} required by '{manifest.id}', but version {installed_version} is installed."
                        if is_optional:
                            logger.info(f"[HPM:Resolver] Optional {msg}")
                            report.missing_optional.append(dep_id)
                        else:
                            logger.warning(f"[HPM:Resolver] Hard {msg}")
                            report.missing_packages.append(dep_id)
                        return False
                except ImportError:
                    pass  # If packaging is missing, ignore constraints gracefully
                except Exception as e:
                    logger.error(f"[HPM:Resolver] Error checking constraint for '{dep_id}': {e}")
            return True

        # 1. Hard inter-package dependencies (blocks if missing — warns only)
        deps = manifest.dependencies if isinstance(manifest.dependencies, dict) else {d: "" for d in manifest.dependencies}
        for dep_id, constraint in deps.items():
            _check_constraint(dep_id, constraint, is_optional=False)

        # 2. Optional inter-package dependencies (informational only, never blocks)
        opt_deps_attr = getattr(manifest, "optional_dependencies", []) or []
        opt_deps = opt_deps_attr if isinstance(opt_deps_attr, dict) else {d: "" for d in opt_deps_attr}
        for dep_id, constraint in opt_deps.items():
            _check_constraint(dep_id, constraint, is_optional=True)

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
                    report.pip_installed.append(req)
            except subprocess.TimeoutExpired:
                logger.error(f"[HPM:Resolver] pip timed out for '{req}'.")
                report.pip_failures.append(req)
            except Exception as e:
                logger.error(f"[HPM:Resolver] pip error for '{req}': {e}")
                report.pip_failures.append(req)
