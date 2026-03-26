# =============================================
# ⚔️ BOT V17 (PRO STABLE EXECUTION ENGINE)
# =============================================

import requests, time, hmac, hashlib, base64, json, os
import numpy as np

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
PASSPHRASE = os.getenv("PASSPHRASE")
BASE_URL = "https://api.bitget.com"

SYMBOLS = [
    "BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT",
    "XLMUSDT","ZECUSDT","ENAUSDT"
]

MIN_SIZE = {
    "BTCUSDT": 0.001,
    "ETHUSDT": 0.01,
    "SOLUSDT": 0.1,
    "BNBUSDT": 0.01,
    "XLMUSDT": 1,
    "ZECUSDT": 0.01,
    "ENAUSDT": 1
}

# 🔥 HARD CAPS (FINAL FIX FOR LOW PRICE COINS)
MAX_SIZE = {
    "BTCUSDT": 0.01,
    "ETHUSDT": 0.5,
    "SOLUSDT": 10,
    "BNBUSDT": 1,
    "XLMUSDT": 500,
    "ZECUSDT": 2,
    "ENAUSDT": 800
}

open_positions = {}
MAX_TRADES = 3

win_streak = 0
loss_streak = 0

# ================= AUTH =================
def sign(msg):
    return base64.b64encode(
        hmac.new(API_SECRET.encode(), msg.encode(), hashlib.sha256).digest()
    ).decode()

def round_price(p):
    return float(f"{p:.2f}")

# ================= MARKET =================
def get_candles(symbol):
    url = f"{BASE_URL}/api/v2/mix/market/candles?symbol={symbol}&granularity=5m&productType=USDT-FUTURES&limit=100"
    try:
        return requests.get(url).json().get("data", [])
    except:
        return []

# ================= CHOP FILTER =================
def is_choppy(c):
    closes = [float(x[4]) for x in c]
    recent_range = max(closes[-10:]) - min(closes[-10:])
    avg_move = np.mean([abs(closes[i]-closes[i-1]) for i in range(-20, -1)])
    return recent_range < avg_move * 1.2

# ================= SIGNAL =================
def analyze(symbol):
    c = get_candles(symbol)
    if len(c) < 50: return None

    if is_choppy(c):
        print(symbol, "CHOPPY → SKIP")
        return None

    closes = [float(x[4]) for x in c]
    highs = [float(x[2]) for x in c]
    lows = [float(x[3]) for x in c]

    price = closes[-1]
    ema50 = np.mean(closes[-50:])

    if price < min(lows[-10:-1]):
        return "LONG"
    if price > max(highs[-10:-1]):
        return "SHORT"
    if price > ema50:
        return "LONG"
    if price < ema50:
        return "SHORT"

    return None

# ================= SIZE =================
def size_calc(symbol, balance, price):
    global win_streak, loss_streak

    leverage = 3
    allocation = 0.08

    if win_streak >= 2:
        allocation = min(0.12, allocation + 0.01 * win_streak)

    if loss_streak >= 2:
        allocation = max(0.04, allocation - 0.02 * loss_streak)

    position_value = balance * allocation
    size = (position_value * leverage) / price

    size = min(size, MAX_SIZE[symbol])

    size = round(size, 3)

    if size * price > balance * 0.5:
        return None

    return max(size, MIN_SIZE[symbol])

# ================= ORDER =================
def place_order(symbol, side, size, sl):
    endpoint = "/api/v2/mix/order/place-order"
    url = BASE_URL + endpoint

    body = {
        "symbol": symbol,
        "productType": "USDT-FUTURES",
        "marginMode": "crossed",
        "marginCoin": "USDT",
        "size": str(size),
        "side": "buy" if side=="LONG" else "sell",
        "orderType": "market",
        "presetStopLossPrice": str(round_price(sl))
    }

    ts = str(int(time.time()*1000))
    msg = ts+"POST"+endpoint+json.dumps(body)
    sig = sign(msg)

    headers = {
        "ACCESS-KEY": API_KEY,
        "ACCESS-SIGN": sig,
        "ACCESS-TIMESTAMP": ts,
        "ACCESS-PASSPHRASE": PASSPHRASE,
        "Content-Type": "application/json"
    }

    try:
        res = requests.post(url, headers=headers, data=json.dumps(body)).json()
    except:
        return None

    return res

# ================= CLOSE =================
def close_position(symbol, side, size):
    endpoint = "/api/v2/mix/order/place-order"
    url = BASE_URL + endpoint

    close_side = "sell" if side=="LONG" else "buy"

    body = {
        "symbol": symbol,
        "productType": "USDT-FUTURES",
        "marginMode": "crossed",
        "marginCoin": "USDT",
        "size": str(size),
        "side": close_side,
        "orderType": "market",
        "reduceOnly": "true"
    }

    ts = str(int(time.time()*1000))
    msg = ts+"POST"+endpoint+json.dumps(body)
    sig = sign(msg)

    headers = {
        "ACCESS-KEY": API_KEY,
        "ACCESS-SIGN": sig,
        "ACCESS-TIMESTAMP": ts,
        "ACCESS-PASSPHRASE": PASSPHRASE,
        "Content-Type": "application/json"
    }

    try:
        res = requests.post(url, headers=headers, data=json.dumps(body)).json()
        print("CLOSED:", res)
    except:
        print("CLOSE ERROR")

# ================= MAIN =================
def run():
    global win_streak, loss_streak

    balance = 1000

    print("BOT STARTED...")

    while True:

        order_placed = False

        # ENTRY
        for s in SYMBOLS:

            if order_placed:
                break

            if len(open_positions) >= MAX_TRADES:
                break

            if s in open_positions:
                continue

            signal = analyze(s)
            if not signal:
                continue

            candles = get_candles(s)
            price = float(candles[-1][4])

            size = size_calc(s, balance, price)

            if size is None:
                print(f"{s} SKIP: size too large")
                continue

            sl = price * 0.98 if signal=="LONG" else price * 1.02

            print(f"{s} | {signal} | {price} | size {size}")

            res = place_order(s, signal, size, sl)

            # 🔥 STRICT RESPONSE CHECK
            if not res or "code" not in res:
                print(f"{s} ERROR: No API response")
                continue

            print(res)

            if res.get("code") == "00000":
                open_positions[s] = {
                    "side": signal,
                    "entry": price,
                    "size": size
                }
                order_placed = True
                time.sleep(1)

        # EXIT
        for s in list(open_positions.keys()):
            candles = get_candles(s)
            price = float(candles[-1][4])

            pos = open_positions[s]
            entry = pos["entry"]
            side = pos["side"]
            size = pos["size"]

            pnl = ((price-entry)/entry)*100 if side=="LONG" else ((entry-price)/entry)*100

            print(f"{s} PNL: {pnl:.2f}%")

            if pnl >= 2:
                print(f"{s} TAKE PROFIT")
                close_position(s, side, size)
                del open_positions[s]
                win_streak += 1
                loss_streak = 0

            elif pnl <= -1.5:
                print(f"{s} STOP LOSS")
                close_position(s, side, size)
                del open_positions[s]
                loss_streak += 1
                win_streak = 0

        print(f"WIN STREAK: {win_streak} | LOSS STREAK: {loss_streak}")

        time.sleep(30)

if __name__ == "__main__":
    run()
