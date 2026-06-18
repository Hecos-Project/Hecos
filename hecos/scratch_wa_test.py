from playwright.sync_api import sync_playwright
try:
    with sync_playwright() as pw:
        b = pw.chromium.connect_over_cdp('http://127.0.0.1:9222')
        pages = [p for c in b.contexts for p in c.pages if 'web.whatsapp.com' in p.url]
        if pages:
            pg = pages[0]
            boxes = pg.evaluate('''() => {
                let els = document.querySelectorAll('div[contenteditable="true"]');
                return Array.from(els).map(e => e.outerHTML.substring(0, 300));
            }''')
            for b in boxes: print(b)
except Exception as e:
    print(e)
