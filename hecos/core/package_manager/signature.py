"""
signature.py
─────────────────────────────────────────────────────────────────────────────
Hecos Package Manager — Digital Signature
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import os
import json
import base64
from typing import Dict, Any, Optional

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

from hecos.core.logging import logger


class SignatureVerifier:
    """
    Digital signature verifier for .hpkg packages using Ed25519.
    """

    def __init__(self, trusted_keys_dir: str):
        self._trusted_keys_dir = trusted_keys_dir
        self._public_keys: Dict[str, Ed25519PublicKey] = {}
        self._load_keys()

    def _load_keys(self) -> None:
        """Load all .pem public keys from the trusted_keys directory."""
        if not os.path.isdir(self._trusted_keys_dir):
            os.makedirs(self._trusted_keys_dir, exist_ok=True)
            return

        for fname in os.listdir(self._trusted_keys_dir):
            if fname.endswith(".pem"):
                key_path = os.path.join(self._trusted_keys_dir, fname)
                try:
                    with open(key_path, "rb") as f:
                        key_data = f.read()
                    pub_key = serialization.load_pem_public_key(key_data)
                    if isinstance(pub_key, Ed25519PublicKey):
                        self._public_keys[fname] = pub_key
                        logger.debug(f"[HPM:Signature] Loaded trusted key: {fname}")
                    else:
                        logger.warning(f"[HPM:Signature] Key {fname} is not an Ed25519 key. Ignored.")
                except Exception as e:
                    logger.error(f"[HPM:Signature] Failed to load key {fname}: {e}")

    def verify_manifest(self, manifest_dict: Dict[str, Any], require_signature: bool = True) -> bool:
        """
        Verify the signature of the manifest using trusted public keys.

        Args:
            manifest_dict: The raw dictionary of the manifest.json
            require_signature: If True, fails if no signature is present.

        Returns:
            True if the signature is valid (or if skipped and valid), False otherwise.
        """
        signature_b64 = manifest_dict.get("signature")

        if not signature_b64:
            if require_signature:
                logger.error("[HPM:Signature] Package is NOT signed, but signatures are required.")
                return False
            else:
                logger.warning("[HPM:Signature] Package is NOT signed. Allowed by bypass flag.")
                return True

        if not self._public_keys:
            if require_signature:
                logger.error("[HPM:Signature] No trusted public keys found in the keyring.")
                return False
            else:
                logger.warning("[HPM:Signature] No trusted public keys found. Allowed by bypass flag.")
                return True

        # Canonicalize the manifest
        # We must remove the signature itself before calculating the payload
        payload_dict = dict(manifest_dict)
        payload_dict.pop("signature", None)

        # To ensure consistency, we dump with sort_keys=True and no spaces
        payload_bytes = json.dumps(payload_dict, sort_keys=True, separators=(',', ':')).encode("utf-8")

        try:
            signature_bytes = base64.b64decode(signature_b64)
        except Exception as e:
            logger.error(f"[HPM:Signature] Invalid Base64 in signature: {e}")
            return False

        # Check against all trusted keys
        for key_name, pub_key in self._public_keys.items():
            try:
                pub_key.verify(signature_bytes, payload_bytes)
                logger.info(f"[HPM:Signature] Signature verified successfully with key: {key_name}")
                return True
            except InvalidSignature:
                continue
            except Exception as e:
                logger.warning(f"[HPM:Signature] Error during verification with {key_name}: {e}")

        logger.error("[HPM:Signature] Signature verification FAILED. Package is altered or from an untrusted source.")
        return False
