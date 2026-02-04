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
            await page.goto(URL, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(3000)

            # --- STEP 1: ACCEPT COOKIES ---
            cookie_selectors = ['button:has-text("Accept")', 'button:has-text("Agree")', '.cookie-accept-btn', '#onetrust-accept-btn-handler']
            for sel in cookie_selectors:
                btn = page.locator(sel).first
                if await btn.is_visible():
                    print("🍪 Found cookie banner. Accepting...")
                    await btn.click()
                    await page.wait_for_timeout(1000)
                    break

            # --- STEP 2: HANDLE LOGIN ---
            login_selectors = ['text="Sign In"', 'button:has-text("Login")', '.login-btn', 'span:has-text("Sign In")']
            for selector in login_selectors:
                btn = page.locator(selector).first
                if await btn.is_visible():
                    print(f"🔑 Clicking login via: {selector}")
                    await btn.click()
                    break

            # Fill credentials (handling potential strict mode errors with .first)
            await page.wait_for_selector('input[type="email"], input[placeholder*="Email"]', timeout=15000)
            await page.locator('input[type="email"], input[placeholder*="Email"]').first.fill(SMM_EMAIL)
            await page.locator('input[type="password"], input[placeholder*="Password"]').first.fill(SMM_PASSWORD)
            await page.locator('button[type="submit"], .submit-btn').first.click()
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
