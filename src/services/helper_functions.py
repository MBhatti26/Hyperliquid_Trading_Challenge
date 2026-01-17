def determine_taint(trades, target_builder):
  position = 0
  is_tainted = False
  
  trades.sort(key=lambda t: t['timeMs'])
  for t in trades:
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
  
  return trades