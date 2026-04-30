"""
Plugin: Image Generation — Dimensions Helper
Resolves aspect ratio strings to (width, height) tuples.
If aspect_ratio == "custom", falls back to the user-supplied width/height.
"""

# Base resolution (longest side). All ratios scale off this.
_BASE = 1024

# Aspect ratio lookup table → (width, height)
ASPECT_RATIO_MAP: dict[str, tuple[int, int]] = {
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

# Human-readable labels for the UI dropdown
ASPECT_RATIO_LABELS: list[dict] = [
    {"value": "1:1",    "label": "1:1 — Square"},
    {"value": "16:9",   "label": "16:9 — Landscape (HD)"},
    {"value": "9:16",   "label": "9:16 — Portrait (Mobile)"},
    {"value": "4:3",    "label": "4:3 — Classic Landscape"},
    {"value": "3:4",    "label": "3:4 — Classic Portrait"},
    {"value": "21:9",   "label": "21:9 — Ultra-Wide"},
    {"value": "3:2",    "label": "3:2 — Photo (Landscape)"},
    {"value": "2:3",    "label": "2:3 — Photo (Portrait)"},
    {"value": "5:4",    "label": "5:4 — Medium Format"},
    {"value": "4:5",    "label": "4:5 — Instagram Portrait"},
    {"value": "custom", "label": "📐 Custom (manual W × H)"},
]


def resolve_dimensions(aspect_ratio: str, width: int, height: int) -> tuple[int, int]:
    """
    Returns (width, height) based on the selected aspect ratio.
    Falls back to the supplied (width, height) when ratio is 'custom' or unknown.
    All values are rounded to the nearest multiple of 64 (required by most diffusion models).
    """
    if aspect_ratio and aspect_ratio.lower() != "custom":
        resolved = ASPECT_RATIO_MAP.get(aspect_ratio)
        if resolved:
            return resolved

    # Custom or unknown: use raw values, but snap to 64-pixel grid
    w = max(256, round(width / 64) * 64)
    h = max(256, round(height / 64) * 64)
    return w, h
