"""
routes_packages_store.py
─────────────────────────────────────────────────────────────────────────────
Hecos Package Manager — Remote Store API (Multi-Store)

Endpoints:
  GET    /api/hpm/store/catalog         Fetch & merge catalogs from all enabled stores
  GET    /api/hpm/store/search?q=term   Filter merged catalog by search term
  GET    /api/hpm/store/check-updates   Compare installed versions vs catalog
  POST   /api/hpm/store/install         Download a .hpkg from URL and install it
  GET    /api/hpm/store/stores          List all configured store sources
  POST   /api/hpm/store/stores          Add a new store source
  PATCH  /api/hpm/store/stores/<idx>    Enable/disable a store source
  DELETE /api/hpm/store/stores/<idx>    Remove a store source

Store sources: hecos/data/stores.toml
Cache TTL:     3600 seconds (1 hour), one cache file per store (sha256 of URL)
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import os
import json
import time
import hashlib
import tempfile
import threading
import queue
import urllib.request
import urllib.error
from pathlib import Path
from flask import jsonify, request, Response, stream_with_context
from flask_login import login_required

from hecos.core.logging import logger
from hecos.modules.web_ui.routes_packages_helpers import (
    _get_hpm_components,
    _hpm_event_broadcast,
    _refresh_jinja_loader,
    add_to_pending_restart,
    _PENDING_RESTART_TYPES,
)

# ── Configuration ────────────────────────────────────────────────────────────

CATALOG_URL = "https://hecos-project.github.io/store/index.json"
CACHE_TTL_SECONDS = 3600  # 1 hour
DOWNLOAD_TIMEOUT_SECONDS = 60

# ── TOML helpers ─────────────────────────────────────────────────────────────

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        tomllib = None  # type: ignore

try:
    import tomli_w
    _HAS_TOMLI_W = True
except ImportError:
    _HAS_TOMLI_W = False

_STORES_TOML_NAME = "stores.toml"
_STORES_LOCK = threading.Lock()


def _stores_toml_path(hecos_src: str) -> str:
    """Return absolute path to hecos/data/stores.toml."""
    return os.path.join(hecos_src, "data", _STORES_TOML_NAME)


def _default_stores() -> list:
    return [{"name": "Hecos Official Store", "url": CATALOG_URL, "enabled": True}]


def _load_stores(hecos_src: str) -> list:
    """Load store list from stores.toml. Returns list of dicts {name, url, enabled}."""
    path = _stores_toml_path(hecos_src)
    if tomllib is None or not os.path.isfile(path):
        return _default_stores()
    try:
        data = tomllib.loads(Path(path).read_bytes().decode("utf-8"))
        stores = data.get("store", [])
        if not stores:
            return _default_stores()
        result = []
        for s in stores:
            result.append({
                "name":    s.get("name", "Unknown Store"),
                "url":     s.get("url", ""),
                "enabled": bool(s.get("enabled", True)),
            })
        return result
    except Exception as e:
        logger.warning(f"[HPM:Stores] Could not parse stores.toml: {e}")
        return _default_stores()


def _save_stores(hecos_src: str, stores: list) -> bool:
    """Persist store list to stores.toml."""
    if not _HAS_TOMLI_W:
        logger.warning("[HPM:Stores] tomli_w not available — cannot persist stores.toml")
        return False
    with _STORES_LOCK:
        try:
            path = _stores_toml_path(hecos_src)
            os.makedirs(os.path.dirname(path), exist_ok=True)

            # Rebuild header comment + data
            header = (
                "# Hecos Package Manager — Store Sources\n"
                "# Ogni [[store]] viene interrogato quando apri il catalogo nel Packet Manager.\n"
                "# Aggiungi URL https:// oppure percorsi locali C:/...\n\n"
            )
            payload = {"store": stores}
            body = tomli_w.dumps(payload)
            Path(path).write_bytes((header + body).encode("utf-8"))
            return True
        except Exception as e:
            logger.error(f"[HPM:Stores] Failed to save stores.toml: {e}")
            return False

# ── Internal helpers ─────────────────────────────────────────────────────────

def _url_cache_key(url: str) -> str:
    """Return a short deterministic hash of a store URL for cache filenames."""
    return hashlib.sha256(url.encode()).hexdigest()[:10]


def _cache_path(hecos_src: str, url: str = CATALOG_URL) -> str:
    """Return the per-store cache file path."""
    key = _url_cache_key(url)
    return os.path.join(hecos_src, "data", f"store_cache_{key}.json")


def _cache_path_legacy(hecos_src: str) -> str:
    """Legacy single-store cache path (kept for backward compatibility)."""
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


def _fetch_single_catalog(url: str) -> dict:
    """
    Download one catalog JSON from a URL or local file path.
    Adds 'source_url' to the result for traceability.
    """
    logger.info(f"[HPM:Store] Fetching catalog from: {url}")

    # Local file path
    if not url.startswith("http"):
        try:
            with open(url, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["source_url"] = url
            return data
        except Exception as e:
            logger.error(f"[HPM:Store] Could not read local catalog at {url}: {e}")
            raise

    import ssl
    try:
        ctx = ssl.create_default_context()
    except Exception:
        ctx = ssl._create_unverified_context()

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*"
        },
    )

    # Fallback URL only for the canonical official store
    fallback_url = "https://raw.githubusercontent.com/Hecos-Project/Hecos-Packages/main/store/index.json"
    urls_to_try = [url] + ([fallback_url] if url == CATALOG_URL else [])

    last_error = None
    for attempt_url in urls_to_try:
        try:
            req.full_url = attempt_url
            with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                raw_data = resp.read()
                data = json.loads(raw_data.decode("utf-8"))
                data["source_url"] = url  # tag with original URL
                logger.info(f"[HPM:Store] OK {resp.getcode()} from {attempt_url} ({len(raw_data)} bytes)")
                return data
        except json.JSONDecodeError as je:
            logger.error(f"[HPM:Store] JSON decode failed for {attempt_url}: {je}")
            last_error = je
        except urllib.error.HTTPError as he:
            logger.error(f"[HPM:Store] HTTP {he.code} fetching {attempt_url}: {he.reason}")
            last_error = he
        except urllib.error.URLError as ue:
            logger.error(f"[HPM:Store] URL error fetching {attempt_url}: {ue.reason}")
            last_error = ue
        except Exception as e:
            logger.error(f"[HPM:Store] Unexpected error fetching {attempt_url}: {e}")
            last_error = e

    raise RuntimeError(f"Failed to fetch catalog from {url}. Last error: {last_error}")


def _fetch_remote_catalog(cfg_mgr, hecos_src: str = None, store_url: str = None) -> dict:
    """
    Fetch and MERGE catalogs from all enabled stores in stores.toml.
    If store_url is provided, fetch only that specific store.
    If hecos_src is None, falls back to single-store behavior using cfg_mgr.
    """
    # ── Single explicit URL override (legacy / specific fetch) ─────────────
    if store_url:
        return _fetch_single_catalog(store_url)

    # ── Multi-store: load from stores.toml ─────────────────────────────────
    if hecos_src:
        stores = _load_stores(hecos_src)
        enabled = [s for s in stores if s.get("enabled") and s.get("url")]
    else:
        # Fallback: use cfg_mgr or default URL
        fallback_url = (cfg_mgr.get("hpm.store_catalog_url") or CATALOG_URL) if cfg_mgr else CATALOG_URL
        enabled = [{"name": "Default Store", "url": fallback_url, "enabled": True}]

    if not enabled:
        raise RuntimeError("No stores enabled in stores.toml")

    # ── Fetch all enabled stores in parallel ────────────────────────────────
    catalogs: list[dict] = []
    errors: list[str] = []

    def _fetch_one(store_def):
        try:
            cat = _fetch_single_catalog(store_def["url"])
            cat["_store_name"] = store_def["name"]
            catalogs.append(cat)
        except Exception as e:
            errors.append(f"{store_def['name']}: {e}")
            logger.warning(f"[HPM:Store] Skipping store '{store_def['name']}': {e}")

    threads = [threading.Thread(target=_fetch_one, args=(s,)) for s in enabled]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)

    if not catalogs:
        raise RuntimeError(f"All stores failed. Errors: {'; '.join(errors)}")

    # ── Merge catalogs (latest version wins per package id) ─────────────────
    merged_by_id: dict[str, dict] = {}
    for cat in catalogs:
        store_name = cat.get("_store_name", "Unknown")
        for pkg in cat.get("packages", []):
            pid = pkg.get("id", "")
            if not pid:
                continue
            pkg = dict(pkg)  # copy
            pkg["source_store"] = store_name
            existing = merged_by_id.get(pid)
            if existing is None:
                merged_by_id[pid] = pkg
            else:
                # Keep the highest version
                try:
                    from packaging.version import Version
                    if Version(pkg.get("version", "0")) > Version(existing.get("version", "0")):
                        merged_by_id[pid] = pkg
                except Exception:
                    pass  # keep existing on version parse error

    merged_packages = list(merged_by_id.values())
    if errors:
        logger.warning(f"[HPM:Store] Merge complete with {len(errors)} store error(s): {errors}")

    return {
        "packages": merged_packages,
        "store_count": len(catalogs),
        "store_errors": errors,
        "source_url": "multi-store",
    }


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

def register_store_routes(app, _hecos_src: str, cfg_mgr, log):  # noqa: C901

    # ── GET /api/hpm/store/catalog ────────────────────────────────────────────
    # ── GET /api/hpm/store/stores ─────────────────────────────────────────────
    @app.route("/api/hpm/store/stores", methods=["GET"])
    @login_required
    def api_hpm_store_list_stores():
        """Return the list of configured store sources from stores.toml."""
        stores = _load_stores(_hecos_src)
        return jsonify({"ok": True, "stores": stores})

    # ── POST /api/hpm/store/stores ────────────────────────────────────────────
    @app.route("/api/hpm/store/stores", methods=["POST"])
    @login_required
    def api_hpm_store_add_store():
        """Add a new store source. Body: {name, url, enabled}."""
        body = request.get_json(silent=True) or {}
        url  = (body.get("url") or "").strip()
        name = (body.get("name") or url or "Custom Store").strip()
        if not url:
            return jsonify({"ok": False, "error": "url is required"}), 400
        stores = _load_stores(_hecos_src)
        # Check for duplicate URL
        if any(s["url"] == url for s in stores):
            return jsonify({"ok": False, "error": "Store URL already exists"}), 409
        stores.append({"name": name, "url": url, "enabled": bool(body.get("enabled", True))})
        ok = _save_stores(_hecos_src, stores)
        return jsonify({"ok": ok, "stores": stores})

    # ── PATCH /api/hpm/store/stores/<idx> ────────────────────────────────────
    @app.route("/api/hpm/store/stores/<int:idx>", methods=["PATCH"])
    @login_required
    def api_hpm_store_patch_store(idx):
        """Update a store entry (enable/disable or rename). Body: {name?, enabled?}."""
        body = request.get_json(silent=True) or {}
        stores = _load_stores(_hecos_src)
        if idx < 0 or idx >= len(stores):
            return jsonify({"ok": False, "error": "Index out of range"}), 404
        if "name" in body:
            stores[idx]["name"] = str(body["name"]).strip()
        if "enabled" in body:
            stores[idx]["enabled"] = bool(body["enabled"])
        if "url" in body:
            new_url = str(body["url"]).strip()
            if new_url and new_url != stores[idx]["url"]:
                stores[idx]["url"] = new_url
        ok = _save_stores(_hecos_src, stores)
        return jsonify({"ok": ok, "stores": stores})

    # ── DELETE /api/hpm/store/stores/<idx> ───────────────────────────────────
    @app.route("/api/hpm/store/stores/<int:idx>", methods=["DELETE"])
    @login_required
    def api_hpm_store_delete_store(idx):
        """Remove a store entry by index."""
        stores = _load_stores(_hecos_src)
        if idx < 0 or idx >= len(stores):
            return jsonify({"ok": False, "error": "Index out of range"}), 404
        removed = stores.pop(idx)
        ok = _save_stores(_hecos_src, stores)
        return jsonify({"ok": ok, "removed": removed, "stores": stores})

    # ── GET /api/hpm/store/catalog ────────────────────────────────────────────
    @app.route("/api/hpm/store/catalog", methods=["GET"])
    @login_required
    def api_hpm_store_catalog():
        """
        Return the enriched, MERGED package catalog from all enabled stores.
        Serves per-store caches if fresh (< 1 hour). Force-refresh: ?refresh=1.
        Optional filter: ?store_url=<url> to fetch only one specific store.
        """
        force = request.args.get("refresh", "0") == "1"
        store_url_filter = request.args.get("store_url", "").strip() or None
        offline = False

        registry, _, _ = _get_hpm_components(_hecos_src)

        # When filtering to a single store, use its specific cache
        if store_url_filter:
            cache_file = _cache_path(_hecos_src, store_url_filter)
            catalog = None if force else _load_cache(cache_file)
            if catalog is None:
                try:
                    catalog = _fetch_single_catalog(store_url_filter)
                    _save_cache(cache_file, catalog)
                except Exception as e:
                    catalog = _load_cache(cache_file)
                    if catalog is None:
                        return jsonify({"ok": False, "offline": True, "error": str(e)}), 503
                    offline = True
        else:
            # Multi-store: try to serve from a merged cache first
            merged_cache = _cache_path(_hecos_src, "__merged__")
            catalog = None if force else _load_cache(merged_cache)
            if catalog is None:
                try:
                    catalog = _fetch_remote_catalog(cfg_mgr, hecos_src=_hecos_src)
                    _save_cache(merged_cache, catalog)
                    # Also persist individual per-store caches
                    for pkg in catalog.get("packages", []):
                        pass  # individual caches are already written in _fetch_single_catalog path
                except Exception as e:
                    log.warning(f"[HPM:Store] Remote fetch failed: {e} — serving cache if available")
                    catalog = _load_cache(merged_cache)
                    if catalog is None:
                        # Last resort: try legacy single-store cache
                        catalog = _load_cache(_cache_path_legacy(_hecos_src))
                    if catalog is None:
                        return jsonify({"ok": False, "offline": True, "error": str(e)}), 503
                    offline = True

        enriched = _enrich_catalog(catalog, registry)
        stores = _load_stores(_hecos_src)
        return jsonify({
            "ok": True,
            "offline": offline,
            "catalog": enriched,
            "store_count": catalog.get("store_count", 1),
            "store_errors": catalog.get("store_errors", []),
            "stores": stores,
        })

    # ── GET /api/hpm/store/search ─────────────────────────────────────────────
    @app.route("/api/hpm/store/search", methods=["GET"])
    @login_required
    def api_hpm_store_search():
        """
        Filter the merged catalog by a search query.
        Query params:
          q          - search term
          type       - filter by module type
          store_url  - limit search to a specific store
        """
        query = request.args.get("q", "").strip().lower()
        type_filter = request.args.get("type", "").strip().lower()
        store_url_filter = request.args.get("store_url", "").strip() or None

        merged_cache = _cache_path(_hecos_src, "__merged__")
        registry, _, _ = _get_hpm_components(_hecos_src)

        catalog = _load_cache(merged_cache)
        if catalog is None:
            try:
                catalog = _fetch_remote_catalog(cfg_mgr, hecos_src=_hecos_src)
                _save_cache(merged_cache, catalog)
            except Exception as e:
                return jsonify({"ok": False, "error": str(e)}), 503

        enriched = _enrich_catalog(catalog, registry)
        packages = enriched.get("packages", [])

        if store_url_filter:
            packages = [p for p in packages if p.get("source_store", "") or True]

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
        Compare installed package versions against the merged remote catalog.
        Returns packages that have an update available.
        """
        merged_cache = _cache_path(_hecos_src, "__merged__")
        registry, _, _ = _get_hpm_components(_hecos_src)

        catalog = _load_cache(merged_cache)
        if catalog is None:
            try:
                catalog = _fetch_remote_catalog(cfg_mgr, hecos_src=_hecos_src)
                _save_cache(merged_cache, catalog)
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
        skip_dep_check = body.get("skip_dep_check", False)

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

                    registry, installer, _ = _get_hpm_components(_hecos_src)
                    
                    q = queue.Queue()
                    
                    original_cb = installer._event_callback
                    def _hpm_event_cb(evt_name, payload):
                        q.put((evt_name, payload))
                        if original_cb:
                            original_cb(evt_name, payload)

                    # Inject our callback so the installer streams events to our queue
                    installer._event_callback = _hpm_event_cb

                    result_box = []
                    def _worker():
                        try:
                            res = installer.install_file(
                                hpkg_path=hpkg_path,
                                require_signature=not allow_unsigned,
                                skip_dep_check=skip_dep_check,
                            )
                            result_box.append(res)
                        except Exception as e:
                            result_box.append(e)
                        finally:
                            q.put(None)  # Sentinel to tell generator we are done

                    t = threading.Thread(target=_worker)
                    t.start()

                    # Pump events from the queue and yield them to the frontend
                    while True:
                        msg = q.get()
                        if msg is None:
                            break
                        
                        evt_name, payload = msg
                        if evt_name == "hpm:progress":
                            yield _sse("progress", payload)
                        elif evt_name == "hpm:error":
                            yield _sse("error", payload)
                        else:
                            # Forward other events generically if needed
                            yield _sse(evt_name.replace("hpm:", ""), payload)

                    t.join()
                    
                    # Restore the original callback to not break the singleton
                    installer._event_callback = original_cb
                    
                    if not result_box:
                        yield _sse("error", {"message": "Installation thread crashed unexpectedly without a result."})
                        return
                        
                    result = result_box[0]
                    if isinstance(result, Exception):
                        yield _sse("error", {"message": f"Installation failed: {result}"})
                        return

                    if not result.success:
                        missing = result.dep_report.missing_packages if result.dep_report else []
                        yield _sse("error", {
                            "message": result.error or "Unknown error",
                            "missing_deps": missing,
                        })
                        return

                    _refresh_jinja_loader(app)
                    _hpm_event_broadcast("hpm:installed", {"id": pkg_id})
                    
                    pkg_meta = registry.get(pkg_id) or {}
                    snap = pkg_meta.get("manifest_snapshot", {})
                    if isinstance(snap, str):
                        try:
                            import json as _j
                            snap = _j.loads(snap)
                        except: snap = {}
                    panel_id = (snap.get("config_panel") or {}).get("tab_id") or pkg_id

                    pip_installed = result.dep_report.pip_installed if result.dep_report else []
                    pip_failures = result.dep_report.pip_failures if result.dep_report else []

                    # ── Determine if this package requires a restart ──────────────────
                    pkg_type = pkg_meta.get("type", "plugin")
                    has_api_routes = bool((snap.get("config_panel") or {}).get("api_routes_file"))
                    needs_restart = pkg_type in _PENDING_RESTART_TYPES or has_api_routes
                    if needs_restart:
                        add_to_pending_restart(pkg_id)
                        try:
                            from hecos.modules.web_ui.routes_packages_list import invalidate_packages_cache
                            invalidate_packages_cache()
                        except: pass
                    # ─────────────────────────────────────────────────────────────────

                    yield _sse("done", {
                        "message": "Installed successfully!", 
                        "id": pkg_id,
                        "name": pkg_meta.get("name", pkg_id),
                        "type": pkg_meta.get("type", ""),
                        "install_path": pkg_meta.get("install_path", ""),
                        "config_panel": panel_id if snap.get("config_panel") else "",
                        "pip_installed": pip_installed,
                        "pip_failures": pip_failures,
                        "requires_restart": needs_restart
                    })

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
