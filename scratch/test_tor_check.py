import sys
sys.path.insert(0, r"c:\Hecos")

try:
    from hecos.modules.browser_automation.search import http_client
    print("Imported http_client successfully.")
    
    # 1. Test clear web
    print("\n[1] Testing clear web...")
    r = http_client.get("https://check.torproject.org/api/ip", network="clear", timeout=10)
    print("Clear IP check:", r.json())
    
    # 2. Test Tor proxy with check.torproject.org
    print("\n[2] Testing Tor clear check...")
    r_tor = http_client.get("https://check.torproject.org/api/ip", network="tor", timeout=15)
    print("Tor IP check:", r_tor.json())
    
    # 3. Test well-known fast onion: DuckDuckGo onion
    print("\n[3] Testing DuckDuckGo Onion...")
    ddg_onion = "https://duckduckgogg42xjoc72x3sjasowoarfbgcmvfimaftt6twagswzczad.onion"
    r_ddg = http_client.get(ddg_onion, network="tor", timeout=25)
    print("DDG Onion status:", r_ddg.status_code, "Length:", len(r_ddg.text))
    
    # 4. Test Ahmia onion
    print("\n[4] Testing Ahmia Onion...")
    ahmia_onion = "http://juhanurmihxlp77nkq76byazcldy2hlmovfu2epvl5ankdibsot4csyd.onion"
    r_ahmia = http_client.get(ahmia_onion, network="tor", timeout=25)
    print("Ahmia Onion status:", r_ahmia.status_code, "Length:", len(r_ahmia.text))
    
    # 5. Test the specific onion user tried
    print("\n[5] Testing user's target onion...")
    user_onion = "http://kidflix4yta3cu5a7skyyi7gdxgqbx4jiyx4uriem4ecv445frkpfcid.onion/?clickid=d805"
    try:
        r_user = http_client.get(user_onion, network="tor", timeout=20)
        print("User Onion status:", r_user.status_code)
    except Exception as e:
        print("User Onion failed as expected:", type(e).__name__, str(e))
        
except Exception as e:
    import traceback
    traceback.print_exc()
