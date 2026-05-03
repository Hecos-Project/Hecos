"""
Centralized management of application states.
"""

import threading

class StateManager:
    def __init__(self, initial_voice_status=True, initial_listening_status=True):
        self._voice_status = initial_voice_status
        self._listening_status = initial_listening_status
        self._last_esc = 0
        self._detected_voice_command = None
        self._system_processing = False
        self._system_status = "STARTUP"
        self._system_speaking = False
        self._last_voice_stop = 0
        self._push_to_talk = False
        self._ptt_hotkey = "ctrl+shift"
        
        # Telemetry for Dashboard live widgets
        self._last_tool = None
        self._last_model = None
        self._last_tokens_prompt = 0
        self._last_tokens_completion = 0
        
        self._event_queue = []
        self._lock = threading.Lock()

    def add_event(self, event_type, data=None):
        """Adds an event to the queue for the WebUI to consume."""
        with self._lock:
            self._event_queue.append({"type": event_type, "data": data})

    def pop_events(self):
        """Returns and clears all pending events."""
        with self._lock:
            events = list(self._event_queue)
            self._event_queue.clear()
            return events

    # Thread-safe properties
    @property
    def voice_status(self):
        with self._lock:
            return self._voice_status

    @voice_status.setter
    def voice_status(self, value):
        with self._lock:
            self._voice_status = value

    @property
    def listening_status(self):
        with self._lock:
            return self._listening_status

    @listening_status.setter
    def listening_status(self, value):
        with self._lock:
            self._listening_status = value

    @property
    def last_esc(self):
        with self._lock:
            return self._last_esc

    @last_esc.setter
    def last_esc(self, value):
        with self._lock:
            self._last_esc = value

    @property
    def detected_voice_command(self):
        with self._lock:
            return self._detected_voice_command

    @detected_voice_command.setter
    def detected_voice_command(self, value):
        with self._lock:
            self._detected_voice_command = value

    @property
    def system_processing(self):
        with self._lock:
            return self._system_processing

    @system_processing.setter
    def system_processing(self, value):
        with self._lock:
            self._system_processing = value

    @property
    def system_status(self):
        with self._lock:
            return self._system_status

    @system_status.setter
    def system_status(self, value):
        with self._lock:
            self._system_status = value

    @property
    def system_speaking(self):
        with self._lock:
            return self._system_speaking

    @system_speaking.setter
    def system_speaking(self, value):
        with self._lock:
            self._system_speaking = value

    @property
    def last_voice_stop(self):
        with self._lock:
            return self._last_voice_stop

    @last_voice_stop.setter
    def last_voice_stop(self, value):
        with self._lock:
            self._last_voice_stop = value

    @property
    def push_to_talk(self):
        with self._lock:
            return self._push_to_talk

    @push_to_talk.setter
    def push_to_talk(self, value):
        with self._lock:
            self._push_to_talk = value

    @property
    def ptt_hotkey(self):
        with self._lock:
            return self._ptt_hotkey

    @ptt_hotkey.setter
    def ptt_hotkey(self, value):
        with self._lock:
            self._ptt_hotkey = value

    # --- Telemetry Properties ---
    @property
    def last_tool(self):
        with self._lock: return self._last_tool

    @last_tool.setter
    def last_tool(self, value):
        with self._lock: self._last_tool = value

    @property
    def last_model(self):
        with self._lock: return self._last_model

    @last_model.setter
    def last_model(self, value):
        with self._lock: self._last_model = value

    @property
    def last_tokens_prompt(self):
        with self._lock: return self._last_tokens_prompt

    @last_tokens_prompt.setter
    def last_tokens_prompt(self, value):
        with self._lock: self._last_tokens_prompt = value

    @property
    def last_tokens_completion(self):
        with self._lock: return self._last_tokens_completion

    @last_tokens_completion.setter
    def last_tokens_completion(self, value):
        with self._lock: self._last_tokens_completion = value