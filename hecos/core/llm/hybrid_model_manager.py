"""
hecos/core/llm/hybrid_model_manager.py
Provides a unified list of models across local and cloud backends,
enriched with architecture, quantization, disk size, and capability metadata.
"""
import glob
import json
import os
import re
import time
from typing import Dict, List, Optional, Tuple

from hecos.core.logging import logger

_META_CACHE_TTL_SEC = 120
_SHOW_PROBE_LIMIT = 15

_LOCAL_VISION_KEYWORDS = (
    "vision", "-vl", "vl:", "_vl", "llava", "moondream", "minicpm",
    "cogvlm", "bakllava", "pixtral", "internvl", "obsidian",
)
_CLOUD_VISION_KEYWORDS = (
    "vision", "-vl", "llava", "pixtral",
    "gpt-4o", "gpt-4.1", "gemini", "claude-3", "claude-4", "grok-2-vision",
)
_THINKING_KEYWORDS = (
    "qwen3", "qwen35", "qwen3.5", "qwen3.8", "gemma4", "gemma-4",
    "deepseek-r1", "deepseek_r1", "qwq", "gpt-oss", "thinking",
    "reasoner", "-r1", "o1-", "o3-", "o4-", "claude-3-7", "claude-4",
    "gemini-2.5", "gemini-3",
)
_TOOLS_KEYWORDS = (
    "qwen2.5", "qwen3", "qwen35", "qwen3.5", "qwen3.8",
    "llama3", "llama-3", "llama4", "mistral", "mixtral",
    "gemma4", "gemma-4", "command-r", "hermes", "phi4", "phi-4",
    "gpt-oss", "deepseek", "gpt-4", "claude", "gemini", "glm-4",
    "granite", "devstral", "codestral",
)


def _canonical_caps(caps: List[str]) -> List[str]:
    """Order capabilities consistently (thinking, tools, vision, plus any extras)."""
    order = {"thinking": 0, "tools": 1, "vision": 2}
    cleaned = [c for c in dict.fromkeys(caps) if c and c != "completion"]
    return sorted(cleaned, key=lambda c: (order.get(c, 99), c))


def _format_size_human(size_bytes: int) -> str:
    if not size_bytes or size_bytes <= 0:
        return ""
    if size_bytes >= 1024 ** 3:
        return f"{size_bytes / (1024 ** 3):.1f} GB"
    return f"{size_bytes / (1024 ** 2):.0f} MB"


def _build_description(
    name: str,
    provider: str,
    family: str = "",
    param_size: str = "",
    quant: str = "",
    size_bytes: int = 0,
    capabilities: Optional[List[str]] = None,
    context_length: int = 0,
    has_projector: bool = False,
) -> str:
    """Build a concise descriptive summary string for tooltips & UI badges."""
    parts = []
    if family:
        parts.append(f"Family: {family}")
    spec = " ".join(x for x in (param_size, quant) if x)
    if spec:
        parts.append(spec)
    size_str = _format_size_human(size_bytes)
    if size_str:
        parts.append(f"Disk: {size_str}")
    if context_length and context_length > 0:
        k_ctx = f"{context_length // 1024}k" if context_length >= 1024 else str(context_length)
        parts.append(f"Ctx: {k_ctx}")
    if has_projector:
        parts.append("Multimodal Projector")

    cap_labels = {
        "thinking": "Thinking/Reasoning",
        "tools": "Tools/Function Calling",
        "vision": "Vision/Multimodal",
    }
    caps = _canonical_caps(capabilities or [])
    if caps:
        parts.append("Supports: " + ", ".join(cap_labels.get(c, c.title()) for c in caps))
    elif provider in ("ollama", "llama_cpp", "kobold"):
        parts.append("Standard text generation")

    return " · ".join(parts) if parts else name


