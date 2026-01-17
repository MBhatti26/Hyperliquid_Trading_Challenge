import requests
from src.core.base import BaseDataSource

class PublicHLDataSource(BaseDataSource):
  def __init__(self, api_url="https://api.hyperliquid.xyz/info"):
    self.url = api_url

  def get_trades(self, wallet_address, from_ms=None, to_ms=None):
    # Use userFillsByTime if from_ms is provided, else userFills
    payload = {
      "type": "userFillsByTime" if from_ms else "userFills",
      "user": wallet_address
    }
    if from_ms:
      payload["startTime"] = from_ms
    if to_ms:
      payload["endTime"] = to_ms

    response = requests.post(self.url, json=payload)
    return response.json()

  def get_deposits(self, wallet_address, from_ms=None, to_ms=None):
    # Implementation for userNonFundingLedgerUpdates
    pass