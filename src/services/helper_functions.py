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
  
  trades_by_coin.sort(key=lambda t: t['timeMs'])
  for t in trades_by_coin:
    trade_amount = float(t['sz'])

    # add or subtract from position each trade
    if t['side'] == 'B': # buy
      position += trade_amount
    elif t['side'] == 'A': # sell
      position -= trade_amount

    # check for differing builders
    if position != 0 and t.get('builder') != target_builder:
      is_tainted = True

    t['tainted'] = is_tainted

    if abs(position) < 1e-9:
      is_tainted = False
  
  return trades_by_coin