import os
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, Literal
from dotenv import load_dotenv
from src.infrastructure.public_hl_datasource import PublicHLDataSource
from src.core.base import BaseDataSource
from src.services.helper_functions import (
  calculate_user_metrics
)

load_dotenv()
TARGET_BUILDER = os.getenv("TARGET_BUILDER")

router = APIRouter()

# Dependency provider
def get_datasource() -> BaseDataSource:
  return PublicHLDataSource()

@router.get("/v1/leaderboard")
async def get_leaderboard(
  users: str,  # Required: comma-separated wallet addresses
  coin: Optional[str] = None,
  fromMs: Optional[int] = None,
  toMs: Optional[int] = None,
  metric: Literal["volume", "pnl", "returnPct"] = "pnl",
  builderOnly: bool = False,
  maxStartCapital: Optional[float] = None,
  ds: BaseDataSource = Depends(get_datasource)
):
  # Validate metric
  valid_metrics = ["volume", "pnl", "returnPct"]
  if metric not in valid_metrics:
    raise HTTPException(
      status_code=400,
      detail=f"Invalid metric. Must be one of: {', '.join(valid_metrics)}"
    )
  
  # Validate returnPct has maxStartCapital
  if metric == "returnPct" and not maxStartCapital:
    raise HTTPException(
      status_code=400,
      detail="maxStartCapital is required when metric is returnPct"
    )
  
  # Parse user addresses
  user_addresses = [u.strip() for u in users.split(",") if u.strip()]
  if not user_addresses:
    raise HTTPException(status_code=400, detail="No valid user addresses provided")
  
  # Calculate metrics for each user
  leaderboard_data = []
  
  for user_address in user_addresses:
    user_metrics = calculate_user_metrics(
      user_address,
      coin,
      fromMs,
      toMs,
      builderOnly,
      metric,
      maxStartCapital,
      TARGET_BUILDER,
      ds
    )
    
    if user_metrics:  # Only include if user has trades
      leaderboard_data.append(user_metrics)
  
  # Sort by metric value (descending - higher is better)
  leaderboard_data.sort(key=lambda x: float(x["metricValue"]), reverse=True)
  
  # Add ranks
  for rank, entry in enumerate(leaderboard_data, start=1):
    entry["rank"] = rank
  
  return leaderboard_data

