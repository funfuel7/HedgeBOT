# =========================================================
# 🚀 BITGET V20 DEBUG BOT (FULL DIAGNOSTIC MODE)
# =========================================================

import requests
import time
import hmac
import hashlib
import base64
import json

# ================= CONFIG =================
API_KEY = "YOUR_API_KEY"
API_SECRET = "YOUR_API_SECRET"
PASSPHRASE = "YOUR_PASSPHRASE"

BASE_URL = "https://api.bitget.com"

# ==========================================

def sign(timestamp, method, request_path, body=""):
    message = str(timestamp) + method + request_path + body
    mac = hmac.new(API_SECRET.encode(), message.encode(), hashlib.sha256)
    return base64.b64encode(mac.digest()).decode()


def get_headers(method, path, body=""):
    timestamp = str(int(time.time() * 1000))
    signature = sign(timestamp, method, path, body)

    return {
        "ACCESS-KEY": API_KEY,
        "ACCESS-SIGN": signature,
        "ACCESS-TIMESTAMP": timestamp,
        "ACCESS-PASSPHRASE": PASSPHRASE,
        "Content-Type": "application/json"
    }


# =========================================================
# 🔍 DEBUG FUNCTIONS
# =========================================================

def test_server():
    print("\n🌐 TESTING SERVER CONNECTION...")
    try:
        res = requests.get(BASE_URL + "/api/spot/v1/public/time")
        print("✅ Server reachable:", res.text)
    except Exception as e:
        print("❌ Server connection failed:", e)


def test_balance():
    print("\n💰 CHECKING FUTURES BALANCE...")

    path = "/api/mix/v1/account/accounts"
    url = BASE_URL + path

    headers = get_headers("GET", path)

    try:
        res = requests.get(url, headers=headers)
        data = res.json()

        print("RAW RESPONSE:", data)

        if data.get("code") == "00000":
            balances = data.get("data", [])
            for b in balances:
                if b.get("marginCoin") == "USDT":
                    print(f"✅ AVAILABLE BALANCE: {b.get('available')}")
                    return
            print("⚠️ No USDT futures balance found")

        else:
            explain_error(data)

    except Exception as e:
        print("❌ Balance request failed:", e)


def test_positions():
    print("\n📊 CHECKING OPEN POSITIONS...")

    path = "/api/mix/v1/position/allPosition"
    url = BASE_URL + path

    headers = get_headers("GET", path)

    try:
        res = requests.get(url, headers=headers)
        data = res.json()

        print("RAW RESPONSE:", data)

        if data.get("code") == "00000":
            positions = data.get("data", [])
            print(f"✅ TOTAL POSITIONS: {len(positions)}")

            for p in positions:
                if float(p.get("total", 0)) > 0:
                    print(f"👉 {p.get('symbol')} | size: {p.get('total')}")

        else:
            explain_error(data)

    except Exception as e:
        print("❌ Position request failed:", e)


def test_order_permission():
    print("\n⚔️ TESTING ORDER PERMISSION (SAFE TEST)...")

    path = "/api/mix/v1/order/placeOrder"
    url = BASE_URL + path

    body = json.dumps({
        "symbol": "BTCUSDT",
        "marginCoin": "USDT",
        "size": "0.001",
        "side": "open_long",
        "orderType": "market",
        "timeInForceValue": "normal"
    })

    headers = get_headers("POST", path, body)

    try:
        res = requests.post(url, headers=headers, data=body)
        data = res.json()

        print("RAW RESPONSE:", data)

        if data.get("code") == "00000":
            print("✅ ORDER PERMISSION WORKING")
        else:
            explain_error(data)

    except Exception as e:
        print("❌ Order test failed:", e)


# =========================================================
# 🧠 ERROR EXPLAINER (IMPORTANT)
# =========================================================

def explain_error(data):
    code = data.get("code")
    msg = data.get("msg")

    print(f"\n❌ ERROR CODE: {code}")
    print(f"❌ MESSAGE: {msg}")

    if code == "40014":
        print("👉 FIX: Enable Futures (Contract) permission OR remove IP restriction")

    elif code == "40037":
        print("👉 FIX: API key invalid")

    elif code == "40762":
        print("👉 FIX: Order size too big for your balance")

    elif code == "45115":
        print("👉 FIX: Price/size precision issue")

    elif code == "30032":
        print("👉 FIX: Using deprecated API version")

    else:
        print("👉 UNKNOWN ERROR — CHECK API SETTINGS")


# =========================================================
# 🚀 RUN ALL TESTS
# =========================================================

def run_debug():
    print("\n==============================")
    print("🚀 BITGET V20 DEBUG STARTED")
    print("==============================")

    test_server()
    test_balance()
    test_positions()
    test_order_permission()

    print("\n==============================")
    print("✅ DEBUG COMPLETE")
    print("==============================")


if __name__ == "__main__":
    run_debug()
