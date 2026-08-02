import os
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None
try:
    import tomli_w
    _HAS_TOMLI_W = True
except ImportError:
    _HAS_TOMLI_W = False

class ConfigManager:
    def __init__(self, config_dir: str):
        self.config_dir = config_dir
        self.config_file = os.path.join(config_dir, "autonomous_agent.toml")
        
        self.config = {
            "trust_mode": "ask",          # 'ask', 'trusted_only', 'allow'
            "max_auto_installs": 3,
            "reflection_schedule": "daily"
        }
        self.load()

    def load(self):
        if tomllib and os.path.isfile(self.config_file):
            try:
                with open(self.config_file, "rb") as f:
                    data = tomllib.load(f)
                    self.config.update(data)
            except Exception:
                pass

    def save(self):
        if _HAS_TOMLI_W:
            os.makedirs(self.config_dir, exist_ok=True)
            with open(self.config_file, "wb") as f:
                tomli_w.dump(self.config, f)
