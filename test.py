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
    # Print diagnostic info to GitHub logs
    if not TOKEN: print("❌ Missing TELEGRAM_TOKEN")
    if not CHAT_ID: print("❌ Missing TELEGRAM_CHAT_ID")
    if not TOKEN or not CHAT_ID: return

    chat_ids = [cid.strip() for cid in CHAT_ID.split(",") if cid.strip()]
    for chat_id in chat_ids:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": chat_id, "text": text}, timeout=10)

async def get_data():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()
        
        try:
            print(f"🌐 Opening {URL}...")
            await page.goto(URL, wait_until="networkidle", timeout=60000)
            
            # Clear popups by pressing Escape
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(2000)

            # Target the specific 'Sign In' link/button in the top header
            # Using get_by_role is more resilient
            login_btn = page.get_by_role("button", name="Sign In").first or \
                        page.get_by_text("Sign In").first
            
            print("🔑 Clicking Sign In (Direct Event)...")
            # dispatch_event bypasses actionability checks
            await login_btn.dispatch_event("click")
            
            # Wait for the email field to appear in the DOM
            print("📝 Waiting for login form...")
            email_selector = 'input[type="email"], input[placeholder*="Email"]'
            await page.wait_for_selector(email_selector, state="attached", timeout=15000)
            
            await page.locator(email_selector).first.fill(SMM_EMAIL)
            await page.locator('input[type="password"]').first.fill(SMM_PASSWORD)
            
            # Use dispatch_event for the final submit as well
            await page.locator('button[type="submit"], .submit-btn').first.dispatch_event("click")
            
            print("⏳ Waiting for price data...")
            await page.wait_for_load_state("networkidle")
            # Wait for the price element to be visible
            await page.wait_for_selector(".strong___3sC58", timeout=20000)
            
            price = await page.inner_text(".strong___3sC58")
            change_raw = await page.inner_text(".row___1PIPI")
            
            # Process text after "("
            change = change_raw.split("(")[1].replace(")", "").strip() if "(" in change_raw else change_raw
            
            return price.strip(), change
            
        except Exception as e:
            # Always save screenshot on any error
            await page.screenshot(path="error_screenshot.png")
            print(f"❌ Automation Error: {e}")
            raise e
        finally:
            await browser.close()
async def main():
    if datetime.now().weekday() < 5:
        try:
            price, change = await get_data()
            now_str = datetime.now().strftime("%b %d, %Y - %H:%M")
            report = f"📅 {now_str}\n💰 Price: {price} USD/mt\n📈 Change: {change}"
            send_msg(report)
        except Exception as e:
            error_msg = f"❌ Error during scrape: {str(e)[:100]}"
            send_msg(error_msg)
            print(error_msg)

if __name__ == "__main__":
    asyncio.run(main())
