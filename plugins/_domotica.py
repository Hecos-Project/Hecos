# plugins/domotica.py

def status():
    """
    Questa è la funzione che diagnostica.py cercherà automaticamente.
    Puoi simulare il controllo di luci, temperatura o serrature.
    """
    # Qui in futuro potresti mettere codice reale per connetterti a Home Assistant o simili
    dispositivi_online = 4
    temperatura_casa = 21.5
    
    return f"ONLINE ({dispositivi_online} disp. connessi) | Temp: {temperatura_casa}°C"