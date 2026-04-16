"""
MODULE: core/keys/key_manager.py
DESCRIPTION: Singleton KeyManager — manages API key pools per provider.
             Provides ordered failover, cooldown tracking, and live reload.
"""

import threading
import time
from typing import Dict, List, Optional

from zentra.core.keys.key_store import ApiKeyEntry, STATUS_VALID, STATUS_UNKNOWN, STATUS_INVALID, STATUS_RATE_LIMITED
from zentra.core.keys import key_loader as _loader
from zentra.core.keys import key_validator as _validator

# Default cooldown for rate-limited keys (seconds)
DEFAULT_COOLDOWN = 60.0

# How many retry attempts with different keys before giving up
MAX_RETRIES = 10


class KeyManager:
    """
    Singleton that manages pools of API keys for each provider.

    Usage:
        from zentra.core.keys import get_key_manager
        km = get_key_manager()

        key = km.get_key("groq")            # Returns next available key string
        km.mark_exhausted("groq", key, "rate_limited")   # After a 429
        km.mark_exhausted("groq", key, "invalid")        # After a 401
        km.mark_valid("groq", key)           # Re-enable manually
    """

    _instance: Optional["KeyManager"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "KeyManager":
        with cls._lock:
            if cls._instance is None:
                inst = super().__new__(cls)
                inst._pools: Dict[str, List[ApiKeyEntry]] = {}
                inst._pool_lock = threading.Lock()
                inst._loaded = False
                inst._monitor_active = False
                inst._monitor_thread: Optional[threading.Thread] = None
                cls._instance = inst
        return cls._instance  # type: ignore

    # ─── Loading ────────────────────────────────────────────────────────────

    def load(self, force: bool = False):
        """Load (or reload) all keys from all sources."""
        with self._pool_lock:
            if self._loaded and not force:
                return
            entries = _loader.load_keys()
            new_pools: Dict[str, List[ApiKeyEntry]] = {}
            for entry in entries:
                new_pools.setdefault(entry.provider, []).append(entry)

            if force and self._pools:
                # Preserve runtime status when reloading (don't reset cooldowns)
                self._merge_status(new_pools)

            self._pools = new_pools
            self._loaded = True

    def _merge_status(self, new_pools: Dict[str, List[ApiKeyEntry]]):
        """After reload, carry over runtime status from old entries."""
        for provider, new_entries in new_pools.items():
            old_entries = self._pools.get(provider, [])
            old_map = {e.value: e for e in old_entries}
            for entry in new_entries:
                if entry.value in old_map:
                    old = old_map[entry.value]
                    entry.status = old.status
                    entry.fail_count = old.fail_count
                    entry.cooldown_until = old.cooldown_until

    def reload(self):
        """Force reload of all keys (called from WebUI or after key edit)."""
        self.load(force=True)

    # ─── Key Access ─────────────────────────────────────────────────────────

    def get_key(self, provider: str) -> Optional[str]:
        """
        Returns the next available key string for the given provider.
        Applies ordered failover: tries keys in pool order, skipping unavailable ones.
        Returns None if no key is available.
        """
        if not self._loaded:
            self.load()

        provider = provider.lower()
        with self._pool_lock:
            pool = self._pools.get(provider, [])
            for entry in pool:
                if entry.is_available():
                    entry.last_used = time.time()
                    if entry.status == STATUS_UNKNOWN:
                        entry.status = STATUS_VALID
                    return entry.value
        return None

    def get_entry(self, provider: str, value: str) -> Optional[ApiKeyEntry]:
        """Get a specific ApiKeyEntry by provider and value."""
        provider = provider.lower()
        pool = self._pools.get(provider, [])
        for entry in pool:
            if entry.value == value:
                return entry
        return None

    # ─── Status Management ──────────────────────────────────────────────────

    def mark_exhausted(self, provider: str, value: str, reason: str = "rate_limited",
                       cooldown: float = DEFAULT_COOLDOWN):
        """
        Mark a key as exhausted after a failure.
        reason: "rate_limited" (429) → temporary cooldown
                "invalid" (401/403) → permanently disabled
        """
        provider = provider.lower()
        with self._pool_lock:
            entry = self.get_entry(provider, value)
            if entry:
                if reason == "invalid":
                    entry.mark_invalid()
                else:
                    entry.mark_rate_limited(cooldown)

    def mark_valid(self, provider: str, value: str):
        """Manually reset a key to valid status."""
        provider = provider.lower()
        with self._pool_lock:
            entry = self.get_entry(provider, value)
            if entry:
                entry.mark_valid()

    # ─── Background Monitoring ──────────────────────────────────────────────

    def start_background_monitor(self, interval_seconds: int = 600):
        """
        Starts a background thread that periodically validates keys.
        Only runs if not already active and if there are keys to check.
        """
        if self._monitor_active:
            return

        def _monitor_loop():
            from zentra.core.logging.logger import info as log_info
            log_info("[KeyManager] Background health monitor started.")
            self._monitor_active = True
            
            while self._monitor_active:
                try:
                    # 1. Identify providers that actually have keys
                    with self._pool_lock:
                        providers = [p for p, entries in self._pools.items() if entries]
                    
                    if not providers:
                        # Sleep and check again later if no keys are configured
                        time.sleep(interval_seconds)
                        continue

                    log_info(f"[KeyManager] Running periodic health check for: {', '.join(providers)}")
                    for p in providers:
                        if not self._monitor_active: break
                        # We only validate "Unknown" or "Valid" keys once in a while.
                        # Keys already "Invalid" are skipped. "Rate Limited" are also skipped 
                        # until their cooldown expires (handled by validate_key inside).
                        self.validate_provider(p)
                        time.sleep(2) # Prevent self-rate-limiting our validation calls
                        
                except Exception as e:
                    from zentra.core.logging.logger import error as log_error
                    log_error(f"[KeyManager] Monitor loop error: {e}")
                
                # Wait for next interval
                for _ in range(interval_seconds):
                    if not self._monitor_active: break
                    time.sleep(1)

        self._monitor_thread = threading.Thread(target=_monitor_loop, daemon=True, name="KeyHealthMonitor")
        self._monitor_thread.start()

    def stop_background_monitor(self):
        """Signals the background monitor thread to stop."""
        self._monitor_active = False
        if self._monitor_thread:
            # We don't join to avoid blocking the main thread if it's shutting down
            self._monitor_thread = None

    def validate_key(self, provider: str, value: str) -> dict:
        """
        Actively validate a key by calling the provider's API.
        Updates key status based on result.
        """
        provider = provider.lower()
        res = _validator.validate_key(provider, value)
        
        with self._pool_lock:
            entry = self.get_entry(provider, value)
            if entry:
                if res["status"] == "valid":
                    entry.mark_valid()
                elif res["status"] == "invalid":
                    entry.mark_invalid()
                elif res["status"] == "rate_limited":
                    # Mark rate limited with a long cooldown if it's a validation failure
                    # (implies quota likely exhausted) — 2 hours.
                    entry.mark_rate_limited(cooldown_seconds=7200)
        
        return res

    def validate_provider(self, provider: str) -> List[dict]:
        """Validate all keys in a provider pool."""
        provider = provider.lower()
        results = []
        with self._pool_lock:
            pool = self._pools.get(provider, [])
            keys = [e.value for e in pool]
        
        for k in keys:
            results.append(self.validate_key(provider, k))
        return results

    def reset_provider(self, provider: str):
        """Reset all keys for a provider to valid status."""
        provider = provider.lower()
        with self._pool_lock:
            for entry in self._pools.get(provider, []):
                if entry.status != STATUS_INVALID:
                    entry.mark_valid()

    # ─── Info / Status ──────────────────────────────────────────────────────

    def list_providers(self) -> List[str]:
        """Return list of providers with at least one key loaded."""
        if not self._loaded:
            self.load()
        return list(self._pools.keys())

    def get_status(self, provider: str) -> List[dict]:
        """Return status dict list for all keys of a provider."""
        if not self._loaded:
            self.load()
        provider = provider.lower()
        pool = self._pools.get(provider, [])
        return [e.to_dict() for e in pool]

    def get_all_status(self) -> Dict[str, List[dict]]:
        """Return status for all providers."""
        if not self._loaded:
            self.load()
        return {p: [e.to_dict() for e in entries] for p, entries in self._pools.items()}

    def has_available_key(self, provider: str) -> bool:
        """Returns True if at least one key is currently available for the provider."""
        if not self._loaded:
            self.load()
        provider = provider.lower()
        return any(e.is_available() for e in self._pools.get(provider, []))

    def count_keys(self, provider: str) -> dict:
        """Returns count stats: total, available, rate_limited, invalid."""
        if not self._loaded:
            self.load()
        provider = provider.lower()
        pool = self._pools.get(provider, [])
        return {
            "total": len(pool),
            "available": sum(1 for e in pool if e.is_available()),
            "rate_limited": sum(1 for e in pool if e.status == "rate_limited"),
            "invalid": sum(1 for e in pool if e.status == STATUS_INVALID),
        }

    # ─── Key Persistence ────────────────────────────────────────────────────

    def add_key(self, provider: str, value: str, description: str = "", save_to_env: bool = False) -> bool:
        """Add a key to the pool and persist it."""
        if save_to_env:
            saved = _loader.save_key_to_env(provider, value, description)
        else:
            saved = _loader.save_key(provider, value, description)
            
        if saved:
            self.reload()
        return saved

    def remove_key(self, provider: str, value: str) -> bool:
        """Remove a key from the pool and delete it from keys.yaml."""
        removed = _loader.remove_key(provider, value)
        if removed:
            self.reload()
        return removed


# ─── Module-level singleton accessor ────────────────────────────────────────

_manager_instance: Optional[KeyManager] = None


def get_key_manager() -> KeyManager:
    """Returns the global KeyManager singleton (lazy-init)."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = KeyManager()
        _manager_instance.load()
    return _manager_instance
