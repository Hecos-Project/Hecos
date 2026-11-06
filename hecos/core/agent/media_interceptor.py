import os
import re
import base64
import mimetypes
from hecos.core.logging import logger

class MediaInterceptor:
    """
    Handles intercepting rich media from tool results.
    - Appends UI-rendered images to the final text response.
    - Propagates [[IGEN_ALERT]] diagnostic banners to the final text response.
    - Intercepts WEBCAM short circuits.
    - Base64-encodes local images on disk for Vision AI feedback.
    """
    
    @staticmethod
    def append_ui_media_to_text(extracted_text: str, accumulated_tool_results: list) -> str:
        """
        Parses tool results to find [[IMG:]] tags, [[IGEN_ALERT]] blocks,
        document paths (HTML:/PDF:), search cards ([[HSEARCH:]] / [[HMEDIA:]]),
        or webcam snapshots (/snapshots) and appends them to the extracted_text for the Chat UI.
        """
        for res in accumulated_tool_results:
            out = res.get("output", "")
            tag_name = str(res.get("tag", "")).upper()
            if out and isinstance(out, str):
                # 1. Check for explicit [[IMG:...]] from ImageGen
                img_tags = re.findall(r'\[\[IMG:([^\]]+)\]\]', out)
                for tag in img_tags:
                    if f"[[IMG:{tag}]]" not in extracted_text:
                        extracted_text += f"\n\n[[IMG:{tag}]]"

                # 1b. Check for [[IGEN_ALERT]]...[[/IGEN_ALERT]] diagnostic notices
                igen_alerts = re.findall(r'\[\[IGEN_ALERT\]\](.*?)\[\[/IGEN_ALERT\]\]', out, flags=re.DOTALL)
                for alert_body in igen_alerts:
                    clean_alert = alert_body.strip()
                    wrapped = f"[[IGEN_ALERT]]{clean_alert}[[/IGEN_ALERT]]"
                    if clean_alert and wrapped not in extracted_text and clean_alert not in extracted_text:
                        extracted_text += f"\n\n{wrapped}"
                        
                # 2. Check for raw paths from WEBCAM module (which saves to /snapshots)
                if tag_name == "WEBCAM" or "snapshots" in out.lower():
                    potential_paths = re.findall(r'((?:[A-Za-z]:[\\/])?[\w\.\-\\\/]+\.(?:jpg|jpeg|png))', out, re.IGNORECASE)
                    for path in potential_paths:
                        fname = os.path.basename(path)
                        if fname in img_tags:
                            continue  # Covered above
                        if tag_name != "WEBCAM" and "snapshots" not in path.lower():
                            continue
                        
                        # Convert local path to web URL for WEBCAM
                        img_url = f"/snapshots/{fname}"
                        if img_url not in extracted_text:
                            extracted_text += f"\n\n![Snapshot]({img_url})"

                # 3. Handle Document Maker specific outputs (HTML / PDF paths)
                doc_matches = re.findall(
                    r'(?:^(?:HTML|PDF):\s*|Document modified successfully:\s*|PDF regenerated:\s*)([A-Za-z]:[\\/][^\r\n]+?\.(?:html?|pdf))\b',
                    out,
                    flags=re.MULTILINE | re.IGNORECASE
                )
                for doc_path in doc_matches:
                    doc_path_clean = doc_path.strip()
                    if doc_path_clean and doc_path_clean not in extracted_text:
                        prefix_type = "PDF" if doc_path_clean.lower().endswith(".pdf") else "HTML"
                        extracted_text += f"\n\n{prefix_type}: {doc_path_clean}"

                # 4. Handle Deep Search [[HSEARCH:...]] and [[HMEDIA:...]] session tokens
                hsearch_tags = re.findall(r'\[\[HSEARCH:([a-zA-Z0-9_-]+)\]\]', out)
                for sid in hsearch_tags:
                    if f"[[HSEARCH:{sid}]]" not in extracted_text:
                        extracted_text += f"\n\n[[HSEARCH:{sid}]]"
                hmedia_tags = re.findall(r'\[\[HMEDIA:([a-zA-Z0-9_-]+)\]\]', out)
                for sid in hmedia_tags:
                    if f"[[HMEDIA:{sid}]]" not in extracted_text and f"[[HSEARCH:{sid}]]" not in extracted_text:
                        extracted_text += f"\n\n[[HMEDIA:{sid}]]"
                    
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
                        from hecos.core.agent.traces import AgentTracer
                        from hecos.core.agent.trace_labeler import tr
                        v_step = AgentTracer.start_step(
                            kind="vision",
                            label=tr("Acquisizione immagine per analisi Vision", "Loading image for Vision analysis"),
                            args_preview=os.path.basename(path),
                            icon="fa-eye",
                            level="info",
                            module_name="Vision AI",
                        )
                        AgentTracer.finish_step(
                            v_step,
                            status="ok",
                            result_preview=f"{os.path.basename(path)} ({len(img_bytes) // 1024} KB)",
                        )
                        logger.info(f"[AGENT] Vision-AI: loaded {os.path.basename(path)} ({len(img_bytes)} bytes)")
                    except Exception as e:
                        logger.debug(f"[MediaInterceptor] Failed to load intercepted image path {path}: {e}")
        return images_list

    @staticmethod
    def load_search_vision_images(output_text: str, images_list: list, agent_emit) -> list:
        """
        Intercepts [[HSEARCH:...]] or [[HMEDIA:...]] tokens from tool output,
        fetches search thumbnails via the unified vision subsystem, and appends
        them to images_list for visual verification.
        """
        if output_text and isinstance(output_text, str):
            sids = re.findall(r'\[\[(?:HSEARCH|HMEDIA):([a-zA-Z0-9_-]+)\]\]', output_text)
            if sids:
                try:
                    from hecos.modules.web_ui.vision import extract_search_session_images
                    from hecos.core.agent.traces import AgentTracer
                    from hecos.core.agent.trace_labeler import tr
                    for sid in set(sids):
                        thumbs = extract_search_session_images(sid)
                        if thumbs:
                            if images_list is None:
                                images_list = []
                            images_list.extend(thumbs)
                            v_step = AgentTracer.start_step(
                                kind="vision",
                                label=tr("Verifica visiva risultati di ricerca", "Visual verification of search results"),
                                args_preview=tr(f"{len(thumbs)} miniature", f"{len(thumbs)} thumbnails"),
                                icon="fa-eye",
                                level="info",
                                module_name="Vision AI",
                            )
                            AgentTracer.finish_step(
                                v_step,
                                status="ok",
                                result_preview=tr(
                                    f"{len(thumbs)} immagini caricate per verifica",
                                    f"{len(thumbs)} thumbnails loaded for verification",
                                ),
                            )
                            logger.info(f"[AGENT] Vision: loaded {len(thumbs)} thumbnails from search session {sid}")
                except Exception as e:
                    logger.debug(f"[MediaInterceptor] Failed to extract search thumbnails: {e}")
        return images_list
