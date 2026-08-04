import os
import sys
import json
import urllib.request
import urllib.error
import threading
import subprocess
import time
from packaging import version
from hecos.tray.config import _ROOT, VERSION_FILE
from hecos.tray.update_sources import load_sources

def get_current_version() -> str:
    try:
        with open(VERSION_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return "1.0.0"

def get_tray_version() -> str:
    try:
        tray_ver_file = os.path.join(_ROOT, "hecos", "tray", "version")
        with open(tray_ver_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return "1.0.0"

def check_for_updates() -> dict:
    """
    Checks the active source for a new release.
    Returns dict: {"update_available": bool, "latest_version": str, "assets": list, "error": str}
    """
    data = load_sources()
    active_name = data.get("active_source", "")
    active_src = None
    for src in data.get("sources", []):
        if src.get("name") == active_name:
            active_src = src
            break
            
    if not active_src:
        return {"update_available": False, "error": "No active update source configured."}
        
    url = active_src.get("url", "")
    source_type = active_src.get("type", "github_release")
    
    if not url:
        return {"update_available": False, "error": "Invalid URL in update source."}
        
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            resp_data = json.loads(response.read().decode('utf-8'))
            
        if source_type == "github_release":
            latest_version = resp_data.get("tag_name", "").lstrip("v")
            assets = resp_data.get("assets", [])
            downloadable_assets = [{"name": a["name"], "url": a["browser_download_url"]} for a in assets]
        else:
            # Custom JSON structure fallback: {"version": "...", "assets": [{"name": "...", "url": "..."}]}
            latest_version = resp_data.get("version", "").lstrip("v")
            downloadable_assets = resp_data.get("assets", [])
            
        current_v = get_tray_version()
        
        try:
            # We use packaging.version for semantic comparison
            has_update = version.parse(latest_version) > version.parse(current_v)
        except Exception:
            # Fallback if version strings are non-standard
            has_update = latest_version != current_v
            
        return {
            "update_available": has_update,
            "latest_version": latest_version,
            "assets": downloadable_assets,
            "error": None
        }
    except Exception as e:
        return {"update_available": False, "error": str(e)}

def download_asset(url: str, dest_path: str, progress_callback=None):
    """
    Downloads a file with an optional progress callback.
    progress_callback(bytes_downloaded, total_bytes)
    """
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            total_size = int(response.info().get('Content-Length', -1))
            bytes_so_far = 0
            chunk_size = 1024 * 64
            
            with open(dest_path, "wb") as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    bytes_so_far += len(chunk)
                    if progress_callback:
                        progress_callback(bytes_so_far, total_size)
    except Exception as e:
        raise Exception(f"Download failed: {e}")

def apply_update_and_restart(tray_exe_path: str, dashboard_exe_path: str):
    """
    Creates a temporary batch/shell script to swap the binaries and restarts the tray.
    The script kills the tray if still alive, moves the new exes over the old ones,
    starts the new tray, and deletes itself.
    """
    bin_dir = os.path.join(_ROOT, "bin")
    
    if sys.platform == "win32":
        swap_script_path = os.path.join(bin_dir, "hecos_swap.bat")
        
        script_content = f"""@echo off
title HECOS Updater
echo Waiting for Hecos Tray to close...
timeout /t 3 /nobreak >nul

:: Ensure old processes are completely dead before replacing
taskkill /F /IM hecos_tray.exe >nul 2>&1
taskkill /F /IM hecos_dashboard.exe >nul 2>&1
timeout /t 1 /nobreak >nul

echo Applying updates...
"""
        if os.path.exists(tray_exe_path):
            script_content += f'move /y "{tray_exe_path}" "{os.path.join(bin_dir, "hecos_tray.exe")}"\n'
        if os.path.exists(dashboard_exe_path):
            script_content += f'move /y "{dashboard_exe_path}" "{os.path.join(bin_dir, "hecos_dashboard.exe")}"\n'
            
        script_content += f"""
echo Restarting Hecos Tray...
start "" "{os.path.join(bin_dir, "hecos_tray.exe")}"
echo Cleaning up...
del "%~f0"
"""
        with open(swap_script_path, "w") as f:
            f.write(script_content)
            
        subprocess.Popen(
            ["cmd.exe", "/c", swap_script_path],
            creationflags=subprocess.CREATE_NEW_CONSOLE | subprocess.CREATE_NO_WINDOW
        )
    else:
        # Linux/macOS swap script
        swap_script_path = os.path.join(bin_dir, "hecos_swap.sh")
        script_content = f"""#!/bin/bash
sleep 3
"""
        if os.path.exists(tray_exe_path):
            script_content += f'mv -f "{tray_exe_path}" "{os.path.join(bin_dir, "hecos_tray")}"\n'
        if os.path.exists(dashboard_exe_path):
            script_content += f'mv -f "{dashboard_exe_path}" "{os.path.join(bin_dir, "hecos_dashboard")}"\n'
            
        script_content += f"""
chmod +x "{os.path.join(bin_dir, "hecos_tray")}"
"{os.path.join(bin_dir, "hecos_tray")}" &
rm "$0"
"""
        with open(swap_script_path, "w") as f:
            f.write(script_content)
        os.chmod(swap_script_path, 0o755)
        
        subprocess.Popen(["bash", swap_script_path], start_new_session=True)
        
    # Exit current process so the swap script can overwrite the file
    sys.exit(0)
