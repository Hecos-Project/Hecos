"""
MODULE: hecos.core.identity
DESCRIPTION: Authorship and product identity verification for Hecos.

Loads the signed .hecos_identity blob from the core directory, verifies
its Ed25519 signature against the HPM public key, and exposes the
author/copyright data to the rest of the system.

Copyright (C) 2024-2026 Antonio Meloni. All rights reserved.
"""

from __future__ import annotations

import base64
import json
import os
from typing import Optional

# ── Internal cache ─────────────────────────────────────────────────────────────
_identity_cache: Optional[dict] = None
_verified_cache: Optional[bool] = None

_IDENTITY_FILE = os.path.join(os.path.dirname(__file__), ".hecos_identity")
_PUBLIC_KEY_SEARCH = [
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "trusted_keys", "hpm_public.pem"),
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "certs", "hpm_private.pem", "public.pem"),
]


def _find_public_key() -> Optional[str]:
    for path in _PUBLIC_KEY_SEARCH:
        resolved = os.path.normpath(path)
        if os.path.isfile(resolved):
            return resolved
    return None


def _load_and_verify() -> tuple[dict, bool]:
    """Reads .hecos_identity, verifies Ed25519 signature."""
    if not os.path.isfile(_IDENTITY_FILE):
        return {}, False

    try:
        with open(_IDENTITY_FILE, "rb") as f:
            blob = json.loads(f.read().decode("utf-8"))
    except Exception:
        return {}, False

    identity = blob.get("identity", {})
    sig_b64  = blob.get("signature", "")
    algo     = blob.get("algo", "")

    if algo != "Ed25519" or not sig_b64:
        return identity, False

    pub_key_path = _find_public_key()
    if not pub_key_path:
        return identity, False

    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.backends import default_backend
        from cryptography.exceptions import InvalidSignature

        with open(pub_key_path, "rb") as f:
            pub_key = serialization.load_pem_public_key(f.read(), backend=default_backend())

        payload_bytes = json.dumps(identity, ensure_ascii=False, sort_keys=True).encode("utf-8")
        signature = base64.b64decode(sig_b64)
        pub_key.verify(signature, payload_bytes)
        return identity, True

    except InvalidSignature:
        return identity, False
    except Exception:
        return identity, False


def get_identity() -> dict:
    """Returns the identity dictionary from the signed blob."""
    global _identity_cache, _verified_cache
    if _identity_cache is None:
        _identity_cache, _verified_cache = _load_and_verify()
    return _identity_cache


def is_verified() -> bool:
    """Returns True if the identity blob signature is valid."""
    global _identity_cache, _verified_cache
    if _verified_cache is None:
        _identity_cache, _verified_cache = _load_and_verify()
    return bool(_verified_cache)


def get_author_card(include_address: bool = False) -> str:
    """
    Returns a human-readable authorship card for display in chat or UI.
    include_address: if True, includes the physical address (default False).
    """
    iid = get_identity()
    verified = is_verified()

    if not iid:
        return "⚠️ Identity blob not found or corrupted."

    badge     = "✅ Signature verified" if verified else "⚠️ Signature unverified"
    product   = iid.get("product",    "Hecos")
    author    = iid.get("author",     "Unknown")
    born      = iid.get("born",       "")
    birthplace= iid.get("birthplace", "")
    address   = iid.get("address",    "")
    copyright_= iid.get("copyright",  "")
    license_  = iid.get("license",    "")

    out = [
        f"## 🔏 {product} — Product Identity",
        f"",
        f"**Author:** {author}",
        f"**Born:** {born} — {birthplace}",
    ]
    if include_address and address:
        out.append(f"**Registered Address:** {address}")
    out += [
        f"",
        f"**Copyright:** {copyright_}",
        f"**License:** {license_}",
        f"",
        f"*{badge}*",
    ]
    return "\n".join(out)
