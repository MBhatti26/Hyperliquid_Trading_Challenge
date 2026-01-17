def determine_taint(trades, target_builder):
  net_size = 0
  is_tainted = False

  for t in trades:
    trade_amount = float(t['sz'])

    # add or subtract from net_size each trade
    if t['side'] == 'B': # buy
      net_size += trade_amount
    elif t['side'] == 'A': # sell
      net_size -= trade_amount

    # check for differing builders
    if net_size != 0 and t.get('builder') != target_builder:
      is_tainted = True

    t['tainted'] = is_tainted

    if net_size <= 0:
      is_tainted = False
  
  return trades