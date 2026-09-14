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
