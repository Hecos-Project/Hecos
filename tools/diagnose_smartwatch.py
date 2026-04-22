"""
=============================================================
  ZENTRA — Smartwatch Protocol Diagnostic
  Autore: Zentra Dev
  Scopo: Capire COME lo smartwatch comunica con il PC
         quando si preme il pulsante PTT/Voice Assistant
=============================================================
ISTRUZIONI:
  1. Avvia questo script (python tools/diagnose_smartwatch.py)
  2. Quando vedi "PRONTO — premi il pulsante sullo smartwatch"
     premi il pulsante microfono/voice assistant sul device
  3. Ripeti la pressione 3-4 volte (sia corta che lunga)
  4. Premi CTRL+C per terminare e leggere il report
=============================================================
"""

import sys
import threading
import time
import socket
import datetime

# ─── CONFIG ───────────────────────────────────────────────
MONITOR_SECONDS = 60          # Tempo massimo di ascolto
HTTP_PORT_MIN   = 5000        # Range porte da monitorare
HTTP_PORT_MAX   = 9999        # per connessioni in entrata
LOG_FILE = "tools/smartwatch_diag.log"
# ──────────────────────────────────────────────────────────

events = []
lock = threading.Lock()

def log(source: str, msg: str):
    ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    line = f"[{ts}] [{source}] {msg}"
    print(line)
    with lock:
        events.append(line)

# ─────────────────────────────────────────────────────────
# LAYER 1: HID / Keyboard events (pynput)
# Rileva: tasti media, tasti speciali, VK codes
# ─────────────────────────────────────────────────────────
def monitor_keyboard():
    try:
        from pynput import keyboard as kb

        def on_press(key):
            try:
                vk   = getattr(key, 'vk',   None)
                name = getattr(key, 'name', None)
                char = getattr(key, 'char', None)
                log("HID-KEY-PRESS",
                    f"key={key!r:30s}  name={name!r:20s}  char={char!r:10s}  VK={vk}")
            except Exception as e:
                log("HID-KEY-PRESS", f"(parse error: {e})")

        def on_release(key):
            try:
                vk   = getattr(key, 'vk',   None)
                name = getattr(key, 'name', None)
                log("HID-KEY-REL ",
                    f"key={key!r:30s}  name={name!r:20s}  VK={vk}")
            except Exception:
                pass

        listener = kb.Listener(on_press=on_press, on_release=on_release)
        listener.daemon = True
        listener.start()
        log("SYSTEM", "Layer 1 attivo — ascolto eventi HID/tastiera (pynput)")
        return listener
    except ImportError:
        log("SYSTEM", "WARN: pynput non installato. Salta Layer 1.")
        return None


# ─────────────────────────────────────────────────────────
# LAYER 2: Raw keyboard via 'keyboard' lib (VK aggiuntivi)
# ─────────────────────────────────────────────────────────
def monitor_keyboard_raw():
    try:
        import keyboard as kb2

        def on_event(e):
            log("RAW-KB",
                f"name={e.name!r:20s}  scan={e.scan_code:5d}  type={e.event_type}")

        kb2.hook(on_event)
        log("SYSTEM", "Layer 2 attivo — ascolto raw keyboard (keyboard lib)")
    except ImportError:
        log("SYSTEM", "WARN: keyboard lib non installato. Salta Layer 2.")
    except Exception as e:
        log("SYSTEM", f"Layer 2 errore: {e}")


# ─────────────────────────────────────────────────────────
# LAYER 3: Network listener — rileva connessioni HTTP in arrivo
# Ascolta su 0.0.0.0 su porte comuni
# ─────────────────────────────────────────────────────────
def network_listener(port: int):
    try:
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("0.0.0.0", port))
        srv.listen(5)
        srv.settimeout(1.0)
        log("SYSTEM", f"Layer 3 attivo — ascolto HTTP su porta {port}")
        while True:
            try:
                conn, addr = srv.accept()
                raw = conn.recv(4096)
                log("HTTP-IN", f"Connessione da {addr[0]}:{addr[1]}")
                try:
                    decoded = raw.decode("utf-8", errors="replace")
                    for line in decoded.splitlines()[:10]:
                        log("HTTP-IN", f"  {line}")
                except Exception:
                    log("HTTP-IN", f"  (raw bytes: {raw[:80]!r})")
                conn.close()
            except socket.timeout:
                continue
            except Exception:
                break
        srv.close()
    except OSError as e:
        log("SYSTEM", f"Layer 3 porta {port}: non disponibile ({e})")


