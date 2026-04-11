import os
from flask import render_template, request, abort, jsonify
from flask_login import login_required, current_user
from zentra.core.auth.decorators import admin_required

def init_docs_routes(app, root_dir, logger):
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
        
        # 1. Try full language file first: chapter_it.md, chapter_en.md
        lang_path = os.path.join(group_dir, f"{chapter_id}_{lang}.md")
        if os.path.exists(lang_path):
            with open(lang_path, "r", encoding="utf-8") as f:
                return f.read()

        # 2. If lang is 'en', try the bare file: chapter.md
        if lang == 'en':
            base_path = os.path.join(group_dir, f"{chapter_id}.md")
            if os.path.exists(base_path):
                with open(base_path, "r", encoding="utf-8") as f:
                    return f.read()
        
        # 3. Fallback to bare file chapter.md for any other language if missing
        base_path = os.path.join(group_dir, f"{chapter_id}.md")
        if os.path.exists(base_path):
            with open(base_path, "r", encoding="utf-8") as f:
                return f.read()
            
        # 4. Ultimate fallback to chapter_en.md if even bare file is missing
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
