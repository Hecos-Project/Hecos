"""
Classe principale ConfigEditor che coordina il caricamento, l'editor e il salvataggio.
"""

import os
from .locks import acquire_lock, release_lock
from .parameters import build_parameter_list
from .ui import UIManager
from hecos.core.i18n import translator

class ConfigEditor:
    def __init__(self, config_path=None):
        # config_path kept for backward compat but ignored — we always use ConfigManager.
        # Lazy import to avoid circular import with app/__init__.py
        from hecos.app.config import ConfigManager
        self._config_manager = ConfigManager()
        self.config = self._load_config()

        from hecos.core.audio.audio_config import get_audio_config, _save_audio_config
        self._get_audio_config = get_audio_config
        self._save_audio_config = _save_audio_config
        self.audio_config = get_audio_config()

        self.param_list = build_parameter_list(self.config)
        self.modified = False
        self.audio_modified = False

    def _load_config(self):
        """Loads config via ConfigManager (YAML-backed) and cleans up stale plugin entries."""
        try:
            config = dict(self._config_manager.config)

            # --- Auto-sync plugins ---
            plugins_config = config.get("plugins", {})
            script_dir = os.path.dirname(os.path.abspath(__file__))
            plugins_dir = os.path.normpath(os.path.join(script_dir, "..", "..", "plugins"))

            real_plugins = set()
            if os.path.exists(plugins_dir):
                for item in os.listdir(plugins_dir):
                    item_path = os.path.join(plugins_dir, item)
                    if os.path.isdir(item_path) and os.path.isfile(os.path.join(item_path, "main.py")):
                        real_plugins.add(item.upper())
                    elif os.path.isfile(item_path) and item.endswith(".py") and not item.startswith("_"):
                        real_plugins.add(item[:-3].upper())

            to_remove = [p for p in plugins_config if p not in real_plugins]
            for p in to_remove:
                del plugins_config[p]
            config["plugins"] = plugins_config

            return config

        except Exception as e:
            print(f"Error loading config via ConfigManager: {e}")
            raise

    def _save_config(self):
        """Saves system config (YAML) and audio config."""
        if self.audio_modified:
            try:
                self._save_audio_config(self.audio_config)
                self.audio_modified = False
            except Exception as e:
                print(f"[AUDIO] Save error: {e}")
        if self.modified:
            try:
                self._config_manager.update_config(self.config)
                print(f"\n{translator.t('config_saved_success')}")
            except Exception as e:
                print(f"\n{translator.t('config_save_error', error=str(e))}")

    def _get_value(self, param):
        """Returns a parameter value from current config."""
        try:
            # Determine active backend
            backend_type = self.config.get('backend', {}).get('type', 'ollama')
            backend_config = self.config.get('backend', {}).get(backend_type, {})
            
            # Key is already present in param.key
            key = param.key
            
            # Handle different section types
            if param.section == 'backend':
                return backend_config.get(key)
            elif param.section == 'ollama':
                return self.config.get('backend', {}).get('ollama', {}).get(key)
            elif param.section == 'kobold':
                return self.config.get('backend', {}).get('kobold', {}).get(key)
            elif param.section in ('voice', 'listening'):
                return self.audio_config.get(key)
            elif param.section == 'ai':
                return self.config.get('ai', {}).get(key)
            elif param.section == 'filters':
                return self.config.get('filters', {}).get(key)
            elif param.section == 'logging':
                return self.config.get('logging', {}).get(key)
            elif param.section == 'system':
                return self.config.get('system', {}).get(key)
            elif param.section == 'cognition':
                return self.config.get('cognition', {}).get(key)
            elif param.section == 'llm':
                return self.config.get('llm', {}).get(key)
            elif param.section.startswith('llm_'):
                provider = param.section.split('_')[1]
                return self.config.get('llm', {}).get('providers', {}).get(provider, {}).get(key)
            elif param.section == 'plugin':
                plugins = self.config.get('plugins', {})
                plugin_cfg = plugins.get(param.plugin_tag, {})
                return plugin_cfg.get(key)
            else:
                return None
        except Exception as e:
            print(f"Error in _get_value for {param.label}: {e}")
            return None

    def _set_value(self, param, value):
        """Imposta il valore e marca come modificato."""
        try:
            # Determina il backend attivo
            backend_type = self.config.get('backend', {}).get('type', 'ollama')
            
            # Uso diretto di param.key
            key = param.key
            
            # Gestisci i diversi tipi di sezioni
            if param.section == 'backend':
                if backend_type not in self.config['backend']:
                    self.config['backend'][backend_type] = {}
                old = self.config['backend'][backend_type].get(key)
                if old != value:
                    self.config['backend'][backend_type][key] = value
                    self.modified = True
            elif param.section == 'ollama':
                if 'ollama' not in self.config['backend']:
                    self.config['backend']['ollama'] = {}
                old = self.config['backend']['ollama'].get(key)
                if old != value:
                    self.config['backend']['ollama'][key] = value
                    self.modified = True
            elif param.section == 'kobold':
                if 'kobold' not in self.config['backend']:
                    self.config['backend']['kobold'] = {}
                old = self.config['backend']['kobold'].get(key)
                if old != value:
                    self.config['backend']['kobold'][key] = value
                    self.modified = True
            elif param.section in ('voice', 'listening'):
                old = self.audio_config.get(key)
                if old != value:
                    self.audio_config[key] = value
                    self.audio_modified = True
            elif param.section == 'ai':
                if 'ai' not in self.config:
                    self.config['ai'] = {}
                old = self.config['ai'].get(key)
                if old != value:
                    self.config['ai'][key] = value
                    self.modified = True
            elif param.section == 'filters':
                if 'filters' not in self.config:
                    self.config['filters'] = {}
                old = self.config['filters'].get(key)
                if old != value:
                    self.config['filters'][key] = value
                    self.modified = True
            elif param.section == 'logging':
                if 'logging' not in self.config:
                    self.config['logging'] = {}
                old = self.config['logging'].get(key)
                if old != value:
                    self.config['logging'][key] = value
                    self.modified = True
            elif param.section == 'system':
                if 'system' not in self.config:
                    self.config['system'] = {}
                old = self.config['system'].get(key)
                if old != value:
                    self.config['system'][key] = value
                    self.modified = True
            elif param.section == 'cognition':
                if 'cognition' not in self.config:
                    self.config['cognition'] = {}
                old = self.config['cognition'].get(key)
                if old != value:
                    self.config['cognition'][key] = value
                    self.modified = True
            elif param.section == 'llm':
                if 'llm' not in self.config:
                    self.config['llm'] = {}
                old = self.config['llm'].get(key)
                if old != value:
                    self.config['llm'][key] = value
                    self.modified = True
            elif param.section.startswith('llm_'):
                provider = param.section.split('_')[1]
                if 'llm' not in self.config: self.config['llm'] = {}
                if 'providers' not in self.config['llm']: self.config['llm']['providers'] = {}
                if provider not in self.config['llm']['providers']: self.config['llm']['providers'][provider] = {}
                
                old = self.config['llm']['providers'][provider].get(key)
                if old != value:
                    self.config['llm']['providers'][provider][key] = value
                    self.modified = True
            elif param.section == 'plugin':
                if 'plugins' not in self.config:
                    self.config['plugins'] = {}
                if param.plugin_tag not in self.config['plugins']:
                    self.config['plugins'][param.plugin_tag] = {}
                old = self.config['plugins'][param.plugin_tag].get(key)
                if old != value:
                    self.config['plugins'][param.plugin_tag][key] = value
                    self.modified = True
        except Exception as e:
            print(f"Error in _set_value for {param.label}: {e}")

    def _handle_special_command(self, command: str) -> bool:
        """Handles special commands triggered from the UI. Returns True if handled."""
        if command == 'clear_instructions':
            if 'ai' in self.config:
                self.config['ai']['special_instructions'] = ''
                self.modified = True
            return True
        if command == 'clear_safety_instructions':
            if 'ai' in self.config:
                self.config['ai']['safety_instructions'] = ''
                self.config['ai']['enable_safety_instructions'] = False
                self.modified = True
            return True
        if command == 'clear_memory':
            import sys
            sys.stdout.write("\n\033[93m[MEMORY] Clearing conversation history...\033[0m\n")
            sys.stdout.flush()
            try:
                from hecos.memory.brain_interface import clear_history
                cleared = clear_history()
                if cleared:
                    sys.stdout.write("\033[92m✅ History cleared successfully!\033[0m\n")
                else:
                    sys.stdout.write("\033[91m❌ Failed to clear history.\033[0m\n")
            except Exception as e:
                sys.stdout.write(f"\033[91m❌ Error: {e}\033[0m\n")
            sys.stdout.flush()
            import msvcrt, time
            sys.stdout.write("Press any key to continue...\n")
            sys.stdout.flush()
            time.sleep(0.5)
            while msvcrt.kbhit(): msvcrt.getch()
            msvcrt.getch()
            return True
        return False

    def run(self):
        """Avvia l'editor interattivo con lock."""
        if not acquire_lock():
            print("Unable to acquire lock. Editor already running?")
            return
        
        try:
            result = None
            ui = UIManager(self.param_list, self._get_value, self._set_value,
                           command_handler=self._handle_special_command)
            result = ui.run()
            
            import sys
            import time
            from hecos.core.i18n import translator
            
            if result == "REBOOT":
                self._save_config()  # saves both system + audio if changed
                print(f"\n\033[91m{translator.t('rebooting_msg')}\033[0m")
                time.sleep(1)
                sys.exit(42)
                
            elif result == "SAVE":
                import os
                os.system('cls' if os.name == 'nt' else 'clear')
                print(f"\n\n\033[92m{'═'*55}")
                print("   ✅ CONFIGURATION SAVED SUCCESSFULLY!   ")
                print(f"{'═'*55}\033[0m")
                self._save_config()  # saves both system + audio if changed
                # Restart solo al salvataggio esplicito utente
                print(f"\n\033[93m{translator.t('rebooting_msg')}...\033[0m")
                time.sleep(2)
                sys.exit(42)
                
            elif result == "DISCARD":
                print(f"\n\033[93mExiting without saving. Changes have been discarded.\033[0m")
                # Nessun salvataggio, nessun riavvio
                
            else: # NO_CHANGES - salva solo se core.py ha pulito vecchi plugin
                if self.modified or self.audio_modified:
                    self._save_config()
                    
        finally:
            release_lock()