"""
Classe principale ConfigEditor che coordina il caricamento, l'editor e il salvataggio.
"""

import json
import os
from .locks import acquire_lock, release_lock
from .parameters import build_parameter_list
from .ui import UIManager

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
        """Carica il file JSON."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Errore caricamento {self.config_path}: {e}")
            raise

    def _save_config(self):
        """Salva il file JSON se ci sono modifiche."""
        if self.modified:
            try:
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    json.dump(self.config, f, indent=4, ensure_ascii=False)
                print("\n✅ Configurazione salvata.")
            except Exception as e:
                print(f"\n❌ Errore salvataggio: {e}")

    def _get_value(self, param):
        """Restituisce il valore di un parametro dal config corrente."""
        try:
            # Determina il backend attivo
            backend_type = self.config.get('backend', {}).get('tipo', 'ollama')
            backend_config = self.config.get('backend', {}).get(backend_type, {})
            
            # Mappa le label ai nomi delle chiavi nel config
            key_mapping = {
                'Modello attivo': 'modello',
                'Temperatura': 'temperature',
                'Num predict': 'num_predict',
                'Contesto (ctx)': 'num_ctx',
                'Layer GPU': 'num_gpu',
                'Velocità voce': 'speed',
                'Tono voce': 'pitch',
                'Soglia energia': 'soglia_energia',
                'Timeout silenzio (s)': 'timeout_silenzio',
                'Rimuovi asterischi': 'rimuovi_asterischi',
                'Rimuovi parentesi tonde': 'rimuovi_parentesi_tonde',
                'Rimuovi parentesi quadre': 'rimuovi_parentesi_quadre',
                'Destinazione Log': 'destinazione',
                'Tipo Messaggi': 'tipo_messaggi',
            }
            
            # Trova la chiave corrispondente
            key = key_mapping.get(param.label, param.key)
            
            # Gestisci i diversi tipi di sezioni
            if param.section == 'backend':
                return backend_config.get(key)
            elif param.section == 'voce':
                return self.config.get('voce', {}).get(key)
            elif param.section == 'ascolto':
                return self.config.get('ascolto', {}).get(key)
            elif param.section == 'filtri':
                return self.config.get('filtri', {}).get(key)
            elif param.section == 'logging':
                return self.config.get('logging', {}).get(key)
            elif param.section == 'plugin':
                # Sezione plugin: accedi a config['plugins'][param.plugin_tag][key]
                plugins = self.config.get('plugins', {})
                plugin_cfg = plugins.get(param.plugin_tag, {})
                return plugin_cfg.get(key)
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
            
            # Mappa le label ai nomi delle chiavi nel config
            key_mapping = {
                'Modello attivo': 'modello',
                'Temperatura': 'temperature',
                'Num predict': 'num_predict',
                'Contesto (ctx)': 'num_ctx',
                'Layer GPU': 'num_gpu',
                'Velocità voce': 'speed',
                'Tono voce': 'pitch',
                'Soglia energia': 'soglia_energia',
                'Timeout silenzio (s)': 'timeout_silenzio',
                'Rimuovi asterischi': 'rimuovi_asterischi',
                'Rimuovi parentesi tonde': 'rimuovi_parentesi_tonde',
                'Rimuovi parentesi quadre': 'rimuovi_parentesi_quadre',
                'Destinazione Log': 'destinazione',
                'Tipo Messaggi': 'tipo_messaggi',
            }
            
            # Trova la chiave corrispondente
            key = key_mapping.get(param.label, param.key)
            
            # Gestisci i diversi tipi di sezioni
            if param.section == 'backend':
                if backend_type not in self.config['backend']:
                    self.config['backend'][backend_type] = {}
                old = self.config['backend'][backend_type].get(key)
                if old != value:
                    self.config['backend'][backend_type][key] = value
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
        except Exception as e:
            print(f"Errore in _set_value per {param.label}: {e}")

    def run(self):
        """Avvia l'editor interattivo con lock."""
        if not acquire_lock():
            print("Impossibile acquisire il lock. Editor già in esecuzione?")
            return
        
        try:
            ui = UIManager(self.param_list, self._get_value, self._set_value)
            result = ui.run()
            if result == "REBOOT":
                # Salva le modifiche e segnala il reboot
                if self.modified:
                    self._save_config()
                print("\n\033[91mRIavvio di Zentra in corso...\033[0m")
                import sys
                sys.exit(42)  # Codice speciale per il reboot
        finally:
            release_lock()
            if self.modified and result != "REBOOT":
                self._save_config()