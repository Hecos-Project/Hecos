import os
import shutil
import difflib

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


_CTRL_ESCAPE_MAP = {
    "\x07": "\\a",
    "\x08": "\\b",
    "\x09": "\\t",
    "\x0a": "\\n",
    "\x0b": "\\v",
    "\x0c": "\\f",
    "\x0d": "\\r",
}


def sanitize_llm_path(raw_path: str) -> str:
    """
    Clean an LLM-supplied filesystem path and repair unescaped Windows backslash control sequences
    such as '\\test_clock\\app.py' accidentally decoded as '<TAB>est_clock<BEL>pp.py'.
    """
    clean = str(raw_path or "").strip().strip("'\"")
    if clean.lower().startswith("file:///"):
        clean = clean[8:]
    elif clean.lower().startswith("file://"):
        clean = clean[7:]
    if any(ch in clean for ch in _CTRL_ESCAPE_MAP):
        clean = "".join(_CTRL_ESCAPE_MAP.get(ch, ch) for ch in clean)
    return clean

# ── File Management ───────────────────────────────────────────────────────────

def read_file_tool(file_path: str, start_line: int = 1, end_line: int = -1) -> str:
    """
    Reads the contents of a file with 1-indexed line numbers and context-safe pagination.
    Use start_line and end_line to paginate large files.
    :param file_path: Absolute path to the file to read.
    :param start_line: First line to read (1-indexed). Default: 1.
    :param end_line: Last line to read (inclusive). Use -1 to read up to 250 lines from start_line.
    """
    file_path = sanitize_llm_path(file_path)
    if not os.path.exists(file_path):
        return f"[EXECUTOR] File not found: {file_path}"
    try:
        s_line = max(1, int(start_line))
        req_end = int(end_line)

        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        total_lines = len(lines)
        if total_lines == 0:
            AgentTracer.emit_action("read_file", f"Reading {file_path}", "0 lines")
            return f"--- {file_path} (empty file, 0 lines) ---"

        if s_line > total_lines:
            return f"[EXECUTOR] start_line={s_line} exceeds file length ({total_lines} lines) in {file_path}."

        default_window = 250
        max_chars = 14000
        if req_end <= 0:
            e_line = min(total_lines, s_line + default_window - 1)
        else:
            e_line = min(total_lines, max(s_line, req_end))

        out_parts = []
        char_count = 0
        actual_end = s_line - 1
        char_truncated = False

        for idx in range(s_line, e_line + 1):
            raw_line = lines[idx - 1]
            # Strip only trailing newline for clean formatting, cap overly long minified lines
            text_no_nl = raw_line.rstrip("\r\n")
            if len(text_no_nl) > 800:
                text_no_nl = text_no_nl[:800] + f" ... [+{len(text_no_nl) - 800} chars]"
            formatted = f"{idx} | {text_no_nl}\n"
            if out_parts and (char_count + len(formatted) > max_chars):
                char_truncated = True
                break
            out_parts.append(formatted)
            char_count += len(formatted)
            actual_end = idx

        header = f"--- {file_path} (lines {s_line}-{actual_end} of {total_lines}) ---\n"
        body = "".join(out_parts).rstrip("\n")
        footer = ""
        if actual_end < total_lines and (req_end <= 0 or char_truncated or actual_end < e_line):
            next_start = actual_end + 1
            next_end = min(total_lines, next_start + default_window - 1)
            footer = (
                f"\n... [TRUNCATED: showing lines {s_line}-{actual_end} of {total_lines}. "
                f"Call read_file('{file_path}', start_line={next_start}, end_line={next_end}) to continue.]"
            )

        res = header + body + footer
        AgentTracer.emit_action("read_file", f"Reading {file_path}", f"{total_lines} lines total")
        return res
    except Exception as e:
        return f"[EXECUTOR] Read error: {e}"

