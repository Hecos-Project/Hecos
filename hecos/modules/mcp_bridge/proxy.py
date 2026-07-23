import os
import json
import queue
import subprocess
import threading
import time
from typing import Dict, List, Any, Optional

# Global counter per server name (persists across manual reloads)
_GLOBAL_RESTART_COUNTS: Dict[str, int] = {}
_GLOBAL_RESTART_LOCK = threading.Lock()

try:
    from hecos.core.logging import logger
except ImportError:
    class _L:
        def info(self, m): print(f"[MCP] {m}")
        def error(self, m): print(f"[MCP ERR] {m}")
        def debug(self, m): pass
        def warning(self, m): print(f"[MCP WARN] {m}")
    logger = _L()

from .constants import (
    MCP_PROTOCOL_VERSION, MCP_CALL_TIMEOUT, MCP_INIT_TIMEOUT,
    MCP_TOOL_RETRIES, MCP_TOOL_RETRY_SLEEP,
    MCP_WATCHDOG_INTERVAL, MCP_RECONNECT_DELAY
)

class MCPProxy:
    """
    Manages a single MCP server connection via stdio.
    """
    def __init__(self, name: str, command: str, args: List[str] = None,
                 env: Dict[str, str] = None, call_timeout: int = MCP_CALL_TIMEOUT):
        self.name         = name
        self.command      = command
        self.args         = args or []
        self.env          = {**os.environ, **(env or {})}
        self.call_timeout = call_timeout

        self.process: Optional[subprocess.Popen] = None
        self.tools: List[dict] = []
        self.status = "starting"  # starting | connected | failed | reconnecting | stopped
        self.last_error = ""      # Last stderr line for UI reporting

        self._msg_id  = 0
        self._id_lock = threading.Lock()

        # Per-request response queues keyed by msg_id
        self._pending: Dict[int, queue.Queue] = {}
        self._pending_lock = threading.Lock()

        # Control events
        self._stop_event  = threading.Event()
        self._ready_event = threading.Event()  # set after initialize handshake

        # Background threads
        self._reader_thread   = None
        self._stderr_thread   = None
        self._watchdog_thread = None

        # Watchdog crash-restart tracking
        self._restart_count = 0

    def start(self):
        self._stop_event.clear()
        self._ready_event.clear()
        self.status = "starting"
        self.tools  = []

        try:
            full_cmd = [self.command] + self.args
            logger.info("MCP_BRIDGE", f"[{self.name}] Starting: {' '.join(str(x) for x in full_cmd)}")

            # On Windows, suppress the console window that subprocess would otherwise open
            popen_kwargs = {}
            if os.name == "nt":
                popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                popen_kwargs["startupinfo"] = startupinfo

            self.process = subprocess.Popen(
                full_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                env=self.env,
                **popen_kwargs,
            )
        except Exception as e:
            logger.error("MCP_BRIDGE", f"[{self.name}] Failed to spawn process: {e}")
            self.status = "failed"
            return

        self._reader_thread   = threading.Thread(target=self._reader_loop,   daemon=True, name=f"mcp-reader-{self.name}")
        self._stderr_thread   = threading.Thread(target=self._stderr_loop,   daemon=True, name=f"mcp-stderr-{self.name}")
        self._watchdog_thread = threading.Thread(target=self._watchdog_loop, daemon=True, name=f"mcp-watchdog-{self.name}")

        self._reader_thread.start()
        self._stderr_thread.start()
        self._watchdog_thread.start()

        threading.Thread(target=self._initialize_and_discover, daemon=True,
                         name=f"mcp-init-{self.name}").start()

    def stop(self):
        logger.info("MCP_BRIDGE", f"[{self.name}] Stopping.")
        self.status = "stopped"
        self._stop_event.set()

        with self._pending_lock:
            for q in self._pending.values():
                q.put(None)
            self._pending.clear()

        p = self.process
        if p:
            try:
                p.stdin.close()
            except Exception:
                pass
            try:
                if os.name == 'nt':
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
                else:
                    p.terminate()
                    p.wait(timeout=3)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass
            self.process = None

    def _reader_loop(self):
        try:
            while not self._stop_event.is_set():
                if not self.process or not self.process.stdout:
                    break
                if self.process.poll() is not None:
                    break

                try:
                    line = self.process.stdout.readline()
                except Exception:
                    break

                if not line:
                    break

                line = line.strip()
                if not line:
                    continue

                if not line.startswith("{"):
                    logger.debug("MCP_BRIDGE", f"[{self.name}] stdout noise: {line[:120]}")
                    continue

                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    logger.debug("MCP_BRIDGE", f"[{self.name}] Malformed JSON: {line[:120]}")
                    continue

                msg_id = msg.get("id")
                if msg_id is not None:
                    with self._pending_lock:
                        q = self._pending.get(msg_id)
                    if q:
                        q.put(msg)
                    else:
                        logger.debug("MCP_BRIDGE", f"[{self.name}] Response for unknown id={msg_id} discarded.")
                else:
                    logger.debug("MCP_BRIDGE", f"[{self.name}] Notification: {line[:200]}")
        finally:
            with self._pending_lock:
                for q in self._pending.values():
                    q.put(None)
            logger.debug("MCP_BRIDGE", f"[{self.name}] Reader thread exited.")

    def _stderr_loop(self):
        try:
            while not self._stop_event.is_set():
                if not self.process or not self.process.stderr:
                    break
                try:
                    line = self.process.stderr.readline()
                except Exception:
                    break
                if not line:
                    break
                line = line.strip()
                if line:
                    logger.warning("MCP_BRIDGE", f"[{self.name}:stderr] {line}")
                    # Save the most relevant error for the UI
                    # (Avoid overwriting with generic empty lines)
                    self.last_error = line

            if self.process and self.process.stderr:
                try:
                    for line in self.process.stderr:
                        line = line.strip()
                        if line:
                            logger.warning("MCP_BRIDGE", f"[{self.name}:stderr] {line}")
                            self.last_error = line
                except Exception:
                    pass
        finally:
            logger.debug("MCP_BRIDGE", f"[{self.name}] Stderr thread exited.")

    def _watchdog_loop(self):
        """Checks process health. Restarts on crash with exponential backoff.
        Gives up after MAX_RESTARTS consecutive failures (global, persists across reloads)."""
        MAX_RESTARTS = 3  # hard limit — prevents process pile-up

        while not self._stop_event.is_set():
            time.sleep(MCP_WATCHDOG_INTERVAL)

            if self._stop_event.is_set():
                break

            if not self.process:
                continue

            if self.process.poll() is not None:
                if self._stop_event.is_set():
                    break

                # Use global counter so manual reloads don't reset it
                with _GLOBAL_RESTART_LOCK:
                    _GLOBAL_RESTART_COUNTS[self.name] = _GLOBAL_RESTART_COUNTS.get(self.name, 0) + 1
                    global_count = _GLOBAL_RESTART_COUNTS[self.name]

                if global_count > MAX_RESTARTS:
                    logger.error("MCP_BRIDGE",
                        f"[{self.name}] Crashed {global_count} times total. "
                        "Giving up to prevent process leak. Restart Hecos to retry."
                    )
                    self.status = "failed"
                    self.process = None
                    return

                # Exponential backoff: 10s, 20s, 40s
                delay = 10 * (2 ** (global_count - 1))
                logger.warning("MCP_BRIDGE",
                    f"[{self.name}] Process exited (code {self.process.returncode}). "
                    f"Restart attempt {global_count}/{MAX_RESTARTS} in {delay}s..."
                )
                self.status = "reconnecting"
                self.process = None  # clear before sleep so is_alive() returns False

                # Wait with stop-event check so we don't block shutdown
                for _ in range(int(delay)):
                    if self._stop_event.is_set():
                        return
                    time.sleep(1)

                if not self._stop_event.is_set():
                    # Clean restart: stop old threads first, then re-spawn
                    self._do_restart()
                    return  # new watchdog thread launched by _do_restart

        logger.debug("MCP_BRIDGE", f"[{self.name}] Watchdog thread exited.")

    def _do_restart(self):
        """Clean restart: kills old process (if any) and spawns fresh threads.
        Called only by the watchdog after cooldown delay."""
        logger.info("MCP_BRIDGE", f"[{self.name}] Performing clean restart.")
        # Kill any zombie process that might still be around
        if self.process:
            try:
                if os.name == 'nt':
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(self.process.pid)],
                                   capture_output=True, timeout=5)
                else:
                    self.process.kill()
            except Exception:
                pass
            self.process = None
        # Now do a fresh start (spawns new process + threads)
        self.start()

    def _next_id(self) -> int:
        with self._id_lock:
            self._msg_id += 1
            return self._msg_id

    def _send(self, method: str, params: dict, timeout: float) -> Optional[dict]:
        if not self.process or self.process.poll() is not None:
            logger.error("MCP_BRIDGE", f"[{self.name}] Cannot send {method!r}: process not running.")
            return None

        msg_id = self._next_id()
        response_q: queue.Queue = queue.Queue(maxsize=1)

        with self._pending_lock:
            self._pending[msg_id] = response_q

        try:
            payload = json.dumps({
                "jsonrpc": "2.0",
                "method":  method,
                "params":  params,
                "id":      msg_id,
            })
            self.process.stdin.write(payload + "\n")
            self.process.stdin.flush()
        except Exception as e:
            logger.error("MCP_BRIDGE", f"[{self.name}] Write error on {method!r}: {e}")
            with self._pending_lock:
                self._pending.pop(msg_id, None)
            return None

        try:
            response = response_q.get(timeout=timeout)
        except queue.Empty:
            logger.error("MCP_BRIDGE", f"[{self.name}] Timeout ({timeout}s) waiting for {method!r} id={msg_id}.")
            response = None
        finally:
            with self._pending_lock:
                self._pending.pop(msg_id, None)

        return response

    def _initialize_and_discover(self):
        time.sleep(1)

        logger.info("MCP_BRIDGE", f"[{self.name}] Sending initialize handshake (protocol {MCP_PROTOCOL_VERSION})...")
        init_resp = self._send("initialize", {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "hecos-mcp-bridge", "version": "2.0"},
        }, timeout=MCP_INIT_TIMEOUT)

        if not init_resp or "result" not in init_resp:
            logger.warning("MCP_BRIDGE", 
                f"[{self.name}] No valid initialize response -- "
                "server may not require handshake, continuing."
            )
        else:
            srv = init_resp["result"].get("serverInfo", {})
            logger.info("MCP_BRIDGE", 
                f"[{self.name}] Handshake OK -- server: {srv.get('name', 'unknown')} {srv.get('version', '')}")
            try:
                notif = json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
                self.process.stdin.write(notif + "\n")
                self.process.stdin.flush()
            except Exception:
                pass

        self._ready_event.set()

        for attempt in range(1, MCP_TOOL_RETRIES + 1):
            if self._stop_event.is_set():
                return

            resp = self._send("tools/list", {}, timeout=MCP_CALL_TIMEOUT)
            if resp and "result" in resp:
                self.tools = resp["result"].get("tools", [])
                self.status = "connected"
                self._restart_count = 0  # Reset on successful connection
                logger.info("MCP_BRIDGE", f"[{self.name}] Ready -- {len(self.tools)} tool(s) discovered.")
                return

            if attempt < MCP_TOOL_RETRIES:
                logger.info("MCP_BRIDGE", 
                    f"[{self.name}] Tool discovery attempt {attempt}/{MCP_TOOL_RETRIES} failed, "
                    f"retrying in {MCP_TOOL_RETRY_SLEEP}s..."
                )
                time.sleep(MCP_TOOL_RETRY_SLEEP)

        self.status = "failed"
        logger.error("MCP_BRIDGE", f"[{self.name}] Tool discovery failed after {MCP_TOOL_RETRIES} attempts.")

    def call(self, method: str, params: dict = None) -> Optional[dict]:
        if params is None:
            params = {}
        if not self._ready_event.is_set():
            self._ready_event.wait(timeout=MCP_INIT_TIMEOUT + 2)
        return self._send(method, params, timeout=self.call_timeout)

    def is_alive(self) -> bool:
        return bool(self.process and self.process.poll() is None)
