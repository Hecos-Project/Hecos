"""
Fish Speech Local FastAPI Server
Provides a pure-Python, resilient, FastAPI HTTP endpoint (/v1/tts)
compatible with Fish Speech API and Hecos FishSpeechEngine.
Runs locally using checkpoints in hecos/engines/fish_speech/checkpoints/fish-speech-1.5.
Eliminates any reliance on problematic C-extensions (like baize / kui).
"""

import os
import sys
import io
import time
import argparse
import tempfile
from typing import Optional

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


app = FastAPI(title="Hecos Fish Speech Local Server", version="3.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine: Optional[TTSInferenceEngine] = None
server_device: str = "cpu"


def init_engine(checkpoint_dir: str, device: str = "auto", compile_model: bool = False, max_seq_len: int = 2048):
    global engine, server_device

    os.environ["FISH_MAX_SEQ_LEN"] = str(max_seq_len)

    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    server_device = device

    logger.info(f"[FISH_SERVER] Initializing Fish Speech on device: {device} (checkpoint: {checkpoint_dir}, max_seq_len: {max_seq_len})...")

    model_manager = ModelManager(
        mode="tts",
        device=device,
        half=True if device.startswith("cuda") else False,
        compile=compile_model,
        llama_checkpoint_path=checkpoint_dir,
        decoder_checkpoint_path=None,
        decoder_config_name="modded_dac_vq",
    )
    engine = model_manager.tts_inference_engine

    logger.info("=" * 60)
    logger.info(f"✅ Fish Speech engine ({engine.model_family.upper()}) ready on {device.upper()}!")
    logger.info("=" * 60)


@app.get("/")
@app.get("/v1/health")
async def health_check():
    family = getattr(engine, "model_family", "s2-pro") if engine is not None else "s2-pro"
    return {
        "ok": True,
        "status": "ready" if engine is not None else "initializing",
        "engine": f"fish_speech_{family}",
        "device": server_device,
        "cuda_available": torch.cuda.is_available(),
    }


@app.get("/v1/tts/defaults")
async def tts_defaults():
    if engine is None:
        raise HTTPException(status_code=503, detail="Engine not loaded.")
    return engine.sampling_defaults()


@app.post("/v1/tts")
async def tts_endpoint(request: Request):
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

    # Synthesize audio in a thread pool to avoid blocking the event loop and health checks
    def _do_inference():
        sample_rate = getattr(engine.decoder_model, "sample_rate", 44100)
        if hasattr(engine.decoder_model, "spec_transform"):
            sample_rate = engine.decoder_model.spec_transform.sample_rate
        req_format = getattr(req, "format", "wav") or "wav"

        if req.streaming:
            audio_chunks = []
            for chunk in inference(req, engine):
                if isinstance(chunk, bytes):
                    audio_chunks.append(chunk)
            if not audio_chunks:
                raise RuntimeError("Engine returned 0 streaming chunks.")
            wav_bytes = b"".join(audio_chunks)
        else:
            raw_audio = next(inference(req, engine))
            if raw_audio is None:
                raise RuntimeError("Engine returned None audio.")

            if hasattr(raw_audio, "dtype") or isinstance(raw_audio, (list, tuple)):
                import numpy as np
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

    try:
        import asyncio
        start_t = time.time()
        wav_bytes, req_format = await asyncio.to_thread(_do_inference)
        elapsed = time.time() - start_t
        logger.info(f"[FISH_SERVER] Synthesized {len(wav_bytes)} bytes in {elapsed:.2f}s for text: {req.text[:50]!r}")
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        return Response(content=wav_bytes, media_type=f"audio/{req_format}")

    except Exception as synth_err:
        logger.error(f"[FISH_SERVER] Synthesis error: {synth_err}")
        raise HTTPException(status_code=500, detail=str(synth_err))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hecos Fish Speech Local Server")
    parser.add_argument("--port", type=int, default=8080, help="Listen port (default 8080)")
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
