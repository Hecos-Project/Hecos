import re

class LegacyTagParser:
    """
    Extracts legacy bracket tags (e.g., [TOOL:ACTION] or [TOOL]) from text.
    """
    
    @staticmethod
    def parse(base_text: str, raw_response: str, tags_found: list) -> None:
        """
        Extracts tags and mutates the tags_found list.
        """
        # Match standard [TOOL:ACTION]
        matches_standard = re.findall(r'\[(\w+):(.*?)\]', base_text)
        for tag, action in matches_standard:
            tags_found.append((tag.lower(), action.strip(), "standard", None))
        
        # Match simple [TOOL]
        if isinstance(raw_response, str):
            matches_simple = re.findall(r'\[(\w+)\]', raw_response)
            for tag in matches_simple:
                if not any(t[0] == tag.lower() for t in tags_found):
                    tags_found.append((tag.lower(), "", "simple", None))

        # Match Slash Commands (e.g., /img, /cmd) emitted by the LLM
        if isinstance(base_text, str):
            slash_matches = re.findall(r'^\s*(/[a-zA-Z0-9_]+.*?)(?:\n|$)', base_text, flags=re.MULTILINE)
            seen_cmds = set()
            img_cmd_count = 0
            for cmd in slash_matches:
                cmd_clean = cmd.strip()
                if not cmd_clean or cmd_clean in seen_cmds:
                    continue
                seen_cmds.add(cmd_clean)
                
                # Check for image commands (/img, /image, /photo, /foto)
                is_img = cmd_clean.lower().startswith(("/img", "/image", "/photo", "/foto"))
                if is_img:
                    img_cmd_count += 1
                    # Hard cap per single LLM response: at most 2 images in one text
                    if img_cmd_count > 2:
                        continue
                tags_found.append(("direct_command", cmd_clean, "slash", None))
                
            # Fallback: some LLMs might hallucinate HTML tags like <img description>
            if img_cmd_count == 0:
                html_img_matches = re.findall(r'<img\s+([^>]+)>', base_text, flags=re.IGNORECASE)
                for img_desc in html_img_matches:
                    cmd_clean = f"/img {img_desc.strip()}"
                    if cmd_clean not in seen_cmds:
                        seen_cmds.add(cmd_clean)
                        tags_found.append(("direct_command", cmd_clean, "slash", None))
                        break  # Cap at 1 fallback image
