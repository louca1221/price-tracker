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
                # This reveals if the chat_id is wrong or the bot isn't started
                print(f"❌ Telegram Error for {chat_id}: {result.get('description')}")
        except Exception as e:
            print(f"❌ Network Error: {e}")

async def get_data():
    """Scrapes Lithium price after bypassing Ant-Design overlays."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Use a realistic User-Agent to avoid headless detection
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            print(f"🌐 Navigating to {URL}...")
            await page.goto(URL, wait_until="networkidle", timeout=60000)
            
            # 1. Trigger Login Modal via JS
            print("🔑 Opening Login Modal...")
            # 1. Check if we are already on a login page before clicking
            print("🧐 Checking if login is already open...")
            email_selector = 'input[type="email"], input[placeholder*="Email"], #account'
            
            # Check for the field without waiting/timing out
            is_login_already_open = await page.locator(email_selector).count() > 0

            if not is_login_already_open:
                print("🔑 No login found. Triggering Modal...")
                await page.evaluate('''() => {
                    const elements = document.querySelectorAll('div, span, a, button');
                    const loginBtn = Array.from(elements).find(el => el.textContent.trim() === 'Sign In');
                    if (loginBtn) loginBtn.click();
                }''')
            else:
                print("✅ Login already open. Skipping click.")

            # 2. Proceed to fill credentials as normal
            print("📝 Filling fields...")
            await page.wait_for_selector(email_selector, state="visible", timeout=10000)
            # ... rest of your fill logic
            # 2. Fill Credentials (Slow-Type Human Simulation)
            print("📝 Entering credentials character-by-character...")
            email_selector = 'input[type="email"], input[placeholder*="Email"], #account'
            pass_selector = 'input[type="password"]'
            
            # Wait for fields to be interactable
            await page.wait_for_selector(email_selector, state="visible", timeout=15000)

            # --- EMAIL ---
            # Click first to ensure focus
            await page.click(email_selector)
            # Clear existing text just in case
            await page.keyboard.press("Control+A")
            await page.keyboard.press("Backspace")
            # Type slowly (100ms per key) to trigger site validation
            await page.keyboard.type(SMM_EMAIL, delay=100)

            # --- PASSWORD ---
            await page.click(pass_selector)
            await page.keyboard.press("Control+A")
            await page.keyboard.press("Backspace")
            await page.keyboard.type(SMM_PASSWORD, delay=100)

            # 3. Small pause to let the 'Sign In' button turn red/active
            await page.wait_for_timeout(1000)

            print("⏳ Submitting login...")
            # We target the specific button text from your screenshot
            submit_btn = page.locator('button:has-text("Sign in"), .ant-btn-primary').first
            await submit_btn.click()
            
            # Wait for the login modal to disappear OR the price to appear
            try:
                # We wait for the 'Sign in' button to go away, which means login worked
                await page.wait_for_selector(".signInButton", state="hidden", timeout=20000)
                print("✅ Session confirmed.")
            except:
                print("⚠️ Login state not detected. Attempting emergency refresh...")
                await page.goto(URL, wait_until="networkidle")

            # 4. Final render wait
            # Instead of a fixed timeout, we wait for the price container specifically
            print("📊 Looking for price data...")
            price_locator = page.locator("div[class*='__avg']").first
            await price_locator.wait_for(state="visible", timeout=30000)

            # 5. Extract Price and Change from dynamic divs
            print("📊 Extracting data...")
            price_locator = page.locator("div[class*='__avg']").first
            await price_locator.wait_for(state="visible", timeout=20000)
            price = await price_locator.inner_text()
            
            wrap_locator = page.locator("div[class*='PriceWrap']").first
            full_text = await wrap_locator.inner_text()
            
            # Extract change by removing the price from the full string
            clean_full = full_text.replace('\n', ' ').strip()
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
            print(f"✅ FINAL: {val_price} | {val_change}")
        except Exception as e:
            # Send error details to Telegram to aid debugging
            send_msg(f"❌ Scrape failed: {str(e)[:100]}")
    else:
        print("😴 Weekend skip.")

if __name__ == "__main__":
    asyncio.run(main())