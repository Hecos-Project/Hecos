"""
Fish Speech Local FastAPI Server
Provides a pure-Python, resilient, FastAPI HTTP endpoint (/v1/tts)
compatible with Fish Speech API and Hecos FishSpeechEngine.
Runs locally using checkpoints in hecos/engines/fish_speech/checkpoints/s2-pro (or fish-speech-1.5).
Eliminates any reliance on problematic C-extensions (like baize / kui).
"""

import os
import sys
import io
import time
import asyncio
import threading
import argparse
from typing import Optional, Set

# Ensure project root & fish_speech engine are on sys.path
_current_dir = os.path.dirname(os.path.abspath(__file__))
_hecos_root = os.path.abspath(os.path.join(_current_dir, "..", "..", "..", ".."))
_fish_engine_dir = os.path.join(_hecos_root, "hecos", "engines", "fish_speech")

if _fish_engine_dir not in sys.path:
    sys.path.insert(0, _fish_engine_dir)
if _hecos_root not in sys.path:
    sys.path.insert(0, _hecos_root)

# Set working directory to engine dir so relative checkpoint references resolve
os.chdir(_fish_engine_dir)

import torch
import torchaudio
if not hasattr(torchaudio, "list_audio_backends"):
    torchaudio.list_audio_backends = lambda: ["soundfile"]

import soundfile as sf
import uvicorn
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

# Import Fish Speech inference modules directly
try:
    from tools.server.model_manager import ModelManager
    from fish_speech.inference_engine import TTSInferenceEngine
    from fish_speech.utils.schema import ServeTTSRequest
    from tools.server.inference import inference_wrapper as inference
    import ormsgpack
except ImportError as e:
    logger.error(f"[FISH_SERVER] Failed to import Fish Speech modules: {e}")
    sys.exit(1)


