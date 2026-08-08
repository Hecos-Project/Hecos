# hecos/setup/web_ui/state.py
# Global mutable state shared across all web UI handlers.

LAST_RESULTS = []
ONBOARDING_DONE = False
UNINSTALL_DONE = False
SMART_UNINSTALL_DONE = False
WIPE_DONE = False

# Available Setup Languages (shown on the splash page)
SETUP_LANGS = {
    "en": "English",
    "it": "Italiano",
    "es": "Español",
    "fr": "Français",
    "de": "Deutsch",
}
