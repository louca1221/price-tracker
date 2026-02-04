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
            
            # --- STEP 1: CLEAR POPUPS/MODALS ---
            # Your log showed 'ant-modal-wrap' was blocking the click.
            # We try to press Escape and click any 'Close' icons found.
            await page.keyboard.press("Escape")
            close_selectors = ['.ant-modal-close', '.close-btn', 'button:has-text("Close")']
            for sel in close_selectors:
                if await page.locator(sel).first.is_visible():
                    await page.locator(sel).first.click(force=True)
            
            # --- STEP 2: HANDLE LOGIN ---
            # We use 'force=True' to click even if an invisible layer is 'intercepting'
            login_btn = page.locator('text="Sign In", .signInButton').first
            print("🔑 Attempting to click Sign In...")
            await login_btn.click(force=True, timeout=10000)

            # Wait for the email input specifically
            await page.wait_for_selector('input[type="email"], input[placeholder*="Email"]', timeout=15000)
            await page.locator('input[type="email"]').first.fill(SMM_EMAIL)
            await page.locator('input[type="password"]').first.fill(SMM_PASSWORD)
            
            # Force click the final submit button
            await page.locator('button[type="submit"], .submit-btn').first.click(force=True)
            await page.wait_for_load_state("networkidle")

            # --- STEP 3: SCRAPE ---
            # After login, wait for the actual price to appear
            await page.wait_for_selector(".strong___3sC58", timeout=20000)
            price = await page.inner_text(".strong___3sC58")
            change_raw = await page.inner_text(".row___1PIPI")

            change = change_raw.split("(")[1].replace(")", "").strip() if "(" in change_raw else change_raw
            
            await browser.close()
            return price.strip(), change
            
        except Exception as e:
            # Save screenshot so you can see the blocking element in GitHub Artifacts
            await page.screenshot(path="error_screenshot.png")
            print(f"❌ Error Detail: {e}")
            await browser.close()
            return "Error (Check Artifacts)", "Error"

def send_msg(text):
    # Ensure TOKEN and CHAT_ID actually exist before sending
    if not TOKEN or not CHAT_ID:
        print("❌ FAILED: Missing TOKEN or CHAT_ID environment variables.")
        return
        
    chat_ids = [cid.strip() for cid in CHAT_ID.split(",") if cid.strip()]
    for chat_id in chat_ids:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": chat_id, "text": text}, timeout=10)

async def main():
    if datetime.now().weekday() < 5:
        now_str = datetime.now().strftime("%b %d, %Y - %H:%M")
        price, change = await get_data()
        
        report = (
            f"📅 Date: {now_str}\n"
            f"📦 Spodumene Concentrate Index\n"
            f"💰 Price: {price} USD/mt\n"
            f"📈 Change: {change}"
        )
        
        send_msg(report)
        print(f"✅ Final Result: {price} | {change}")
    else:
        print("😴 Weekend skip.")

if __name__ == "__main__":
    asyncio.run(main())
