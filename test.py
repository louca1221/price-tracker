import os
import asyncio
import requests
from datetime import datetime
from playwright.async_api import async_playwright

# --- CONFIG (Maps to GitHub Secrets) ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SMM_EMAIL = os.getenv("SMM_EMAIL")
SMM_PASSWORD = os.getenv("SMM_PASSWORD")
URL = "https://www.metal.com/Lithium/201906260003"

def send_msg(text):
    """Sends the final report or error logs to Telegram."""
    if not TOKEN or not CHAT_ID:
        print("❌ FAILED: Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID")
        return

    chat_ids = [cid.strip() for cid in CHAT_ID.split(",") if cid.strip()]
    for chat_id in chat_ids:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        try:
            requests.post(url, data={"chat_id": chat_id, "text": text}, timeout=15)
        except Exception as e:
            print(f"❌ Telegram Error: {e}")

async def get_data():
    """Main scraping logic using Playwright."""
    async with async_playwright() as p:
        # Launching with a standard user-agent to avoid basic bot detection
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            print(f"🌐 Navigating to {URL}...")
            await page.goto(URL, wait_until="networkidle", timeout=60000)
            
            # 1. Trigger Login Modal via JS (Bypasses transparent overlays)
            print("🔑 Opening Login Modal...")
            await page.evaluate('''() => {
                const elements = document.querySelectorAll('div, span, a, button');
                const loginBtn = Array.from(elements).find(el => el.textContent.trim() === 'Sign In');
                if (loginBtn) loginBtn.click();
            }''')

            # 2. Fill Credentials via JS (Bypasses "intercepted pointer" errors)
            print("📝 Entering credentials...")
            email_selector = 'input[type="email"], input[placeholder*="Email"]'
            await page.wait_for_selector(email_selector, state="attached", timeout=15000)

            await page.evaluate(f'''(e, p) => {{
                const email = document.querySelector('input[type="email"], input[placeholder*="Email"]');
                const pass = document.querySelector('input[type="password"]');
                if (email) {{
                    email.value = e;
                    email.dispatchEvent(new Event('input', {{ bubbles: true }}));
                }}
                if (pass) {{
                    pass.value = p;
                    pass.dispatchEvent(new Event('input', {{ bubbles: true }}));
                }}
            }}''', SMM_EMAIL, SMM_PASSWORD)

            # 3. Submit and wait for modal to close
            print("⏳ Submitting login...")
            await page.evaluate('document.querySelector("button[type=\'submit\'], .ant-btn-primary").click()')
            
            # Wait for the login modal to disappear from the DOM
            try:
                await page.wait_for_selector(".ant-modal", state="hidden", timeout=10000)
                print("✅ Login successful, modal closed.")
            except:
                print("⚠️ Modal still visible, forcing refresh...")

            # 4. Re-navigate to refresh data with logged-in permissions
            print(f"🚀 Refreshing data page...")
            await page.goto(URL, wait_until="networkidle")
            await page.wait_for_timeout(5000) # Buffer for price to render

            # 5. Extract Price and Change using partial class matches
            print("📊 Extracting data...")
            
            # Find the Average Price
            price_locator = page.locator("div[class*='__avg']").first
            await price_locator.wait_for(state="visible", timeout=20000)
            price = await price_locator.inner_text()
            
            # Find the Change (Parent wrap contains both price and the change spans)
            # We grab the text and subtract the price to get the remainder (the change)
            wrap_locator = page.locator("div[class*='__price']").first
            full_text = await wrap_locator.inner_text()
            
            # Clean up: Replace newlines and remove the price portion
            clean_full = full_text.replace('\n', ' ').strip()
            change = clean_full.replace(price.strip(), "").strip()

            return price.strip(), change
            
        except Exception as e:
            # Save debug image to GitHub Artifacts
            await page.screenshot(path="error_screenshot.png")
            print(f"❌ Scrape Error: {e}")
            raise e
        finally:
            await browser.close()

async def main():
    # Only run on weekdays (Monday=0, Sunday=6)
    if datetime.now().weekday() < 5:
        try:
            val_price, val_change = await get_data()
            now_str = datetime.now().strftime("%b %d, %Y - %H:%M")
            
            report = (
                f"📅 Date: {now_str}\n"
                f"📦 Spodumene Concentrate Index\n"
                f"💰 Price: {val_price} USD/mt\n"
                f"📈 Change: {val_change}"
            )
            
            send_msg(report)
            print(f"✅ SUCCESS: {val_price} | {val_change}")
            
        except Exception as e:
            error_msg = f"❌ Scrape failed: {str(e)[:100]}"
            send_msg(error_msg)
            print(error_msg)
    else:
        print("😴 Skipping: It's the weekend.")

if __name__ == "__main__":
    asyncio.run(main())
