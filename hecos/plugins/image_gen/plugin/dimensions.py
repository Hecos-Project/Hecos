"""
Plugin: Image Generation — Dimensions Helper
Resolves aspect ratio strings to (width, height) tuples.
"""

# Aspect ratio lookup table → (width, height)
ASPECT_RATIO_MAP = {
    "1:1":   (1024, 1024),
    "16:9":  (1344,  768),
    "9:16":  ( 768, 1344),
    "4:3":   (1152,  896),
    "3:4":   ( 896, 1152),
    "21:9":  (1536,  640),
    "3:2":   (1152,  768),
    "2:3":   ( 768, 1152),
    "5:4":   (1152,  896),
    "4:5":   ( 896, 1120),
}


def resolve_dimensions(aspect_ratio: str, width: int, height: int) -> tuple[int, int]:
    """
    Returns (width, height) based on the selected aspect ratio.
    Falls back to the supplied (width, height) when ratio is 'custom' or unknown.
    All values are rounded to the nearest multiple of 64.
    """
    if aspect_ratio and aspect_ratio.lower() != "custom":
        resolved = ASPECT_RATIO_MAP.get(aspect_ratio)
        if resolved:
            return resolved

    w = max(256, round(width / 64) * 64)
    h = max(256, round(height / 64) * 64)
    return w, h
