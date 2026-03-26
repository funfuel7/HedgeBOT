# =============================================
# ⚔️ FINAL BOT V8 (TRAILING + BREAKEVEN + HEDGE)
# =============================================

import requests, time, hmac, hashlib, base64, json, os
import numpy as np

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
PASSPHRASE = os.getenv("PASSPHRASE")
BASE_URL = "https://api.bitget.com"

CRYPTO = ["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT"]
STOCKS = ["NAS100USDT","SPXUSDT"]
METALS = ["XAUUSDT","XAGUSDT"]

SYMBOLS = CRYPTO + STOCKS + METALS

open_positions = {}
MAX_TRADES = 3
RISK = 0.01

# ================= AUTH =================
def sign(msg):
    return base64.b64encode(
        hmac.new(API_SECRET.encode(), msg.encode(), hashlib.sha256).digest()
    ).decode()

def round_price(p): return round(p, 3)

# ================= DATA =================
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
    rsi = 100 - (100/(1 + np.mean([x for x in np.diff(closes) if x>0]) / (abs(np.mean([x for x in np.diff(closes) if x<0]))+1e-6)))

    if price < min(lows[-10:-1]) and rsi < 30: return "LONG"
    if price > max(highs[-10:-1]) and rsi > 70: return "SHORT"

    if price > ema50: return "LONG"
    if price < ema50: return "SHORT"

    return None

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

# ================= POSITION SIZE =================
def size_calc(balance, price):
    return round(max((balance*RISK)/price, 0.001),3)

# ================= MAIN =================
def run():
    balance = 1000

    print("BOT STARTED...")

    while True:
        for s in SYMBOLS:

            if len(open_positions) >= MAX_TRADES: break
            if s in open_positions: continue

            signal = analyze(s)
            if not signal: continue

            candles = get_candles(s)
            price = float(candles[-1][4])
            size = size_calc(balance, price)

            if signal=="LONG":
                sl = price*0.98
            else:
                sl = price*1.02

            print(f"{s} | {signal} | {price}")

            res = place_order(s, signal, size, sl)
            print(res)

            open_positions[s] = {
                "side": signal,
                "entry": price,
                "sl": sl
            }

        # ================= TRAILING + BREAKEVEN =================
        for s in list(open_positions.keys()):
            candles = get_candles(s)
            price = float(candles[-1][4])

            pos = open_positions[s]
            entry = pos["entry"]
            side = pos["side"]

            # breakeven
            if side=="LONG" and price > entry*1.01:
                pos["sl"] = entry
            if side=="SHORT" and price < entry*0.99:
                pos["sl"] = entry

            # trailing
            if side=="LONG":
                new_sl = price*0.98
                if new_sl > pos["sl"]:
                    pos["sl"] = new_sl

            if side=="SHORT":
                new_sl = price*1.02
                if new_sl < pos["sl"]:
                    pos["sl"] = new_sl

        time.sleep(60)

if __name__ == "__main__":
    run()
