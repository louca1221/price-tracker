async def get_data():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            print(f"🌐 Navigating to {URL}...")
            await page.goto(URL, wait_until="networkidle", timeout=60000)
            
            # 1. Trigger Login Modal via JS
            print("🔑 Opening Login Modal...")
            await page.evaluate('''() => {
                const elements = document.querySelectorAll('div, span, a, button');
                const loginBtn = Array.from(elements).find(el => el.textContent.trim() === 'Sign In');
                if (loginBtn) loginBtn.click();
            }''')

            # 2. Fill Credentials (FIXED: Arguments passed as a single list)
            print("📝 Entering credentials via direct focus...")
            email_selector = 'input[type="email"], input[placeholder*="Email"], #account'
            await page.wait_for_selector(email_selector, state="attached", timeout=15000)

            # [SMM_EMAIL, SMM_PASSWORD] is the single 'arg' required by evaluate
            await page.evaluate('''([e, p]) => {
                const emailInput = document.querySelector('input[type="email"], input[placeholder*="Email"], #account');
                const passInput = document.querySelector('input[type="password"]');
                if (emailInput) {
                    emailInput.focus();
                    emailInput.value = e;
                    emailInput.dispatchEvent(new Event('input', { bubbles: true }));
                }
                if (passInput) {
                    passInput.focus();
                    passInput.value = p;
                    passInput.dispatchEvent(new Event('input', { bubbles: true }));
                }
            }''', [SMM_EMAIL, SMM_PASSWORD])

            # 3. Submit with Force Click to bypass the row/label interception
            print("⏳ Submitting login...")
            submit_btn = page.locator('button:has-text("Sign in"), .ant-btn-primary').first
            await submit_btn.click(force=True)
            
            # 4. Wait for modal to clear and re-navigate
            try:
                await page.wait_for_selector(".ant-modal", state="hidden", timeout=15000)
                print("✅ Login successful.")
            except:
                print("⚠️ Modal still active, attempting re-navigation...")

            await page.goto(URL, wait_until="networkidle")
            await page.wait_for_timeout(5000) 

            # 5. Extract Data using partial class matches
            print("📊 Extracting data...")
            price_locator = page.locator("div[class*='__avg']").first
            await price_locator.wait_for(state="visible", timeout=20000)
            price = await price_locator.inner_text()
            
            wrap_locator = page.locator("div[class*='PriceWrap']").first
            full_text = await wrap_locator.inner_text()
            
            clean_full = full_text.replace('\n', ' ').strip()
            change = clean_full.replace(price.strip(), "").strip()

            return price.strip(), change
            
        except Exception as e:
            await page.screenshot(path="error_screenshot.png")
            print(f"❌ Scrape Error: {e}")
            raise e
        finally:
            await browser.close()
