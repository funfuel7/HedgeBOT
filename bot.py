# =============================================
# ⚔️ FINAL PRO BOT (V4 - FULL 3 LAYER SYSTEM)
# =============================================

import requests
import time
import hmac
import hashlib
import base64
import json
import numpy as np

# ================= CONFIG =================
API_KEY = "YOUR_API_KEY"
API_SECRET = "YOUR_API_SECRET"
PASSPHRASE = "YOUR_PASSPHRASE"
BASE_URL = "https://api.bitget.com"

# MULTI ASSET
CRYPTO = ["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","SUIUSDT","PEPEUSDT"]
STOCKS = ["NAS100USDT","SPXUSDT"]
METALS = ["XAUUSDT","XAGUSDT"]

SYMBOLS = CRYPTO + STOCKS + METALS

RISK_PER_TRADE = 0.01
MAX_TRADES = 5

# ================= AUTH =================
def sign(message):
    return base64.b64encode(hmac.new(API_SECRET.encode(), message.encode(), hashlib.sha256).digest()).decode()

# ================= MARKET DATA =================
def get_candles(symbol):
    url = f"{BASE_URL}/api/v2/mix/market/candles?symbol={symbol}&granularity=5m&productType=USDT-FUTURES&limit=100"

    try:
        res = requests.get(url).json()
    except:
        return []

    if 'data' not in res:
        return []

    return res['data']

# ================= INDICATORS =================
def ema(data, period=50):
    return np.mean(data[-period:])


def rsi(data):
    deltas = np.diff(data)
    gain = np.mean([x for x in deltas if x > 0]) if len(deltas) else 0
    loss = abs(np.mean([x for x in deltas if x < 0])) if len(deltas) else 0

    if loss == 0:
        return 100
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# ================= AI SCANNER =================
def analyze(symbol):
    candles = get_candles(symbol)
    if not candles or len(candles) < 50:
        return None

    closes = [float(x[4]) for x in candles]
    highs = [float(x[2]) for x in candles]
    lows = [float(x[3]) for x in candles]

    current = closes[-1]
    prev_high = max(highs[-10:-1])
    prev_low = min(lows[-10:-1])

    ema50 = ema(closes, 50)
    rsi_val = rsi(closes)

    # LIQUIDITY SWEEP
    if current < prev_low and rsi_val < 30:
        return "LONG"
    if current > prev_high and rsi_val > 70:
        return "SHORT"

    # TREND
    if current > ema50 and rsi_val > 55:
        return "LONG"
    if current < ema50 and rsi_val < 45:
        return "SHORT"

    return None

# ================= POSITION SIZE =================
def calc_size(balance, price):
    if price <= 0:
        return 0

    risk_amount = balance * RISK_PER_TRADE
    size = risk_amount / price

    return round(max(size, 0.001), 3)

# ================= ORDER (V2 FIXED) =================
def place_order(symbol, side, size):
    if size <= 0:
        return

    endpoint = "/api/v2/mix/order/place-order"
    url = BASE_URL + endpoint

    body = {
        "symbol": symbol,
        "productType": "USDT-FUTURES",
        "marginMode": "crossed",
        "marginCoin": "USDT",
        "size": str(size),
        "side": "buy" if side == "LONG" else "sell",
        "orderType": "market",
        "force": "gtc"
    }

    timestamp = str(int(time.time() * 1000))
    message = timestamp + "POST" + endpoint + json.dumps(body)
    signature = sign(message)

    headers = {
        "ACCESS-KEY": API_KEY,
        "ACCESS-SIGN": signature,
        "ACCESS-TIMESTAMP": timestamp,
        "ACCESS-PASSPHRASE": PASSPHRASE,
        "Content-Type": "application/json"
    }

    try:
        res = requests.post(url, headers=headers, data=json.dumps(body))
        print("ORDER:", res.json())
    except Exception as e:
        print("ORDER ERROR:", e)

# ================= HEDGE ENGINE =================
def hedge(symbol, side, size):
    hedge_side = "SHORT" if side == "LONG" else "LONG"
    hedge_size = size * 0.5
    place_order(symbol, hedge_side, hedge_size)

# ================= MAIN =================
def run_bot():
    balance = 1000

    print("BOT STARTED...")

    while True:
        trades = 0

        for symbol in SYMBOLS:
            if trades >= MAX_TRADES:
                break

            signal = analyze(symbol)
            if not signal:
                continue

            candles = get_candles(symbol)
            if not candles:
                continue

            price = float(candles[-1][4])
            size = calc_size(balance, price)

            print(f"{symbol} | {signal} | Price: {price} | Size: {size}")

            place_order(symbol, signal, size)
            hedge(symbol, signal, size)

            trades += 1

        time.sleep(60)

# ================= START =================
if __name__ == "__main__":
    run_bot()
