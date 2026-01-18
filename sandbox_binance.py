import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from binance.client import Client
from binance.exceptions import BinanceAPIException
from datetime import datetime

# =========================
# KONFIGURACJA MYSQL
# =========================
MYSQL_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "menago",
    "port": 3306
}

TABLE = "bnbusdt_1h"
TRADES_TABLE = "_binance_crypto_trades"
HISTORY_BARS = 50  # ile świec pobrać

# =========================
# KONFIGURACJA BINANCE SANDBOX
# =========================
BINANCE_API_KEY = "Twój_Sandbox_API_KEY"
BINANCE_API_SECRET = "Twój_Sandbox_API_SECRET"
SYMBOL = "BNBUSDT"

try:
    client = Client(BINANCE_API_KEY, BINANCE_API_SECRET, testnet=True)
    print(f"{datetime.now()} ✅ Połączono z Binance Sandbox")
except BinanceAPIException as e:
    print(f"{datetime.now()} ❌ Błąd połączenia z Binance: {e}")
    exit(1)

# =========================
# PARAMETRY STRATEGII
# =========================
NUM_FALLING = 6
ALLOW_ONE_BREAK = True
TAKE_PROFIT_PERC = 12.0
STOP_LOSS_PERC = 5.0
RED_CANDLES_TO_SELL = 3
LOSS_LOOKBACK_BARS = 1
BUY_QUANTITY = 1  # ilość BNB do kupna

# =========================
# POZYCJA AKTYWNA
# =========================
class Position:
    def __init__(self):
        self.active = False
        self.db_id = None      # ID rekordu w bazie _binance_crypto_trades
        self.entry_price = 0.0
        self.tp_tracking = False
        self.red_count = 0

position = Position()

# =========================
# POŁĄCZENIE Z MYSQL
# =========================
def get_engine():
    return create_engine(
        f"mysql+mysqlconnector://{MYSQL_CONFIG['user']}:{MYSQL_CONFIG['password']}"
        f"@{MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{MYSQL_CONFIG['database']}"
    )

# =========================
# POBRANIE DANYCH HISTORYCZNYCH
# =========================
def load_data():
    try:
        print(f"{datetime.now()} 🔄 Łączenie z bazą MySQL...")
        engine = get_engine()
        query = f"SELECT * FROM {TABLE} ORDER BY open_time DESC LIMIT {HISTORY_BARS}"
        df = pd.read_sql(query, engine)
        df = df[::-1].reset_index(drop=True)  # od najstarszej do najnowszej
        print(f"{datetime.now()} ✅ Dane pobrane z bazy ({len(df)} świec)")
        return df
    except SQLAlchemyError as e:
        print(f"{datetime.now()} ❌ Błąd podczas pobierania danych z MySQL: {e}")
        return pd.DataFrame()

# =========================
# SPRAWDZENIE AKTYWNEJ POZYCJI W BAZIE
# =========================
def check_open_position(symbol):
    engine = get_engine()
    query = f"SELECT * FROM {TRADES_TABLE} WHERE symbol = '{symbol}' AND position_status = 'OPEN' ORDER BY buy_time DESC LIMIT 1"
    df = pd.read_sql(query, engine)
    if df.empty:
        return None
    return df.iloc[0]  # ostatnia otwarta pozycja

# =========================
# FUNKCJE STRATEGII
# =========================
def check_falling(df, num, allow_break):
    falling_count = 0
    break_used = False
    for i in range(1, num + (1 if allow_break else 0) + 1):
        mid_curr = (df['open'].iloc[-i] + df['close'].iloc[-i]) / 2
        mid_prev = (df['open'].iloc[-i-1] + df['close'].iloc[-i-1]) / 2
        if mid_curr < mid_prev:
            falling_count += 1
        else:
            if allow_break and not break_used:
                break_used = True
            else:
                return False
    return falling_count >= num

def recent_loss(symbol, since_bars):
    engine = get_engine()
    query = f"""
        SELECT * FROM {TRADES_TABLE} 
        WHERE symbol = '{symbol}' AND position_status = 'CLOSED'
        ORDER BY sell_time DESC LIMIT {since_bars}
    """
    df = pd.read_sql(query, engine)
    if df.empty:
        return False
    last_trade = df.iloc[0]
    return last_trade['profit_loss_perc'] < 0

# =========================
# DODAWANIE I AKTUALIZACJA TRANSAKCJI W BAZIE
# =========================
def insert_trade(symbol, buy_price, buy_time):
    engine = get_engine()
    sql = f"""
        INSERT INTO {TRADES_TABLE} (symbol, buy_time, buy_price, position_status)
        VALUES (%s, %s, %s, 'OPEN')
    """
    with engine.begin() as conn:
        result = conn.execute(sql, (symbol, buy_time, buy_price))
        trade_id = result.lastrowid
    return trade_id

