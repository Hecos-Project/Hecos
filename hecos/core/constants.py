import os

# Base directory for the Hecos internal structure
# Calculated relative to hecos/core/constants.py (1 level up)
HECOS_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))

# Main storage directories (relative to HECOS_DIR)
LOGS_DIR = os.path.join(HECOS_DIR, "logs")
MEMORY_DIR = os.path.join(HECOS_DIR, "memory")
CONFIG_DATA_DIR = os.path.join(HECOS_DIR, "config", "data")

# Centralized media directory — all user-generated media goes here.
# Delete this single folder to remove all personal media for privacy.
MEDIA_DIR = os.path.join(HECOS_DIR, "media")
IMAGES_DIR = os.path.join(MEDIA_DIR, "images")        # AI-generated images
SNAPSHOTS_DIR = os.path.join(MEDIA_DIR, "screenshots") # Webcam snapshots
AUDIO_DIR = os.path.join(MEDIA_DIR, "audio")           # TTS audio files
VIDEO_DIR = os.path.join(MEDIA_DIR, "video")           # Future: video recordings

# Standardize path creation logic
def ensure_directories():
    """Ensure that all core directories exist."""
    dirs = [LOGS_DIR, MEMORY_DIR, CONFIG_DATA_DIR,
            MEDIA_DIR, IMAGES_DIR, SNAPSHOTS_DIR, AUDIO_DIR, VIDEO_DIR]
    for d in dirs:
        if not os.path.exists(d):
            os.makedirs(d, exist_ok=True)
