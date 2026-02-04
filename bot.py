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
    """Sends the report to Telegram and prints diagnostic info."""
    if not TOKEN or not CHAT_ID:
        print("❌ FAILED: Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID")
        return
    chat_ids = [cid.strip() for cid in CHAT_ID.split(",") if cid.strip()]
    for chat_id in chat_ids:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        try:
            response = requests.post(url, data={"chat_id": chat_id, "text": text}, timeout=15)
            result = response.json()
            if result.get("ok"):
                print(f"✅ Telegram: Message sent to {chat_id}")
            else:
                print(f"❌ Telegram Error for {chat_id}: {result.get('description')}")
        except Exception as e:
            print(f"❌ Network Error: {e}")

async def get_data():
    """Scrapes Lithium price after bypassing Ant-Design overlays."""
    async with async_playwright() as p:
        # headless=True for GitHub Actions; False for local watching
        browser = await p.chromium.launch(headless=True, slow_mo=1000)
        
        # --- 1. SESSION LOADING ---
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
        
        page = await context.new_page()
        
        try:
            print(f"🌐 Navigating to {URL}...")
            await page.goto(URL, wait_until="networkidle", timeout=60000)
            
            # --- 2. CHECK LOGIN STATUS ---
            price_selector = "div[class*='__avg']"
            is_logged_in = await page.locator(price_selector).first.count() > 0

            if not is_logged_in:
                print("🔒 Not logged in. Starting login flow...")
                
                # Check if login modal is already open
                email_selector = 'input[type="email"], input[placeholder*="Email"], #account'
                if await page.locator(email_selector).count() == 0:
                    print("🔑 Triggering Modal...")
                    await page.evaluate('''() => {
                        const elements = document.querySelectorAll('div, span, a, button');
                        const loginBtn = Array.from(elements).find(el => el.textContent.trim() === 'Sign In');
                        if (loginBtn) loginBtn.click();
                    }''')

                await page.wait_for_selector(email_selector, state="visible", timeout=15000)

                # Email
                await page.click(email_selector)
                await page.keyboard.press("Control+A")
                await page.keyboard.press("Backspace")
                await page.keyboard.type(SMM_EMAIL, delay=100)

                # Password
                await page.click('input[type="password"]')
                await page.keyboard.press("Control+A")
                await page.keyboard.press("Backspace")
                await page.keyboard.type(SMM_PASSWORD, delay=100)

                await page.wait_for_timeout(1000)
                print("⏳ Submitting login...")
                await page.locator('button:has-text("Sign in"), .ant-btn-primary').first.click()
                
                # --- 3. SESSION SAVING ---
                await page.wait_for_selector(".signInButton", state="hidden", timeout=20000)
                await context.storage_state(path=STORAGE_PATH)
                print(f"💾 Session saved to {STORAGE_PATH}")
                
                # Refresh to confirm logged-in data
                await page.goto(URL, wait_until="networkidle")
            else:
                print("✅ Already logged in via session file!")

            # --- 4. DATA EXTRACTION (Precise) ---
            print("📊 Extracting price...")
            price_locator = page.locator("div[class*='__avg']").first
            await price_locator.wait_for(state="visible", timeout=30000)
            price = await price_locator.inner_text()
            
            # Target ONLY the change div to avoid grabbing the date again
            print("📊 Extracting change...")
            change_locator = page.locator("div[class*='Change']").first
            change_raw = await change_locator.inner_text()
            
            # Clean up the change text (removes extra lines/spaces)
            change = change_raw.replace('\n', ' ').strip()

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
            
            # --- EMOJI TOGGLE LOGIC ---
            # If the change starts with '-', use 📉, otherwise use 📈
            emoji = "📉" if val_change.startswith("-") else "📈"
            
            now_str = datetime.now().strftime("%b %d, %Y - %H:%M")
            report = (
                f"📅 Date: {now_str}\n"
                f"📦 Spodumene Concentrate Index\n"
                f"💰 Price: {val_price} USD/mt\n"
                f"{emoji} Change: {val_change}"
            )
            
            send_msg(report)
            print(f"✅ FINAL: {val_price} | {val_change}")
        except Exception as e:
            send_msg(f"❌ Scrape failed: {str(e)[:100]}")
    else:
        print("😴 Weekend skip.")

if __name__ == "__main__":
    asyncio.run(main())