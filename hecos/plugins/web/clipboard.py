def get_clipboard() -> str:
    """
    Returns the current text from the system clipboard.
    Use this when the user says 'use what I just copied' or 'fix this code'.
    """
    try:
        import pyperclip
        text = pyperclip.paste()
        if not text or not text.strip():
            return "[WEB] Clipboard is empty."
        return f"📋 Clipboard content:\n\n{text[:3000]}"
    except ImportError:
        return "[WEB] Clipboard requires pyperclip: pip install pyperclip"
    except Exception as e:
        return f"[WEB] Clipboard read error: {e}"


def set_clipboard(text: str) -> str:
    """
    Copies the given text to the system clipboard.
    :param text: The text to copy to clipboard.
    """
    try:
        import pyperclip
        pyperclip.copy(text)
        preview = text[:80].replace("\n", " ")
        return f"📋 Copied to clipboard: \"{preview}{'...' if len(text) > 80 else ''}\""
    except ImportError:
        return "[WEB] Clipboard requires pyperclip: pip install pyperclip"
    except Exception as e:
        return f"[WEB] Clipboard write error: {e}"
