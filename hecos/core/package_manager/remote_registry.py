"""
remote_registry.py
─────────────────────────────────────────────────────────────────────────────
Hecos Package Manager — Remote Registry Client (STUB)

This module is a stub for the future online package repository.
When implemented, it will:
  - Connect to https://packages.hecos.ai (or a self-hosted registry)
  - Allow browsing, searching, and downloading .hpkg packages
  - Cache the package index locally for offline browsing
  - Authenticate with an API key for private/premium packages

Current behavior: returns empty results (no network calls made).
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional
from hecos.core.logging import logger


# Default remote registry URL (future)
REMOTE_REGISTRY_URL = "https://packages.hecos.ai/v1"


class RemoteRegistryClient:
    """
    STUB: Client for the online Hecos Package Registry.

    Future implementation will fetch package lists from a remote API
    and allow direct download + install of community packages.
    """

    def __init__(self, base_url: str = REMOTE_REGISTRY_URL, api_key: str = ""):
        self._base_url = base_url
        self._api_key = api_key
        self._enabled = False  # Will be True once implemented

    def search(self, query: str = "", category: str = "") -> List[Dict[str, Any]]:
        """
        STUB: Search the remote package registry.

        Returns:
            List of package metadata dicts. Currently always empty.
        """
        if not self._enabled:
            logger.debug(
                "[HPM:Remote] Remote registry is not yet enabled. "
                "Returning empty results."
            )
            return []

        # ── FUTURE IMPLEMENTATION ───────────────────────────────────────────
        # import requests
        # resp = requests.get(
        #     f"{self._base_url}/packages",
        #     params={"q": query, "category": category},
        #     headers={"X-API-Key": self._api_key},
        #     timeout=10
        # )
        # resp.raise_for_status()
        # return resp.json().get("packages", [])
        # ────────────────────────────────────────────────────────────────────
        return []

    def download(self, package_id: str, version: str = "latest") -> Optional[bytes]:
        """
        STUB: Download a .hpkg file from the remote registry.

        Returns:
            Raw bytes of the .hpkg file, or None if unavailable.
        """
        if not self._enabled:
            logger.debug(
                f"[HPM:Remote] Remote download requested for '{package_id}' "
                f"but remote registry is not yet enabled."
            )
            return None

        # ── FUTURE IMPLEMENTATION ───────────────────────────────────────────
        # import requests
        # resp = requests.get(
        #     f"{self._base_url}/packages/{package_id}/download",
        #     params={"version": version},
        #     headers={"X-API-Key": self._api_key},
        #     timeout=60,
        #     stream=True
        # )
        # resp.raise_for_status()
        # return resp.content
        # ────────────────────────────────────────────────────────────────────
        return None

    def get_package_info(self, package_id: str) -> Optional[Dict[str, Any]]:
        """
        STUB: Fetch metadata for a specific package from the remote registry.
        """
        if not self._enabled:
            return None
        return None

    @property
    def is_available(self) -> bool:
        """Returns True when remote registry is configured and reachable."""
        return False  # Will check network connectivity when enabled
