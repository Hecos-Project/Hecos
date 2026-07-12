"""
MODULE: Mail API
DESCRIPTION: Flask REST endpoints for the Mail plugin.
             Registered at boot via on_load() in main.py or directly from the WebUI module.

Endpoints:
    GET  /api/mail/messages                  list/search messages
    GET  /api/mail/messages/<id>             single message
    POST /api/mail/send                      send email
    POST /api/mail/reply/<id>                reply to message
    POST /api/mail/forward/<id>              forward message
    PUT  /api/mail/messages/<id>             update (read, starred, folder)
    DEL  /api/mail/messages/<id>             delete
    POST /api/mail/sync                      sync folder from IMAP
    GET  /api/mail/stats                     per-folder counts
    GET  /api/mail/drafts                    list drafts
    POST /api/mail/drafts                    save draft
    PUT  /api/mail/drafts/<id>               update draft
    DEL  /api/mail/drafts/<id>               delete draft
    POST /api/mail/test-account              test SMTP+IMAP connection
    GET  /api/mail/folders                   list IMAP folders
    PUT  /api/mail/account-password          update app password
    GET  /api/mail/config                    read MAIL plugin config
    PUT  /api/mail/config                    write MAIL plugin config
"""

from flask import Blueprint, request, jsonify
from hecos.core.logging import logger

mail_bp = Blueprint("mail", __name__, url_prefix="/api/mail")


def register_routes(app):
    """Registers the mail blueprint on the Flask app (idempotent)."""
    if "mail" not in app.blueprints:
        app.register_blueprint(mail_bp)
        logger.debug("MAIL", "API blueprint registered at /api/mail")


def _get_cfg() -> dict:
    """Returns the current MAIL plugin config."""
    try:
        from .mail_config.config_manager import get_config
        return get_config()
    except Exception:
        return {}


def _get_username() -> str:
    """Returns the currently logged-in username."""
    try:
        from flask_login import current_user
        return getattr(current_user, "username", "admin")
    except Exception:
        return "admin"


# â”€â”€ Messages â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@mail_bp.route("/messages", methods=["GET"])
def list_messages():
    from hecos.hpm.mail import store
    folder      = request.args.get("folder", "INBOX").upper()
    limit       = int(request.args.get("limit", 50))
    unread_only = request.args.get("unread", "false").lower() == "true"
    starred     = request.args.get("starred", "false").lower() == "true"
    query       = request.args.get("q", "").strip()
    try:
        if query:
            items = store.search_messages(query=query, folder=folder if folder != "ALL" else None, limit=limit)
        else:
            items = store.list_folder(folder=folder, limit=limit,
                                      unread_only=unread_only, starred_only=starred)
        return jsonify({"ok": True, "messages": items, "count": len(items), "folder": folder})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@mail_bp.route("/messages/<message_id>", methods=["GET"])
def get_message(message_id):
    from hecos.hpm.mail import store
    msg = store.get_message(message_id)
    if not msg:
        return jsonify({"ok": False, "error": "Message not found"}), 404
    # Auto-mark as read when fetched
    if not msg.get("read"):
        store.mark_read(message_id, True)
        msg["read"] = True
    return jsonify({"ok": True, "message": msg})


@mail_bp.route("/messages/<message_id>", methods=["PUT"])
def update_message(message_id):
    from hecos.hpm.mail import store
    data = request.get_json(force=True) or {}
    try:
        if "read" in data:
            store.mark_read(message_id, bool(data["read"]))
        if "starred" in data:
            store.mark_starred(message_id, bool(data["starred"]))
        if "folder" in data:
            store.move_message(message_id, data["folder"].upper())
        return jsonify({"ok": True, "message": store.get_message(message_id)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@mail_bp.route("/messages/<message_id>", methods=["DELETE"])
def delete_message(message_id):
    from hecos.hpm.mail import store
    permanent = request.args.get("permanent", "false").lower() == "true"
    if permanent:
        ok = store.delete_message(message_id)
    else:
        ok = store.move_message(message_id, "TRASH")
    if ok:
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "Message not found"}), 404


