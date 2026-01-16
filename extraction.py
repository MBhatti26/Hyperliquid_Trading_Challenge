import requests
import json

def get_trades(wallet_address):
    url = "https://api.hyperliquid.xyz/info"
    
    payload = {
        "type": "userFills",
        "user": wallet_address
    }
    
    response = requests.post(url, json=payload)
    return response.json()

# Test it
wallet = "0x010461C14e146ac35Fe42271BDC1134EE31C703a"
trades = get_trades(wallet)

print(f"Found {len(trades)} trades")
print(json.dumps(trades[0], indent=2))