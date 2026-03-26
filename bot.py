# =============================================
# ⚔️ BOT V12 (PRO AI + 30s EXIT CHECK)
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
def get_candles(symbol, tf="5m"):
    url = f"{BASE_URL}/api/v2/mix/market/candles?symbol={symbol}&granularity={tf}&productType=USDT-FUTURES&limit=100"
    try:
        return requests.get(url).json().get("data", [])
    except:
        return []

# ================= INDICATORS =================
def ema(data, p=50):
    return np.mean(data[-p:])

def rsi(data):
    deltas = np.diff(data)
    gain = np.mean([x for x in deltas if x > 0]) if len(deltas) else 0
    loss = abs(np.mean([x for x in deltas if x < 0])) if len(deltas) else 0
    if loss == 0: return 100
    rs = gain / loss
    return 100 - (100/(1+rs))

def volume_spike(volumes):
    return volumes[-1] > np.mean(volumes[-20:]) * 1.5

# ================= AI SIGNAL =================
def analyze(symbol):

    c5 = get_candles(symbol, "5m")
    c15 = get_candles(symbol, "15m")

    if len(c5) < 50 or len(c15) < 50:
        return None

    closes5 = [float(x[4]) for x in c5]
    highs5 = [float(x[2]) for x in c5]
    lows5 = [float(x[3]) for x in c5]
    vols5 = [float(x[5]) for x in c5]

    closes15 = [float(x[4]) for x in c15]

    price = closes5[-1]

    ema_htf = ema(closes15, 50)
    ema_ltf = ema(closes5, 50)
    rsi_val = rsi(closes5)

    prev_high = max(highs5[-10:-1])
    prev_low = min(lows5[-10:-1])

    vol_ok = volume_spike(vols5)

    # LONG
    if (
        price < prev_low and
        price > ema_ltf and
        price > ema_htf and
        rsi_val < 40 and
        vol_ok
    ):
        return "LONG"

    # SHORT
    if (
        price > prev_high and
        price < ema_ltf and
        price < ema_htf and
        rsi_val > 60 and
        vol_ok
    ):
        return "SHORT"

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

            print(f"{s} | {signal} | {price} | size {size}")

            res = place_order(s, signal, size, sl)
            print(res)

            if res.get("code") == "00000":
                open_positions[s] = {
                    "side": signal,
                    "entry": price,
                    "size": size
                }

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

            elif pnl <= -1.5:
                print(f"{s} STOP LOSS")
                close_position(s, side, size)
                del open_positions[s]

        time.sleep(30)  # 🔥 CHECK EVERY 30 SECONDS

if __name__ == "__main__":
    run()
