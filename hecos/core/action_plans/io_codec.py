"""
hecos/core/action_plans/io_codec.py
Multi-format Export & Import codec for Hecos Action Plans:
  - Markdown (.md) — Default human-readable & hand-editable format with clean YAML frontmatter
  - Standalone HTML (.html) — Visual dark-glass / print-to-PDF report with lossless embedded JSON
  - Structured YAML (.yaml / .yml) — Clean multiline block YAML, 100% lossless
  - JSON (.hecos-plan.json / .json) — Machine-friendly lossless archive
"""

from __future__ import annotations

import html as html_mod
import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import yaml

from hecos.core.action_plans.models import (
    build_plan_markdown_document,
    compute_plan_progress,
    normalize_step_status,
    normalize_steps,
)

EXPORT_SCHEMA_VERSION = "hecos.action_plan.v1"
SUPPORTED_EXPORT_FORMATS = ("md", "html", "yaml", "json")

_FILE_TAG_RE = re.compile(
    r"\[(?P<tag>NEW|MODIFY|DELETE|RENAME|TEST)\]\s*`?(?P<path>[^`\r\n,;()]+)`?",
    re.IGNORECASE,
)
_CHECKBOX_RE = re.compile(r"^\s*[-*•]\s*\[(?P<mark>[ xX\-~])\]\s*(?P<text>.+?)\s*$")
_NUMBERED_RE = re.compile(r"^\s*(?:Step\s+)?(?P<num>\d+)[.)]\s+(?P<text>.+?)\s*$", re.IGNORECASE)
_HEADING_STEP_RE = re.compile(r"^\s*#{3,4}\s+(?:Step\s+)?(?P<num>\d+)?[.):]?\s*(?P<text>.+?)\s*$", re.IGNORECASE)
_FRONTMATTER_RE = re.compile(r"^\s*---\s*\n(?P<yaml>.*?)\n---\s*(?:\n|$)", re.DOTALL)
_HTML_EMBEDDED_JSON_RE = re.compile(
    r'<script[^>]*\bid=["\']hecos-plan-data["\'][^>]*>(?P<json>.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)


class _LiteralStr(str):
    """String subclass serialized as YAML literal block (`|`) when multiline."""


class _PlanYamlDumper(yaml.SafeDumper):
    pass


def _represent_literal_str(dumper: yaml.SafeDumper, data: _LiteralStr):
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", str(data), style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", str(data))


_PlanYamlDumper.add_representer(_LiteralStr, _represent_literal_str)


def normalize_export_format(fmt: str = "md") -> str:
    """Normalize format aliases into one of: 'md', 'html', 'yaml', 'json' (default 'md')."""
    clean = str(fmt or "md").strip().lower().lstrip(".")
    if clean in ("", "md", "markdown"):
        return "md"
    if clean in ("html", "htm"):
        return "html"
    if clean in ("yaml", "yml"):
        return "yaml"
    if clean == "json":
        return "json"
    return "md"


def format_from_filename(filename: str, fallback: str = "md") -> str:
    """Infer export/import format from a filename extension."""
    ext = os.path.splitext(str(filename or ""))[1].lower().lstrip(".")
    if ext in ("md", "markdown"):
        return "md"
    if ext in ("html", "htm"):
        return "html"
    if ext in ("yaml", "yml"):
        return "yaml"
    if ext == "json":
        return "json"
    return normalize_export_format(fallback)


def suggest_plan_filename(plan: Dict[str, Any], fmt: str = "md") -> str:
    """Build a safe filesystem-friendly filename from a plan title and target format."""
    raw_title = str((plan or {}).get("title") or "action_plan").strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "_", raw_title).strip("_")[:60] or "action_plan"
    eff = normalize_export_format(fmt)
    if eff == "md":
        return f"{slug}.md"
    if eff == "html":
        return f"{slug}.html"
    if eff == "yaml":
        return f"{slug}.yaml"
    return f"{slug}.hecos-plan.json"


def _build_canonical_payload(plan: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "schema": EXPORT_SCHEMA_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "plan": {
            "plan_id": str(plan.get("plan_id") or ""),
            "title": str(plan.get("title") or "Action Plan"),
            "goal": str(plan.get("goal") or ""),
            "plan_markdown": str(plan.get("plan_markdown") or ""),
            "verification_plan": str(plan.get("verification_plan") or ""),
            "revision": int(plan.get("revision") or 1),
            "revision_history": list(plan.get("revision_history") or []),
            "status": str(plan.get("status") or "awaiting_approval"),
            "plan_mode": str(plan.get("plan_mode") or "plan_only"),
            "steps": list(plan.get("steps") or []),
            "metadata": dict(plan.get("metadata") or {}),
        },
    }


