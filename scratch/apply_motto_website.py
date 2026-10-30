import os

css_path = r"C:\Hecos-Website\assets\css\style.css"
index_path = r"C:\Hecos-Website\index.html"
about_path = r"C:\Hecos-Website\about.html"

# 1. Update style.css
motto_css = """
/* ─── Core Motto / Manifesto Banner ──────────────────────────────────────── */
.motto-banner-wrap {
  margin: 32px auto 35px;
  max-width: 860px;
  width: 100%;
  padding: 0 16px;
  box-sizing: border-box;
}

.motto-card {
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
}

.motto-card::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, #6c8cff 25%, #a78bfa 50%, #ff8c00 75%, transparent);
}

.motto-card:hover {
  border-color: rgba(108, 140, 255, 0.55);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.6), 0 0 35px rgba(108, 140, 255, 0.28);
  transform: translateY(-2px);
}

.motto-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 5px 14px;
  border-radius: 20px;
  background: rgba(255, 140, 0, 0.12);
  border: 1px solid rgba(255, 140, 0, 0.35);
  color: #ff9d2e;
  font-size: 11px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 1.5px;
  margin-bottom: 14px;
}

.motto-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #ff8c00;
  box-shadow: 0 0 8px #ff8c00;
  animation: mottoPulse 2s infinite ease-in-out;
}

@keyframes mottoPulse {
  0%, 100% { opacity: 0.5; transform: scale(0.9); }
  50% { opacity: 1; transform: scale(1.2); box-shadow: 0 0 12px #ff8c00; }
}

.motto-quote {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 600;
  line-height: 1.7;
  color: var(--text);
  font-family: var(--font-sans);
  letter-spacing: -0.2px;
}

.motto-highlight-primary {
  color: #ffffff;
  font-weight: 800;
  text-shadow: 0 0 14px rgba(255, 255, 255, 0.2);
}

.motto-highlight-gradient {
  background: linear-gradient(135deg, #6c8cff 0%, #a78bfa 50%, #f472b6 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  font-weight: 800;
  letter-spacing: 0.3px;
}

@media (max-width: 768px) {
  .motto-banner-wrap {
    margin: 24px auto 28px;
    padding: 0 12px;
  }
  .motto-card {
    padding: 20px 18px;
  }
  .motto-quote {
    font-size: 1rem;
    line-height: 1.6;
  }
}
"""

with open(css_path, "r", encoding="utf-8") as f:
    css_content = f.read()

if ".motto-banner-wrap" not in css_content:
    with open(css_path, "a", encoding="utf-8") as f:
        f.write("\n" + motto_css)
    print("CSS updated successfully in", css_path)
else:
    print("CSS already contains motto styles.")

# 2. Update index.html
motto_html_index = """
            <!-- CORE MOTTO / MANIFESTO -->
            <div class="motto-banner-wrap">
                <div class="motto-card">
                    <div class="motto-pill">
                        <span class="motto-dot"></span>
                        <span>Our Unshakeable Motto</span>
                    </div>
                    <blockquote class="motto-quote">
                        <span class="motto-highlight-primary">Zero moral filters. Zero social bias. Zero political agendas.</span><br>
                        From the core engine to every single module, Hecos is built on one unshakeable rule:<br>
                        <span class="motto-highlight-gradient">Freedom of thought belongs to everyone.</span>
                    </blockquote>
                </div>
            </div>
"""

with open(index_path, "r", encoding="utf-8") as f:
    index_content = f.read()

if "Our Unshakeable Motto" not in index_content:
    slideshow_marker = "<!-- start slideshow -->"
    if slideshow_marker in index_content:
        index_content = index_content.replace(slideshow_marker, motto_html_index + "\n            " + slideshow_marker)
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(index_content)
        print("index.html updated successfully with motto banner.")
    else:
        print("Error: Could not find slideshow marker in index.html")
else:
    print("index.html already contains motto banner.")

# 3. Update about.html
motto_html_about = """
        <!-- CORE MOTTO / MANIFESTO -->
        <div class="motto-banner-wrap" style="margin: 0 auto 30px;">
            <div class="motto-card">
                <div class="motto-pill">
                    <span class="motto-dot"></span>
                    <span>Core Manifesto &amp; Motto</span>
                </div>
                <blockquote class="motto-quote">
                    <span class="motto-highlight-primary">Zero moral filters. Zero social bias. Zero political agendas.</span><br>
                    From the core engine to every single module, Hecos is built on one unshakeable rule:<br>
                    <span class="motto-highlight-gradient">Freedom of thought belongs to everyone.</span>
                </blockquote>
            </div>
        </div>
"""

with open(about_path, "r", encoding="utf-8") as f:
    about_content = f.read()

if "Core Manifesto &amp; Motto" not in about_content:
    creator_sec_marker = '<section class="creator-section">'
    if creator_sec_marker in about_content:
        about_content = about_content.replace(creator_sec_marker, motto_html_about + "\n        " + creator_sec_marker)
    
    # Also add the quote under Adapting Technology for Humanity
    target_heading = "<h3>Adapting Technology for Humanity</h3>"
    quote_tony = """<h3>Adapting Technology for Humanity</h3>
                <p style="font-size: 1.12rem; color: #fff; border-left: 3px solid var(--accent); padding-left: 16px; font-style: italic; background: rgba(108,140,255,0.06); padding-top: 10px; padding-bottom: 10px; border-radius: 0 8px 8px 0; margin-bottom: 18px;">
                    &ldquo;Zero moral filters. Zero social bias. Zero political agendas. From the core engine to every single module, Hecos is built on one unshakeable rule: freedom of thought belongs to everyone.&rdquo;
                </p>"""
    if target_heading in about_content and quote_tony not in about_content:
        about_content = about_content.replace(target_heading, quote_tony)

    with open(about_path, "w", encoding="utf-8") as f:
        f.write(about_content)
    print("about.html updated successfully with motto banner and quote.")
else:
    print("about.html already contains motto.")
