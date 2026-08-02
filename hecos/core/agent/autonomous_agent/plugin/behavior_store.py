import os
import json
from typing import List, Dict, Any

def get_behaviors_file() -> str:
    # hecos/data/behaviors.json
    try:
        hecos_src = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..", "hecos"))
        if not os.path.isdir(hecos_src):
            hecos_src = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        return os.path.join(hecos_src, "data", "behaviors.json")
    except Exception:
        return "behaviors.json"

def list_behaviors() -> List[Dict[str, Any]]:
    path = get_behaviors_file()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_behavior(behavior: Dict[str, Any]) -> bool:
    behaviors = list_behaviors()
    behaviors.append(behavior)
    path = get_behaviors_file()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(behaviors, f, indent=2)
        return True
    except Exception:
        return False
