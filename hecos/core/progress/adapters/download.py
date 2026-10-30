"""
hecos/core/progress/adapters/download.py
─────────────────────────────────────────────────────────────────────────────
Progress-aware file download adapter.
Supports HTTP/HTTPS streams via urllib or requests, with chunked progress reporting,
speed/ETA calculations, and cancellation support.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import os
import urllib.request
from typing import Optional, Dict
from hecos.core.progress.model import Task, CancellationRequested


def download_file(
    url: str,
    dest_path: str,
    task: Optional[Task] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 120,
    chunk_size: int = 65536,
) -> str:
    """
    Downloads a remote file to dest_path while streaming progress to task.
    Supports cancellation: if task is cancelled, stops immediately and removes partial download.
    """
    os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
    tmp_path = dest_path + ".part"

    req_headers = {"User-Agent": "Hecos-Progress/1.0"}
    if headers:
        req_headers.update(headers)

    req = urllib.request.Request(url, headers=req_headers)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            total_bytes = 0
            content_length = resp.headers.get("Content-Length")
            if content_length and content_length.isdigit():
                total_bytes = int(content_length)

            if task:
                task.advance(bytes_done=0, total_bytes=total_bytes, message=f"Scaricamento {os.path.basename(dest_path)}...")

            with open(tmp_path, "wb") as out_f:
                while True:
                    if task:
                        task.check_cancelled()

                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break

                    out_f.write(chunk)
                    if task:
                        task.advance(delta_bytes=len(chunk), total_bytes=total_bytes)

        if os.path.exists(dest_path):
            os.remove(dest_path)
        os.rename(tmp_path, dest_path)
        return dest_path

    except (CancellationRequested, Exception) as exc:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        raise exc


def get_reporthook(task: Task):
    """
    Returns a reporthook callback suitable for urllib.request.urlretrieve.
    """
    def _hook(block_num: int, block_size: int, total_size: int):
        task.check_cancelled()
        done = block_num * block_size
        if total_size > 0:
            task.advance(bytes_done=min(done, total_size), total_bytes=total_size)
        else:
            task.advance(delta_bytes=block_size)

    return _hook
