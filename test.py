import os
import asyncio
import requests
from datetime import datetime
from playwright.async_api import async_playwright

# --- CONFIG ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SMM_EMAIL = os.getenv("SMM_EMAIL")
SMM_PASSWORD = os.getenv("SMM_PASSWORD")
URL = "https://www.metal.com/Lithium/201906260003"

def send_msg(text):
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
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            print(f"🌐 Navigating to {URL}...")
            await page.goto(URL, wait_until="networkidle", timeout=60000)
            
            # 1. Open Login Modal via JS
            print("🔑 Opening Login Modal...")
            await page.evaluate('''() => {
                const elements = document.querySelectorAll('div, span, a, button');
                const loginBtn = Array.from(elements).find(el => el.textContent.trim() === 'Sign In');
                if (loginBtn) loginBtn.click();
            }''')

            # 2. Fill Credentials (FIXED ARGUMENT PASSING)
            print("📝 Entering credentials...")
            email_selector = 'input[type="email"], input[placeholder*="Email"]'
            await page.wait_for_selector(email_selector, state="attached", timeout=15000)

            # We pass email and password as a list/tuple to satisfy evaluate()
            await page.evaluate('''([e, p]) => {
                const email = document.querySelector('input[type="email"], input[placeholder*="Email"]');
                const pass = document.querySelector('input[type="password"]');
                if (email) {
                    email.value = e;
                    email.dispatchEvent(new Event('input', { bubbles: true }));
                }
                if (pass) {
                    pass.value = p;
                    pass.dispatchEvent(new Event('input', { bubbles: true }));
                }
            }''', [SMM_EMAIL, SMM_PASSWORD])

            # 3. Submit
            print("⏳ Submitting login...")
            await page.evaluate('document.querySelector("button[type=\'submit\'], .ant-btn-primary").click()')
            
            # Wait for modal to disappear
            try:
                await page.wait_for_selector(".ant-modal", state="hidden", timeout=10000)
            except:
                pass

            # 4. Re-navigate to ensure logged-in data is visible
            print(f"🚀 Refreshing data page...")
            await page.goto(URL, wait_until="networkidle")
            await page.wait_for_timeout(5000) 

            # 5. Extract Data using your new <div> structure
            print("📊 Extracting data...")
            
            # Target the specific 'avg' class
            price_locator = page.locator("div[class*='__avg']").first
            await price_locator.wait_for(state="visible", timeout=20000)
            price = await price_locator.inner_text()
            
            # Target the parent wrap to get the full change text
            wrap_locator = page.locator("div[class*='PriceWrap']").first
            full_text = await wrap_locator.inner_text()
            
            # Clean up the output
            clean_full = full_text.replace('\n', ' ').strip()
            # Remove the price from the full string to leave just the change
            change = clean_full.replace(price.strip(), "").strip()

            return price.strip(), change
            
        except Exception as e:
            await page.screenshot(path="error_screenshot.png")
            print(f"❌ Scrape Error: {e}")
            raise e
        finally:
            await browser.close()

async def main():
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
            send_msg(f"❌ Scrape failed: {str(e)[:100]}")
    else:
        print("😴 Weekend skip.")

if __name__ == "__main__":
    asyncio.run(main())
