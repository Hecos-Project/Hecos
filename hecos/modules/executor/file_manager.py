import os

try:
    from hecos.core.logging import logger
    from hecos.core.agent.traces import AgentTracer
except ImportError:
    class DummyLogger:
        def debug(self, *args, **kwargs): print("[EXE_DEBUG]", *args)
        def info(self, *args, **kwargs): print("[EXE_INFO]", *args)
        def error(self, *args, **kwargs): print("[EXE_ERR]", *args)
    logger = DummyLogger()
    class DummyTracer:
        @staticmethod
        def emit_action(t, c, o): print(f"[ACTION] {t}: {c}\n{o}")
    AgentTracer = DummyTracer()

# ── Path Safety Guard ─────────────────────────────────────────────────────────
# Directories that Executor must never write to or delete from.
_FORBIDDEN_PREFIXES = (
    os.environ.get("SystemRoot", "C:\\Windows"),
    "C:\\Windows",
    "/etc", "/bin", "/sbin", "/usr/bin",
)

def _is_safe_path(path: str) -> bool:
    """Returns False if the resolved path points to a protected system directory."""
    abs_path = os.path.abspath(path)
    for forbidden in _FORBIDDEN_PREFIXES:
        if forbidden and abs_path.lower().startswith(os.path.abspath(forbidden).lower()):
            return False
    return True

# ── File Management ───────────────────────────────────────────────────────────

def read_file_tool(file_path: str, start_line: int = 1, end_line: int = -1) -> str:
    """
    Reads the contents of a file. Use start_line and end_line to limit output.
    :param file_path: Absolute path to the file to read.
    :param start_line: First line to read (1-indexed). Default: 1.
    :param end_line: Last line to read (inclusive). Use -1 for the entire file.
    """
    if not os.path.exists(file_path):
        return f"[EXECUTOR] File not found: {file_path}"
    try:
        # Robustness: The LLM often sends arguments as strings.
        s_line = int(start_line)
        e_line = int(end_line)
        
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        if e_line == -1:
            e_line = len(lines)
        chunk = "".join(lines[max(0, s_line - 1):e_line])
        res = f"--- {file_path} (lines {s_line}–{e_line}) ---\n{chunk}"
        AgentTracer.emit_action("read_file", f"Reading {file_path}", f"{len(lines)} lines total")
        return res
    except Exception as e:
        return f"[EXECUTOR] Read error: {e}"

def write_file_tool(file_path: str, content: str, mode: str = "w") -> str:
    """
    Writes or creates a file. Mode 'w' overwrites; 'a' appends.
    :param file_path: Absolute path to the file to write or create.
    :param content: The full text content to write.
    :param mode: 'w' to overwrite (default), 'a' to append.
    """
    if not _is_safe_path(file_path):
        return "[EXECUTOR] ACCESS DENIED: Writing to system paths is forbidden."
    try:
        parent = os.path.dirname(os.path.abspath(file_path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(file_path, mode, encoding="utf-8") as f:
            f.write(content)
        logger.info(f"[EXECUTOR] write_file OK: {file_path} (mode={mode})")
        res = f"[EXECUTOR] File written successfully: {file_path}"
        AgentTracer.emit_action("write_file", f"Mode: {mode} -> {file_path}", f"{len(content)} characters written")
        return res
    except Exception as e:
        return f"[EXECUTOR] Write error: {e}"

def patch_file_tool(file_path: str, old_text: str, new_text: str) -> str:
    """
    Replaces the first occurrence of old_text with new_text in a file.
    Use this for surgical edits instead of rewriting the entire file.
    Returns an error with a file preview if old_text is not found.
    :param file_path: Absolute path to the file to patch.
    :param old_text: The exact text block to find (whitespace must match exactly).
    :param new_text: The replacement text block.
    """
    if not _is_safe_path(file_path):
        return "[EXECUTOR] ACCESS DENIED: Patching system paths is forbidden."
    if not os.path.exists(file_path):
        return f"[EXECUTOR] File not found: {file_path}"
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            original = f.read()
        if old_text not in original:
            preview = original[:400].replace('\n', '↵')
            return f"[EXECUTOR] Text to replace not found. File starts with: {preview}..."
        patched = original.replace(old_text, new_text, 1)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(patched)
        logger.info(f"[EXECUTOR] patch_file OK: {file_path}")
        res = f"[EXECUTOR] File patched successfully: {file_path}"
        AgentTracer.emit_action("patch_file", f"Patching {file_path}", f"Replaced text block successfully")
        return res
    except Exception as e:
        return f"[EXECUTOR] Patch error: {e}"

def delete_file_tool(file_path: str) -> str:
    """
    Deletes a file. Cannot delete directories.
    :param file_path: Absolute path to the file to delete.
    """
    if not _is_safe_path(file_path):
        return "[EXECUTOR] ACCESS DENIED: Deleting system paths is forbidden."
    if not os.path.exists(file_path):
        return f"[EXECUTOR] File not found: {file_path}"
    if os.path.isdir(file_path):
        return "[EXECUTOR] Path is a directory. Use execute_shell_command to remove directories."
    try:
        os.remove(file_path)
        logger.info(f"[EXECUTOR] delete_file OK: {file_path}")
        res = f"[EXECUTOR] File deleted: {file_path}"
        AgentTracer.emit_action("delete_file", f"Deleting {file_path}", res)
        return res
    except Exception as e:
        return f"[EXECUTOR] Delete error: {e}"

def create_dir_tool(directory_path: str) -> str:
    """
    Creates a directory (and all intermediate parents) if it does not exist.
    :param directory_path: Absolute path to the directory to create.
    """
    if not _is_safe_path(directory_path):
        return "[EXECUTOR] ACCESS DENIED: Creating system directories is forbidden."
    try:
        os.makedirs(directory_path, exist_ok=True)
        logger.info(f"[EXECUTOR] create_dir OK: {directory_path}")
        res = f"[EXECUTOR] Directory created: {directory_path}"
        AgentTracer.emit_action("create_dir", f"mkdir {directory_path}", res)
        return res
    except Exception as e:
        return f"[EXECUTOR] Create dir error: {e}"

def list_dir_tool(directory_path: str) -> str:
    """
    Lists the files and subdirectories in a given directory.
    :param directory_path: Absolute path to the directory to list.
    """
    if not os.path.exists(directory_path):
        return f"[EXECUTOR] Directory not found: {directory_path}"
    try:
        items = os.listdir(directory_path)
        lines = [f"--- Contents of {directory_path} ({len(items)} items) ---"]
        for item in sorted(items):
            full = os.path.join(directory_path, item)
            tag = "[DIR] " if os.path.isdir(full) else "[FILE]"
            lines.append(f"  {tag} {item}")
        
        res = "\n".join(lines)
        AgentTracer.emit_action("list_dir", f"ls {directory_path}", f"{len(items)} items listed")
        return res
    except Exception as e:
        return f"[EXECUTOR] List dir error: {e}"
