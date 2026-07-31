"""
registry.py
─────────────────────────────────────────────────────────────────────────────
Hecos External Dependency Manager — Catalog Registry
─────────────────────────────────────────────────────────────────────────────
Loads and exposes the TOML catalog of all known external (non-pip) deps.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from hecos.core.logging import logger

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # fallback (already in hecos deps)
    except ImportError:
        tomllib = None  # will raise on first use

_CATALOG_PATH = Path(__file__).parent / "ext_deps.toml"
_CURRENT_PLATFORM = sys.platform  # "win32" | "linux" | "darwin"


@dataclass
class ExternalDep:
    """Represents a single external (non-pip) dependency."""
    id: str
    name: str
    description: str
    version: str
    check_type: str            # "executable" | "registry_key" | "path"
    check_value: str
    platforms: List[str]       # ["windows"] | ["linux"] | ["*"]
    download_url: str
    checksum_sha256: str
    install_args: List[str]
    required_by: List[str]
    optional: bool = True

    @property
    def is_platform_relevant(self) -> bool:
        """Returns True if this dep applies to the current OS."""
        if "*" in self.platforms:
            return True
        platform_map = {
            "win32": "windows",
            "linux": "linux",
            "darwin": "darwin",
        }
        current = platform_map.get(_CURRENT_PLATFORM, _CURRENT_PLATFORM)
        return current in self.platforms


# ── Module-level cache ────────────────────────────────────────────────────────
_registry: Optional[dict[str, ExternalDep]] = None


def load_registry() -> dict[str, ExternalDep]:
    """Loads and caches the dep catalog from ext_deps.toml."""
    global _registry
    if _registry is not None:
        return _registry

    if tomllib is None:
        raise RuntimeError(
            "[EDM] Cannot load ext_deps.toml: tomllib/tomli not available. "
            "Please install Python 3.11+ or run: pip install tomli"
        )

    if not _CATALOG_PATH.exists():
        logger.error("EDM", f"Dependency catalog not found at: {_CATALOG_PATH}")
        raise FileNotFoundError(
            f"[EDM] Dependency catalog not found at: {_CATALOG_PATH}"
        )

    with open(_CATALOG_PATH, "rb") as f:
        data = tomllib.load(f)

    _registry = {}
    for entry in data.get("dep", []):
        dep = ExternalDep(
            id=entry["id"],
            name=entry["name"],
            description=entry.get("description", ""),
            version=entry.get("version", ""),
            check_type=entry["check_type"],
            check_value=entry["check_value"],
            platforms=entry.get("platforms", ["*"]),
            download_url=entry.get("download_url", ""),
            checksum_sha256=entry.get("checksum_sha256", ""),
            install_args=entry.get("install_args", []),
            required_by=entry.get("required_by", []),
            optional=entry.get("optional", True),
        )
        _registry[dep.id] = dep

    logger.debug("EDM", f"Loaded {len(_registry)} external dependencies from catalog.")
    return _registry


def get_dep(dep_id: str) -> Optional[ExternalDep]:
    """Returns the ExternalDep for a given id, or None if not in catalog."""
    return load_registry().get(dep_id)


def get_all_deps() -> List[ExternalDep]:
    """Returns all deps in the catalog."""
    return list(load_registry().values())


def get_deps_for_component(component_id: str) -> List[ExternalDep]:
    """Returns all deps required by a specific component id."""
    return [
        dep for dep in load_registry().values()
        if component_id in dep.required_by
    ]
