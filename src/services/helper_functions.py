def determine_taint(trades, target_builder, sort_by='time'):
  # Group trades by coin name
  coins = {}
  for t in trades:
    c = t['coin']
    if c not in coins: 
      coins[c] = []
    coins[c].append(t)
  
  # Run separately for each coin's list
  for coin_name in coins:
    taint_by_coin(coins[coin_name], target_builder, sort_by)
  
  return trades

def taint_by_coin(trades_by_coin, target_builder, sort_by='time'):
  position = 0
  is_tainted = False
  
  trades_by_coin.sort(key=lambda t: t[sort_by])
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

    # Check if a flip occurred (passing through zero)
    # If the sign of the position changes, it's a new lifecycle.
    if (position * (position - trade_amount if t['side'] == 'B' else position + trade_amount)) < 0:
      is_tainted = False # Reset for the new side of the flip
  
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

def check_if_user_tainted(trades, builderOnly, target_builder):
  """
  Check if user has any tainted position lifecycles
  
  A position lifecycle is tainted if it contains both:
  - Trades from target builder
  - Trades NOT from target builder
  
  Returns True if ANY lifecycle is tainted
  """
  if not builderOnly:
    return False
  
  # Group trades by coin
  trades_by_coin = {}
  for trade in trades:
    coin_name = trade.get("coin")
    if coin_name not in trades_by_coin:
      trades_by_coin[coin_name] = []
    trades_by_coin[coin_name].append(trade)
  
  # Check each coin's lifecycles for taint
  for coin_name, coin_trades in trades_by_coin.items():
    if is_coin_tainted(coin_trades, target_builder):
      return True
  
  return False

def is_coin_tainted(coin_trades, target_builder):
  """
  Check if any position lifecycle for this coin is tainted
  """
  lifecycle_has_builder = False
  lifecycle_has_non_builder = False
  
  for trade in coin_trades:
    side = trade.get("side")
    start_position = float(trade.get("startPosition", 0))
    size = float(trade.get("sz", 0))
    
    # Calculate end position
    if side == "B":  # BUY
      end_position = start_position + size
    else:  # SELL
      end_position = start_position - size
    
    # Check if builder trade
    trade_builder = trade.get("builder") or trade.get("builderAddress")
    is_builder_trade = False
    
    if "builderFee" in trade:
      has_builder_fee = float(trade.get("builderFee", 0)) > 0
      is_builder_trade = has_builder_fee and (trade_builder == target_builder if trade_builder else False)
    else:
      is_builder_trade = (trade_builder == target_builder) if trade_builder else False
    
    # Track builder/non-builder
    if is_builder_trade:
      lifecycle_has_builder = True
    else:
      lifecycle_has_non_builder = True
    
    # Check for taint
    if lifecycle_has_builder and lifecycle_has_non_builder:
      return True  # This lifecycle is tainted
    
    # Check if position closed (lifecycle ends)
    if end_position == 0:
      # Reset for next lifecycle
      lifecycle_has_builder = False
      lifecycle_has_non_builder = False
  
  return False

def calculate_pnl(trades):
  """
  Calculate total realized PnL (sum of closedPnl)
  """
  pnl = 0.0
  for trade in trades:
    closed_pnl = float(trade.get("closedPnl", 0))
    pnl += closed_pnl
  return pnl

def calculate_volume(trades):
  """
  Calculate total notional traded (price * size for all trades)
  """
  volume = 0.0
  for trade in trades:
    price = float(trade.get("px", 0))
    size = float(trade.get("sz", 0))
    volume += price * size
  return volume

def calculate_user_metrics(
  user_address,
  coin,
  fromMs,
  toMs,
  builderOnly,
  metric,
  maxStartCapital,
  target_builder,
  ds
):
  """
  Calculate trading metrics for a single user
  
  Returns:
  {
    "user": "0x...",
    "metricValue": "123.45",
    "tradeCount": 50,
    "tainted": false
  }
  """
  # Get all trades for user
  raw_fills = ds.get_user_fills(user_address, from_ms=fromMs, to_ms=toMs)
  
  if not raw_fills:
    return None
  
  # Filter by coin if specified
  if coin:
    raw_fills = [f for f in raw_fills if f.get("coin") == coin]
  
  if not raw_fills:
    return None
  
  # Sort trades
  raw_fills = sorted(raw_fills, key=lambda x: (x.get("time", 0), x.get("tid", 0)))
  
  # Calculate tainted status (check for mixed builder/non-builder activity)
  is_tainted = check_if_user_tainted(raw_fills, builderOnly, target_builder)
  
  # Filter trades based on builderOnly mode
  if builderOnly:
    filtered_fills = []
    for fill in raw_fills:
      trade_builder = fill.get("builder") or fill.get("builderAddress")
      is_builder_trade = False
        
      if "builderFee" in fill:
        has_builder_fee = float(fill.get("builderFee", 0)) > 0
        is_builder_trade = has_builder_fee and (trade_builder == target_builder if trade_builder else False)
      else:
        is_builder_trade = (trade_builder == target_builder) if trade_builder else False
      
      if is_builder_trade:
        filtered_fills.append(fill)
    
    raw_fills = filtered_fills

  if not raw_fills:
    return None

  # Calculate the requested metric
  if metric == "volume":
    metric_value = calculate_volume(raw_fills)
  elif metric == "pnl":
    metric_value = calculate_pnl(raw_fills)
  elif metric == "returnPct":
    pnl = calculate_pnl(raw_fills)
    metric_value = (pnl / maxStartCapital) * 100 if maxStartCapital else 0

  return {
    "user": user_address,
    "metricValue": str(metric_value),
    "tradeCount": len(raw_fills),
    "tainted": is_tainted
  }
