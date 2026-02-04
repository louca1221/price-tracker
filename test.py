import os
import asyncio
import requests
from datetime import datetime
from playwright.async_api import async_playwright

# --- CONFIG (Check these names in your Secrets!) ---
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
            print(f"🌐 Opening {URL}...")
            await page.goto(URL, wait_until="networkidle", timeout=60000)
            
            # Press escape to clear initial popups
            await page.keyboard.press("Escape")

            # Try to find and click Sign In
            print("🔍 Looking for Sign In button...")
            login_btn = page.locator('text="Sign In", .signInButton').first
            # We use dispatch_event to click through blocking modals
            await login_btn.dispatch_event("click")
            
            # Wait for the email field to appear
            print("📝 Waiting for login form...")
            email_field = page.locator('input[type="email"], input[placeholder*="Email"]').first
            await email_field.wait_for(state="attached", timeout=15000)
            
            await email_field.fill(SMM_EMAIL)
            await page.locator('input[type="password"]').first.fill(SMM_PASSWORD)
            await page.locator('button[type="submit"], .submit-btn').first.dispatch_event("click")
            
            print("⏳ Waiting for price page...")
            await page.wait_for_load_state("networkidle")
            await page.wait_for_selector(".strong___3sC58", timeout=20000)
            
            price = await page.inner_text(".strong___3sC58")
            change_raw = await page.inner_text(".row___1PIPI")
            change = change_raw.split("(")[1].replace(")", "").strip() if "(" in change_raw else change_raw
            
            return price.strip(), change
            
        except Exception as e:
            # THIS IS CRITICAL: Save the image so we can see why it failed
            print(f"❌ Error occurred: {e}")
            await page.screenshot(path="error_screenshot.png")
            raise e # Tell GitHub the job failed
        finally:
            await browser.close()

def send_msg(text):
    if not TOKEN or not CHAT_ID:
        print(f"❌ SECRET ERROR: TOKEN={bool(TOKEN)}, CHAT_ID={bool(CHAT_ID)}")
        return
    for cid in CHAT_ID.split(","):
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                      data={"chat_id": cid.strip(), "text": text})

async def main():
    if datetime.now().weekday() < 5:
        try:
            price, change = await get_data()
            now_str = datetime.now().strftime("%b %d, %Y - %H:%M")
            send_msg(f"📅 {now_str}\n💰 Price: {price} USD/mt\n📈 Change: {change}")
        except:
            print("Job failed. Check artifacts.")
            exit(1) # Force GitHub to show a red "Fail" status

if __name__ == "__main__":
    asyncio.run(main())
