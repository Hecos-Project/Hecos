"""
hecos/core/module_bus.py
─────────────────────────────────────────────────────────────────────────────
ModuleBus — Lifecycle manager for all isolated HPM module subprocesses.

Responsibilities:
  - Create/destroy ModuleProxy instances.
  - Provide get_proxy(tag) as the replacement for get_plugin_module(tag).
  - Gracefully shut down all subprocesses on Hecos exit (atexit hook).
  - Allow hot-restart of a single module after install/update.

Usage:
  from hecos.core.module_bus import get_bus
  bus = get_bus()
  proxy = bus.get_proxy('IMAGE_GEN')
  result = proxy.tools.generate_image(prompt='...')
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import atexit
import os
import sys
import threading
from typing import Dict, Optional

from hecos.core.logging import logger
from hecos.core.ipc.proxy import ModuleProxy


class ModuleBus:
    def __init__(self):
        self._proxies: Dict[str, ModuleProxy] = {}
        self._lock = threading.Lock()
        atexit.register(self.shutdown_all)

    def start_module(self, tag, module_dir, venv_python_exe=None):
        venv_exe = venv_python_exe or self._resolve_venv_python(module_dir)
        proxy = ModuleProxy(tag, module_dir, venv_exe)
        ok = proxy.start()
        if ok:
            with self._lock:
                self._proxies[tag] = proxy
            logger.info(f"[ModuleBus] Module '{tag}' started from {module_dir}")
            return proxy
        logger.error(f"[ModuleBus] Failed to start plugin '{tag}'")
        return None

    def stop_plugin(self, tag):
        with self._lock:
            proxy = self._proxies.pop(tag, None)
        if proxy:
            proxy.stop()
            logger.info(f"[ModuleBus] Module '{tag}' stopped.")

    def restart_module(self, tag):
        with self._lock:
            proxy = self._proxies.get(tag)
        if not proxy:
            logger.warning(f"[ModuleBus] restart_module: '{tag}' not registered.")
            return False
        ok = proxy.restart()
        logger.info(f"[ModuleBus] Module '{tag}' restarted: {ok}")
        return ok

    def get_proxy(self, tag):
        with self._lock:
            proxy = self._proxies.get(tag)
        if proxy and not proxy.is_alive():
            logger.warning(f"[ModuleBus] Module '{tag}' process died, attempting restart...")
            proxy.restart()
        return proxy

    def list_active(self):
        result = {}
        with self._lock:
            for tag, proxy in self._proxies.items():
                pid = proxy._process.pid if proxy._process else None
                result[tag] = {"tag": tag, "dir": proxy.module_dir, "alive": proxy.is_alive(), "pid": pid}
        return result

    def shutdown_all(self):
        with self._lock:
            tags = list(self._proxies.keys())
        for tag in tags:
            try:
                self.stop_plugin(tag)
            except Exception as e:
                logger.debug(f"[ModuleBus] Error stopping '{tag}' on shutdown: {e}")

    @staticmethod
    def _resolve_venv_python(module_dir):
        if os.name == 'nt':
            candidate = os.path.join(module_dir, 'venv', 'Scripts', 'python.exe')
        else:
            candidate = os.path.join(module_dir, 'venv', 'bin', 'python')
        return candidate if os.path.exists(candidate) else sys.executable


_bus_instance = None
_bus_lock = threading.Lock()

def get_bus() -> ModuleBus:
    global _bus_instance
    if _bus_instance is None:
        with _bus_lock:
            if _bus_instance is None:
                _bus_instance = ModuleBus()
    return _bus_instance
