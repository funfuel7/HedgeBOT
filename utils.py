import requests

def get_ohlcv(symbol):
    url = f"https://api.bitget.com/api/mix/v1/market/candles?symbol={symbol}&granularity=5m&limit=100"
    data = requests.get(url).json()
    df = pd.DataFrame(data, columns=["time","open","high","low","close","volume"])
    df = df.astype(float)
    return df
