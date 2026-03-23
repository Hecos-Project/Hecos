"""
Gestione della selezione e configurazione dei modelli LLM.
"""

import requests
from core.logging import logger
from core.i18n import translator

class ModelManager:
    def __init__(self, config_manager):
        self.config_manager = config_manager

    def handle_modelli(self, input_digitale_sicuro_callback):
        """Gestione F2 - Selezione modelli universale (Ollama, Kobold, Cloud)."""
        print(f"\n\n\033[96m{translator.t('model_mgmt_title')}\033[0m")
        
        config = self.config_manager.config
        all_models = [] # Lista di dict: {"name": str, "type": str, "provider": str}
        model_sizes = self._get_model_sizes()
        
        # 1. Recupero Modelli OLLAMA (Local)
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=1)
            if response.status_code == 200:
                for m in response.json().get('models', []):
                    all_models.append({"name": m['name'], "type": "ollama", "provider": "local"})
        except:
            # Fallback su config
            for m in config.get('backend', {}).get('ollama', {}).get('modelli_disponibili', {}).values():
                all_models.append({"name": m, "type": "ollama", "provider": "local"})
                
        # 2. Recupero Modelli KOBOLD (Local)
        for m in config.get('backend', {}).get('kobold', {}).get('modelli_disponibili', {}).values():
            all_models.append({"name": m, "type": "kobold", "provider": "local"})

        # 3. Recupero Modelli CLOUD
        allow_cloud = config.get('llm', {}).get('allow_cloud', False)
        if allow_cloud:
            providers = config.get('llm', {}).get('providers', {})
            for provider_name, p_data in providers.items():
                api_key = p_data.get('api_key')
                cloud_models = []
                
                if provider_name in ["groq", "openai"] and api_key:
                    cloud_models = self._fetch_cloud_models(provider_name, api_key)
                
                if not cloud_models:
                    cloud_models = p_data.get('modelli', [])
                
                for m_name in cloud_models:
                    full_name = f"{provider_name}/{m_name}" if not m_name.startswith(f"{provider_name}/") else m_name
                    all_models.append({"name": full_name, "type": "cloud", "provider": provider_name})

        if not all_models:
            print(f"\033[91m{translator.t('no_models_found')}\033[0m")
            import time
            time.sleep(2)
            return

        # 4. Visualizzazione
        backend_attuale = config.get('backend', {}).get('tipo', 'ollama')
        modello_attuale = config.get('backend', {}).get(backend_attuale, {}).get('modello', '')
        
        print(translator.t("active_backend", backend=backend_attuale.upper(), model=modello_attuale))
        
        current_section = ""
        for idx, m in enumerate(all_models, 1):
            section = f"{m['type'].upper()} ({m['provider'].upper()})"
            if section != current_section:
                print(f"\n\033[34m--- {section} ---\033[0m")
                current_section = section
            
            prefisso = "\033[92m >> " if m['name'] == modello_attuale else "    "
            size = model_sizes.get(m['name'], "")
            size_str = f" \033[90m[{size}]\033[0m" if size else ""
            
            print(f"{prefisso}[{idx:2}] {m['name']}{size_str}\033[0m")

        print(f"\n\033[93m{translator.t('select_model_index')}\033[0m")
        scelta = input_digitale_sicuro_callback(">> ")
        
        if scelta and scelta != "ESC":
            try:
                idx = int(scelta) - 1
                if 0 <= idx < len(all_models):
                    target = all_models[idx]
                    nuovo_modello = target['name']
                    nuovo_tipo = target['type']
                    
                    self.config_manager.set(nuovo_tipo, 'backend', 'tipo')
                    self.config_manager.set(nuovo_modello, 'backend', nuovo_tipo, 'modello')
                    
                    self.config_manager.save()
                    print(f"\n\033[92m{translator.t('model_set_success', model=nuovo_modello, type=nuovo_tipo)}\033[0m")
                else:
                    print(f"\n\033[91m{translator.t('invalid_index')}\033[0m")
            except:
                print(f"\n\033[91m{translator.t('selection_error')}\033[0m")
            import time
            time.sleep(2)

    def _get_model_sizes(self):
        """Recupera le dimensioni dei modelli da Ollama."""
        model_sizes = {}
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code == 200:
                data = response.json()
                for model in data.get('models', []):
                    name = model.get('name')
                    size = model.get('size', 0)
                    if size > 1024**3:
                        size_str = f"{size/(1024**3):.1f} GB"
                    elif size > 1024**2:
                        size_str = f"{size/(1024**2):.1f} MB"
                    else:
                        size_str = f"{size/1024:.0f} KB"
                    model_sizes[name] = size_str
        except Exception as e:
            logger.debug("MODEL", f"Impossibile recuperare dimensioni modelli: {e}")
        return model_sizes

    def _fetch_cloud_models(self, provider, api_key):
        """Tenta di recuperare la lista modelli direttamente dalle API del provider."""
        try:
            url = ""
            if provider == "groq":
                url = "https://api.groq.com/openai/v1/models"
            elif provider == "openai":
                url = "https://api.openai.com/v1/models"
            else:
                return []
            
            headers = {"Authorization": f"Bearer {api_key}"}
            response = requests.get(url, headers=headers, timeout=2)
            if response.status_code == 200:
                data = response.json().get('data', [])
                return [m['id'] for m in data]
        except:
            pass
        return []
