# ============================================================================
# POSITION TRACKING LOGIC - COMPLETE EXPLANATION
# ============================================================================
#
# OVERVIEW:
# This endpoint reconstructs a user's position history from their trade data.
# A "position" is how many coins you currently own (positive = long, negative = short).
# We track how this position changes over time with each trade.
#
# KEY DATA STRUCTURE FROM HYPERLIQUID:
# Each trade/fill contains:
# - startPosition: The position size BEFORE this trade executed
# - side: "A" (Ask/SELL) or "B" (Bid/BUY)  ← CRITICAL: A=SELL, B=BUY
# - sz: Size of the trade
# - px: Price of the trade
# - time: When it happened
# - dir: Human-readable direction ("Open Long", "Close Short", etc.)
# - closedPnl: Realized PnL if closing position (0 if opening)
#
# IMPORTANT: SIDE DEFINITIONS IN HYPERLIQUID
# - side "A" = Ask = SELL
# - side "B" = Bid = BUY
# This is standard trading terminology (Ask = seller, Bid = buyer)
#
# VERIFIED WITH DATA:
# - "side": "A", "dir": "Open Short" → Opening short = SELLING
# - "side": "B", "dir": "Close Short" → Closing short = BUYING back
#
# ============================================================================
# POSITION SIZE CALCULATION
# ============================================================================
# 
# Formula:
# - If side == "B" (BUY):  end_position = start_position + size
# - If side == "A" (SELL): end_position = start_position - size
#
# EXAMPLES:
#
# Example 1: Opening a Long Position
# Start: 0 (no position)
# BUY (side B) 100 coins
# End: 0 + 100 = +100 (long 100 coins)
#
# Example 2: Closing a Short Position
# Start: -500 (short 500 coins)
# BUY (side B) 200 coins (buying back some of what you shorted)
# End: -500 + 200 = -300 (still short, but only 300 coins now)
#
# Example 3: Adding to a Short Position
# Start: -200 (short 200 coins)
# SELL (side A) 50 more coins
# End: -200 - 50 = -250 (short 250 coins)
#
# Example 4: Position Flip (Short to Long)
# Start: -100 (short 100 coins)
# BUY (side B) 200 coins
# End: -100 + 200 = +100 (flipped to long 100 coins!)
#
# ============================================================================
# AVERAGE ENTRY PRICE CALCULATION
# ============================================================================
#
# The average entry price is the weighted average of all prices you paid
# when opening/adding to your position.
#
# CASE 1: Opening a New Position (startPosition == 0)
# - Simply use the price of this trade
# - total_cost = price * size
# - avg_entry_px = price
#
# Example:
# BUY 100 coins at $50
# avg_entry = $50
# total_cost = $5,000
#
# CASE 2: Adding to Position (position getting larger)
# - Calculate weighted average of all entry prices
# - total_cost += (price * size)
# - avg_entry_px = total_cost / total_position_size
#
# Example:
# Previous: 100 coins at avg $50 (total_cost = $5,000)
# Now: BUY 50 coins at $52
# 
# new_cost_added = 50 * $52 = $2,600
# total_cost = $5,000 + $2,600 = $7,600
# new_position_size = 100 + 50 = 150
# new_avg_entry = $7,600 / 150 = $50.67
#
# CASE 3: Closing Position (position getting smaller)
# - Average entry price STAYS THE SAME
# - You're selling at current market price, but your entry price doesn't change
# - Just reduce total_cost proportionally
#
# Example:
# Had: 150 coins at avg $50.67
# Sell: 50 coins at $55 (market price)
# Remaining: 100 coins still at avg $50.67 (entry price unchanged)
#
# CASE 4: Position Flip (sign changes)
# - Old position closes completely
# - New position opens in opposite direction
# - Reset avg_entry_px to current price
# - Reset total_cost
# - This is like ending one trade and starting a brand new one
#
# Example:
# Had: +100 long at avg $50
# Sell: 200 coins at $55
# Result: -100 short at avg $55 (new position, new entry price)
#
# ============================================================================
# POSITION LIFECYCLE & TAINT DETECTION
# ============================================================================
#
# POSITION LIFECYCLE:
# A lifecycle is the complete journey from opening to closing a position.
# Start: netSize moves from 0 to non-zero (position opens)
# End: netSize returns to 0 (position fully closes)
#
# Example Lifecycle:
# Time 1: netSize = 0 (no position)
# Time 2: BUY 100 → netSize = +100 (lifecycle starts)
# Time 3: BUY 50 → netSize = +150 (same lifecycle continues)
# Time 4: SELL 75 → netSize = +75 (same lifecycle continues)
# Time 5: SELL 75 → netSize = 0 (lifecycle ends)
# Time 6: BUY 200 → netSize = +200 (NEW lifecycle starts)
#
# TAINT DETECTION:
# A position is "tainted" if during its lifecycle, the user mixed:
# - Trades from the target builder (builder bot)
# - Trades NOT from the target builder (manual trading or different bot)
#
# Why this matters:
# If we're judging a trading bot's performance, we want positions that
# were ONLY traded using that bot. If the user manually interfered,
# we can't fairly judge the bot's results.
#
# Taint tracking per lifecycle:
# - lifecycle_has_builder = False (at start)
# - lifecycle_has_non_builder = False (at start)
# - For each trade in the lifecycle:
#   - If trade is from target builder: lifecycle_has_builder = True
#   - If trade is NOT from target builder: lifecycle_has_non_builder = True
# - If BOTH become True: tainted = True
#
# Example 1: Clean (Not Tainted)
# Lifecycle 1:
#   BUY 100 via Builder Bot → lifecycle_has_builder = True
#   BUY 50 via Builder Bot → still only builder trades
#   SELL 150 via Builder Bot → close position
# Result: tainted = False (all trades used the builder)
#
# Example 2: Tainted
# Lifecycle 2:
#   BUY 100 via Builder Bot → lifecycle_has_builder = True
#   BUY 50 manually → lifecycle_has_non_builder = True
#   SELL 150 via Builder Bot → close position
# Result: tainted = True (mixed builder + manual trades)
#
# ============================================================================
# POSITION FLIP HANDLING
# ============================================================================
#
# A position flip occurs when the position changes from positive to negative
# or negative to positive. This happens when you close MORE than your current
# position, causing you to open a position in the opposite direction.
#
# Detection: start_position * end_position < 0
# (One is positive, one is negative, so their product is negative)
#
# Example 1: Long to Short Flip
# Start: +100 (long 100 coins)
# Action: SELL 200 coins
# Result: +100 - 200 = -100 (now short 100 coins)
#
# This is actually TWO actions:
# 1. Close the long position of 100 (first 100 coins sold)
# 2. Open a short position of 100 (additional 100 coins sold)
#
# When flip occurs:
# - OLD lifecycle ends (the long position is closed)
# - NEW lifecycle starts (the short position opens)
# - Reset average entry price to current trade price
# - Reset taint tracking (new lifecycle = fresh start)
# - Increment lifecycle_id
#
# Example 2: Short to Long Flip  
# Start: -500 (short 500 coins)
# Action: BUY 700 coins
# Result: -500 + 700 = +200 (now long 200 coins)
#
# This closed the short AND opened a long.
# Same handling: end old lifecycle, start new one.
#
# ============================================================================
# OUTPUT FORMAT
# ============================================================================
#
# Each position snapshot returned contains:
# {
#   "timeMs": 1768596355756,        // Unix timestamp in milliseconds
#   "coin": "kPEPE",                 // Which coin
#   "netSize": "-11218204.0",        // Position size (negative = short, positive = long)
#   "avgEntryPx": "0.005907",        // Average entry price
#   "tainted": false                 // Only present if builderOnly=True
# }
#
# Reading the netSize:
# - Positive number (e.g., "100"): Long 100 coins (you own them, profit if price rises)
# - Negative number (e.g., "-100"): Short 100 coins (you borrowed and sold, profit if price falls)
# - Zero ("0"): No position (flat, not in the market)
#
# The response is a time-ordered list of these snapshots,
# showing how the position evolved with each trade.
#
# ============================================================================

