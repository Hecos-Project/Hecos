"""
Separate thread management.
"""

import threading
import time
from zentra.core.audio import listen, voice
from zentra.core.logging import logger

class AscoltoThread(threading.Thread):
    def __init__(self, state_manager):
        super().__init__(daemon=True)
        self.state = state_manager
        self.name = "PassiveListening"

    def run(self):
        logger.info("[LISTENING THREAD] Initialized.")
        while True:
            # Skip mic listening if web UI owns audio
            if (self.state.stt_source == 'system' and
                self.state.listening_status and 
                not self.state.system_speaking and 
                not self.state.system_processing):
                text = listen.listen(state=self.state)
                if text and len(text.strip()) > 1:
                    logger.info(f"[LISTENING THREAD] Input detected: '{text}'")
                    self.state.detected_voice_command = text
            time.sleep(0.2)