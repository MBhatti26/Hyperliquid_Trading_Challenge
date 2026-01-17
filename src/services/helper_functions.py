def determine_taint(trades, target_builder):
  # Group trades by coin name
  coins = {}
  for t in trades:
    c = t['coin']
    if c not in coins: 
      coins[c] = []
    coins[c].append(t)
  
  # Run separately for each coin's list
  for coin_name in coins:
    taint_by_coin(coins[coin_name], target_builder)
  
  return trades

def taint_by_coin(trades_by_coin, target_builder):
  position = 0
  is_tainted = False
  
  trades_by_coin.sort(key=lambda t: t['time'])
  for t in trades_by_coin:
    trade_amount = float(t['sz'])

    # add or subtract from position each trade
    if t['side'] == 'B': # buy
      position += trade_amount
    else: # sell if 'A' or 'S'
      position -= trade_amount

    # check for differing builders
    if position != 0 and t.get('builder') != target_builder:
      is_tainted = True

    t['tainted'] = is_tainted

    if abs(position) < 1e-9:
      is_tainted = False
  
  return trades_by_coin

def filter_by_coin(coin, fills):
  fills = [f for f in fills if f['coin'] == coin]
  return fills

def aggregate_trades(trades, builder_only):
  realized_pnl = 0.0
  fees_paid = 0.0
  trade_count = 0

  for fill in trades:
    if builder_only and fill.get('tainted'):
      continue

    realized_pnl += float(fill.get('closedPnl', 0))
    fees_paid += float(fill.get('fee', 0))
    trade_count += 1
  return {
    "realized_pnl": realized_pnl,
    "fees_paid": fees_paid,
    "trade_count": trade_count
  }

def calculate_return_pct(equity_at_start, realized_pnl, maxStartCapital):
  base_capital = max(equity_at_start, 1.0)

  if maxStartCapital:
    effective_capital = min(base_capital, maxStartCapital)
  else:
    effective_capital = base_capital

  return (realized_pnl / effective_capital) * 100

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
    
    if start_position != 0 and current_avg_entry == 0:
      # We're joining mid-lifecycle
      # Use current price as best estimate
      current_avg_entry = price
      total_cost = price * abs(start_position)
    
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

