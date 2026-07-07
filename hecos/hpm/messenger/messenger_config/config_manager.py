"""
MODULE: Messenger Config Manager
"""
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib

try:
    import tomli_w
    _HAS_TOMLI_W = True
except ImportError:
    _HAS_TOMLI_W = False

_THIS_DIR = Path(__file__).parent.resolve()
_DEFAULTS_FILE = _THIS_DIR / "defaults.toml"
_CONFIG_FILE   = _THIS_DIR / "messenger.toml"

def get_config() -> dict:
    if not _CONFIG_FILE.exists():
        _create_from_defaults()
    try:
        return tomllib.loads(_CONFIG_FILE.read_bytes().decode("utf-8"))
    except Exception:
        return tomllib.loads(_DEFAULTS_FILE.read_bytes().decode("utf-8"))

def save_config(data: dict) -> bool:
    if not _HAS_TOMLI_W:
        return False
    try:
        _CONFIG_FILE.write_bytes(tomli_w.dumps(data).encode("utf-8"))
        return True
    except Exception:
        return False

def _create_from_defaults():
    save_config(tomllib.loads(_DEFAULTS_FILE.read_bytes().decode("utf-8")))

class _DummyConfig:
    def __init__(self, data: dict):
        self._data = data
    def __getattr__(self, name):
        return self._data.get(name)

class TelegramConfig(_DummyConfig): pass
class WhatsAppConfig(_DummyConfig): pass
class DiscordConfig(_DummyConfig): pass

class MessengerConfigObj:
    def __init__(self, data: dict):
        self.telegram = TelegramConfig(data.get("telegram", {}))
        self.whatsapp = WhatsAppConfig(data.get("whatsapp", {}))
        self.discord  = DiscordConfig(data.get("discord", {}))

def get_config_obj() -> MessengerConfigObj:
    return MessengerConfigObj(get_config())
