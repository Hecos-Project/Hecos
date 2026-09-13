import re

class ReasoningParser:
    """
    Isolates the complex regex logic used to extract the <think> blocks
    from the LLM output, handling edge cases like missing tags or cutoffs.
    """
    
    @staticmethod
    def extract_reasoning(base_text: str) -> tuple[str, str | None]:
        """
        Parses the text and extracts the reasoning block if present.
        Returns: (clean_base_text, think_block_or_none)
        """
        think_block = None
        
        if not isinstance(base_text, str) or not base_text:
            return base_text, think_block
            
        # Pattern A: properly tagged <think>...</think>
        think_match = re.search(r'<think>(.*?)</think>', base_text, re.DOTALL | re.IGNORECASE)
        if think_match:
            think_block = think_match.group(1).strip()
            base_text = re.sub(r'<think>.*?</think>', '', base_text, flags=re.DOTALL | re.IGNORECASE).strip()
            base_text = re.sub(r'<think>.*$', '', base_text, flags=re.DOTALL | re.IGNORECASE).strip()
            return base_text, think_block

        # Pattern B: bare </think> — everything before it is the reasoning block
        if '</think>' in base_text:
            parts = base_text.split('</think>', 1)
            think_block = parts[0].strip()
            base_text = parts[1].strip() if len(parts) > 1 else ''
            return base_text, think_block

        # Pattern C: unclosed <think> tag — model got cut off by max_tokens mid-thought
        if '<think>' in base_text.lower():
            parts = re.split(r'<think>', base_text, maxsplit=1, flags=re.IGNORECASE)
            think_block = parts[1].strip() if len(parts) > 1 else ''
            base_text = parts[0].strip()
            return base_text, think_block
            
        return base_text, think_block
