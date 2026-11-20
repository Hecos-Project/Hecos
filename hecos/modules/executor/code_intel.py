"""
Code intelligence helpers powered by battle-tested libraries:
- tree-sitter-language-pack: multi-language AST outline & fallback syntax verification
- grep-ast: enclosing-scope AST-aware code search
- ruff: fast Python static analysis (syntax, undefined names, broken imports)
- pathspec + beautifulsoup4: .gitignore filtering & static web asset verification
"""

from __future__ import annotations

import fnmatch
import json
import logging
import os
import re
import shutil
import subprocess
import sys
from typing import Iterable, List, Optional, Tuple

try:
    from hecos.core.logging import logger
except ImportError:
    logger = logging.getLogger(__name__)

_DEFAULT_IGNORED_DIRS = {
    "__pycache__",
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "python_env",
    "node_modules",
    "dist",
    "build",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".eggs",
    ".idea",
    ".vscode",
}

_BINARY_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".bmp", ".svgz",
    ".pdf", ".zip", ".tar", ".gz", ".7z", ".rar", ".whl",
    ".exe", ".dll", ".pyd", ".so", ".dylib", ".bin", ".dat",
    ".mp3", ".wav", ".ogg", ".flac", ".mp4", ".webm", ".mov",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".pyc", ".pyo", ".sqlite", ".db", ".lance",
}

_RUFF_HARD_CODES = {
    "F402", "F631", "F632", "F633", "F634",
    "F701", "F702", "F704", "F706", "F707",
    "F811", "F821", "F822", "F823",
}


def resolve_python_tool_binary(tool_name: str) -> Optional[str]:
    """Locate a CLI tool bundled in the active Python env (e.g. ruff, pytest, uv) or PATH."""
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    candidates: List[str] = []
    exts = (".exe", "") if os.name == "nt" else ("",)
    for base_dir in (exe_dir, os.path.join(exe_dir, "Scripts"), os.path.join(exe_dir, "bin")):
        for ext in exts:
            candidates.append(os.path.join(base_dir, f"{tool_name}{ext}"))
    for cand in candidates:
        if os.path.isfile(cand):
            return cand
    return shutil.which(tool_name)


