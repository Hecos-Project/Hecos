import os
import glob
import json
from hecos.core.i18n import translator

class Parameter:
    """
    Rappresenta un parametro di configurazione con metadati per l'editor.
    """
    def __init__(self, section, key, label, param_type, **kwargs):
        self.section = section          # 'backend', 'voice', 'listening', 'filtri', 'logging', 'plugin'
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
    
    # Active model (from backend) - read-only, change with F2
    lbl_modello = translator.t("label_active_model")
    if 'available_models' in backend_config:
        models = list(backend_config['available_models'].values())
        params.append(Parameter('backend', 'model', lbl_modello, 'str', options=models, readonly=True))
    else:
        params.append(Parameter('backend', 'model', lbl_modello, 'str', readonly=True))
    
    # Riga informativa: mostra il nome del modello globale per riferimento rapido nel pannello plugin
    lbl_f2_hint = translator.t("label_f2_model_hint")
    params.append(Parameter(
        'backend', '_f2_hint', lbl_f2_hint, 'info',
        readonly=True,
        info_value=active_model_value
    ))
    
    # --- Artificial Intelligence (Special Instructions) ---
    params.append(Parameter('ai', 'special_instructions', translator.t("label_special_instructions"), 'str'))
    params.append(Parameter('ai', 'save_special_instructions', translator.t("label_save_special_instructions"), 'bool'))
    params.append(Parameter('ai', 'clear_instructions', translator.t("label_clear_special_instructions"), 'command', command='clear_instructions'))

    # --- LLM Section ---
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
    
    # --- Voice Section (Piper Engine) ---
    voice_conf = config.get('voice', {})
    
    try:
        hecos_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        piper_path_dir = os.path.join(hecos_root, 'bin', 'piper')
        onnx_files = [os.path.basename(f) for f in glob.glob(os.path.join(piper_path_dir, "*.onnx"))]
        if not onnx_files: onnx_files = ["it_IT-aurora-medium.onnx"]
        percorsi_onnx = [os.path.join(piper_path_dir, f) for f in onnx_files]
    except Exception:
        # Fallback se la root non è determinabile
        percorsi_onnx = [os.path.join("bin", "piper", "it_IT-aurora-medium.onnx")]
        
    params.append(Parameter('voice', 'onnx_model', translator.t("label_modello_voce"), 'str', options=percorsi_onnx))
    
    params.append(Parameter('voice', 'speed', translator.t("label_speed"), 'float', 
                           min=0.5, max=2.5, step=0.1))
    params.append(Parameter('voice', 'noise_scale', translator.t("label_noise_scale"), 'float', 
                           min=0.0, max=1.0, step=0.05))
    params.append(Parameter('voice', 'noise_w', translator.t("label_noise_w"), 'float', 
                           min=0.0, max=1.0, step=0.05))
    params.append(Parameter('voice', 'sentence_silence', translator.t("label_sentence_silence"), 'float', 
                           min=0.0, max=3.0, step=0.1))

    # --- Listening ---
    listening = config.get('listening', {})
    params.append(Parameter('listening', 'energy_threshold', translator.t("label_energy_threshold"), 'int', 
                           min=100, max=1000, step=50))
    params.append(Parameter('listening', 'silence_timeout', translator.t("label_silence_timeout"), 'int', 
                           min=1, max=10, step=1))
    params.append(Parameter('listening', 'phrase_limit', translator.t("label_phrase_limit"), 'int', 
                           min=5, max=60, step=5))
    params.append(Parameter('listening', 'push_to_talk', 'Enable Push-To-Talk (PTT)', 'bool'))
    params.append(Parameter('listening', 'ptt_hotkey', 'PTT Hotkey Shortcut', 'str'))

    # --- Filters ---
    filters = config.get('filters', {})
    filter_opts = ['none', 'voice', 'text', 'both']
    params.append(Parameter('filters', 'remove_asterisks', translator.t("label_rimuovi_asterischi"), 'str', options=filter_opts))
    params.append(Parameter('filters', 'remove_round_brackets', translator.t("label_rimuovi_parentesi_tonde"), 'str', options=filter_opts))
    params.append(Parameter('filters', 'remove_square_brackets', translator.t("label_rimuovi_parentesi_quadre"), 'str', options=filter_opts))

    # --- Logging ---
    logging_cfg = config.get('logging', {})
    params.append(Parameter('logging', 'destination', translator.t("label_destinazione_log"), 'str', options=['chat', 'console', 'file_only']))
    params.append(Parameter('logging', 'message_types', translator.t("label_tipo_messaggi"), 'str', options=['info', 'debug', 'both']))

    # --- Cognition (Memory System) ---
    params.append(Parameter('cognition', 'memory_enabled',          'Memory System',                 'bool'))
    params.append(Parameter('cognition', 'episodic_memory',         'Save Conversations',            'bool'))
    params.append(Parameter('cognition', 'clear_on_restart',        'Clear History on Restart',      'bool'))
    params.append(Parameter('cognition', 'max_history_messages',    'Max History Messages',          'int'))
    params.append(Parameter('cognition', 'include_identity_context','Inject Identity Context',       'bool'))
    params.append(Parameter('cognition', 'include_self_awareness',  'Inject Self‑Awareness',         'bool'))
    params.append(Parameter('cognition', 'clear_history', 'Clear History Now', 'command', command='clear_memory'))

    # --- Comando speciale RIAVVIA e opzioni di sistema ---
    params.append(Parameter('system', 'fast_boot', translator.t("label_avvio_rapido"), 'bool'))
    params.append(Parameter('system', 'flask_debug', 'Flask Debug Mode', 'bool'))
    params.append(Parameter('system', 'language', translator.t("label_lingua_system"), 'str', options=['it', 'en']))
    params.append(Parameter('system', 'reboot', translator.t("label_reboot"), 'command', 
                           command='reboot'))
    params.append(Parameter('system', 'save_exit', translator.t("label_save_exit"), 'command', 
                           command='save_exit'))

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
            
            # Special handling for model selection (dropdown)
            kwargs = {}
            if key == "llm_model":
                if 'available_models' in backend_config:
                    kwargs['options'] = [""] + list(backend_config['available_models'].values())
                else:
                    if config.get('llm', {}).get('allow_cloud', False):
                        cloud_models = []
                        for provider in config.get('llm', {}).get('providers', {}).values():
                            cloud_models.extend(provider.get('models', []))
                        kwargs['options'] = [""] + cloud_models
                # Passes global model as hint for display
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