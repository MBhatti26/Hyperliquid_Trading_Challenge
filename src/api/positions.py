import os
from fastapi import APIRouter, Depends
from typing import Optional
from dotenv import load_dotenv
from src.infrastructure.public_hl_datasource import PublicHLDataSource
from src.core.base import BaseDataSource
from src.services.helper_functions import process_coin_positions

load_dotenv()
TARGET_BUILDER = os.getenv("TARGET_BUILDER")

router = APIRouter()

def get_datasource() -> BaseDataSource:
    return PublicHLDataSource()

@router.get("/v1/positions")
async def get_positions(
  user: str,
  coin: Optional[str] = None,
  fromMs: Optional[int] = None,
  toMs: Optional[int] = None,
  builderOnly: bool = False,
  ds: BaseDataSource = Depends(get_datasource)
):
  # Step 1: Get all trades
  raw_fills = ds.get_user_fills(user, from_ms=fromMs, to_ms=toMs)
  
  if not raw_fills:
    return []
  
  # Step 2: Filter by coin if specified
  if coin:
    raw_fills = [f for f in raw_fills if f.get("coin") == coin]
  
  # Step 3: Sort by time, then by trade ID for consistency
  raw_fills = sorted(raw_fills, key=lambda x: (x.get("time", 0), x.get("tid", 0)))
  
  # Step 4: Group trades by coin
  trades_by_coin = {}
  for fill in raw_fills:
    coin_name = fill.get("coin")
    if coin_name not in trades_by_coin:
      trades_by_coin[coin_name] = []
    trades_by_coin[coin_name].append(fill)
  
  # Step 5: Build position history
  position_history = []
  
  for coin_name, coin_trades in trades_by_coin.items():
    position_states = process_coin_positions(coin_trades, builderOnly, TARGET_BUILDER)
    position_history.extend(position_states)
  
  # Step 6: Sort all positions by time
  position_history = sorted(position_history, key=lambda x: x.get("timeMs", 0))
  
  return position_history
