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
from typing import List, Callable, Dict, Any, TYPE_CHECKING

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

    def __init__(self, registry: "PackageRegistry", event_callback: Callable[[str, Dict[str, Any]], None] = None):
        self._registry = registry
        self._event_callback = event_callback

    def _emit(self, event_name: str, payload: Dict[str, Any]) -> None:
        if self._event_callback:
            self._event_callback(event_name, payload)

    def resolve(self, manifest, install_pip: bool = True, install_path: str = None) -> DependencyReport:
        """
        Check inter-package deps and optionally install pip requirements.

        Args:
            manifest:    Parsed HpkgManifest object.
            install_pip: If True, pip requirements are installed automatically.
            install_path: Directory where the package is installed (needed for isolated venv).
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
            pip_isolation = getattr(manifest, "pip_isolation", "shared")
            self._install_pip_requirements(manifest.pip_requirements, report, pip_isolation, install_path)

        if not report.has_issues:
            logger.info(f"[HPM:Resolver] All dependencies for '{manifest.id}' satisfied.")
        else:
            logger.warning(
                f"[HPM:Resolver] Dependency issues for '{manifest.id}': {report.summary}"
            )

        return report

    # ── Private ──────────────────────────────────────────────────────────────

    def _install_pip_requirements(self, requirements: List[str], report: DependencyReport, isolation: str = "shared", install_path: str = None) -> None:
        """Install pip packages either globally or in an isolated venv."""
        import os
        import subprocess

        python_exe = sys.executable

        if isolation == "isolated":
            if not install_path:
                logger.error("[HPM:Resolver] Cannot isolate pip dependencies: install_path is None.")
                report.pip_failures.extend(requirements)
                return

            venv_dir = os.path.join(install_path, "venv")
            pyvenv_cfg = os.path.join(venv_dir, "pyvenv.cfg")

            # Re-create venv if broken (missing pyvenv.cfg) or not yet created
            if not os.path.exists(pyvenv_cfg):
                # Clean up any partial venv directory first
                if os.path.exists(venv_dir):
                    import shutil
                    shutil.rmtree(venv_dir, ignore_errors=True)

                logger.info(f"[HPM:Resolver] Creating virtual environment at {venv_dir}...")
                self._emit("hpm:progress", {"step": "venv", "message": "Creating isolated virtual environment..."})
                try:
                    # Use --copies to avoid Windows symlink permission issues.
                    # Do NOT use --without-pip: let venv bundle pip directly (reliable on all Python installs).
                    subprocess.run(
                        [sys.executable, "-m", "venv", "--copies", venv_dir],
                        check=True,
                        capture_output=True,
                        timeout=300  # pip bundling can be slow on first run
                    )
                    logger.info("[HPM:Resolver] Virtual environment created successfully.")
                except subprocess.CalledProcessError as e:
                    logger.error(f"[HPM:Resolver] Failed to create venv: {e.stderr.decode(errors='replace')}")
                    report.pip_failures.extend(requirements)
                    return
                except subprocess.TimeoutExpired:
                    logger.error("[HPM:Resolver] Venv creation timed out after 300s.")
                    report.pip_failures.extend(requirements)
                    return

            # Determine the python executable inside the venv
            if os.name == 'nt':
                python_exe = os.path.join(venv_dir, "Scripts", "python.exe")
            else:
                python_exe = os.path.join(venv_dir, "bin", "python")

            if not os.path.exists(python_exe):
                logger.error(f"[HPM:Resolver] Venv python executable not found: {python_exe}")
                report.pip_failures.extend(requirements)
                return

            # ── Bootstrap: ensure wheel + setuptools are in the new venv ──────
            logger.info("[HPM:Resolver] Bootstrapping wheel/setuptools in isolated venv...")
            self._emit("hpm:progress", {"step": "venv_bootstrap", "message": "Bootstrapping pip/wheel/setuptools..."})
            try:
                proc = subprocess.Popen(
                    [python_exe, "-m", "pip", "install", "--upgrade", "pip", "wheel", "setuptools"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                for line in iter(proc.stdout.readline, ""):
                    if line:
                        line_clean = line.strip()
                        self._emit("hpm:progress", {"step": "pip_log", "message": line_clean})
                proc.stdout.close()
                retcode = proc.wait(timeout=120)
                if retcode != 0:
                    logger.warning(f"[HPM:Resolver] Bootstrap step failed with code {retcode}.")
                else:
                    logger.info("[HPM:Resolver] pip/wheel/setuptools bootstrapped.")
            except Exception as _boot_e:
                logger.warning(f"[HPM:Resolver] Bootstrap step failed (non-fatal): {_boot_e}")

            # Install hecos_sdk into the venv
            sdk_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "hecos_sdk"))
            if os.path.exists(sdk_path):
                logger.info("[HPM:Resolver] Installing hecos_sdk into isolated venv...")
                self._emit("hpm:progress", {"step": "venv_sdk", "message": "Installing Hecos SDK bridge..."})
                try:
                    subprocess.run(
                        [python_exe, "-m", "pip", "install", "--no-deps", sdk_path],
                        check=True,
                        capture_output=True,
                        timeout=120
                    )
                    logger.info("[HPM:Resolver] hecos_sdk installed successfully into venv.")
                except subprocess.CalledProcessError as e:
                    logger.warning(f"[HPM:Resolver] Failed to install hecos_sdk: {e.stderr.decode(errors='replace')}")
                except subprocess.TimeoutExpired:
                    logger.warning("[HPM:Resolver] hecos_sdk install timed out.")
            else:
                logger.warning(f"[HPM:Resolver] hecos_sdk not found at {sdk_path}, skipping SDK install.")




        for req in requirements:
            req = req.strip()

            if not req or req.startswith("#"):
                continue
            logger.info(f"[HPM:Resolver] pip install: {req}")
            self._emit("hpm:progress", {"step": "pip", "message": f"pip install {req}..."})
            try:
                from hecos.core.progress.adapters.pip import run_pip
                def _pip_cb(data):
                    self._emit("hpm:progress", data)

                retcode, output = run_pip(
                    ["install", req, "--no-input"],
                    python_exe=python_exe,
                    on_progress=_pip_cb,
                )
                if retcode != 0:
                    logger.error(f"[HPM:Resolver] pip install failed for {req} with code {retcode}.")
                    report.pip_failures.append(req)
                else:
                    logger.info(f"[HPM:Resolver] pip: '{req}' installed successfully.")
                    report.pip_installed.append(req)
            except Exception as e:
                logger.error(f"[HPM:Resolver] pip install error for {req}: {e}")
                report.pip_failures.append(req)

    @staticmethod
    def normalize_pip_name(req: str) -> str:
        """
        Extract and PEP-503-normalize the base distribution name from a PEP-508
        requirement string (stripping extras like `[socks]`, version specifiers,
        environment markers, URLs, and comments).

        Examples:
            "requests[socks]>=2.31.0" -> "requests"
            "misaki[en]"              -> "misaki"
            "tomli_w"                 -> "tomli-w"
            "ruamel.yaml>=0.18; ..."  -> "ruamel-yaml"
        """
        import re

        if not req:
            return ""
        text = req.strip()
        if not text or text.startswith("#"):
            return ""
        # Strip inline comments, markers, URLs, extras, version operators, parens, spaces
        base = re.split(r'[#;@\[\s><=!~()]', text, maxsplit=1)[0].strip()
        if not base:
            return ""
        return re.sub(r'[-_.]+', '-', base).lower()

    def get_safe_to_uninstall_pip_deps(self, pkg_requirements: List[str], current_pkg_id: str) -> List[str]:
        """
        Cross-checks pip_requirements against Hecos Core (all dependencies &
        optional-dependencies in pyproject.toml), other installed HPM packages,
        and all transitive dependencies via importlib.metadata.
        Returns a deduplicated list of PEP-503 canonical pip package names that
        are genuinely safe to uninstall.
        """
        import os
        import importlib.metadata

        if not pkg_requirements:
            return []

        # 1. Normalize all candidate pip package names requested by the package
        candidate_order: List[str] = []
        candidate_packages = set()
        for req in pkg_requirements:
            clean_req = self.normalize_pip_name(req)
            if clean_req and clean_req not in candidate_packages:
                candidate_packages.add(clean_req)
                candidate_order.append(clean_req)

        if not candidate_packages:
            return []

        safe_to_remove = set(candidate_packages)

        # 2. Protect ALL Hecos Core dependencies (core + all optional-dependencies + build-system)
        core_deps = set()
        hecos_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        toml_path = os.path.join(hecos_root, "pyproject.toml")
        if os.path.exists(toml_path):
            try:
                try:
                    import tomllib  # Python 3.11+
                except ImportError:
                    import tomli as tomllib  # type: ignore

                with open(toml_path, "rb") as f:
                    toml_data = tomllib.load(f)

                project_tbl = toml_data.get("project") or {}
                for dep in project_tbl.get("dependencies") or []:
                    norm = self.normalize_pip_name(dep)
                    if norm:
                        core_deps.add(norm)

                opt_deps = project_tbl.get("optional-dependencies") or {}
                if isinstance(opt_deps, dict):
                    for group_deps in opt_deps.values():
                        for dep in group_deps or []:
                            norm = self.normalize_pip_name(dep)
                            if norm:
                                core_deps.add(norm)

                build_tbl = toml_data.get("build-system") or {}
                for dep in build_tbl.get("requires") or []:
                    norm = self.normalize_pip_name(dep)
                    if norm:
                        core_deps.add(norm)
            except Exception as e:
                logger.error(f"[HPM:Resolver] Failed to parse core pyproject.toml: {e}")
                # Fail-safe: if we cannot verify core dependencies, NEVER uninstall shared pip packages!
                logger.warning("[HPM:Resolver] Aborting shared pip uninstall to protect Hecos Core.")
                return []

        for req in list(safe_to_remove):
            if req in core_deps:
                logger.info(f"[HPM:Resolver] Keeping pip dependency '{req}' because it is used by Hecos Core.")
                safe_to_remove.remove(req)

        # 3. Protect dependencies declared by other installed HPM packages
        other_packages_deps = set()
        all_packages = self._registry.list_all()
        for pkg in all_packages:
            if pkg.get("id") == current_pkg_id:
                continue
            manifest = pkg.get("manifest_snapshot") or {}
            pip_reqs = manifest.get("pip_requirements") or []
            for req in pip_reqs:
                clean_req = self.normalize_pip_name(req)
                if clean_req:
                    other_packages_deps.add(clean_req)

        for req in list(safe_to_remove):
            if req in other_packages_deps:
                logger.info(f"[HPM:Resolver] Keeping pip dependency '{req}' because it is used by another installed HPM package.")
                safe_to_remove.remove(req)

        # 4. Protect transitive dependencies via importlib.metadata (fixed-point loop)
        # Only skip distributions that are STILL marked for removal; any package
        # that is staying installed (including kept candidates) keeps its own deps.
        if safe_to_remove:
            try:
                installed_dists = []
                for dist in importlib.metadata.distributions():
                    dist_name = self.normalize_pip_name(dist.metadata.get("Name", "") or "")
                    if not dist_name:
                        continue
                    req_names = {
                        self.normalize_pip_name(r)
                        for r in (dist.requires or [])
                    }
                    req_names.discard("")
                    installed_dists.append((dist_name, req_names))

                changed = True
                while changed and safe_to_remove:
                    changed = False
                    for dist_name, req_names in installed_dists:
                        if dist_name in safe_to_remove:
                            continue
                        overlap = safe_to_remove & req_names
                        if overlap:
                            for req_base in sorted(overlap):
                                logger.info(
                                    f"[HPM:Resolver] Keeping pip dependency '{req_base}' "
                                    f"because it is required by installed package '{dist_name}'."
                                )
                                safe_to_remove.remove(req_base)
                                changed = True
                            if not safe_to_remove:
                                break
            except Exception as e:
                logger.error(f"[HPM:Resolver] Error while cross-checking transitive pip dependencies: {e}")
                # Fail-safe: avoid breaking the shared environment on metadata inspection error
                return []

        # Return canonical distribution names (never raw specifiers with extras/versions)
        return [pkg for pkg in candidate_order if pkg in safe_to_remove]