def _strip_checklist_section(md: str) -> str:
    """Remove any trailing/existing `## Execution Checklist` section to avoid duplicates on round-trip."""
    lines = str(md or "").splitlines()
    out: List[str] = []
    skipping = False
    for line in lines:
        m = re.match(r"^\s*##\s+(.+?)\s*$", line)
        if m:
            heading = m.group(1).strip().lower()
            if "execution checklist" in heading:
                skipping = True
                continue
            elif skipping:
                skipping = False
        if not skipping:
            out.append(line)
    return "\n".join(out).strip()


def _serialize_markdown_export(plan: Dict[str, Any]) -> str:
    """Render clean, human-editable Markdown with lightweight YAML frontmatter & full step checklist."""
    title = str(plan.get("title") or "Action Plan").strip()
    rev = max(1, int(plan.get("revision") or 1))
    status = str(plan.get("status") or "awaiting_approval").strip()
    exported_at = datetime.now(timezone.utc).isoformat()
    steps = plan.get("steps") or []

    fm_dict = {
        "hecos_schema": EXPORT_SCHEMA_VERSION,
        "title": title,
        "revision": rev,
        "status": status,
        "exported_at": exported_at,
    }
    fm_yaml = yaml.safe_dump(fm_dict, sort_keys=False, allow_unicode=True).strip()
    frontmatter = f"---\n{fm_yaml}\n---"

    # Build human-readable body without duplicating Execution Checklist
    plan_for_body = dict(plan)
    if plan_for_body.get("plan_markdown"):
        plan_for_body["plan_markdown"] = _strip_checklist_section(plan_for_body["plan_markdown"])
    body_md = build_plan_markdown_document(plan_for_body, include_step_checklist=False)

    parts = [frontmatter, body_md]

    if steps:
        icons = {"done": "[x]", "running": "[ ]", "failed": "[ ]", "skipped": "[-]", "pending": "[ ]"}
        cl_lines = ["## Execution Checklist"]
        for idx, s in enumerate(steps, start=1):
            st_num = int(s.get("index") or idx)
            mark = icons.get(str(s.get("status") or "pending").lower(), "[ ]")
            st_title = str(s.get("title") or f"Step {st_num}").strip()
            cl_lines.append(f"- {mark} **Step {st_num}:** {st_title}")
            sfiles = s.get("files") or []
            if sfiles:
                cl_lines.append("  - **Files:** " + ", ".join(f"`{f}`" for f in sfiles))
            sdetails = str(s.get("details") or "").strip()
            if sdetails:
                cl_lines.append(f"  - **Details:** {sdetails}")
            snotes = str(s.get("notes") or "").strip()
            if snotes:
                cl_lines.append(f"  - **Notes:** {snotes}")
        parts.append("\n".join(cl_lines))

    return "\n\n".join(p for p in parts if p.strip()).rstrip() + "\n"


def _serialize_yaml_export(plan: Dict[str, Any]) -> str:
    """Render clean, multiline-friendly YAML that is 100% lossless on re-import."""
    payload = _build_canonical_payload(plan)
    p = payload["plan"]
    for key in ("goal", "plan_markdown", "verification_plan"):
        if isinstance(p.get(key), str) and "\n" in p[key]:
            p[key] = _LiteralStr(p[key])
    for st in p.get("steps") or []:
        if isinstance(st, dict):
            for k in ("details", "notes"):
                if isinstance(st.get(k), str) and "\n" in st[k]:
                    st[k] = _LiteralStr(st[k])
    return yaml.dump(
        payload,
        Dumper=_PlanYamlDumper,
        sort_keys=False,
        allow_unicode=True,
        width=100,
    )


