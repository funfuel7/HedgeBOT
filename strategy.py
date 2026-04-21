import pandas as pd
import ta

def generate_signal(df):
    df['ema9'] = ta.trend.ema_indicator(df['close'], window=9)
    df['ema21'] = ta.trend.ema_indicator(df['close'], window=21)
    df['rsi'] = ta.momentum.rsi(df['close'], window=14)

    last = df.iloc[-1]
    prev = df.iloc[-2]

    # Bullish Engulfing
    bullish = prev['close'] < prev['open'] and last['close'] > last['open'] and last['close'] > prev['open']

    # Bearish Engulfing
    bearish = prev['close'] > prev['open'] and last['close'] < last['open'] and last['close'] < prev['open']

    # LONG
    if bullish and last['rsi'] < 40 and last['ema9'] > last['ema21']:
        return "long"

    # SHORT
    if bearish and last['rsi'] > 60 and last['ema9'] < last['ema21']:
        return "short"

    return None
