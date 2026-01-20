"""
Optymalizacja parametrów strategii DOGE PineScript.

Testuje różne kombinacje parametrów i znajduje najlepsze ustawienia
pod względem zwrotu z inwestycji.
"""

import json
from datetime import datetime
from itertools import product
from database_manager import DatabaseManager
from backtest_engine import BacktestEngine
from strategies import DOGEPineScriptStrategy



def optimize_doge_strategy():
    """
    Optymalizuje parametry strategii DOGE.
    Testuje różne kombinacje i zwraca najlepsze wyniki.
    """
    
    # Wczytaj konfigurację
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Inicjalizacja
    db = DatabaseManager(config['mysql'])
    
    # Zakres dat do testowania
    start_date = datetime(2025, 1, 1)
    end_date = datetime(2025, 12, 31, 23, 59, 59)
    
    # Kapitał początkowy
    initial_capital = 100.0
    
    # Symbol do testowania
    tables = ['dogeusdt_1h']
    
    print("\n" + "="*100)
    print("🔧 OPTYMALIZACJA PARAMETRÓW STRATEGII DOGE PINESCRIPT")
    print("="*100)
    print(f"📅 Okres testowania: {start_date.date()} → {end_date.date()}")
    print(f"💰 Kapitał początkowy: {initial_capital} USDT")
    print(f"📊 Symbol: DOGEUSDT")
    print("="*100 + "\n")
    
    # Parametry do optymalizacji - DOSTOSOWANE DO DOGE (małe świece!)
    param_grid = {
        'candle_count': [4, 5, 6],  # Liczba opadających świeczek
        'price_below_ma20_pct': [0.5, 1.0, 1.5],  # Procent poniżej MA20
        'min_red_body_pct': [0.3, 0.5, 0.7, 1.0],  # ZMNIEJSZONE! DOGE ma małe świece
        'profit_trigger_pct': [2.0],  # Stały
        'stop_loss_multiplier': [1.0],  # Stały
        'red_candle_count_trigger': [2],  # Stały
        'red_candle_above_ma20_pct': [1.0],  # Stały
        'require_ma_trend': [False]  # Wyłącz wymaganie trendu MA (zbyt restrykcyjne)
    }
    
    # Generuj wszystkie kombinacje
    keys = list(param_grid.keys())
    values = list(param_grid.values())
    combinations = list(product(*values))
    
    total_combinations = len(combinations)
    print(f"🔍 Testowanie {total_combinations} kombinacji parametrów...\n")
    
    results = []
    
    for idx, combo in enumerate(combinations, 1):
        # Utwórz słownik parametrów
        params = dict(zip(keys, combo))
        
        # Wyświetl progress
        if idx % 5 == 0 or idx == 1:
            print(f"⏳ Progress: {idx}/{total_combinations} ({idx/total_combinations*100:.1f}%)")
        
        # Uruchom backtest
        try:
            engine = BacktestEngine(db, initial_capital=initial_capital)
            
            report = engine.run_backtest_optimized(
                strategy_class=DOGEPineScriptStrategy,
                strategy_params=params,
                start_date=start_date,
                end_date=end_date,
                tables=tables,
                interval_hours=1
            )
            
            # Zapisz wyniki
            result = {
                'params': params,
                'total_return_perc': report['total_return_perc'],
                'total_return_usdt': report['total_return_usdt'],
                'total_trades': report['total_trades'],
                'winning_trades': report['winning_trades'],
                'losing_trades': report['losing_trades'],
                'win_rate': report['win_rate'],
                'avg_profit': report['avg_profit'],
                'avg_loss': report['avg_loss'],
                'final_capital': report['final_capital']
            }
            
            results.append(result)
            
            # Wyświetl jeśli znaleziono transakcje
            if report['total_trades'] > 0:
                print(f"   ✅ Znaleziono {report['total_trades']} transakcji | "
                      f"Zwrot: {report['total_return_perc']:+.2f}% | "
                      f"Win rate: {report['win_rate']:.1f}%")
                print(f"      Parametry: candle={params['candle_count']}, "
                      f"below_ma20={params['price_below_ma20_pct']}, "
                      f"min_red={params['min_red_body_pct']}")
        
        except Exception as e:
            print(f"   ❌ Błąd dla kombinacji {idx}: {e}")
            continue
    
    print(f"\n{'='*100}")
    print("✅ OPTYMALIZACJA ZAKOŃCZONA")
    print(f"{'='*100}\n")
    
    # Sortuj wyniki
    # 1. Po liczbie transakcji (musi być > 0)
    # 2. Po zwrocie z inwestycji
    results_with_trades = [r for r in results if r['total_trades'] > 0]
    results_no_trades = [r for r in results if r['total_trades'] == 0]
    
    if results_with_trades:
        # Sortuj po zwrocie
        results_with_trades.sort(key=lambda x: x['total_return_perc'], reverse=True)
        
        print("🏆 TOP 10 NAJLEPSZYCH KONFIGURACJI:\n")
        print(f"{'#':<4} {'Zwrot':<10} {'Transakcje':<12} {'Win Rate':<10} {'Śr. Zysk':<10} {'Śr. Strata':<12} {'Parametry'}")
        print("-" * 100)
        
        for idx, result in enumerate(results_with_trades[:10], 1):
            params = result['params']
            param_str = f"candle={params['candle_count']}, below_ma20={params['price_below_ma20_pct']}, min_red={params['min_red_body_pct']}"
            
            print(f"{idx:<4} {result['total_return_perc']:>+8.2f}% "
                  f"{result['total_trades']:>11} "
                  f"{result['win_rate']:>9.1f}% "
                  f"{result['avg_profit']:>9.2f}% "
                  f"{result['avg_loss']:>11.2f}% "
                  f"{param_str}")
        
        # Najlepsza konfiguracja
        best = results_with_trades[0]
        
        print(f"\n{'='*100}")
        print("🥇 NAJLEPSZA KONFIGURACJA:")
        print(f"{'='*100}")
        print(f"📊 Zwrot: {best['total_return_perc']:+.2f}% ({best['total_return_usdt']:+.2f} USDT)")
        print(f"📈 Kapitał końcowy: {best['final_capital']:.2f} USDT")
        print(f"🔢 Liczba transakcji: {best['total_trades']}")
        print(f"✅ Wygrane: {best['winning_trades']} ({best['win_rate']:.1f}%)")
        print(f"❌ Przegrane: {best['losing_trades']}")
        print(f"📊 Średni zysk: {best['avg_profit']:.2f}%")
        print(f"📉 Średnia strata: {best['avg_loss']:.2f}%")
        print(f"\n⚙️  PARAMETRY:")
        for key, value in best['params'].items():
            print(f"   • {key}: {value}")
        
        # Zapisz najlepszą konfigurację do pliku
        best_config = {
            'symbol': 'DOGEUSDT',
            'table': 'dogeusdt_1h',
            'strategy': 'DOGEPineScriptStrategy',
            'strategy_id': 'DOGE_Optimized',
            'buy_quantity': 100,
            'enabled': True,
            'params': best['params']
        }
        
        with open('reports/doge_best_config.json', 'w', encoding='utf-8') as f:
            json.dump(best_config, f, indent=4, ensure_ascii=False)
        
        print(f"\n💾 Najlepsza konfiguracja zapisana do: reports/doge_best_config.json")
        
        # Zapisz wszystkie wyniki
        with open('reports/doge_optimization_results.json', 'w', encoding='utf-8') as f:
            json.dump(results_with_trades, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Wszystkie wyniki zapisane do: reports/doge_optimization_results.json")
        
    else:
        print("❌ BRAK TRANSAKCJI")
        print("Żadna z testowanych kombinacji nie wygenerowała sygnałów kupna.")
        print("\nMożliwe przyczyny:")
        print("1. Warunki strategii są zbyt restrykcyjne")
        print("2. Trend DOGE w 2025 nie pasuje do strategii spadkowej")
        print("3. Wymaganie trendu MA (MA20 < MA50 < MA100 < MA200) jest zbyt rygorystyczne")
        print("\nRekomendacje:")
        print("- Rozszerz zakres parametrów (mniejsze wartości)")
        print("- Usuń lub złagodź wymaganie trendu MA")
        print("- Przetestuj na innych okresach czasu")
    
    print(f"\n{'='*100}\n")
    
    return results_with_trades if results_with_trades else results


if __name__ == "__main__":
    optimize_doge_strategy()
