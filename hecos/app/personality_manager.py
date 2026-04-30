"""
Management of Hecos's personality (soul) selection.
"""

import time
from hecos.ui import interface
from hecos.core.i18n import translator

class PersonalityManager:
    def __init__(self, config_manager):
        self.config_manager = config_manager

    def handle_personality(self, input_callback, soul_files=None):
        """Management F3 - Personality selection."""
        try:
            # Always sync before listing or choosing
            soul_files = self.config_manager.sync_available_personalities()
        except Exception as e:
            from hecos.core.logging import logger
            logger.error(f"[PERSONALITY] Sync error: {e}")
            soul_files = []
            
        if not soul_files:
            print(f"\n\033[91m{translator.t('no_personality_files')}\033[0m")
            time.sleep(1)
        else:
            # Selection menu already shown by the UI interface
            
            choice = input_callback(translator.t("select_persona_index"))
            if choice == "ESC":
                print(f"\033[93m{translator.t('operation_cancelled')}\033[0m")
                return
                
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(soul_files):
                    new_p = soul_files[idx]
                    self.config_manager.set(new_p, 'ai', 'active_personality')
                    self.config_manager.save()
                    print(f"\033[92m{translator.t('personality_updated', name=new_p)}\033[0m")
                    time.sleep(1)
                else:
                    print(f"\033[91m{translator.t('invalid_index')}\033[0m")
                    time.sleep(1)
