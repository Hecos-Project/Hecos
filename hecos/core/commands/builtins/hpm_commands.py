"""
hpm_commands.py
─────────────────────────────────────────────────────────────────────────────
HDCS — HPM Direct Commands
Slash commands for the Hecos Package Manager, modelled after pip/npm.

Registered commands:
  /hpm list              List all installed packages
  /hpm info <id>         Show details of an installed or available package
  /hpm search <query>    Search the remote catalog
  /hpm install <id>      Download and install a package from the store
  /hpm uninstall <id>    Uninstall an installed package
  /hpm update <id|all>   Update a package (or all packages) to latest
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import os
import json
import logging

_log = logging.getLogger("HecosHpmCommands")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_registry():
    """Return the HPM PackageRegistry singleton."""
    import sys
    hecos_src = getattr(sys, "_hecos_src_dir", None) or _guess_hecos_src()
    from hecos.core.package_manager.registry import PackageRegistry
    data_dir = os.path.join(hecos_src, "data")
    return PackageRegistry(data_dir=data_dir)


def _guess_hecos_src() -> str:
    """Fallback: locate the hecos/ package directory."""
    import hecos
    return os.path.dirname(hecos.__file__)


def _fetch_store_catalog(config_manager=None) -> list[dict]:
    """
    Fetch the remote store catalog.
    Returns the list of package dicts or [] on failure.
    """
    import sys
    hecos_src = getattr(sys, "_hecos_src_dir", None) or _guess_hecos_src()
    cache_file = os.path.join(hecos_src, "data", "store_cache.json")

    url = "https://hecos-project.github.io/store/index.json"
    if config_manager:
        url = config_manager.get("hpm.store_catalog_url") or url

    # Local development or local file override
    if not url.startswith("http"):
        try:
            with open(url, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("packages", [])
        except Exception as e:
            _log.warning(f"[HPM:Cmd] Could not read local catalog at {url}: {e}")
            return []

    # Try disk cache first
    try:
        if os.path.isfile(cache_file):
            import time
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if time.time() - data.get("cached_at", 0) < 3600:
                return data.get("packages", [])
    except Exception:
        pass

    # Fetch remote
    try:
        import urllib.request
        with urllib.request.urlopen(url, timeout=8) as r:
            catalog = json.loads(r.read().decode("utf-8"))
        # Save to cache
        import time
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump({**catalog, "cached_at": time.time()}, f)
        return catalog.get("packages", [])
    except Exception as e:
        _log.warning(f"[HPM:Cmd] Could not fetch store catalog: {e}")
        return []


def _fmt_size(n: int) -> str:
    if n >= 1048576:
        return f"{n / 1048576:.1f} MB"
    return f"{n / 1024:.1f} KB"


# ── Handlers ──────────────────────────────────────────────────────────────────

def _cmd_hpm_list(raw_args_str="", **kwargs) -> str:
    """List all installed HPM packages, grouped by type."""
    try:
        reg = _get_registry()
        pkgs = [p for p in reg.list_all() if p.get("status") != "broken"]
    except Exception as e:
        return f"❌ Could not read package registry: {e}"

    if not pkgs:
        return "📦 No HPM packages installed yet. Try `/hpm search` to browse the store."

    by_type: dict[str, list] = {}
    for p in pkgs:
        t = p.get("type", "plugin")
        by_type.setdefault(t, []).append(p)

    lines = [f"## 📦 Installed Packages ({len(pkgs)} total)\n"]
    TYPE_EMOJI = {
        "plugin": "🔌", "extension": "🧩", "app": "🖥️", "widget": "📊",
        "persona": "🎭", "theme": "🎨", "skill_pack": "🎓", "core_module": "⚙️",
    }
    for ptype, items in sorted(by_type.items()):
        icon = TYPE_EMOJI.get(ptype, "📦")
        lines.append(f"### {icon} {ptype.replace('_', ' ').title()} ({len(items)})")
        for p in items:
            status = "✅" if p.get("status") == "installed" else "⏸️"
            lines.append(f"- {status} **{p['name']}** `v{p['version']}` — by {p.get('author', '?')}")
    lines.append("\n*Use `/hpm info <id>` for details or `/hpm update all` to check for updates.*")
    return "\n".join(lines)


def _cmd_hpm_info(raw_args_str="", **kwargs) -> str:
    """Show details of a specific package (installed or from store catalog)."""
    pkg_id = raw_args_str.strip().lower()
    if not pkg_id:
        return "**Usage:** `/hpm info <package_id>` — e.g. `/hpm info weather_pro`"

    # Check installed first
    try:
        reg = _get_registry()
        pkg = reg.get(pkg_id)
    except Exception:
        pkg = None

    # Fall back to catalog
    if not pkg:
        catalog = _fetch_store_catalog(kwargs.get("config_manager"))
        pkg = next((p for p in catalog if p.get("id") == pkg_id), None)

    if not pkg:
        return f"❌ Package `{pkg_id}` not found locally or in the store catalog."

    lines = [
        f"## 📦 {pkg.get('name', pkg_id)}",
        f"**ID:** `{pkg.get('id', pkg_id)}`",
        f"**Version:** `{pkg.get('version', '?')}`",
        f"**Type:** `{pkg.get('type', '?')}`",
        f"**Author:** {pkg.get('author', 'Unknown')}",
        f"**Status:** {pkg.get('status', 'available from store')}",
    ]
    if pkg.get("description"):
        lines.append(f"\n{pkg['description']}")
    if pkg.get("tags"):
        lines.append(f"\n**Tags:** {', '.join(pkg['tags'])}")
    if pkg.get("size_bytes"):
        lines.append(f"**Size:** {_fmt_size(pkg['size_bytes'])}")
    if pkg.get("changelog"):
        lines.append(f"\n**Changelog:** {pkg['changelog']}")
    return "\n".join(lines)


def _cmd_hpm_search(raw_args_str="", **kwargs) -> str:
    """Search the remote package catalog by keyword."""
    query = raw_args_str.strip().lower()
    if not query:
        return "**Usage:** `/hpm search <term>` — e.g. `/hpm search weather`"

    catalog = _fetch_store_catalog(kwargs.get("config_manager"))
    if not catalog:
        return "❌ Could not reach the Hecos Package Store. Check your connection."

    results = []
    for p in catalog:
        hay = " ".join([p.get("name",""), p.get("description",""),
                        p.get("author",""), *p.get("tags", [])]).lower()
        if query in hay:
            results.append(p)

    if not results:
        return f"🔍 No packages found for **\"{raw_args_str.strip()}\"**."

    lines = [f"## 🔍 Search results for \"{raw_args_str.strip()}\" ({len(results)} found)\n"]
    for p in results:
        lines.append(f"- **{p['name']}** `{p.get('type','')}` v{p.get('version','?')} — {p.get('description','')[:80]}…")
        lines.append(f"  *Install:* `/hpm install {p['id']}`")
    return "\n".join(lines)


def _cmd_hpm_install(raw_args_str="", **kwargs) -> str:
    """Download and install a package from the Hecos Package Store."""
    pkg_id = raw_args_str.strip().lower()
    if not pkg_id:
        return "**Usage:** `/hpm install <package_id>` — e.g. `/hpm install weather_pro`"

    # Look up in catalog
    catalog = _fetch_store_catalog(kwargs.get("config_manager"))
    pkg = next((p for p in catalog if p.get("id") == pkg_id), None)
    if not pkg:
        return (f"❌ Package `{pkg_id}` not found in the Hecos Store.\n"
                f"Try `/hpm search {pkg_id}` to find similar packages.")

    # Check if already installed
    try:
        reg = _get_registry()
        existing = reg.get(pkg_id)
        if existing and existing.get("status") == "installed":
            installed_v = existing.get("version", "?")
            store_v = pkg.get("version", "?")
            if installed_v == store_v:
                return f"✅ `{pkg_id}` is already installed at v{installed_v}. Nothing to do."
            else:
                return (f"⬆️ Update available: v{installed_v} → v{store_v}\n"
                        f"Run `/hpm update {pkg_id}` to update, or visit the Store tab in the Package Manager.")
    except Exception:
        pass

    download_url = pkg.get("download_url", "")
    if not download_url:
        return f"❌ No download URL found for `{pkg_id}`. Please install via the Store tab in the WebUI."

    # Perform download + install
    import tempfile
    import sys
    hecos_src = getattr(sys, "_hecos_src_dir", None) or _guess_hecos_src()

    try:
        import urllib.request
        with tempfile.TemporaryDirectory(prefix="hecos_hpm_cli_") as tmpdir:
            filename = download_url.split("/")[-1] or f"{pkg_id}.hpkg"
            dest = os.path.join(tmpdir, filename)

            yield_msg = f"⏳ Downloading `{pkg['name']}` v{pkg['version']}…"
            # Download
            with urllib.request.urlopen(download_url, timeout=60) as r:
                with open(dest, "wb") as out:
                    out.write(r.read())

            # Install
            from hecos.core.package_manager.installer import PackageInstaller
            from hecos.core.package_manager.registry import PackageRegistry
            from hecos.core.system.version import VERSION
            data_dir = os.path.join(hecos_src, "data")
            reg2 = PackageRegistry(data_dir=data_dir)
            installer = PackageInstaller(
                hecos_root=os.path.dirname(hecos_src),
                registry=reg2,
                hecos_version=VERSION,
            )
            result = installer.install_file(hpkg_path=dest, require_signature=True)
            if not result.success:
                return f"❌ Installation failed: {result.error or 'Unknown error'}"

    except Exception as e:
        return f"❌ Could not install `{pkg_id}`: {e}"

    return (f"✅ **{pkg['name']}** v{pkg['version']} installed successfully!\n"
            f"You may need to restart Hecos for some modules to take effect.")


def _cmd_hpm_uninstall(raw_args_str="", **kwargs) -> str:
    """Uninstall an installed HPM package."""
    pkg_id = raw_args_str.strip().lower()
    if not pkg_id:
        return "**Usage:** `/hpm uninstall <package_id>` — e.g. `/hpm uninstall weather_pro`"

    import sys
    hecos_src = getattr(sys, "_hecos_src_dir", None) or _guess_hecos_src()
    try:
        from hecos.core.package_manager.registry import PackageRegistry
        from hecos.core.package_manager.uninstaller import PackageUninstaller
        data_dir = os.path.join(hecos_src, "data")
        reg = PackageRegistry(data_dir=data_dir)

        pkg = reg.get(pkg_id)
        if not pkg:
            return f"❌ Package `{pkg_id}` is not installed."
        if pkg.get("removable") is False:
            return f"🔒 `{pkg_id}` is a built-in module and cannot be removed."

        uninstaller = PackageUninstaller(
            hecos_root=os.path.dirname(hecos_src),
            registry=reg,
        )
        result = uninstaller.uninstall(pkg_id)
        if not result.get("ok"):
            return f"❌ Uninstall failed: {result.get('error', 'Unknown error')}"

    except Exception as e:
        return f"❌ Could not uninstall `{pkg_id}`: {e}"

    return f"✅ **{pkg_id}** has been uninstalled successfully."


def _cmd_hpm_update(raw_args_str="", **kwargs) -> str:
    """Check for and apply updates to one or all installed packages."""
    target = raw_args_str.strip().lower()
    if not target:
        return ("**Usage:**\n"
                "- `/hpm update <package_id>` — update a specific package\n"
                "- `/hpm update all` — check and update all packages")

    catalog = _fetch_store_catalog(kwargs.get("config_manager"))
    catalog_map = {p["id"]: p for p in catalog}

    try:
        reg = _get_registry()
        installed = reg.list_all()
    except Exception as e:
        return f"❌ Could not read package registry: {e}"

    if target == "all":
        to_update = []
        for p in installed:
            cat_pkg = catalog_map.get(p["id"])
            if cat_pkg and cat_pkg.get("version") != p.get("version"):
                to_update.append((p, cat_pkg))

        if not to_update:
            return "✅ All packages are up to date!"

        lines = [f"## ⬆️ Updates Available ({len(to_update)} packages)\n"]
        for inst, cat in to_update:
            lines.append(f"- **{inst['name']}** `v{inst['version']}` → `v{cat['version']}`")
            lines.append(f"  *Run `/hpm update {inst['id']}`* or use the Store tab.")
        return "\n".join(lines)
    else:
        # Single package update
        inst = reg.get(target)
        if not inst:
            return f"❌ `{target}` is not installed."
        cat_pkg = catalog_map.get(target)
        if not cat_pkg:
            return f"❌ `{target}` is not in the store catalog."
        if cat_pkg.get("version") == inst.get("version"):
            return f"✅ `{target}` is already at the latest version (v{inst['version']})."
        return (f"⬆️ Update available for **{inst['name']}**: "
                f"v{inst['version']} → v{cat_pkg['version']}\n"
                f"Install via the **Store tab** in the Package Manager or run:\n"
                f"`/hpm install {target}`")


def _cmd_hpm(raw_args_str="", **kwargs) -> str:
    """Main router for /hpm commands."""
    args = raw_args_str.strip()
    if not args:
        return ("**Hecos Package Manager CLI**\n"
                "Available commands:\n"
                "- `/hpm list` — list installed packages\n"
                "- `/hpm search <query>` — search the remote store\n"
                "- `/hpm info <id>` — details about a package\n"
                "- `/hpm install <id>` — install a package\n"
                "- `/hpm uninstall <id>` — remove a package\n"
                "- `/hpm update <id|all>` — check for updates")
    
    parts = args.split(" ", 1)
    subcmd = parts[0].lower()
    subargs = parts[1] if len(parts) > 1 else ""

    if subcmd in ("list", "ls"):
        return _cmd_hpm_list(subargs, **kwargs)
    elif subcmd == "info":
        return _cmd_hpm_info(subargs, **kwargs)
    elif subcmd in ("search", "find"):
        return _cmd_hpm_search(subargs, **kwargs)
    elif subcmd == "install":
        return _cmd_hpm_install(subargs, **kwargs)
    elif subcmd in ("uninstall", "remove"):
        return _cmd_hpm_uninstall(subargs, **kwargs)
    elif subcmd in ("update", "upgrade"):
        return _cmd_hpm_update(subargs, **kwargs)
    else:
        return f"❌ Unknown subcommand: `{subcmd}`. Type `/hpm` for help."


# ── Command descriptors ───────────────────────────────────────────────────────

HPM_COMMANDS = [
    {
        "id": "hpm",
        "aliases": ["/hpm"],
        "description": "Hecos Package Manager (install, update, search, list)",
        "usage": "/hpm <command> [args]",
        "example": "/hpm search weather",
        "icon": "📦",
        "category": "HPM",
        "requires_auth": "admin",
        "requires_args": True,
        "save_to_memory": False,
        "_handler": _cmd_hpm,
    }
]

