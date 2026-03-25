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
        models_ollama = []
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=1)
            if response.status_code == 200:
                for m in response.json().get('models', []):
                    models_ollama.append(m['name'])
                # Salva nel config per persistenza
                self.config_manager.set({str(i+1): name for i, name in enumerate(models_ollama)}, 'backend', 'ollama', 'modelli_disponibili')
                self.config_manager.save()
        except Exception as e:
            logger.debug("MODEL", f"Ollama dynamic fetch failed: {e}")
            # Fallback su cache
            models_ollama = list(config.get('backend', {}).get('ollama', {}).get('modelli_disponibili', {}).values())

        for m_name in models_ollama:
            all_models.append({"name": m_name, "type": "ollama", "provider": "local"})
                
        # 2. Recupero Modelli KOBOLD (Local)
        models_kobold = []
        try:
            url = config.get('backend', {}).get('kobold', {}).get('url', 'http://localhost:5001').rstrip('/') + '/api/v1/model'
            r = requests.get(url, timeout=1)
            if r.status_code == 200:
                model_name = r.json().get('result', 'kobold_model')
                models_kobold = [model_name]
                self.config_manager.set({"1": model_name}, 'backend', 'kobold', 'modelli_disponibili')
                self.config_manager.save()
        except Exception as e:
            logger.debug("MODEL", f"Kobold dynamic fetch failed: {e}")
            models_kobold = list(config.get('backend', {}).get('kobold', {}).get('modelli_disponibili', {}).values())

        for m_name in models_kobold:
            all_models.append({"name": m_name, "type": "kobold", "provider": "local"})

        # 3. Recupero Modelli CLOUD
        allow_cloud = config.get('llm', {}).get('allow_cloud', False)
        if allow_cloud:
            import os
            providers = config.get('llm', {}).get('providers', {})
            for provider_name, p_data in providers.items():
                api_key = p_data.get('api_key')
                
                # Fallback sulle variabili d'ambiente (OS) se non presente nel config
                if not api_key:
                    env_key_name = f"{provider_name.upper()}_API_KEY"
                    api_key = os.environ.get(env_key_name, '').strip().strip("'").strip('"')
                    if api_key:
                        logger.debug("MODEL", f"Using environment variable {env_key_name} for {provider_name} (starts with: {api_key[:5]}...).")
                    else:
                        logger.debug("MODEL", f"Environment variable {env_key_name} for {provider_name} not found.")

                cloud_models = []
                
                if provider_name in ["groq", "openai", "anthropic", "gemini"] and api_key:
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
        backend_attuale, modello_attuale = self.get_effective_model_info(config)
        
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
            logger.debug("MODEL", f"Unable to fetch model sizes: {e}")
        return model_sizes

    def _fetch_cloud_models(self, provider, api_key):
        """Tenta di recuperare la lista modelli direttamente dalle API del provider."""
        try:
            url = ""
            if provider == "groq":
                url = "https://api.groq.com/openai/v1/models"
            elif provider == "openai":
                url = "https://api.openai.com/v1/models"
            elif provider == "gemini":
                # Google Gemini (Google AI Studio)
                url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
                # For Gemini, the key is in the URL, not in the header
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json().get('models', [])
                    models = [m['name'].replace('models/', '') for m in data if 'name' in m]
                    logger.debug("MODEL", f"Fetched {len(models)} models from {provider}.")
                    return models
                else:
                    logger.errore(f"MODEL: {provider} API error {response.status_code}")
                    return []
            else:
                return []
            
            headers = {"Authorization": f"Bearer {api_key}"}
            response = requests.get(url, headers=headers, timeout=5) # Aumentato timeout
            if response.status_code == 200:
                data = response.json().get('data', [])
                models = [m['id'] for m in data]
                logger.debug("MODEL", f"Fetched {len(models)} models from {provider}.")
                return models
            else:
                logger.errore(f"MODEL: {provider} API error {response.status_code}: {response.text[:100]}")
        except Exception as e:
            logger.debug("MODEL", f"Fetch error for {provider}: {e}")
        return []
        
    @staticmethod
    def get_effective_model_info(config_dict):
        """Restituisce il backend e modello effettivo, gestendo i fallback sicuri."""
        backend_type = config_dict.get('backend', {}).get('tipo', 'ollama')
        allow_cloud = config_dict.get('llm', {}).get('allow_cloud', False)
        
        # Fallback a un backend locale se il cloud è disattivato ma risulta come attivo
        if backend_type == 'cloud' and not allow_cloud:
            backend_type = 'ollama'
            
        modello = config_dict.get('backend', {}).get(backend_type, {}).get('modello', 'N/D')
        return backend_type, modello
