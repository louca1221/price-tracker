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
STORAGE_PATH = "state.json"

def send_msg(text):
    if not TOKEN or not CHAT_ID:
        print("❌ FAILED: Missing Secrets")
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
        
        # --- STORAGE STATE LOGIC START ---
        if os.path.exists(STORAGE_PATH):
            print("🚀 Loading saved session...")
            context = await browser.new_context(
                storage_state=STORAGE_PATH,
                viewport={'width': 1280, 'height': 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        else:
            print("🔑 No session found, starting fresh...")
            context = await browser.new_context(
                viewport={'width': 1280, 'height': 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        # --- STORAGE STATE LOGIC END ---

        page = await context.new_page()
        
        try:
            print(f"🌐 Navigating to {URL}...")
            await page.goto(URL, wait_until="networkidle", timeout=60000)
            
            # Check if we are actually logged in by looking for the price
            # If the price isn't there, we need to perform the login steps
            price_locator = page.locator("div[class*='__avg']").first
            is_logged_in = await price_locator.count() > 0

            if not is_logged_in:
                print("🔒 Not logged in. Starting login flow...")
                
                # Check if login modal is already open
                email_selector = 'input[type="email"], input[placeholder*="Email"], #account'
                if await page.locator(email_selector).count() == 0:
                    print("🔑 Triggering Login Modal...")
                    await page.evaluate('''() => {
                        const elements = document.querySelectorAll('div, span, a, button');
                        const loginBtn = Array.from(elements).find(el => el.textContent.trim() === 'Sign In');
                        if (loginBtn) loginBtn.click();
                    }''')

                await page.wait_for_selector(email_selector, state="visible", timeout=15000)
                
                # Type Email
                await page.click(email_selector)
                await page.keyboard.press("Control+A")
                await page.keyboard.press("Backspace")
                await page.keyboard.type(SMM_EMAIL, delay=100)

                # Type Password
                await page.click('input[type="password"]')
                await page.keyboard.press("Control+A")
                await page.keyboard.press("Backspace")
                await page.keyboard.type(SMM_PASSWORD, delay=100)

                await page.wait_for_timeout(1000)
                print("⏳ Submitting login...")
                await page.locator('button:has-text("Sign in"), .ant-btn-primary').first.click()
                
                # Wait for login to complete and SAVE STATE
                await page.wait_for_load_state("networkidle")
                await context.storage_state(path=STORAGE_PATH)
                print(f"💾 Session saved to {STORAGE_PATH}")
                
                # Refresh to see the price
                await page.goto(URL, wait_until="networkidle")
            else:
                print("✅ Already logged in via session file!")

            # Extraction
            print("📊 Extracting data...")
            await price_locator.wait_for(state="visible", timeout=20000)
            price = await price_locator.inner_text()
            
            wrap_locator = page.locator("div[class*='PriceWrap']").first
            full_text = await wrap_locator.inner_text()
            
            clean_full = full_text.replace('\n', ' ').strip()
            change = clean_full.replace(price.strip(), "").strip()

            return price.strip(), change
            
        except Exception as e:
            await page.screenshot(path="error_screenshot.png")
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
            print(f"✅ FINAL: {val_price} | {val_change}")
        except Exception as e:
            # Send error details to Telegram to aid debugging
            send_msg(f"❌ Scrape failed: {str(e)[:100]}")
    else:
        print("😴 Weekend skip.")

if __name__ == "__main__":
    asyncio.run(main())