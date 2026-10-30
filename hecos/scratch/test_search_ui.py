import os
from playwright.sync_api import sync_playwright

def run_test():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        console_logs = []
        errors = []
        page.on("console", lambda m: console_logs.append(f"[{m.type}] {m.text}"))
        page.on("pageerror", lambda e: errors.append(str(e)))

        # Load search.html content
        with open(r"C:\Hecos\hecos\modules\browser_automation\web\templates\search.html", "r", encoding="utf-8") as f:
            html = f.read()

        # Clean Jinja tags for local testing
        import re
        html = re.sub(r"\{\{.*?\}\}", "", html)
        html = re.sub(r"\{%.*?%\}", "", html)

        # Replace script src with inline scripts
        js_dir = r"C:\Hecos\hecos\modules\browser_automation\web\static\js\search"
        scripts = ["search_api.js", "search_state.js", "search_bookmarks.js", "search_results.js", "search_copilot.js", "search_main.js"]
        script_tags = ""
        for s in scripts:
            p_script = os.path.join(js_dir, s)
            with open(p_script, "r", encoding="utf-8") as sf:
                script_tags += f"\n<script>{sf.read()}</script>\n"

        html = html.replace("</body>", f"{script_tags}</body>")

        page.set_content(html, wait_until="load")

        print(f"Page loaded. Any early errors? {errors}")

        # Check window objects
        check_objs = page.evaluate("""() => {
            return {
                SearchResults: typeof window.SearchResults,
                SearchState: typeof window.SearchState,
                SearchAPI: typeof window.SearchAPI,
                BookmarksManager: typeof window.BookmarksManager,
                SearchCopilot: typeof window.SearchCopilot
            };
        }""")
        print("Window objects:", check_objs)

        # Simulate typing in #search-input and pressing Enter
        page.fill("#search-input", "cybersecurity")
        page.press("#search-input", "Enter")

        # Check what happened in state
        query_val = page.evaluate("() => window.SearchState ? window.SearchState.currentQuery : null")
        print(f"SearchState.currentQuery after Enter: '{query_val}'")

        # Now simulate incoming stream results
        sim_results = page.evaluate("""() => {
            const state = window.SearchState;
            const mockItems = [
                {
                    id: "item1",
                    title: "Tor Dark Torch Privacy Forum",
                    url: "http://torch4345345onion.onion/post/1",
                    snippet: "Hidden privacy services forum discussions.",
                    engine: "torch",
                    engine_id: "dark_torch",
                    category: "onion",
                    network: "tor"
                },
                {
                    id: "item2",
                    title: "Clear News Cyber Intel Report",
                    url: "https://clearnews.com/article/1",
                    snippet: "Latest clear web news on cybersecurity.",
                    engine: "clear_news",
                    engine_id: "clear_news",
                    category: "news",
                    network: "clearnet"
                },
                {
                    id: "item3",
                    title: "Media Video Demonstration",
                    url: "https://youtube.com/watch?v=12345",
                    snippet: "Watch the latest security video guide.",
                    engine: "youtube",
                    engine_id: "media_videos",
                    category: "videos",
                    network: "clearnet",
                    thumbnail_url: "https://i.ytimg.com/vi/12345/hqdefault.jpg"
                }
            ];

            state.addResults(mockItems);
            window.updateFilterCounts();
            window.renderCurrentView();

            return {
                totalResultsInState: state.results.length,
                countAll: document.getElementById('count-all')?.innerText,
                countDark: document.getElementById('count-dark')?.innerText,
                countVideos: document.getElementById('count-videos')?.innerText,
                renderedCards: document.querySelectorAll('#results-list .result-card').length,
                infiniteStatusText: document.getElementById('infinite-scroll-status')?.innerText
            };
        }""")
        print("Simulation step 1 (All Tab):", sim_results)

        # Switch to DarkWeb (.onion) tab
        dark_tab_res = page.evaluate("""() => {
            window.setFilter('dark', true);
            return {
                activeFilter: window.SearchState.activeFilter,
                renderedCards: document.querySelectorAll('#results-list .result-card').length,
                firstCardText: document.querySelector('#results-list .result-card')?.innerText.substring(0, 100)
            };
        }""")
        print("Dark Tab Filter:", dark_tab_res)

        # Switch to Videos tab
        videos_tab_res = page.evaluate("""() => {
            window.setFilter('videos', true);
            return {
                activeFilter: window.SearchState.activeFilter,
                renderedCards: document.querySelectorAll('#results-list .media-card, #results-list .result-card').length,
                firstCardText: document.querySelector('#results-list .media-card, #results-list .result-card')?.innerText.substring(0, 100)
            };
        }""")
        print("Videos Tab Filter:", videos_tab_res)

        print("Final console errors:", [l for l in console_logs if "[error]" in l])
        print("Final errors:", errors)

        browser.close()

if __name__ == "__main__":
    run_test()
