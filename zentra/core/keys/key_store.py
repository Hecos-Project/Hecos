"""
MODULE: core/keys/key_store.py
DESCRIPTION: Dataclass representing a single API key entry in the pool.
"""

import time
from dataclasses import dataclass, field

# Status constants
STATUS_VALID = "valid"
STATUS_RATE_LIMITED = "rate_limited"
STATUS_INVALID = "invalid"
STATUS_UNKNOWN = "unknown"


@dataclass
class ApiKeyEntry:
    """Represents a single API key with its metadata, status and rotation state."""

    provider: str           # "groq", "gemini", "openai", etc.
    value: str              # The actual key string (masked in logs)
    description: str = ""  # Human-readable label, e.g. "Groq Free Tier - personale"
    source: str = "unknown" # "env" | "keys_yaml" | "system_yaml"
    status: str = STATUS_UNKNOWN
    last_used: float = 0.0
    fail_count: int = 0
    cooldown_until: float = 0.0  # Unix timestamp — key is suppressed until this time

    @property
    def masked(self) -> str:
        """Returns a masked version of the key for safe logging."""
        v = self.value
        if len(v) > 8:
            return f"{v[:4]}...{v[-4:]}"
        return "***"

    def is_available(self) -> bool:
        """Returns True if the key can be used right now."""
        if self.status == STATUS_INVALID:
            return False
        if self.status == STATUS_RATE_LIMITED:
            return time.time() >= self.cooldown_until
        return True

    def mark_rate_limited(self, cooldown_seconds: float = 60.0):
        """Mark this key as temporarily rate-limited with a cooldown."""
        self.status = STATUS_RATE_LIMITED
        self.fail_count += 1
        self.cooldown_until = time.time() + cooldown_seconds

    def mark_invalid(self):
        """Mark this key as permanently invalid (bad key, auth error)."""
        self.status = STATUS_INVALID
        self.fail_count += 1

    def mark_valid(self):
        """Reset key to valid status."""
        self.status = STATUS_VALID
        self.fail_count = 0
        self.cooldown_until = 0.0

    def to_dict(self, include_value: bool = False) -> dict:
        """Serialize to dict for API/JSON responses. Value is masked by default."""
        return {
            "provider": self.provider,
            "value": self.value if include_value else self.masked,
            "description": self.description,
            "source": self.source,
            "status": self.status,
            "fail_count": self.fail_count,
            "cooldown_remaining": max(0.0, round(self.cooldown_until - time.time(), 1)),
            "available": self.is_available(),
        }
