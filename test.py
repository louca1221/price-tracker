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
            
            # Step 1: Use raw JS to find the text "Sign In" and click it
            # This logic works in every browser because it doesn't use Playwright selectors
            print("🔑 Brute-forcing Login Modal...")
            await page.evaluate('''() => {
                // Find every element that might be a button or link
                const elements = document.querySelectorAll('div, span, a, button');
                for (const el of elements) {
                    if (el.textContent.trim() === 'Sign In') {
                        el.click(); // Trigger the click directly
                        return;
                    }
                }
            }''')

            # Step 2: Wait for the login form fields to exist
            print("📝 Waiting for login form...")
            email_input = page.locator('input[type="email"], input[placeholder*="Email"]').first
            await email_input.wait_for(state="attached", timeout=15000)

            # Step 3: Fill using JavaScript (Bypasses "intercepted pointer" errors)
            await page.evaluate(f'''() => {{
                const email = document.querySelector('input[type="email"], input[placeholder*="Email"]');
                const pass = document.querySelector('input[type="password"]');
                if (email) {{
                    email.value = "{SMM_EMAIL}";
                    email.dispatchEvent(new Event('input', {{ bubbles: true }}));
                }}
                if (pass) {{
                    pass.value = "{SMM_PASSWORD}";
                    pass.dispatchEvent(new Event('input', {{ bubbles: true }}));
                }}
            }}''')

           # Step 4: Final scraping using the new class structure
            print("📊 Scraping price data from new elements...")
            
            # We wait for the 'avg' price container to appear
            price_selector = "[class*='__avg']"
            await page.wait_for_selector(price_selector, timeout=20000)
            
            # Extract the raw values
            price = await page.inner_text(price_selector)
            
            # The change is usually in a span inside the 'downChange' or 'upChange' div
            change_raw = await page.inner_text("[class*='Change']")
            
            # Cleaning the change text: 
            # If change_raw is "-2(-0.10%)", this pulls out "-2 (-0.10%)"
            if "(" in change_raw:
                val = change_raw.split("(")[0].strip()
                percent = change_raw.split("(")[1].replace(")", "").strip()
                change = f"{val} ({percent})"
            else:
                change = change_raw.strip()

            return price.strip(), change
            
        except Exception as e:
            await page.screenshot(path="error_screenshot.png")
            print(f"❌ Automation Error: {e}")
            raise e
        finally:
            await browser.close()

def send_msg(text):
    if not TOKEN or not CHAT_ID:
        print("❌ Missing Secrets")
        return
    for chat_id in CHAT_ID.split(","):
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                      data={"chat_id": chat_id.strip(), "text": text})

async def main():
    if datetime.now().weekday() < 5:
        try:
            price, change = await get_data()
            now_str = datetime.now().strftime("%b %d, %Y - %H:%M")
            send_msg(f"📅 {now_str}\n💰 Price: {price} USD/mt\n📈 Change: {change}")
        except Exception as e:
            send_msg(f"❌ Scrape failed: {str(e)[:50]}")

if __name__ == "__main__":
    asyncio.run(main())
