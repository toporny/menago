"""
Pełny backtest strategii DOGE Momentum na rok 2025.
"""

import json
from datetime import datetime
from database_manager import DatabaseManager
from backtest_engine import BacktestEngine
from strategies import DOGEMomentumStrategy

# Wczytaj konfigurację
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# Inicjalizacja
db = DatabaseManager(config['mysql'])
engine = BacktestEngine(db, initial_capital=100.0)

# Parametry strategii
strategy_params = {
    'red_candles_min': 2,
    'red_candles_max': 4,
    'price_below_ma20_pct': 1.0,
    'volume_increase_pct': 20.0,
    'stop_loss_pct': 1.5,
    'take_profit_pct': 4.0,
    'trailing_activation_pct': 2.0,
    'trailing_stop_pct': 1.0
}

# Uruchom backtest
print("\nUruchamianie backtestingu...")
report = engine.run_backtest_optimized(
    strategy_class=DOGEMomentumStrategy,
    strategy_params=strategy_params,
    start_date=datetime(2025, 1, 1),
    end_date=datetime(2025, 12, 31, 23, 59, 59),
    tables=['dogeusdt_1h'],
    interval_hours=1
)

# Dodaj informacje o strategii
report['strategy_name'] = 'DOGE Momentum Reversal Strategy'
report['strategy_params'] = strategy_params
report['test_period'] = '2025-01-01 -> 2025-12-31'
report['interval_hours'] = 1

# Wyświetl raport
engine.print_report(report)

# Zapisz raport
import os
os.makedirs('reports', exist_ok=True)

report_file_json = 'reports/backtest_DOGE_Momentum_2025.json'
report_json = report.copy()
for trade in report_json.get('trades', []):
    trade['entry_time'] = str(trade['entry_time'])
    trade['exit_time'] = str(trade['exit_time'])

for point in report_json.get('equity_curve', []):
    point['time'] = str(point['time'])

with open(report_file_json, 'w', encoding='utf-8') as f:
    json.dump(report_json, f, indent=2, ensure_ascii=False)

print(f"\nRaport JSON zapisany do: {report_file_json}")

# Zapisz raport TXT
report_file_txt = 'reports/backtest_DOGE_Momentum_2025.txt'
engine.save_report_to_txt(report, report_file_txt)
