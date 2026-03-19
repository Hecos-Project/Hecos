import ctypes
import re
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from comtypes import CLSCTX_ALL

def info():
    return {
        "tag": "MEDIA",
        "desc": "Controllo hardware volume e mute.",
        "comandi": {
            "vol:0-100": "Regola volume master.",
            "mute:on/off": "Attiva o disattiva il silenzio."
        }
    }

def get_volume_control():
    """Ottiene il controllo volume usando il metodo più compatibile possibile."""
    try:
        devices = AudioUtilities.GetSpeakers()
        # GUID specifico per IAudioEndpointVolume (evita errori di attributo)
        interface = devices.Activate(
            IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return ctypes.cast(interface, ctypes.POINTER(IAudioEndpointVolume))
    except Exception as e:
        print(f"DEBUG AUDIO ERROR: {e}")
        return None

def esegui(comando):
    try:
        volume = get_volume_control()
        if not volume:
            return "Errore hardware: Interfaccia audio non raggiungibile."

        cmd = comando.lower().strip()

        # Ricerca numeri nel comando per il volume
        numeri = re.findall(r'\d+', cmd)
        if numeri:
            livello = int(numeri[0])
            livello = max(0, min(100, livello))
            volume.SetMasterVolumeLevelScalar(livello / 100.0, None)
            return f"Volume impostato al {livello}%."

        if "mute:on" in cmd or "silenzio" in cmd:
            volume.SetMute(1, None)
            return "Mute attivato."
        
        if "mute:off" in cmd or "attiva" in cmd:
            volume.SetMute(0, None)
            return "Mute disattivato."

        return "Comando media non riconosciuto."
    except Exception as e:
        return f"Errore interno MEDIA: {str(e)}"