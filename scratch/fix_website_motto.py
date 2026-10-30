about_path = r"C:\Hecos-Website\about.html"
css_path = r"C:\Hecos-Website\assets\css\style.css"

# 1. Update about.html - Remove the duplicate quote under creator photo
with open(about_path, "r", encoding="utf-8") as f:
    about_content = f.read()

target_quote_block = """                <p style=\"font-size: 1.12rem; color: #fff; border-left: 3px solid var(--accent); padding-left: 16px; font-style: italic; background: rgba(108,140,255,0.06); padding-top: 10px; padding-bottom: 10px; border-radius: 0 8px 8px 0; margin-bottom: 18px;\">
                    &ldquo;Zero moral filters. Zero social bias. Zero political agendas. From the core engine to every single module, Hecos is built on one unshakeable rule: freedom of thought belongs to everyone.&rdquo;
                </p>"""

if target_quote_block in about_content:
    about_content = about_content.replace(target_quote_block + "\n                \n", "")
    about_content = about_content.replace(target_quote_block + "\n", "")
    with open(about_path, "w", encoding="utf-8") as f:
        f.write(about_content)
    print("Successfully removed duplicate motto from creator section in about.html")
else:
    # Try more flexible replacement if whitespace differed
    import re
    pattern = r'<p style="font-size: 1\.12rem;[^>]+>[\s\S]*?freedom of thought belongs to everyone\.&rdquo;\s*</p>\s*'
    if re.search(pattern, about_content):
        about_content = re.sub(pattern, "", about_content)
        with open(about_path, "w", encoding="utf-8") as f:
            f.write(about_content)
        print("Successfully removed duplicate motto using regex in about.html")
    else:
        print("Warning: target quote block not found in about.html")

# 2. Update style.css - Add the prominent blue border line (border-left: 4px solid var(--accent)) to motto-card
with open(css_path, "r", encoding="utf-8") as f:
    css_content = f.read()

old_card = """.motto-card {
  position: relative;
  background: linear-gradient(135deg, rgba(20, 23, 38, 0.95) 0%, rgba(28, 32, 51, 0.95) 100%);
  border: 1px solid rgba(108, 140, 255, 0.35);
  border-radius: 14px;
  padding: 26px 32px;
  text-align: center;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5), 0 0 25px rgba(108, 140, 255, 0.15);
  backdrop-filter: blur(12px);
  overflow: hidden;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}"""

new_card = """.motto-card {
  position: relative;
  background: linear-gradient(135deg, rgba(20, 23, 38, 0.95) 0%, rgba(28, 32, 51, 0.95) 100%);
  border: 1px solid rgba(108, 140, 255, 0.25);
  border-left: 4px solid var(--accent);
  border-radius: 0 14px 14px 0;
  padding: 26px 32px;
  text-align: center;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5), 0 0 25px rgba(108, 140, 255, 0.15), -4px 0 16px rgba(108, 140, 255, 0.35);
  backdrop-filter: blur(12px);
  overflow: hidden;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}"""

if old_card in css_content:
    css_content = css_content.replace(old_card, new_card)
    with open(css_path, "w", encoding="utf-8") as f:
        f.write(css_content)
    print("Successfully updated motto-card in style.css with prominent blue accent line.")
else:
    print("Note: old_card exact match not found or already updated.")