def load_gitignore_spec(root_dir: str):
    """Build a pathspec matcher from <root_dir>/.gitignore when pathspec is available."""
    gitignore_path = os.path.join(root_dir, ".gitignore")
    if not os.path.isfile(gitignore_path):
        return None
    try:
        import pathspec

        with open(gitignore_path, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
        return pathspec.PathSpec.from_lines("gitignore", lines)
    except Exception as exc:
        logger.debug(f"[code_intel] Could not parse .gitignore at {gitignore_path}: {exc}")
        return None


def iter_project_files(
    root_dir: str,
    max_files: int = 250,
    file_glob: str = "",
) -> Iterable[Tuple[str, str]]:
    """Yield (abs_path, rel_posix_path) under root_dir skipping ignored/binary files."""
    abs_root = os.path.abspath(root_dir)
    if os.path.isfile(abs_root):
        yield abs_root, os.path.basename(abs_root)
        return
    if not os.path.isdir(abs_root):
        return

    spec = load_gitignore_spec(abs_root)
    glob_pattern = (file_glob or "").strip()
    count = 0

    for cur_dir, dirs, files in os.walk(abs_root):
        rel_dir = os.path.relpath(cur_dir, abs_root).replace("\\", "/")
        kept_dirs: List[str] = []
        for d in sorted(dirs):
            if d in _DEFAULT_IGNORED_DIRS or d.endswith(".egg-info") or d.startswith("."):
                continue
            rel_sub = d if rel_dir == "." else f"{rel_dir}/{d}"
            if spec and spec.match_file(rel_sub + "/"):
                continue
            kept_dirs.append(d)
        dirs[:] = kept_dirs

        for fname in sorted(files):
            ext = os.path.splitext(fname)[1].lower()
            if ext in _BINARY_EXTS:
                continue
            rel_file = fname if rel_dir == "." else f"{rel_dir}/{fname}"
            if spec and spec.match_file(rel_file):
                continue
            if glob_pattern and not (
                fnmatch.fnmatch(fname, glob_pattern) or fnmatch.fnmatch(rel_file, glob_pattern)
            ):
                continue
            yield os.path.join(cur_dir, fname), rel_file
            count += 1
            if count >= max_files:
                return


def _format_structure_items(items, indent: int = 0, out: Optional[List[str]] = None, limit: int = 24) -> List[str]:
    if out is None:
        out = []
    prefix = "  " * indent
    for item in items:
        if len(out) >= limit:
            break
        kind_raw = getattr(item, "kind", None)
        kind_str = str(kind_raw).split(".")[-1].lower() if kind_raw is not None else "sym"
        name = getattr(item, "name", "") or ""
        sig = (getattr(item, "signature", None) or "").strip()
        span = getattr(item, "span", None)
        line_tag = f"L{span.start_line + 1}" if span is not None else ""
        label = sig if sig and len(sig) <= 96 else f"{kind_str} {name}".strip()
        if line_tag:
            out.append(f"{prefix}{label} ({line_tag})")
        else:
            out.append(f"{prefix}{label}")
        children = getattr(item, "children", None) or []
        if children and len(out) < limit:
            _format_structure_items(children, indent=indent + 1, out=out, limit=limit)
    return out


def _extract_html_outline(source: str, limit: int = 12) -> List[str]:
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(source, "html.parser")
        lines: List[str] = []
        if soup.title and soup.title.string:
            lines.append(f"<title>: {soup.title.string.strip()[:60]}")
        for tag in soup.find_all(["link", "script", "form"]):
            if len(lines) >= limit:
                break
            if tag.name == "link" and tag.get("href"):
                lines.append(f"<link href={tag.get('href')}>")
            elif tag.name == "script" and tag.get("src"):
                lines.append(f"<script src={tag.get('src')}>")
            elif tag.name == "form":
                action = tag.get("action") or "(inline)"
                lines.append(f"<form action={action}>")
        ids = [el.get("id") for el in soup.find_all(attrs={"id": True}) if el.get("id")]
        if ids and len(lines) < limit:
            sample = ", ".join(f"#{i}" for i in ids[:8])
            if len(ids) > 8:
                sample += f", ... (+{len(ids) - 8})"
            lines.append(f"ids: {sample}")
        return lines[:limit]
    except Exception:
        return []


def _extract_css_outline(source: str, limit: int = 16) -> List[str]:
    try:
        import tree_sitter_language_pack as tslp

        parser = tslp.get_parser("css")
        src_bytes = source.encode("utf-8", errors="replace")
        tree = parser.parse(src_bytes)
        lines: List[str] = []
        for child in tree.root_node.children:
            if len(lines) >= limit:
                break
            if child.type == "rule_set":
                for sub in child.children:
                    if sub.type == "selectors":
                        text = src_bytes[sub.start_byte:sub.end_byte].decode("utf-8", errors="replace").strip()
                        text = " ".join(text.split())
                        if len(text) > 72:
                            text = text[:69] + "..."
                        lines.append(f"{text} (L{child.start_point[0] + 1})")
                        break
            elif child.type in ("media_statement", "keyframes_statement"):
                first = src_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace").splitlines()[0]
                lines.append(f"{first[:72].strip()} (L{child.start_point[0] + 1})")
        return lines
    except Exception:
        return []


def extract_file_outline(abs_path: str, max_symbols: int = 24) -> List[str]:
    """Extract concise structural symbols (classes, functions, HTML links/ids, CSS rules)."""
    try:
        if os.path.getsize(abs_path) > 256 * 1024:
            return ["(large file >256KB — outline skipped)"]
        with open(abs_path, "r", encoding="utf-8", errors="replace") as fh:
            source = fh.read()
    except OSError as exc:
        return [f"(read error: {exc})"]

    ext = os.path.splitext(abs_path)[1].lower()
    if ext in (".html", ".htm"):
        return _extract_html_outline(source, limit=min(max_symbols, 12))
    if ext == ".css":
        return _extract_css_outline(source, limit=min(max_symbols, 16))

    try:
        import tree_sitter_language_pack as tslp

        lang = tslp.detect_language_from_path(abs_path)
        if not lang or not tslp.has_language(lang):
            return []
        res = tslp.process(source, tslp.ProcessConfig(language=lang))
        structure = getattr(res, "structure", None) or []
        return _format_structure_items(structure, limit=max_symbols)
    except Exception as exc:
        logger.debug(f"[code_intel] outline fallback for {abs_path}: {exc}")
        return []


def build_repo_map(root_dir: str, max_files: int = 60, max_lines: int = 160) -> str:
    """
    Build a concise multi-language AST repository map showing files, key classes/functions,
    and line numbers. Strictly bounded to fit comfortably inside local LLM context windows.
    """
    abs_root = os.path.abspath(root_dir)
    if not os.path.exists(abs_root):
        return f"[EXECUTOR] Path not found: {abs_root}"

    try:
        max_files_i = max(1, min(int(max_files), 200))
    except (TypeError, ValueError):
        max_files_i = 60
    try:
        max_lines_i = max(20, min(int(max_lines), 400))
    except (TypeError, ValueError):
        max_lines_i = 160

    out_lines: List[str] = [f"[EXECUTOR] Repo map for: {abs_root}"]
    files_seen = 0
    truncated = False

    for fpath, rel_path in iter_project_files(abs_root, max_files=max_files_i):
        files_seen += 1
        outline = extract_file_outline(fpath, max_symbols=16)
        try:
            with open(fpath, "r", encoding="utf-8", errors="replace") as lf:
                line_count = sum(1 for _ in lf)
        except OSError:
            line_count = 0

        header = f"{rel_path} ({line_count} lines)"
        if len(out_lines) + 1 > max_lines_i:
            truncated = True
            break
        out_lines.append(header)
        for sym_line in outline:
            if len(out_lines) + 1 > max_lines_i:
                truncated = True
                break
            out_lines.append(f"  {sym_line}")
        if truncated:
            break

    if files_seen == 0:
        logger.debug(f"[CODE_INTEL] repo_map empty for {abs_root}")
        return f"[EXECUTOR] Repo map for {abs_root}: (no source files found)"
    if truncated:
        out_lines.append(f"... (repo map truncated at {max_lines_i} lines; narrow root_dir or read specific files)")
    logger.info(f"[CODE_INTEL] repo_map built: {abs_root} ({files_seen} files, {len(out_lines)} lines, truncated={truncated})")
    return "\n".join(out_lines)


def _compile_search_pattern(query: str, case_sensitive: bool) -> re.Pattern:
    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        return re.compile(query, flags)
    except re.error:
        return re.compile(re.escape(query), flags)


def ast_search_code(
    query: str,
    target_path: str,
    file_glob: str = "",
    case_sensitive: bool = False,
    max_matches: int = 35,
) -> str:
    """
    Search code using grep-ast (attaching enclosing function/class signatures for matches)
    with clean fallback to numbered line matches when a file type has no tree-sitter grammar.
    """
    if not query or not str(query).strip():
        return "[EXECUTOR] Search query cannot be empty."
    abs_target = os.path.abspath(target_path)
    if not os.path.exists(abs_target):
        return f"[EXECUTOR] Path not found: {abs_target}"

    try:
        max_m = max(1, min(int(max_matches), 100))
    except (TypeError, ValueError):
        max_m = 35

    pattern = _compile_search_pattern(query, case_sensitive)
    chunks: List[str] = []
    match_count = 0
    files_matched = 0

    try:
        from grep_ast import TreeContext
    except Exception:
        TreeContext = None  # type: ignore

    for fpath, rel_path in iter_project_files(abs_target, max_files=400, file_glob=file_glob):
        if os.path.getsize(fpath) > 512 * 1024:
            continue
        try:
            with open(fpath, "r", encoding="utf-8", errors="replace") as fh:
                content = fh.read()
        except OSError:
            continue

        if not pattern.search(content):
            continue

        files_matched += 1
        rendered_block = ""
        file_hits = 0

        if TreeContext is not None:
            try:
                tc = TreeContext(
                    rel_path,
                    content,
                    color=False,
                    line_number=True,
                    margin=1,
                    mark_lois=True,
                    loi_pad=1,
                )
                try:
                    lois = tc.grep(query, not case_sensitive)
                except re.error:
                    lois = tc.grep(re.escape(query), not case_sensitive)
                if lois:
                    sorted_lois = sorted(lois)
                    remaining = max(1, max_m - match_count)
                    capped_lois = set(sorted_lois[:remaining])
                    file_hits = len(capped_lois)
                    tc.add_lines_of_interest(capped_lois)
                    tc.add_context()
                    rendered_block = tc.format().rstrip()
            except Exception:
                rendered_block = ""

        if not rendered_block:
            lines = content.splitlines()
            snippet_lines: List[str] = []
            for idx, line in enumerate(lines, start=1):
                if pattern.search(line):
                    snippet_lines.append(f"{idx:>4}█{line[:180]}")
                    file_hits += 1
                    if match_count + file_hits >= max_m:
                        break
            rendered_block = "\n".join(snippet_lines)

        if rendered_block:
            match_count += file_hits
            chunks.append(f"=== {rel_path} ===\n{rendered_block}")
        if match_count >= max_m:
            break

    if not chunks:
        scope_note = f" (glob={file_glob})" if file_glob else ""
        logger.debug(f"[CODE_INTEL] ast_search 0 hits for '{query}' in {abs_target}{scope_note}")
        return f"[EXECUTOR] No matches for '{query}' in {abs_target}{scope_note}"

    result = "\n\n".join(chunks)
    if len(result) > 10000:
        result = result[:9800] + "\n... [SEARCH OUTPUT TRUNCATED — refine query or file_glob]"
    logger.info(f"[CODE_INTEL] ast_search '{query}' -> {match_count} matches in {files_matched} file(s) ({abs_target})")
    header = f"[EXECUTOR] Matches for '{query}' ({match_count} lines across {files_matched} file(s)):\n"
    return header + result


def run_ruff_check(abs_path: str) -> Tuple[bool, List[str], List[str]]:
    """
    Run Ruff static checks (E9 syntax + F undefined names / broken imports / logic hazards).
    Returns (has_no_blocking_errors, blocking_errors, non_blocking_warnings).
    """
    ruff_bin = resolve_python_tool_binary("ruff")
    if not ruff_bin:
        return True, [], []

    try:
        proc = subprocess.run(
            [ruff_bin, "check", "--no-fix", "--no-cache", "--select=E9,F", "--output-format=json", abs_path],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=15,
        )
    except Exception as exc:
        logger.debug(f"[CODE_INTEL] ruff invocation skipped: {exc}")
        return True, [], []

    stdout = (proc.stdout or "").strip()
    if not stdout:
        if proc.returncode not in (0, 1):
            err_msg = (proc.stderr or f"ruff exited with code {proc.returncode}").strip()
            return False, [err_msg], []
        return True, [], []

    try:
        items = json.loads(stdout)
    except json.JSONDecodeError:
        return True, [], []

    errors: List[str] = []
    warnings: List[str] = []
    for item in items:
        code = item.get("code") or "RUFF"
        msg = item.get("message") or ""
        loc = item.get("location") or {}
        row = loc.get("row", "?")
        col = loc.get("column", "?")
        formatted = f"L{row}:{col} [{code}] {msg}"
        if code.startswith("E9") or code in _RUFF_HARD_CODES or code == "RUFF":
            errors.append(formatted)
        else:
            warnings.append(formatted)

    logger.debug(f"[CODE_INTEL] ruff {abs_path}: errors={len(errors)}, warnings={len(warnings)}")
    return len(errors) == 0, errors[:12], warnings[:8]


def _find_tree_error_nodes(node, src_bytes: bytes, out: List[str], limit: int = 5) -> None:
    if len(out) >= limit:
        return
    if node.type == "ERROR" or node.is_missing:
        row, col = node.start_point
        snippet = src_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace").strip()
        snippet = " ".join(snippet.split())[:60]
        kind = "missing token" if node.is_missing else "syntax error"
        out.append(f"L{row + 1}:{col + 1} {kind}" + (f" near '{snippet}'" if snippet else ""))
        return
    for child in node.children:
        if child.has_error:
            _find_tree_error_nodes(child, src_bytes, out, limit=limit)


def check_tree_sitter_syntax(abs_path: str, source: str) -> Optional[str]:
    """
    Verify syntax via tree-sitter grammars (useful for JS/TS/CSS/HTML when node is unavailable).
    Returns None when clean or when no grammar applies; returns an error summary string otherwise.
    """
    try:
        import tree_sitter_language_pack as tslp

        lang = tslp.detect_language_from_path(abs_path)
        if not lang or not tslp.has_language(lang):
            return None
        parser = tslp.get_parser(lang)
        src_bytes = source.encode("utf-8", errors="replace")
        tree = parser.parse(src_bytes)
        if not tree.root_node.has_error:
            return None
        errors: List[str] = []
        _find_tree_error_nodes(tree.root_node, src_bytes, errors, limit=5)
        if not errors:
            return f"Parser ({lang}) reported a syntax error."
        return "; ".join(errors)
    except Exception as exc:
        logger.debug(f"[code_intel] tree-sitter syntax check failed for {abs_path}: {exc}")
        return None


def check_static_web_assets(html_path: str) -> List[str]:
    """
    Verify local <link href=...> and <script src=...> assets referenced by an HTML file exist on disk.
    """
    if not os.path.isfile(html_path):
        return []
    try:
        from bs4 import BeautifulSoup

        with open(html_path, "r", encoding="utf-8", errors="replace") as fh:
            html_src = fh.read()
        soup = BeautifulSoup(html_src, "html.parser")
    except Exception:
        return []

    html_dir = os.path.dirname(os.path.abspath(html_path))
    parent_dir = os.path.dirname(html_dir)
    issues: List[str] = []
    seen = set()

    for tag in soup.find_all(["link", "script"]):
        if tag.name == "link":
            rel = [r.lower() for r in (tag.get("rel") or [])]
            if rel and "stylesheet" not in rel and "icon" not in rel:
                continue
            ref = tag.get("href")
        else:
            ref = tag.get("src")

        if not isinstance(ref, str):
            continue
        clean = ref.strip()
        if not clean or clean in seen:
            continue
        seen.add(clean)

        lower = clean.lower()
        if lower.startswith(("http://", "https://", "//", "data:", "blob:", "#", "javascript:")):
            continue
        if "{{" in clean or "{%" in clean:
            continue

        clean_no_q = clean.split("?", 1)[0].split("#", 1)[0].strip()
        if not clean_no_q:
            continue

        if clean_no_q.startswith("/static/"):
            rel_sub = clean_no_q[len("/static/"):].lstrip("/")
            cand1 = os.path.join(html_dir, "static", rel_sub)
            cand2 = os.path.join(parent_dir, "static", rel_sub)
            if not (os.path.isfile(cand1) or os.path.isfile(cand2)):
                issues.append(f"Referenced static asset '{clean_no_q}' was not found under static/{rel_sub}.")
            continue

        if clean_no_q.startswith("/"):
            continue

        target = os.path.abspath(os.path.join(html_dir, clean_no_q))
        if not os.path.exists(target):
            issues.append(
                f"Referenced local asset '{clean_no_q}' in {os.path.basename(html_path)} does not exist at {target}."
            )

    return issues[:10]