def _inline_md_to_html(text: str) -> str:
    esc = html_mod.escape(str(text or ""))
    esc = re.sub(r"`([^`]+)`", r"<code>\1</code>", esc)
    esc = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", esc)
    esc = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", esc)
    esc = esc.replace("[NEW]", '<span class="badge b-new">NEW</span>')
    esc = esc.replace("[MODIFY]", '<span class="badge b-mod">MODIFY</span>')
    esc = esc.replace("[DELETE]", '<span class="badge b-del">DELETE</span>')
    esc = esc.replace("[RENAME]", '<span class="badge b-info">RENAME</span>')
    esc = esc.replace("[TEST]", '<span class="badge b-test">TEST</span>')
    return esc


def _simple_markdown_to_html(md: str) -> str:
    """Lightweight offline-safe Markdown -> HTML converter for standalone HTML plan reports."""
    lines = str(md or "").replace("\r\n", "\n").splitlines()
    out: List[str] = []
    in_code = False
    code_buf: List[str] = []
    in_ul = False

    def close_ul():
        nonlocal in_ul
        if in_ul:
            out.append("</ul>")
            in_ul = False

    for line in lines:
        if line.strip().startswith("```"):
            close_ul()
            if not in_code:
                in_code = True
                code_buf = []
            else:
                out.append("<pre><code>" + html_mod.escape("\n".join(code_buf)) + "</code></pre>")
                in_code = False
                code_buf = []
            continue
        if in_code:
            code_buf.append(line)
            continue

        stripped = line.strip()
        if not stripped:
            close_ul()
            continue

        hm = re.match(r"^(#{1,4})\s+(.+)$", stripped)
        if hm:
            close_ul()
            lvl = min(4, len(hm.group(1)))
            out.append(f"<h{lvl}>{_inline_md_to_html(hm.group(2))}</h{lvl}>")
            continue

        bm = re.match(r"^[-*•]\s+(.+)$", stripped)
        if bm:
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{_inline_md_to_html(bm.group(1))}</li>")
            continue

        close_ul()
        out.append(f"<p>{_inline_md_to_html(stripped)}</p>")

    if in_code and code_buf:
        out.append("<pre><code>" + html_mod.escape("\n".join(code_buf)) + "</code></pre>")
    close_ul()
    return "\n".join(out)


