import ctypes
import re
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from comtypes import CLSCTX_ALL
try:
    from zentra.core.logging import logger
    from zentra.core.i18n import translator
except ImportError:
    class DummyLogger:
        def debug(self, *args, **kwargs): print("[MEDIA_DEBUG]", *args)
        def error(self, *args, **kwargs): print("[MEDIA_ERR]", *args)
    logger = DummyLogger()
    class DummyTranslator:
        def t(self, key, **kwargs): return key
    translator = DummyTranslator()

class MediaTools:
    """
    Plugin: Media & Volume Control
    Allows managing system audio (volume, mute).
    """

    def __init__(self):
        self.tag = "MEDIA"
        self.desc = translator.t("plugin_media_desc")
        self.status = "ONLINE"
        self.config_schema = {}

    def _get_volume_control(self):
        """Obtains volume control using the most compatible method possible."""
        try:
            devices = AudioUtilities.GetSpeakers()
            if not devices:
                return None
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            return ctypes.cast(interface, ctypes.POINTER(IAudioEndpointVolume))
        except Exception as e:
            logger.error(f"MEDIA: Audio access error: {e}")
            return None

    def set_volume(self, level: str) -> str:
        """
        Sets the system volume to a specific level.
        
        :param level: The desired volume level, from 0 to 100.
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
            return "Please specify a number from 0 to 100."
        except Exception as e:
            logger.error(f"MEDIA: Volume error: {e}")
            return translator.t("plugin_media_error_internal", error=str(e))

    def set_mute(self, state: str) -> str:
        """
        Toggles system mute mode on or off.
        
        :param state: Use 'on' (to mute) or 'off' (to unmute).
        """
        try:
            volume = self._get_volume_control()
            if not volume:
                return translator.t("plugin_media_error_interface")

            cmd = state.lower().strip()
            if "on" in cmd or "mute" in cmd or "silenzio" in cmd:
                volume.SetMute(1, None)
                return translator.t("plugin_media_mute_on")
            
            if "off" in cmd or "unmute" in cmd or "attiva" in cmd:
                volume.SetMute(0, None)
                return translator.t("plugin_media_mute_off")

            return "Please specify 'on' or 'off'."
        except Exception as e:
            logger.error(f"MEDIA: Mute error: {e}")
            return translator.t("plugin_media_error_internal", error=str(e))

# Publicly instantiate the tool for export to the Core
tools = MediaTools()

# --- COMPATIBILITY SHIMS ---
def info():
    return {"tag": tools.tag, "desc": tools.desc}

def status():
    return tools.status