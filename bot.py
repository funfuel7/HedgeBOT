# =============================================
# ⚔️ BOT V10 (DUAL EXIT: TP + BOT CLOSE)
# =============================================

import requests, time, hmac, hashlib, base64, json, os
import numpy as np

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
PASSPHRASE = os.getenv("PASSPHRASE")
BASE_URL = "https://api.bitget.com"

SYMBOLS = ["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT"]

MIN_SIZE = {
    "BTCUSDT": 0.001,
    "ETHUSDT": 0.01,
    "SOLUSDT": 0.1,
    "BNBUSDT": 0.01
}

open_positions = {}
MAX_TRADES = 3
RISK = 0.01

# ================= AUTH =================
def sign(msg):
    return base64.b64encode(
        hmac.new(API_SECRET.encode(), msg.encode(), hashlib.sha256).digest()
    ).decode()

def round_price(p): return round(p, 3)

# ================= MARKET =================
def get_candles(symbol):
    url = f"{BASE_URL}/api/v2/mix/market/candles?symbol={symbol}&granularity=5m&productType=USDT-FUTURES&limit=100"
    try:
        return requests.get(url).json().get("data", [])
    except:
        return []

# ================= SIGNAL =================
def analyze(symbol):
    c = get_candles(symbol)
    if len(c) < 50: return None

    closes = [float(x[4]) for x in c]
    highs = [float(x[2]) for x in c]
    lows = [float(x[3]) for x in c]

    price = closes[-1]
    ema50 = np.mean(closes[-50:])

    if price < min(lows[-10:-1]): return "LONG"
    if price > max(highs[-10:-1]): return "SHORT"

    if price > ema50: return "LONG"
    if price < ema50: return "SHORT"

    return None

# ================= SIZE =================
def size_calc(symbol, balance, price):
    size = (balance * RISK) / price
    return max(round(size, 3), MIN_SIZE[symbol])

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

    return requests.post(url, headers=headers, data=json.dumps(body)).json()

# ================= TP LIMIT ORDER =================
def place_tp(symbol, side, size, tp):
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
        "orderType": "limit",
        "price": str(round_price(tp)),
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

    res = requests.post(url, headers=headers, data=json.dumps(body))
    print("TP ORDER:", res.json())

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

    res = requests.post(url, headers=headers, data=json.dumps(body))
    print("CLOSED:", res.json())

# ================= MAIN =================
def run():
    balance = 1000

    print("BOT STARTED...")

    while True:

        # ENTRY
        for s in SYMBOLS:

            if len(open_positions) >= MAX_TRADES: break
            if s in open_positions: continue

            signal = analyze(s)
            if not signal: continue

            candles = get_candles(s)
            price = float(candles[-1][4])

            size = size_calc(s, balance, price)

            sl = price * 0.98 if signal=="LONG" else price * 1.02
            tp = price * 1.02 if signal=="LONG" else price * 0.98

            print(f"{s} | {signal} | {price}")

            res = place_order(s, signal, size, sl)
            print(res)

            if res.get("code") == "00000":
                place_tp(s, signal, size, tp)

                open_positions[s] = {
                    "side": signal,
                    "entry": price,
                    "size": size
                }

        # EXIT MANAGEMENT
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
                print(f"{s} BOT TP HIT")
                close_position(s, side, size)
                del open_positions[s]

            elif pnl <= -1.5:
                print(f"{s} BOT SL HIT")
                close_position(s, side, size)
                del open_positions[s]

        time.sleep(60)

if __name__ == "__main__":
    run()
