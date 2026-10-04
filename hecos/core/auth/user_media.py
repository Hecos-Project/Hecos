import os
import shutil
from werkzeug.utils import secure_filename
from hecos.memory.user_vault_manager import get_vault_path

class UserMediaManager:
    """
    Manages media library and avatars for Hecos users.
    Paths:
      hecos/memory/users/<username>/media/   -> all media files
      hecos/memory/users/<username>/avatars/ -> current avatar (image or video)
    """
    
    ALLOWED_IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.webp', '.gif'}
    ALLOWED_VIDEO_EXTS = {'.mp4', '.webm', '.mov', '.avi'}
    ALLOWED_AUDIO_EXTS = {'.mp3', '.wav', '.ogg', '.m4a'}
    
    @staticmethod
    def _user_dir(username: str) -> str:
        safe_name = secure_filename(username)
        return get_vault_path(safe_name)

    @staticmethod
    def _ensure_dirs(user_dir: str):
        media_dir = os.path.join(user_dir, "media")
        avatars_dir = os.path.join(user_dir, "avatars")
        os.makedirs(media_dir, exist_ok=True)
        os.makedirs(avatars_dir, exist_ok=True)
        
        # Legacy migration
        legacy_avatar = os.path.join(user_dir, "avatar.jpg")
        if os.path.exists(legacy_avatar) and os.path.isfile(legacy_avatar):
            target = os.path.join(avatars_dir, "avatar.jpg")
            if not os.path.exists(target):
                shutil.move(legacy_avatar, target)
            else:
                try: os.remove(legacy_avatar)
                except: pass
                
        return media_dir, avatars_dir

    @staticmethod
    def resolve_avatar(username: str) -> dict:
        import urllib.parse
        
        safe_name = secure_filename(username)
        u_dir = UserMediaManager._user_dir(safe_name)
        default_avatar = {"url": "/assets/Hecos_Logo_NBG.png", "type": "image"}
        
        if not os.path.isdir(u_dir):
            return default_avatar
            
        UserMediaManager._ensure_dirs(u_dir)
        avatars_dir = os.path.join(u_dir, "avatars")
        if not os.path.isdir(avatars_dir):
            return default_avatar
            
        try:
            for f in sorted(os.listdir(avatars_dir)):
                ext = os.path.splitext(f)[1].lower()
                is_img = ext in UserMediaManager.ALLOWED_IMAGE_EXTS
                is_vid = ext in UserMediaManager.ALLOWED_VIDEO_EXTS
                
                if is_img or is_vid:
                    # Serve directly via user avatar API which we'll update to handle media/avatars
                    rel_path = f"/hecos/api/users/{urllib.parse.quote(safe_name)}/avatars/{urllib.parse.quote(f)}"
                    return {
                        "url": rel_path,
                        "type": "video" if is_vid else "image"
                    }
        except Exception:
            pass
            
        return default_avatar

    @staticmethod
    def list_media(username: str) -> list:
        import urllib.parse
        
        u_dir = UserMediaManager._user_dir(username)
        media_dir, avatars_dir = UserMediaManager._ensure_dirs(u_dir)
        
        current_avatar_filename = None
        try:
            for f in sorted(os.listdir(avatars_dir)):
                ext = os.path.splitext(f)[1].lower()
                if ext in UserMediaManager.ALLOWED_IMAGE_EXTS or ext in UserMediaManager.ALLOWED_VIDEO_EXTS:
                    current_avatar_filename = f
                    break
        except Exception:
            pass

        items = []
        safe_name = secure_filename(username)
        
        try:
            for f in os.listdir(media_dir):
                file_path = os.path.join(media_dir, f)
                if not os.path.isfile(file_path):
                    continue
                    
                ext = os.path.splitext(f)[1].lower()
                media_type = "other"
                if ext in UserMediaManager.ALLOWED_IMAGE_EXTS:
                    media_type = "image"
                elif ext in UserMediaManager.ALLOWED_VIDEO_EXTS:
                    media_type = "video"
                elif ext in UserMediaManager.ALLOWED_AUDIO_EXTS:
                    media_type = "audio"
                    
                try:
                    stat = os.stat(file_path)
                    size = stat.st_size
                    mtime = stat.st_mtime
                except Exception:
                    size = 0
                    mtime = 0
                    
                rel_url = f"/hecos/api/users/{urllib.parse.quote(safe_name)}/media/{urllib.parse.quote(f)}"
                
                items.append({
                    "name": f,
                    "url": rel_url,
                    "type": media_type,
                    "size": size,
                    "mtime": mtime,
                    "is_avatar": (f == current_avatar_filename)
                })
                
            items.sort(key=lambda x: x["mtime"], reverse=True)
            return items
        except Exception as e:
            return []

    @staticmethod
    def upload_media(username: str, file_obj) -> dict:
        u_dir = UserMediaManager._user_dir(username)
        media_dir, _ = UserMediaManager._ensure_dirs(u_dir)
        
        filename = secure_filename(file_obj.filename)
        if not filename:
            raise ValueError("Invalid filename")
            
        save_path = os.path.join(media_dir, filename)
        file_obj.save(save_path)
        
        ext = os.path.splitext(filename)[1].lower()
        mtype = "other"
        if ext in UserMediaManager.ALLOWED_IMAGE_EXTS: mtype = "image"
        elif ext in UserMediaManager.ALLOWED_VIDEO_EXTS: mtype = "video"
        elif ext in UserMediaManager.ALLOWED_AUDIO_EXTS: mtype = "audio"
        
        import urllib.parse
        safe_name = secure_filename(username)
        rel_url = f"/hecos/api/users/{urllib.parse.quote(safe_name)}/media/{urllib.parse.quote(filename)}"
        
        return {
            "name": filename,
            "url": rel_url,
            "type": mtype,
            "size": os.path.getsize(save_path),
            "mtime": os.path.getmtime(save_path)
        }

    @staticmethod
    def delete_media(username: str, filenames: list) -> int:
        u_dir = UserMediaManager._user_dir(username)
        media_dir, _ = UserMediaManager._ensure_dirs(u_dir)
        
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
    def rename_media(username: str, old_name: str, new_name: str) -> dict:
        u_dir = UserMediaManager._user_dir(username)
        media_dir, _ = UserMediaManager._ensure_dirs(u_dir)
        
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
        safe_name = secure_filename(username)
        rel_url = f"/hecos/api/users/{urllib.parse.quote(safe_name)}/media/{urllib.parse.quote(safe_new)}"
        
        return {
            "name": safe_new,
            "url": rel_url
        }

    @staticmethod
    def set_avatar(username: str, filename: str) -> dict:
        u_dir = UserMediaManager._user_dir(username)
        media_dir, avatars_dir = UserMediaManager._ensure_dirs(u_dir)
        
        safe_filename = secure_filename(filename)
        if not safe_filename:
            raise ValueError("Invalid filename")
            
        source_path = os.path.join(media_dir, safe_filename)
        if not os.path.exists(source_path):
            direct_avatar_path = os.path.join(avatars_dir, safe_filename)
            if not os.path.exists(direct_avatar_path):
                raise FileNotFoundError(f"File {safe_filename} not found in media")
            source_path = direct_avatar_path
            
        try:
            for f in os.listdir(avatars_dir):
                old_avatar_path = os.path.join(avatars_dir, f)
                if os.path.isfile(old_avatar_path):
                    media_backup_path = os.path.join(media_dir, f)
                    if not os.path.exists(media_backup_path) and old_avatar_path != source_path:
                        shutil.copy2(old_avatar_path, media_backup_path)
                    
                    if old_avatar_path != source_path:
                        os.remove(old_avatar_path)
        except Exception:
            pass 
            
        target_path = os.path.join(avatars_dir, safe_filename)
        if source_path != target_path:
            shutil.copy2(source_path, target_path)
            
        return UserMediaManager.resolve_avatar(username)
