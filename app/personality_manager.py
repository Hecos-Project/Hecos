"""
Gestione della selezione della personalità (anima) di Zentra.
"""

import time
from ui import interfaccia
from core.i18n import translator

class PersonalityManager:
    def __init__(self, config_manager):
        self.config_manager = config_manager

    def handle_personalita(self, input_digitale_sicuro_callback):
        """Gestione F3 - Selezione personalità."""
        anime_files = interfaccia.elenca_personalita()
        
        # Sincronizza config
        if anime_files:
            anime_dict = {str(i+1): name for i, name in enumerate(anime_files)}
            self.config_manager.set(anime_dict, 'ia', 'personalita_disponibili')
            self.config_manager.save()
            
        if not anime_files:
            print(f"\n\033[91m{translator.t('no_personality_files')}\033[0m")
            time.sleep(1)
        else:
            print(f"\n\n\033[96m{translator.t('personality_mgmt_title')}\033[0m")
            for i, nome_file in enumerate(anime_files, 1):
                print(f" [{i}] {nome_file}")
            
            scelta = input_digitale_sicuro_callback(translator.t("select_persona_index"))
            if scelta == "ESC":
                print(f"\033[93m{translator.t('operation_cancelled')}\033[0m")
                return
                
            if scelta.isdigit():
                idx = int(scelta) - 1
                if 0 <= idx < len(anime_files):
                    nuova_p = anime_files[idx]
                    self.config_manager.set(nuova_p, 'ia', 'personalita_attiva')
                    self.config_manager.save()
                    print(f"\033[92m{translator.t('personality_updated', name=nuova_p)}\033[0m")
                    time.sleep(1)
                else:
                    print(f"\033[91m{translator.t('invalid_index')}\033[0m")
                    time.sleep(1)
