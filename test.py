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
            
            # --- STEP 1: REMOVE BLOCKING MODALS ---
            await page.evaluate('() => { document.querySelectorAll(".ant-modal-mask, .ant-modal-wrap, .ant-modal").forEach(el => el.remove()); }')
            await page.keyboard.press("Escape")

            # --- STEP 2: OPEN LOGIN FORM ---
            login_btn = page.locator('text="Sign In", .signInButton').first
            if await login_btn.is_visible():
                print("🔑 Clicking Sign In...")
                await login_btn.dispatch_event("click")
                # Wait for the login form to actually exist in the DOM
                await page.wait_for_timeout(3000)

            # --- STEP 3: FILL LOGIN (Aggressive Search) ---
            print("📝 Looking for email field...")
            # We use a broader selector for the email/password fields
            email_field = page.locator('input[type="email"], input[placeholder*="Email"], input[name*="mail"]').first
            password_field = page.locator('input[type="password"], input[placeholder*="Pass"]').first
            
            # Wait for it to be attached (not necessarily visible yet)
            await email_field.wait_for(state="attached", timeout=20000)
            
            await email_field.fill(SMM_EMAIL)
            await password_field.fill(SMM_PASSWORD)
            
            submit_btn = page.locator('button[type="submit"], button:has-text("Sign In"), .submit-btn').first
            await submit_btn.dispatch_event("click")
            
            print("⏳ Waiting for login to complete...")
            await page.wait_for_load_state("networkidle")

            # --- STEP 4: SCRAPE PRICE ---
            await page.wait_for_selector(".strong___3sC58", timeout=30000)
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
        # Added print for debugging secrets
        print(f"❌ DEBUG: TOKEN exists: {bool(TOKEN)}, CHAT_ID exists: {bool(CHAT_ID)}")
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
        print("😴 Weekend.")

if __name__ == "__main__":
    asyncio.run(main())
