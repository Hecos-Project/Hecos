"""
routes_packages_store.py
─────────────────────────────────────────────────────────────────────────────
Hecos Package Manager — Remote Store API

Endpoints:
  GET  /api/hpm/store/catalog         Fetch & cache the remote package catalog
  GET  /api/hpm/store/search?q=term   Filter catalog by search term
  GET  /api/hpm/store/check-updates   Compare installed versions vs catalog
  POST /api/hpm/store/install         Download a .hpkg from URL and install it

Catalog source: https://hecos-project.github.io/store/index.json
Cache TTL:      3600 seconds (1 hour), stored in hecos/data/store_cache.json
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import os
import json
import time
import tempfile
import threading
import urllib.request
from flask import jsonify, request, Response, stream_with_context
from flask_login import login_required

from hecos.core.logging import logger
from hecos.modules.web_ui.routes_packages_helpers import (
    _get_hpm_components,
    _hpm_event_broadcast,
    _refresh_jinja_loader,
)

# ── Configuration ────────────────────────────────────────────────────────────

CATALOG_URL = "https://hecos-project.github.io/store/index.json"
CACHE_TTL_SECONDS = 3600  # 1 hour
DOWNLOAD_TIMEOUT_SECONDS = 60

# ── Internal helpers ─────────────────────────────────────────────────────────

def _cache_path(hecos_src: str) -> str:
    """Return the path of the local store cache file."""
    return os.path.join(hecos_src, "data", "store_cache.json")


def _load_cache(cache_file: str) -> dict | None:
    """Load the cached catalog if it exists and has not expired."""
    try:
        if not os.path.isfile(cache_file):
            return None
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        if time.time() - data.get("cached_at", 0) < CACHE_TTL_SECONDS:
            return data
        return None
    except Exception:
        return None


def _save_cache(cache_file: str, catalog: dict) -> None:
    """Persist the catalog to disk with a timestamp."""
    try:
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump({**catalog, "cached_at": time.time()}, f, indent=2)
    except Exception as e:
        logger.warning(f"[HPM:Store] Could not write cache: {e}")


def _fetch_remote_catalog(cfg_mgr) -> dict:
    """Download the catalog JSON from the configured store URL."""
    url = (cfg_mgr.get("hpm.store_catalog_url") or CATALOG_URL) if cfg_mgr else CATALOG_URL
    logger.info(f"[HPM:Store] Attempting to fetch remote catalog from: {url}")
    
    # If the URL is a local file path, read it directly
    if not url.startswith("http"):
        try:
            with open(url, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"[HPM:Store] Could not read local catalog at {url}: {e}")
            raise

    # Prepare robust SSL context (useful on some Windows setups or proxies)
    import ssl
    try:
        ctx = ssl.create_default_context()
    except Exception:
        ctx = ssl._create_unverified_context()

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*"
        },
    )
    
    # Optional fallback URL just in case
    fallback_url = "https://raw.githubusercontent.com/Hecos-Project/Hecos-Packages/main/store/index.json"
    
    urls_to_try = [url]
    if url == CATALOG_URL:
        urls_to_try.append(fallback_url)

    last_error = None
    for attempt_url in urls_to_try:
        try:
            logger.debug(f"[HPM:Store] Requesting {attempt_url}...")
            req.full_url = attempt_url
            with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                status_code = resp.getcode()
                raw_data = resp.read()
                logger.info(f"[HPM:Store] Response {status_code} from {attempt_url}. Size: {len(raw_data)} bytes")
                
                try:
                    return json.loads(raw_data.decode("utf-8"))
                except json.JSONDecodeError as je:
                    logger.error(f"[HPM:Store] JSON decode failed for {attempt_url}. Error: {je}")
                    logger.debug(f"[HPM:Store] Raw response snippet: {raw_data[:200]}")
                    last_error = je
                    continue

        except urllib.error.HTTPError as he:
            logger.error(f"[HPM:Store] HTTP Error {he.code} fetching {attempt_url}: {he.reason}")
            last_error = he
        except urllib.error.URLError as ue:
            logger.error(f"[HPM:Store] URL Error fetching {attempt_url}: {ue.reason}")
            last_error = ue
        except Exception as e:
            logger.error(f"[HPM:Store] Unexpected error fetching {attempt_url}: {e}")
            last_error = e

    raise RuntimeError(f"All attempts to fetch catalog failed. Last error: {last_error}")


def _enrich_catalog(catalog: dict, registry) -> dict:
    """
    Enrich each catalog entry with local installation state:
      - installed: bool
      - installed_version: str | None
      - update_available: bool
    """
    installed_map: dict[str, str] = {}
    try:
        for pkg in registry.list_all():
            installed_map[pkg["id"]] = pkg.get("version", "")
    except Exception:
        pass

    enriched = []
    for pkg in catalog.get("packages", []):
        pid = pkg.get("id", "")
        inst_ver = installed_map.get(pid)
        pkg = dict(pkg)  # copy, don't mutate
        pkg["installed"] = inst_ver is not None
        pkg["installed_version"] = inst_ver
        pkg["update_available"] = (
            inst_ver is not None and inst_ver != pkg.get("version", "")
        )
        enriched.append(pkg)

    return {**catalog, "packages": enriched}


def _download_hpkg(url: str, dest_dir: str) -> str:
    """
    Download a .hpkg file from a URL into dest_dir.
    Returns the local file path.
    """
    filename = url.split("/")[-1].split("?")[0] or "package.hpkg"
    dest_path = os.path.join(dest_dir, filename)

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Hecos-HPM/1.0"},
    )
    with urllib.request.urlopen(req, timeout=DOWNLOAD_TIMEOUT_SECONDS) as resp:
        with open(dest_path, "wb") as out:
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                out.write(chunk)

    return dest_path


# ── Route Registration ────────────────────────────────────────────────────────

def register_store_routes(app, _hecos_src: str, cfg_mgr, log):

    # ── GET /api/hpm/store/catalog ────────────────────────────────────────────
    @app.route("/api/hpm/store/catalog", methods=["GET"])
    @login_required
    def api_hpm_store_catalog():
        """
        Return the enriched remote package catalog.
        Serves from local cache if fresh (< 1 hour old).
        Force-refresh by passing ?refresh=1.
        """
        force = request.args.get("refresh", "0") == "1"
        offline = False

        cache_file = _cache_path(_hecos_src)
        registry, _, _ = _get_hpm_components(_hecos_src)

        catalog = None if force else _load_cache(cache_file)

        if catalog is None:
            try:
                catalog = _fetch_remote_catalog(cfg_mgr)
                _save_cache(cache_file, catalog)
            except Exception as e:
                log.warning(f"[HPM:Store] Remote fetch failed: {e} — serving cache if available")
                catalog = _load_cache(cache_file)
                if catalog is None:
                    return jsonify({"ok": False, "offline": True, "error": str(e)}), 503
                offline = True

        enriched = _enrich_catalog(catalog, registry)
        return jsonify({
            "ok": True,
            "offline": offline,
            "catalog": enriched,
        })

    # ── GET /api/hpm/store/search ─────────────────────────────────────────────
    @app.route("/api/hpm/store/search", methods=["GET"])
    @login_required
    def api_hpm_store_search():
        """
        Filter the catalog by a search query (name, description, tags, author).
        Query params:
          q     - search term
          type  - filter by module type (plugin, widget, app, persona, theme, ...)
        """
        query = request.args.get("q", "").strip().lower()
        type_filter = request.args.get("type", "").strip().lower()

        cache_file = _cache_path(_hecos_src)
        registry, _, _ = _get_hpm_components(_hecos_src)

        catalog = _load_cache(cache_file)
        if catalog is None:
            try:
                catalog = _fetch_remote_catalog(cfg_mgr)
                _save_cache(cache_file, catalog)
            except Exception as e:
                return jsonify({"ok": False, "error": str(e)}), 503

        enriched = _enrich_catalog(catalog, registry)
        packages = enriched.get("packages", [])

        if type_filter:
            packages = [p for p in packages if p.get("type", "") == type_filter]

        if query:
            def _matches(pkg):
                haystack = " ".join([
                    pkg.get("name", ""),
                    pkg.get("description", ""),
                    pkg.get("author", ""),
                    " ".join(pkg.get("tags", [])),
                ]).lower()
                return query in haystack
            packages = [p for p in packages if _matches(p)]

        return jsonify({"ok": True, "packages": packages, "total": len(packages)})

    # ── GET /api/hpm/store/check-updates ──────────────────────────────────────
    @app.route("/api/hpm/store/check-updates", methods=["GET"])
    @login_required
    def api_hpm_store_check_updates():
        """
        Compare installed package versions against the remote catalog.
        Returns packages that have an update available.
        """
        cache_file = _cache_path(_hecos_src)
        registry, _, _ = _get_hpm_components(_hecos_src)

        catalog = _load_cache(cache_file)
        if catalog is None:
            try:
                catalog = _fetch_remote_catalog(cfg_mgr)
                _save_cache(cache_file, catalog)
            except Exception as e:
                return jsonify({"ok": False, "error": str(e)}), 503

        enriched = _enrich_catalog(catalog, registry)
        updates = [p for p in enriched.get("packages", []) if p.get("update_available")]
        return jsonify({"ok": True, "updates": updates, "count": len(updates)})

    # ── POST /api/hpm/store/install ────────────────────────────────────────────
    @app.route("/api/hpm/store/install", methods=["POST"])
    @login_required
    def api_hpm_store_install():
        """
        Download a .hpkg from a remote URL and install it.
        Body JSON: { "id": "package_id", "download_url": "https://..." }
        Returns a streaming SSE response with progress events.
        """
        body = request.get_json(silent=True) or {}
        pkg_id = body.get("id", "").strip()
        download_url = body.get("download_url", "").strip()

        if not pkg_id or not download_url:
            return jsonify({"ok": False, "error": "id and download_url are required"}), 400

        allow_unsigned = body.get("allow_unsigned", False)

        def _sse(event: str, data: dict) -> str:
            return f"event: {event}\ndata: {json.dumps(data)}\n\n"

        def generate():
            yield _sse("progress", {"step": "download", "message": f"Downloading {pkg_id}..."})

            try:
                with tempfile.TemporaryDirectory(prefix="hecos_hpm_store_") as tmpdir:
                    yield _sse("progress", {"step": "download", "message": "Fetching from remote..."})

                    try:
                        hpkg_path = _download_hpkg(download_url, tmpdir)
                    except Exception as e:
                        yield _sse("error", {"message": f"Download failed: {e}"})
                        return

                    yield _sse("progress", {"step": "install", "message": "Installing package..."})

                    try:
                        registry, installer, _ = _get_hpm_components(_hecos_src)
                        result = installer.install(
                            hpkg_path=hpkg_path,
                            allow_unsigned=allow_unsigned,
                        )
                    except Exception as e:
                        yield _sse("error", {"message": f"Installation failed: {e}"})
                        return

                    if not result.get("ok"):
                        yield _sse("error", {"message": result.get("error", "Unknown error")})
                        return

                    _refresh_jinja_loader(app)
                    _hpm_event_broadcast("hpm:installed", {"id": pkg_id})
                    yield _sse("done", {"message": "Installed successfully!", "id": pkg_id})

            except Exception as e:
                log.error(f"[HPM:Store] Unexpected error during store install of '{pkg_id}': {e}")
                yield _sse("error", {"message": f"Unexpected error: {e}"})

        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )
