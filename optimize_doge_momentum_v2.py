"""
Optymalizacja parametrów strategii DOGE Momentum v2.0
Cel: Zwiększyć win rate z 28.6% do ~35% aby osiągnąć rentowność.
"""

import json
from datetime import datetime
from itertools import product
from database_manager import DatabaseManager
from backtest_engine import BacktestEngine
from strategies import DOGEMomentumStrategy

# Wczytaj konfigurację
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# Inicjalizacja
db = DatabaseManager(config['mysql'])

# Zakres dat
start_date = datetime(2025, 1, 1)
end_date = datetime(2025, 12, 31, 23, 59, 59)
initial_capital = 100.0
tables = ['dogeusdt_1h']

print("\n" + "="*100)
print("🔧 OPTYMALIZACJA DOGE MOMENTUM v2.0")
print("="*100)
print(f"📅 Okres: {start_date.date()} → {end_date.date()}")
print(f"💰 Kapitał: {initial_capital} USDT")
print(f"🎯 Cel: Win rate > 35% (obecnie 28.6%)")
print("="*100 + "\n")

# Parametry do optymalizacji
# Skupimy się na kluczowych parametrach które wpływają na filtrowanie
param_grid = {
    'red_candles_min': [2],  # Stały
    'red_candles_max': [2, 3],  # Testuj 2-2 i 2-3
    'price_below_ma20_pct': [0.5, 0.7, 1.0],  # Jak daleko poniżej MA20
    'volume_increase_pct': [25.0, 30.0, 35.0],  # Próg volume spike
    'rsi_oversold': [30, 35, 40],  # Próg RSI
    'stop_loss_pct': [1.2],  # Stały (dopasowany do volatility)
    'take_profit_pct': [3.0],  # Stały
    'trailing_activation_pct': [1.5],  # Stały
    'trailing_stop_pct': [0.8]  # Stały
}

# Generuj kombinacje
keys = list(param_grid.keys())
values = list(param_grid.values())
combinations = list(product(*values))

total_combinations = len(combinations)
print(f"🔍 Testowanie {total_combinations} kombinacji parametrów...\n")

results = []
best_result = None
best_score = -999999

for idx, combo in enumerate(combinations, 1):
    params = dict(zip(keys, combo))
    
    # Progress
    if idx % 3 == 0 or idx == 1:
        print(f"⏳ Progress: {idx}/{total_combinations} ({idx/total_combinations*100:.1f}%)")
    
    try:
        engine = BacktestEngine(db, initial_capital=initial_capital)
        
        report = engine.run_backtest_optimized(
            strategy_class=DOGEMomentumStrategy,
            strategy_params=params,
            start_date=start_date,
            end_date=end_date,
            tables=tables,
            interval_hours=1
        )
        
        # Oblicz score (priorytet: win rate, potem zwrot)
        # Score = win_rate * 100 + total_return_perc
        # To preferuje wysokie win rate nawet jeśli zwrot jest niższy
        win_rate = report.get('win_rate', 0)
        total_return = report.get('total_return_perc', 0)
        total_trades = report.get('total_trades', 0)
        
        # Score tylko jeśli mamy przynajmniej 10 transakcji
        if total_trades >= 10:
            score = win_rate * 2 + total_return  # Win rate ma 2x wagę
            
            result = {
                'params': params,
                'total_return_perc': total_return,
                'total_trades': total_trades,
                'winning_trades': report.get('winning_trades', 0),
                'win_rate': win_rate,
                'avg_profit': report.get('avg_profit', 0),
                'avg_loss': report.get('avg_loss', 0),
                'final_capital': report.get('final_capital', 0),
                'score': score
            }
            
            results.append(result)
            
            # Wyświetl jeśli dobry wynik
            if total_trades > 0 and (win_rate >= 30 or total_return > 0):
                print(f"   ✅ Trades: {total_trades} | Win: {win_rate:.1f}% | Return: {total_return:+.2f}% | Score: {score:.1f}")
                print(f"      RSI<{params['rsi_oversold']}, Vol>{params['volume_increase_pct']}%, "
                      f"MA<{params['price_below_ma20_pct']}%, Candles:{params['red_candles_min']}-{params['red_candles_max']}")
            
            # Aktualizuj najlepszy
            if score > best_score:
                best_score = score
                best_result = result
    
    except Exception as e:
        print(f"   ❌ Błąd: {e}")
        continue

