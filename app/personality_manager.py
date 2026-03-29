"""
Management of Zentra's personality (soul) selection.
"""

import time
from ui import interface
from core.i18n import translator

class PersonalityManager:
    def __init__(self, config_manager):
        self.config_manager = config_manager

    def handle_personality(self, input_callback, soul_files=None):
        """Management F3 - Personality selection."""
        if soul_files is None:
            soul_files = interface.list_personalities()
        
        # Sync config
        if soul_files:
            personality_dict = {str(i+1): name for i, name in enumerate(soul_files)}
            self.config_manager.set(personality_dict, 'ai', 'available_personalities')
            self.config_manager.save()
            
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
