"""
Definizione dei parametri modificabili e delle loro caratteristiche.
"""

class Parameter:
    """
    Rappresenta un parametro di configurazione con metadati per l'editor.
    """
    def __init__(self, section, key, label, param_type, **kwargs):
        self.section = section
        self.key = key
        self.label = label
        self.type = param_type  # 'int', 'float', 'bool', 'str', 'command'
        self.min = kwargs.get('min')
        self.max = kwargs.get('max')
        self.step = kwargs.get('step')
        self.options = kwargs.get('options')  # per stringhe con scelta
        self.command = kwargs.get('command')  # per comandi speciali

def build_parameter_list(config):
    """
    Costruisce la lista di parametri a partire dalla configurazione corrente.
    """
    params = []

    # Backend e Modelli
    backend_type = config.get('backend', {}).get('tipo', 'ollama')
    backend_config = config.get('backend', {}).get(backend_type, {})
    
    # Modello attivo (dal backend)
    if 'modelli_disponibili' in backend_config:
        models = list(backend_config['modelli_disponibili'].values())
        params.append(Parameter('backend', backend_type, 'Modello attivo', 'str', options=models))
    else:
        params.append(Parameter('backend', backend_type, 'Modello attivo', 'str'))
    
    # Parametri del backend
    params.append(Parameter('backend', backend_type, 'Temperatura', 'float', 
                           min=0.0, max=2.0, step=0.1))
    params.append(Parameter('backend', backend_type, 'Num predict', 'int', 
                           min=100, max=2000, step=50))
    params.append(Parameter('backend', backend_type, 'Contesto (ctx)', 'int', 
                           min=512, max=16384, step=512))
    params.append(Parameter('backend', backend_type, 'Layer GPU', 'int', 
                           min=0, max=99, step=1))
    
    # --- SEZIONE VOCE (PIPER ENGINE) ---
    voce_conf = config.get('voce', {})
    
    # Velocità (Length Scale inversa)
    params.append(Parameter('voce', 'speed', 'Velocità Voce', 'float', 
                           min=0.5, max=2.5, step=0.1))
    
    # Intonazione (Noise Scale) - Rende la voce più "emotiva" o più "robotica"
    params.append(Parameter('voce', 'noise_scale', 'Variabilità Tono', 'float', 
                           min=0.0, max=1.0, step=0.05))
    
    # Fluidità (Noise W) - Controlla la naturalezza dei legami tra fonemi
    params.append(Parameter('voce', 'noise_w', 'Fluidità Fonemi', 'float', 
                           min=0.0, max=1.0, step=0.05))
    
    # Pausa tra frasi
    params.append(Parameter('voce', 'sentence_silence', 'Pausa Frasi (sec)', 'float', 
                           min=0.0, max=3.0, step=0.1))

    # Ascolto
    ascolto = config.get('ascolto', {})
    params.append(Parameter('ascolto', 'soglia_energia', 'Soglia energia', 'int', 
                           min=100, max=1000, step=50))
    params.append(Parameter('ascolto', 'timeout_silenzio', 'Timeout silenzio (s)', 'int', 
                           min=1, max=10, step=1))

    # Filtri
    filtri = config.get('filtri', {})
    params.append(Parameter('filtri', 'rimuovi_asterischi', 'Rimuovi asterischi', 'bool'))
    params.append(Parameter('filtri', 'rimuovi_parentesi_tonde', 'Rimuovi parentesi tonde', 'bool'))
    params.append(Parameter('filtri', 'rimuovi_parentesi_quadre', 'Rimuovi parentesi quadre', 'bool'))

    # --- COMANDI SPECIALI ---
    params.append(Parameter('system', 'reboot', 'RIAVVIA AURA', 'command', 
                           command='reboot', options=None))

    return params