import os
from fastapi import APIRouter, Depends
from typing import Optional
from dotenv import load_dotenv
from src.infrastructure.public_hl_datasource import PublicHLDataSource
from src.core.base import BaseDataSource

load_dotenv()
TARGET_BUILDER = os.getenv("TARGET_BUILDER")

router = APIRouter()

def get_datasource() -> BaseDataSource:
    return PublicHLDataSource()

@router.get("/v1/positions/history")
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


def process_coin_positions(coin_trades, builderOnly, target_builder):
    """
    Process trades for a single coin and build position history
    """
    positions = []
    
    # Track lifecycle for taint detection
    lifecycle_id = 0
    lifecycle_has_builder = False
    lifecycle_has_non_builder = False
    
    # Track cost basis for avgEntryPx calculation
    total_cost = 0.0
    current_avg_entry = 0.0
    
    for fill in coin_trades:
        # Extract trade data
        side = fill.get("side")  # "A" = SELL, "B" = BUY
        size = float(fill.get("sz", 0))
        price = float(fill.get("px", 0))
        time_ms = fill.get("time")
        start_position = float(fill.get("startPosition", 0))
        
        # Calculate position AFTER this trade
        # CRITICAL: side "B" = BUY (add), side "A" = SELL (subtract)
        if side == "B":  # BUY
            end_position = start_position + size
        else:  # side == "A", SELL
            end_position = start_position - size
        
        # Check if this is a builder trade
        trade_builder = fill.get("builder") or fill.get("builderAddress")
        is_builder_trade = False
        
        if "builderFee" in fill:
            has_builder_fee = float(fill.get("builderFee", 0)) > 0
            is_builder_trade = has_builder_fee and (trade_builder == target_builder if trade_builder else False)
        else:
            is_builder_trade = (trade_builder == target_builder) if trade_builder else False
        
        # If builderOnly mode and not a builder trade, skip
        if builderOnly and not is_builder_trade:
            continue
        
        # Track builder/non-builder for taint
        if is_builder_trade:
            lifecycle_has_builder = True
        else:
            lifecycle_has_non_builder = True
        
        # Calculate average entry price
        if start_position == 0 and end_position != 0:
            # Opening a new position
            current_avg_entry = price
            total_cost = price * abs(end_position)
            lifecycle_id += 1
            
        elif start_position * end_position < 0:
            # Position flip (long → short or short → long)
            current_avg_entry = price
            total_cost = price * abs(end_position)
            lifecycle_id += 1
            # Reset taint tracking for new lifecycle
            lifecycle_has_builder = is_builder_trade
            lifecycle_has_non_builder = not is_builder_trade
            
        elif abs(end_position) > abs(start_position):
            # Adding to position (increasing size)
            cost_added = price * size
            total_cost += cost_added
            current_avg_entry = total_cost / abs(end_position)
            
        else:
            # Reducing position (partial or full close)
            # Average entry price stays the same
            total_cost = current_avg_entry * abs(end_position) if end_position != 0 else 0
        
        # Determine if tainted
        tainted = False
        if builderOnly:
            tainted = lifecycle_has_builder and lifecycle_has_non_builder
        
        # Create position snapshot
        snapshot = {
            "timeMs": time_ms,
            "coin": fill.get("coin"),
            "netSize": str(end_position),
            "avgEntryPx": str(current_avg_entry) if end_position != 0 else "0"
        }
        
        # Add tainted field if builderOnly
        if builderOnly:
            snapshot["tainted"] = tainted
        
        positions.append(snapshot)
        
        # Check if position closed (returned to 0)
        if end_position == 0:
            # Reset for next lifecycle
            lifecycle_has_builder = False
            lifecycle_has_non_builder = False
            total_cost = 0
            current_avg_entry = 0
    
    return positions