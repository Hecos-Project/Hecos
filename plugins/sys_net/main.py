"""Modulo principale del plugin Sys_Net. Gestione di Rete e DNS."""
import subprocess
import re
import os
import ctypes

try:
    from core.logging import logger
    from core.i18n import translator
except ImportError:
    class DummyLogger:
        def debug(self, *args, **kwargs): print("[SYS_NET]", *args)
        def info(self, *args, **kwargs): print("[SYS_NET_INFO]", *args)
        def error(self, *args, **kwargs): print("[SYS_NET_ERR]", *args)
    logger = DummyLogger()
    class DummyTranslator:
        def t(self, key, **kwargs): return key
    translator = DummyTranslator()

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
        self.desc = "Strumenti di rete avanzati: IP, Ping, Mappatura LAN, VPN/DNS."
        self.status = "Online"

    # --- PHASE 1: NETWORK AWARENESS (READING) ---

    def get_public_ip(self) -> str:
        """
        Interrogates an external service to find the current public outbound IP address.
        Useful to verify if a VPN is active or to know the internet location of the system.
        """
        logger.debug(f"PLUGIN_{self.tag}", "Fetching public IP...")
        try:
            import urllib.request
            # Fast, reliable, no key required
            req = urllib.request.Request("https://api.ipify.org")
            with urllib.request.urlopen(req, timeout=5) as response:
                ip = response.read().decode("utf-8")
                return f"My current public IP address is: {ip}"
        except Exception as e:
            logger.error(f"Failed to fetch public IP: {e}")
            return f"Error fetching public IP: {e}"

    def get_network_info(self) -> str:
        """
        Runs ipconfig to extract local IPv4, Subnet, Default Gateway, and active DNS servers.
        Provides a comprehensive overview of the current adapter's configuration.
        """
        logger.debug(f"PLUGIN_{self.tag}", "Reading local IP config...")
        try:
            output = subprocess.check_output("ipconfig /all", shell=True, text=True, stderr=subprocess.STDOUT)
            # We filter for the active adapter (ones that have IPv4 Address)
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
            
            if not results:
                return output[:1000] # Fallback raw
            return "Local Network Configuration:\n" + "\n".join(results)
        except Exception as e:
            return f"Error fetching local network info: {e}"

    def ping_test(self, target: str) -> str:
        """
        Executes a network ping test to the specified target (IP or domain).
        Useful to check latency or verify if a domain/server is reachable.
        
        :param target: The domain name (e.g., 'google.com') or IP address to ping.
        """
        logger.debug(f"PLUGIN_{self.tag}", f"Pinging {target}...")
        try:
            # We use 'ping -n 4' to send exactly 4 ICMP packets
            target = re.sub(r'[^a-zA-Z0-9.-]', '', target) # Sanitize input
            if not target: return "Invalid target"
            output = subprocess.check_output(f"ping -n 4 {target}", shell=True, text=True, stderr=subprocess.STDOUT)
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
            output = subprocess.check_output("arp -a", shell=True, text=True, stderr=subprocess.STDOUT)
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
    # Legacy wrapper if needed (we rely on native Function Calling API via get_network_info etc)
    return f"Errore: Usa i Tools nativi per Sys_Net (es. get_network_info)."
