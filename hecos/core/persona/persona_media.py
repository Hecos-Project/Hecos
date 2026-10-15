import os
import shutil
import time
from werkzeug.utils import secure_filename
from hecos.core.constants import HECOS_DIR

class PersonaMediaManager:
    """
    Manages media library and avatars for Hecos personas (Souls).
    Paths:
      hecos/personas/<soul>/media/   -> all media files
      hecos/personas/<soul>/avatars/ -> current avatar (image or video)
    """
    
    ALLOWED_IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.webp', '.gif'}
    ALLOWED_VIDEO_EXTS = {'.mp4', '.webm', '.mov', '.avi'}
    ALLOWED_AUDIO_EXTS = {'.mp3', '.wav', '.ogg', '.m4a'}
    
    @staticmethod
    def _personas_dir():
        return os.path.join(HECOS_DIR, "personas")

    @staticmethod
    def _persona_dir(persona_name: str) -> str:
        safe_name = persona_name.replace(".yaml", "")
        # Prevent path traversal
        if ".." in safe_name or "/" in safe_name or "\\" in safe_name:
            safe_name = "Hecos_System_Soul"
        
        p_dir = os.path.join(PersonaMediaManager._personas_dir(), safe_name)
        if not os.path.isdir(p_dir):
            return os.path.join(PersonaMediaManager._personas_dir(), "Hecos_System_Soul")
        return p_dir

    @staticmethod
    def _ensure_dirs(persona_dir: str):
        media_dir = os.path.join(persona_dir, "media")
        avatars_dir = os.path.join(persona_dir, "avatars")
        os.makedirs(media_dir, exist_ok=True)
        os.makedirs(avatars_dir, exist_ok=True)
        return media_dir, avatars_dir

    @staticmethod
    def resolve_avatar(persona_name: str) -> dict:
        """
        Returns the current avatar info for a persona.
        Looks in avatars/ folder. Returns the first valid image/video found.
        """
        import urllib.parse
        
        safe_name = persona_name.replace(".yaml", "")
        if ".." in safe_name or "/" in safe_name or "\\" in safe_name:
            safe_name = "Hecos_System_Soul"
            
        p_dir = os.path.join(PersonaMediaManager._personas_dir(), safe_name)
        default_avatar = {"url": "/assets/Hecos_Logo_NBG.png", "type": "image"}
        
        if not os.path.isdir(p_dir):
            return default_avatar
            
        avatars_dir = os.path.join(p_dir, "avatars")
        if not os.path.isdir(avatars_dir):
            return default_avatar
            
        try:
            for f in sorted(os.listdir(avatars_dir)):
                ext = os.path.splitext(f)[1].lower()
                is_img = ext in PersonaMediaManager.ALLOWED_IMAGE_EXTS
                is_vid = ext in PersonaMediaManager.ALLOWED_VIDEO_EXTS
                
                if is_img or is_vid:
                    rel_path = f"/personas/{urllib.parse.quote(safe_name)}/avatars/{urllib.parse.quote(f)}"
                    return {
                        "url": rel_path,
                        "type": "video" if is_vid else "image"
                    }
        except Exception:
            pass
            
        return default_avatar

    @staticmethod
    def list_media(persona_name: str) -> list:
        """
        Lists all media files in the persona's media/ directory.
        Also checks avatars/ to flag the current avatar if it matches by name.
        """
        import urllib.parse
        
        p_dir = PersonaMediaManager._persona_dir(persona_name)
        media_dir, avatars_dir = PersonaMediaManager._ensure_dirs(p_dir)
        
        # Find current avatar filename to flag it
        current_avatar_filename = None
        try:
            for f in sorted(os.listdir(avatars_dir)):
                ext = os.path.splitext(f)[1].lower()
                if ext in PersonaMediaManager.ALLOWED_IMAGE_EXTS or ext in PersonaMediaManager.ALLOWED_VIDEO_EXTS:
                    current_avatar_filename = f
                    break
        except Exception:
            pass

        items = []
        safe_name = os.path.basename(p_dir)
        
        try:
            for f in os.listdir(media_dir):
                file_path = os.path.join(media_dir, f)
                if not os.path.isfile(file_path):
                    continue
                    
                ext = os.path.splitext(f)[1].lower()
                media_type = "other"
                if ext in PersonaMediaManager.ALLOWED_IMAGE_EXTS:
                    media_type = "image"
                elif ext in PersonaMediaManager.ALLOWED_VIDEO_EXTS:
                    media_type = "video"
                elif ext in PersonaMediaManager.ALLOWED_AUDIO_EXTS:
                    media_type = "audio"
                    
                try:
                    stat = os.stat(file_path)
                    size = stat.st_size
                    mtime = stat.st_mtime
                except Exception:
                    size = 0
                    mtime = 0
                    
                rel_url = f"/personas/{urllib.parse.quote(safe_name)}/media/{urllib.parse.quote(f)}"
                
                items.append({
                    "name": f,
                    "url": rel_url,
                    "type": media_type,
                    "size": size,
                    "mtime": mtime,
                    "is_avatar": (f == current_avatar_filename)
                })
                
            # Sort newest first
            items.sort(key=lambda x: x["mtime"], reverse=True)
            return items
        except Exception as e:
            return []

    @staticmethod
    def upload_media(persona_name: str, file_obj) -> dict:
        """Saves a file to media/ folder."""
        p_dir = PersonaMediaManager._persona_dir(persona_name)
        media_dir, _ = PersonaMediaManager._ensure_dirs(p_dir)
        
        filename = secure_filename(file_obj.filename)
        if not filename:
            raise ValueError("Invalid filename")
            
        save_path = os.path.join(media_dir, filename)
        file_obj.save(save_path)
        
        # Determine type
        ext = os.path.splitext(filename)[1].lower()
        mtype = "other"
        if ext in PersonaMediaManager.ALLOWED_IMAGE_EXTS: mtype = "image"
        elif ext in PersonaMediaManager.ALLOWED_VIDEO_EXTS: mtype = "video"
        elif ext in PersonaMediaManager.ALLOWED_AUDIO_EXTS: mtype = "audio"
        
        import urllib.parse
        safe_name = os.path.basename(p_dir)
        rel_url = f"/personas/{urllib.parse.quote(safe_name)}/media/{urllib.parse.quote(filename)}"
        
        return {
            "name": filename,
            "url": rel_url,
            "type": mtype,
            "size": os.path.getsize(save_path),
            "mtime": os.path.getmtime(save_path)
        }

    @staticmethod
    def delete_media(persona_name: str, filenames: list) -> int:
        """Deletes specified files from media/. Does NOT delete from avatars/."""
        p_dir = PersonaMediaManager._persona_dir(persona_name)
        media_dir, _ = PersonaMediaManager._ensure_dirs(p_dir)
        
        deleted = 0
        for fname in filenames:
            safe_fname = secure_filename(fname)
            if not safe_fname:
                continue
                
            path = os.path.join(media_dir, safe_fname)
            if os.path.exists(path) and os.path.isfile(path):
                try:
                    os.remove(path)
                    deleted += 1
                except Exception:
                    pass
        return deleted

    @staticmethod
    def rename_media(persona_name: str, old_name: str, new_name: str) -> dict:
        """Renames a file in media/."""
        p_dir = PersonaMediaManager._persona_dir(persona_name)
        media_dir, _ = PersonaMediaManager._ensure_dirs(p_dir)
        
        safe_old = secure_filename(old_name)
        safe_new = secure_filename(new_name)
        
        if not safe_old or not safe_new:
            raise ValueError("Invalid filename")
            
        old_path = os.path.join(media_dir, safe_old)
        new_path = os.path.join(media_dir, safe_new)
        
        if not os.path.exists(old_path):
            raise FileNotFoundError("File not found")
            
        if os.path.exists(new_path):
            raise FileExistsError("Target file already exists")
            
        os.rename(old_path, new_path)
        
        import urllib.parse
        safe_name = os.path.basename(p_dir)
        rel_url = f"/personas/{urllib.parse.quote(safe_name)}/media/{urllib.parse.quote(safe_new)}"
        
        return {
            "name": safe_new,
            "url": rel_url
        }

    @staticmethod
    def set_avatar(persona_name: str, filename: str) -> dict:
        """
        Sets a file from media/ as the active avatar.
        Moves existing avatar to media/ (if not already there), then copies new file to avatars/.
        """
        p_dir = PersonaMediaManager._persona_dir(persona_name)
        media_dir, avatars_dir = PersonaMediaManager._ensure_dirs(p_dir)
        
        safe_filename = secure_filename(filename)
        if not safe_filename:
            raise ValueError("Invalid filename")
            
        source_path = os.path.join(media_dir, safe_filename)
        if not os.path.exists(source_path):
            # If not in media, check if it was directly uploaded to avatars/
            # (legacy upload API wrapper)
            direct_avatar_path = os.path.join(avatars_dir, safe_filename)
            if not os.path.exists(direct_avatar_path):
                raise FileNotFoundError(f"File {safe_filename} not found in media")
            source_path = direct_avatar_path
            
        # 1. Back up existing avatars to media/ and delete them from avatars/
        try:
            for f in os.listdir(avatars_dir):
                old_avatar_path = os.path.join(avatars_dir, f)
                if os.path.isfile(old_avatar_path):
                    # Only backup if not already in media
                    media_backup_path = os.path.join(media_dir, f)
                    if not os.path.exists(media_backup_path) and old_avatar_path != source_path:
                        shutil.copy2(old_avatar_path, media_backup_path)
                    
                    # Delete from avatars/ so it's clean
                    if old_avatar_path != source_path:
                        os.remove(old_avatar_path)
        except Exception as e:
            pass # Keep going even if cleanup fails
            
        # 2. Copy the new avatar to avatars/ (unless it's already there)
        target_path = os.path.join(avatars_dir, safe_filename)
        if source_path != target_path:
            shutil.copy2(source_path, target_path)
            
        return PersonaMediaManager.resolve_avatar(persona_name)
