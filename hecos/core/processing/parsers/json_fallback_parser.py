import json
import time
from hecos.core.logging import logger

class JsonFallbackParser:
    """
    Parses fallback JSON outputs from models (e.g. Ollama models that fail to use 
    native tool calls and return raw JSON text instead).
    """
    
    @staticmethod
    def parse(base_text: str, tags_found: list, think_block: str | None) -> tuple[str, str | None]:
        """
        Parses the JSON text, extracts tools into tags_found (mutating the list),
        and returns the clean text and any updated think block.
        """
        try:
            raw_stripped = base_text.strip()
            if not (raw_stripped.startswith("{") and raw_stripped.endswith("}")):
                return base_text, think_block
                
            parsed_json = json.loads(raw_stripped)
            if not isinstance(parsed_json, dict):
                return base_text, think_block
                
            # 1. Handle tool/function invocation format
            if "function" in parsed_json and isinstance(parsed_json["function"], dict):
                f_obj = parsed_json["function"]
                f_name = f_obj.get("name", "")
                f_args_raw = f_obj.get("parameters", f_obj.get("arguments", {}))
                if "__" in f_name:
                    t_tag, t_method = f_name.split("__", 1)
                    tags_found.append((t_tag.lower(), f_args_raw, "function_call", t_method, f"call_{int(time.time())}"))
                    logger.info(f"[PROCESSOR] Intercepted raw JSON function call: {f_name}")
                    return "", think_block
                    
            # 2. Handle text response with 'thought' format
            elif "response" in parsed_json or "thought" in parsed_json:
                resp = parsed_json.get("response")
                thought_val = parsed_json.get("thought", None)
                
                if thought_val is not None:
                    if isinstance(thought_val, str):
                        think_block = thought_val.strip()
                    elif isinstance(thought_val, dict):
                        think_block = thought_val.get("reasoning", "").strip() or str(thought_val).strip()
                    
                if isinstance(resp, dict) and "text" in resp:
                    base_text = resp["text"]
                elif isinstance(resp, str):
                    base_text = resp
                elif resp is not None:
                    base_text = str(resp)
                elif thought_val is not None and not resp:
                    base_text = "" # Thought only, no response
                    
                logger.info("[PROCESSOR] Intercepted raw JSON thought/response block.")
                
            # 3. Handle plain {"text": "...", ...} format
            elif "text" in parsed_json and isinstance(parsed_json["text"], str) and len(parsed_json) <= 5:
                base_text = parsed_json["text"]
                logger.info("[PROCESSOR] Intercepted raw JSON {text:...} response block.")

            # 4. Handle list of tool calls
            elif "tool_calls" in parsed_json and isinstance(parsed_json["tool_calls"], list):
                for tc in parsed_json["tool_calls"]:
                    f_obj = tc.get("function", {})
                    f_name = f_obj.get("name", "")
                    f_args_raw = f_obj.get("arguments", {})
                    if "__" in f_name:
                        t_tag, t_method = f_name.split("__", 1)
                        tags_found.append((t_tag.lower(), f_args_raw, "function_call", t_method, tc.get("id", f"call_{int(time.time())}")))
                        base_text = ""
                if tags_found:
                    logger.info(f"[PROCESSOR] Intercepted raw JSON tool_calls list.")
                    
        except Exception as e:
            # Silently fail if JSON is malformed, just return the raw text
            pass
            
        return base_text, think_block
