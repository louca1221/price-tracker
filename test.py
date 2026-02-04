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
            await page.goto(URL, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(5000)

            # --- Clear Popups ---
            await page.keyboard.press("Escape")
            await page.evaluate('() => document.querySelectorAll(".ant-modal-mask, .ant-modal-wrap").forEach(e => e.remove())')

            # --- Login ---
            print("🔑 Attempting Login...")
            login_btn = page.locator('text="Sign In", .signInButton').first
            await login_btn.dispatch_event("click")
            
            await page.wait_for_selector('input[type="email"]', timeout=10000)
            await page.fill('input[type="email"]', SMM_EMAIL)
            await page.fill('input[type="password"]', SMM_PASSWORD)
            await page.locator('button[type="submit"]').first.click()
            
            # --- Scrape ---
            await page.wait_for_selector(".strong___3sC58", timeout=20000)
            price = await page.inner_text(".strong___3sC58")
            change_raw = await page.inner_text(".row___1PIPI")
            
            change = change_raw.split("(")[1].replace(")", "").strip() if "(" in change_raw else change_raw
            return price.strip(), change

        except Exception as e:
            await page.screenshot(path="error_screenshot.png")
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
