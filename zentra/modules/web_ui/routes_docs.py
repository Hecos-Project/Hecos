import os
import json
from flask import render_template, request, abort, jsonify
from flask_login import login_required, current_user
from zentra.core.auth.decorators import admin_required

def init_docs_routes(app, cfg_mgr, root_dir, logger):
    """Modular Documentation routes."""

    def list_chapters(group, lang='en'):
        """Scans the directory for chapters and returns a unique localized list."""
        group_dir = os.path.join(root_dir, "docs", group)
        if not os.path.isdir(group_dir):
            return []
        
        all_files = [f for f in os.listdir(group_dir) if f.endswith(".md")]
        
        unique_cids = set()
        for f in all_files:
            cid = f[:-3]
            for l in ['_en', '_it', '_es']:
                if cid.endswith(l):
                    cid = cid[:-3]
                    break
            unique_cids.add(cid)
        
        final_list = [cid for cid in sorted(unique_cids) if cid[:2].isdigit()]
        
        chapters = []
        for cid in final_list:
            # 1. Try to get title from localized file
            title = None
            # Priority: 1. specific language, 2. bare file, 3. english fallback
            search_files = [f"{cid}_{lang}.md", f"{cid}.md"]
            if lang != 'en':
                search_files.append(f"{cid}_en.md")

            for sf in search_files:
                p = os.path.join(group_dir, sf)
                if os.path.exists(p):
                    try:
                        with open(p, "r", encoding="utf-8") as f:
                            for line in f:
                                clean_line = line.strip()
                                if clean_line.startswith("#"):
                                    title = clean_line.lstrip("#").strip()
                                    break
                        if title: break
                    except: pass
            
            if not title:
                # Fallback to CID transformation
                name = cid.replace("_", " ").title()
                if cid[:2].isdigit():
                    prefix = cid[:2].lstrip('0') or "0"
                    rest = cid[3:].replace("_", " ").title()
                    title = f"{prefix}. {rest}"
                else:
                    title = name
                
            chapters.append({"id": cid, "name": title})
        return chapters

    def get_chapter_content(group, chapter_id, lang='en'):
        """Fetches chapter content with language fallback."""
        group_dir = os.path.join(root_dir, "docs", group)
        
        # 1. Try requested language first: chapter_it.md, chapter_en.md, etc.
        lang_path = os.path.join(group_dir, f"{chapter_id}_{lang}.md")
        if os.path.exists(lang_path):
            with open(lang_path, "r", encoding="utf-8") as f:
                return f.read()

        # 2. Try bare file as a generic fallback (if exists)
        base_path = os.path.join(group_dir, f"{chapter_id}.md")
        if os.path.exists(base_path):
            with open(base_path, "r", encoding="utf-8") as f:
                return f.read()

        # 3. Ultimate selection: fallback to English version (_en.md) if everything else fails
        if lang != 'en':
            en_path = os.path.join(group_dir, f"{chapter_id}_en.md")
            if os.path.exists(en_path):
                with open(en_path, "r", encoding="utf-8") as f:
                    return f.read()

        return None

    @app.route("/zentra/docs")
    @login_required
    def docs_ui():
        group = request.args.get("group", "user")
        chapter = request.args.get("chapter", "")
        lang = request.args.get("lang", "en")
        
        if group == "tech" and not (current_user.is_authenticated and current_user.role == 'admin'):
            abort(403)
            
        chapters = list_chapters(group, lang)
        if not chapter and chapters:
            chapter = chapters[0]['id']
            
        return render_template("docs.html", 
                             group=group, 
                             initial_chapter=chapter, 
                             lang=lang, 
                             zconfig=cfg_mgr.config,
                             page_title="Zentra Documentation")

    @app.route("/api/docs/list/<group>")
    @login_required
    def api_docs_list(group):
        if group == "tech" and not (current_user.is_authenticated and current_user.role == 'admin'):
            return jsonify({"error": "Admin required"}), 403
        lang = request.args.get("lang", "en")
        return jsonify(list_chapters(group, lang))

    @app.route("/api/docs/content/<group>/<chapter>")
    @login_required
    def api_docs_content(group, chapter):
        if group == "tech" and not (current_user.is_authenticated and current_user.role == 'admin'):
            return jsonify({"error": "Admin required"}), 403
            
        lang = request.args.get("lang", "en")
        content = get_chapter_content(group, chapter, lang)
        if content is None:
            return jsonify({"error": "Chapter not found"}), 404
            
        return jsonify({"content": content})

    @app.route("/api/docs/unified/generate")
    @login_required
    def api_docs_unified_generate():
        """Aggregates all chapters into a single downloadable HTML manual."""
        group = request.args.get("group", "user")
        lang = request.args.get("lang", "en")
        
        if group == "tech" and not (current_user.is_authenticated and current_user.role == 'admin'):
            abort(403)
            
        chapters = list_chapters(group, lang)
        combined_md = f"# Zentra Core - Unified {group.title()} Guide\n\n"
        
        for ch in chapters:
            content = get_chapter_content(group, ch['id'], lang)
            if content:
                # Add horizontal rule between chapters
                combined_md += f"\n\n---\n\n{content}\n"
        
        # We wrap the combined markdown in a basic standalone HTML with a Print/Save style
        title = f"Zentra_{group}_{lang}_Master_Manual"
        
        html_output = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{ font-family: 'Inter', sans-serif; line-height: 1.6; max-width: 900px; margin: 0 auto; padding: 60px 40px; color: #1e293b; background: #fff; }}
        h1 {{ color: #2563eb; border-bottom: 3px solid #e2e8f0; padding-bottom: 12px; margin-bottom: 30px; font-weight: 800; }}
        h2 {{ color: #1e293b; margin-top: 50px; border-bottom: 1px solid #f1f5f9; padding-bottom: 8px; font-weight: 700; }}
        h3 {{ color: #334155; margin-top: 35px; }}
        pre {{ background: #0f172a; color: #f8fafc; padding: 20px; border-radius: 12px; overflow-x: auto; margin: 25px 0; border: 1px solid #1e293b; }}
        code {{ background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-family: 'JetBrains Mono', monospace; font-size: 0.9em; color: #ef4444; }}
        pre code {{ background: transparent; padding: 0; color: inherit; }}
        blockquote {{ border-left: 4px solid #2563eb; background: #eff6ff; margin: 30px 0; padding: 15px 30px; color: #64748b; font-style: italic; }}
        hr {{ border: 0; border-top: 1px solid #e2e8f0; margin: 50px 0; }}
        table {{ width: 100%; border-collapse: collapse; margin: 30px 0; }}
        th, td {{ border: 1px solid #e2e8f0; padding: 12px; text-align: left; }}
        th {{ background: #f8fafc; color: #1e293b; }}
        img {{ max-width: 100%; height: auto; border-radius: 8px; margin: 30px 0; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
        .no-print {{ display: block; position: sticky; top: 0; z-index: 1000; background: #fef9c3; border: 1px solid #fde047; padding: 12px; margin-bottom: 40px; border-radius: 8px; text-align: center; font-size: 14px; font-weight: 600; color: #854d0e; }}
        @media print {{ .no-print {{ display: none; }} body {{ padding: 0; }} }}
    </style>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
</head>
<body>
    <div class="no-print" style="background:#fff9c4; padding:10px; border:1px solid #fbc02d; margin-bottom:20px; border-radius:5px;">
        <b>Unified View Generated Successfully.</b> Use Ctrl+P to save as PDF.
    </div>
    <div id="content"></div>
    <script>
        document.getElementById('content').innerHTML = marked.parse({json.dumps(combined_md)});
    </script>
</body>
</html>"""
        return html_output

    @app.route("/api/docs/search")
    @login_required
    def api_docs_search():
        group = request.args.get("group", "user")
        query = request.args.get("query", "").strip().lower()
        lang = request.args.get("lang", "en")
        
        if not query:
            return jsonify([])
            
        if group == "tech" and not (current_user.is_authenticated and current_user.role == 'admin'):
            return jsonify({"error": "Admin required"}), 403
            
        chapters = list_chapters(group, lang)
        results = []
        
        for ch in chapters:
            content = get_chapter_content(group, ch['id'], lang)
            if not content: continue
            
            # Simple case-insensitive search
            text = content.lower()
            idx = text.find(query)
            if idx != -1:
                # Extract a snippet
                start = max(0, idx - 40)
                end = min(len(content), idx + len(query) + 60)
                snippet = content[start:end].replace("\n", " ").strip()
                if start > 0: snippet = "..." + snippet
                if end < len(content): snippet = snippet + "..."
                
                results.append({
                    "id": ch['id'],
                    "title": ch['name'],
                    "snippet": snippet
                })
                
        return jsonify(results)
