from fastapi import APIRouter, Depends
from typing import Optional, Literal
from src.infrastructure.public_hl_datasource import PublicHLDataSource
from src.core.base import BaseDataSource

router = APIRouter()

# Dependency provider
def get_datasource() -> BaseDataSource:
  return PublicHLDataSource()

@router.get("/v1/leaderboard")
async def get_leaderboard(
  coin: Optional[str] = None,
  fromMs: Optional[int] = None,
  toMs: Optional[int] = None,
  metric: Literal["volume", "pnl", "returnPct"] = "pnl",
  builderOnly: bool = False,
  maxStartCapital: Optional[float] = 1000.0,
  ds: BaseDataSource = Depends(get_datasource) # might be different due to no need for wallet address
):
  # Step 1: Get base data from datasource
  # This is going to look different since we do not need a user to run this
  # raw_fills = ds.get_user_fills(user, from_ms=fromMs, to_ms=toMs)

  # Step 2: shape the data to return
  # The following needs to be returned in a ranked list:
  # rank, user, metricValue, tradeCount, tainted
  return []