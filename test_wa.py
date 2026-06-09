
from playwright.sync_api import sync_playwright
import sys
try:
    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp('http://localhost:9222')
        print('Connected:', len(browser.contexts[0].pages), 'pages')
except Exception as e:
    print('Error:', e)
