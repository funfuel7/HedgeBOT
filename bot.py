# =============================================
# ⚔️ BOT V19 FINAL (STABLE + REAL BALANCE FIXED)
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

MAX_TRADES = 3

# ================= AUTH =================
def sign(msg):
    return base64.b64encode(
        hmac.new(API_SECRET.encode(), msg.encode(), hashlib.sha256).digest()
    ).decode()

def headers(method, endpoint, body=""):
    ts = str(int(time.time()*1000))
    msg = ts + method + endpoint + body
    return {
        "ACCESS-KEY": API_KEY,
        "ACCESS-SIGN": sign(msg),
        "ACCESS-TIMESTAMP": ts,
        "ACCESS-PASSPHRASE": PASSPHRASE,
        "Content-Type": "application/json"
    }

# ================= BALANCE (FIXED) =================
def get_balance():
    endpoint = "/api/v2/mix/account/accounts?productType=USDT-FUTURES"
    url = BASE_URL + endpoint

    try:
        res = requests.get(url, headers=headers("GET", endpoint)).json()

        print("BALANCE RAW:", res)

        if res.get("code") != "00000":
            return 0

        data = res.get("data", [])
        if not data:
            return 0

        acc = data[0]

        if "available" in acc:
            return float(acc["available"])

        if "crossMaxAvailable" in acc:
            return float(acc["crossMaxAvailable"])

        return 0

    except Exception as e:
        print("BALANCE ERROR:", e)
        return 0

# ================= POSITIONS =================
def get_positions():
    endpoint = "/api/v2/mix/position/all-position?productType=USDT-FUTURES"
    url = BASE_URL + endpoint

    try:
        res = requests.get(url, headers=headers("GET", endpoint)).json()

        if res.get("code") != "00000":
            return {}

        positions = {}

        for p in res.get("data", []):
            size = float(p.get("total", 0))
            if size == 0:
                continue

            symbol = p["symbol"]
            entry = float(p["openPriceAvg"])
            side = "LONG" if p["holdSide"] == "long" else "SHORT"

            positions[symbol] = {
                "entry": entry,
                "side": side,
                "size": size
            }

        return positions

    except Exception as e:
        print("POSITION ERROR:", e)
        return {}

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
    if len(c) < 50:
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
def size_calc(balance, price):
    leverage = 3
    allocation = 0.04

    # SAFE BUFFER
    position_value = balance * allocation * 0.7

    size = (position_value * leverage) / price
    return round(size, 3)

# ================= ORDER =================
def place_order(symbol, side, size):
    endpoint = "/api/v2/mix/order/place-order"
    url = BASE_URL + endpoint

    body = json.dumps({
        "symbol": symbol,
        "productType": "USDT-FUTURES",
        "marginMode": "crossed",
        "marginCoin": "USDT",
        "size": str(size),
        "side": "buy" if side=="LONG" else "sell",
        "orderType": "market"
    })

    try:
        res = requests.post(url, headers=headers("POST", endpoint, body), data=body).json()
        print("ORDER:", res)
        return res
    except Exception as e:
        print("ORDER ERROR:", e)
        return None

# ================= CLOSE =================
def close_position(symbol, side, size):
    endpoint = "/api/v2/mix/order/place-order"
    url = BASE_URL + endpoint

    body = json.dumps({
        "symbol": symbol,
        "productType": "USDT-FUTURES",
        "marginMode": "crossed",
        "marginCoin": "USDT",
        "size": str(size),
        "side": "sell" if side=="LONG" else "buy",
        "orderType": "market",
        "reduceOnly": "true"
    })

    try:
        res = requests.post(url, headers=headers("POST", endpoint, body), data=body).json()
        print("CLOSED:", res)
    except Exception as e:
        print("CLOSE ERROR:", e)

# ================= MAIN =================
def run():
    print("🚀 BOT V19 FINAL STARTED...")

    while True:
        try:
            balance = get_balance()
            print("AVAILABLE BALANCE:", balance)

            positions = get_positions()
            print("ACTIVE POSITIONS:", list(positions.keys()))

            # ===== EXIT =====
            for s, pos in positions.items():
                candles = get_candles(s)
                if not candles:
                    continue

                price = float(candles[-1][4])
                entry = pos["entry"]
                side = pos["side"]
                size = pos["size"]

                pnl = ((price-entry)/entry)*100 if side=="LONG" else ((entry-price)/entry)*100

                print(f"{s} PNL: {pnl:.2f}%")

                if pnl >= 2:
                    print(f"{s} TAKE PROFIT")
                    close_position(s, side, size)

                elif pnl <= -1.5:
                    print(f"{s} STOP LOSS")
                    close_position(s, side, size)

            # ===== ENTRY =====
            if len(positions) < MAX_TRADES and balance > 20:

                for s in SYMBOLS:

                    if s in positions:
                        continue

                    signal = analyze(s)
                    if not signal:
                        continue

                    candles = get_candles(s)
                    if not candles:
                        continue

                    price = float(candles[-1][4])
                    size = size_calc(balance, price)

                    print(f"{s} | {signal} | {price} | size {size}")

                    res = place_order(s, signal, size)

                    if res and res.get("code") == "00000":
                        break

            else:
                print("LOW BALANCE OR MAX TRADES → SKIP ENTRY")

        except Exception as e:
            print("MAIN LOOP ERROR:", e)

        time.sleep(30)

if __name__ == "__main__":
    run()
