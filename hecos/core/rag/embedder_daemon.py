"""
MODULE: RAG Embedder Daemon (JSON IPC)
DESCRIPTION: Gestisce un subprocess Python isolato che esegue fastembed/onnxruntime.
             Pattern identico a PiperDaemon — JSON su stdin/stdout, auto-restart.

             Questo daemon gira nel processo principale di Hecos come CLIENT.
             Il modello ONNX è nel subprocess figlio (embedder_worker.py) — completamente
             isolato da Playwright/Chromium, eliminando il conflitto Win32 thread pool.
"""

import os
import sys
import json
import uuid
import threading
import subprocess
import time
from hecos.core.logging import logger


class EmbedderDaemon:
    """
    Client per il subprocess embedder_worker.py.
    Thread-safe. Auto-restart se il subprocess muore.
    """

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        self._model_name = model_name
        self._proc: subprocess.Popen | None = None
        self._lock = threading.Lock()
        self._ready_event = threading.Event()
        self._pending: dict[str, dict] = {}   # {req_id: {"event": Event, "result": dict}}
        self._pending_lock = threading.Lock()
        self._stdout_thread: threading.Thread | None = None
        self._dim: int = 384
        self._dead = False  # Set True on permanent failure

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def start(self):
        """Avvia il subprocess in modo non-bloccante e attende max 60s per 'ready'."""
        self._ensure_running()

    def _ensure_running(self):
        """Avvia/riavvia il subprocess se non è attivo. Thread-safe."""
        with self._lock:
            if self._proc is not None and self._proc.poll() is None:
                return  # già vivo

            worker_path = os.path.join(os.path.dirname(__file__), "embedder_worker.py")
            if not os.path.isfile(worker_path):
                logger.error("RAG][EmbedderDaemon", f"Worker script non trovato: {worker_path}")
                self._dead = True
                return

            logger.info("RAG][EmbedderDaemon", f"Avvio subprocess embedder ({self._model_name})...")

            kwargs: dict = {
                "stdin":  subprocess.PIPE,
                "stdout": subprocess.PIPE,
                "stderr": subprocess.PIPE,
            }
            if sys.platform == "win32":
                kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW

            try:
                self._ready_event.clear()
                self._proc = subprocess.Popen([sys.executable, worker_path], **kwargs)

                # Manda la configurazione (prima riga di stdin)
                config = json.dumps({"model_name": self._model_name}) + "\n"
                self._proc.stdin.write(config.encode("utf-8"))
                self._proc.stdin.flush()

                # Avvia il thread lettore stdout (async)
                if self._stdout_thread is None or not self._stdout_thread.is_alive():
                    self._stdout_thread = threading.Thread(
                        target=self._read_stdout_loop, daemon=True, name="EmbedderDaemon-stdout"
                    )
                    self._stdout_thread.start()

                logger.info("RAG][EmbedderDaemon", "Subprocess avviato — attendo 'ready'...")

            except Exception as e:
                logger.error("RAG][EmbedderDaemon", f"Impossibile avviare il subprocess: {e}")
                self._proc = None
                self._dead = True

    def _read_stdout_loop(self):
        """Thread background: legge JSON line-by-line dallo stdout del subprocess."""
        while self._proc and self._proc.poll() is None:
            try:
                raw = self._proc.stdout.readline()
                if not raw:
                    break
                line = raw.decode("utf-8", errors="replace").strip()
                if not line:
                    continue

                resp = json.loads(line)

                # ── Messaggio di stato ────────────────────────────────────────
                if resp.get("status") == "ready":
                    self._dim = resp.get("dim", 384)
                    self._ready_event.set()
                    logger.info("RAG][EmbedderDaemon", f"Embedder subprocess pronto (dim={self._dim}).")
                    continue

                if resp.get("status") == "error":
                    logger.error("RAG][EmbedderDaemon", f"Subprocess errore di avvio: {resp.get('error')}")
                    self._dead = True
                    self._ready_event.set()  # sblocca i waiter anche in caso di errore
                    continue

                # ── Risposta a una richiesta embed ────────────────────────────
                req_id = resp.get("id", "")
                with self._pending_lock:
                    if req_id in self._pending:
                        self._pending[req_id]["result"] = resp
                        self._pending[req_id]["event"].set()

            except json.JSONDecodeError as e:
                logger.warning("RAG][EmbedderDaemon", f"JSON non valido dallo stdout del worker: {e}")
            except Exception as e:
                logger.error("RAG][EmbedderDaemon", f"Errore lettura stdout: {e}")
                break

        # Il subprocess è morto — segnala tutti i waiter pendenti
        logger.warning("RAG][EmbedderDaemon", "Subprocess embedder terminato.")
        with self._pending_lock:
            for entry in self._pending.values():
                entry["result"] = {"error": "Worker subprocess died"}
                entry["event"].set()

    # ── Public API ─────────────────────────────────────────────────────────────

    def embed(self, texts: list[str], timeout: float = 30.0) -> list[list[float]]:
        """
        Invia una richiesta di embedding al subprocess e attende la risposta.
        Thread-safe. Timeout di 30s per richiesta.
        """
        if not texts:
            return []

        self._ensure_running()

        if self._dead:
            raise RuntimeError("[RAG][EmbedderDaemon] Daemon in stato di errore permanente.")

        if not self._ready_event.wait(timeout=60.0):
            raise TimeoutError("[RAG][EmbedderDaemon] Subprocess non pronto entro 60s.")

        if self._dead:
            raise RuntimeError("[RAG][EmbedderDaemon] Subprocess fallito durante il caricamento.")

        req_id = uuid.uuid4().hex
        event = threading.Event()
        with self._pending_lock:
            self._pending[req_id] = {"event": event, "result": None}

        # Invia la richiesta
        req = json.dumps({"id": req_id, "texts": texts}) + "\n"
        try:
            with self._lock:
                if self._proc and self._proc.poll() is None:
                    self._proc.stdin.write(req.encode("utf-8"))
                    self._proc.stdin.flush()
                else:
                    with self._pending_lock:
                        self._pending.pop(req_id, None)
                    raise RuntimeError("[RAG][EmbedderDaemon] Subprocess non raggiungibile.")
        except Exception as e:
            with self._pending_lock:
                self._pending.pop(req_id, None)
            raise RuntimeError(f"[RAG][EmbedderDaemon] IPC write error: {e}") from e

        # Attendi la risposta
        if not event.wait(timeout=timeout):
            with self._pending_lock:
                self._pending.pop(req_id, None)
            raise TimeoutError(f"[RAG][EmbedderDaemon] Timeout ({timeout}s) per richiesta {req_id}.")

        with self._pending_lock:
            result = self._pending.pop(req_id, {}).get("result", {})

        if "error" in result:
            raise RuntimeError(f"[RAG][EmbedderDaemon] Errore worker: {result['error']}")

        return result.get("vectors", [])

    @property
    def dimension(self) -> int:
        return self._dim

    def is_alive(self) -> bool:
        return self._proc is not None and self._proc.poll() is None


# ── Singleton ──────────────────────────────────────────────────────────────────

_instances: dict[str, EmbedderDaemon] = {}
_instances_lock = threading.Lock()


def get_daemon(model_name: str = "BAAI/bge-small-en-v1.5") -> EmbedderDaemon:
    """
    Restituisce (o crea) un EmbedderDaemon singleton per il modello specificato.
    Pattern identico a PiperDaemon.get_daemon().
    """
    global _instances
    with _instances_lock:
        if model_name not in _instances:
            daemon = EmbedderDaemon(model_name=model_name)
            _instances[model_name] = daemon
        return _instances[model_name]
