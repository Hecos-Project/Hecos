import os
import json
from datetime import datetime
from hecos.core.logging import logger
from hecos.core.constants import LOGS_DIR

_feed_file = os.path.join(LOGS_DIR, "presenter_feed.jsonl")

def add_feed_entry(event_type: str, text: str, persist: bool = True):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "event_name": event_type,
        "text": text
    }
    if persist:
        try:
            with open(_feed_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
            
            # Simple rotation based on max_items from config
            from hecos.modules.web_ui.extensions.presenter.config.store import load_presenter_config
            cfg = load_presenter_config()
            max_items = cfg.feed.max_items
            
            with open(_feed_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            if len(lines) > max_items:
                with open(_feed_file, "w", encoding="utf-8") as f:
                    f.writelines(lines[-max_items:])
                    
        except Exception as e:
            logger.error(f"[Presenter] Could not save feed entry: {e}")
            
    # Emit to frontend via SSE
    try:
        from hecos.modules.web_ui.server import get_state_manager
        sm = get_state_manager()
        if sm is not None:
            sm.add_event("presenter_feed", entry)
    except Exception as e:
        logger.error(f"[Presenter] SSE push error: {e}")
