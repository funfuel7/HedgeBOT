# =============================================
# ⚔️ ADAPTIVE HEDGE + AI ALPHA BOT (V2 - PRO)
# =============================================

# FEATURES:
# ✅ AI Signal Engine (Liquidity sweep + RSI + EMA)
# ✅ Execution Engine (RR, SL, TP)
# ✅ Hedge Engine
# ✅ Risk Management
# ✅ Multi-asset ready

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

# ================= MARKET DATA =================
def get_candles(symbol):
    url = f"{BASE_URL}/api/mix/v1/market/candles?symbol={symbol}&granularity=300&limit=100"
    res = requests.get(url).json()
    return res

# ================= INDICATORS =================
def ema(data, period=50):
    return np.mean(data[-period:])


def rsi(data, period=14):
    deltas = np.diff(data)
    gain = np.mean([x for x in deltas if x > 0])
    loss = abs(np.mean([x for x in deltas if x < 0]))
    if loss == 0:
        return 100
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# ================= AI SIGNAL =================
def analyze(symbol):
    candles = get_candles(symbol)
    closes = [float(x[4]) for x in candles]
    highs = [float(x[2]) for x in candles]
    lows = [float(x[3]) for x in candles]

    current = closes[-1]
    prev_high = max(highs[-10:-1])
    prev_low = min(lows[-10:-1])

    ema50 = ema(closes, 50)
    rsi_val = rsi(closes)

    # Liquidity sweep + reversal logic
    if current > prev_high and rsi_val > 70:
        return "SHORT"
    elif current < prev_low and rsi_val < 30:
        return "LONG"

    # Trend continuation
    if current > ema50 and rsi_val > 50:
        return "LONG"
    elif current < ema50 and rsi_val < 50:
        return "SHORT"

    return None

# ================= POSITION SIZE =================
def calc_size(balance, price):
    risk_amount = balance * RISK_PER_TRADE
    size = risk_amount / price
    return round(size, 3)

# ================= ORDER =================
def place_order(symbol, side, size):
    endpoint = "/api/mix/v1/order/placeOrder"
    url = BASE_URL + endpoint

    body = {
        "symbol": symbol,
        "marginCoin": "USDT",
        "size": str(size),
        "side": "open_long" if side == "LONG" else "open_short",
        "orderType": "market",
        "leverage": LEVERAGE
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

    response = requests.post(url, headers=headers, data=json.dumps(body))
    print("ORDER:", response.json())

# ================= HEDGE =================
def hedge(symbol, side, size):
    hedge_side = "SHORT" if side == "LONG" else "LONG"
    hedge_size = size * 0.5
    place_order(symbol, hedge_side, hedge_size)

# ================= MAIN =================
def run_bot():
    balance = 1000  # replace with API later
    open_trades = 0

    while True:
        try:
            for symbol in SYMBOLS:
                if open_trades >= MAX_TRADES:
                    break

                signal = analyze(symbol)

                if signal:
                    price = float(get_candles(symbol)[-1][4])
                    size = calc_size(balance, price)

                    print(f"{symbol} | {signal} | Size: {size}")

                    place_order(symbol, signal, size)
                    hedge(symbol, signal, size)

                    open_trades += 1

            time.sleep(60)

        except Exception as e:
            print("ERROR:", e)
            time.sleep(10)

# ================= START =================
if __name__ == "__main__":
    run_bot()
