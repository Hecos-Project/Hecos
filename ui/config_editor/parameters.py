import os
import glob
from core.i18n import translator

class Parameter:
    """
    Rappresenta un parametro di configurazione con metadati per l'editor.
    """
    def __init__(self, section, key, label, param_type, **kwargs):
        self.section = section          # 'backend', 'voce', 'ascolto', 'filtri', 'logging', 'plugin'
        self.key = key                  # nome nel config.json
        self.label = label              # nome visualizzato
        self.type = param_type          # 'int', 'float', 'bool', 'str', 'command', 'info'
        self.min = kwargs.get('min')
        self.max = kwargs.get('max')
        self.step = kwargs.get('step')
        self.options = kwargs.get('options')    # per stringhe con scelta
        self.command = kwargs.get('command')    # per comandi speciali
        self.plugin_tag = kwargs.get('plugin_tag')  # se section == 'plugin', indica il tag del plugin
        self.readonly = kwargs.get('readonly', False)  # se True, non è modificabile dall'utente
        self.info_value = kwargs.get('info_value', None) # per il tipo 'info': valore statico da mostrare
        self.global_default_model = kwargs.get('global_default_model', None) # hint per plugin modello_llm

def build_parameter_list(config):
    """
    Costruisce la lista di parametri a partire dalla configurazione corrente,
    includendo anche i plugin attivi.
    """
    params = []

    # --- Backend e Modelli (esistenti) ---
    from app.model_manager import ModelManager
    backend_type, active_model_value = ModelManager.get_effective_model_info(config)
    backend_config = config.get('backend', {}).get(backend_type, {})
    
    # Modello attivo (dal backend) - sola lettura, si modifica con F2
    lbl_modello = translator.t("label_active_model")
    if 'modelli_disponibili' in backend_config:
        models = list(backend_config['modelli_disponibili'].values())
        params.append(Parameter('backend', 'modello', lbl_modello, 'str', options=models, readonly=True))
    else:
        params.append(Parameter('backend', 'modello', lbl_modello, 'str', readonly=True))
    
    # Riga informativa: mostra il nome del modello globale per riferimento rapido nel pannello plugin
    lbl_f2_hint = translator.t("label_f2_model_hint")
    params.append(Parameter(
        'backend', '_f2_hint', lbl_f2_hint, 'info',
        readonly=True,
        info_value=active_model_value
    ))
    
    # --- Sezione LLM ---
    params.append(Parameter('llm', 'allow_cloud', translator.t("label_llm_allow_cloud"), 'bool'))
    params.append(Parameter('llm', 'debug_llm', translator.t("label_debug_llm"), 'bool'))
    
    # --- API Keys Cloud ---
    if config.get('llm', {}).get('allow_cloud', False):
        params.append(Parameter('llm_openai', 'api_key', 'OpenAI API Key', 'str'))
        params.append(Parameter('llm_anthropic', 'api_key', 'Anthropic API Key', 'str'))
        params.append(Parameter('llm_groq', 'api_key', 'Groq API Key', 'str'))
        params.append(Parameter('llm_gemini', 'api_key', 'Gemini API Key', 'str'))
    
    # Parametri del backend (Ollama)
    params.append(Parameter('ollama', 'temperature', translator.t("label_temperature"), 'float', 
                           min=0.0, max=2.0, step=0.1))
    params.append(Parameter('ollama', 'num_predict', translator.t("label_num_predict"), 'int', 
                           min=100, max=2000, step=50))
    params.append(Parameter('ollama', 'num_ctx', translator.t("label_num_ctx"), 'int', 
                           min=512, max=16384, step=512))
    params.append(Parameter('ollama', 'num_gpu', translator.t("label_num_gpu"), 'int', 
                           min=-1, max=99, step=1))
    
    # --- SEZIONE VOCE (PIPER ENGINE) ---
    voce_conf = config.get('voce', {})
    
    try:
        piper_path_dir = r"C:\piper"
        onnx_files = [os.path.basename(f) for f in glob.glob(os.path.join(piper_path_dir, "*.onnx"))]
        if not onnx_files: onnx_files = ["en_US-lessac-medium.onnx"]
        percorsi_onnx = [os.path.join(piper_path_dir, f) for f in onnx_files]
    except Exception:
        percorsi_onnx = [r"C:\piper\en_US-lessac-medium.onnx"]
        
    params.append(Parameter('voce', 'modello_onnx', translator.t("label_modello_voce"), 'str', options=percorsi_onnx))
    
    params.append(Parameter('voce', 'speed', translator.t("label_speed"), 'float', 
                           min=0.5, max=2.5, step=0.1))
    params.append(Parameter('voce', 'noise_scale', translator.t("label_noise_scale"), 'float', 
                           min=0.0, max=1.0, step=0.05))
    params.append(Parameter('voce', 'noise_w', translator.t("label_noise_w"), 'float', 
                           min=0.0, max=1.0, step=0.05))
    params.append(Parameter('voce', 'sentence_silence', translator.t("label_sentence_silence"), 'float', 
                           min=0.0, max=3.0, step=0.1))

    # --- Ascolto ---
    ascolto = config.get('ascolto', {})
    params.append(Parameter('ascolto', 'soglia_energia', translator.t("label_soglia_energia"), 'int', 
                           min=100, max=1000, step=50))
    params.append(Parameter('ascolto', 'timeout_silenzio', translator.t("label_timeout_silenzio"), 'int', 
                           min=1, max=10, step=1))

    # --- Filtri ---
    filtri = config.get('filtri', {})
    params.append(Parameter('filtri', 'rimuovi_asterischi', translator.t("label_rimuovi_asterischi"), 'bool'))
    params.append(Parameter('filtri', 'rimuovi_parentesi_tonde', translator.t("label_rimuovi_parentesi_tonde"), 'bool'))
    params.append(Parameter('filtri', 'rimuovi_parentesi_quadre', translator.t("label_rimuovi_parentesi_quadre"), 'bool'))

    # --- Logging ---
    logging_cfg = config.get('logging', {})
    params.append(Parameter('logging', 'destinazione', translator.t("label_destinazione_log"), 'str', options=['chat', 'console', 'file_only']))
    params.append(Parameter('logging', 'tipo_messaggi', translator.t("label_tipo_messaggi"), 'str', options=['info', 'debug', 'both']))

    # --- Comando speciale RIAVVIA e opzioni di sistema ---
    params.append(Parameter('system', 'avvio_rapido', translator.t("label_avvio_rapido"), 'bool'))
    params.append(Parameter('system', 'lingua', translator.t("label_lingua_system"), 'str', options=['it', 'en']))
    params.append(Parameter('system', 'reboot', translator.t("label_reboot"), 'command', 
                           command='reboot'))

    # --- Motore: Routing (Dual Engine) ---
    params.append(Parameter('motore_routing', 'modalita', translator.t("label_routing_mode"), 'str', 
                           options=['auto', 'forza_nativo', 'forza_legacy']))
    params.append(Parameter('motore_routing', 'modelli_legacy', translator.t("label_routing_models"), 'str'))

    # --- Selezione Dinamica Modelli Legacy ---
    import requests
    models_by_provider = {
        'ollama': [],
        'kobold': [],
        'openai': [],
        'anthropic': [],
        'groq': [],
        'gemini': [],
        'other': []
    }
    
    def _add_model(name):
        if '/' in name:
            prov = name.split('/')[0].lower()
            if prov in models_by_provider:
                if name not in models_by_provider[prov]: models_by_provider[prov].append(name)
            else:
                if name not in models_by_provider['other']: models_by_provider['other'].append(name)
        else:
            if name not in models_by_provider['ollama']: models_by_provider['ollama'].append(name)

    # 0. Modelli persistenti nel config
    for b_type in ['ollama', 'kobold']:
        b_conf = config.get('backend', {}).get(b_type, {})
        for m_name in b_conf.get('modelli_disponibili', {}).values():
            _add_model(m_name)
    
    # 1. Scansione Live OLLAMA
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=1.0)
        if r.status_code == 200:
            for m in r.json().get('models', []): _add_model(m['name'])
    except: pass
    
    # 2. Scansione Live KOBOLD
    try:
        kb_url = config.get('backend', {}).get('kobold', {}).get('url', 'http://localhost:5001').rstrip('/') + '/api/v1/model'
        r = requests.get(kb_url, timeout=0.5)
        if r.status_code == 200:
            kb_model = r.json().get('result')
            if kb_model: _add_model(kb_model)
    except: pass

    # 3. Cloud (da config)
    allow_cloud = config.get('llm', {}).get('allow_cloud', False)
    if allow_cloud:
        providers = config.get('llm', {}).get('providers', {})
        for p_name, p_data in providers.items():
            for m_name in p_data.get('modelli', []):
                full_name = f"{p_name}/{m_name}" if not m_name.startswith(p_name+"/") else m_name
                _add_model(full_name)
                    
    # 4. Modelli già in stringa legacy
    legacy_str = config.get('motore_routing', {}).get('modelli_legacy', '')
    for m in [s.strip() for s in legacy_str.split(',') if s.strip()]:
        _add_model(m)

    # Genera i parametri raggruppati
    for provider, models in models_by_provider.items():
        if not models: continue
        section_name = f"legacy_{provider}"
        for model in sorted(models):
            params.append(Parameter(section_name, model, f"Legacy Mode: {model}", 'bool'))

    # --- PLUGINS (dinamici) ---
    plugins_section = config.get('plugins', {})
    for plugin_tag, plugin_cfg in plugins_section.items():
        # Per ogni chiave il cui valore è un tipo semplice, creiamo un parametro
        for key, value in plugin_cfg.items():
            # Ignora dizionari e liste (non modificabili dall'editor)
            if isinstance(value, (dict, list)):
                continue
            # Determina il tipo
            if isinstance(value, bool):
                param_type = 'bool'
            elif isinstance(value, int):
                param_type = 'int'
            elif isinstance(value, float):
                param_type = 'float'
            else:
                param_type = 'str'
            # Crea una label leggibile
            label_key = f"plugin_{plugin_tag.lower()}_{key}_desc"
            label = translator.t(label_key)
            if label == label_key:
                # Se manca la traduzione, usa una versione pulita della chiave
                label = key.replace('_', ' ').capitalize()
            
            # Gestione speciale per la selezione del modello (dropdown)
            kwargs = {}
            if key == "modello_llm":
                if 'modelli_disponibili' in backend_config:
                    kwargs['options'] = [""] + list(backend_config['modelli_disponibili'].values())
                else:
                    if config.get('llm', {}).get('allow_cloud', False):
                        cloud_models = []
                        for provider in config.get('llm', {}).get('providers', {}).values():
                            cloud_models.extend(provider.get('modelli', []))
                        kwargs['options'] = [""] + cloud_models
                # Passa il modello globale come hint per il display
                kwargs['global_default_model'] = active_model_value

            # Aggiungi il parametro con sezione 'plugin' e plugin_tag
            params.append(Parameter(
                section='plugin',
                key=key,
                label=label,
                param_type=param_type,
                plugin_tag=plugin_tag,
                **kwargs
            ))

    return params