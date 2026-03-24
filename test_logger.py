import json
import logging
from core.logging import logger as log_mod
from app.config import ConfigManager

if __name__ == "__main__":
    cm = ConfigManager()
    log_mod.init_logger(cm.config)
    
    # Let's see what handlers the root logger has
    root_logger = logging.getLogger()
    print("Root handlers:", root_logger.handlers)
    
    # See what handlers LiteLLM has
    llm_logger = logging.getLogger("LiteLLM")
    print("LiteLLM handlers:", llm_logger.handlers)
    
    # Send a debug log
    log_mod.debug("LiteLLM", "This is a test debug message that should NOT go to stdout")
    log_mod.info("LiteLLM", "This is an info message that should NOT go to stdout if console is active")
    
    print("Test complete.")
