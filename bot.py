# =============================================
# ⚔️ FINAL BOT V5 (SL + TP + SAFE + ENV FIX)
# =============================================

import requests
import time
import hmac
import hashlib
import base64
import json
import numpy as np
import os

# ================= CONFIG =================
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
PASSPHRASE = os.getenv("PASSPHRASE")
BASE_URL = "https://api.bitget.com"

SYMBOLS = ["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT"]
RISK_PER_TRADE = 0.01
MAX_TRADES = 3

open_positions = {}

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
    return res.get("data", [])

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

# ================= AI SIGNAL =================
def analyze(symbol):
    candles = get_candles(symbol)
    if len(candles) < 50:
        return None

    closes = [float(x[4]) for x in candles]
    highs = [float(x[2]) for x in candles]
    lows = [float(x[3]) for x in candles]

    current = closes[-1]
    prev_high = max(highs[-10:-1])
    prev_low = min(lows[-10:-1])

    ema50 = ema(closes, 50)
    rsi_val = rsi(closes)

    if current < prev_low and rsi_val < 30:
        return "LONG"
    if current > prev_high and rsi_val > 70:
        return "SHORT"

    if current > ema50 and rsi_val > 55:
        return "LONG"
    if current < ema50 and rsi_val < 45:
        return "SHORT"

    return None

# ================= SIZE =================
def calc_size(balance, price):
    size = (balance * RISK_PER_TRADE) / price
    return round(max(size, 0.001), 3)

# ================= ORDER =================
def place_order(symbol, side, size, sl, tp):
    if not API_KEY:
        print("API KEY MISSING!")
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
        "presetStopLossPrice": str(sl),
        "presetTakeProfitPrice": str(tp)
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

    res = requests.post(url, headers=headers, data=json.dumps(body))
    print("ORDER:", res.json())

# ================= MAIN =================
def run_bot():
    balance = 1000

    print("BOT STARTED...")

    while True:
        trades = 0

        for symbol in SYMBOLS:
            if trades >= MAX_TRADES:
                break

            if symbol in open_positions:
                continue

            signal = analyze(symbol)
            if not signal:
                continue

            candles = get_candles(symbol)
            price = float(candles[-1][4])
            size = calc_size(balance, price)

            # SL TP LOGIC
            if signal == "LONG":
                sl = price * 0.98
                tp = price * 1.04
            else:
                sl = price * 1.02
                tp = price * 0.96

            print(f"{symbol} | {signal} | Price: {price} | SL: {sl} | TP: {tp}")

            place_order(symbol, signal, size, sl, tp)

            open_positions[symbol] = signal
            trades += 1

        time.sleep(60)

# ================= START =================
if __name__ == "__main__":
    run_bot()
