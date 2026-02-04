import os
import asyncio
from playwright.async_api import async_playwright
from datetime import datetime

# CONFIG
SMM_EMAIL = os.getenv("SMM_EMAIL")
SMM_PASSWORD = os.getenv("SMM_PASSWORD")
URL = "https://www.metal.com/Lithium/201906260003"

async def get_smm_data():
    async with async_playwright() as p:
        # 1. Launch Browser
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # 2. Go to Login (adjust URL if SMM has a specific /login page)
        await page.goto(URL)
        
        # 3. Handle Login
        # Note: You may need to click a 'Login' button first to see these fields
        await page.fill('input[type="email"]', SMM_EMAIL) 
        await page.fill('input[type="password"]', SMM_PASSWORD)
        await page.click('button[type="submit"]')
        
        # 4. Wait for price to load
        await page.wait_for_selector(".strong___3sC58")
        
        price = await page.inner_text(".strong___3sC58")
        change_text = await page.inner_text(".row___1PIPI")
        
        await browser.close()
        return price.strip(), change_text.strip()

def send_msg(text):
    # 1. Get the raw string from GitHub Secrets
    raw_ids = os.getenv("CHAT_ID")
    
    if not raw_ids:
        print("❌ Error: CHAT_ID secret is empty or not found.")
        return

    # 2. Split by comma and CLEAN every ID (removes spaces/tabs/newlines)
    # This turns "123, 456" into ["123", "456"]
    chat_ids = [cid.strip() for cid in raw_ids.split(",") if cid.strip()]
    
    print(f"DEBUG: Attempting to send to {len(chat_ids)} IDs: {chat_ids}")

    for chat_id in chat_ids:
        base_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text
        }
        try:
            response = requests.post(base_url, data=payload, timeout=10)
            if response.status_code == 200:
                print(f"✅ Successfully sent to: {chat_id}")
            else:
                print(f"⚠️ Telegram rejected {chat_id}: {response.text}")
        except Exception as e:
            print(f"❌ Network error for {chat_id}: {e}")


# --- EXECUTION ---
# Only run if it's a weekday (0=Mon, 4=Fri)
if datetime.now().weekday() < 5:
    now_str = datetime.now().strftime("%b %d, %Y - %H:%M")
    price, change = get_data()

    message = (
        f"📅 Date: {now_str}\n"
        f"📦 Spodumene Concentrate Index (CIF China)\n"
        f"💰 Price: {price} USD/mt\n"
        f"📈 Change: {change}"
    )

    send_msg(message)
    print(f"Report Sent: {price} | {change}")
else:
    print("Weekend skip: No report sent.")
