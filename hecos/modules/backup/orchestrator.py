"""
MODULE: Backup Orchestrator
DESCRIPTION: Core backup/restore logic for every Hecos module.
             Each backup_<module>() function calls the corresponding internal
             Flask route using app.test_client() — no external network,
             no direct DB imports, fully decoupled.

             run_full_backup() orchestrates all modules and writes a ZIP bundle.
             restore_from_zip() unpacks and restores selected modules.
"""

import io
import json
import zipfile
import threading
from datetime import datetime, timezone
from hecos.core.logging import logger

_run_lock = threading.Lock()


# ── Per-module backup helpers ────────────────────────────────────────────────

def _call_internal(app, method: str, url: str, json_body=None) -> dict | None:
    """
    Makes an internal Flask request using test_client().
    Returns the parsed JSON body on 2xx, or None on error.
    """
    try:
        with app.test_request_context():
            with app.test_client() as client:
                if method == "GET":
                    resp = client.get(url, headers={"X-Hecos-Internal": "backup"})
                else:
                    resp = client.post(url, json=json_body or {}, headers={"X-Hecos-Internal": "backup"})
        if resp.status_code == 200:
            return json.loads(resp.data)
    except Exception as e:
        logger.warning("BACKUP", f"Internal call {method} {url} failed: {e}")
    return None


def backup_calendar(app) -> dict | None:
    """Export all calendar events."""
    return _call_internal(app, "GET", "/api/calendar/backup")


def backup_contacts(app) -> dict | None:
    """Export all contacts."""
    return _call_internal(app, "GET", "/api/contacts/backup")


def backup_chat(app) -> dict | None:
    """Export full chat history."""
    return _call_internal(app, "GET", "/hecos/api/history/backup")


def backup_memory(app) -> dict | None:
    """Export memory vault and RAG documents."""
    return _call_internal(app, "GET", "/hecos/api/memory/backup")


def backup_reminders(app) -> dict | None:
    """Export all reminders."""
    return _call_internal(app, "GET", "/api/reminders/backup")


def backup_flows(app) -> dict | None:
    """Export all flows (raw YAML bundle)."""
    return _call_internal(app, "GET", "/api/flows/backup")


def backup_users(app) -> dict | None:
    """Export all users (no passwords)."""
    return _call_internal(app, "GET", "/hecos/api/users/backup")


def backup_lists(app) -> dict | None:
    """Export all lists with items."""
    return _call_internal(app, "GET", "/api/lists/backup")


def backup_system_config(app) -> dict | None:
    """Export all YAML/JSON config files."""
    return _call_internal(app, "GET", "/hecos/api/system_config/backup")


# ── Restore helpers ──────────────────────────────────────────────────────────

def restore_calendar(app, data: dict) -> dict:
    resp = _call_internal(app, "POST", "/api/calendar/restore", data)
    return resp or {"ok": False, "error": "No response from calendar restore"}


def restore_contacts(app, data: dict) -> dict:
    resp = _call_internal(app, "POST", "/api/contacts/restore", data)
    return resp or {"ok": False, "error": "No response from contacts restore"}


def restore_chat(app, data: dict) -> dict:
    resp = _call_internal(app, "POST", "/hecos/api/history/restore", data)
    return resp or {"ok": False, "error": "No response from chat restore"}


def restore_memory(app, data: dict) -> dict:
    resp = _call_internal(app, "POST", "/hecos/api/memory/restore", data)
    return resp or {"ok": False, "error": "No response from memory restore"}


def restore_reminders(app, data: dict) -> dict:
    resp = _call_internal(app, "POST", "/api/reminders/restore", data)
    return resp or {"ok": False, "error": "No response from reminders restore"}


def restore_flows(app, data: dict) -> dict:
    resp = _call_internal(app, "POST", "/api/flows/restore", data)
    return resp or {"ok": False, "error": "No response from flows restore"}


def restore_users(app, data: dict) -> dict:
    resp = _call_internal(app, "POST", "/hecos/api/users/restore", data)
    return resp or {"ok": False, "error": "No response from users restore"}


def restore_lists(app, data: dict) -> dict:
    resp = _call_internal(app, "POST", "/api/lists/restore", data)
    return resp or {"ok": False, "error": "No response from lists restore"}


def restore_system_config(app, data: dict) -> dict:
    resp = _call_internal(app, "POST", "/hecos/api/system_config/restore", data)
    return resp or {"ok": False, "error": "No response from system_config restore"}


# ── Module registry ──────────────────────────────────────────────────────────

_BACKUP_FNS = {
    "calendar":  backup_calendar,
    "contacts":  backup_contacts,
    "chat":      backup_chat,
    "memory":    backup_memory,
    "reminders": backup_reminders,
    "flows":     backup_flows,
    "users":     backup_users,
    "lists":     backup_lists,
    "system_config": backup_system_config,
}

_RESTORE_FNS = {
    "calendar":  restore_calendar,
    "contacts":  restore_contacts,
    "chat":      restore_chat,
    "memory":    restore_memory,
    "reminders": restore_reminders,
    "flows":     restore_flows,
    "users":     restore_users,
    "lists":     restore_lists,
    "system_config": restore_system_config,
}


# ── Full backup orchestration ─────────────────────────────────────────────────

