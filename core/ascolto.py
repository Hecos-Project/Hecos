import speech_recognition as sr
from . import voce
import json
import time

def ascolta():
    # Controllo ridondante: se sta parlando, non ascoltare affatto
    if voce.sta_parlando: 
        return ""
    
    try:
        with open('config.json', 'r') as f:
            conf = json.load(f)['ascolto']
    except:
        return ""

    r = sr.Recognizer()
    r.energy_threshold = conf['soglia_energia']
    r.dynamic_energy_threshold = False
    
    with sr.Microphone() as source:
        # Piccolo delay per evitare di sentire l'eco finale della voce
        if voce.sta_parlando: return ""
        
        try:
            # Regolazione rumore ambientale
            r.adjust_for_ambient_noise(source, duration=0.2)
            
            audio = r.listen(source, timeout=conf['timeout_silenzio'], 
                             phrase_time_limit=conf['limite_frase'])
            
            # Se ha iniziato a parlare MENTRE ascoltavo, scarta tutto
            if voce.sta_parlando: return ""
            
            testo = r.recognize_google(audio, language="it-IT", show_all=False)
            return testo.lower()
        except:
            return ""