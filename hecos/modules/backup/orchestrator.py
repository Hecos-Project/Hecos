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
        else:
            logger.warning("BACKUP", f"Internal call {method} {url} returned HTTP {resp.status_code}: {resp.data}")
            try:
                return json.loads(resp.data)
            except Exception:
                return {"ok": False, "error": f"HTTP {resp.status_code}: {resp.data.decode('utf-8', errors='ignore')}"}
    except Exception as e:
        logger.warning("BACKUP", f"Internal call {method} {url} failed: {e}")
        return {"ok": False, "error": str(e)}


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
    return _call_internal(app, "GET", "/hecos/api/backup_module/flows/backup")


def backup_users(app) -> dict | None:
    """Export all users (no passwords)."""
    return _call_internal(app, "GET", "/hecos/api/backup_module/users/backup")


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
    resp = _call_internal(app, "POST", "/hecos/api/backup_module/flows/restore", data)
    return resp or {"ok": False, "error": "No response from flows restore"}


def restore_users(app, data: dict) -> dict:
    resp = _call_internal(app, "POST", "/hecos/api/backup_module/users/restore", data)
    return resp or {"ok": False, "error": "No response from users restore"}


def restore_lists(app, data: dict) -> dict:
    resp = _call_internal(app, "POST", "/api/lists/restore", data)
    return resp or {"ok": False, "error": "No response from lists restore"}


def restore_system_config(app, data: dict) -> dict:
    resp = _call_internal(app, "POST", "/hecos/api/system_config/restore", data)
    return resp or {"ok": False, "error": "No response from system_config restore"}


# ── Module registry ──────────────────────────────────────────────────────────

# ── Module registry ──────────────────────────────────────────────────────────

def _make_hpm_backup_fn(endpoint: str):
    def fn(app):
        return _call_internal(app, "GET", endpoint)
    return fn

def _make_hpm_restore_fn(endpoint: str):
    def fn(app, data):
        return _call_internal(app, "POST", endpoint, data) or {"ok": False, "error": f"No response from {endpoint}"}
    return fn

def get_backup_fns() -> dict:
    fns = {
        "contacts":  backup_contacts,
        "chat":      backup_chat,
        "memory":    backup_memory,
        "flows":     backup_flows,
        "users":     backup_users,
        "system_config": backup_system_config,
    }
    
    # Discover HPM packages
    try:
        import os, tomllib
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        hpm_dir = os.path.join(root, "hpm")
        if os.path.isdir(hpm_dir):
            for d in os.listdir(hpm_dir):
                mf_path = os.path.join(hpm_dir, d, "hpkg_manifest.toml")
                if os.path.exists(mf_path):
                    with open(mf_path, "rb") as f:
                        mf_data = tomllib.load(f)
                    if "backup" in mf_data and mf_data["backup"].get("enabled"):
                        pkg_id = mf_data.get("id", d)
                        endpoint = mf_data["backup"].get("backup_endpoint")
                        if endpoint:
                            fns[pkg_id] = _make_hpm_backup_fn(endpoint)
    except Exception as e:
        logger.error(f"[BACKUP] Error discovering HPM backup fns: {e}")
        
    return fns

def get_restore_fns() -> dict:
    fns = {
        "contacts":  restore_contacts,
        "chat":      restore_chat,
        "memory":    restore_memory,
        "flows":     restore_flows,
        "users":     restore_users,
        "system_config": restore_system_config,
    }
    
    # Discover HPM packages
    try:
        import os, tomllib
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        hpm_dir = os.path.join(root, "hpm")
        if os.path.isdir(hpm_dir):
            for d in os.listdir(hpm_dir):
                mf_path = os.path.join(hpm_dir, d, "hpkg_manifest.toml")
                if os.path.exists(mf_path):
                    with open(mf_path, "rb") as f:
                        mf_data = tomllib.load(f)
                    if "backup" in mf_data and mf_data["backup"].get("enabled"):
                        pkg_id = mf_data.get("id", d)
                        endpoint = mf_data["backup"].get("restore_endpoint")
                        if endpoint:
                            fns[pkg_id] = _make_hpm_restore_fn(endpoint)
    except Exception as e:
        logger.error(f"[BACKUP] Error discovering HPM restore fns: {e}")
        
    return fns


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

        backup_fns = get_backup_fns()
        if modules_enabled is None:
            modules_enabled = {k: True for k in backup_fns}

        results = {}
        bundle = {}

        for mod_name, fn in backup_fns.items():
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
    fn = get_backup_fns().get(module_name)
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

            for mod_name, restore_fn in get_restore_fns().items():
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