def run_full_backup(app, dest_path: str, modules_enabled: dict | None = None) -> dict:
    """
    Run a full backup of all enabled modules.
    Writes a ZIP to dest_path named hecos_backup_YYYY-MM-DD_HH-MM-SS.zip
    Returns: { ok, filename, path, results, timestamp }
    """
    if not _run_lock.acquire(blocking=False):
        return {"ok": False, "error": "A backup is already running."}

    try:
        ts = datetime.now(timezone.utc)
        ts_str = ts.strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"hecos_backup_{ts_str}.zip"
        zip_path = str(dest_path).rstrip("/\\") + "/" + filename if dest_path else filename

        if modules_enabled is None:
            modules_enabled = {k: True for k in _BACKUP_FNS}

        results = {}
        bundle = {}

        for mod_name, fn in _BACKUP_FNS.items():
            if not modules_enabled.get(mod_name, True):
                results[mod_name] = {"skipped": True}
                logger.debug("BACKUP", f"Module {mod_name} skipped (disabled in config).")
                continue
            logger.info("BACKUP", f"Backing up module: {mod_name}")
            try:
                data = fn(app)
                if data and data.get("ok") is not False:
                    bundle[mod_name] = data
                    results[mod_name] = {"ok": True}
                    logger.debug("BACKUP", f"Module {mod_name} backed up successfully.")
                else:
                    error_details = str(data.get("error", data)) if isinstance(data, dict) else str(data)
                    logger.warning("BACKUP", f"Module {mod_name} returned error: {error_details}")
                    results[mod_name] = {"ok": False, "error": error_details}
            except Exception as e:
                logger.error(f"[BACKUP] Error backing up {mod_name}: {e}")
                results[mod_name] = {"ok": False, "error": str(e)}

        # Build manifest
        manifest = {
            "hecos_backup": True,
            "version": "1.0",
            "timestamp": ts.isoformat(),
            "modules_included": [m for m in results if results[m].get("ok")],
        }

        # Write ZIP
        import os
        if dest_path:
            os.makedirs(dest_path, exist_ok=True)

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))
            for mod_name, data in bundle.items():
                if isinstance(data, dict) and data.get("_is_files_bundle"):
                    for filepath, content in data.get("files", {}).items():
                        zf.writestr(filepath, content)
                else:
                    zf.writestr(f"{mod_name}.json", json.dumps(data, indent=2, ensure_ascii=False))

        zip_bytes = buf.getvalue()
        if dest_path:
            with open(zip_path, "wb") as f:
                f.write(zip_bytes)

        ok = any(r.get("ok") for r in results.values())
        if ok:
            logger.info("BACKUP", f"✅ Backup completed → {filename} (Size: {len(zip_bytes)} bytes)")
        else:
            logger.error(f"[BACKUP] ❌ Backup failed. Modules results: {results}")
        return {
            "ok": ok,
            "filename": filename,
            "path": zip_path if dest_path else None,
            "zip_bytes": zip_bytes,
            "results": results,
            "timestamp": ts.isoformat(),
        }

    except Exception as e:
        logger.error(f"[BACKUP] run_full_backup error: {e}")
        return {"ok": False, "error": str(e)}
    finally:
        _run_lock.release()


def backup_single_module(app, module_name: str) -> dict:
    """Run backup for a single module. Returns the raw data dict."""
    fn = _BACKUP_FNS.get(module_name)
    if not fn:
        return {"ok": False, "error": f"Unknown module: {module_name}"}
    try:
        data = fn(app)
        return data or {"ok": False, "error": "No data returned"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def restore_from_zip(app, zip_bytes: bytes, modules: list | None = None) -> dict:
    """
    Restore from a ZIP backup bundle.
    modules: list of module names to restore (None = all present in ZIP).
    Returns: { ok, results }
    """
    results = {}
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            names = zf.namelist()

            # Validate manifest
            if "manifest.json" not in names:
                return {"ok": False, "error": "Invalid backup: manifest.json missing"}
            manifest = json.loads(zf.read("manifest.json"))
            if not manifest.get("hecos_backup"):
                return {"ok": False, "error": "Invalid backup file"}

            for mod_name, restore_fn in _RESTORE_FNS.items():
                if modules is not None and mod_name not in modules:
                    results[mod_name] = {"skipped": True}
                    continue

                if mod_name == "system_config":
                    prefix = "config_data/"
                    files_dict = {
                        name.split("/")[-1]: zf.read(name).decode("utf-8")
                        for name in names if name.startswith(prefix) and not name.endswith("/")
                    }
                    if not files_dict:
                        results[mod_name] = {"skipped": True, "reason": "Not in backup"}
                        continue
                    try:
                        result = restore_fn(app, {"data": files_dict})
                        results[mod_name] = result
                    except Exception as e:
                        logger.error(f"[BACKUP] Restore error for {mod_name}: {e}")
                        results[mod_name] = {"ok": False, "error": str(e)}
                    continue

                json_file = f"{mod_name}.json"
                if json_file not in names:
                    results[mod_name] = {"skipped": True, "reason": "Not in backup"}
                    continue
                try:
                    data = json.loads(zf.read(json_file))
                    result = restore_fn(app, data)
                    results[mod_name] = result
                except Exception as e:
                    logger.error(f"[BACKUP] Restore error for {mod_name}: {e}")
                    results[mod_name] = {"ok": False, "error": str(e)}

    except zipfile.BadZipFile:
        return {"ok": False, "error": "Invalid ZIP file"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

    ok = any(r.get("ok") for r in results.values())
    return {"ok": ok, "results": results}
