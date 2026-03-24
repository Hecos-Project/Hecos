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
    """
    return {}

def get_volume_control():
    """Ottiene il controllo volume usando il metodo più compatibile possibile."""
    try:
        devices = AudioUtilities.GetSpeakers()
        if not devices:
            return None
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return ctypes.cast(interface, ctypes.POINTER(IAudioEndpointVolume))
    except Exception as e:
        logger.errore(f"MEDIA: Audio access error: {e}")
        return None

def esegui(comando):
    try:
        volume = get_volume_control()
        if not volume:
            return translator.t("plugin_media_error_interface")

        cmd = comando.lower().strip()

        # Ricerca numeri nel comando per il volume
        numeri = re.findall(r'\d+', cmd)
        if numeri:
            livello = int(numeri[0])
            livello = max(0, min(100, livello))
            volume.SetMasterVolumeLevelScalar(livello / 100.0, None)
            return translator.t("plugin_media_vol_success", level=livello)

        if "mute:on" in cmd or "silenzio" in cmd:
            volume.SetMute(1, None)
            return translator.t("plugin_media_mute_on")
        
        if "mute:off" in cmd or "attiva" in cmd:
            volume.SetMute(0, None)
            return translator.t("plugin_media_mute_off")

        return translator.t("plugin_media_cmd_unrecognized")
    except Exception as e:
        logger.errore(f"MEDIA: Errore esecuzione comando: {e}")
        return translator.t("plugin_media_error_internal", error=str(e))