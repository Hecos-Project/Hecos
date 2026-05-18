from hecos.tray.network_utils import get_scheme, get_urls, get_lan_ip, is_hecos_online
from hecos.tray.system_utils import play_beep, get_version, launch_console, terminate_consoles
from hecos.tray.browser_manager import (
    get_cdp_alive, set_cdp_alive, discover_browsers, launch_browser,
    launch_ai_ready_browser, is_ai_ready_browser_running, _get_cdp_port
)
