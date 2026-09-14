import os
import re
import base64
import mimetypes
from hecos.core.logging import logger

class MediaInterceptor:
    """
    Handles intercepting rich media from tool results.
    - Appends UI-rendered images to the final text response.
    - Intercepts WEBCAM short circuits.
    - Base64-encodes local images on disk for Vision AI feedback.
    """
    
    @staticmethod
    def append_ui_media_to_text(extracted_text: str, accumulated_tool_results: list) -> str:
        """
        Parses tool results to find [[IMG:]] tags or raw paths (like /snapshots) 
        and appends them as Markdown to the extracted_text for the Chat UI.
        """
        for res in accumulated_tool_results:
            out = res.get("output", "")
            if out and isinstance(out, str):
                # 1. Check for explicit [[IMG:...]] from ImageGen
                img_tags = re.findall(r'\[\[IMG:([^\]]+)\]\]', out)
                for idx, tag in enumerate(img_tags):
                    # Append directly as expected by chat UI
                    if f"[[IMG:{tag}]]" not in extracted_text:
                        extracted_text += f"\n\n[[IMG:{tag}]]"
                        
                # 2. Check for raw paths (e.g. from WEBCAM module which saves to /snapshots)
                potential_paths = re.findall(r'((?:[A-Za-z]:[\\/])?[\w\.\-\\\/]+\.(?:jpg|jpeg|png))', out, re.IGNORECASE)
                for path in potential_paths:
                    fname = os.path.basename(path)
                    if fname in img_tags:
                        continue  # Covered above
                    
                    # Convert local path to web URL for WEBCAM
                    img_url = f"/snapshots/{fname}"
                    if img_url not in extracted_text:
                        extracted_text += f"\n\n![Snapshot]({img_url})"

                # 3. Append other raw tool outputs so they are saved to history
                if img_tags:
                    continue
                # Skip [EXECUTOR] confirmations that just echo a path
                if isinstance(out, str) and out.strip().startswith("[EXECUTOR]"):
                    continue
                # Skip if the output is just a bare path already present in the AI's response
                out_stripped = out.strip()
                if re.fullmatch(r'[A-Za-z]:[\\/][^\n]+', out_stripped):
                    if out_stripped.replace('\\', '/') in extracted_text.replace('\\', '/'):
                        continue
                
                # Check for Document Maker specific outputs
                if "HTML:" in out_stripped or "PDF:" in out_stripped:
                    if "HTML:" in extracted_text and "PDF:" in extracted_text:
                        continue
                        
                # Only append if it's not already somewhere in the text to avoid duplication
                if out_stripped not in extracted_text:
                    extracted_text += f"\n\n{out}"
                    
        return extracted_text

    @staticmethod
    def check_webcam_short_circuit(output_text: str) -> bool:
        """
        Returns True if the WEBCAM short circuit token was intercepted.
        """
        CAMERA_TOKEN = "[CAMERA_SNAPSHOT_REQUEST]"
        if output_text and CAMERA_TOKEN in str(output_text).strip():
            return True
        return False

    @staticmethod
    def load_vision_images(output_text: str, images_list: list, agent_emit) -> list:
        """
        Intercepts image paths from the tool output, base64 encodes them, 
        and appends them to the images_list to feed back to Vision AI.
        """
        if output_text and isinstance(output_text, str):
            potential_paths = re.findall(r'((?:[A-Za-z]:[\\/])?[\w\.\-\\\/]+\.(?:jpg|jpeg|png))', output_text, re.IGNORECASE)
            for path in potential_paths:
                if os.path.exists(path):
                    try:
                        with open(path, "rb") as f:
                            img_bytes = f.read()
                        if images_list is None:
                            images_list = []
                        mime, _ = mimetypes.guess_type(path)
                        images_list.append({
                            "data_b64": base64.b64encode(img_bytes).decode("utf-8"),
                            "mime_type": mime or "image/jpeg",
                            "name": os.path.basename(path)
                        })
                        agent_emit(f"Intercepted image for Vision-AI: {os.path.basename(path)}", level="info")
                        logger.info(f"[AGENT] Vision-AI: loaded {os.path.basename(path)} ({len(img_bytes)} bytes)")
                    except Exception as e:
                        logger.debug(f"[MediaInterceptor] Failed to load intercepted image path {path}: {e}")
        return images_list
