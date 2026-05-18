"""
routes_system_sysnet.py
────────────────────────────────────────────────────────────────────────────
Hecos WebUI — SysNet & Reboot APIs
Registers:
  POST /api/system/reboot
  GET  /api/sysnet/test-proxy    (SSE streaming)
────────────────────────────────────────────────────────────────────────────
"""
import json
import re
import threading
import time
from flask import jsonify, Response, stream_with_context, request as flask_req


def init_system_sysnet_routes(app, logger):

    @app.route("/api/system/reboot", methods=["POST"])
    def system_reboot():
        """Reboots the entire Hecos system via os._exit(42)."""
        try:
            logger.info("[WebUI] User requested system reboot from Web UI.")

            def do_reboot():
                import os, winsound
                time.sleep(1.0)
                print(f"\n\033[91m[WEB_UI] Riavvio del sistema in corso...\033[0m")
                winsound.Beep(600, 150)
                winsound.Beep(400, 150)
                os._exit(42)

            threading.Thread(target=do_reboot, daemon=True).start()
            return jsonify({"ok": True, "message": "Reboot initiated"})
        except Exception as exc:
            logger.error(f"[WebUI] system_reboot error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/sysnet/test-proxy")
    def sysnet_test_proxy():
        """SSE endpoint: tests the proxy URL passed as query param ?url=... step by step."""
        proxy_url = flask_req.args.get("url", "").strip()

        def generate():
            def emit(msg, level="INFO"):
                data = json.dumps({"msg": msg, "level": level, "ts": time.strftime("%H:%M:%S")})
                return f"data: {data}\n\n"

            yield emit("🔍 Avvio test connettività proxy...")
            time.sleep(0.1)

            if not proxy_url:
                yield emit("⚠️  Nessun proxy configurato — test della connessione diretta.", "WARN")
                time.sleep(0.2)
                try:
                    import urllib.request
                    yield emit("→ Contatto api.ipify.org (connessione diretta)...")
                    ip = urllib.request.urlopen("https://api.ipify.org", timeout=6).read().decode()
                    yield emit(f"✅ Connessione diretta OK. IP pubblico: {ip}", "OK")
                except Exception as e:
                    yield emit(f"❌ Connessione diretta fallita: {e}", "ERR")
                yield emit("--- Fine test ---", "DONE")
                return

            m = re.match(r'^(\w+)://(?:[^@]+@)?([^:/]+):(\d+)', proxy_url)
            if m:
                proto, host, port = m.group(1), m.group(2), m.group(3)
                yield emit(f"📡 Proxy rilevato: protocollo={proto.upper()}, host={host}, porta={port}")
            else:
                yield emit(f"📡 Proxy URL: {proxy_url}")
            time.sleep(0.1)

            if m:
                # Step 1: DNS resolve
                yield emit(f"→ Risoluzione DNS di {host}...")
                try:
                    import socket
                    ip_resolved = socket.gethostbyname(host)
                    yield emit(f"✅ DNS risolto: {host} → {ip_resolved}", "OK")
                except Exception as e:
                    yield emit(f"❌ DNS fallito: {e}. Verificare che l'host del proxy sia corretto.", "ERR")
                    yield emit("--- Interruzione test: host non raggiungibile ---", "DONE")
                    return
                time.sleep(0.1)

                # Step 2: TCP port check
                yield emit(f"→ Test connessione TCP su {host}:{port}...")
                try:
                    import socket
                    sock = socket.create_connection((host, int(port)), timeout=5)
                    sock.close()
                    yield emit(f"✅ Porta {port} aperta e raggiungibile.", "OK")
                except Exception as e:
                    yield emit(f"❌ Porta {port} non raggiungibile: {e}", "ERR")
                    yield emit("--- Interruzione test: porta chiusa o firewall ---", "DONE")
                    return
                time.sleep(0.1)

            # Step 3: HTTP request through proxy
            yield emit("→ Tentativo richiesta HTTP tramite proxy (ipinfo.io)...")
            try:
                import requests as req_lib
                proxies = {"http": proxy_url, "https": proxy_url}
                r = req_lib.get("https://ipinfo.io/json", proxies=proxies, timeout=12)
                if r.status_code == 200:
                    data       = r.json()
                    ext_ip     = data.get("ip", "N/A")
                    city       = data.get("city", "Sconosciuta")
                    country    = data.get("country", "??")
                    region_str = f"{city}, {country}"
                    yield emit(f"✅ PROXY FUNZIONANTE! IP: {ext_ip} ({region_str})", "OK")
                    yield emit(f"ℹ️  Le richieste Hecos useranno questo IP in questa regione.", "OK")
                    payload = json.dumps({"ip": ext_ip, "loc": region_str, "status": "active"})
                    yield emit(payload, "PAYLOAD")
                else:
                    yield emit(f"⚠️  Proxy raggiunto ma risposta inattesa: HTTP {r.status_code}", "WARN")
            except Exception as e:
                err_msg = str(e)
                if   "timed out" in err_msg.lower():  yield emit(f"⏱️  Timeout: il proxy non ha risposto entro 12s. Prova un proxy più veloce.", "ERR")
                elif "refused"   in err_msg.lower():  yield emit(f"🚫 Connessione rifiutata dal proxy. Verificare porta e indirizzo.", "ERR")
                elif "SOCKS"     in err_msg:          yield emit(f"❌ Errore SOCKS: {err_msg[:120]}", "ERR")
                else:                                 yield emit(f"❌ Errore: {err_msg[:150]}", "ERR")

            yield emit("--- Fine test ---", "DONE")

        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
