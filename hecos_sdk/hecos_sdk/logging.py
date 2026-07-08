import sys
import json

class SDKLogger:
    def __init__(self):
        pass

    def _send_log(self, level, msg):
        try:
            payload = {
                "type": "log",
                "level": level,
                "msg": str(msg)
            }
            sys.stdout.write(json.dumps(payload) + "\n")
            sys.stdout.flush()
        except Exception:
            pass

    def info(self, msg):
        self._send_log("info", msg)

    def warning(self, msg):
        self._send_log("warning", msg)

    def error(self, msg):
        self._send_log("error", msg)

    def debug(self, msg):
        self._send_log("debug", msg)

logger = SDKLogger()
