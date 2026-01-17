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

def calculate_return_pct(equity_at_start, realized_pnl):
  base_capital = max(equity_at_start, 1.0)
  
  # effectiveCapital = min(equityAtFromMs, maxStartCapital)
  effective_capital = base_capital

  return realized_pnl / effective_capital * 100
