from playwright.sync_api import sync_playwright

def run_cuj(page):
    page.goto("http://localhost:3000")
    page.wait_for_timeout(2000)

    # We must setup dialog handler BEFORE we trigger it
    page.on("dialog", lambda dialog: dialog.accept())

    # Switch to ML Tab via JS or selector
    page.evaluate("switchTab('tab-ml')")
    page.wait_for_timeout(1000)

    # Open details
    page.evaluate("document.querySelector('summary').click()")
    page.wait_for_timeout(500)

    # Click the start button
    page.evaluate("startMLTraining()")
    page.wait_for_timeout(2000)

    page.screenshot(path="/home/jules/verification/screenshots/verification.png")

if __name__ == "__main__":
    import os
    os.makedirs("/home/jules/verification/screenshots", exist_ok=True)
    os.makedirs("/home/jules/verification/videos", exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            record_video_dir="/home/jules/verification/videos"
        )
        page = context.new_page()
        try:
            run_cuj(page)
        finally:
            context.close()
            browser.close()
