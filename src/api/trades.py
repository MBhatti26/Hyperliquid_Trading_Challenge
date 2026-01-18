import os
from fastapi import APIRouter, Depends
from typing import Optional
from dotenv import load_dotenv
from src.infrastructure.public_hl_datasource import PublicHLDataSource
from src.core.base import BaseDataSource
from src.services.helper_functions import determine_taint

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
  builderOnly: bool = False,
  ds: BaseDataSource = Depends(get_datasource)
):
  # 1. Get ALL raw fills (don't filter yet!)
  raw_fills = ds.get_user_fills(user, from_ms=fromMs, to_ms=toMs)
  
  # 2. Map raw fills to the required schema
  processed_fills = []
  for f in raw_fills:
    # Check builder attribution 
    # matching address AND fee > 0
    trade_builder = f.get("builder")
    is_target_builder = (trade_builder == TARGET_BUILDER and float(f.get("builderFee", 0)) > 0)
    
    processed_fills.append({
      "timeMs": f.get("time"),
      "coin": f.get("coin"),
      "side": f.get("side"),
      "px": f.get("px"),
      "sz": f.get("sz"),
      "fee": f.get("fee"),
      "closedPnl": f.get("closedPnl"),
      "builder": trade_builder,
      "is_target_builder": is_target_builder # Helper for step 4
    })

  # 3. Determine Taint on the FULL list
  # This function needs the whole history to see if a non-builder trade "tainted" the position
  determine_taint(processed_fills, TARGET_BUILDER, sort_by='timeMs')

  # 4. Final Filter
  final_results = []
  for f in processed_fills:
    # Filter by coin if requested
    if coin and f["coin"] != coin:
      continue
        
    if builderOnly:
      # Rule: Only target builder AND NOT tainted 
      if f["is_target_builder"] and not f.get("tainted"):
          final_results.append(f)
    else:
      # All-trades mode: return everything [cite: 10]
      final_results.append(f)

  return final_results