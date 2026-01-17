import os
from dotenv import load_dotenv
from fastapi import APIRouter, Depends
from typing import Optional
from src.infrastructure.public_hl_datasource import PublicHLDataSource
from src.core.base import BaseDataSource
from src.services.helper_functions import (
  determine_taint,
  filter_by_coin,
  aggregate_trades,
  calculate_return_pct,
)

load_dotenv()
TARGET_BUILDER = os.getenv("TARGET_BUILDER")

router = APIRouter()

# Dependency provider
def get_datasource() -> BaseDataSource:
  return PublicHLDataSource()

@router.get("/v1/pnl")
async def get_pnl(
  user: str,
  coin: Optional[str] = None,
  fromMs: Optional[int] = None,
  toMs: Optional[int] = None,
  builderOnly: bool = False,
  ds: BaseDataSource = Depends(get_datasource) # might be different due to no need for wallet address
):
  # Step 1: Get base data from datasource
  raw_fills = ds.get_user_fills(user, from_ms=fromMs, to_ms=toMs)

  # filter by coin
  if coin:
    raw_fills = filter_by_coin(coin, raw_fills)

  # Step 2: Taint for builder-only
  processed_trades = determine_taint(raw_fills, TARGET_BUILDER)
  is_tainted = any(pt.get('tainted', False) for pt in processed_trades)

  # Step 3: Aggregate Data
  aggregates = aggregate_trades(processed_trades, builderOnly)
  realized_pnl, fees_paid, trade_count = aggregates.get("realized_pnl"), aggregates.get("fees_paid"), aggregates.get("trade_count")

  # Step 4: Relative PnL
  equity_at_start = await ds.get_equity_at_timestamp(user, fromMs) if fromMs else 1.0
  relative_pnl = calculate_return_pct(equity_at_start, realized_pnl) 

  # Step 5: shape the data to return
  return {
    "realizedPnl": realized_pnl,
    "returnPct": relative_pnl,
    "feesPaid": fees_paid,
    "tradeCount": trade_count,
    "tainted": is_tainted if builderOnly else None,
  }