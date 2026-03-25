# =============================================
# ⚔️ ADAPTIVE HEDGE + AI BOT (STABLE V3 - FIXED)
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

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
RISK_PER_TRADE = 0.01
LEVERAGE = 3
MAX_TRADES = 3

# ================= AUTH =================
def sign(message):
    return base64.b64encode(hmac.new(API_SECRET.encode(), message.encode(), hashlib.sha256).digest()).decode()

# ================= MARKET DATA (V2 FIXED) =================
def get_candles(symbol):
    url = f"{BASE_URL}/api/v2/mix/market/candles?symbol={symbol}&granularity=5m&productType=USDT-FUTURES&limit=100"

    try:
        res = requests.get(url).json()
    except Exception as e:
        print("REQUEST ERROR:", e)
        return []

    if 'data' not in res or not isinstance(res['data'], list):
        print(f"API ERROR for {symbol}: ", res)
        return []

    return res['data']

# ================= INDICATORS =================
def ema(data, period=50):
    return np.mean(data[-period:])


def rsi(data, period=14):
    deltas = np.diff(data)
    gain = np.mean([x for x in deltas if x > 0]) if len([x for x in deltas if x > 0]) > 0 else 0
    loss = abs(np.mean([x for x in deltas if x < 0])) if len([x for x in deltas if x < 0]) > 0 else 0

    if loss == 0:
        return 100

    rs = gain / loss
    return 100 - (100 / (1 + rs))

# ================= AI SIGNAL =================
def analyze(symbol):
    candles = get_candles(symbol)

    if not candles or len(candles) < 50:
        return None

    try:
        closes = [float(x[4]) for x in candles if len(x) > 4]
        highs = [float(x[2]) for x in candles if len(x) > 2]
        lows = [float(x[3]) for x in candles if len(x) > 3]
    except:
        return None

    if len(closes) < 50:
        return None

    current = closes[-1]
    ema50 = ema(closes, 50)
    rsi_val = rsi(closes)

    # Liquidity sweep + reversal
    if current < min(lows[-10:-1]) and rsi_val < 30:
        return "LONG"

    if current > max(highs[-10:-1]) and rsi_val > 70:
        return "SHORT"

    # Trend
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

    if size < 0.001:
        size = 0.001

    return round(size, 3)

# ================= ORDER (V2 FIXED) =================
def place_order(symbol, side, size):
    if size <= 0:
        print("INVALID SIZE, skipping trade")
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
        response = requests.post(url, headers=headers, data=json.dumps(body))
        print("ORDER RESPONSE:", response.json())
    except Exception as e:
        print("ORDER ERROR:", e)

# ================= HEDGE =================
def hedge(symbol, side, size):
    hedge_side = "SHORT" if side == "LONG" else "LONG"
    hedge_size = size * 0.5
    place_order(symbol, hedge_side, hedge_size)

# ================= MAIN =================
def run_bot():
    balance = 1000
    open_trades = 0

    print("BOT STARTED...")

    while True:
        try:
            open_trades = 0

            for symbol in SYMBOLS:
                if open_trades >= MAX_TRADES:
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

                open_trades += 1

            time.sleep(60)

        except Exception as e:
            print("MAIN LOOP ERROR:", e)
            time.sleep(10)

# ================= START =================
if __name__ == "__main__":
    run_bot()
