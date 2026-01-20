"""
Test strategii DOGE na rzeczywistych danych z bazy.
Sprawdza dlaczego nie ma sygnałów kupna.
"""

import json
import pandas as pd
from datetime import datetime
from database_manager import DatabaseManager
from strategies import DOGEPineScriptStrategy

# Wczytaj konfigurację
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# Inicjalizacja
db = DatabaseManager(config['mysql'])

# Parametry strategii (domyślne z PineScript)
params = {
    'candle_count': 6,
    'price_below_ma20_pct': 2.0,
    'min_red_body_pct': 2.0,
    'profit_trigger_pct': 2.0,
    'stop_loss_multiplier': 1.0,
    'red_candle_count_trigger': 2,
    'red_candle_above_ma20_pct': 1.0,
    'require_ma_trend': False  # Wyłączone
}

# Utwórz strategię
strategy = DOGEPineScriptStrategy('DOGEUSDT', params, 'DOGE_Test')

print("="*80)
print("TEST STRATEGII DOGE NA RZECZYWISTYCH DANYCH")
print("="*80)
print(f"\nParametry strategii:")
for key, value in params.items():
    print(f"  {key}: {value}")

# Pobierz dane z bazy
print(f"\nPobieranie danych z bazy...")

# Użyj DatabaseManager
from sqlalchemy import text
engine = db.get_engine()

query = text("""
    SELECT open_time, open, high, low, close, volume 
    FROM dogeusdt_1h 
    WHERE open_time >= '2025-01-01' AND open_time <= '2025-12-31' 
    ORDER BY open_time ASC 
    LIMIT 300
""")

with engine.connect() as conn:
    result = conn.execute(query)
    rows = result.fetchall()
    columns = result.keys()
    df = pd.DataFrame(rows, columns=columns)

print(f"Załadowano {len(df)} świec")
print(f"Okres: {df['open_time'].iloc[0]} -> {df['open_time'].iloc[-1]}")

# Sprawdź warunki dla każdej świecy
print(f"\n{'='*80}")
print("ANALIZA WARUNKÓW STRATEGII")
print(f"{'='*80}\n")

signals_found = 0

for i in range(250, min(300, len(df))):  # Sprawdź ostatnie 50 świec
    # Pobierz okno danych
    window_df = df.iloc[:i+1].copy()
    
    if len(window_df) < 200:
        continue
    
    # Sprawdź każdy warunek osobno
    open_time = window_df['open_time'].iloc[-1]
    
    # 1. Falling sequence
    falling = strategy._check_falling_sequence(window_df)
    
    # 2. Strong red
    strong_red = strategy._check_strong_red_exists(window_df)
    
    # 3. MA trend (opcjonalny)
    ma_trend = strategy._check_ma_trend_down(window_df) if strategy.require_ma_trend else True
    
    # 4. Price below MA20
    ma20 = strategy._calculate_ma(window_df, 20).iloc[-1]
    current_close = window_df['close'].iloc[-1]
    price_threshold = ma20 * (1 - strategy.price_below_ma20_pct / 100)
    price_ok = current_close < price_threshold
    
    # 5. Valid stop loss
    stop_loss_pct = strategy._calculate_dynamic_stop_loss_pct(window_df)
    sl_ok = stop_loss_pct is not None
    
    # Sygnał kupna?
    buy_signal = strategy.check_buy_signal(window_df)
    
    # Wyświetl tylko jeśli przynajmniej 3 warunki spełnione
    conditions_met = sum([falling, strong_red, ma_trend, price_ok, sl_ok])
    
    if conditions_met >= 3 or buy_signal:
        print(f"\n{open_time}:")
        print(f"  1. Falling sequence: {'OK' if falling else 'FAIL'}")
        print(f"  2. Strong red exists: {'OK' if strong_red else 'FAIL'}")
        print(f"  3. MA trend down: {'OK' if ma_trend else 'FAIL (opcjonalny)'}")
        print(f"  4. Price < MA20: {'OK' if price_ok else 'FAIL'} (close={current_close:.6f}, threshold={price_threshold:.6f})")
        print(f"  5. Valid SL: {'OK' if sl_ok else 'FAIL'} (SL={stop_loss_pct*100 if sl_ok else 'N/A'}%)")
        print(f"  -> BUY SIGNAL: {'YES!!!' if buy_signal else 'NO'}")
        
        if buy_signal:
            signals_found += 1

print(f"\n{'='*80}")
print(f"PODSUMOWANIE: Znaleziono {signals_found} sygnałów kupna w {min(50, len(df)-250)} sprawdzonych świecach")
print(f"{'='*80}")

if signals_found == 0:
    print("\nBRAK SYGNAŁÓW - sprawdzam szczegółowo pierwsze 10 świec:")
    
    for i in range(250, min(260, len(df))):
        window_df = df.iloc[:i+1].copy()
        
        if len(window_df) < 200:
            continue
        
        open_time = window_df['open_time'].iloc[-1]
        
        print(f"\n{open_time}:")
        
        # Sprawdź falling sequence szczegółowo
        print(f"  Falling sequence check:")
        for j in range(strategy.candle_count - 1):
            mid_j = strategy._body_mid(window_df, j)
            mid_j_plus_1 = strategy._body_mid(window_df, j + 1)
            status = "OK" if mid_j < mid_j_plus_1 else "FAIL"
            print(f"    bodyMid({j})={mid_j:.6f} < bodyMid({j+1})={mid_j_plus_1:.6f}? {status}")
        
        # Sprawdź strong red szczegółowo
        print(f"  Strong red check:")
        for j in range(strategy.candle_count):
            idx = -(j + 1)
            open_price = window_df['open'].iloc[idx]
            close_price = window_df['close'].iloc[idx]
            
            if close_price < open_price:
                drop_pct = (open_price - close_price) / open_price * 100
                is_strong = drop_pct >= strategy.min_red_body_pct
                print(f"    Swica {j}: drop={drop_pct:.2f}% {'OK' if is_strong else 'FAIL (too small)'}")
