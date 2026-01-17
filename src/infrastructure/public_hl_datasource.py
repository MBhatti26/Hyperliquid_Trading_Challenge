import requests
# from hyperliquid.info import Info
# from hyperliquid.utils import constants
from src.core.base import BaseDataSource

class PublicHLDataSource(BaseDataSource):
  def __init__(self, api_url="https://api.hyperliquid.xyz/info"):
    self.url = api_url

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
  
  async def get_equity_at_timestamp(self, user: str, timestamp_ms: int):
    """
    Calculates historical equity by taking current state and reversing
    all ledger updates back to the target timestamp
    """
    # 1. Get Current Equity (Margin Summary)
    state_payload = {"type": "clearinghouseState", "user": user}
    state_resp = requests.post(self.url, json=state_payload).json()
    
    # Current equity is the 'marginSummary' account value
    current_equity = float(state_resp.get('marginSummary', {}).get('accountValue', 0))

    # 2. Get Ledger Updates from timestamp_ms to now
    # userNonFundingLedgerUpdates includes deposits, withdrawals, and transfers
    ledger_payload = {
      "type": "userNonFundingLedgerUpdates",
      "user": user,
      "startTime": timestamp_ms
    }
    ledger_resp = requests.post(self.url, json=ledger_payload).json()

    # 3. Reverse the changes
    # If someone deposited AFTER the timestamp, subtract it from current equity
    # to find out what they had at the start.
    delta = 0.0
    for update in ledger_resp:
      # The 'delta' field in the ledger update represents the change in account value
      delta += float(update.get('delta', 0))

    # 4. Final Calculation
    # Equity_Start = Equity_Now - Change_Since_Start
    equity_at_start = current_equity - delta
    
    return max(equity_at_start, 0.0)