def write_file_tool(file_path: str, content: str, mode: str = "w") -> str:
    """
    Writes or creates a file. Mode 'w' overwrites; 'a' appends.
    :param file_path: Absolute or workspace-relative path to the file to write or create.
    :param content: The full text content to write.
    :param mode: 'w' to overwrite (default), 'a' to append.
    """
    abs_path = os.path.abspath(file_path)
    if not _is_safe_path(abs_path):
        return "[EXECUTOR] ACCESS DENIED: Writing to system paths is forbidden."
    try:
        parent = os.path.dirname(abs_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(abs_path, mode, encoding="utf-8") as f:
            f.write(content)
        if not os.path.exists(abs_path):
            return f"[EXECUTOR] Write failed: file was not created at {abs_path}"
        size_bytes = os.path.getsize(abs_path)
        uri = "file:///" + abs_path.replace("\\", "/")
        logger.info(f"[EXECUTOR] write_file OK: {abs_path} (mode={mode}, bytes={size_bytes})")
        res = f"[EXECUTOR] File verified on disk: {abs_path} ({size_bytes} bytes) | URI: {uri}"
        AgentTracer.emit_action("write_file", f"Mode: {mode} -> {abs_path}", f"{len(content)} characters written ({size_bytes} bytes)")
        return res
    except Exception as e:
        return f"[EXECUTOR] Write error: {e}"

def _find_closest_block_hint(lines: list[str], old_text: str, window_pad: int = 3) -> str:
    """Locate the highest-similarity section of the file when patch_file cannot find old_text."""
    if not lines:
        return "(file is empty)"
    needle_lines = [l.strip() for l in old_text.replace("\r\n", "\n").splitlines() if l.strip()]
    if not needle_lines:
        sample = "\n".join(f"{i + 1} | {lines[i].rstrip(chr(10) + chr(13))}" for i in range(min(10, len(lines))))
        return f"First lines:\n{sample}"

    win_size = max(1, min(len(old_text.splitlines()) or 1, len(lines)))
    best_ratio = -1.0
    best_idx = 0
    needle_joined = "\n".join(needle_lines)

    if len(needle_joined) <= 32 and len(lines) > 20:
        try:
            from diff_match_patch import diff_match_patch
            dmp = diff_match_patch()
            full_norm = "\n".join(l.rstrip("\r\n") for l in lines)
            pos = dmp.match_main(full_norm, needle_lines[0][:32], 0)
            if pos >= 0:
                best_idx = full_norm[:pos].count("\n")
                best_ratio = 0.8
        except Exception:
            pass

    if best_ratio < 0.0:
        step = 1 if len(lines) <= 400 else 2
        for i in range(0, max(1, len(lines) - win_size + 1), step):
            cand = "\n".join(l.strip() for l in lines[i:i + win_size])
            ratio = difflib.SequenceMatcher(None, needle_joined, cand).quick_ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_idx = i

    lo = max(0, best_idx - window_pad)
    hi = min(len(lines), best_idx + win_size + window_pad)
    excerpt = "\n".join(
        f"{idx + 1} | {lines[idx].rstrip(chr(10) + chr(13))[:200]}"
        for idx in range(lo, hi)
    )
    return f"Closest section (lines {lo + 1}-{hi} of {len(lines)}):\n{excerpt}"


def patch_file_tool(
    file_path: str,
    old_text: str,
    new_text: str,
    start_line: int = 0,
    end_line: int = 0,
) -> str:
    """
    Surgically replaces a unique occurrence of old_text with new_text in a file.
    Detects ambiguous matches, tolerates CRLF/trailing-whitespace differences, and
    optionally restricts search to start_line..end_line.
    :param file_path: Absolute or workspace-relative path to the file to patch.
    :param old_text: Existing block to find and replace.
    :param new_text: Replacement text block.
    :param start_line: Optional 1-indexed start line to narrow matching (0 = full file).
    :param end_line: Optional 1-indexed end line to narrow matching (0 = end of file).
    """
    abs_path = os.path.abspath(file_path)
    if not _is_safe_path(abs_path):
        return "[EXECUTOR] ACCESS DENIED: Patching system paths is forbidden."
    if not os.path.exists(abs_path):
        return f"[EXECUTOR] File not found: {abs_path}"
    if old_text is None or old_text == "":
        return "[EXECUTOR] Patch error: old_text must not be empty."

    try:
        with open(abs_path, "r", encoding="utf-8", errors="replace", newline="") as f:
            original = f.read()

        s_line = max(0, int(start_line or 0))
        e_line = max(0, int(end_line or 0))
        all_lines = original.splitlines(keepends=True)

        if s_line > 0 or e_line > 0:
            start_idx = max(0, s_line - 1) if s_line > 0 else 0
            end_idx = min(len(all_lines), e_line) if e_line > 0 else len(all_lines)
            if start_idx >= len(all_lines) or end_idx <= start_idx:
                return f"[EXECUTOR] Invalid line range {s_line}-{e_line} for {abs_path} ({len(all_lines)} lines)."
            prefix = "".join(all_lines[:start_idx])
            target_region = "".join(all_lines[start_idx:end_idx])
            suffix = "".join(all_lines[end_idx:])
        else:
            start_idx = 0
            prefix = ""
            target_region = original
            suffix = ""

        patched_region = None
        exact_count = target_region.count(old_text)
        if exact_count > 1:
            occ_lines = []
            pos = 0
            while True:
                found = target_region.find(old_text, pos)
                if found == -1:
                    break
                occ_lines.append(start_idx + target_region[:found].count("\n") + 1)
                pos = found + len(old_text)
            return (
                f"[EXECUTOR] Ambiguous patch: old_text matches {exact_count} occurrences in {abs_path} "
                f"(lines {occ_lines}). Include more surrounding context or pass start_line/end_line."
            )
        elif exact_count == 1:
            patched_region = target_region.replace(old_text, new_text, 1)
        else:
            newline_style = "\r\n" if "\r\n" in original else "\n"
            region_lf = target_region.replace("\r\n", "\n")
            old_lf = old_text.replace("\r\n", "\n")
            new_lf = new_text.replace("\r\n", "\n")
            lf_count = region_lf.count(old_lf)
            if lf_count > 1:
                return (
                    f"[EXECUTOR] Ambiguous patch: old_text matches {lf_count} occurrences (CRLF-normalized) "
                    f"in {abs_path}. Include more context or pass start_line/end_line."
                )
            elif lf_count == 1:
                replaced_lf = region_lf.replace(old_lf, new_lf, 1)
                patched_region = replaced_lf.replace("\n", newline_style) if newline_style == "\r\n" else replaced_lf
            else:
                reg_lines = region_lf.splitlines(keepends=True)
                old_block_lines = old_lf.splitlines()
                norm_old = [l.rstrip(" \t") for l in old_block_lines]
                n = len(norm_old)
                if n > 0 and len(reg_lines) >= n:
                    norm_reg = [l.rstrip(" \t\r\n") for l in reg_lines]
                    hits = [i for i in range(len(norm_reg) - n + 1) if norm_reg[i:i + n] == norm_old]
                    if len(hits) > 1:
                        hit_lines = [start_idx + i + 1 for i in hits]
                        return (
                            f"[EXECUTOR] Ambiguous patch: old_text matches {len(hits)} whitespace-normalized "
                            f"blocks in {abs_path} (lines {hit_lines}). Specify start_line/end_line."
                        )
                    elif len(hits) == 1:
                        i = hits[0]
                        had_end_nl = reg_lines[i + n - 1].endswith("\n")
                        rep_text = new_lf
                        if had_end_nl and not rep_text.endswith("\n"):
                            rep_text += "\n"
                        elif not had_end_nl and rep_text.endswith("\n") and not old_text.endswith("\n"):
                            rep_text = rep_text[:-1]
                        rebuilt = "".join(reg_lines[:i]) + rep_text + "".join(reg_lines[i + n:])
                        patched_region = rebuilt.replace("\n", newline_style) if newline_style == "\r\n" else rebuilt

        if patched_region is None:
            hint = _find_closest_block_hint(all_lines, old_text)
            return f"[EXECUTOR] Text to replace not found in {abs_path}. {hint}"

        patched = prefix + patched_region + suffix
        with open(abs_path, "w", encoding="utf-8", newline="") as f:
            f.write(patched)
        size_bytes = os.path.getsize(abs_path)
        uri = "file:///" + abs_path.replace("\\", "/")
        logger.info(f"[EXECUTOR] patch_file OK: {abs_path} (bytes={size_bytes})")
        res = f"[EXECUTOR] File patched and verified on disk: {abs_path} ({size_bytes} bytes) | URI: {uri}"
        AgentTracer.emit_action("patch_file", f"Patching {abs_path}", f"Replaced text block successfully ({size_bytes} bytes)")
        return res
    except Exception as e:
        return f"[EXECUTOR] Patch error: {e}"


def move_path_tool(src_path: str, dst_path: str) -> str:
    """Safely rename or move a file or directory within authorized paths."""
    src_abs = os.path.abspath(src_path)
    dst_abs = os.path.abspath(dst_path)
    if not _is_safe_path(src_abs) or not _is_safe_path(dst_abs):
        return "[EXECUTOR] ACCESS DENIED: Moving files to/from protected system paths is forbidden."
    if not os.path.exists(src_abs):
        return f"[EXECUTOR] Source path not found: {src_abs}"
    try:
        parent = os.path.dirname(dst_abs)
        if parent:
            os.makedirs(parent, exist_ok=True)
        shutil.move(src_abs, dst_abs)
        uri = "file:///" + dst_abs.replace("\\", "/")
        logger.info(f"[EXECUTOR] move_path OK: {src_abs} -> {dst_abs}")
        res = f"[EXECUTOR] Moved successfully: {src_abs} -> {dst_abs} | URI: {uri}"
        AgentTracer.emit_action("move_path", f"{src_abs} -> {dst_abs}", res)
        return res
    except Exception as e:
        return f"[EXECUTOR] Move error: {e}"

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
    Media files (images, videos) are formatted as markdown links so the UI
    can render them directly (the chat renderer processes these links).
    :param directory_path: Absolute path to the directory to list.
    """
    import re

    IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg'}
    VIDEO_EXTS = {'.mp4', '.webm', '.ogg', '.mov', '.mkv', '.avi', '.m4v',
                  '.ts', '.flv', '.3gp', '.wmv', '.mpeg', '.mpg'}

    if not os.path.exists(directory_path):
        return f"[EXECUTOR] Directory not found: {directory_path}"
    try:
        items = os.listdir(directory_path)
        lines = [f"--- Contents of {directory_path} ({len(items)} items) ---"]
        for item in sorted(items):
            full = os.path.join(directory_path, item)
            if os.path.isdir(full):
                lines.append(f"  [DIR]  {item}")
            else:
                ext = os.path.splitext(item)[1].lower()
                if ext in IMAGE_EXTS:
                    # Render as inline image: the chat renders ![name](path) as an image
                    lines.append(f"  [IMG]  ![{item}]({full})")
                elif ext in VIDEO_EXTS:
                    # Render as markdown link: the chat renders [name](path) as a video card
                    lines.append(f"  [VID]  [{item}]({full})")
                else:
                    lines.append(f"  [FILE] {item}")

        res = "\n".join(lines)
        AgentTracer.emit_action("list_dir", f"ls {directory_path}", f"{len(items)} items listed")
        return res
    except Exception as e:
        return f"[EXECUTOR] List dir error: {e}"
