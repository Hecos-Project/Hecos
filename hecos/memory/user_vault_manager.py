"""
MODULE: User Vault Manager
DESCRIPTION: Creates and manages per-user memory vault directories.
             Each user gets a private folder at hecos/memory/users/{username}/
             containing their chat history, profile notes, and avatar.
             
             This module serves as the integration point for the future
             RAG plugin: the collaborator's semantic memory can simply
             place its data inside get_vault_path(username).
"""

import os

# hecos/memory/user_vault_manager.py -> ../ is hecos/
_HECOS_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
_USERS_DIR = os.path.join(_HECOS_DIR, "memory", "users")


def get_vault_path(username: str) -> str:
    """Returns the absolute path to the user's private vault directory."""
    return os.path.join(_USERS_DIR, username)


def create_user_vault(username: str) -> str:
    """
    Creates the directory structure for a user vault.
    Safe to call multiple times (idempotent).
    Returns the vault path.
    """
    vault = get_vault_path(username)
    os.makedirs(vault, exist_ok=True)
    return vault


def delete_user_vault(username: str) -> bool:
    """
    Removes the entire vault directory for a user.
    Called when a user account is deleted. Irreversible.
    """
    import shutil
    vault = get_vault_path(username)
    if os.path.exists(vault):
        try:
            shutil.rmtree(vault)
            return True
        except Exception as e:
            from hecos.core.logging import logger
            logger.error(f"[VaultManager] Could not delete vault for {username}: {e}")
            return False
    return True  # Already doesn't exist


def list_vaults() -> list:
    """Returns a list of usernames that have an existing vault."""
    if not os.path.exists(_USERS_DIR):
        return []
    return [d for d in os.listdir(_USERS_DIR)
            if os.path.isdir(os.path.join(_USERS_DIR, d))]
