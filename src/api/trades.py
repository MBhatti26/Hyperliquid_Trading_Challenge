from fastapi import APIRouter, Depends
from typing import Optional
from src.infrastructure.public_hl_datasource import PublicHLDataSource
from src.core.base import BaseDataSource

router = APIRouter()

# Dependency provider
def get_datasource() -> BaseDataSource:
  return PublicHLDataSource()

@router.get("/v1/trades")
async def get_trades(
  user: str,
  coin: Optional[str] = None,
  fromMs: Optional[int] = None,
  toMs: Optional[int] = None,
  builderOnly: bool = False,
  ds: BaseDataSource = Depends(get_datasource)
):
  raw_fills = ds.get_user_fills(user, from_ms=fromMs, to_ms=toMs)
  normalized_trades = []
  
  for fill in raw_fills:
    if coin and fill.get("coin") != coin:
      continue
        
    # Builder-only logic
    # proxy check: if builderFee exists or specific builder addr matches
    is_builder = float(fill.get("builderFee", 0)) > 0 
    
    if builderOnly and not is_builder:
      continue

    normalized_trades.append({
      "timeMs": fill.get("time"),
      "coin": fill.get("coin"),
      "side": fill.get("side"),
      "px": fill.get("px"),
      "sz": fill.get("sz"),
      "fee": fill.get("fee"),
      "closedPnl": fill.get("closedPnl"),
      "builder": "TARGET_BUILDER" if is_builder else None
    })
  return normalized_trades