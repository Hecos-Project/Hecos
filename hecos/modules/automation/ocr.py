import os
import shutil
import time
from typing import Optional, Tuple
from hecos.core.logging import logger

class TesseractNotFoundError(Exception):
    pass

def _ensure_tesseract():
    """Check if tesseract is installed. For Windows, configure the path if needed."""
    try:
        import pytesseract
    except ImportError:
        return False
        
    if shutil.which("tesseract"):
        return True
        
    # Check default windows location
    default_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(default_path):
        pytesseract.pytesseract.tesseract_cmd = default_path
        return True
        
    return False

def find_text_on_screen(target_text: str, instance: int = 0) -> Optional[Tuple[int, int]]:
    """
    Takes a screenshot, runs OCR to find the bounding box of `target_text`, 
    and returns its center (x, y) coordinates. 
    `instance` handles multiple occurrences (0 = first match, 1 = second, etc.).
    """
    if not _ensure_tesseract():
        raise TesseractNotFoundError(
            "Tesseract OCR engine is not installed or not in PATH. "
            "Please install it from https://github.com/UB-Mannheim/tesseract/wiki to use the text-clicking features."
        )
        
    try:
        import pytesseract
        import cv2
        import numpy as np
        import mss
    except ImportError as e:
        logger.error(f"[AUTOMATION] Missing dependency for OCR: {e}")
        return None

    # Step 1: Capture all screens (stitched)
    try:
        with mss.mss() as sct:
            monitorInfo = sct.monitors[0]
            shot = sct.grab(monitorInfo)
            img = np.array(shot)
            
            offset_x = monitorInfo["left"]
            offset_y = monitorInfo["top"]
    except Exception as e:
        logger.error(f"[AUTOMATION] Failed to capture screen for OCR: {e}")
        return None

    # Step 2: Preprocess for OCR (grayscale, optional thresholding)
    gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
    
    # Step 3: Run OCR
    try:
        data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)
    except Exception as e:
        logger.error(f"[AUTOMATION] OCR execution failed: {e}")
        return None

    # Step 4: Search for target_text
    matches = []
    target_lower = target_text.lower().strip()
    
    for i in range(len(data['text'])):
        word = data['text'][i]
        if not word.strip():
            continue
            
        # Basic substring or exact match check (depending on strictness)
        if target_lower in word.lower():
            x = data['left'][i]
            y = data['top'][i]
            w = data['width'][i]
            h = data['height'][i]
            
            # Calculate absolute screen coordinates based on monitor[0] offset
            center_x = offset_x + x + (w // 2)
            center_y = offset_y + y + (h // 2)
            matches.append((center_x, center_y))

    if not matches:
        return None
        
    # Return the requested instance, or the last one if unbounded
    if instance < len(matches):
        return matches[instance]
    return matches[-1]
