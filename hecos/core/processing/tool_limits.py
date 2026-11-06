"""
hecos/core/processing/tool_limits.py
Manages NLP parsing for image quantities and enforces per-turn generation limits.
"""

import re
from typing import Any, Dict, List, Optional
from hecos.core.logging import logger

NUMBER_WORDS = {
    'un': 1, 'uno': 1, 'una': 1, 'due': 2, 'tre': 3, 'quattro': 4, 'cinque': 5,
    'sei': 6, 'sette': 7, 'otto': 8, 'nove': 9, 'dieci': 10, 'undici': 11,
    'dodici': 12, 'tredici': 13, 'quattordici': 14, 'quindici': 15, 'sedici': 16,
    'diciassette': 17, 'diciotto': 18, 'diciannove': 19, 'venti': 20,
    'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6,
    'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10, 'eleven': 11, 'twelve': 12,
    'fifteen': 15, 'twenty': 20,
}

_WORD_OR_DIGIT_PATTERN = r'(\d+|' + '|'.join(NUMBER_WORDS.keys()) + r')'


def _parse_num_val(val: Optional[str]) -> Optional[int]:
    if not val:
        return None
    v = val.strip().lower()
    if v.isdigit():
        return int(v)
    return NUMBER_WORDS.get(v)


def get_requested_image_limit(user_text: str) -> int:
    """
    Parses user_text to check how many images/photos the user asked for.
    Supports numbers (digits or Italian/English words), parenthesized counts,
    and document requests with illustrations.
    Defaults to 1, with a safe ceiling of 20.
    """
    if not user_text or not isinstance(user_text, str):
        return 1
    t = user_text.lower()

    counts = []

    # 1. Explicit parentheses with number or word: e.g. (6), ( 6 ), (sei), (six)
    m_paren = re.search(r'\(\s*' + _WORD_OR_DIGIT_PATTERN + r'\s*(?:foto|fotografie|immagini|photos?|images?|pics?)?\s*\)', t)
    if m_paren:
        n = _parse_num_val(m_paren.group(1))
        if n and n >= 1:
            counts.append(n)

    # 2. Pattern: <verb> [ne/mi/ci] <number> e.g. 'devi farne 6', 'fanne 6', 'fammi 6', 'generane 6', 'generi 6', 'creane 6'
    m_verb = re.findall(
        r'\b(?:fai|fammi|fanne|farne|fare|faccene|facci|crea|creami|creane|creare|genera|generami|generane|generi|generare|manda|mandami|mandane|mandare|invia|inviami|inviane|mostra|mostrami|mostrane|produci|producimi|producine|disegna|disegnami|disegnane|scatta|scattami|scattane|voglio|vorrei|desidero|metti|inserisci|includi|allega|aggiungi|prepara|preparami|make|generate|create|produce|draw|take|want)\s+(?:almeno\s+|circa\s+)?' + _WORD_OR_DIGIT_PATTERN + r'\b',
        t
    )
    for match in m_verb:
        n = _parse_num_val(match)
        if n:
            counts.append(n)

    # 3. Pattern: <number> [di] <foto/immagini/images/photos>
    m_noun = re.findall(
        r'\b' + _WORD_OR_DIGIT_PATTERN + r'\s*(?:di\s+)?(?:foto|fotografie|immagini|immagine|photos?|pictures?|images?|pics?|illustrazioni|scatti)\b',
        t
    )
    for match in m_noun:
        n = _parse_num_val(match)
        if n:
            counts.append(n)

    # 4. Pattern: <foto/immagini> [:] [(] <number>
    m_after = re.findall(
        r'\b(?:foto|fotografie|immagini|immagine|photos?|pictures?|images?|pics?)\s*(?:sono|:|per\s+un\s+totale\s+di)?\s*' + _WORD_OR_DIGIT_PATTERN + r'\b',
        t
    )
    for match in m_after:
        n = _parse_num_val(match)
        if n:
            counts.append(n)

    if counts:
        return min(max(1, max(counts)), 20)

    # 5. If user asked for an illustrated document without explicit count, allow up to 6
    has_doc_intent = bool(re.search(r'\b(?:documento|doc|pdf|html|scheda)\b', t))
    has_img_intent = bool(re.search(r'\b(?:foto|immagini|illustrazioni|photos?|images?|illustrato|illustrata)\b', t))
    if has_doc_intent and has_img_intent:
        return 6

    return 1


def is_image_tool_call(
    original_tag: str,
    action_or_args: Any,
    module_to_call: str,
    method_name: Optional[str],
) -> bool:
    """Returns True if the requested tool invocation corresponds to image generation."""
    if original_tag == "direct_command" and isinstance(action_or_args, str):
        cmd_lower = action_or_args.strip().lower()
        if cmd_lower.startswith(("/img", "/image", "/photo", "/foto")):
            return True
    elif module_to_call.upper() == "IMAGE_GEN" and (method_name in ("generate_image", "slash_img") or not method_name):
        return True
    return False


def build_image_limit_exceeded_result(
    call_id: str,
    original_tag: str,
    image_limit: int,
    sm: Any = None,
) -> Dict[str, Any]:
    """Generates the tool output dict when the image generation turn limit has been exceeded."""
    tag_name = "SLASH_COMMAND" if original_tag == "direct_command" else "IMAGE_GEN"
    if sm and getattr(sm, "image_gen_failed", False):
        logger.warning("[PROCESSOR] Skipping duplicate image call after fatal backend/plugin error.")
        return {
            "id": call_id,
            "output": (
                "\n\n[IMAGE_GEN: Image generation failed due to a backend technical error or because the plugin is not installed. "
                "Explicitly inform the user that the image could not be generated and report the exact error notice enclosed in [[IGEN_ALERT]] without retrying or inventing fake URLs.]"
            ),
            "tag": tag_name,
        }

    logger.warning(f"[PROCESSOR] Image generation limit reached ({image_limit}). Skipping duplicate/extra generation.")
    return {
        "id": call_id,
        "output": f"[IMAGE_GEN: Limit of {image_limit} image(s) per turn already reached. The requested image has already been generated successfully. Conclude your response now.]",
        "tag": tag_name,
    }


def update_image_turn_counters(
    output_val: Any,
    is_image_call: bool,
    image_limit: int,
    images_already_done: int,
    sm: Any = None,
) -> int:
    """Updates image turn counters on success or short-circuits retries on fatal backend/plugin errors."""
    if not is_image_call:
        return images_already_done
    out_str = str(output_val or "")
    if "[[IMG:" in out_str or "gen_" in out_str:
        images_already_done += 1
        if sm:
            sm.total_images_in_turn = images_already_done
    elif (
        "[[IGEN_ALERT]]" in out_str
        or "FATAL_BACKEND_ERROR" in out_str
        or out_str.startswith("Error:")
        or "[IMAGE_GEN_ERROR]" in out_str
    ):
        logger.warning("[PROCESSOR] Image generation returned a backend/plugin error — blocking further retries in this turn.")
        images_already_done = image_limit
        if sm:
            sm.total_images_in_turn = image_limit
            sm.image_gen_failed = True
    return images_already_done

