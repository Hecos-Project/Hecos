"""
Classe principale ConfigEditor che coordina il caricamento, l'editor e il salvataggio.
"""

import json
import os
from .locks import acquire_lock, release_lock
from .parameters import build_parameter_list
from .ui import UIManager
from core.i18n import translator

class ConfigEditor:
    def __init__(self, config_path="config.json"):
        # Ottieni il percorso della directory in cui si trova main.py
        script_dir = os.path.dirname(os.path.abspath(__file__))  # directory di core.py (ui/config_editor)
        ui_dir = os.path.dirname(script_dir)  # directory ui
        project_dir = os.path.dirname(ui_dir)  # directory del progetto (dove sta main.py)
        self.config_path = os.path.join(project_dir, config_path)
        self.config = self._load_config()
        self.param_list = build_parameter_list(self.config)
        self.modified = False

    def _load_config(self):
        """Carica il file JSON, pulisce config plugin vecchi e sincronizza con la cartella."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            # --- Auto-sync dei plugin ---
            plugins_config = config.get("plugins", {})
            script_dir = os.path.dirname(os.path.abspath(__file__))  
            ui_dir = os.path.dirname(script_dir)  
            project_dir = os.path.dirname(ui_dir)  
            plugins_dir = os.path.join(project_dir, "plugins")
            
            # Trova i plugin reali (cartelle con main.py o file .py validi)
            plugin_reali = set()
            if os.path.exists(plugins_dir):
                for item in os.listdir(plugins_dir):
                    item_path = os.path.join(plugins_dir, item)
                    if os.path.isdir(item_path) and os.path.isfile(os.path.join(item_path, "main.py")):
                        plugin_reali.add(item.upper())
                    elif os.path.isfile(item_path) and item.endswith(".py") and not item.startswith("_"):
                        plugin_reali.add(item[:-3].upper())
            
            # Rimuovere da config.json i plugin che non esistono più
            da_rimuovere = [p for p in plugins_config if p not in plugin_reali]
            for p in da_rimuovere:
                del plugins_config[p]
                self.modified = True  # Segna come modificato se abbiamo pulito qualcosa
                
            config["plugins"] = plugins_config
            
            # --- Auto-init Routing ---
            if "motore_routing" not in config:
                config["motore_routing"] = {"modalita": "auto", "modelli_legacy": ""}
            elif "modelli_legacy" not in config["motore_routing"]:
                 config["motore_routing"]["modelli_legacy"] = ""
                 
            return config
            
        except Exception as e:
            print(f"Errore caricamento {self.config_path}: {e}")
            raise

    def _save_config(self):
        """Salva il file JSON se ci sono modifiche e aggiorna il traduttore."""
        if self.modified:
            try:
                # Controlla cambio lingua prima del salvataggio
                vecchia_lingua = None
                if os.path.exists(self.config_path):
                    try:
                        with open(self.config_path, 'r', encoding='utf-8') as f:
                            old_data = json.load(f)
                            vecchia_lingua = old_data.get("lingua")
                    except: pass

                with open(self.config_path, 'w', encoding='utf-8') as f:
                    json.dump(self.config, f, indent=4, ensure_ascii=False)
                
                # Sincronizza il traduttore se la lingua è cambiata
                nuova_lingua = self.config.get("lingua")
                if nuova_lingua and nuova_lingua != vecchia_lingua:
                    from core.i18n import translator
                    translator.get_translator().set_language(nuova_lingua)
                
                print(f"\n{translator.t('config_saved_success')}")
            except Exception as e:
                print(f"\n{translator.t('config_save_error', error=str(e))}")

    def _get_value(self, param):
        """Restituisce il valore di un parametro dal config corrente."""
        try:
            # Determina il backend attivo
            backend_type = self.config.get('backend', {}).get('tipo', 'ollama')
            backend_config = self.config.get('backend', {}).get(backend_type, {})
            
            # La chiave è già presente in param.key grazie alla nuova build_parameter_list
            key = param.key
            
            # Gestisci i diversi tipi di sezioni
            if param.section == 'backend':
                return backend_config.get(key)
            elif param.section == 'ollama':
                return self.config.get('backend', {}).get('ollama', {}).get(key)
            elif param.section == 'kobold':
                return self.config.get('backend', {}).get('kobold', {}).get(key)
            elif param.section == 'voce':
                return self.config.get('voce', {}).get(key)
            elif param.section == 'ascolto':
                return self.config.get('ascolto', {}).get(key)
            elif param.section == 'filtri':
                return self.config.get('filtri', {}).get(key)
            elif param.section == 'logging':
                return self.config.get('logging', {}).get(key)
            elif param.section == 'system':
                return self.config.get(key)
            elif param.section == 'llm':
                return self.config.get('llm', {}).get(key)
            elif param.section.startswith('llm_'):
                provider = param.section.split('_')[1]
                return self.config.get('llm', {}).get('providers', {}).get(provider, {}).get(key)
            elif param.section == 'plugin':
                # Sezione plugin: accedi a config['plugins'][param.plugin_tag][key]
                plugins = self.config.get('plugins', {})
                plugin_cfg = plugins.get(param.plugin_tag, {})
                return plugin_cfg.get(key)
            elif param.section == 'motore_routing':
                return self.config.get('motore_routing', {}).get(key)
            elif param.section.startswith('legacy_'):
                # Il valore è True se la chiave (nome modello) è nella stringa CSV
                legacy_str = self.config.get('motore_routing', {}).get('modelli_legacy', '')
                legacy_list = [m.strip().lower() for m in legacy_str.split(',') if m.strip()]
                return key.lower() in legacy_list
            else:
                return None
        except Exception as e:
            print(f"Errore in _get_value per {param.label}: {e}")
            return None

    def _set_value(self, param, value):
        """Imposta il valore e marca come modificato."""
        try:
            # Determina il backend attivo
            backend_type = self.config.get('backend', {}).get('tipo', 'ollama')
            
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
            elif param.section == 'voce':
                if 'voce' not in self.config:
                    self.config['voce'] = {}
                old = self.config['voce'].get(key)
                if old != value:
                    self.config['voce'][key] = value
                    self.modified = True
            elif param.section == 'ascolto':
                if 'ascolto' not in self.config:
                    self.config['ascolto'] = {}
                old = self.config['ascolto'].get(key)
                if old != value:
                    self.config['ascolto'][key] = value
                    self.modified = True
            elif param.section == 'filtri':
                if 'filtri' not in self.config:
                    self.config['filtri'] = {}
                old = self.config['filtri'].get(key)
                if old != value:
                    self.config['filtri'][key] = value
                    self.modified = True
            elif param.section == 'logging':
                if 'logging' not in self.config:
                    self.config['logging'] = {}
                old = self.config['logging'].get(key)
                if old != value:
                    self.config['logging'][key] = value
                    self.modified = True
            elif param.section == 'system':
                old = self.config.get(key)
                if old != value:
                    self.config[key] = value
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
                # Sezione plugin: aggiorna config['plugins'][param.plugin_tag][key]
                if 'plugins' not in self.config:
                    self.config['plugins'] = {}
                if param.plugin_tag not in self.config['plugins']:
                    self.config['plugins'][param.plugin_tag] = {}
                old = self.config['plugins'][param.plugin_tag].get(key)
                if old != value:
                    self.config['plugins'][param.plugin_tag][key] = value
                    self.modified = True
            elif param.section == 'motore_routing':
                if 'motore_routing' not in self.config:
                    self.config['motore_routing'] = {}
                old = self.config['motore_routing'].get(key)
                if old != value:
                    self.config['motore_routing'][key] = value
                    self.modified = True
            elif param.section.startswith('legacy_'):
                # Sincronizza il boolean con la stringa modelli_legacy
                if 'motore_routing' not in self.config:
                    self.config['motore_routing'] = {"modelli_legacy": ""}
                
                legacy_str = self.config['motore_routing'].get('modelli_legacy', '')
                legacy_list = [m.strip().lower() for m in legacy_str.split(',') if m.strip()]
                
                model_name = key.lower()
                if value: # Aggiungi
                    if model_name not in legacy_list:
                        legacy_list.append(model_name)
                        self.config['motore_routing']['modelli_legacy'] = ", ".join(legacy_list)
                        self.modified = True
                else: # Rimuovi
                    if model_name in legacy_list:
                        legacy_list.remove(model_name)
                        self.config['motore_routing']['modelli_legacy'] = ", ".join(legacy_list)
                        self.modified = True
        except Exception as e:
            print(f"Errore in _set_value per {param.label}: {e}")

    def run(self):
        """Avvia l'editor interattivo con lock."""
        if not acquire_lock():
            print("Impossibile acquisire il lock. Editor già in esecuzione?")
            return
        
        try:
            result = None
            ui = UIManager(self.param_list, self._get_value, self._set_value)
            result = ui.run()
            
            import sys
            import time
            from core.i18n import translator
            
            if result == "REBOOT":
                if self.modified:
                    self._save_config()
                print(f"\n\033[91m{translator.t('rebooting_msg')}\033[0m")
                time.sleep(1)
                sys.exit(42)
                
            elif result == "SAVE":
                if self.modified:
                    self._save_config()
                # Auto-riavvio garantito se ci sono state modifiche salvate dall'utente
                print(f"\n\033[91m{translator.t('rebooting_msg')}\033[0m")
                time.sleep(1)
                sys.exit(42)
                
            elif result == "DISCARD":
                print(f"\n\033[93mUscita senza salvare. Le modifiche sono state scartate.\033[0m")
                # Nessun salvataggio, nessun riavvio
                
            else: # NO_CHANGES
                # Possiamo salvare solo se core.py ha pulito vecchi plugin, ma non serve riavviare
                if self.modified:
                    self._save_config()
                    
        finally:
            release_lock()