import requests
# from hyperliquid.info import Info
# from hyperliquid.utils import constants
from src.core.base import BaseDataSource

class PublicHLDataSource(BaseDataSource):
  def __init__(self, api_url="https://api.hyperliquid.xyz/info"):
    self.url = api_url

  async def get_trades(self, wallet_address, from_ms=None, to_ms=None):
    """Fetch chronological fills for a user."""
    # Using the SDK's user_fills method
    # Note: If from_ms is needed, you may need to use raw requests for userFillsByTime
    fills = self.info.user_fills(wallet_address)
    return fills

  async def get_deposits(self, wallet_address, from_ms=None, to_ms=None):
    """
    Fetch deposit history. 
    Uses 'userNonFundingLedgerUpdates' for comprehensive history.
    """
    # For now, return empty or implement a placeholder to satisfy the ABC
    return []
  
  def get_user_fills(self, user: str, from_ms: int = None, to_ms: int = None):
    # Use userFillsByTime if timestamps are provided
    if from_ms:
        payload = {
          "type": "userFillsByTime",
          "user": user,
          "startTime": from_ms
        }
        if to_ms:
          payload["endTime"] = to_ms
    else:
      payload = {"type": "userFills", "user": user}

    response = requests.post(self.url, json=payload)
    return response.json()