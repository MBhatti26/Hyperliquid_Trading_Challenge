import requests
import json

def get_trades(wallet_address):
    url = "https://api.hyperliquid.xyz/info"
    payload = {
        "type": "userFills",
        "user": wallet_address
    }

    response = requests.post(url, json=payload)
    response.raise_for_status()  # throws a helpful error if request fails
    return response.json()

wallet = "0x010461C14e146ac35Fe42271BDC1134EE31C703a"
trades = get_trades(wallet)

# Save to JSON file
filename = f"trades_{wallet}.json"
with open(filename, "w", encoding="utf-8") as f:
    json.dump(trades, f, indent=2)

print(f"Saved {len(trades)} trades to {filename}")
