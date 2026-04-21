from strategy import generate_signal
from utils import get_ohlcv
from executor import manage_trade
from risk import calculate_position_size
import config

def run_bot(client, balance):

    active_trades = 0

    for symbol in config.SYMBOLS:

        if active_trades >= config.MAX_TRADES:
            break

        df = get_ohlcv(symbol)
        signal = generate_signal(df)

        if signal:
            entry = df['close'].iloc[-1]
            sl = entry * (1 - config.SL if signal == "long" else 1 + config.SL)

            size = calculate_position_size(balance, config.RISK_PER_TRADE, entry, sl)

            client.open_position(symbol, signal, size, config.LEVERAGE)

            manage_trade(client, symbol, signal, entry, size)

            active_trades += 1