def _serialize_html_export(plan: Dict[str, Any]) -> str:
    """Render a standalone, print-friendly Hecos HTML report with embedded lossless JSON."""
    payload = _build_canonical_payload(plan)
    p = payload["plan"]
    prog = compute_plan_progress(p)
    title_esc = html_mod.escape(p["title"])
    status_esc = html_mod.escape(str(p.get("status") or "awaiting_approval").replace("_", " ").title())
    rev = int(p.get("revision") or 1)
    exported_at = html_mod.escape(payload["exported_at"][:19].replace("T", " ") + " UTC")

    plan_for_body = dict(p)
    if plan_for_body.get("plan_markdown"):
        plan_for_body["plan_markdown"] = _strip_checklist_section(plan_for_body["plan_markdown"])
    body_md = build_plan_markdown_document(plan_for_body, include_step_checklist=False)
    blueprint_html = _simple_markdown_to_html(body_md)

    step_rows: List[str] = []
    for idx, s in enumerate(p.get("steps") or [], start=1):
        st = str(s.get("status") or "pending").lower()
        icon = "✓" if st == "done" else ("−" if st == "skipped" else ("✗" if st == "failed" else "○"))
        st_cls = f"st-{html_mod.escape(st)}"
        files_html = ""
        if s.get("files"):
            chips = "".join(f'<span class="file-chip">{_inline_md_to_html(f)}</span>' for f in s["files"])
            files_html = f'<div class="step-files">{chips}</div>'
        details_html = f'<div class="step-details">{html_mod.escape(s["details"])}</div>' if s.get("details") else ""
        notes_html = f'<div class="step-notes">Note: {html_mod.escape(s["notes"])}</div>' if s.get("notes") else ""
        step_rows.append(
            f'<div class="step {st_cls}">'
            f'<span class="step-icon">{icon}</span>'
            f'<div class="step-body">'
            f'<div class="step-title"><strong>{int(s.get("index") or idx)}.</strong> {html_mod.escape(str(s.get("title") or ""))}</div>'
            f'{files_html}{details_html}{notes_html}'
            f'</div></div>'
        )
    steps_html = "\n".join(step_rows)

    embedded_json = json.dumps(payload, indent=2, ensure_ascii=False).replace("</", "<\\/")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title_esc} — Hecos Action Plan</title>
  <style>
    :root {{ --bg: #020617; --card: #0f172a; --border: rgba(56,189,248,0.28); --text: #e2e8f0; --muted: #94a3b8; --accent: #38bdf8; --ok: #10b981; --warn: #f59e0b; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; padding: 28px 18px; background: var(--bg); color: var(--text); font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.55; }}
    .wrap {{ max-width: 960px; margin: 0 auto; display: flex; flex-direction: column; gap: 18px; }}
    .header {{ background: var(--card); border: 1px solid var(--border); border-radius: 14px; padding: 18px 22px; }}
    .pills {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 8px; }}
    .pill {{ font-size: 11px; font-weight: 700; text-transform: uppercase; padding: 3px 9px; border-radius: 999px; background: rgba(56,189,248,0.16); border: 1px solid rgba(56,189,248,0.45); color: #7dd3fc; }}
    .pill-rev {{ background: rgba(139,92,246,0.18); border-color: rgba(167,139,250,0.45); color: #ddd6fe; }}
    h1 {{ margin: 0 0 8px; font-size: 22px; }}
    .meta {{ font-size: 12px; color: var(--muted); }}
    .progress {{ height: 6px; border-radius: 999px; background: rgba(148,163,184,0.2); overflow: hidden; margin-top: 12px; }}
    .progress-fill {{ height: 100%; background: linear-gradient(90deg, var(--accent), var(--ok)); width: {prog["percent"]}%; }}
    .panel {{ background: var(--card); border: 1px solid rgba(148,163,184,0.2); border-radius: 14px; padding: 18px 22px; }}
    .panel > h2 {{ margin: 0 0 12px; font-size: 15px; color: #7dd3fc; border-bottom: 1px solid rgba(148,163,184,0.16); padding-bottom: 8px; }}
    .step {{ display: flex; gap: 10px; padding: 8px 10px; border-radius: 8px; border: 1px solid rgba(148,163,184,0.14); margin-bottom: 8px; background: rgba(2,6,23,0.35); }}
    .step.st-done {{ opacity: 0.78; border-color: rgba(16,185,129,0.32); }}
    .step-icon {{ font-weight: 700; min-width: 18px; text-align: center; color: var(--muted); }}
    .step.st-done .step-icon {{ color: var(--ok); }}
    .step-body {{ flex: 1; min-width: 0; }}
    .step-files {{ display: flex; flex-wrap: wrap; gap: 5px; margin-top: 5px; }}
    .file-chip {{ font-size: 11px; padding: 2px 7px; border-radius: 6px; background: rgba(30,41,59,0.85); border: 1px solid rgba(148,163,184,0.28); font-family: ui-monospace, Consolas, monospace; }}
    .step-details {{ font-size: 12.5px; color: var(--muted); margin-top: 4px; }}
    .step-notes {{ font-size: 12px; color: #7dd3fc; margin-top: 3px; font-style: italic; }}
    .blueprint h1, .blueprint h2, .blueprint h3 {{ color: #f1f5f9; margin-top: 16px; }}
    .blueprint code {{ background: rgba(2,6,23,0.7); padding: 1px 5px; border-radius: 4px; font-family: ui-monospace, Consolas, monospace; font-size: 0.92em; }}
    .blueprint pre {{ background: #020617; padding: 12px; border-radius: 8px; overflow-x: auto; border: 1px solid rgba(148,163,184,0.2); }}
    .badge {{ display: inline-block; font-size: 10px; font-weight: 700; padding: 1px 5px; border-radius: 4px; margin-right: 4px; }}
    .b-new {{ background: rgba(16,185,129,0.2); color: #6ee7b7; border: 1px solid rgba(16,185,129,0.45); }}
    .b-mod {{ background: rgba(245,158,11,0.2); color: #fcd34d; border: 1px solid rgba(245,158,11,0.45); }}
    .b-del {{ background: rgba(239,68,68,0.2); color: #fca5a5; border: 1px solid rgba(239,68,68,0.45); }}
    .b-info {{ background: rgba(56,189,248,0.2); color: #7dd3fc; border: 1px solid rgba(56,189,248,0.45); }}
    .b-test {{ background: rgba(139,92,246,0.2); color: #ddd6fe; border: 1px solid rgba(167,139,250,0.45); }}
    .footer {{ text-align: center; font-size: 11.5px; color: var(--muted); }}
    @media print {{
      body {{ background: #fff; color: #0f172a; padding: 0; }}
      .header, .panel, .step {{ background: #fff; color: #0f172a; border-color: #cbd5e1; }}
      .panel > h2, .blueprint h1, .blueprint h2, .blueprint h3 {{ color: #0f172a; }}
      .step-details, .meta, .footer {{ color: #475569; }}
      .blueprint pre, .blueprint code, .file-chip {{ background: #f1f5f9; color: #0f172a; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <header class="header">
      <div class="pills">
        <span class="pill">{status_esc}</span>
        <span class="pill pill-rev">v{rev}</span>
      </div>
      <h1>{title_esc}</h1>
      <div class="meta">Progress: {prog["done"]}/{prog["total"]} ({prog["percent"]}%) &middot; Exported {exported_at}</div>
      <div class="progress"><div class="progress-fill"></div></div>
    </header>
    <section class="panel">
      <h2>Execution Checklist</h2>
      {steps_html}
    </section>
    <section class="panel blueprint">
      <h2>Plan Blueprint</h2>
      {blueprint_html}
    </section>
    <div class="footer">Hecos Action Plan Report &middot; Re-importable directly into Hecos Chat</div>
  </div>
  <script type="application/json" id="hecos-plan-data">
{embedded_json}
  </script>
</body>
</html>
"""


def serialize_plan_for_export(plan: Dict[str, Any], fmt: str = "md") -> Tuple[str, str, str]:
    """
    Serialize an Action Plan into (content_text, mime_type, suggested_filename).
    Supports:
      - fmt='md' (default): Human-readable Markdown with clean YAML frontmatter & checklist
      - fmt='html': Standalone visual/printable HTML report with embedded lossless JSON
      - fmt='yaml': Clean multiline YAML, 100% lossless
      - fmt='json': Lossless .hecos-plan.json
    """
    if not isinstance(plan, dict):
        raise ValueError("Invalid plan object")

    eff = normalize_export_format(fmt)
    filename = suggest_plan_filename(plan, eff)

    if eff == "md":
        return _serialize_markdown_export(plan), "text/markdown; charset=utf-8", filename
    if eff == "html":
        return _serialize_html_export(plan), "text/html; charset=utf-8", filename
    if eff == "yaml":
        return _serialize_yaml_export(plan), "application/x-yaml; charset=utf-8", filename

    payload = _build_canonical_payload(plan)
    json_text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    return json_text, "application/json; charset=utf-8", filename


def _extract_section(md: str, heading_keywords: Tuple[str, ...]) -> str:
    """Extract body of the first level-2 Markdown section matching any keyword."""
    lines = md.splitlines()
    capturing = False
    collected: List[str] = []
    for line in lines:
        m = re.match(r"^\s*##\s+(.+?)\s*$", line)
        if m:
            if capturing:
                break
            heading = m.group(1).strip().lower()
            if any(k in heading for k in heading_keywords):
                capturing = True
                continue
        elif capturing:
            collected.append(line)
    return "\n".join(collected).strip()


def _extract_file_tags(text: str) -> List[str]:
    found: List[str] = []
    seen = set()
    for m in _FILE_TAG_RE.finditer(text or ""):
        tag = m.group("tag").upper()
        path = m.group("path").strip().strip("`").strip("*").strip()
        if not path:
            continue
        item = f"[{tag}] {path}"
        if item not in seen:
            seen.add(item)
            found.append(item)
    return found


def _strip_step_prefix(text: str) -> str:
    clean = str(text or "").strip()
    clean = re.sub(r"^\*\*Step\s+\d+[:.)]?\*\*\s*", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"^Step\s+\d+[:.)]\s*", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"^\*\*(.+?)\*\*\s*(?:—|-|:)\s*", r"\1 — ", clean)
    return clean.strip()


def _parse_frontmatter(raw: str) -> Tuple[Dict[str, Any], str]:
    """Extract optional leading YAML frontmatter (`--- ... ---`) and return (meta, body)."""
    m = _FRONTMATTER_RE.match(raw)
    if not m:
        return {}, raw
    try:
        parsed = yaml.safe_load(m.group("yaml"))
        meta = parsed if isinstance(parsed, dict) else {}
    except Exception:
        meta = {}
    return meta, raw[m.end():].strip()


def _parse_markdown_plan(md_text: str, filename: str = "") -> Dict[str, Any]:
    """Parse a Markdown Action Plan (Hecos frontmatter or external/Antigravity MD) into structured fields."""
    raw_full = str(md_text or "").replace("\r\n", "\n").strip()
    if not raw_full:
        raise ValueError("Markdown file is empty")

    fm, raw = _parse_frontmatter(raw_full)
    if not raw:
        raise ValueError("Markdown file has no content body")

    # 1. Title from frontmatter or first H1 heading or filename stem
    title = str(fm.get("title") or "").strip()
    if not title:
        for line in raw.splitlines():
            m = re.match(r"^\s*#\s+(.+?)\s*$", line)
            if m:
                title = m.group(1).strip()
                title = re.sub(r"\s*(?:\*\(v\d+\)\*|·\s*\*\*v\d+\*\*|\(v\d+\))\s*$", "", title).strip()
                break
    if not title:
        stem = os.path.splitext(os.path.basename(filename or ""))[0]
        title = re.sub(r"[_\-]+", " ", stem).strip().title() or "Imported Action Plan"

    try:
        revision = max(1, int(fm.get("revision") or 1))
    except Exception:
        revision = 1

    # 2. Goal & Verification sections
    goal = _extract_section(raw, ("goal", "obiettivo", "overview", "scopo", "summary"))
    verification = _extract_section(raw, ("verification", "verifica", "testing", "test plan", "consistency checks"))

    # 3. Extract steps from Execution Checklist (supporting indented Files/Details/Notes),
    #    or checkbox bullets, or ### headings, or numbered lists.
    steps: List[Dict[str, Any]] = []

    checklist_sec = _extract_section(raw, ("execution checklist", "checklist", "steps", "piano", "tasks"))
    scan_source = checklist_sec if checklist_sec else raw

    # Pass A: Markdown task checkboxes (- [ ] / - [x]) with optional indented sub-bullets
    cur_cb: Optional[Dict[str, Any]] = None
    for line in scan_source.splitlines():
        m = _CHECKBOX_RE.match(line)
        if m:
            if cur_cb:
                steps.append(cur_cb)
            mark = m.group("mark").lower()
            body = _strip_step_prefix(m.group("text"))
            if not body:
                cur_cb = None
                continue
            status = "done" if mark == "x" else ("skipped" if mark in ("-", "~") else "pending")
            files = _extract_file_tags(body)
            clean_title = _FILE_TAG_RE.sub("", body).strip(" —-:")
            if not clean_title:
                clean_title = body
            cur_cb = {
                "title": clean_title[:280],
                "status": status,
                "files": files,
                "details": "",
                "notes": "",
            }
            continue

        if cur_cb is not None and re.match(r"^\s{2,}[-*•]\s+", line):
            sub_txt = re.sub(r"^\s*[-*•]\s+", "", line).strip()
            fm_sub = re.match(r"^\*\*Files:\*\*\s*(.+)$", sub_txt, re.IGNORECASE)
            dm_sub = re.match(r"^\*\*Details:\*\*\s*(.+)$", sub_txt, re.IGNORECASE)
            nm_sub = re.match(r"^\*\*Notes?:\*\*\s*(.+)$", sub_txt, re.IGNORECASE)
            if fm_sub:
                raw_files = fm_sub.group(1)
                tagged = _extract_file_tags(raw_files)
                if tagged:
                    for f in tagged:
                        if f not in cur_cb["files"]:
                            cur_cb["files"].append(f)
                else:
                    for tok in re.findall(r"`([^`]+)`", raw_files):
                        if tok.strip() and tok.strip() not in cur_cb["files"]:
                            cur_cb["files"].append(tok.strip())
            elif dm_sub:
                cur_cb["details"] = dm_sub.group(1).strip()[:1200]
            elif nm_sub:
                cur_cb["notes"] = nm_sub.group(1).strip().strip("*")[:800]
            else:
                for f in _extract_file_tags(sub_txt):
                    if f not in cur_cb["files"]:
                        cur_cb["files"].append(f)
    if cur_cb:
        steps.append(cur_cb)

    # Pass B: ### headings (common in Antigravity / Hecos Proposed Changes / Shot Sequences)
    if not steps:
        lines = raw.splitlines()
        cur_step: Optional[Dict[str, Any]] = None
        in_verif = False
        for line in lines:
            h2 = re.match(r"^\s*##\s+(.+?)\s*$", line)
            if h2:
                if cur_step:
                    steps.append(cur_step)
                    cur_step = None
                h2_low = h2.group(1).strip().lower()
                in_verif = any(k in h2_low for k in ("verification", "verifica", "goal", "obiettivo"))
                continue
            if in_verif:
                continue
            hm = _HEADING_STEP_RE.match(line)
            if hm:
                if cur_step:
                    steps.append(cur_step)
                heading_text = _strip_step_prefix(hm.group("text"))
                cur_step = {
                    "title": heading_text[:280],
                    "status": "pending",
                    "files": _extract_file_tags(heading_text),
                    "details": "",
                }
                continue
            if cur_step is not None:
                found_files = _extract_file_tags(line)
                if found_files:
                    for f in found_files:
                        if f not in cur_step["files"]:
                            cur_step["files"].append(f)
                stripped = line.strip()
                if stripped and not stripped.startswith("```") and not cur_step["details"]:
                    plain = re.sub(r"^[-*•]\s*", "", stripped)
                    plain = re.sub(r"^\*\*(?:Details|Files|Note|Notes)\s*:\*\*\s*", "", plain, flags=re.IGNORECASE)
                    if plain and not _FILE_TAG_RE.match(plain):
                        cur_step["details"] = plain[:400]
        if cur_step:
            steps.append(cur_step)

    # Pass C: Numbered lines (1. ..., 2. ...)
    if not steps:
        for line in scan_source.splitlines():
            m = _NUMBERED_RE.match(line)
            if not m:
                continue
            body = _strip_step_prefix(m.group("text"))
            if body:
                steps.append({
                    "title": body[:280],
                    "status": "pending",
                    "files": _extract_file_tags(body),
                })

    # Pass D: Fallback single step so any valid Markdown document imports cleanly
    if not steps:
        steps = [{
            "title": f"Implement {title}",
            "status": "pending",
            "files": _extract_file_tags(raw)[:8],
            "details": goal[:300] if goal else "",
        }]

    # Keep clean blueprint Markdown without duplicated Execution Checklist tail if body exists above it
    stripped_body = _strip_checklist_section(raw)
    clean_blueprint = stripped_body if stripped_body else raw

    return {
        "title": title[:220],
        "goal": goal[:1500],
        "plan_markdown": clean_blueprint[:24000],
        "verification_plan": verification[:3000],
        "revision": revision,
        "revision_history": [],
        "steps": normalize_steps(steps),
        "metadata": {"imported_format": "md"},
    }


def _sanitize_imported_steps(raw_steps: Any, reset_progress: bool = False) -> List[Dict[str, Any]]:
    steps = normalize_steps(raw_steps)
    if not steps:
        return []
    all_finished = all(s.get("status") in ("done", "skipped") for s in steps)
    for st in steps:
        if reset_progress or all_finished:
            st["status"] = "pending"
        else:
            norm = normalize_step_status(st.get("status"))
            st["status"] = "pending" if norm in ("running", "failed") else norm
    return steps


def _parse_structured_dict(
    data: Dict[str, Any],
    *,
    filename: str = "",
    imported_format: str = "json",
    reset_progress: bool = False,
) -> Dict[str, Any]:
    plan_obj = data.get("plan") if isinstance(data.get("plan"), dict) else data
    title = str(plan_obj.get("title") or "").strip()
    goal = str(plan_obj.get("goal") or "").strip()
    plan_md = str(plan_obj.get("plan_markdown") or "").strip()
    verif = str(plan_obj.get("verification_plan") or "").strip()
    raw_steps = plan_obj.get("steps")
    steps = _sanitize_imported_steps(raw_steps, reset_progress=reset_progress)

    if not steps and plan_md:
        parsed_md = _parse_markdown_plan(plan_md, filename=filename)
        steps = _sanitize_imported_steps(parsed_md["steps"], reset_progress=reset_progress)
        if not title:
            title = parsed_md["title"]
        if not goal:
            goal = parsed_md["goal"]
        if not verif:
            verif = parsed_md["verification_plan"]

    if not steps:
        raise ValueError(f"{imported_format.upper()} plan contains no steps and no parseable plan_markdown")

    if not title:
        stem = os.path.splitext(os.path.basename(filename or ""))[0]
        stem = re.sub(r"\.hecos-plan$", "", stem, flags=re.IGNORECASE)
        title = re.sub(r"[_\-]+", " ", stem).strip().title() or "Imported Action Plan"

    rev = max(1, int(plan_obj.get("revision") or 1))
    history = list(plan_obj.get("revision_history") or [])
    meta = dict(plan_obj.get("metadata") or {})
    meta["imported_format"] = imported_format
    if plan_obj.get("plan_id"):
        meta["imported_source_plan_id"] = str(plan_obj.get("plan_id"))

    return {
        "title": title[:220],
        "goal": goal[:1500],
        "plan_markdown": plan_md[:24000],
        "verification_plan": verif[:3000],
        "revision": rev,
        "revision_history": history[-20:],
        "steps": steps,
        "metadata": meta,
    }


def _parse_html_plan(html_text: str, *, filename: str = "", reset_progress: bool = False) -> Dict[str, Any]:
    """Parse an exported Hecos HTML report (lossless via embedded JSON) or generic HTML fallback."""
    m = _HTML_EMBEDDED_JSON_RE.search(html_text or "")
    if m:
        raw_json = m.group("json").strip().replace("<\\/", "</")
        try:
            data = json.loads(raw_json)
            if isinstance(data, dict):
                return _parse_structured_dict(
                    data,
                    filename=filename,
                    imported_format="html",
                    reset_progress=reset_progress,
                )
        except Exception as exc:
            raise ValueError(f"Corrupted embedded Hecos plan data in HTML: {exc}") from exc

    # Fallback: parse arbitrary HTML document headings & list items
    title_m = re.search(r"<h1[^>]*>(.*?)</h1>", html_text, re.IGNORECASE | re.DOTALL)
    title = html_mod.unescape(re.sub(r"<[^>]+>", "", title_m.group(1))).strip() if title_m else ""
    li_items = [
        html_mod.unescape(re.sub(r"<[^>]+>", "", x)).strip()
        for x in re.findall(r"<li[^>]*>(.*?)</li>", html_text, re.IGNORECASE | re.DOTALL)
    ]
    li_items = [x for x in li_items if x]
    md_synth = f"# {title or 'Imported HTML Plan'}\n\n" + "\n".join(f"- [ ] {x}" for x in li_items)
    parsed = _parse_markdown_plan(md_synth, filename=filename)
    parsed["steps"] = _sanitize_imported_steps(parsed["steps"], reset_progress=reset_progress)
    parsed["metadata"]["imported_format"] = "html"
    return parsed


def parse_imported_plan_content(
    content: str,
    *,
    filename: str = "",
    reset_progress: bool = False,
) -> Dict[str, Any]:
    """
    Parse an imported Action Plan from Markdown (.md), HTML (.html), YAML (.yaml/.yml), or JSON (.json).
    Raises ValueError with a clear message if the content is empty or malformed.
    """
    text = str(content or "").lstrip("\ufeff").strip()
    if not text:
        raise ValueError("Imported plan file is empty")

    ext = os.path.splitext(filename or "")[1].lower()

    # 1. HTML (.html / .htm or embedded hecos-plan-data / <!DOCTYPE html>)
    if ext in (".html", ".htm") or text.lower().startswith(("<!doctype html", "<html")) or _HTML_EMBEDDED_JSON_RE.search(text):
        return _parse_html_plan(text, filename=filename, reset_progress=reset_progress)

    # 2. JSON (.json or starts with '{')
    if ext == ".json" or text.startswith("{"):
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            if ext == ".json":
                raise ValueError(f"Invalid JSON plan file: {exc}") from exc
            data = None
        if isinstance(data, dict):
            return _parse_structured_dict(
                data,
                filename=filename,
                imported_format="json",
                reset_progress=reset_progress,
            )

    # 3. YAML (.yaml / .yml)
    if ext in (".yaml", ".yml"):
        try:
            data = yaml.safe_load(text)
        except Exception as exc:
            raise ValueError(f"Invalid YAML plan file: {exc}") from exc
        if not isinstance(data, dict):
            raise ValueError("YAML plan file must contain a mapping object")
        return _parse_structured_dict(
            data,
            filename=filename,
            imported_format="yaml",
            reset_progress=reset_progress,
        )

    # 4. Markdown (.md or general text)
    parsed = _parse_markdown_plan(text, filename=filename)
    parsed["steps"] = _sanitize_imported_steps(parsed["steps"], reset_progress=reset_progress)
    return parsed
