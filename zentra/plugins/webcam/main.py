import cv2
import os
import time
try:
    from zentra.core.logging import logger
    from zentra.core.i18n import translator
    from zentra.core.constants import SNAPSHOTS_DIR
    # NOTE: SNAPSHOTS_DIR now points to zentra/media/screenshots (centralized media)
    from app.config import ConfigManager
except ImportError:
    class DummyLogger:
        def debug(self, *args, **kwargs): print("[CAM_DEBUG]", *args)
        def error(self, *args, **kwargs): print("[CAM_ERR]", *args)
    logger = DummyLogger()
    class DummyTranslator:
        def t(self, key, **kwargs): return key
    translator = DummyTranslator()
    class DummyConfigMgr:
        def __init__(self): self.config = {}
        def get_plugin_config(self, tag, key, default): return default
    ConfigManager = DummyConfigMgr

class WebcamTools:
    """
    Plugin: Webcam & Hardware Sensor
    Allows Zentra to take photographs using the system webcam.
    """

    def __init__(self):
        self.tag = "WEBCAM"
        self.desc = translator.t("plugin_webcam_desc")
        self.status = translator.t("plugin_webcam_status_online")
        
        self.config_schema = {
            "save_directory": {
                "type": "str",
                "default": "screenshots",
                "description": translator.t("plugin_webcam_save_dir_desc")
            },
            "image_format": {
                "type": "str",
                "default": "jpg",
                "options": ["jpg", "png"],
                "description": translator.t("plugin_webcam_img_format_desc")
            },
            "camera_index": {
                "type": "int",
                "default": 0,
                "min": 0,
                "max": 10,
                "description": translator.t("plugin_webcam_cam_index_desc")
            },
            "stabilization_delay": {
                "type": "float",
                "default": 0.5,
                "min": 0.0,
                "max": 2.0,
                "description": translator.t("plugin_webcam_stab_delay_desc")
            }
        }

    def take_snapshot(self, target: str = "server") -> str:
        """
        Takes a photo using the computer's webcam and saves it to disk.
        Use this tool when the user asks to take a photo or look at something.
        
        Args:
            target (str): "server" to use the local OS webcam hardware.
                          "client" to ask the user's remote device (smartphone/browser) 
                                   to take a picture and auto-upload it.
        """
        logger.debug(f"PLUGIN_{self.tag}", f"Executing snapshot protocol (Target: {target})")
        
        if target.lower() == "client":
            return "[CAMERA_SNAPSHOT_REQUEST]"
        
        cfg = ConfigManager()
        save_dir = cfg.get_plugin_config(self.tag, "save_directory", "snapshots")
        img_format = cfg.get_plugin_config(self.tag, "image_format", "jpg")
        camera_index = cfg.get_plugin_config(self.tag, "camera_index", 0)
        delay = cfg.get_plugin_config(self.tag, "stabilization_delay", 0.5)
        
        try:
            # Standardize snapshot directory to stay inside zentra/
            # If the user sets a relative path, we join it with SNAPSHOTS_DIR root
            if not os.path.isabs(save_dir):
                save_dir = os.path.join(os.path.dirname(SNAPSHOTS_DIR), save_dir)
            
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)

            cap = cv2.VideoCapture(camera_index)
            
            if not cap.isOpened():
                return translator.t("plugin_webcam_error_sensor")

            # Flush the stale buffer to avoid grabbing old cached OS frames
            # We read a few transient frames during the stabilization period
            flush_frames = 5
            for i in range(flush_frames):
                cap.read()
                if delay > 0:
                    time.sleep(delay / flush_frames)
            
            # Now take the final fresh frame
            ret, frame = cap.read()
            if ret:
                timestamp = int(time.time())
                filename = f"zentra_snap_{timestamp}.{img_format}"
                full_path = os.path.join(save_dir, filename)
                cv2.imwrite(full_path, frame)
                cap.release()
                logger.debug(f"PLUGIN_{self.tag}", f"Snapshot saved at {full_path}")
                return translator.t("plugin_webcam_snap_saved", path=full_path)
            
            cap.release()
            return translator.t("plugin_webcam_error_read")

        except Exception as e:
            logger.error(f"PLUGIN_{self.tag}: Error: {e}")
            return translator.t("plugin_webcam_error_critical", error=str(e))

# Publicly instantiate the tool for exporting to Core
tools = WebcamTools()

# --- COMPATIBILITY SHIMS ---
def info():
    return {"tag": tools.tag, "desc": tools.desc}

def status():
    return tools.status