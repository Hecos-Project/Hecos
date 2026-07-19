"""
MODULE: routes_keys.py
DESCRIPTION: REST API routes for the Key Manager WebUI panel.
"""
from flask import jsonify, request


def init_keys_routes(app, logger):
    """Register /api/keys/* routes."""

    def _km():
        from hecos.core.keys import get_key_manager
        return get_key_manager()

    # ── GET /api/keys/status ─────────────────────────────────────────────────
    @app.route("/api/keys/status", methods=["GET"])
    def keys_status():
        """Return full status dict for all providers and their keys."""
        try:
            data = _km().get_all_status()
            return jsonify({"ok": True, "data": data})
        except Exception as e:
            logger.error(f"[KeyManager] status error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    # ── POST /api/keys/reload ────────────────────────────────────────────────
    @app.route("/api/keys/reload", methods=["POST"])
    def keys_reload():
        """Force reload of all keys from disk (keys.yaml + .env + system.yaml)."""
        try:
            _km().reload()
            logger.info("[KeyManager] Pool reloaded via WebUI.")
            return jsonify({"ok": True, "message": "Pool ricaricato."})
        except Exception as e:
            logger.error(f"[KeyManager] reload error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    # ── POST /api/keys/add ───────────────────────────────────────────────────
    @app.route("/api/keys/add", methods=["POST"])
    def keys_add():
        """Add a key to the pool and persist it in config/keys.yaml."""
        body = request.get_json(silent=True) or {}
        provider = (body.get("provider") or "").strip().lower()
        value = (body.get("value") or "").strip()
        description = (body.get("description") or "").strip()
        save_to_env = bool(body.get("save_to_env", False))

        if not provider:
            return jsonify({"ok": False, "error": "Provider mancante."}), 400
        if not value:
            return jsonify({"ok": False, "error": "Valore chiave mancante."}), 400
        if "\n" in value or "\r" in value:
            return jsonify({"ok": False, "error": "Il valore della chiave non può contenere andate a capo."}), 400

        try:
            ok = _km().add_key(provider, value, description, save_to_env=save_to_env)
            if ok:
                logger.info(f"[KeyManager] Key added for '{provider}' via WebUI (to_env={save_to_env}).")
                return jsonify({"ok": True})
            else:
                return jsonify({"ok": False, "error": "Chiave già presente nel pool."})
        except Exception as e:
            logger.error(f"[KeyManager] add error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    # ── DELETE /api/keys/remove ──────────────────────────────────────────────
    @app.route("/api/keys/remove", methods=["DELETE"])
    def keys_remove():
        """Remove a key from the pool and from keys.yaml."""
        body = request.get_json(silent=True) or {}
        provider = (body.get("provider") or "").strip().lower()
        value = (body.get("value") or "").strip()

        if not provider or not value:
            return jsonify({"ok": False, "error": "Provider e valore richiesti."}), 400

        try:
            ok = _km().remove_key(provider, value)
            if ok:
                logger.info(f"[KeyManager] Key removed for '{provider}' via WebUI.")
                return jsonify({"ok": True})
            else:
                return jsonify({"ok": False, "error": "Chiave non trovata in keys.yaml (solo le chiavi da file possono essere rimosse)."})
        except Exception as e:
            logger.error(f"[KeyManager] remove error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    # ── POST /api/keys/reset ─────────────────────────────────────────────────
    @app.route("/api/keys/reset", methods=["POST"])
    def keys_reset():
        """Reset a specific key status to valid."""
        body = request.get_json(silent=True) or {}
        provider = (body.get("provider") or "").strip().lower()
        value = (body.get("value") or "").strip()

        if not provider or not value:
            return jsonify({"ok": False, "error": "Provider e valore richiesti."}), 400

        try:
            _km().mark_valid(provider, value)
            logger.info(f"[KeyManager] Key reset for '{provider}' via WebUI.")
            return jsonify({"ok": True})
        except Exception as e:
            logger.error(f"[KeyManager] reset error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    # ── POST /api/keys/reset_provider ────────────────────────────────────────
    @app.route("/api/keys/reset_provider", methods=["POST"])
    def keys_reset_provider():
        """Reset all non-invalid keys for a provider back to valid."""
        body = request.get_json(silent=True) or {}
        provider = (body.get("provider") or "").strip().lower()

        if not provider:
            return jsonify({"ok": False, "error": "Provider mancante."}), 400

        try:
            _km().reset_provider(provider)
            logger.info(f"[KeyManager] All keys reset for '{provider}' via WebUI.")
            return jsonify({"ok": True})
        except Exception as e:
            logger.error(f"[KeyManager] reset_provider error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500
    # ── POST /api/keys/validate ──────────────────────────────────────────────
    @app.route("/api/keys/validate", methods=["POST"])
    def keys_validate():
        """Trigger active validation for a specific key."""
        body = request.get_json(silent=True) or {}
        provider = (body.get("provider") or "").strip().lower()
        value = (body.get("value") or "").strip()

        if not provider or not value:
            return jsonify({"ok": False, "error": "Provider e valore richiesti."}), 400

        try:
            res = _km().validate_key(provider, value)
            return jsonify({"ok": True, "result": res})
        except Exception as e:
            logger.error(f"[KeyManager] validate error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    # ── POST /api/keys/validate_provider ─────────────────────────────────────
    @app.route("/api/keys/validate_provider", methods=["POST"])
    def keys_validate_provider():
        """Trigger active validation for all keys in a provider pool."""
        body = request.get_json(silent=True) or {}
        provider = (body.get("provider") or "").strip().lower()

        if not provider:
            return jsonify({"ok": False, "error": "Provider mancante."}), 400

        try:
            results = _km().validate_provider(provider)
            return jsonify({"ok": True, "results": results})
        except Exception as e:
            logger.error(f"[KeyManager] validate_provider error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    # ── GET/POST /hecos/api/keymanager/settings ───────────────────────────────
    @app.route("/hecos/api/keymanager/settings", methods=["GET"])
    def km_settings_get():
        """Return current key manager advanced settings (timeout, cooldown, max_retries)."""
        try:
            import hecos.core.keys.key_manager as _km_mod
            settings = {
                "cloud_timeout": getattr(_km_mod, "_KM_CLOUD_TIMEOUT", 30),
                "cooldown":      getattr(_km_mod, "_KM_COOLDOWN", 60),
                "max_retries":   getattr(_km_mod, "_KM_MAX_RETRIES", 5),
            }
            return jsonify({"ok": True, "settings": settings})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/hecos/api/keymanager/settings", methods=["POST"])
    def km_settings_post():
        """
        Update key manager advanced settings at runtime.
        Accepted fields: cloud_timeout (int), cooldown (int), max_retries (int).
        Changes take effect immediately for subsequent LLM calls.
        """
        body = request.get_json(silent=True) or {}
        try:
            import hecos.core.keys.key_manager as _km_mod
            import hecos.core.llm.client as _client_mod

            cloud_timeout = int(body.get("cloud_timeout", 30))
            cooldown      = int(body.get("cooldown",       60))
            max_retries   = int(body.get("max_retries",     5))

            # Clamp to sane values
            cloud_timeout = max(5, min(300, cloud_timeout))
            cooldown      = max(10, min(7200, cooldown))
            max_retries   = max(1, min(20, max_retries))

            # Apply runtime overrides (module-level globals read by client.py)
            _km_mod._KM_CLOUD_TIMEOUT = cloud_timeout
            _km_mod._KM_COOLDOWN      = cooldown
            _km_mod._KM_MAX_RETRIES   = max_retries
            _km_mod.DEFAULT_COOLDOWN  = float(cooldown)

            logger.info(f"[KeyManager] Settings updated: timeout={cloud_timeout}s, cooldown={cooldown}s, retries={max_retries}")
            return jsonify({"ok": True, "applied": {
                "cloud_timeout": cloud_timeout,
                "cooldown":      cooldown,
                "max_retries":   max_retries
            }})
        except Exception as e:
            logger.error(f"[KeyManager] settings_post error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500