# ─────────────────────────────────────────────────────────
# LAYER 4: Bluetooth RFCOMM / SPP sniffer (Windows WMI)
# ─────────────────────────────────────────────────────────
def monitor_bluetooth_wmi():
    try:
        import wmi
        c = wmi.WMI()
        devices = c.Win32_PnPEntity(PNPClass="Bluetooth")
        if devices:
            log("BT-WMI", f"Device Bluetooth rilevati: {len(devices)}")
            for d in devices:
                log("BT-WMI", f"  → {d.Name} | DeviceID: {d.DeviceID[:60]}")
        else:
            log("BT-WMI", "Nessun device Bluetooth PnP rilevato.")
    except ImportError:
        log("SYSTEM", "INFO: wmi non installato, salto Layer 4 (WMI). "
            "Puoi installarlo con: pip install wmi")
    except Exception as e:
        log("BT-WMI", f"Errore WMI: {e}")


# ─────────────────────────────────────────────────────────
# LAYER 5: Monitor connessioni TCP attive (netstat-like)
# Fotografia prima/dopo pressione
# ─────────────────────────────────────────────────────────
def snapshot_connections(label: str):
    try:
        import subprocess
        result = subprocess.run(
            ["netstat", "-ano", "-p", "TCP"],
            capture_output=True, text=True, timeout=5
        )
        lines = [l for l in result.stdout.splitlines()
                 if "ESTABLISHED" in l or "CLOSE_WAIT" in l]
        log("NET-SNAP", f"--- {label} ({len(lines)} connessioni attive) ---")
        for l in lines[:20]:
            log("NET-SNAP", f"  {l.strip()}")
    except Exception as e:
        log("NET-SNAP", f"Errore: {e}")


# ─────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────
def main():
    print("\n" + "="*60)
    print("  ZENTRA — Smartwatch BTH Protocol Diagnostic")
    print("="*60)
    print(f"  Monitoraggio per {MONITOR_SECONDS}s su tutti i layer")
    print(f"  Log salvato in: {LOG_FILE}")
    print("="*60 + "\n")

    # Layer 4 (WMI info snapshot)
    monitor_bluetooth_wmi()

    # Layer 3 (HTTP listeners) su porte comuni
    for port in [5000, 5001, 8080, 8888, 9000]:
        t = threading.Thread(target=network_listener, args=(port,), daemon=True)
        t.start()

    # Layer 5 snapshot PRIMA
    snapshot_connections("PRIMA della pressione")

    # Layer 1 (pynput)
    monitor_keyboard()

    # Layer 2 (keyboard lib)
    monitor_keyboard_raw()

    print("\n" + "="*60)
    print("  ✅ PRONTO — PREMI IL PULSANTE SULLO SMARTWATCH")
    print("  (premi 3-4 volte, sia corto che lungo)")
    print("  Per terminare: CTRL+C")
    print("="*60 + "\n")

    try:
        time.sleep(MONITOR_SECONDS)
    except KeyboardInterrupt:
        pass

    # Layer 5 snapshot DOPO
    snapshot_connections("DOPO della pressione")

    # ─── REPORT FINALE ────────────────────────────────────
    print("\n" + "="*60)
    print("  📋 REPORT FINALE")
    print("="*60)

    hid_events  = [e for e in events if "HID-KEY" in e or "RAW-KB" in e]
    http_events = [e for e in events if "HTTP-IN" in e]
    bt_events   = [e for e in events if "BT-WMI" in e]

    if hid_events:
        print(f"\n✅ TROVATO: Lo smartwatch invia TASTI HID ({len(hid_events)} eventi)")
        print("   → Protocollo: Bluetooth HID (tastiera/media keys)")
        print("   → Fix: aggiornare ptt_bus.py con i VK codes trovati")
        print("\n   Dettaglio eventi HID:")
        for e in hid_events[:30]:
            print(f"     {e}")
    else:
        print("\n❌ Nessun tasto HID rilevato.")

    if http_events:
        print(f"\n✅ TROVATO: Lo smartwatch invia richieste HTTP ({len(http_events)} eventi)")
        print("   → Protocollo: HTTP webhook")
        print("   → Fix: aggiungere /api/audio/ptt/trigger in routes_audio.py")
        for e in http_events[:20]:
            print(f"     {e}")
    else:
        print("❌ Nessuna connessione HTTP rilevata.")

    if not hid_events and not http_events:
        print("\n⚠️  NESSUN SEGNALE RILEVATO con i layer attivi.")
        print("   Possibili cause:")
        print("   1. Il device usa GATT BLE (Bluetooth Low Energy) — non intercettato da pynput")
        print("   2. Il device parla direttamente con un'app Windows (Companion App)")
        print("   3. Il Bluetooth non era connesso durante il test")
        print("\n   Prossimo step: controlla il Bluetooth in Device Manager =>")
        print("   Pannello di controllo > Dispositivi e Stampanti > cerca lo smartwatch")
        print("   oppure esegui in PowerShell:")
        print('   Get-PnpDevice | Where-Object { $_.Class -eq "Bluetooth" } | Select Name, Status')

    # Salva log
    try:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(events))
        print(f"\n📁 Log completo salvato in: {LOG_FILE}")
    except Exception as e:
        print(f"\n⚠️  Impossibile salvare log: {e}")

    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    main()
