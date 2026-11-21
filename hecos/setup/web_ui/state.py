# hecos/setup/web_ui/state.py
# Global mutable state shared across all web UI handlers.

from __future__ import annotations

import secrets
from typing import Any, Optional

LAST_RESULTS = []
ONBOARDING_DONE = False
UNINSTALL_DONE = False
SMART_UNINSTALL_DONE = False
WIPE_DONE = False

# True when launched via INSTALL_HECOS_WINDOWS.bat / INSTALL_HECOS_LINUX.sh outside a full Core checkout
STANDALONE_MODE = False

# Active background InstallJob (SSE streaming)
CURRENT_JOB: Optional[Any] = None

# Per-session CSRF token required on every state-changing POST request
SESSION_TOKEN = secrets.token_urlsafe(24)

# Available Setup Languages
SETUP_LANGS = {
    "it": "Italiano",
    "en": "English",
    "es": "Español",
    "fr": "Français",
    "de": "Deutsch",
}
