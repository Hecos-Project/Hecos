"""
hecos/core/audio/tts/kokoro/voice_manager.py
Manages custom Kokoro voice packs (.pt) in hecos/models/kokoro/voices
and source tracks from hecos/assets/voice_clones.
"""

import os
import re
import json
import time
import glob
import torch
from hecos.core.logging import logger

_VOICE_PACK_CACHE = {}


class KokoroVoiceManager:
    """Registry and storage manager for custom Kokoro cloned voices (.pt)."""

    @classmethod
    def get_hecos_dir(cls) -> str:
        """Returns the hecos package root directory (e.g. C:\Hecos\hecos)."""
        return os.path.normpath(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))

    @classmethod
    def get_voices_dir(cls) -> str:
        """Returns hecos/models/kokoro/voices directory."""
        p = os.path.normpath(os.path.join(cls.get_hecos_dir(), "models", "kokoro", "voices"))
        os.makedirs(p, exist_ok=True)
        return p

    @classmethod
    def get_source_audio_dir(cls) -> str:
        """Returns hecos/assets/voice_clones directory containing reference audio tracks."""
        p1 = os.path.normpath(os.path.join(cls.get_hecos_dir(), "assets", "voice_clones"))
        if os.path.isdir(p1):
            return p1
        p2 = os.path.normpath(os.path.join(cls.get_hecos_dir(), "..", "assets", "voice_clones"))
        if os.path.isdir(p2):
            return p2
        os.makedirs(p1, exist_ok=True)
        return p1

    @classmethod
    def get_root_dir(cls) -> str:
        """Returns root workspace directory."""
        return os.path.normpath(os.path.abspath(os.path.join(cls.get_hecos_dir(), "..")))

    @property
    def VOICES_DIR(self):
        return self.get_voices_dir()

    @property
    def SOURCES_DIR(self):
        return self.get_source_audio_dir()


    @classmethod
    def list_sources(cls) -> list:
        """Returns all available reference audio WAV files from assets/voice_clones."""
        source_dir = cls.get_source_audio_dir()
        voices_dir = cls.get_voices_dir()
        installed_pt_files = [os.path.splitext(os.path.basename(f))[0].lower() for f in glob.glob(os.path.join(voices_dir, "*.pt"))]

        results = []
        for f in glob.glob(os.path.join(source_dir, "*.wav")):
            bname = os.path.basename(f)
            name_no_ext = os.path.splitext(bname)[0]
            size_bytes = os.path.getsize(f)
            size_kb = round(size_bytes / 1024, 1)

            # Check if any installed voice originates or matches this name
            has_clone = any(name_no_ext.lower() in pt or pt in name_no_ext.lower() for pt in installed_pt_files)

            results.append({
                "filename": bname,
                "name": name_no_ext,
                "path": f,
                "size_kb": size_kb,
                "has_clone": has_clone,
                "mtime": os.path.getmtime(f)
            })

        results.sort(key=lambda x: x["filename"].lower())
        return results

    @classmethod
    def list_custom_voices(cls) -> list:
        """Returns metadata for all installed custom Kokoro voice packs (.pt)."""
        voices_dir = cls.get_voices_dir()
        voices = []

        for pt_path in glob.glob(os.path.join(voices_dir, "*.pt")):
            filename = os.path.basename(pt_path)
            voice_id = os.path.splitext(filename)[0]
            json_path = os.path.splitext(pt_path)[0] + ".json"

            meta = {}
            if os.path.exists(json_path):
                try:
                    with open(json_path, "r", encoding="utf-8") as jf:
                        meta = json.load(jf)
                except Exception as je:
                    logger.debug("KOKORO_VM", f"Error reading meta for {filename}: {je}")

            lang_code = meta.get("lang_code") or (voice_id[0] if len(voice_id) > 2 and voice_id[0] in "abefhijpz" else "i")
            gender = meta.get("gender") or (voice_id[1] if len(voice_id) > 2 and voice_id[1] in "mf" else "f")
            display_name = meta.get("name") or voice_id

            lang_prefix = f"{lang_code}{gender}"

            voices.append({
                "id": voice_id,
                "voice_id": voice_id,
                "filename": filename,
                "name": display_name,
                "display_title": display_name,
                "display_label": f"🎭 {display_name} (Custom {lang_code.upper()})",
                "lang_code": lang_code,
                "gender": gender,
                "lang_prefix": lang_prefix,
                "source_wav": meta.get("source_wav", ""),
                "path": pt_path,
                "size": os.path.getsize(pt_path),
                "size_kb": round(os.path.getsize(pt_path) / 1024, 1),
                "created_at": meta.get("created_at") or time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(pt_path)))
            })

        voices.sort(key=lambda x: x["name"].lower())
        return voices

    @classmethod
    def get_custom_voice_dict(cls) -> dict:
        """Returns a dict of {voice_id: display_label} for Kokoro dropdowns."""
        return {v["id"]: v["display_label"] for v in cls.list_custom_voices()}

    @classmethod
    def resolve_voice_pack(cls, voice_id: str):
        """
        Resolves voice_id to a torch.Tensor pack or .pt path.
        Returns (pack_or_path, lang_code).
        """
        if not voice_id:
            return None, "a"

        # Check in memory cache
        if voice_id in _VOICE_PACK_CACHE:
            pack, lang = _VOICE_PACK_CACHE[voice_id]
            return pack, lang

        voices_dir = cls.get_voices_dir()
        pt_path = None

        if voice_id.endswith(".pt") and os.path.isfile(voice_id):
            pt_path = voice_id
        else:
            cand = os.path.join(voices_dir, f"{voice_id}.pt")
            if os.path.isfile(cand):
                pt_path = cand

        if pt_path:
            try:
                pack = torch.load(pt_path, weights_only=True)
                # Read metadata for lang_code if available
                json_path = os.path.splitext(pt_path)[0] + ".json"
                lang_code = "a"
                if os.path.exists(json_path):
                    with open(json_path, "r", encoding="utf-8") as jf:
                        lang_code = json.load(jf).get("lang_code", "a")
                else:
                    bname = os.path.basename(pt_path)
                    if bname[0] in "abefhijpz":
                        lang_code = bname[0]

                _VOICE_PACK_CACHE[voice_id] = (pack, lang_code)
                return pack, lang_code
            except Exception as e:
                logger.error("KOKORO_VM", f"Failed to load custom voice pack {pt_path}: {e}")

        return None, None

    @classmethod
    def create_clone(cls, wav_filename: str, custom_name: str, lang_prefix: str = "af", display_title: str = None) -> dict:
        """
        Extracts voice pack from wav_filename and saves it as a new custom Kokoro voice.
        """
        from .cloner import KokoroCloner

        source_dir = cls.get_source_audio_dir()
        wav_path = os.path.join(source_dir, wav_filename) if not os.path.isabs(wav_filename) else wav_filename
        if not os.path.isfile(wav_path):
            raise FileNotFoundError(f"Source WAV not found: {wav_path}")

        # Clean voice ID
        clean_name = re.sub(r'[^a-zA-Z0-9_-]', '_', custom_name.strip()).lower().strip('_')
        if not clean_name:
            clean_name = "custom_voice"

        prefix = lang_prefix.lower() if lang_prefix else "af"
        voice_id = f"{prefix}_{clean_name}" if not clean_name.startswith(prefix) else clean_name

        voices_dir = cls.get_voices_dir()
        output_pt = os.path.join(voices_dir, f"{voice_id}.pt")
        output_json = os.path.join(voices_dir, f"{voice_id}.json")

        # Enroll and save tensor
        pack = KokoroCloner.enroll_from_wav(wav_path, output_pt)

        # Meta
        lang_code = prefix[0] if len(prefix) > 0 else "a"
        gender = prefix[1] if len(prefix) > 1 else "f"
        final_title = display_title or custom_name.strip()

        meta = {
            "id": voice_id,
            "name": final_title,
            "lang_code": lang_code,
            "gender": gender,
            "source_wav": os.path.basename(wav_path),
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        with open(output_json, "w", encoding="utf-8") as jf:
            json.dump(meta, jf, indent=2)

        # Invalidate cache
        _VOICE_PACK_CACHE[voice_id] = (pack, lang_code)
        logger.info("KOKORO_VM", f"Successfully created Kokoro custom voice '{voice_id}' ({output_pt})")

        return {
            "ok": True,
            "voice_id": voice_id,
            "name": final_title,
            "path": output_pt,
            "lang_code": lang_code,
            "gender": gender
        }

    @classmethod
    def delete_clone(cls, voice_id: str) -> bool:
        """Deletes a custom Kokoro voice pack and metadata."""
        voices_dir = cls.get_voices_dir()
        pt_path = os.path.join(voices_dir, f"{voice_id}.pt")
        json_path = os.path.join(voices_dir, f"{voice_id}.json")

        deleted = False
        if os.path.exists(pt_path):
            os.remove(pt_path)
            deleted = True
        if os.path.exists(json_path):
            os.remove(json_path)

        if voice_id in _VOICE_PACK_CACHE:
            del _VOICE_PACK_CACHE[voice_id]

        return deleted
