import requests
from datetime import datetime
import os
from bs4 import BeautifulSoup

# --- CONFIG ---
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
URL = "https://www.metal.com/Lithium/201906260003"

def get_price():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(URL, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # This is the specific class for Spodumene Index on metal.com
        price_element = soup.find("span", class_="strong___3sC58") 
        
        if price_element:
            return price_element.text.strip()
        else:
            return "Price Unavailable (Site might be blocking the bot)"
            
    except Exception as e:
        return f"Connection Error: {e}"
        
def get_change():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(URL, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # This is the specific class for Spodumene Index on metal.com
        change_element = soup.find("div", class_="row___1PIPI") 
        
        if change_element:
            return change_element.text.strip()
        else:
            return "Change Unavailable (Site might be blocking the bot)"
            
    except Exception as e:
        return f"Connection Error: {e}"
        
    if change_element:
        full_text = change_element.text.strip()
        
        # Check if the "(" is actually in the text to avoid errors
        if "(" in full_text:
            # Split at "(" and take the part after it
            # Example: "Price (150.00)" becomes "150.00)"
            after_bracket = full_text.split("(")[1]
            
            # Remove the closing ")" and any extra spaces
            clean_change = after_bracket.replace(")", "").strip()
            return clean_change
        
        return full_text # Fallback if no bracket is found
    else:
        return "Change not found"

def send_msg(text):
    base_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    requests.post(base_url, data=payload)

# --- EXECUTION ---
# 1. Generate the date first so it is available for the message
now_str = datetime.now().strftime("%b %d, %Y - %H:%M")

# 2. Get the price
price = get_price()
change = get_change()

# 3. Create the final message
message = f"📅 Date: {now_str}\n📦 Spodumene Concentrate Index (CIF China)\n💰 Price: {price} USD/mt \n 📈 Change: {change}"

# 4. Send and Print
send_msg(message)
print(f"Script finished. Result: {price}{change}")




