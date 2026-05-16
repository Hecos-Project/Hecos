"""
WEB_UI Plugin — Server SSL Automation
Contains logic to handle SSL certificate validation, generation, and extraction.
"""
import os
import logging

def ensure_ssl_context(webui_cfg, lan_ip, config_manager, logger=None):
    """
    Validates or generates SSL certificates based on LAN IP matching.
    Returns:
        tuple or None: (cert_abs_path, key_abs_path) for SSL context or None if fallback.
    """
    logger = logger or logging.getLogger(__name__)
    
    use_https = webui_cfg.get("https_enabled", False)
    if not use_https:
        return None

    cert_file = webui_cfg.get("cert_file")
    key_file = webui_cfg.get("key_file")

    # Resolve relative paths to absolute (relative to project root)
    _plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # modules/web_ui -> we want project root
    # Actually __file__ is hecos/modules/web_ui/server_ssl.py
    # So __file__ dir is web_ui, dir dir is modules, dir dir dir is hecos
    _project_root = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))

    def _resolve(p):
        if p and not os.path.isabs(p):
            return os.path.join(_project_root, p)
        return p

    cert_file_abs = _resolve(cert_file)
    key_file_abs  = _resolve(key_file)

    def _cert_covers_ip(cert_path, ip):
        """Returns True if the cert has `ip` in its SANs."""
        try:
            from cryptography import x509
            with open(cert_path, "rb") as f:
                cert = x509.load_pem_x509_certificate(f.read())
            san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
            import ipaddress as _ip
            for entry in san.value:
                if isinstance(entry, x509.IPAddress) and str(entry.value) == ip:
                    return True
                if isinstance(entry, x509.DNSName) and entry.value == ip:
                    return True
        except Exception:
            pass
        return False

    certs_ok = (
        cert_file_abs and key_file_abs
        and os.path.exists(cert_file_abs)
        and os.path.exists(key_file_abs)
        and _cert_covers_ip(cert_file_abs, lan_ip)
    )

    # Auto-generate only when truly missing or IP has changed
    if not certs_ok:
        try:
            from hecos.core.security.pki.ca_manager import CAManager
            from hecos.core.security.pki.cert_generator import CertGenerator

            logger.info("[PKI] Certificates missing or stale. Regenerating for %s...", lan_ip)
            ca_mgr  = CAManager()
            cert_gen = CertGenerator(ca_mgr)

            c_path, k_path = cert_gen.generate_host_cert(lan_ip)

            # Persist the absolute paths so the next restart resolves correctly
            # Modify config structure in place
            webui_cfg["cert_file"] = c_path
            webui_cfg["key_file"]  = k_path
            config_manager.save()

            cert_file_abs = c_path
            key_file_abs  = k_path
            logger.info("[PKI] New certificates saved for %s.", lan_ip)
        except Exception as pki_e:
            logger.error("[PKI] Automation failed: %s", pki_e)

    if cert_file_abs and key_file_abs and os.path.exists(cert_file_abs) and os.path.exists(key_file_abs):
        return (cert_file_abs, key_file_abs)
    else:
        logger.warning("[WebUI] HTTPS enabled but cert/key not found. Fallback to HTTP.")
        # Change configuration flag in memory so logging prints HTTP
        webui_cfg["https_enabled"] = False 
        return None
