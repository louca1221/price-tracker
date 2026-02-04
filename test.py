import os
import asyncio
import requests
from datetime import datetime
from playwright.async_api import async_playwright

# --- CONFIG ---
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
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
            
            # 1. Try to clear any popups by pressing Escape
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(2000)

            # 2. Find and FORCE click the login button
            # 'force=True' ignores the 'intercepts pointer events' error
            login_btn = page.locator('text="Sign In", .signInButton, button:has-text("Sign In")').first
            
            if await login_btn.is_visible():
                print("🔑 Clicking login (Forced)...")
                await login_btn.click(force=True) 
            
            # 3. Fill Credentials
            # We wait for the input to be attached to the page
            await page.wait_for_selector('input[type="email"], input[placeholder*="Email"]', state="attached", timeout=15000)
            await page.locator('input[type="email"]').first.fill(SMM_EMAIL)
            await page.locator('input[type="password"]').first.fill(SMM_PASSWORD)
            
            # Force click the final submit button too
            await page.locator('button[type="submit"], .submit-btn').first.click(force=True)
            
            # 4. Wait for redirection and price
            await page.wait_for_load_state("networkidle")
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
        print("❌ Missing TOKEN or CHAT_ID secrets.")
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
