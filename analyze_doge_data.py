"""
Analiza danych DOGE - charakterystyka świec, volatility, trendy.
Cel: Zrozumieć zachowanie DOGE i stworzyć optymalną strategię.
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime
from database_manager import DatabaseManager
from sqlalchemy import text

# Wczytaj konfigurację
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

db = DatabaseManager(config['mysql'])
engine = db.get_engine()

print("="*100)
print("ANALIZA DANYCH DOGE - 2025")
print("="*100)

# Pobierz wszystkie dane z 2025
query = text("""
    SELECT open_time, open, high, low, close, volume,
           ma10, ma20, ma50, ma100, ma200
    FROM dogeusdt_1h 
    WHERE open_time >= '2025-01-01' AND open_time <= '2025-12-31' 
    ORDER BY open_time ASC
""")

with engine.connect() as conn:
    result = conn.execute(query)
    rows = result.fetchall()
    columns = result.keys()
    df = pd.DataFrame(rows, columns=columns)

print(f"\nZaladowano {len(df)} swiec z 2025 roku")
print(f"Okres: {df['open_time'].iloc[0]} -> {df['open_time'].iloc[-1]}")

# === 1. PODSTAWOWE STATYSTYKI ===
print(f"\n{'='*100}")
print("1. PODSTAWOWE STATYSTYKI CENY")
print(f"{'='*100}")

print(f"Cena min: {df['low'].min():.6f}")
print(f"Cena max: {df['high'].max():.6f}")
print(f"Cena srednia: {df['close'].mean():.6f}")
print(f"Zmiana ceny (rok): {((df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0] * 100):.2f}%")

# === 2. ANALIZA ŚWIEC ===
print(f"\n{'='*100}")
print("2. ANALIZA SWIEC")
print(f"{'='*100}")

# Oblicz charakterystyki świec
df['body'] = abs(df['close'] - df['open'])
df['body_pct'] = (df['body'] / df['open']) * 100
df['is_red'] = df['close'] < df['open']
df['is_green'] = df['close'] > df['open']
df['upper_wick'] = df['high'] - df[['open', 'close']].max(axis=1)
df['lower_wick'] = df[['open', 'close']].min(axis=1) - df['low']
df['total_range'] = df['high'] - df['low']
df['range_pct'] = (df['total_range'] / df['open']) * 100

print(f"\nSredni rozmiar korpusu: {df['body_pct'].mean():.3f}%")
print(f"Mediana rozmiaru korpusu: {df['body_pct'].median():.3f}%")
print(f"Max rozmiar korpusu: {df['body_pct'].max():.3f}%")
print(f"\nRozkład rozmiarow korpusu:")
print(f"  < 0.3%: {(df['body_pct'] < 0.3).sum()} swiec ({(df['body_pct'] < 0.3).sum() / len(df) * 100:.1f}%)")
print(f"  0.3-0.5%: {((df['body_pct'] >= 0.3) & (df['body_pct'] < 0.5)).sum()} swiec ({((df['body_pct'] >= 0.3) & (df['body_pct'] < 0.5)).sum() / len(df) * 100:.1f}%)")
print(f"  0.5-1.0%: {((df['body_pct'] >= 0.5) & (df['body_pct'] < 1.0)).sum()} swiec ({((df['body_pct'] >= 0.5) & (df['body_pct'] < 1.0)).sum() / len(df) * 100:.1f}%)")
print(f"  1.0-2.0%: {((df['body_pct'] >= 1.0) & (df['body_pct'] < 2.0)).sum()} swiec ({((df['body_pct'] >= 1.0) & (df['body_pct'] < 2.0)).sum() / len(df) * 100:.1f}%)")
print(f"  > 2.0%: {(df['body_pct'] >= 2.0).sum()} swiec ({(df['body_pct'] >= 2.0).sum() / len(df) * 100:.1f}%)")

print(f"\nCzerwone vs Zielone:")
print(f"  Czerwone: {df['is_red'].sum()} ({df['is_red'].sum() / len(df) * 100:.1f}%)")
print(f"  Zielone: {df['is_green'].sum()} ({df['is_green'].sum() / len(df) * 100:.1f}%)")

# === 3. VOLATILITY ===
print(f"\n{'='*100}")
print("3. ANALIZA VOLATILITY")
print(f"{'='*100}")

df['returns'] = df['close'].pct_change() * 100
df['volatility_20'] = df['returns'].rolling(20).std()

print(f"\nSrednia zmiana ceny (1h): {df['returns'].mean():.3f}%")
print(f"Std zmiana ceny (1h): {df['returns'].std():.3f}%")
print(f"Max wzrost (1h): {df['returns'].max():.3f}%")
print(f"Max spadek (1h): {df['returns'].min():.3f}%")

print(f"\nDuze ruchy (>2%):")
print(f"  Wzrosty >2%: {(df['returns'] > 2).sum()} ({(df['returns'] > 2).sum() / len(df) * 100:.1f}%)")
print(f"  Spadki >2%: {(df['returns'] < -2).sum()} ({(df['returns'] < -2).sum() / len(df) * 100:.1f}%)")

# === 4. TRENDY I ŚREDNIE KROCZĄCE ===
print(f"\n{'='*100}")
print("4. ANALIZA TRENDOW (MA)")
print(f"{'='*100}")

df['above_ma20'] = df['close'] > df['ma20']
df['above_ma50'] = df['close'] > df['ma50']
df['ma_trend_up'] = (df['ma10'] > df['ma20']) & (df['ma20'] > df['ma50'])
df['ma_trend_down'] = (df['ma10'] < df['ma20']) & (df['ma20'] < df['ma50'])

print(f"\nCena wzgledem MA:")
print(f"  Powyżej MA20: {df['above_ma20'].sum()} swiec ({df['above_ma20'].sum() / len(df) * 100:.1f}%)")
print(f"  Ponizej MA20: {(~df['above_ma20']).sum()} swiec ({(~df['above_ma20']).sum() / len(df) * 100:.1f}%)")

print(f"\nTrendy MA:")
print(f"  Trend wzrostowy (MA10>MA20>MA50): {df['ma_trend_up'].sum()} swiec ({df['ma_trend_up'].sum() / len(df) * 100:.1f}%)")
print(f"  Trend spadkowy (MA10<MA20<MA50): {df['ma_trend_down'].sum()} swiec ({df['ma_trend_down'].sum() / len(df) * 100:.1f}%)")

# === 5. SEKWENCJE ŚWIEC ===
print(f"\n{'='*100}")
print("5. ANALIZA SEKWENCJI")
print(f"{'='*100}")

# Policz sekwencje czerwonych/zielonych
red_streaks = []
green_streaks = []
current_streak = 0
current_color = None

for is_red in df['is_red']:
    if is_red:
        if current_color == 'red':
            current_streak += 1
        else:
            if current_color == 'green' and current_streak > 0:
                green_streaks.append(current_streak)
            current_streak = 1
            current_color = 'red'
    else:
        if current_color == 'green':
            current_streak += 1
        else:
            if current_color == 'red' and current_streak > 0:
                red_streaks.append(current_streak)
            current_streak = 1
            current_color = 'green'

print(f"\nNajdluzsza seria czerwonych: {max(red_streaks) if red_streaks else 0} swiec")
print(f"Najdluzsza seria zielonych: {max(green_streaks) if green_streaks else 0} swiec")
print(f"Srednia seria czerwonych: {np.mean(red_streaks) if red_streaks else 0:.1f} swiec")
print(f"Srednia seria zielonych: {np.mean(green_streaks) if green_streaks else 0:.1f} swiec")

# === 6. NAJLEPSZE MOMENTY DO KUPNA ===
print(f"\n{'='*100}")
print("6. ANALIZA NAJLEPSZYCH MOMENTOW DO KUPNA")
print(f"{'='*100}")

# Znajdź największe spadki po których nastąpił wzrost
df['future_return_24h'] = df['close'].shift(-24).pct_change(24) * 100
df['future_max_24h'] = df['high'].rolling(24).max().shift(-24)
df['future_gain_24h'] = ((df['future_max_24h'] - df['close']) / df['close'] * 100)

# Najlepsze momenty = duży spadek + duży przyszły wzrost
best_entries = df.nlargest(20, 'future_gain_24h')[['open_time', 'close', 'returns', 'future_gain_24h', 'body_pct', 'above_ma20']]

print(f"\nTop 20 najlepszych momentow do kupna (najwiekszy potencjal wzrostu w 24h):")
print(best_entries.to_string(index=False))

# === 7. WNIOSKI ===
print(f"\n{'='*100}")
print("7. WNIOSKI I REKOMENDACJE")
print(f"{'='*100}")

print(f"\n1. DOGE ma MALE swieceki - sredni korpus {df['body_pct'].mean():.3f}%")
print(f"2. Volatility jest NISKA - std {df['returns'].std():.3f}%")
print(f"3. Duze ruchy (>2%) sa RZADKIE - tylko {(abs(df['returns']) > 2).sum() / len(df) * 100:.1f}% swiec")
print(f"4. Trend jest MIESZANY - {df['ma_trend_up'].sum() / len(df) * 100:.1f}% wzrost, {df['ma_trend_down'].sum() / len(df) * 100:.1f}% spadek")

print(f"\nREKOMENDACJE DLA STRATEGII:")
print(f"- Nie wymagaj duzych swiec (>2%) - to eliminuje 95%+ okazji")
print(f"- Szukaj malych, konsekwentnych ruchow (0.3-1%)")
print(f"- Wykorzystaj MA crossover zamiast trendow MA")
print(f"- Skup sie na momentum i volume")
print(f"- Krotkie TP (2-5%) i SL (1-3%)")

# Zapisz wyniki do pliku
df.to_csv('reports/doge_analysis_2025.csv', index=False)
print(f"\n\nDane zapisane do: reports/doge_analysis_2025.csv")
