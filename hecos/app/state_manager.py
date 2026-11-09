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
        
        # Cross-pipeline chat / voice deduplication state
        self._last_chat_message = ""
        self._last_chat_time = 0.0
        
        self._event_queues = []
        self._lock = threading.Lock()

    def check_in(self):
        """Registers a new SSE client and returns its specific event queue."""
        import queue
        q = queue.Queue(maxsize=100)
        with self._lock:
            self._event_queues.append(q)
        return q

    def check_out(self, q):
        """Unregisters an SSE client queue."""
        with self._lock:
            if q in self._event_queues:
                self._event_queues.remove(q)

    def add_event(self, event_type, data=None):
        """Broadcasts an event to all connected WebUI SSE clients."""
        import queue
        event = {"type": event_type, "data": data}
        with self._lock:
            for q in self._event_queues:
                try:
                    q.put_nowait(event)
                except queue.Full:
                    pass

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

    # --- Cross-pipeline Message Deduplication ---
    def record_chat_message(self, message: str):
        """Records the most recent user chat message and its timestamp for deduplication."""
        import time
        with self._lock:
            self._last_chat_message = (message or "").strip()
            self._last_chat_time = time.time()

    def is_recent_duplicate(self, text: str, window_seconds: float = 6.0) -> bool:
        """Checks if a voice or chat message is a duplicate of a recently processed message."""
        import time
        with self._lock:
            if not self._last_chat_message or not text:
                return False
            elapsed = time.time() - self._last_chat_time
            if elapsed > window_seconds:
                return False
            return self._are_phrases_similar(self._last_chat_message, text)

    @staticmethod
    def _are_phrases_similar(phrase1: str, phrase2: str, threshold: float = 0.65) -> bool:
        if not phrase1 or not phrase2:
            return False
        import re
        def clean(s):
            s = s.lower().strip()
            s = re.sub(r'[^\w\s]', ' ', s)
            num_map = {'zero': '0', 'uno': '1', 'una': '1', 'un': '1', 'due': '2', 'tre': '3', 
                       'quattro': '4', 'cinque': '5', 'sei': '6', 'sette': '7', 'otto': '8', 'nove': '9', 'dieci': '10'}
            tokens = [num_map.get(t, t) for t in s.split()]
            return tokens

        tokens1 = clean(phrase1)
        tokens2 = clean(phrase2)
        if not tokens1 or not tokens2:
            return False
        if tokens1 == tokens2:
            return True

        set1, set2 = set(tokens1), set(tokens2)
        intersection = set1.intersection(set2)
        union = set1.union(set2)
        jaccard = len(intersection) / len(union) if union else 0.0
        min_len = min(len(set1), len(set2))
        overlap_ratio = len(intersection) / min_len if min_len > 0 else 0.0

        return jaccard >= threshold or overlap_ratio >= 0.75

