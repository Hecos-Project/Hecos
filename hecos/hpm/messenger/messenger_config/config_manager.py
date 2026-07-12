"""
MODULE: Messenger Config Manager (Pydantic + TOML)
"""
from pathlib import Path
from pydantic import BaseModel, Field

try:
    from hecos.core.package_manager.config import HPMBaseConfigManager
except ImportError:
    class HPMBaseConfigManager:
        pass


class TelegramConfig(BaseModel):
    enabled: bool = False
    bot_token: str = ""
    default_chat_id: str = ""


class WhatsAppConfig(BaseModel):
    enabled: bool = False
    phone_country_code: str = "+39"
    send_as_single_block: bool = True
    use_template: bool = False
    template_id: str = ""


class DiscordConfig(BaseModel):
    enabled: bool = False
    webhook_url: str = ""
    default_channel: str = ""


class MessengerConfig(BaseModel):
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    whatsapp: WhatsAppConfig = Field(default_factory=WhatsAppConfig)
    discord: DiscordConfig = Field(default_factory=DiscordConfig)


_THIS_DIR = Path(__file__).parent.resolve()
_CONFIG_FILE   = _THIS_DIR / "messenger.toml"

_manager = None
if hasattr(HPMBaseConfigManager, "get"):
    # We use empty root_key "" here because previously messenger did not have a root key in the TOML file.
    # Wait, HPMBaseConfigManager requires a root key right now to dump properly, 
    # but we can pass "messenger" and adjust `get_config_obj` to just return manager.get()
    # It will automatically migrate or nest it under [messenger].
    _manager = HPMBaseConfigManager(MessengerConfig, _CONFIG_FILE, "messenger")


def get_config() -> dict:
    if _manager:
        return _manager.get().model_dump(mode='json')
    return MessengerConfig().model_dump(mode='json')


def save_config(data: dict) -> bool:
    if _manager:
        try:
            obj = MessengerConfig.model_validate(data)
            return _manager.save(obj)
        except Exception:
            return False
    return False


def get_config_obj() -> MessengerConfig:
    if _manager:
        return _manager.get()
    return MessengerConfig()