print(f"\n{'='*100}")
print("✅ OPTYMALIZACJA ZAKOŃCZONA")
print(f"{'='*100}\n")

# Sortuj wyniki po score
results.sort(key=lambda x: x['score'], reverse=True)

if results:
    print("🏆 TOP 10 NAJLEPSZYCH KONFIGURACJI:\n")
    print(f"{'#':<4} {'Score':<8} {'Win%':<8} {'Return%':<10} {'Trades':<8} {'Parametry'}")
    print("-" * 100)
    
    for idx, result in enumerate(results[:10], 1):
        params = result['params']
        param_str = (f"RSI<{params['rsi_oversold']}, Vol>{params['volume_increase_pct']}%, "
                    f"MA<{params['price_below_ma20_pct']}%, Red:{params['red_candles_min']}-{params['red_candles_max']}")
        
        print(f"{idx:<4} {result['score']:>6.1f}  {result['win_rate']:>6.1f}%  "
              f"{result['total_return_perc']:>+8.2f}%  {result['total_trades']:>7}  {param_str}")
    
    # Najlepsza konfiguracja
    best = results[0]
    
    print(f"\n{'='*100}")
    print("🥇 NAJLEPSZA KONFIGURACJA:")
    print(f"{'='*100}")
    print(f"📊 Score: {best['score']:.1f}")
    print(f"📈 Win Rate: {best['win_rate']:.1f}% (cel: >35%)")
    print(f"💰 Zwrot: {best['total_return_perc']:+.2f}%")
    print(f"💵 Kapitał końcowy: {best['final_capital']:.2f} USDT")
    print(f"🔢 Transakcje: {best['total_trades']} (wygrane: {best['winning_trades']})")
    print(f"📊 Średni zysk: {best['avg_profit']:.2f}%")
    print(f"📉 Średnia strata: {best['avg_loss']:.2f}%")
    print(f"\n⚙️  PARAMETRY:")
    for key, value in best['params'].items():
        print(f"   • {key}: {value}")
    
    # Zapisz najlepszą konfigurację
    best_config = {
        'symbol': 'DOGEUSDT',
        'table': 'dogeusdt_1h',
        'strategy': 'DOGEMomentumStrategy',
        'strategy_id': 'DOGE_Momentum_v2_Optimized',
        'buy_quantity': 100,
        'enabled': True,
        'params': best['params'],
        'backtest_results': {
            'win_rate': best['win_rate'],
            'total_return_perc': best['total_return_perc'],
            'total_trades': best['total_trades'],
            'score': best['score']
        }
    }
    
    with open('reports/doge_momentum_v2_best_config.json', 'w', encoding='utf-8') as f:
        json.dump(best_config, f, indent=4, ensure_ascii=False)
    
    print(f"\n💾 Najlepsza konfiguracja zapisana do: reports/doge_momentum_v2_best_config.json")
    
    # Zapisz wszystkie wyniki
    with open('reports/doge_momentum_v2_optimization_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Wszystkie wyniki zapisane do: reports/doge_momentum_v2_optimization_results.json")
    
    # Porównanie z bazową wersją
    print(f"\n{'='*100}")
    print("📊 PORÓWNANIE Z WERSJĄ BAZOWĄ:")
    print(f"{'='*100}")
    print(f"Bazowa v2.0:  Win Rate: 28.6% | Return: -3.89% | Trades: 35")
    print(f"Optymalna:    Win Rate: {best['win_rate']:.1f}% | Return: {best['total_return_perc']:+.2f}% | Trades: {best['total_trades']}")
    
    improvement = best['win_rate'] - 28.6
    print(f"\n{'🎉 POPRAWA' if improvement > 0 else '⚠️  ZMIANA'}: Win Rate {improvement:+.1f}%")

else:
    print("❌ BRAK WYNIKÓW")
    print("Wszystkie kombinacje wygenerowały < 10 transakcji.")

print(f"\n{'='*100}\n")
