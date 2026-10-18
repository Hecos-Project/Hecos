"""
MODULE: Fish Speech TTS - API Client
DESCRIPTION: Handles HTTP transport, MessagePack (ormsgpack) and JSON payload serialization,
             server readiness probes, and daemon auto-starting.
"""

import os
import time
import base64
from typing import Optional
from urllib.parse import urlparse
import socket
import requests
from hecos.core.logging import logger

try:
    import ormsgpack
    ORMSGPACK_AVAILABLE = True
except ImportError:
    ORMSGPACK_AVAILABLE = False


def is_ormsgpack_available() -> bool:
    global ORMSGPACK_AVAILABLE
    if not ORMSGPACK_AVAILABLE:
        try:
            import ormsgpack  # noqa: F401
            ORMSGPACK_AVAILABLE = True
        except ImportError:
            ORMSGPACK_AVAILABLE = False
    return ORMSGPACK_AVAILABLE


class FishSpeechClient:
    """
    Communicates with local Fish Speech FastAPI server or Fish Audio Cloud endpoint.
    """

    _last_ready_check: float = 0.0
    _last_ready_result: bool = False

    @staticmethod
    def is_available() -> bool:
        """Returns True if the required libraries are installed."""
        try:
            import ormsgpack  # noqa: F401
            return True
        except ImportError:
            return False

    @classmethod
    def model_ready(cls) -> bool:
        """
        Checks if the configured Fish Speech endpoint is reachable and responsive,
        or if local model checkpoints are present on disk, or if an API key is present for cloud mode.
        Caches the result for 5 seconds to prevent polling bottlenecks.
        """
        if not cls.is_available():
            return False

        now = time.time()
        if now - cls._last_ready_check < 5.0:
            return cls._last_ready_result

        cls._last_ready_check = now
        try:
            from hecos.core.audio.device_manager import get_audio_config
            from hecos.core.audio.tts.fish_speech.params import get_project_root

            cfg = get_audio_config().get("fish_speech", {})
            api_url = cfg.get("api_url", "http://127.0.0.1:8080/v1/tts").strip()
            api_key = cfg.get("api_key", "").strip()

            if api_key:
                cls._last_ready_result = True
                return True

            if not api_url:
                cls._last_ready_result = False
                return False

            parsed = urlparse(api_url)
            host = parsed.hostname or "127.0.0.1"
            port = parsed.port or (443 if parsed.scheme == "https" else 80)

            # Check if local model weights are already on disk
            if host in ("127.0.0.1", "localhost"):
                root = get_project_root()
                s2_dir = os.path.join(root, "hecos", "engines", "fish_speech", "checkpoints", "s2-pro")
                if os.path.isfile(os.path.join(s2_dir, "codec.pth")):
                    cls._last_ready_result = True
                    return True

                ckpt_dir = os.path.join(root, "hecos", "engines", "fish_speech", "checkpoints", "fish-speech-1.5")
                model_pth = os.path.join(ckpt_dir, "model.pth")
                decoder_pth = os.path.join(ckpt_dir, "firefly-gan-vq-fsq-8x1024-21hz-generator.pth")
                if os.path.isfile(model_pth) and os.path.isfile(decoder_pth):
                    cls._last_ready_result = True
                    return True

            # Fast non-blocking socket probe (<150ms timeout)
            with socket.create_connection((host, port), timeout=0.15):
                cls._last_ready_result = True
                return True
        except Exception:
            cls._last_ready_result = False
            return False

    @staticmethod
    def synthesize_chunk(text: str, api_url: str, api_key: str, ref_audio: str = "",
                         ref_text: str = "", temp: float = 0.7, top_p: float = 0.7,
                         rep_pen: float = 1.2, max_tokens: int = 1024,
                         chunk_length: int = 200, seed: int = 0, normalize: bool = True,
                         use_memory_cache: bool = True, reference_id: str = "") -> Optional[bytes]:
        """
        Sends a single synthesis request to the Fish Speech API and returns WAV bytes.
        """
        audio_bytes = None
        if ref_audio and os.path.exists(ref_audio):
            try:
                with open(ref_audio, "rb") as f:
                    audio_bytes = f.read()
                logger.debug("FISH_SPEECH", f"Reference audio loaded ({len(audio_bytes)} bytes) from '{os.path.basename(ref_audio)}'")
            except Exception as e:
                logger.warning("FISH_SPEECH", f"Failed to read reference audio: {e}")

        # Construct payload according to ServeTTSRequest specification
        references = []
        if audio_bytes:
            references.append({
                "audio": audio_bytes,
                "text": ref_text or ""
            })

        # Safeguard: Clamp temperature and max_tokens for local Fish Speech to prevent infinite generation loops.
        effective_temp = min(temp, 0.8) if (not api_key and temp > 0.8) else temp
        effective_top_p = min(top_p, 0.85) if (not api_key and top_p > 0.85) else top_p
        if text and max_tokens > 0:
            dyn_ceiling = max(96, int(len(text) * 3.5) + 64)
            effective_max_tokens = min(max_tokens, dyn_ceiling)
        else:
            effective_max_tokens = max_tokens or 256

        payload = {
            "text": text,
            "references": references,
            "format": "wav",
            "streaming": False,
            "temperature": effective_temp,
            "top_p": effective_top_p,
            "repetition_penalty": rep_pen,
            "max_new_tokens": effective_max_tokens,
            "chunk_length": chunk_length,
            "normalize": normalize,
            "use_memory_cache": "on" if use_memory_cache else "off"
        }
        if reference_id:
            payload["reference_id"] = reference_id
        if seed and seed > 0:
            payload["seed"] = seed

        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        use_msgpack = is_ormsgpack_available() and audio_bytes
        if use_msgpack:
            import ormsgpack
            headers["Content-Type"] = "application/msgpack"
            data = ormsgpack.packb(payload)
            fmt_desc = "MessagePack (ormsgpack)"
        else:
            headers["Content-Type"] = "application/json"
            if audio_bytes:
                payload["references"][0]["audio"] = base64.b64encode(audio_bytes).decode("utf-8")
            import json
            data = json.dumps(payload)
            fmt_desc = "JSON (base64 audio)"

        # Automatic zero-friction daemon management for local synthesis
        parsed = urlparse(api_url)
        target_host = parsed.hostname or "127.0.0.1"
        target_port = parsed.port or (443 if parsed.scheme == "https" else 80)

        if target_host in ("127.0.0.1", "localhost") and not api_key:
            try:
                from hecos.core.audio.tts.fish_speech_daemon import FishSpeechDaemon
                daemon = FishSpeechDaemon.get_instance()
                if not daemon.is_port_listening(target_host, target_port):
                    logger.info("FISH_SPEECH", f"Local Fish Speech server not listening on port {target_port}. Starting automatically...")
                    started, start_msg = daemon.ensure_running(timeout=90.0)
                    if not started:
                        logger.error("FISH_SPEECH", f"❌ Could not auto-start Fish Speech server: {start_msg}")
                        return None
            except Exception as d_err:
                logger.error("FISH_SPEECH", f"Daemon auto-start check error: {d_err}")

        logger.debug("FISH_SPEECH", f"Sending request to '{api_url}' ({len(text)} chars) using {fmt_desc}...")
        start_t = time.time()

        try:
            resp = requests.post(api_url, data=data, headers=headers, timeout=180)
            elapsed = time.time() - start_t
            if resp.status_code == 200 and resp.content:
                logger.info("FISH_SPEECH", f"✅ Synthesized {len(resp.content)} bytes in {elapsed:.2f}s (HTTP 200)")
                return resp.content
            else:
                logger.error("FISH_SPEECH", f"❌ API error HTTP {resp.status_code} in {elapsed:.2f}s: {resp.text[:300]}")
                return None
        except Exception as exc:
            elapsed = time.time() - start_t
            logger.error("FISH_SPEECH", f"❌ Connection exception after {elapsed:.2f}s to '{api_url}': {exc}")
            if "10061" in str(exc) or "Connection refused" in str(exc) or "ConnectTimeout" in str(exc):
                logger.warning(
                    "FISH_SPEECH",
                    "💡 Target endpoint is unreachable. "
                    "If using local server: start 'tools/api_server.py' or Docker on port 8080. "
                    "If using Cloud: set URL to 'https://api.fish.audio/v1/tts' and enter your API key in Central Hub."
                )
            return None
