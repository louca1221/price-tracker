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
        # Launch browser
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            # 1. Load the page
            await page.goto(URL, wait_until="networkidle")

            # 2. Handle Login (Using .first and visible filters to avoid Strict Mode Violation)
            login_btn = page.locator('button:has-text("Sign In"), .login-btn, a:has-text("Sign In")').filter(visible=True).first
            
            if await login_btn.is_visible():
                print("🔑 Login required. Entering credentials...")
                await login_btn.click()
                
                # Fill email and password (using .first to be safe)
                await page.locator('input[type="email"], input[placeholder*="Email"]').first.fill(SMM_EMAIL)
                await page.locator('input[type="password"], input[placeholder*="Password"]').first.fill(SMM_PASSWORD)
                
                # Click the final Submit/Sign In button
                await page.locator('button[type="submit"], .submit-btn').first.click()
                await page.wait_for_load_state("networkidle")

            # 3. Scrape the data
            # Adjusting selectors for the 2026 site layout
            await page.wait_for_selector(".strong___3sC58", timeout=15000)
            
            price_raw = await page.inner_text(".strong___3sC58")
            change_raw = await page.inner_text(".row___1PIPI")

            # Cleaning the split logic: text after "("
            change = change_raw.split("(")[1].replace(")", "").strip() if "(" in change_raw else change_raw
            
            await browser.close()
            return price_raw.strip(), change
            
        except Exception as e:
            await browser.close()
            return f"Error: {str(e)[:60]}", "Error"

def send_msg(text):
    if not TOKEN or not CHAT_ID:
        print("❌ Missing TOKEN or CHAT_ID secrets.")
        return

    # Cleaning and splitting multiple Chat IDs
    chat_ids = [cid.strip() for cid in CHAT_ID.split(",") if cid.strip()]
    
    for chat_id in chat_ids:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        try:
            res = requests.post(url, data={"chat_id": chat_id, "text": text}, timeout=10)
            print(f"📡 Sent to {chat_id}: {res.status_code}")
        except Exception as e:
            print(f"❌ Failed to send to {chat_id}: {e}")

async def main():
    # Weekday check (0=Mon, 4=Fri)
    if datetime.now().weekday() < 5:
        now_str = datetime.now().strftime("%b %d, %Y - %H:%M")
        price, change = await get_data()

        report = (
            f"📅 Date: {now_str}\n"
            f"📦 Spodumene Concentrate Index (CIF China)\n"
            f"💰 Price: {price} USD/mt\n"
            f"📈 Change: {change}"
        )

        send_msg(report)
        print(f"✅ Execution finished: {price} | {change}")
    else:
        print("😴 Weekend detected. Skipping report.")

if __name__ == "__main__":
    asyncio.run(main())
