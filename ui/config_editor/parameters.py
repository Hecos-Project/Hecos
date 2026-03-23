from core.i18n import translator

class Parameter:
    """
    Rappresenta un parametro di configurazione con metadati per l'editor.
    """
    def __init__(self, section, key, label, param_type, **kwargs):
        self.section = section          # 'backend', 'voce', 'ascolto', 'filtri', 'logging', 'plugin'
        self.key = key                  # nome nel config.json
        self.label = label              # nome visualizzato
        self.type = param_type          # 'int', 'float', 'bool', 'str', 'command'
        self.min = kwargs.get('min')
        self.max = kwargs.get('max')
        self.step = kwargs.get('step')
        self.options = kwargs.get('options')    # per stringhe con scelta
        self.command = kwargs.get('command')    # per comandi speciali
        self.plugin_tag = kwargs.get('plugin_tag')  # se section == 'plugin', indica il tag del plugin

def build_parameter_list(config):
    """
    Costruisce la lista di parametri a partire dalla configurazione corrente,
    includendo anche i plugin attivi.
    """
    params = []

    # --- Backend e Modelli (esistenti) ---
    backend_type = config.get('backend', {}).get('tipo', 'ollama')
    backend_config = config.get('backend', {}).get(backend_type, {})
    
    # Modello attivo (dal backend)
    lbl_modello = translator.t("label_active_model")
    if 'modelli_disponibili' in backend_config:
        models = list(backend_config['modelli_disponibili'].values())
        params.append(Parameter('backend', 'modello', lbl_modello, 'str', options=models))
    else:
        params.append(Parameter('backend', 'modello', lbl_modello, 'str'))
    
    # --- Sezione LLM ---
    params.append(Parameter('llm', 'allow_cloud', translator.t("label_llm_allow_cloud", default="Cloud"), 'bool'))
    params.append(Parameter('llm', 'debug_llm', "Debug LiteLLM (Console)", 'bool'))
    
    # --- API Keys Cloud ---
    if config.get('llm', {}).get('allow_cloud', False):
        params.append(Parameter('llm_openai', 'api_key', 'OpenAI API Key', 'str'))
        params.append(Parameter('llm_anthropic', 'api_key', 'Anthropic API Key', 'str'))
        params.append(Parameter('llm_groq', 'api_key', 'Groq API Key', 'str'))
        params.append(Parameter('llm_gemini', 'api_key', 'Gemini API Key', 'str'))
    
    # Parametri del backend
    params.append(Parameter('backend', 'temperature', translator.t("label_temperature"), 'float', 
                           min=0.0, max=2.0, step=0.1))
    params.append(Parameter('backend', 'num_predict', translator.t("label_num_predict"), 'int', 
                           min=100, max=2000, step=50))
    params.append(Parameter('backend', 'num_ctx', translator.t("label_num_ctx"), 'int', 
                           min=512, max=16384, step=512))
    params.append(Parameter('backend', 'num_gpu', translator.t("label_num_gpu"), 'int', 
                           min=0, max=99, step=1))
    
    # --- SEZIONE VOCE (PIPER ENGINE) ---
    voce_conf = config.get('voce', {})
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
    params.append(Parameter('logging', 'tipo_messaggi', translator.t("label_tipo_messaggi"), 'str', options=['info', 'debug', 'entrambi']))

    # --- Comando speciale RIAVVIA ---
    params.append(Parameter('system', 'reboot', translator.t("label_reboot"), 'command', 
                           command='reboot'))
    params.append(Parameter('system', 'lingua', translator.t("label_lingua_sistema"), 'str', options=['it', 'en']))

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
            label = translator.t(f"plugin_{plugin_tag.lower()}_{key}_desc", default=key.replace('_', ' ').capitalize())
            # Aggiungi il parametro con sezione 'plugin' e plugin_tag
            params.append(Parameter(
                section='plugin',
                key=key,
                label=label,
                param_type=param_type,
                plugin_tag=plugin_tag,
                # eventualmente min/max/step potrebbero essere letti dallo schema,
                # ma per ora li omettiamo e lasciamo la modifica libera
            ))

    return params