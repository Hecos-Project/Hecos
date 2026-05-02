import os
import sys
import psutil
import json
import logging

def get_lock_file_path(lock_name: str) -> str:
    """Returns the absolute path for the lock file."""
    # We place lock files in the 'logs' directory
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    lock_dir = os.path.join(base_dir, "logs")
    if not os.path.exists(lock_dir):
        os.makedirs(lock_dir)
    return os.path.join(lock_dir, f"{lock_name}.lock")

def is_process_running(pid: int) -> bool:
    """Checks if a process with the given PID is currently running and is a Python/Hecos instance."""
    try:
        if not psutil.pid_exists(pid):
            return False
        p = psutil.Process(pid)
        name = p.name().lower()
        return 'python' in name or 'hecos' in name
    except Exception:
        return False

def acquire_lock(lock_name: str) -> bool:
    """
    Attempts to acquire a lock for the given name.
    Returns True if acquired, False if another instance is already running.
    """
    lock_path = get_lock_file_path(lock_name)
    current_pid = os.getpid()

    if os.path.exists(lock_path):
        try:
            with open(lock_path, "r") as f:
                data = json.load(f)
                old_pid = data.get("pid")
                if old_pid and is_process_running(old_pid):
                    return False
        except (json.JSONDecodeError, IOError, ValueError):
            # If the file is corrupted or unreadable, we assume it's safe to overwrite
            pass

    # Write the current PID to the lock file
    try:
        with open(lock_path, "w") as f:
            json.dump({"pid": current_pid, "lock_name": lock_name}, f)
        return True
    except IOError:
        return False

def release_lock(lock_name: str):
    """Releases the lock by removing the lock file."""
    lock_path = get_lock_file_path(lock_name)
    if os.path.exists(lock_path):
        try:
            os.remove(lock_path)
        except OSError:
            pass
