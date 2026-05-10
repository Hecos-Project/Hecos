import cv2
import os
import time
import sys

try:
    from hecos.core.logging import logger
    from hecos.core.i18n import translator
    from hecos.app.config import ConfigManager
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
    Plugin: Webcam & Vision
    Captures images from the system webcam or takes desktop screenshots.
    Both outputs can be passed to a Vision AI model for analysis.
    """

    def __init__(self):
        self.tag = "WEBCAM"
        self.desc = translator.t("plugin_webcam_desc")
        self.status = translator.t("plugin_webcam_status_online")
        self.routing_instructions = (
            "MULTIMODAL CAPABILITY: You DO have 'eyes'! You are natively connected to a visual multimodal core. "
            "Whenever the user asks you to look at the screen, see what is there, or analyze GUI/windows, "
            "you MUST actually execute the `desktop_screenshot` tool. The system will take the picture and feed it directly into your visual core! "
            "NEVER say you cannot see the image. Just call the tool, and in the next thought loop you will see it perfectly."
        )

        self.config_schema = {
            "save_directory": {
                "type": "str",
                "default": "snapshots",
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

    # ── Private helpers ────────────────────────────────────────────────────────

    def _get_save_dir(self) -> str:
        cfg = ConfigManager()
        save_dir = cfg.get_plugin_config(self.tag, "save_directory", "snapshots")
        os.makedirs(save_dir, exist_ok=True)
        return save_dir

    def _get_format(self) -> str:
        cfg = ConfigManager()
        return cfg.get_plugin_config(self.tag, "image_format", "jpg")

    # ── Public Tools ───────────────────────────────────────────────────────────

    def take_snapshot(self, target: str = "server") -> str:
        """
        Takes a photo using the computer's webcam and saves it to disk.
        Use this when the user asks to take a photo or to see what is in front of the camera.

        Args:
            target (str): "server" to use the local OS webcam hardware.
                          "client" to ask the user's browser/mobile device to take and upload a picture.
        """
        logger.debug(f"PLUGIN_{self.tag}", f"Snapshot protocol (target={target})")

        if target.lower() == "client":
            return "[CAMERA_SNAPSHOT_REQUEST]"

        cfg = ConfigManager()
        save_dir = self._get_save_dir()
        img_format = self._get_format()
        camera_index = cfg.get_plugin_config(self.tag, "camera_index", 0)
        delay = cfg.get_plugin_config(self.tag, "stabilization_delay", 0.5)

        try:
            cap = cv2.VideoCapture(camera_index)
            if not cap.isOpened():
                return translator.t("plugin_webcam_error_sensor")

            flush_frames = 5
            for _ in range(flush_frames):
                cap.read()
                if delay > 0:
                    time.sleep(delay / flush_frames)

            ret, frame = cap.read()
            cap.release()

            if not ret:
                return translator.t("plugin_webcam_error_read")

            timestamp = int(time.time())
            filename = f"hecos_snap_{timestamp}.{img_format}"
            full_path = os.path.join(save_dir, filename)
            cv2.imwrite(full_path, frame)
            logger.debug(f"PLUGIN_{self.tag}", f"Snapshot saved at {full_path}")
            return translator.t("plugin_webcam_snap_saved", path=full_path)

        except Exception as e:
            logger.error(f"PLUGIN_{self.tag}: Error: {e}")
            return translator.t("plugin_webcam_error_critical", error=str(e))

    def desktop_screenshot(self, monitor: int = 0) -> str:
        """
        Takes a screenshot of the entire desktop (or a specific monitor) and saves it to disk.
        Use this to let the AI see and describe what is currently on the screen.
        The returned file path can be sent to a Vision AI model for visual analysis.

        :param monitor: Monitor number to capture (0 = all monitors combined, 1 = primary). Default: 0.
        """
        try:
            monitor = int(monitor)
        except (ValueError, TypeError):
            monitor = 0
            
        img_format = self._get_format()
        timestamp = int(time.time())
        filename = f"hecos_desktop_{timestamp}.{img_format}"
        
        # Save to hecos/media/Hecos_screenshots
        hecos_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        save_dir = os.path.join(hecos_root, "media", "Hecos_screenshots")
        os.makedirs(save_dir, exist_ok=True)
        full_path = os.path.join(save_dir, filename)

        # Cleanup: Delete screenshots older than 5 minutes to avoid disk bloat
        try:
            now = time.time()
            for f in os.listdir(save_dir):
                if f.startswith("hecos_desktop_"):
                    fpath = os.path.join(save_dir, f)
                    if os.path.isfile(fpath) and os.stat(fpath).st_mtime < now - 300: # 5 minutes
                        try:
                            os.remove(fpath)
                        except Exception:
                            pass
        except Exception as e:
            logger.debug(f"[WEBCAM] Cleanup error: {e}")

        # Try mss (fastest, supports multi-monitor)
        try:
            import mss
            import mss.tools
            with mss.mss() as sct:
                monitors = sct.monitors
                idx = monitor if monitor < len(monitors) else 1
                shot = sct.grab(monitors[idx])
                mss.tools.to_png(shot.rgb, shot.size, output=full_path.replace(f".{img_format}", ".png"))
                # Rename if not PNG
                png_path = full_path.replace(f".{img_format}", ".png")
                if img_format != "png" and os.path.exists(png_path):
                    from PIL import Image
                    Image.open(png_path).save(full_path)
                    os.remove(png_path)
                elif img_format == "png":
                    full_path = png_path
            logger.info(f"[WEBCAM] desktop_screenshot (mss): {full_path}")
            return f"[WEBCAM] Desktop screenshot saved: {full_path}"
        except Exception as e:
            logger.debug(f"[WEBCAM] mss failed, trying fallback: {e}")
            
        # Fallback: Pillow ImageGrab (Windows/macOS only)
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab(all_screens=(monitor == 0))
            img.save(full_path)
            logger.info(f"[WEBCAM] desktop_screenshot (Pillow): {full_path}")
            return f"[WEBCAM] Desktop screenshot saved: {full_path}"
        except ImportError:
            pass

        # Final fallback: Windows API via pyautogui
        try:
            import pyautogui
            img = pyautogui.screenshot()
            img.save(full_path)
            logger.info(f"[WEBCAM] desktop_screenshot (pyautogui): {full_path}")
            return f"[WEBCAM] Desktop screenshot saved: {full_path}"
        except ImportError:
            pass

        return (
            "[WEBCAM] desktop_screenshot requires at least one of: "
            "mss (recommended), Pillow, or pyautogui.\n"
            "Install with: pip install mss  OR  pip install pillow"
        )


# ── Singleton ──────────────────────────────────────────────────────────────────
tools = WebcamTools()


def info():
    return {"tag": tools.tag, "desc": tools.desc}


def status():
    return tools.status