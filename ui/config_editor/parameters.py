"""
Definizione dei parametri modificabili e delle loro caratteristiche.
Inclusi i plugin caricati dinamicamente.
"""

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
    if 'modelli_disponibili' in backend_config:
        models = list(backend_config['modelli_disponibili'].values())
        params.append(Parameter('backend', 'modello', 'Modello attivo', 'str', options=models))
    else:
        params.append(Parameter('backend', 'modello', 'Modello attivo', 'str'))
    
    # Parametri del backend
    params.append(Parameter('backend', 'temperature', 'Temperatura', 'float', 
                           min=0.0, max=2.0, step=0.1))
    params.append(Parameter('backend', 'num_predict', 'Num predict', 'int', 
                           min=100, max=2000, step=50))
    params.append(Parameter('backend', 'num_ctx', 'Contesto (ctx)', 'int', 
                           min=512, max=16384, step=512))
    params.append(Parameter('backend', 'num_gpu', 'Layer GPU', 'int', 
                           min=0, max=99, step=1))
    
    # --- SEZIONE VOCE (PIPER ENGINE) ---
    voce_conf = config.get('voce', {})
    params.append(Parameter('voce', 'speed', 'Velocità Voce', 'float', 
                           min=0.5, max=2.5, step=0.1))
    params.append(Parameter('voce', 'noise_scale', 'Variabilità Tono', 'float', 
                           min=0.0, max=1.0, step=0.05))
    params.append(Parameter('voce', 'noise_w', 'Fluidità Fonemi', 'float', 
                           min=0.0, max=1.0, step=0.05))
    params.append(Parameter('voce', 'sentence_silence', 'Pausa Frasi (sec)', 'float', 
                           min=0.0, max=3.0, step=0.1))

    # --- Ascolto ---
    ascolto = config.get('ascolto', {})
    params.append(Parameter('ascolto', 'soglia_energia', 'Soglia energia', 'int', 
                           min=100, max=1000, step=50))
    params.append(Parameter('ascolto', 'timeout_silenzio', 'Timeout silenzio (s)', 'int', 
                           min=1, max=10, step=1))

    # --- Filtri ---
    filtri = config.get('filtri', {})
    params.append(Parameter('filtri', 'rimuovi_asterischi', 'Rimuovi asterischi', 'bool'))
    params.append(Parameter('filtri', 'rimuovi_parentesi_tonde', 'Rimuovi parentesi tonde', 'bool'))
    params.append(Parameter('filtri', 'rimuovi_parentesi_quadre', 'Rimuovi parentesi quadre', 'bool'))

    # --- Logging ---
    logging_cfg = config.get('logging', {})
    params.append(Parameter('logging', 'destinazione', 'Destinazione Log', 'str', options=['chat', 'console']))
    params.append(Parameter('logging', 'tipo_messaggi', 'Tipo Messaggi', 'str', options=['info', 'debug', 'entrambi']))

    # --- Comando speciale RIAVVIA ---
    params.append(Parameter('system', 'reboot', 'RIAVVIA ZENTRA', 'command', 
                           command='reboot'))
    params.append(Parameter('system', 'lingua', 'Lingua Sistema', 'str', options=['it', 'en']))

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
            label = key.replace('_', ' ').capitalize()
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