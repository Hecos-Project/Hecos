"""Modulo principale del plugin Sys_Net. Gestione di Rete e DNS."""
import subprocess
import re
import os
import ctypes

try:
    from core.logging import logger
    from core.i18n import translator
    from app.config import ConfigManager
    from core.system.os_adapter import OSAdapter
except ImportError:
    class DummyLogger:
        def debug(self, *args, **kwargs): print("[SYS_NET]", *args)
        def info(self, *args, **kwargs): print("[SYS_NET_INFO]", *args)
        def error(self, *args, **kwargs): print("[SYS_NET_ERR]", *args)
    logger = DummyLogger()
    class DummyTranslator:
        def t(self, key, **kwargs): return key
    translator = DummyTranslator()
    class DummyConfig:
        def get_plugin_config(self, tag, key, default): return default
    def FakeConfigManager(): return DummyConfig()
    ConfigManager = FakeConfigManager

def is_admin():
    """Returns True if Zentra is running with Windows Administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False

class SysNetTools:
    """
    Plugin: Sys_Net
    Advanced networking tools for Zentra. Allows the AI to map the local network,
    check public IP, ping servers, and actively modify DNS configuration to bypass
    censorship or regional blocks.
    """

    def __init__(self):
        self.tag = "SYS_NET"
        self.desc = "Strumenti di rete avanzati: IP, Ping, Stato Proxy, Mappatura LAN e VPN/DNS."
        self.status = "Online"
        
        self.config_schema = {
            "proxy_url": {
                "type": "str",
                "default": "",
                "description": "URL completo del Proxy (es. socks5://127.0.0.1:2080 o http://ip:port). Lascia vuoto per non usare nessun proxy."
            }
        }

    def _get_proxy_url(self) -> str:
        """Helper: returns the configured proxy_url from SYS_NET settings."""
        try:
            return ConfigManager().get_plugin_config(self.tag, "proxy_url", "").strip()
        except:
            return ""

    # --- PHASE 1: NETWORK AWARENESS (READING) ---

    def get_public_ip(self) -> str:
        """
        Interrogates an external service to find the current public outbound IP address.
        Useful to verify if a VPN is active or to know the internet location of the system.
        """
        logger.debug(f"PLUGIN_{self.tag}", "Fetching public IP...")
        try:
            import urllib.request
            req = urllib.request.Request("https://api.ipify.org")
            with urllib.request.urlopen(req, timeout=5) as response:
                ip = response.read().decode("utf-8")
                return f"Il mio indirizzo IP pubblico attuale è: {ip}"
        except Exception as e:
            logger.error(f"Failed to fetch public IP: {e}")
            return f"Errore nel recuperare l'IP pubblico: {e}"

    def get_proxy_status(self) -> str:
        """
        Reports the current proxy configuration status in Zentra, including the URL and whether it is active.
        Also verifies the live outgoing IP with and without the proxy to confirm if it is working.
        """
        proxy_url = self._get_proxy_url()
        logger.debug(f"PLUGIN_{self.tag}", f"Checking proxy status: {proxy_url!r}")

        if not proxy_url:
            # Try to get direct IP for reference
            try:
                import urllib.request
                ip = urllib.request.urlopen("https://api.ipify.org", timeout=5).read().decode()
            except:
                ip = "(non disponibile)"
            return (
                f"**Stato Proxy Zentra: DISATTIVO** ❌\n"
                f"Nessun proxy configurato in Zentra. Le richieste usano la connessione diretta.\n"
                f"IP pubblico corrente (connessione diretta): `{ip}`\n\n"
                f"Per attivare un proxy, vai su Impostazioni → Sys Net e inserisci un URL proxy."
            )

        # Parse the proxy URL for display
        try:
            import re
            m = re.match(r'^(\w+)://(?:[^@]+@)?([^:/]+):(\d+)$', proxy_url)
            if m:
                proto, host, port = m.group(1), m.group(2), m.group(3)
                proxy_display = f"{proto}://{host}:{port}"
            else:
                proxy_display = proxy_url
        except:
            proxy_display = proxy_url

        # Try to reach ipify through the configured proxy
        try:
            import requests
            proxies = {"http": proxy_url, "https": proxy_url}
            r = requests.get("https://api.ipify.org?format=json", proxies=proxies, timeout=10)
            if r.status_code == 200:
                ip_via_proxy = r.json().get('ip', 'N/A')
                return (
                    f"**Stato Proxy Zentra: ATTIVO** ✅\n"
                    f"Proxy configurato: `{proxy_display}`\n"
                    f"IP pubblico in uscita (via proxy): `{ip_via_proxy}`\n"
                    f"Il proxy funziona correttamente. Gemini e altri provider IA utilizzeranno questo IP."
                )
            else:
                return (
                    f"**Stato Proxy Zentra: ERRORE** ⚠️\n"
                    f"Proxy configurato: `{proxy_display}`\n"
                    f"Il proxy ha risposto con codice HTTP {r.status_code}. Verificare l'indirizzo."
                )
        except Exception as e:
            return (
                f"**Stato Proxy Zentra: IRRAGGIUNGIBILE** ❌\n"
                f"Proxy configurato: `{proxy_display}`\n"
                f"Impossibile connettersi al proxy. Dettaglio errore: {e}\n"
                f"Verificare che il servizio proxy sia avviato e l'indirizzo sia corretto."
            )

    def get_network_info(self) -> str:
        """
        Runs ipconfig to extract local IPv4, Subnet, Default Gateway, and active DNS servers.
        Provides a comprehensive overview of the current adapter's configuration.
        """
        logger.debug(f"PLUGIN_{self.tag}", "Reading local IP config...")
        try:
            cmd = OSAdapter.get_network_info_cmd()
            output = subprocess.check_output(cmd, shell=True, text=True, errors='replace', stderr=subprocess.STDOUT)
            
            cfg_proxy = ConfigManager().get_plugin_config(self.tag, "proxy_url", "")
            proxy_info = f"\nZentra Configured Proxy: {cfg_proxy if cfg_proxy else 'None'}"
            
            if OSAdapter.get_os() != 'windows':
                return output[:2000] + proxy_info

            # We filter for the active adapter (ones that have IPv4 Address) on Windows
            lines = output.split('\n')
            results = []
            
            adapter_name = ""
            for line in lines:
                l = line.strip()
                if not l: continue
                # Match adapter name e.g. "Wireless LAN adapter Wi-Fi:"
                if not l.startswith(" ") and l.endswith(":"):
                    adapter_name = l[:-1]
                if "IPv4" in l or "Gateway" in l or "DNS Servers" in l and "IPv6" not in l:
                    results.append(f"[{adapter_name}] {l}")
            
            cfg_proxy = ConfigManager().get_plugin_config(self.tag, "proxy_url", "")
            proxy_info = f"\nZentra Configured Proxy: {cfg_proxy if cfg_proxy else 'None'}"
            
            if not results:
                return output[:1000] + proxy_info
            return "Local Network Configuration:\n" + "\n".join(results) + proxy_info
        except Exception as e:
            return f"Error fetching local network info: {e}"

    def test_proxy(self) -> str:
        """
        Tests the configured Proxy by attempting to reach an external service and reports the visible IP.
        Useful to verify if the proxy configuration bypasses geographic blocks successfully.
        """
        return self.get_proxy_status()

    def ping_test(self, target: str) -> str:
        """
        Executes a network ping test to the specified target (IP or domain).
        Useful to check latency or verify if a domain/server is reachable.
        
        :param target: The domain name (e.g., 'google.com') or IP address to ping.
        """
        logger.debug(f"PLUGIN_{self.tag}", f"Pinging {target}...")
        try:
            target = re.sub(r'[^a-zA-Z0-9.-]', '', target) # Sanitize input
            if not target: return "Invalid target"
            
            cmd = OSAdapter.get_ping_cmd(target, count=4)
            output = subprocess.check_output(cmd, shell=True, text=True, errors='replace', stderr=subprocess.STDOUT)
            return output
        except subprocess.CalledProcessError as e:
            return f"Ping failed or destination unreachable:\n{e.output}"
        except Exception as e:
            return f"Error executing ping: {e}"

    def scan_local_network(self) -> str:
        """
        Executes an ARP scan ('arp -a') to discover active devices connected to the same LAN.
        """
        logger.debug(f"PLUGIN_{self.tag}", "Scanning local network (ARP)...")
        try:
            cmd = OSAdapter.get_arp_cmd()
            output = subprocess.check_output(cmd, shell=True, text=True, errors='replace', stderr=subprocess.STDOUT)
            return output
        except subprocess.CalledProcessError as e:
            return f"ARP scan failed:\n{e.output}"
        except Exception as e:
            return f"Error scanning network: {e}"

    # --- PHASE 2: DNS MANAGEMENT (WRITING - ADMIN REQUIRED) ---

    def _get_active_interface(self) -> str:
        """Helper: returns the exact name of the active network interface (e.g. 'Wi-Fi' or 'Ethernet')."""
        try:
            # netsh interface show interface -> extracts the "Connected" one
            output = subprocess.check_output("netsh interface show interface", shell=True, text=True)
            for line in output.split('\n'):
                if "Connected" in line or "Connesso" in line:
                    # columns are Admin State, State, Type, Interface Name
                    parts = re.split(r'\s{2,}', line.strip())
                    if len(parts) >= 4:
                        return parts[-1]
            return "Wi-Fi" # Safe fallback
        except:
            return "Wi-Fi"

    def set_dns_servers(self, primary: str, secondary: str) -> str:
        """
        Changes the DNS servers of the active network adapter to bypass ISP level blocking.
        Requires Zentra to be running as Administrator!
        Common safe DNS: 8.8.8.8/8.8.4.4 (Google), 1.1.1.1/1.0.0.1 (Cloudflare).
        
        :param primary: The primary DNS IPv4 address.
        :param secondary: The secondary DNS IPv4 address.
        """
        if OSAdapter.get_os() != 'windows':
            return "ERROR: DNS configuration is currently supported only on Windows."
            
        if not is_admin():
            logger.warning("[SysNet] Attempted to change DNS without Admin privileges.")
            return "PERMISSION DENIED: Modifying DNS requires Zentra to be running as Windows Administrator. Please restart Zentra as Admin."

        interface = self._get_active_interface()
        logger.info(f"[SysNet] Changing DNS for interface '{interface}' to {primary}, {secondary}")
        
        try:
            # Set primary
            cmd1 = f'netsh interface ipv4 set dnsservers name="{interface}" static {primary} primary'
            subprocess.check_output(cmd1, shell=True, text=True, stderr=subprocess.STDOUT)
            
            # Set secondary
            if secondary:
                cmd2 = f'netsh interface ipv4 add dnsservers name="{interface}" {secondary} index=2'
                subprocess.check_output(cmd2, shell=True, text=True, stderr=subprocess.STDOUT)
                
            return f"SUCCESS: DNS servers for '{interface}' explicitly set to {primary} and {secondary}."
        except subprocess.CalledProcessError as e:
            return f"Error setting DNS (Is the interface name correct?): {e.output}"
        except Exception as e:
            return f"Fatal error setting DNS: {e}"

    def reset_dns(self) -> str:
        """
        Restores the DNS configuration of the active network adapter back to DHCP (automatic).
        Requires Zentra to be running as Administrator!
        """
        if OSAdapter.get_os() != 'windows':
            return "ERROR: DNS configuration is currently supported only on Windows."

        if not is_admin():
            logger.warning("[SysNet] Attempted to reset DNS without Admin privileges.")
            return "PERMISSION DENIED: Resetting DNS requires Zentra to be running as Windows Administrator."

        interface = self._get_active_interface()
        logger.info(f"[SysNet] Resetting DNS for interface '{interface}' to DHCP (Automatic)")
        
        try:
            cmd = f'netsh interface ipv4 set dnsservers name="{interface}" source=dhcp'
            subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.STDOUT)
            return f"SUCCESS: DNS configuration for '{interface}' restored to Automatic (DHCP)."
        except subprocess.CalledProcessError as e:
            return f"Error resetting DNS: {e.output}"

# Export the tools
tools = SysNetTools()

def info():
    return {"tag": tools.tag, "desc": tools.desc}

def status():
    return tools.status

def execute(comando: str) -> str:
    """Compatibilità legacy (tag-based): smista comandi testuali ai nuovi metodi."""
    c = comando.strip()
    c_lower = c.lower()

    if c_lower in ("get_public_ip", "ip", "public_ip", "mio_ip"):
        return tools.get_public_ip()
    elif c_lower in ("get_proxy_status", "proxy_status", "stato_proxy", "test_proxy", "testa_proxy", "testa_connessione_proxy"):
        return tools.get_proxy_status()
    elif c_lower in ("get_network_info", "network_info", "rete", "network"):
        return tools.get_network_info()
    elif c_lower in ("scan_local_network", "scan", "scan_lan", "arp", "scansione"):
        return tools.scan_local_network()
    elif c_lower.startswith("ping:") or c_lower.startswith("ping_test:"):
        target = c.split(":", 1)[1].strip()
        return tools.ping_test(target)
    elif c_lower.startswith("set_dns:"):
        parts = c.split(":", 1)[1].strip().split(",")
        primary = parts[0].strip() if parts else ""
        secondary = parts[1].strip() if len(parts) > 1 else ""
        return tools.set_dns_servers(primary, secondary)
    elif c_lower in ("reset_dns", "dhcp_dns"):
        return tools.reset_dns()

    return f"Errore: Comando '{comando}' non riconosciuto nel plugin {tools.tag}. Usa i Function Tools nativi."
