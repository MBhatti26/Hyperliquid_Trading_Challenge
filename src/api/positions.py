from fastapi import APIRouter, Depends
from typing import Optional
from src.infrastructure.public_hl_datasource import PublicHLDataSource
from src.core.base import BaseDataSource

router = APIRouter()

# Dependency provider
def get_datasource() -> BaseDataSource:
  return PublicHLDataSource()

@router.get("/v1/positions")
async def get_positions(
  user: str,
  coin: Optional[str] = None,
  fromMs: Optional[int] = None,
  toMs: Optional[int] = None,
  builderOnly: bool = False,
  ds: BaseDataSource = Depends(get_datasource) # might be different due to no need for wallet address
):
  # Step 1: Get base data from datasource
  raw_fills = ds.get_user_fills(user, from_ms=fromMs, to_ms=toMs)

  # Step 2: Calculations
  # if builderOnly, then return tainted

  # Step 3: shape the data to return
  # right now this returns the raw data. It needs to be shaped
  # The following needs to be returned:
  # minimum: { timeMs, netSize, avgEntryPx } & tainted (if builderOnly)
  return raw_fills