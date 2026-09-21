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
            for cmd in slash_matches:
                tags_found.append(("direct_command", cmd.strip(), "slash", None))
                
            # Fallback: some LLMs might hallucinate HTML tags like <img description>
            html_img_matches = re.findall(r'<img\s+([^>]+)>', base_text, flags=re.IGNORECASE)
            for img_desc in html_img_matches:
                tags_found.append(("direct_command", f"/img {img_desc.strip()}", "slash", None))
