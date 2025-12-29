import requests
from bs4 import BeautifulSoup

# --- CONFIG ---
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
URL = "https://www.metal.com/Lithium/201906260003"

def get_price():
    # These headers make you look like a real browser
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(URL, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Change 'span' and 'price-class' to match your specific site
        price_element = soup.find("span", class_="strong___3sC58 priceUp___3Mgsl") 
        
        if price_element:
            return price_element.text.strip()
        else:
            return "Could not find the price tag on the page."
            
    except Exception as e:
        return f"Error connecting to site: {e}"

def send_msg(text):
    base_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    requests.post(base_url, data=payload)

# Execution
price = get_price()
send_msg(f"Spodumene Concentrate Index (CIF China) Price, USD/mt Avg.:: {price}")

print(f"Script finished. Result: {price}")

