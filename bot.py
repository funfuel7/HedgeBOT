# =============================================
# ⚔️ FINAL BOT V7 (TP FIXED + SEPARATE TP ORDER)
# =============================================

import requests
import time
import hmac
import hashlib
import base64
import json
import numpy as np
import os

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
    return base64.b64encode(
        hmac.new(API_SECRET.encode(), message.encode(), hashlib.sha256).digest()
    ).decode()

def round_price(price):
    return round(price, 3)

# ================= MARKET =================
def get_candles(symbol):
    url = f"{BASE_URL}/api/v2/mix/market/candles?symbol={symbol}&granularity=5m&productType=USDT-FUTURES&limit=100"
    try:
        return requests.get(url).json().get("data", [])
    except:
        return []

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

# ================= AI =================
def analyze(symbol):
    candles = get_candles(symbol)
    if len(candles) < 50:
        return None

    closes = [float(x[4]) for x in candles]
    highs = [float(x[2]) for x in candles]
    lows = [float(x[3]) for x in candles]

    current = closes[-1]
    ema50 = ema(closes, 50)
    rsi_val = rsi(closes)

    if current < min(lows[-10:-1]) and rsi_val < 30:
        return "LONG"

    if current > max(highs[-10:-1]) and rsi_val > 70:
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
def place_market_order(symbol, side, size, sl):
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
        "presetStopLossPrice": str(round_price(sl))
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
    return res.json()

# ================= TP ORDER =================
def place_tp_order(symbol, side, size, tp):
    endpoint = "/api/v2/mix/order/place-order"
    url = BASE_URL + endpoint

    # opposite side to close position
    close_side = "sell" if side == "LONG" else "buy"

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
    print("TP ORDER:", res.json())

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

            if signal == "LONG":
                sl = price * 0.98
                tp = price * 1.04
            else:
                sl = price * 1.02
                tp = price * 0.96

            print(f"{symbol} | {signal} | Price: {price} | SL: {sl} | TP: {tp}")

            order = place_market_order(symbol, signal, size, sl)
            print("ORDER:", order)

            # PLACE TP SEPARATELY
            place_tp_order(symbol, signal, size, tp)

            open_positions[symbol] = signal
            trades += 1

        time.sleep(60)

# ================= START =================
if __name__ == "__main__":
    run_bot()