def update_trade(trade_id, sell_price, sell_time, profit_perc):
    engine = get_engine()
    sql = f"""
        UPDATE {TRADES_TABLE} 
        SET sell_price = %s, sell_time = %s, profit_loss_perc = %s, position_status = 'CLOSED'
        WHERE id = %s
    """
    with engine.begin() as conn:
        conn.execute(sql, (sell_price, sell_time, profit_perc, trade_id))

# =========================
# LOGIKA STRATEGII
# =========================
def run_strategy():
    global position
    df = load_data()
    if df.empty:
        print(f"{datetime.now()} ❌ Brak danych do analizy. Kończę działanie.")
        return

    current_price = df['close'].iloc[-1]  # cena z bazy
    print(f"{datetime.now()} ℹ️ Aktualna cena (z bazy) {SYMBOL}: {current_price}")

    # Sprawdzenie aktywnej pozycji w bazie
    open_trade = check_open_position(SYMBOL)
    if open_trade is not None:
        position.active = True
        position.db_id = open_trade['id']
        position.entry_price = open_trade['buy_price']
        print(f"{datetime.now()} ℹ️ Aktywna pozycja w bazie – kupno po {position.entry_price} USDT")
    else:
        position.active = False
        position.db_id = None
        position.entry_price = 0.0

    # Sprawdzenie warunków kupna
    if not position.active:
        if check_falling(df, NUM_FALLING, ALLOW_ONE_BREAK) and not recent_loss(SYMBOL, LOSS_LOOKBACK_BARS):
            # Kupno – faktycznie przez API
            try:
                order = client.order_market_buy(symbol=SYMBOL, quantity=BUY_QUANTITY)
                buy_price = float(order['fills'][0]['price'])
                buy_time = datetime.now()
                trade_id = insert_trade(SYMBOL, buy_price, buy_time)
                position.active = True
                position.db_id = trade_id
                position.entry_price = buy_price
                position.tp_tracking = False
                position.red_count = 0
                print(f"{datetime.now()} 🟢 KUPNO wykonane po {buy_price} USDT, zapis w bazie id={trade_id}")
            except BinanceAPIException as e:
                print(f"{datetime.now()} ❌ Błąd przy próbie kupna: {e}")
        else:
            print(f"{datetime.now()} ⚪ Warunki kupna nie spełnione")

    # Zarządzanie pozycją (TP/SL)
    if position.active:
        sl_price = position.entry_price * (1 - STOP_LOSS_PERC / 100)
        tp_price = position.entry_price * (1 + TAKE_PROFIT_PERC / 100)

        # STOP LOSS
        if current_price <= sl_price:
            try:
                order = client.order_market_sell(symbol=SYMBOL, quantity=BUY_QUANTITY)
                sell_price = float(order['fills'][0]['price'])
                sell_time = datetime.now()
                profit_perc = (sell_price - position.entry_price) / position.entry_price * 100
                update_trade(position.db_id, sell_price, sell_time, profit_perc)
                print(f"{datetime.now()} 🔴 STOP LOSS – sprzedano po {sell_price} USDT, zysk/strata: {profit_perc:.2f}%")
            except BinanceAPIException as e:
                print(f"{datetime.now()} ❌ Błąd przy sprzedaży STOP LOSS: {e}")
            finally:
                position.active = False
                position.db_id = None
                position.tp_tracking = False
                position.red_count = 0
            return

        # TAKE PROFIT – śledzony
        if not position.tp_tracking and current_price >= tp_price:
            position.tp_tracking = True
            position.red_count = 0
            print(f"{datetime.now()} 🟡 TAKE PROFIT aktywowany")

        if position.tp_tracking:
            last_candle = df.iloc[-1]
            if last_candle['close'] < last_candle['open']:
                position.red_count += 1
            else:
                position.red_count = 0

            if position.red_count >= RED_CANDLES_TO_SELL:
                try:
                    order = client.order_market_sell(symbol=SYMBOL, quantity=BUY_QUANTITY)
                    sell_price = float(order['fills'][0]['price'])
                    sell_time = datetime.now()
                    profit_perc = (sell_price - position.entry_price) / position.entry_price * 100
                    update_trade(position.db_id, sell_price, sell_time, profit_perc)
                    print(f"{datetime.now()} 🟢 TAKE PROFIT – sprzedaż po {sell_price} USDT, zysk: {profit_perc:.2f}%")
                except BinanceAPIException as e:
                    print(f"{datetime.now()} ❌ Błąd przy sprzedaży TP: {e}")
                finally:
                    position.active = False
                    position.db_id = None
                    position.tp_tracking = False
                    position.red_count = 0

# =========================
# URUCHOMIENIE
# =========================
if __name__ == "__main__":
    print(f"{datetime.now()} 🚀 Uruchamiam strategię BNB/USDT")
    run_strategy()
    print(f"{datetime.now()} 🏁 Zakończono działanie strategii")
