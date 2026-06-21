"""
signature.py
─────────────────────────────────────────────────────────────────────────────
Hecos Package Manager — Digital Signature (STUB)

This module is a stub for the future digital signature verification system.
When implemented, it will:
  - Verify that .hpkg files are signed by a trusted developer key
  - Support a keyring of trusted public keys stored in hecos/data/trusted_keys/
  - Enforce signature verification for packages installed from remote registries

Current behavior: always returns True (no verification performed).
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

from hecos.core.logging import logger


class SignatureVerifier:
    """
    STUB: Digital signature verifier for .hpkg packages.

    Future implementation will use asymmetric cryptography (e.g. Ed25519)
    to verify that a package was signed by a trusted developer.
    """

    def __init__(self, trusted_keys_dir: str = ""):
        self._trusted_keys_dir = trusted_keys_dir
        self._enabled = False  # Will be True once implemented

    def verify(self, hpkg_data: bytes, signature: str | None) -> bool:
        """
        Verify the signature of a .hpkg package.

        STUB: Currently always returns True.
        When enabled, will verify signature against trusted_keys_dir.

        Args:
            hpkg_data: Raw bytes of the .hpkg file.
            signature: Base64-encoded signature string from the manifest.

        Returns:
            True if the package is trusted, False otherwise.
        """
        if not self._enabled:
            # Stub: no enforcement yet
            if signature:
                logger.debug(
                    "[HPM:Signature] Signature field found but verification is not yet enforced. "
                    "This will be required in a future version."
                )
            return True

        # ── FUTURE IMPLEMENTATION ───────────────────────────────────────────
        # from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        # from cryptography.hazmat.primitives import serialization
        # import base64
        # ...
        # ────────────────────────────────────────────────────────────────────
        raise NotImplementedError("Digital signature verification not yet implemented.")
