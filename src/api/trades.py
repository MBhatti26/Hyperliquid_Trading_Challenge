import os
from fastapi import APIRouter, Depends
from typing import Optional
from dotenv import load_dotenv
from src.infrastructure.public_hl_datasource import PublicHLDataSource
from src.core.base import BaseDataSource
from src.services.helper_functions import (
  determine_taint,
)

load_dotenv()
TARGET_BUILDER = os.getenv("TARGET_BUILDER")

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
  builderOnly: bool = True,
  ds: BaseDataSource = Depends(get_datasource)
):
  # calls get_user_fills from ./src/infrastructure/public_hl_datasource.py
  raw_fills = ds.get_user_fills(user, from_ms=fromMs, to_ms=toMs)

  if not raw_fills or "error" in str(raw_fills):
    return []

  normalized_trades = []
  
  for fill in raw_fills:
    if coin and fill.get("coin") != coin:
      continue
        
    # Builder-only logic
    # checks if this was traded using a builder
    # assumes builder if fee is greater than 0    
    if "builderFee" in fill:
      is_builder = float(fill.get("builderFee", 0)) > 0
    else:
      # Assume it's true demo if builderOnly is turned on
      is_builder = True if builderOnly else False

    if not is_builder:
      continue

    # This takes the original output and reframes it to only push out below
    normalized_trades.append({
      "timeMs": fill.get("time"),
      "coin": fill.get("coin"),
      "side": fill.get("side"),
      "px": fill.get("px"),
      "sz": fill.get("sz"),
      "fee": fill.get("fee"),
      "closedPnl": fill.get("closedPnl"),
      "builder": TARGET_BUILDER if is_builder else None
    })

  # add column "tainted" if net_size !=0 and builder != TARGET_BUILDER
  determine_taint(
    normalized_trades,
    TARGET_BUILDER
  )
  return normalized_trades