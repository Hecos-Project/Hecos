import os
from pathlib import Path
from typing import TypeVar, Generic, Type, Dict, Any
from pydantic import BaseModel

try:
    import tomllib
except ImportError:
    import tomli as tomllib

try:
    import tomli_w
    _HAS_TOMLI_W = True
except ImportError:
    _HAS_TOMLI_W = False

from hecos.core.logging import logger

T = TypeVar('T', bound=BaseModel)

class HPMBaseConfigManager(Generic[T]):
    """
    Base generic class for managing HPM package configurations using Pydantic + TOML.
    Provides automatic validation, serialization, and default fallback.
    """
    def __init__(self, schema_cls: Type[T], config_path: Path | str, root_key: str):
        self.schema_cls = schema_cls
        self.config_path = Path(config_path)
        self.root_key = root_key
        
        # Instantiate defaults
        self.defaults = schema_cls()
        self._ensure_config_file()

    def _ensure_config_file(self):
        """Creates the config file with default values if it doesn't exist."""
        if not self.config_path.exists():
            self.save(self.defaults)

    def get(self) -> T:
        """Reads the TOML file and returns the validated Pydantic model instance."""
        try:
            raw = tomllib.loads(self.config_path.read_bytes().decode("utf-8"))
            if self.root_key in raw:
                return self.schema_cls.model_validate(raw[self.root_key])
            else:
                return self.defaults
        except Exception as e:
            logger.error(f"[{self.root_key.upper()}_CONFIG] Failed to read or parse config: {e}")
            return self.defaults

    def save(self, config_obj: T) -> bool:
        """Serializes the Pydantic model to the root_key block in the TOML file."""
        if not _HAS_TOMLI_W:
            logger.error(f"[{self.root_key.upper()}_CONFIG] tomli_w not installed. Cannot save config.")
            return False
        
        try:
            # Load existing content to preserve other top-level keys if present
            if self.config_path.exists():
                try:
                    raw = tomllib.loads(self.config_path.read_bytes().decode("utf-8"))
                except Exception:
                    raw = {}
            else:
                raw = {}
                
            # Dump the model using JSON-compatible types (resolves lists/dicts correctly for TOML)
            raw[self.root_key] = config_obj.model_dump(mode='json')
            
            toml_bytes = tomli_w.dumps(raw).encode("utf-8")
            self.config_path.write_bytes(toml_bytes)
            logger.debug(f"[{self.root_key.upper()}_CONFIG] Config saved.")
            return True
        except Exception as e:
            logger.error(f"[{self.root_key.upper()}_CONFIG] Failed to save config: {e}")
            return False

    def get_schema_json(self) -> Dict[str, Any]:
        """Returns the Pydantic JSON schema, useful for dynamic UI generation."""
        return self.schema_cls.model_json_schema()
