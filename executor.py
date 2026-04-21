import time

def manage_trade(client, symbol, side, entry_price, size):
    tp1 = entry_price * (1 + 0.006 if side == "long" else 1 - 0.006)
    tp2 = entry_price * (1 + 0.012 if side == "long" else 1 - 0.012)
    sl = entry_price * (1 - 0.005 if side == "long" else 1 + 0.005)

    partial_closed = False

    while True:
        price = client.get_price(symbol)

        # Stop Loss
        if (side == "long" and price <= sl) or (side == "short" and price >= sl):
            client.close_position(symbol)
            print("SL HIT")
            break

        # TP1
        if not partial_closed:
            if (side == "long" and price >= tp1) or (side == "short" and price <= tp1):
                client.partial_close(symbol, 0.5)
                partial_closed = True
                print("Partial profit booked")

        # TP2
        if (side == "long" and price >= tp2) or (side == "short" and price <= tp2):
            client.close_position(symbol)
            print("Full TP hit")
            break

        # Momentum dying exit
        if partial_closed:
            if abs(price - tp1) < 0.001:
                client.close_position(symbol)
                print("Exited due to weak momentum")
                break

        time.sleep(2)
