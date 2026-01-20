"""
Szybki test nowej strategii DOGE Momentum.
"""

import json
import pandas as pd
from datetime import datetime
from database_manager import DatabaseManager
from strategies import DOGEMomentumStrategy
from sqlalchemy import text

# Wczytaj konfigurację
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

db = DatabaseManager(config['mysql'])
engine = db.get_engine()

# Parametry strategii
params = {
    'red_candles_min': 2,
    'red_candles_max': 4,
    'price_below_ma20_pct': 1.0,
    'volume_increase_pct': 20.0,
    'stop_loss_pct': 1.5,
    'take_profit_pct': 4.0,
    'trailing_activation_pct': 2.0,
    'trailing_stop_pct': 1.0
}

strategy = DOGEMomentumStrategy('DOGEUSDT', params, 'DOGE_Test')

print("="*80)
print("TEST STRATEGII DOGE MOMENTUM")
print("="*80)

# Pobierz dane
query = text("""
    SELECT open_time, open, high, low, close, volume,
           ma10, ma20, ma50
    FROM dogeusdt_1h 
    WHERE open_time >= '2025-01-01' AND open_time <= '2025-12-31' 
    ORDER BY open_time ASC
    LIMIT 500
""")

with engine.connect() as conn:
    result = conn.execute(query)
    rows = result.fetchall()
    columns = result.keys()
    df = pd.DataFrame(rows, columns=columns)

print(f"\nZaladowano {len(df)} swiec")

# Testuj strategię
signals_found = 0

for i in range(50, len(df)):
    window_df = df.iloc[:i+1].copy()
    
    if strategy.check_buy_signal(window_df):
        signals_found += 1
        open_time = window_df['open_time'].iloc[-1]
        price = window_df['close'].iloc[-1]
        
        print(f"\nSYGNAL KUPNA #{signals_found}:")
        print(f"  Data: {open_time}")
        print(f"  Cena: {price:.6f}")
        print(f"  TP: {strategy.get_take_profit(price):.6f} (+{strategy.take_profit_pct}%)")
        print(f"  SL: {strategy.get_stop_loss(price):.6f} (-{strategy.stop_loss_pct}%)")

print(f"\n{'='*80}")
print(f"PODSUMOWANIE: Znaleziono {signals_found} sygnalow kupna w {len(df)-50} sprawdzonych swiecach")
print(f"{'='*80}")
