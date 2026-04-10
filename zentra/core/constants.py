import os

# Base directory for the Zentra Core internal structure
# Calculated relative to zentra/core/constants.py (2 levels up)
ZENTRA_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Main storage directories (relative to ZENTRA_DIR)
LOGS_DIR = os.path.join(ZENTRA_DIR, "logs")
SNAPSHOTS_DIR = os.path.join(ZENTRA_DIR, "snapshots")
IMAGES_DIR = os.path.join(SNAPSHOTS_DIR, "images")
MEMORY_DIR = os.path.join(ZENTRA_DIR, "memory")
CONFIG_DATA_DIR = os.path.join(ZENTRA_DIR, "config", "data")

# Standardize path creation logic
def ensure_directories():
    """Ensure that all core directories exist."""
    dirs = [LOGS_DIR, SNAPSHOTS_DIR, IMAGES_DIR, MEMORY_DIR, CONFIG_DATA_DIR]
    for d in dirs:
        if not os.path.exists(d):
            os.makedirs(d, exist_ok=True)
