import re
from pathlib import Path

about_path = Path(r"C:\Hecos-Website\about.html")
features_path = Path(r"C:\Hecos-Website\features.html")

# 1. Update about.html: remove motto card
about_content = about_path.read_text(encoding="utf-8")
pattern = r"\s*<!-- CORE MOTTO / MANIFESTO -->[\s\S]*?</div>\s*</div>\s*(?=\s*<section class=\"creator-section\">)"
new_about, count = re.subn(pattern, "\n\n        ", about_content)
if count > 0:
    about_path.write_text(new_about, encoding="utf-8")
    print(f"[OK] Removed motto from about.html (matches: {count})")
else:
    print("[!] Warning: Motto pattern not found in about.html")

# 2. Update features.html: add Net Search card right after Browser Automation
features_content = features_path.read_text(encoding="utf-8")

netsearch_card = """                <div class="card card-accent2">
                    <span class="card-icon" style="display:inline-flex; align-items:center; filter: drop-shadow(0 0 8px rgba(255, 140, 0, 0.4)); color: #ff9d2e;">
                        <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <circle cx="11" cy="11" r="8"></circle>
                            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                        </svg>
                    </span>
                    <div class="card-title">Net Search (Uncensored Web Engine)</div>
                    <p>An autonomous deep retrieval engine engineered to locate and recover any file across the global network. Operating with <strong>zero censorship, zero moral filters, and no content limits</strong>, it aggregates multi-engine clear web search, advanced file dorking, media stream extractors, OSINT tracking, and native Tor (.onion) routing to find any file or resource with absolute freedom.</p>
                </div>"""

browser_automation_marker = """                <div class="card card-green">
                    <span class="card-icon">🌍</span>
                    <div class="card-title">Browser Automation</div>
                    <p>Interact semantically with web pages via a managed Chromium instance. Navigate, click, extract data, and automate browser-based workflows.</p>
                </div>"""

if "Net Search (Uncensored Web Engine)" not in features_content:
    if browser_automation_marker in features_content:
        features_content = features_content.replace(
            browser_automation_marker,
            browser_automation_marker + "\n" + netsearch_card
        )
        features_path.write_text(features_content, encoding="utf-8")
        print("[OK] Net Search card added to features.html right after Browser Automation")
    else:
        # Fallback to end of grid
        grid_end = "            </div>\n        </section>"
        features_content = features_content.replace(grid_end, netsearch_card + "\n" + grid_end)
        features_path.write_text(features_content, encoding="utf-8")
        print("[OK] Net Search card added to features.html before end of grid")
else:
    print("[!] Net Search card is already present in features.html")