app = FastAPI(title="Hecos Fish Speech Local Server", version="3.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine: Optional[TTSInferenceEngine] = None
server_device: str = "cpu"
_state_lock = threading.Lock()
_active_requests: int = 0
_active_since: Optional[float] = None
_cancel_events: Set[threading.Event] = set()
_vram_paging_detected: bool = False
_last_wav_kbps: float = 0.0


def _cancel_all_inflight() -> int:
    with _state_lock:
        events = list(_cancel_events)
    for ev in events:
        ev.set()
    return len(events)


def init_engine(checkpoint_dir: str, device: str = "auto", compile_model: bool = False, max_seq_len: int = 2048):
    global engine, server_device, _vram_paging_detected

    os.environ["FISH_MAX_SEQ_LEN"] = str(max_seq_len)

    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    server_device = device

    logger.info(f"[FISH_SERVER] Initializing Fish Speech on device: {device} (checkpoint: {checkpoint_dir}, max_seq_len: {max_seq_len})...")

    t_init = time.perf_counter()
    model_manager = ModelManager(
        mode="tts",
        device=device,
        half=True if device.startswith("cuda") else False,
        compile=compile_model,
        llama_checkpoint_path=checkpoint_dir,
        decoder_checkpoint_path=None,
        decoder_config_name="modded_dac_vq",
    )
    init_elapsed = time.perf_counter() - t_init
    engine = model_manager.tts_inference_engine

    # If CUDA init + 16-token warmup took > 28s, WDDM is paging weights into shared system RAM
    if device.startswith("cuda") and init_elapsed > 28.0:
        _vram_paging_detected = True
        logger.warning(
            f"[FISH_SERVER] Slow CUDA init/warmup ({init_elapsed:.1f}s) — GPU VRAM overflow into shared system RAM likely."
        )

    logger.info("=" * 60)
    logger.info(f"✅ Fish Speech engine ({engine.model_family.upper()}) ready on {device.upper()} in {init_elapsed:.1f}s!")
    logger.info("=" * 60)


@app.get("/")
@app.get("/v1/health")
async def health_check():
    family = getattr(engine, "model_family", "s2-pro") if engine is not None else "s2-pro"
    vram_mb = 0.0
    vram_reserved_mb = 0.0
    gpu_free_mb = 0.0
    gpu_total_mb = 0.0
    if torch.cuda.is_available():
        try:
            vram_mb = round(torch.cuda.memory_allocated() / (1024 * 1024), 1)
            vram_reserved_mb = round(torch.cuda.memory_reserved() / (1024 * 1024), 1)
            free_b, total_b = torch.cuda.mem_get_info()
            gpu_free_mb = round(free_b / (1024 * 1024), 1)
            gpu_total_mb = round(total_b / (1024 * 1024), 1)
        except Exception:
            pass
    with _state_lock:
        active = _active_requests
        busy_sec = round(max(0.0, time.time() - _active_since), 1) if (_active_since and active > 0) else 0.0
        paging = _vram_paging_detected
        kbps = _last_wav_kbps
    return {
        "ok": True,
        "service": "hecos-fish-speech",
        "pid": os.getpid(),
        "status": "ready" if engine is not None else "initializing",
        "busy": active > 0,
        "active_requests": active,
        "busy_seconds": busy_sec,
        "engine": f"fish_speech_{family}",
        "device": server_device,
        "cuda_available": torch.cuda.is_available(),
        "vram_mb": vram_mb,
        "vram_reserved_mb": vram_reserved_mb,
        "gpu_free_mb": gpu_free_mb,
        "gpu_total_mb": gpu_total_mb,
        "vram_paging": paging,
        "last_wav_kbps": kbps,
    }


@app.post("/v1/tts/cancel")
async def cancel_tts():
    cancelled = _cancel_all_inflight()
    logger.warning(f"[FISH_SERVER] Cancel requested via /v1/tts/cancel — signaled {cancelled} active/queued request(s).")
    return {"ok": True, "cancelled": cancelled}


@app.get("/v1/tts/defaults")
async def tts_defaults():
    if engine is None:
        raise HTTPException(status_code=503, detail="Engine not loaded.")
    return engine.sampling_defaults()


@app.post("/v1/tts")
async def tts_endpoint(request: Request):
    global _active_requests, _active_since
    if engine is None:
        raise HTTPException(status_code=503, detail="Fish Speech engine is still initializing or not loaded.")

    content_type = request.headers.get("content-type", "").lower()
    raw_body = await request.body()

    try:
        if "msgpack" in content_type:
            payload = ormsgpack.unpackb(raw_body)
        else:
            payload = await request.json()
    except Exception as parse_err:
        raise HTTPException(status_code=400, detail=f"Failed to parse payload: {parse_err}")

    # Build request object
    try:
        # Decode base64 audio if present in JSON references
        references = payload.get("references") or []
        for ref in references:
            if isinstance(ref, dict) and isinstance(ref.get("audio"), str):
                import base64
                ref["audio"] = base64.b64decode(ref["audio"])

        req = ServeTTSRequest(**payload)
    except Exception as req_err:
        raise HTTPException(status_code=422, detail=f"Invalid ServeTTSRequest payload: {req_err}")

    cancel_event = threading.Event()
    inference_done = asyncio.Event()

    with _state_lock:
        if _active_requests == 0:
            _active_since = time.time()
        _active_requests += 1
        _cancel_events.add(cancel_event)

    async def _watch_disconnect():
        try:
            while not inference_done.is_set() and not cancel_event.is_set():
                if await request.is_disconnected():
                    cancel_event.set()
                    logger.warning(
                        f"[FISH_SERVER] Client disconnected — aborting synthesis for text: {req.text[:50]!r}"
                    )
                    break
                try:
                    await asyncio.wait_for(inference_done.wait(), timeout=0.4)
                except asyncio.TimeoutError:
                    pass
        except Exception:
            pass

    # Synthesize audio in a thread pool to avoid blocking the event loop and health checks
    def _do_inference():
        sample_rate = getattr(engine.decoder_model, "sample_rate", 44100)
        if hasattr(engine.decoder_model, "spec_transform"):
            sample_rate = engine.decoder_model.spec_transform.sample_rate
        req_format = getattr(req, "format", "wav") or "wav"

        if req.streaming:
            audio_chunks = []
            for chunk in inference(req, engine, cancel_event=cancel_event):
                if isinstance(chunk, bytes):
                    audio_chunks.append(chunk)
            if not audio_chunks:
                raise RuntimeError("Engine returned 0 streaming chunks.")
            wav_bytes = b"".join(audio_chunks)
        else:
            raw_audio = next(inference(req, engine, cancel_event=cancel_event))
            if raw_audio is None:
                raise RuntimeError("Engine returned None audio.")

            if hasattr(raw_audio, "dtype") or isinstance(raw_audio, (list, tuple)):
                buffer = io.BytesIO()
                sf.write(
                    buffer,
                    raw_audio,
                    sample_rate,
                    format=req_format,
                )
                wav_bytes = buffer.getvalue()
            elif isinstance(raw_audio, bytes):
                wav_bytes = raw_audio
            else:
                raise RuntimeError(f"Unexpected audio type from engine: {type(raw_audio)}")
        return wav_bytes, req_format

    watcher_task = asyncio.create_task(_watch_disconnect())
    try:
        global _vram_paging_detected, _last_wav_kbps
        start_t = time.time()
        wav_bytes, req_format = await asyncio.to_thread(_do_inference)
        elapsed = max(0.001, time.time() - start_t)
        kbps = round((len(wav_bytes) / 1024.0) / elapsed, 1)
        with _state_lock:
            _last_wav_kbps = kbps
            if server_device.startswith("cuda") and len(wav_bytes) > 80_000:
                # 44.1kHz 16-bit mono WAV is ~86 KB/s of audio; normal CUDA generation achieves >25 KB/s,
                # whereas PCIe shared-RAM paging drops below ~8 KB/s (<2 tok/s).
                _vram_paging_detected = kbps < 10.0
        logger.info(f"[FISH_SERVER] Synthesized {len(wav_bytes)} bytes in {elapsed:.2f}s ({kbps:.1f} KB/s) for text: {req.text[:50]!r}")
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        return Response(content=wav_bytes, media_type=f"audio/{req_format}")

    except Exception as synth_err:
        err_text = str(synth_err)
        if cancel_event.is_set() or "cancelled" in err_text.lower():
            logger.warning(f"[FISH_SERVER] Synthesis aborted cleanly: {err_text}")
            raise HTTPException(status_code=499, detail="Synthesis cancelled or client disconnected.")
        logger.error(f"[FISH_SERVER] Synthesis error: {synth_err}")
        raise HTTPException(status_code=500, detail=err_text)
    finally:
        inference_done.set()
        watcher_task.cancel()
        with _state_lock:
            _cancel_events.discard(cancel_event)
            _active_requests = max(0, _active_requests - 1)
            if _active_requests == 0:
                _active_since = None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hecos Fish Speech Local Server")
    parser.add_argument("--port", type=int, default=18480, help="Listen port (default 18480)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host address (default 127.0.0.1)")
    parser.add_argument("--device", type=str, default="auto", help="Device: auto, cuda, or cpu")
    parser.add_argument("--checkpoint-dir", type=str, default=None, help="Path to checkpoint directory")
    parser.add_argument("--max-seq-len", type=int, default=1024, help="Maximum sequence length / KV cache size (default 1024)")
    args = parser.parse_args()

    ckpt_dir = args.checkpoint_dir
    if not ckpt_dir:
        s2_dir = os.path.join(_fish_engine_dir, "checkpoints", "s2-pro")
        legacy_dir = os.path.join(_fish_engine_dir, "checkpoints", "fish-speech-1.5")
        if os.path.isdir(s2_dir) and (os.path.isfile(os.path.join(s2_dir, "codec.pth")) or os.path.isfile(os.path.join(s2_dir, "config.json"))):
            ckpt_dir = s2_dir
        else:
            ckpt_dir = legacy_dir

    try:
        init_engine(ckpt_dir, device=args.device, max_seq_len=args.max_seq_len)
    except Exception as exc:
        logger.error(f"[FISH_SERVER] Failed to initialize engine: {exc}")
        sys.exit(1)

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
