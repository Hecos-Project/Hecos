import ctypes
import re
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from comtypes import CLSCTX_ALL
try:
    from core.logging import logger
    from core.i18n import translator
except ImportError:
    class DummyLogger:
        def debug(self, *args, **kwargs): print("[MEDIA_DEBUG]", *args)
        def errore(self, *args, **kwargs): print("[MEDIA_ERR]", *args)
    logger = DummyLogger()
    class DummyTranslator:
        def t(self, key, **kwargs): return key
    translator = DummyTranslator()

class MediaTools:
    """
    Plugin: Media & Volume Control
    Permette di gestire l'audio di sistema (volume, muto).
    """

    def __init__(self):
        self.tag = "MEDIA"
        self.desc = translator.t("plugin_media_desc")
        self.status = "ONLINE"
        self.config_schema = {}

    def _get_volume_control(self):
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

    def set_volume(self, level: str) -> str:
        """
        Imposta il volume di sistema a un livello specifico.
        
        :param level: Il livello di volume desiderato, da 0 a 100.
        """
        try:
            volume = self._get_volume_control()
            if not volume:
                return translator.t("plugin_media_error_interface")

            numeri = re.findall(r'\d+', str(level))
            if numeri:
                livello = int(numeri[0])
                livello = max(0, min(100, livello))
                volume.SetMasterVolumeLevelScalar(livello / 100.0, None)
                return translator.t("plugin_media_vol_success", level=livello)
            return "Specificare un numero da 0 a 100."
        except Exception as e:
            logger.errore(f"MEDIA: Errore volume: {e}")
            return translator.t("plugin_media_error_internal", error=str(e))

    def set_mute(self, state: str) -> str:
        """
        Attiva o disattiva la modalità silenziosa (muto) del sistema.
        
        :param state: Usare 'on' (per silenziare) o 'off' (per riattivare l'audio).
        """
        try:
            volume = self._get_volume_control()
            if not volume:
                return translator.t("plugin_media_error_interface")

            cmd = state.lower().strip()
            if "on" in cmd or "silenzio" in cmd:
                volume.SetMute(1, None)
                return translator.t("plugin_media_mute_on")
            
            if "off" in cmd or "attiva" in cmd:
                volume.SetMute(0, None)
                return translator.t("plugin_media_mute_off")

            return "Specificare 'on' o 'off'."
        except Exception as e:
            logger.errore(f"MEDIA: Errore mute: {e}")
            return translator.t("plugin_media_error_internal", error=str(e))

# Istanzia pubblicamente lo strumento per l'esportazione verso il Core
tools = MediaTools()

# --- COMPATIBILITY SHIMS ---
def info():
    return {"tag": tools.tag, "desc": tools.desc}

def status():
    return tools.status