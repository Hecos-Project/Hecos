import ctypes
import re
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from comtypes import CLSCTX_ALL
from core.logging import logger
from core.i18n import translator

def info():
    return {
        "tag": "MEDIA",
        "desc": translator.t("plugin_media_desc"),
        "comandi": {
            "vol:0-100": translator.t("plugin_media_vol_desc"),
            "mute:on/off": translator.t("plugin_media_mute_desc")
        }
    }

def status():
    """Stato del plugin."""
    return "ONLINE"

def config_schema():
    """
    Schema di configurazione per questo plugin.
    Attualmente non ci sono parametri configurabili, ma la funzione è presente
    per coerenza con la nuova architettura.
    """
    return {}

def get_volume_control():
    """Ottiene il controllo volume usando il metodo più compatibile possibile."""
    try:
        devices = AudioUtilities.GetSpeakers()
        if not devices:
            return None
        # Attivazione dell'interfaccia via IID standard
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        # Casting esplicito utilizzando QueryInterface per evitare AttributeError
        return ctypes.cast(interface, ctypes.POINTER(IAudioEndpointVolume))
    except Exception as e:
        logger.errore(f"MEDIA: Errore accesso audio: {e}")
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
        logger.errore(f"MEDIA: Errore esecuzione comando: {e}")
        return f"Errore interno MEDIA: {str(e)}"