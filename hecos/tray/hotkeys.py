import threading
from hecos.tray.config import HECOS_PORT
from hecos.tray.utils import get_scheme

class TrayHotKeyManager:
    """
    Manages the Ctrl+Shift global hotkey directly from the user's active graphical
    session. Because the Hecos core runs as a Window Service in Session 0, it cannot
    see the interactive keyboard. This hooks from the Tray App and fires an HTTP webhook.
    """
    def __init__(self):
        self.listener = None
        self.pressed = set()
        self.is_active = False

    def start(self):
        try:
            from pynput.keyboard import Key, Listener
        except ImportError:
            print("[TRAY-PTT] pynput not installed. Global hotkeys via Tray App disabled.")
            return

        def _is_mod(target):
            if target == "ctrl":
                return Key.ctrl in self.pressed or Key.ctrl_l in self.pressed or Key.ctrl_r in self.pressed
            if target == "shift":
                return Key.shift in self.pressed or Key.shift_l in self.pressed or Key.shift_r in self.pressed
            return False

        def on_press(key):
            try:
                self.pressed.add(key)
                
                if _is_mod("ctrl") and _is_mod("shift") and not self.is_active:
                    self.is_active = True
                    self._fire_trigger("start")
            except Exception:
                pass

        def on_release(key):
            if key in self.pressed:
                try:
                    self.pressed.remove(key)
                except KeyError:
                    pass

            if self.is_active and not (_is_mod("ctrl") and _is_mod("shift")):
                self.is_active = False
                self._fire_trigger("stop")

        self.listener = Listener(on_press=on_press, on_release=on_release)
        self.listener.daemon = True
        self.listener.start()
        print("[TRAY-PTT] Global Hotkey (Ctrl+Shift) Listener started in User Session.")

    def _fire_trigger(self, action):
        def _do_fire():
            import urllib.request
            import ssl
            scheme = get_scheme()
            url = f"{scheme}://127.0.0.1:{HECOS_PORT}/api/remote-triggers/ptt/{action}"
            try:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                urllib.request.urlopen(url, timeout=2, context=ctx)
            except Exception as e:
                pass
                
        # Fire in a background thread so we don't block the pynput loop
        threading.Thread(target=_do_fire, daemon=True).start()

# Singleton instance
tray_hotkeys = TrayHotKeyManager()
