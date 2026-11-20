"""
hecos/core/commands/builtins/doc_commands.py
Built-in slash commands for local document discovery, preview, and HTML editing:
/show, /docs
"""

import os
import re
import urllib.parse
from typing import Any, Dict, List


def _cmd_show(raw_args_str: str = "", **kwargs) -> str:
    """
    Show a local file as a rich card in chat (with Visual Editor button for HTML files).
    Usage: /show <percorso_file>  or  /show docs  (to list all documents)
    """
    path = raw_args_str.strip().strip('"').strip("'")

    if not path:
        return (
            "**Uso:** `/show <percorso o nome file>`\n"
            "Esempi:\n"
            "- `/show C:\\Hecos\\hecos\\media\\documents\\mio_doc.html`\n"
            "- `/show mio_doc.html` (cerca in media/documents)\n"
            "- `/docs` per vedere tutti i documenti disponibili"
        )

    # If not an absolute path, look in media/documents
    if not os.path.isabs(path):
        hecos_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        docs_dir = os.path.join(hecos_dir, "media", "documents")
        candidates = [path, path + ".html", path + ".pdf"]
        resolved = None
        for c in candidates:
            full = os.path.join(docs_dir, c)
            if os.path.exists(full):
                resolved = full
                break
        # Fuzzy search
        if not resolved and os.path.isdir(docs_dir):
            for f in os.listdir(docs_dir):
                if path.lower() in f.lower():
                    resolved = os.path.join(docs_dir, f)
                    break
        if not resolved:
            return f"❌ File non trovato: `{path}`. Prova con il percorso completo."
        path = resolved
    elif not os.path.exists(path):
        return f"❌ File non trovato: `{path}`"

    fname = os.path.basename(path)
    url_path = path.replace('\\', '/')
    safe_path = urllib.parse.quote(url_path)
    return f"[{fname}](/api/local_file?path={safe_path})\n*{path}*"


def _cmd_docs_list(raw_args_str: str = "", **kwargs) -> str:
    """List all documents in media/documents with clickable links."""
    hecos_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    docs_dir = os.path.join(hecos_dir, "media", "documents")

    if not os.path.isdir(docs_dir):
        return f"❌ Cartella documenti non trovata: `{docs_dir}`"

    search = raw_args_str.strip().lower()
    files = sorted([
        f for f in os.listdir(docs_dir)
        if os.path.isfile(os.path.join(docs_dir, f))
        and (not search or search in f.lower())
    ])

    if not files:
        return "📂 Nessun documento trovato" + (f" per '{search}'" if search else "") + f" in `{docs_dir}`"

    lines = [f"## 📁 Documenti ({len(files)} file)\n"]
    for f in files:
        full_path = os.path.join(docs_dir, f)
        url_path = full_path.replace('\\', '/')
        safe_path = urllib.parse.quote(url_path)
        size_bytes = os.path.getsize(full_path)
        size_str = f"{size_bytes / 1024:.1f} KB" if size_bytes > 1024 else f"{size_bytes} B"

        # For HTML files, include image count
        extra = ""
        if f.endswith(".html"):
            try:
                with open(full_path, "r", encoding="utf-8", errors="replace") as fh:
                    html = fh.read()
                img_count = len(re.findall(r'<img\s', html, re.IGNORECASE))
                extra = f" — {img_count} immagini"
            except Exception:
                pass

        lines.append(f"[{f}](/api/local_file?path={safe_path}) ({size_str}){extra}")

    lines.append("\n*Clicca su un file per aprirlo o modificarlo.*")
    return "\n".join(lines)


DOC_COMMANDS: List[Dict[str, Any]] = [
    {
        "id": "show",
        "aliases": ["/show", "/file", "/anteprima"],
        "description": "Mostra l'anteprima di un file locale in chat (con Visual Editor per HTML)",
        "usage": "/show <percorso_o_nome_file>",
        "example": "/show mio_documento.html",
        "icon": "📄",
        "category": "CORE",
        "requires_auth": "any",
        "requires_args": True,
        "save_to_memory": False,
        "_handler": _cmd_show,
    },
    {
        "id": "docs",
        "aliases": ["/docs", "/documenti", "/docs_list"],
        "description": "Elenca tutti i documenti in media/documents con link cliccabili",
        "usage": "/docs [filtro]",
        "example": "/docs rivista",
        "icon": "📁",
        "category": "CORE",
        "requires_auth": "any",
        "requires_args": False,
        "save_to_memory": False,
        "_handler": _cmd_docs_list,
    },
]

