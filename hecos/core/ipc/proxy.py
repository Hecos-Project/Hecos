"""
hecos/core/ipc/proxy.py
─────────────────────────────────────────────────────────────────────────────
ModuleProxy — Core-side representative for an isolated HPM plugin subprocess.

Duck-type compatible with the old `module.tools` interface used by
hecos/core/processing/__init__.py. No changes needed in the dispatcher.

Lifecycle:
  proxy = ModuleProxy(tag, plugin_dir, venv_python_exe)
  proxy.start()            # launches the subprocess
  result = proxy.call("generate_image", {"prompt": "..."})
  proxy.stop()             # graceful shutdown
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import os
import sys
import subprocess
import threading
from typing import Any, Dict, Optional

from hecos.core.logging import logger
from .protocol import make_call, make_info, make_shutdown, parse_response


class _ToolsInterface:
    """
    Proxy object that mimics the old `tools` attribute on a loaded plugin module.
    Dispatches every attribute access as an IPC call to the subprocess.
    """

    def __init__(self, proxy: "ModuleProxy"):
        object.__setattr__(self, "_proxy", proxy)

    def __getattr__(self, method_name: str):
        proxy = object.__getattribute__(self, "_proxy")

        # Build a wrapper with the real signature from the manifest so that
        # executor._build_kwargs inspects the correct parameter names.
        # We read slash_commands from the cached manifest to reconstruct the sig.
        import inspect as _inspect

        manifest = proxy._manifest_cache or {}
        # Find the matching slash command schema
        args_schema = {}
        for sc in manifest.get("slash_commands", []):
            if sc.get("method") == method_name:
                args_schema = sc.get("args_schema") or {}
                break

        if args_schema:
            # Build a real function with named parameters
            param_names = list(args_schema.keys())
            # Build params list (all str, no defaults)
            params = [_inspect.Parameter("self", _inspect.Parameter.POSITIONAL_OR_KEYWORD)] + [
                _inspect.Parameter(p, _inspect.Parameter.POSITIONAL_OR_KEYWORD)
                for p in param_names
            ]
            def _make_remote(mname, pnames):
                def _remote(self_ignored=None, **kwargs):
                    return proxy.call(mname, kwargs)
                _remote.__signature__ = _inspect.Signature(
                    [_inspect.Parameter(p, _inspect.Parameter.POSITIONAL_OR_KEYWORD) for p in pnames]
                )
                return _remote
            return _make_remote(method_name, param_names)
        else:
            # Fallback: generic **kwargs wrapper
            def _remote(**kwargs):
                return proxy.call(method_name, kwargs)
            return _remote


class ModuleProxy:
    """
    Manages the lifecycle of one HPM plugin subprocess and routes calls to it.
    """

    def __init__(
        self,
        tag: str,
        plugin_dir: str,
        venv_python_exe: Optional[str] = None,
        timeout: float = 30.0,
    ):
        self.tag          = tag
        self.plugin_dir   = plugin_dir
        self.timeout      = timeout
        self._python_exe  = venv_python_exe or sys.executable
        self._process: Optional[subprocess.Popen] = None
        self._lock        = threading.Lock()
        self._manifest_cache: Optional[Dict[str, Any]] = None

        # Duck-type surface: processing/__init__.py checks `hasattr(plugin_obj, "tools")`
        self.tools = _ToolsInterface(self)

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self) -> bool:
        """Launch the plugin subprocess. Returns True on success."""
        try:
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            env["HECOS_MODULE_TAG"] = self.tag  # for process title in Task Manager
            kwargs = {}
            if os.name == 'nt':
                kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
                
            self._process = subprocess.Popen(
                [self._python_exe, "-m", "hecos_sdk.runner"],
                cwd=self.plugin_dir,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,  # line-buffered
                env=env,
                **kwargs
            )
            # Start a background thread to forward stderr to the Hecos logger
            t = threading.Thread(target=self._stderr_relay, daemon=True)
            t.start()

            logger.info(f"[IPC:{self.tag}] Subprocess started (PID={self._process.pid})")
            return True
        except Exception as e:
            logger.error(f"[IPC:{self.tag}] Failed to start subprocess: {e}")
            return False

    def stop(self):
        """Gracefully shut down the subprocess."""
        if not self._process:
            return
        try:
            self._send_raw(make_shutdown())
            self._process.wait(timeout=5)
        except Exception:
            self._process.kill()
        finally:
            self._process = None
        logger.info(f"[IPC:{self.tag}] Subprocess stopped.")

    def is_alive(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def restart(self) -> bool:
        self.stop()
        return self.start()

    def get_manifest(self) -> Dict[str, Any]:
        """Fetch the plugin's manifest data. Cached after first call."""
        if self._manifest_cache is not None:
            return self._manifest_cache
        if not self.is_alive():
            return {}
        raw = make_info()
        resp = self._rpc(raw)
        if resp.get("type") == "manifest":
            self._manifest_cache = resp.get("data", {})
            return self._manifest_cache
        return {}

    def call(self, method: str, kwargs: Optional[Dict[str, Any]] = None) -> Any:
        """
        Invoke a method on the remote plugin tools and return its result.
        Raises RuntimeError if the plugin is not running or the call fails.
        """
        if not self.is_alive():
            raise RuntimeError(f"[IPC:{self.tag}] Subprocess is not running.")

        raw = make_call(method, kwargs or {})
        resp = self._rpc(raw)

        if resp.get("ok"):
            return resp.get("value")
        else:
            err = resp.get("error", "Unknown IPC error")
            logger.error(f"[IPC:{self.tag}] Call '{method}' failed:\n{err}")
            raise RuntimeError(err)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _send_raw(self, line: str):
        if self._process and self._process.stdin:
            self._process.stdin.write(line)
            self._process.stdin.flush()

    def _rpc(self, raw_request: str) -> Dict[str, Any]:
        """Send a request line and block until the corresponding response arrives."""
        with self._lock:
            self._send_raw(raw_request)
            # Read lines until we get a non-log response
            while True:
                if not self._process or not self._process.stdout:
                    return {"ok": False, "error": "Process died"}
                line = self._process.stdout.readline()
                if not line:
                    return {"ok": False, "error": "Subprocess closed stdout unexpectedly"}
                resp = parse_response(line)
                msg_type = resp.get("type")
                if msg_type == "log":
                    # Forward plugin log to core logger
                    level  = resp.get("level", "info")
                    msg    = resp.get("msg", "")
                    getattr(logger, level, logger.info)(f"[PLUGIN:{self.tag}] {msg}")
                    continue
                # Any other response (result, manifest) is returned
                return resp

    def _stderr_relay(self):
        """Read subprocess stderr and relay to core logger (background thread)."""
        if not self._process:
            return
        for line in self._process.stderr:
            line = line.rstrip()
            if line:
                logger.warning(f"[PLUGIN:{self.tag}:stderr] {line}")
