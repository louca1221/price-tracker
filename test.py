import requests
from datetime import datetime
import os
from bs4 import BeautifulSoup

# --- CONFIG ---
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
URL = "https://www.metal.com/Lithium/201906260003"

def get_data():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(URL, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Get the Price
        price_el = soup.find("span", class_="strong___3sC58")
        price = price_el.text.strip() if price_el else "N/A"
        
        # 2. Get the Change and split it
        change_el = soup.find("div", class_="row___1PIPI")
        if change_el:
            change_text = change_el.text.strip()
            if "(" in change_text:
                change = change_text.split("(")[1].replace(")", "").strip()
            else:
                change = change_text
        else:
            change = "N/A"
            
        return price, change
            
    except Exception as e:
        return f"Error: {e}", "Error"

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
if datetime.now().weekday() < 6:
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
