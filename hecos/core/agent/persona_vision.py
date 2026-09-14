import os
from hecos.core.logging import logger

class PersonaVision:
    """
    Handles extracting the visual description of the current AI identity 
    from the persona.yaml file or using hardcoded fallbacks.
    """
    
    @staticmethod
    def get_visual_description(config):
        """Attempts to extract a visual description of the current AI identity from YAML or fallback."""
        try:
            # 1. Identify the active personality file
            active_p = config.get('ai', {}).get('active_personality', 'Hecos_System_Soul').replace('.yaml', '')
            
            # 2. Try to load the YAML file
            root_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
            p_path = os.path.join(root_dir, "personas", active_p, "persona.yaml")
            
            # If still not found, try one level up (workspace root) just in case
            if not os.path.exists(p_path):
                p_path = os.path.join(root_dir, "..", "hecos", "personas", active_p, "persona.yaml")
            
            if os.path.exists(p_path):
                import yaml
                with open(p_path, 'r', encoding='utf-8') as f:
                    p_data = yaml.safe_load(f) or {}
                
                # Check for the new dynamic field or fallback to old
                v_desc = p_data.get("visual_description")
                if not v_desc and "anatomy" in p_data:
                    anatomy = p_data["anatomy"]
                    v_desc = f"{anatomy.get('sex', 'Person')}, {anatomy.get('body_type', 'average')} body, {anatomy.get('hair_color', 'dark')} hair, {anatomy.get('eye_color', 'dark')} eyes."
                    
                if v_desc:
                    return v_desc

            # 3. Hard-coded fallback for legacy or missing fields
            name = active_p.lower()
            if "urania" in name:
                return "a beautiful female cybernetic android with bright turquoise neon-blue hair, bright blue eyes, wearing white and pink-glowing circuitry armor"
            elif "motoko" in name:
                return "Major Motoko Kusanagi from Ghost in the Shell, purple hair, tactical suit"
            elif "atlas" in name:
                return "a handsome, professional and futuristic man with a sharp jawline"
            
            # Generic fallbacks
            if "woman" in name or "femmina" in name:
                return "a beautiful woman"
            elif "man" in name or "maschio" in name:
                return "a handsome man"
                
            return "a futuristic person"
        except Exception as e:
            logger.debug(f"[PersonaVision] Failed to load dynamic visual description: {e}")
            return "a digital entity"
