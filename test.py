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
        # Launch headless browser
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = await context.new_page()

        try:
            # 1. Navigate to the page
            await page.goto(URL, wait_until="networkidle")

            # 2. Check if login is required (Looks for 'Sign In' text or login button)
            # If the site redirected you to login, fill the fields.
            if await page.get_by_text("Sign In").is_visible():
                print("Logging in...")
                # Adjust these selectors if the ID/Name changes on the site
                await page.fill('input[type="email"], input[placeholder*="Email"]', SMM_EMAIL)
                await page.fill('input[type="password"], input[placeholder*="Password"]', SMM_PASSWORD)
                await page.click('button:has-text("Sign In"), button[type="submit"]')
                await page.wait_for_load_state("networkidle")

            # 3. Wait for the price elements to appear
            await page.wait_for_selector(".strong___3sC58", timeout=15000)
            
            price_raw = await page.inner_text(".strong___3sC58")
            change_raw = await page.inner_text(".row___1PIPI")

            # Cleaning the split logic as requested
            change = change_raw.split("(")[1].replace(")", "").strip() if "(" in change_raw else change_raw
            
            await browser.close()
            return price_raw.strip(), change
            
        except Exception as e:
            await browser.close()
            return f"Error: {str(e)[:50]}...", "Error"

def send_msg(text):
    if not CHAT_ID: return
    chat_ids = [cid.strip() for cid in CHAT_ID.split(",") if cid.strip()]
    for chat_id in chat_ids:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": chat_id, "text": text})

async def main():
    # Only run on weekdays
    if datetime.now().weekday() < 5:
        now_str = datetime.now().strftime("%b %d, %Y - %H:%M")
        price, change = await get_data()

        message = (
            f"📅 Date: {now_str}\n"
            f"📦 Spodumene Concentrate Index (CIF China)\n"
            f"💰 Price: {price} USD/mt\n"
            f"📈 Change: {change}"
        )

        send_msg(message)
        print(f"Report Sent: {price} | {change}")
    else:
        print("Weekend: Skipping.")

if __name__ == "__main__":
    asyncio.run(main())
