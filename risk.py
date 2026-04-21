def calculate_position_size(balance, risk_per_trade, entry, sl):
    risk_amount = balance * risk_per_trade
    sl_distance = abs(entry - sl)
    size = risk_amount / sl_distance
    return size
