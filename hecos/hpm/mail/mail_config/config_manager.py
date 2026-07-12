from pydantic import BaseModel, ConfigDict
from hecos.core.system.module_state import _BASE_DIR
from hecos.config.hpm_base_config_manager import HPMBaseConfigManager
import os

class MailConfig(BaseModel):
    model_config = ConfigDict(extra='allow')
    enabled: bool = True
    lazy_load: bool = True
    mail_address: str = ""
    mail_app_password: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_security: str = "STARTTLS"
    imap_host: str = ""
    imap_port: int = 993
    imap_security: str = "SSL"
    max_messages: int = 100
    sync_on_open: bool = True
    auto_detect_provider: bool = True

_manager = HPMBaseConfigManager(
    plugin_id="mail",
    config_model=MailConfig,
    defaults_file=os.path.join(os.path.dirname(__file__), "defaults.toml")
)

def get_config() -> dict:
    return _manager.get_config()

def save_config(new_config: dict) -> bool:
    try:
        obj = MailConfig.model_validate(new_config)
        return _manager.save(obj)
    except Exception as e:
        print(f"[MAIL] Config save error: {e}")
        return False
