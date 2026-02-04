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

async def get_data():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()
        
        try:
            print(f"🌐 Navigating to {URL}...")
            await page.goto(URL, wait_until="networkidle", timeout=60000)
            
            # Use JS to find and click the 'Sign In' button to bypass ALL UI blocks
            print("🔑 Attempting deep-click on Sign In...")
            await page.evaluate('''() => {
                const buttons = Array.from(document.querySelectorAll('div, span, button, a'));
                const loginBtn = buttons.find(el => el.textContent.trim() === 'Sign In');
                if (loginBtn) loginBtn.click();
            }''')
            
            # Wait for form fields
            email_selector = 'input[type="email"], input[placeholder*="Email"]'
            await page.wait_for_selector(email_selector, state="attached", timeout=15000)
            
            await page.locator(email_selector).first.fill(SMM_EMAIL)
            await page.locator('input[type="password"]').first.fill(SMM_PASSWORD)
            
            # Final submit via JS click
            await page.evaluate('''() => {
                const submit = document.querySelector('button[type="submit"], .submit-btn');
                if (submit) submit.click();
            }''')
            
            print("⏳ Waiting for price page...")
            await page.wait_for_load_state("networkidle")
            await page.wait_for_selector(".strong___3sC58", timeout=20000)
            
            price = await page.inner_text(".strong___3sC58")
            change_raw = await page.inner_text(".row___1PIPI")
            
            change = change_raw.split("(")[1].replace(")", "").strip() if "(" in change_raw else change_raw
            return price.strip(), change
            
        except Exception as e:
            await page.screenshot(path="error_screenshot.png")
            print(f"❌ Automation Error: {e}")
            raise e
        finally:
            await browser.close()

def send_msg(text):
    if not TOKEN or not CHAT_ID:
        print("❌ Missing Secrets")
        return
    for chat_id in CHAT_ID.split(","):
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                      data={"chat_id": chat_id.strip(), "text": text})

async def main():
    if datetime.now().weekday() < 5:
        try:
            price, change = await get_data()
            now_str = datetime.now().strftime("%b %d, %Y - %H:%M")
            send_msg(f"📅 {now_str}\n💰 Price: {price} USD/mt\n📈 Change: {change}")
        except Exception as e:
            send_msg(f"❌ Scrape failed: {str(e)[:50]}")

if __name__ == "__main__":
    asyncio.run(main())
