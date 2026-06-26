"""
CORE: Hecos Package Manager (HPM)
─────────────────────────────────────────────────────────────────────────────
Manages installation, update, and removal of .hpkg packages.
Each sub-module has a single, well-defined responsibility:

  package_schema.py      — Pydantic schema for hpkg_manifest.json
  registry.py            — SQLite registry of installed packages
  validator.py           — ZIP integrity + manifest schema checks
  installer.py           — Atomic install with rollback
  uninstaller.py         — Clean removal of all package artefacts
  dependency_resolver.py — pip + inter-package dependency handling
  signature.py           — (stub) Digital signature verification
  remote_registry.py     — (stub) Online package repository client
─────────────────────────────────────────────────────────────────────────────
"""

from .registry import PackageRegistry
from .installer import PackageInstaller
from .uninstaller import PackageUninstaller
from .validator import PackageValidator

__all__ = [
    "PackageRegistry",
    "PackageInstaller",
    "PackageUninstaller",
    "PackageValidator",
]