def _infer_capabilities(
    name: str,
    family: str = "",
    renderer: str = "",
    parser: str = "",
    has_projector: bool = False,
    template_text: str = "",
    is_cloud: bool = False,
) -> List[str]:
    """Infer model capabilities from architecture, template, projector layers, and model name."""
    haystack = " ".join(x for x in (name, family, renderer, parser) if x).lower()
    tmpl_low = (template_text or "").lower()
    caps = []

    if any(k in haystack for k in _THINKING_KEYWORDS) or "<think" in tmpl_low or "thinking" in tmpl_low or "reasoning" in tmpl_low:
        caps.append("thinking")

    if any(k in haystack for k in _TOOLS_KEYWORDS) or "tools" in tmpl_low or "tool_call" in tmpl_low:
        caps.append("tools")

    vision_kws = _CLOUD_VISION_KEYWORDS if is_cloud else _LOCAL_VISION_KEYWORDS
    if has_projector or any(k in haystack for k in vision_kws):
        caps.append("vision")

    return _canonical_caps(caps)


def _get_cache_path() -> str:
    hecos_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    tmp_dir = os.path.join(hecos_root, "tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    return os.path.join(tmp_dir, "ollama_models_meta_cache.json")


def _load_meta_cache() -> dict:
    try:
        path = _get_cache_path()
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except Exception:
        pass
    return {}


def _save_meta_cache(cache: dict) -> None:
    try:
        path = _get_cache_path()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
    except Exception:
        pass


def _get_ollama_models_dir() -> str:
    env_dir = os.environ.get("OLLAMA_MODELS")
    if env_dir and os.path.isdir(env_dir):
        return env_dir
    return os.path.join(os.path.expanduser("~"), ".ollama", "models")


def _find_ollama_manifest_path(models_dir: str, model_name: str) -> Optional[str]:
    manifests_root = os.path.join(models_dir, "manifests")
    if not os.path.isdir(manifests_root):
        return None

    clean = (model_name or "").strip()
    if not clean:
        return None

    if ":" in clean.split("/")[-1]:
        repo_part, tag = clean.rsplit(":", 1)
    else:
        repo_part, tag = clean, "latest"

    segments = [s for s in repo_part.split("/") if s]
    if len(segments) == 1:
        candidates = [os.path.join(manifests_root, "registry.ollama.ai", "library", segments[0], tag)]
    elif len(segments) == 2:
        candidates = [
            os.path.join(manifests_root, "registry.ollama.ai", segments[0], segments[1], tag),
            os.path.join(manifests_root, segments[0], segments[1], tag),
        ]
    else:
        candidates = [os.path.join(manifests_root, *segments, tag)]

    for cand in candidates:
        if os.path.isfile(cand):
            return cand

    # Fallback: fuzzy tail match across local manifests
    tail = os.path.join(*segments, tag).lower() if segments else ""
    for fp in glob.glob(os.path.join(manifests_root, "**", "*"), recursive=True):
        if os.path.isfile(fp) and fp.lower().endswith(tail):
            return fp
    return None


def _read_local_ollama_manifest(model_name: str) -> dict:
    """Read Ollama model size, family, params, quant, projector, and template directly from disk."""
    models_dir = _get_ollama_models_dir()
    manifest_path = _find_ollama_manifest_path(models_dir, model_name)
    if not manifest_path:
        return {}

    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception:
        return {}

    cfg_meta = manifest.get("config") or {}
    layers = manifest.get("layers") or []
    size_bytes = int(cfg_meta.get("size") or 0) + sum(int(l.get("size") or 0) for l in layers)

    has_projector = any("projector" in (l.get("mediaType") or "").lower() for l in layers)

    blobs_dir = os.path.join(models_dir, "blobs")
    cfg_digest = (cfg_meta.get("digest") or "").replace(":", "-")
    cfg_json = {}
    if cfg_digest:
        cfg_blob = os.path.join(blobs_dir, cfg_digest)
        if os.path.isfile(cfg_blob):
            try:
                with open(cfg_blob, "r", encoding="utf-8") as f:
                    cfg_json = json.load(f)
            except Exception:
                pass

    template_text = ""
    for l in layers:
        if (l.get("mediaType") or "").endswith(".template"):
            td = (l.get("digest") or "").replace(":", "-")
            tpath = os.path.join(blobs_dir, td)
            if os.path.isfile(tpath):
                try:
                    with open(tpath, "r", encoding="utf-8", errors="ignore") as f:
                        template_text = f.read(8192)
                except Exception:
                    pass
            break

    family = cfg_json.get("model_family") or ""
    if not family and isinstance(cfg_json.get("model_families"), list) and cfg_json["model_families"]:
        family = cfg_json["model_families"][0]
    param_size = cfg_json.get("model_type") or ""
    quant_level = cfg_json.get("file_type") or ""
    renderer = cfg_json.get("renderer") or ""
    parser = cfg_json.get("parser") or ""

    caps = _infer_capabilities(
        model_name,
        family=family,
        renderer=renderer,
        parser=parser,
        has_projector=has_projector,
        template_text=template_text,
    )

    return {
        "capabilities": caps,
        "size_bytes": size_bytes,
        "parameter_size": param_size,
        "quantization_level": quant_level,
        "family": family,
        "has_projector": has_projector,
        "digest": cfg_meta.get("digest") or "",
    }


def _extract_context_length(show_json: dict) -> int:
    model_info = show_json.get("model_info") or {}
    for k, v in model_info.items():
        if str(k).endswith(".context_length") and isinstance(v, (int, float)):
            return int(v)
    return 0


def _collect_ollama_metadata(ollama_models: List[str], config: dict, fast_mode: bool) -> Dict[str, dict]:
    """Resolve metadata for all Ollama models combining cache, local manifests, and live API."""
    cache = _load_meta_cache()
    meta_by_name: Dict[str, dict] = {}
    cache_dirty = False

    # 1. Seed from persistent cache + local Ollama disk manifests (zero network wait)
    for name in ollama_models:
        cached = cache.get(name) or {}
        disk = _read_local_ollama_manifest(name)
        merged = {
            "capabilities": list(cached.get("capabilities") or []),
            "size_bytes": cached.get("size_bytes") or 0,
            "parameter_size": cached.get("parameter_size") or "",
            "quantization_level": cached.get("quantization_level") or "",
            "family": cached.get("family") or "",
            "context_length": cached.get("context_length") or 0,
            "has_projector": bool(cached.get("has_projector")),
            "digest": cached.get("digest") or "",
            "show_checked": bool(cached.get("show_checked")),
            "ts": cached.get("ts") or 0,
        }
        if disk:
            if not merged["size_bytes"] or (disk.get("digest") and disk["digest"] != merged["digest"]):
                merged["size_bytes"] = disk.get("size_bytes") or merged["size_bytes"]
                merged["show_checked"] = False
            merged["parameter_size"] = disk.get("parameter_size") or merged["parameter_size"]
            merged["quantization_level"] = disk.get("quantization_level") or merged["quantization_level"]
            merged["family"] = disk.get("family") or merged["family"]
            merged["has_projector"] = merged["has_projector"] or bool(disk.get("has_projector"))
            if disk.get("digest"):
                merged["digest"] = disk["digest"]
            if not merged["capabilities"] or not merged["show_checked"]:
                merged["capabilities"] = _canonical_caps(disk.get("capabilities") or [])
            cache[name] = dict(merged, ts=merged["ts"] or time.time())
            cache_dirty = True

        # Fallback inference if model exists only remotely/in config without manifest match
        if not merged["capabilities"]:
            merged["capabilities"] = _infer_capabilities(name, family=merged["family"], has_projector=merged["has_projector"])

        meta_by_name[name] = merged

    # 2. Enrich live from Ollama API (quick timeout so offline Ollama doesn't stall UI)
    try:
        import requests as _req
        ollama_base = config.get("backend", {}).get("ollama", {}).get("url", "http://localhost:11434").rstrip("/")
        tags_timeout = 0.6 if fast_mode else 2.5
        resp = _req.get(f"{ollama_base}/api/tags", timeout=tags_timeout)
        if resp.status_code == 200:
            now = time.time()
            show_probes = 0
            for m in resp.json().get("models", []):
                name = m.get("name", "")
                if not name:
                    continue
                entry = dict(meta_by_name.get(name) or {})
                details = m.get("details") or {}
                live_caps = _canonical_caps(m.get("capabilities", []))
                digest = m.get("digest") or entry.get("digest") or ""

                entry["size_bytes"] = m.get("size") or entry.get("size_bytes") or 0
                entry["parameter_size"] = details.get("parameter_size") or entry.get("parameter_size") or ""
                entry["quantization_level"] = details.get("quantization_level") or entry.get("quantization_level") or ""
                entry["family"] = details.get("family") or entry.get("family") or ""

                if live_caps:
                    entry["capabilities"] = live_caps
                    entry["show_checked"] = True
                else:
                    needs_show = (
                        not entry.get("show_checked")
                        or (digest and digest != entry.get("digest"))
                        or (now - float(entry.get("ts") or 0) > _META_CACHE_TTL_SEC and not entry.get("context_length"))
                    )
                    if needs_show and show_probes < _SHOW_PROBE_LIMIT:
                        show_probes += 1
                        try:
                            s_resp = _req.post(
                                f"{ollama_base}/api/show",
                                json={"model": name},
                                timeout=0.6 if fast_mode else 1.5,
                            )
                            if s_resp.status_code == 200:
                                s_json = s_resp.json()
                                show_caps = _canonical_caps(s_json.get("capabilities", []))
                                s_det = s_json.get("details") or {}
                                entry["parameter_size"] = s_det.get("parameter_size") or entry["parameter_size"]
                                entry["quantization_level"] = s_det.get("quantization_level") or entry["quantization_level"]
                                entry["family"] = s_det.get("family") or entry["family"]
                                ctx_len = _extract_context_length(s_json)
                                if ctx_len:
                                    entry["context_length"] = ctx_len
                                has_proj = entry.get("has_projector") or bool(s_json.get("projector_info"))
                                entry["has_projector"] = has_proj
                                if show_caps:
                                    entry["capabilities"] = show_caps
                                else:
                                    entry["capabilities"] = _canonical_caps(
                                        entry.get("capabilities", [])
                                        + _infer_capabilities(
                                            name,
                                            family=entry["family"],
                                            has_projector=has_proj,
                                            template_text=s_json.get("template") or "",
                                        )
                                    )
                                entry["show_checked"] = True
                        except Exception:
                            pass

                if not entry.get("capabilities"):
                    entry["capabilities"] = _infer_capabilities(
                        name,
                        family=entry.get("family", ""),
                        has_projector=bool(entry.get("has_projector")),
                    )

                entry["digest"] = digest
                entry["ts"] = now
                meta_by_name[name] = entry
                cache[name] = entry
                cache_dirty = True
    except Exception as e:
        logger.debug(f"[HYBRID] Live Ollama metadata unavailable (using local/cached metadata): {e}")

    if cache_dirty:
        _save_meta_cache(cache)

    return meta_by_name


def _parse_gguf_metadata(filename: str, size_bytes: int) -> dict:
    param_match = re.search(r"(?i)(?:^|[-_.\s])(\d+(?:\.\d+)?[bm])(?=$|[-_.\s.])", filename)
    quant_match = re.search(r"(?i)(IQ\d+_[A-Z0-9_]+|Q\d+_[K0-9_A-Z]+|BF16|F16|F32)", filename)
    param_size = param_match.group(1).upper() if param_match else ""
    quant_level = quant_match.group(1).upper() if quant_match else ""
    caps = _infer_capabilities(filename)
    return {
        "capabilities": caps,
        "parameter_size": param_size,
        "quantization_level": quant_level,
        "size_bytes": size_bytes,
        "description": _build_description(
            filename,
            provider="llama_cpp",
            param_size=param_size,
            quant=quant_level,
            size_bytes=size_bytes,
            capabilities=caps,
        ),
    }


def get_hybrid_models(config: dict, config_manager=None, fast_mode=True) -> list:
    """
    Returns a combined list of local and cloud models.
    Uses fast_mode to avoid blocking the HTTP request while still resolving rich metadata
    from local Ollama manifests, cache, GGUF filenames, and live Ollama API when running.
    """
    models = []

    if config_manager is None:
        logger.warning("[HYBRID] No config_manager provided; local models may be unavailable.")
        return models

    try:
        from hecos.app.model_manager import ModelManager
        mm = ModelManager(config_manager)
        categorized = mm.get_available_models(fast_mode=fast_mode)

        ollama_list = list(categorized.get("Ollama (Local)", []))
        ollama_meta = _collect_ollama_metadata(ollama_list, config, fast_mode=fast_mode)

        # 1. Local Models
        for m in ollama_list:
            meta = ollama_meta.get(m, {})
            caps = _canonical_caps(meta.get("capabilities", []))
            param_size = meta.get("parameter_size", "")
            quant_level = meta.get("quantization_level", "")
            size_bytes = meta.get("size_bytes", 0)
            family = meta.get("family", "")
            ctx_len = meta.get("context_length", 0)
            has_proj = bool(meta.get("has_projector"))
            models.append({
                "id": m,
                "name": m,
                "type": "local",
                "provider": "ollama",
                "capabilities": caps,
                "parameter_size": param_size,
                "quantization_level": quant_level,
                "size_bytes": size_bytes,
                "family": family,
                "context_length": ctx_len,
                "has_projector": has_proj,
                "description": _build_description(
                    m,
                    provider="ollama",
                    family=family,
                    param_size=param_size,
                    quant=quant_level,
                    size_bytes=size_bytes,
                    capabilities=caps,
                    context_length=ctx_len,
                    has_projector=has_proj,
                ),
            })

        for m in categorized.get("Kobold (Local)", []):
            caps = _infer_capabilities(m)
            models.append({
                "id": m,
                "name": m,
                "type": "local",
                "provider": "kobold",
                "capabilities": caps,
                "parameter_size": "",
                "quantization_level": "",
                "size_bytes": 0,
                "description": _build_description(m, provider="kobold", capabilities=caps),
            })

        llama_cpp_models = categorized.get("LlamaCPP (Local)") or {}
        if isinstance(llama_cpp_models, dict):
            for _display_name, filename in llama_cpp_models.items():
                size_bytes = 0
                try:
                    from hecos.core.llm.backends.llama_cpp.discovery import get_model_path
                    filepath = get_model_path(filename)
                    if filepath and os.path.isfile(filepath):
                        size_bytes = os.path.getsize(filepath)
                except Exception:
                    pass
                g_meta = _parse_gguf_metadata(filename, size_bytes)
                models.append({
                    "id": filename,
                    "name": filename,
                    "type": "local",
                    "provider": "llama_cpp",
                    **g_meta,
                })
        else:
            for m in llama_cpp_models:
                g_meta = _parse_gguf_metadata(m, 0)
                models.append({
                    "id": m,
                    "name": m,
                    "type": "local",
                    "provider": "llama_cpp",
                    **g_meta,
                })

        # 2. Cloud Models — always shown if providers are configured
        for cat_key, cat_models in categorized.items():
            if cat_key.startswith("Cloud"):
                for m in cat_models:
                    provider = m.split("/")[0] if "/" in m else "cloud"
                    caps = _infer_capabilities(m, is_cloud=True)
                    models.append({
                        "id": m,
                        "name": m,
                        "type": "cloud",
                        "provider": provider,
                        "capabilities": caps,
                        "description": _build_description(m, provider=provider, capabilities=caps),
                    })
    except Exception as e:
        logger.warning(f"[HYBRID] Failed to get models: {e}")

    return models
