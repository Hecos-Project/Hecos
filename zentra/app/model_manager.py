"""
Management of LLM model selection and configuration.
"""

import requests
import os
from zentra.core.logging import logger

# CRITICAL: Disable LiteLLM remote cost map fetching to prevent startup timeouts
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
from zentra.core.i18n import translator

class ModelManager:
    def __init__(self, config_manager):
        self.config_manager = config_manager

    def get_available_models(self, fast_mode=False):
        """Fetches and returns a dictionary of categorized model names (Local + Cloud)."""
        config = self.config_manager.config
        categorized_models = {
            "Ollama (Local)": [],
            "Kobold (Local)": [],
            "Cloud": []
        }
        
        # 1. OLLAMA Models (Local)
        if fast_mode:
            cache = config.get('backend', {}).get('ollama', {}).get('available_models', {})
            categorized_models["Ollama (Local)"].extend(list(cache.values()))
        else:
            try:
                response = requests.get("http://localhost:11434/api/tags", timeout=1)
                if response.status_code == 200:
                    models_ollama = [m['name'] for m in response.json().get('models', [])]
                    self.config_manager.set({str(i+1): name for i, name in enumerate(models_ollama)}, 'backend', 'ollama', 'available_models')
                    self.config_manager.save()
                    for m_name in models_ollama:
                        categorized_models["Ollama (Local)"].append(m_name)
            except:
                # Fallback on cache
                cache = config.get('backend', {}).get('ollama', {}).get('available_models', {})
                categorized_models["Ollama (Local)"].extend(list(cache.values()))

        # 2. KOBOLD Models (Local)
        if fast_mode:
            cache = config.get('backend', {}).get('kobold', {}).get('available_models', {})
            categorized_models["Kobold (Local)"].extend(list(cache.values()))
        else:
            try:
                url = config.get('backend', {}).get('kobold', {}).get('url', 'http://localhost:5001').rstrip('/') + '/api/v1/model'
                r = requests.get(url, timeout=1)
                if r.status_code == 200:
                    model_name = r.json().get('result', 'kobold_model')
                    categorized_models["Kobold (Local)"].append(model_name)
            except:
                cache = config.get('backend', {}).get('kobold', {}).get('available_models', {})
                categorized_models["Kobold (Local)"].extend(list(cache.values()))

        # 3. CLOUD Models
        if config.get('llm', {}).get('allow_cloud', False):
            providers = config.get('llm', {}).get('providers', {})
            if fast_mode:
                for provider_name, p_data in providers.items():
                    cloud_models = p_data.get('models', [])
                    prov_key = f"Cloud ({provider_name.capitalize()})"
                    if prov_key not in categorized_models:
                        categorized_models[prov_key] = []
                    for m_name in cloud_models:
                        full_name = f"{provider_name}/{m_name}" if not m_name.startswith(f"{provider_name}/") else m_name
                        categorized_models[prov_key].append(full_name)
            else:
                import os
                try:
                    from zentra.core.keys.key_manager import KeyManager
                    key_mgr = KeyManager()
                except ImportError:
                    key_mgr = None
                    
                for provider_name, p_data in providers.items():
                    api_key = p_data.get('api_key')
                    if not api_key and key_mgr:
                        api_key = key_mgr.get_key(provider_name.lower())
                    elif not api_key:
                        # Fallback old style
                        api_key = os.environ.get(f"{provider_name.upper()}_API_KEY", "").strip().strip("'").strip('"')
                    
                    cloud_models = []
                    if api_key:
                        cloud_models = self._fetch_cloud_models(provider_name, api_key)
                    
                    # Merge user-defined custom models from config with dynamically fetched ones
                    custom_user_models = p_data.get('models', [])
                    for cm in custom_user_models:
                        # Normalize name
                        m_clean = cm.replace(f"{provider_name}/", "")
                        if m_clean not in cloud_models:
                            cloud_models.insert(0, m_clean)  # Put user models at the top
                            
                    if not cloud_models:
                        cloud_models = ["default-model-missing"]
                    
                    prov_key = f"Cloud ({provider_name.capitalize()})"
                    if prov_key not in categorized_models:
                        categorized_models[prov_key] = []
                        
                    for m_name in cloud_models:
                        full_name = f"{provider_name}/{m_name}" if not m_name.startswith(f"{provider_name}/") else m_name
                        categorized_models[prov_key].append(full_name)

        
        # Clean empty categories
        return {k: list(dict.fromkeys(v)) for k, v in categorized_models.items() if v}

    def get_effective_model(self, config_dict):
        """Returns the currently active model name."""
        backend_type, model = self.get_effective_model_info(config_dict)
        return model

    def handle_models(self, input_callback, prefetched=None):
        """Management F2 - User selection session.
        
        Args:
            input_callback: function to get user input.
            prefetched: optional pre-fetched categorized dict from get_available_models().
                        If None, will fetch fresh from servers.
        """
        categorized = prefetched if prefetched is not None else self.get_available_models()
        if not categorized:
            print(f"\033[91m{translator.t('no_models_found')}\033[0m")
            import time; time.sleep(2)
            return

        # Flatten for selection logic (preserving category order)
        flat_list = []
        for cat in categorized.values():
            flat_list.extend(cat)

        choice = input_callback(">> ")
        if choice and choice != "ESC":
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(flat_list):
                    new_model = flat_list[idx]
                    # Identify backend from model name
                    new_backend = "ollama"
                    if "/" in new_model:
                        new_backend = "cloud"
                    elif any(m in new_model.lower() for m in ["gpt", "claude", "gemini"]):
                        new_backend = "cloud"
                    
                    self.config_manager.set(new_backend, 'backend', 'type')
                    self.config_manager.set(new_model, 'backend', new_backend, 'model')
                    self.config_manager.save()
                    print(f"\n\033[92m{translator.t('model_set_success', model=new_model, type=new_backend)}\033[0m")
                else:
                    print(f"\n\033[91m{translator.t('invalid_index')}\033[0m")
            except:
                print(f"\n\033[91m{translator.t('selection_error')}\033[0m")
            import time; time.sleep(2)


    def _get_model_sizes(self):
        """Fetches model sizes from Ollama."""
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
        """Attempts to fetch the model list directly from the provider's APIs."""
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
                    logger.error("MODEL", f"{provider} API error {response.status_code}")
                    return []
            else:
                return []
            
            headers = {"Authorization": f"Bearer {api_key}"}
            response = requests.get(url, headers=headers, timeout=5) # Increased timeout
            if response.status_code == 200:
                data = response.json().get('data', [])
                models = [m['id'] for m in data]
                logger.debug("MODEL", f"Fetched {len(models)} models from {provider}.")
                return models
            else:
                # Use debug for discovery errors to prevent TUI flickering
                logger.debug("MODEL", f"{provider} API error {response.status_code}: {response.text[:100]}")
                # Log a single clear warning for restricted account
                if "restricted" in response.text.lower():
                     logger.warning("MODEL", f"Provider {provider} account is RESTRICTED/BLOCKED.")
        except Exception as e:
            logger.debug("MODEL", f"Fetch error for {provider}: {e}")
        return []
        
    @staticmethod
    def get_effective_model_info(config_dict):
        """Returns the effective backend and model, handling safe fallbacks."""
        backend_type = config_dict.get('backend', {}).get('type', 'ollama')
        allow_cloud = config_dict.get('llm', {}).get('allow_cloud', False)
        
        # Fallback to a local backend if cloud is disabled but appears active
        if backend_type == 'cloud' and not allow_cloud:
            backend_type = 'ollama'
            
        model = config_dict.get('backend', {}).get(backend_type, {}).get('model', 'N/D')
        return backend_type, model
