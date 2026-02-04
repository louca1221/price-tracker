import os
import asyncio
import requests
from datetime import datetime
from playwright.async_api import async_playwright

# --- CONFIG (Updated to match your Secret names) ---
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
            await page.goto(URL, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(5000)

            # --- STEP 1: CLEAR OVERLAYS ---
            # Your logs show 'ant-modal-wrap' is the culprit. We'll remove it via JS.
            await page.evaluate('() => { document.querySelectorAll(".ant-modal-mask, .ant-modal-wrap").forEach(el => el.remove()); }')
            await page.keyboard.press("Escape")

            # --- STEP 2: LOGIN ---
            login_btn = page.locator('text="Sign In", .signInButton').first
            if await login_btn.is_visible():
                print("🔑 Clicking login...")
                # dispatch_event avoids the "intercepts pointer events" error entirely
                await login_btn.dispatch_event("click")

            await page.wait_for_selector('input[type="email"]', timeout=15000)
            await page.fill('input[type="email"]', SMM_EMAIL)
            await page.fill('input[type="password"]', SMM_PASSWORD)
            await page.locator('button[type="submit"]').first.dispatch_event("click")
            
            await page.wait_for_load_state("networkidle")

            # --- STEP 3: SCRAPE ---
            await page.wait_for_selector(".strong___3sC58", timeout=20000)
            price = await page.inner_text(".strong___3sC58")
            change_raw = await page.inner_text(".row___1PIPI")

            change = change_raw.split("(")[1].replace(")", "").strip() if "(" in change_raw else change_raw
            
            await browser.close()
            return price.strip(), change
            
        except Exception as e:
            await page.screenshot(path="error_screenshot.png")
            print(f"❌ Error Detail: {e}")
            await browser.close()
            return "Error (Check Artifacts)", "Error"

def send_msg(text):
    if not TOKEN or not CHAT_ID:
        print("❌ FAILED: Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID environment variables.")
        return
        
    chat_ids = [cid.strip() for cid in CHAT_ID.split(",") if cid.strip()]
    for chat_id in chat_ids:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": chat_id, "text": text}, timeout=10)

async def main():
    if datetime.now().weekday() < 5:
        now_str = datetime.now().strftime("%b %d, %Y - %H:%M")
        price, change = await get_data()
        
        report = f"📅 Date: {now_str}\n📦 Spodumene Index\n💰 Price: {price} USD/mt\n📈 Change: {change}"
        send_msg(report)
        print(f"✅ Final Result: {price} | {change}")
    else:
        print("😴 Weekend skip.")

if __name__ == "__main__":
    asyncio.run(main())