# â”€â”€ Send / Reply / Forward â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@mail_bp.route("/send", methods=["POST"])
def send_email():
    data = request.get_json(force=True) or {}
    to      = data.get("to", "")
    subject = data.get("subject", "")
    body    = data.get("body", "")
    is_html = data.get("is_html", False)

    # â”€â”€ Template rendering (optional) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    template_id   = data.get("template_id", "").strip()
    template_vars = data.get("template_vars", {})
    if template_id:
        try:
            from hecos.plugins.templates import store as tpl_store
            rendered = tpl_store.render_template(template_id, template_vars)
            subject  = rendered.get("subject")   or subject
            # Prefer HTML body when available; fall back to plain text
            if rendered.get("body_html"):
                body    = rendered["body_html"]
                is_html = True
            elif rendered.get("body_text"):
                body = rendered["body_text"]
        except KeyError:
            return jsonify({"ok": False, "error": f"Template '{template_id}' not found."}), 404
        except Exception as e:
            logger.warning(f"[MAIL API] template render error: {e}")

    if not to or not subject or not body:
        return jsonify({"ok": False, "error": "to, subject and body are required"}), 400
    try:
        from hecos.hpm.mail.smtp_client import build_smtp_client
        from hecos.hpm.mail.hooks import resolve_to_addresses
        cfg      = _get_cfg()
        username = _get_username()
        resolved_to  = ", ".join(resolve_to_addresses(to))
        resolved_cc  = ", ".join(resolve_to_addresses(data.get("cc", ""))) if data.get("cc") else ""
        resolved_bcc = ", ".join(resolve_to_addresses(data.get("bcc", ""))) if data.get("bcc") else ""
        client = build_smtp_client(cfg, username)
        ok, msg = client.send(
            to=resolved_to, subject=subject, body=body,
            cc=resolved_cc, bcc=resolved_bcc,
            is_html=is_html,
            attach_paths=data.get("attach_paths", [])
        )
        if ok:
            return jsonify({"ok": True, "message": msg})
        return jsonify({"ok": False, "error": msg}), 500
    except Exception as e:
        logger.error(f"[MAIL API] /send error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@mail_bp.route("/reply/<message_id>", methods=["POST"])
def reply_message(message_id):
    from hecos.hpm.mail import store
    from hecos.hpm.mail.smtp_client import build_smtp_client
    data = request.get_json(force=True) or {}
    body      = data.get("body", "")
    reply_all = data.get("reply_all", False)
    if not body:
        return jsonify({"ok": False, "error": "body is required"}), 400
    try:
        msg = store.get_message(message_id)
        if not msg:
            return jsonify({"ok": False, "error": "Message not found"}), 404
        subject = msg.get("subject", "")
        if not subject.lower().startswith("re:"):
            subject = "Re: " + subject
        cc = msg.get("to_addrs", "") if reply_all else ""
        cfg      = _get_cfg()
        username = _get_username()
        client = build_smtp_client(cfg, username)
        ok, result = client.send(
            to=msg.get("from_addr", ""), subject=subject, body=body,
            cc=cc, in_reply_to=msg.get("message_id_header", "")
        )
        if ok:
            store.mark_read(message_id, True)
            return jsonify({"ok": True, "message": result})
        return jsonify({"ok": False, "error": result}), 500
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@mail_bp.route("/forward/<message_id>", methods=["POST"])
def forward_message(message_id):
    from hecos.hpm.mail import store
    from hecos.hpm.mail.smtp_client import build_smtp_client
    from hecos.hpm.mail.hooks import resolve_to_addresses
    data = request.get_json(force=True) or {}
    to   = data.get("to", "")
    if not to:
        return jsonify({"ok": False, "error": "to is required"}), 400
    try:
        msg = store.get_message(message_id)
        if not msg:
            return jsonify({"ok": False, "error": "Message not found"}), 404
        subject = msg.get("subject", "")
        if not subject.lower().startswith("fwd:"):
            subject = "Fwd: " + subject
        fwd_body = (data.get("body") or "") + "\n\n---------- Forwarded message ----------\n"
        fwd_body += f"From: {msg.get('from_addr', '')}\nDate: {msg.get('date', '')}\nSubject: {msg.get('subject', '')}\n\n"
        fwd_body += msg.get("body_text", "")
        resolved = ", ".join(resolve_to_addresses(to))
        cfg      = _get_cfg()
        username = _get_username()
        client   = build_smtp_client(cfg, username)
        ok, result = client.send(to=resolved, subject=subject, body=fwd_body)
        if ok:
            return jsonify({"ok": True, "message": result})
        return jsonify({"ok": False, "error": result}), 500
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# â”€â”€ Sync â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@mail_bp.route("/sync-all", methods=["POST"])
def sync_all():
    try:
        from hecos.hpm.mail.imap_client import build_imap_client
        from hecos.hpm.mail import store
        cfg      = _get_cfg()
        username = _get_username()
        client = build_imap_client(cfg, username)
        ok, err = client.connect()
        if not ok:
            return jsonify({"ok": False, "error": err}), 500
            
        max_msgs = int(cfg.get("max_messages", 100))
        folders = ["INBOX", "SENT", "DRAFTS", "TRASH", "SPAM"]
        results = {}
        total = 0
        
        for folder in folders:
            try:
                known = store.get_uid_set(folder)
                messages = client.sync_folder(folder=folder, max_msgs=max_msgs, known_uids=known)
                count = 0
                for m in messages:
                    store.upsert_message(m)
                    count += 1
                results[folder] = count
                total += count
            except Exception as e:
                results[folder] = 0
                logger.warning(f"[MAIL] sync-all {folder} skipped: {e}")
                
        client.disconnect()
        stats = store.get_stats()
        return jsonify({"ok": True, "synced": total, "per_folder": results, "stats": stats})
    except Exception as e:
        logger.error(f"[MAIL API] /sync-all error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


# â”€â”€ Stats â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@mail_bp.route("/stats", methods=["GET"])
def get_stats():
    from hecos.hpm.mail import store
    try:
        return jsonify({"ok": True, "stats": store.get_stats()})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# â”€â”€ Drafts â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@mail_bp.route("/drafts", methods=["GET"])
def list_drafts():
    from hecos.hpm.mail import store
    return jsonify({"ok": True, "drafts": store.list_drafts()})


@mail_bp.route("/drafts", methods=["POST"])
def create_draft():
    from hecos.hpm.mail import store
    data = request.get_json(force=True) or {}
    d = store.save_draft(
        to_addrs=data.get("to", ""), cc=data.get("cc", ""), bcc=data.get("bcc", ""),
        subject=data.get("subject", ""), body=data.get("body", ""),
        is_html=data.get("is_html", False)
    )
    return jsonify({"ok": True, "draft": d}), 201


@mail_bp.route("/drafts/<draft_id>", methods=["PUT"])
def update_draft(draft_id):
    from hecos.hpm.mail import store
    data = request.get_json(force=True) or {}
    d = store.save_draft(
        to_addrs=data.get("to", ""), cc=data.get("cc", ""), bcc=data.get("bcc", ""),
        subject=data.get("subject", ""), body=data.get("body", ""),
        is_html=data.get("is_html", False), draft_id=draft_id
    )
    return jsonify({"ok": True, "draft": d})


@mail_bp.route("/drafts/<draft_id>", methods=["DELETE"])
def delete_draft(draft_id):
    from hecos.hpm.mail import store
    ok = store.delete_draft(draft_id)
    return jsonify({"ok": ok})


# â”€â”€ Account management â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@mail_bp.route("/test-account", methods=["POST"])
def test_account():
    """Tests both SMTP and IMAP connections with current settings."""
    try:
        from hecos.hpm.mail.smtp_client import build_smtp_client
        from hecos.hpm.mail.imap_client import build_imap_client
        cfg      = _get_cfg()
        username = _get_username()
        smtp_ok, smtp_msg = build_smtp_client(cfg, username).test_connection()
        imap_ok, imap_msg = build_imap_client(cfg, username).test_connection()
        return jsonify({
            "ok": smtp_ok and imap_ok,
            "smtp": {"ok": smtp_ok, "message": smtp_msg},
            "imap": {"ok": imap_ok, "message": imap_msg}
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@mail_bp.route("/account-password", methods=["PUT"])
def update_app_password():
    """Updates the email address and/or app password in the MAIL plugin config."""
    data     = request.get_json(force=True) or {}
    password = data.get("password", "").strip()
    email    = data.get("email", "").strip()
    if not password and not email:
        return jsonify({"ok": False, "error": "email or password is required"}), 400
    try:
        from hecos.hpm.mail.credential_helper import set_mail_credentials
        ok = set_mail_credentials(email=email, password=password)
        return jsonify({"ok": ok})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@mail_bp.route("/account-info", methods=["GET"])
def get_account_info():
    """Returns the mail address currently configured (never returns the password in plain text via GET)."""
    try:
        from hecos.hpm.mail.credential_helper import get_user_email, get_user_app_password
        email    = get_user_email()
        has_pwd  = bool(get_user_app_password())
        return jsonify({"ok": True, "email": email, "has_password": has_pwd})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@mail_bp.route("/folders", methods=["GET"])
def list_folders():
    """Lists available IMAP folders on the server."""
    try:
        from hecos.hpm.mail.imap_client import build_imap_client
        cfg      = _get_cfg()
        username = _get_username()
        client   = build_imap_client(cfg, username)
        ok, err  = client.connect()
        if not ok:
            return jsonify({"ok": False, "error": err}), 500
        folders = client.list_folders()
        client.disconnect()
        return jsonify({"ok": True, "folders": folders})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@mail_bp.route("/config", methods=["GET"])
def get_mail_config():
    """Returns the current MAIL plugin settings (excludes credentials)."""
    try:
        cfg = _get_cfg()
        safe = {k: v for k, v in cfg.items() if k != "mail_app_password"}
        return jsonify({"ok": True, "config": safe})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@mail_bp.route("/config", methods=["PUT"])
def update_mail_config():
    """Persists MAIL plugin settings to mail.toml via ConfigManager."""
    data = request.get_json(force=True) or {}
    ALLOWED = {
        "enabled", "lazy_load", "sync_on_open", "auto_detect_provider",
        "smtp_host", "smtp_port", "smtp_security",
        "imap_host", "imap_port", "imap_security",
        "max_messages",
    }
    try:
        from .mail_config.config_manager import get_config, save_config
        current = get_config()
        for key, val in data.items():
            if key in ALLOWED:
                if key in ("smtp_port", "imap_port", "max_messages"):
                    try:
                        val = int(val)
                    except (TypeError, ValueError):
                        val = current.get(key, 0)
                elif key in ("enabled", "lazy_load", "sync_on_open", "auto_detect_provider"):
                    val = bool(val)
                current[key] = val
        ok = save_config(current)
        logger.info(f"[MAIL] Config saved: {current}")
        return jsonify({"ok": ok})
    except Exception as e:
        logger.error(f"[MAIL] PUT /api/mail/config error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500
