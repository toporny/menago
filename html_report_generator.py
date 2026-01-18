"""
Enhanced HTML Report Generator - Generuje interaktywne raporty HTML z wykresami świecowymi.

Tworzy responsywny raport HTML z rozwijalnymi wykresami dla każdej transakcji.
"""

from typing import Dict, List
from datetime import datetime, timedelta
import json


def get_candles_for_trade(db_manager, table: str, entry_time, exit_time, 
                          before_candles: int = 24, after_candles: int = 24) -> List[Dict]:
    """
    Pobiera świeczki dla danej transakcji (przed i po).
    
    Args:
        db_manager: Obiekt DatabaseManager
        table: Nazwa tabeli ze świecami
        entry_time: Czas wejścia w pozycję (datetime lub string)
        exit_time: Czas wyjścia z pozycji (datetime lub string)
        before_candles: Liczba świeczek przed wejściem
        after_candles: Liczba świeczek po wyjściu
    
    Returns:
        Lista słowników ze świeczkami
    """
    # Konwertuj stringi na datetime jeśli potrzeba
    if isinstance(entry_time, str):
        entry_time = datetime.strptime(entry_time[:19], '%Y-%m-%d %H:%M:%S')
    if isinstance(exit_time, str):
        exit_time = datetime.strptime(exit_time[:19], '%Y-%m-%d %H:%M:%S')
    
    # Oblicz zakres czasowy
    start_time = entry_time - timedelta(hours=before_candles)
    end_time = exit_time + timedelta(hours=after_candles)
    
    # Pobierz dane
    df = db_manager.load_all_data_in_range(table, start_time, end_time)
    
    if df.empty:
        return []
    
    # Konwertuj do listy słowników
    candles = []
    for _, row in df.iterrows():
        # Konwertuj czas do Unix timestamp (wymagane przez lightweight-charts)
        timestamp = int(row['open_time'].timestamp())
        
        candles.append({
            'time': timestamp,
            'open': float(row['open']),
            'high': float(row['high']),
            'low': float(row['low']),
            'close': float(row['close']),
            'volume': float(row['volume']) if 'volume' in row else 0
        })
    
    return candles


def generate_html_report_with_charts(report: Dict, filename: str, db_manager=None):
    """
    Generuje raport HTML z interaktywnymi wykresami świecowymi.
    
    Args:
        report: Słownik z raportem backtestingu
        filename: Nazwa pliku HTML do zapisu
        db_manager: Obiekt DatabaseManager (opcjonalny, dla wykresów)
    """
    
    # Oblicz dodatkowe statystyki
    profit_loss_perc = ((report['final_capital'] - report['initial_capital']) / report['initial_capital']) * 100
    total_return_color = "green" if profit_loss_perc >= 0 else "red"
    win_rate_color = "green" if report['win_rate'] >= 50 else "orange" if report['win_rate'] >= 30 else "red"
    
    # Przygotuj dane wykresów dla każdej transakcji
    trades_with_charts = []
    if db_manager:
        for trade in report['trades']:
            # Pobierz świeczki dla tej transakcji
            table = trade['symbol'].lower() + '_1h'
            candles = get_candles_for_trade(
                db_manager, 
                table,
                trade['entry_time'],
                trade['exit_time'],
                before_candles=24,
                after_candles=24
            )
            
            trades_with_charts.append({
                **trade,
                'candles': candles
            })
    else:
        trades_with_charts = report['trades']
    
    html_content = f"""<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Raport Backtestingu - {report.get('strategy_name', 'Strategia')}</title>
    <script src="https://cdn.jsdelivr.net/npm/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            color: #333;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }}
        
        .header .period {{
            font-size: 1.2em;
            opacity: 0.9;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            padding: 40px;
            background: #f8f9fa;
        }}
        
        .stat-card {{
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }}
        
        .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 12px rgba(0,0,0,0.15);
        }}
        
        .stat-card .label {{
            font-size: 0.9em;
            color: #666;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .stat-card .value {{
            font-size: 2em;
            font-weight: bold;
            color: #333;
        }}
        
        .stat-card.positive .value {{
            color: #10b981;
        }}
        
        .stat-card.negative .value {{
            color: #ef4444;
        }}
        
        .section {{
            padding: 40px;
        }}
        
        .section-title {{
            font-size: 1.8em;
            margin-bottom: 20px;
            color: #667eea;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }}
        
        .params-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }}
        
        .param-item {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 10px;
            border-left: 4px solid #667eea;
        }}
        
        .param-item .param-name {{
            font-size: 0.85em;
            color: #666;
            margin-bottom: 5px;
        }}
        
        .param-item .param-value {{
            font-size: 1.1em;
            font-weight: bold;
            color: #333;
        }}
        
        /* Tabela transakcji */
        .trades-container {{
            margin-top: 20px;
        }}
        
        .trade-row {{
            background: white;
            border-radius: 10px;
            margin-bottom: 10px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
        }}
        
        .trade-row:hover {{
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }}
        
        .trade-header {{
            display: grid;
            grid-template-columns: 50px 120px 180px 180px 120px 120px 120px 100px;
            gap: 10px;
            padding: 15px 20px;
            cursor: pointer;
            align-items: center;
            background: #f8f9fa;
            transition: background 0.2s ease;
        }}
        
        .trade-header:hover {{
            background: #e9ecef;
        }}
        
        .trade-header.active {{
            background: #667eea;
            color: white;
        }}
        
        .trade-header div {{
            font-size: 0.9em;
        }}
        
        .trade-header .trade-number {{
            font-weight: bold;
            font-size: 1.1em;
        }}
        
        .trade-chart {{
            display: none;
            padding: 20px;
            background: #f8f9fa;
            border-top: 2px solid #e9ecef;
        }}
        
        .trade-chart.active {{
            display: block;
        }}
        
        .chart-container {{
            width: 100%;
            height: 400px;
            background: white;
            border-radius: 10px;
            padding: 10px;
        }}
        
        .profit {{
            color: #10b981;
            font-weight: bold;
        }}
        
        .loss {{
            color: #ef4444;
            font-weight: bold;
        }}
        
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
        }}
        
        .badge-success {{
            background: #d1fae5;
            color: #065f46;
        }}
        
        .badge-danger {{
            background: #fee2e2;
            color: #991b1b;
        }}
        
        .expand-icon {{
            transition: transform 0.3s ease;
        }}
        
        .expand-icon.active {{
            transform: rotate(90deg);
        }}
        
        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #666;
            font-size: 0.9em;
        }}
        
        @media print {{
            body {{
                background: white;
                padding: 0;
            }}
            
            .container {{
                box-shadow: none;
            }}
            
            .stat-card:hover {{
                transform: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>📊 {report.get('strategy_name', 'Strategia Tradingowa')}</h1>
            <div class="period">
                {report.get('test_period', 'Okres testowania')} | Interwał: {report.get('interval_hours', 1)}h
            </div>
        </div>
        
        <!-- Główne statystyki -->
        <div class="stats-grid">
            <div class="stat-card {'positive' if profit_loss_perc >= 0 else 'negative'}">
                <div class="label">Zwrot</div>
                <div class="value" style="color: {total_return_color}">{profit_loss_perc:+.2f}%</div>
            </div>
            
            <div class="stat-card">
                <div class="label">Kapitał początkowy</div>
                <div class="value">{report['initial_capital']:.2f} USDT</div>
            </div>
            
            <div class="stat-card">
                <div class="label">Kapitał końcowy</div>
                <div class="value">{report['final_capital']:.2f} USDT</div>
            </div>
            
            <div class="stat-card">
                <div class="label">Zysk/Strata</div>
                <div class="value" style="color: {total_return_color}">{report['total_return_usdt']:+.2f} USDT</div>
            </div>
            
            <div class="stat-card">
                <div class="label">Liczba transakcji</div>
                <div class="value">{report['total_trades']}</div>
            </div>
            
            <div class="stat-card">
                <div class="label">Współczynnik wygranych</div>
                <div class="value" style="color: {win_rate_color}">{report['win_rate']:.1f}%</div>
            </div>
            
            <div class="stat-card {'positive' if report['winning_trades'] > report['losing_trades'] else 'negative'}">
                <div class="label">Wygrane / Przegrane</div>
                <div class="value">{report['winning_trades']} / {report['losing_trades']}</div>
            </div>
            
            <div class="stat-card">
                <div class="label">Risk/Reward Ratio</div>
                <div class="value">{abs(report['avg_profit'] / report['avg_loss']) if report['avg_loss'] != 0 else 0:.2f}</div>
            </div>
        </div>
        
        <!-- Parametry strategii -->
        <div class="section">
            <h2 class="section-title">⚙️ Parametry Strategii</h2>
            <div class="params-grid">
"""
    
    # Dodaj parametry strategii
    for param_name, param_value in report.get('strategy_params', {}).items():
        html_content += f"""
                <div class="param-item">
                    <div class="param-name">{param_name}</div>
                    <div class="param-value">{param_value}</div>
                </div>
"""
    
    html_content += f"""
            </div>
        </div>
        
        <!-- Transakcje z wykresami -->
        <div class="section">
            <h2 class="section-title">📈 Wszystkie Transakcje ({report['total_trades']}) - Kliknij aby zobaczyć wykres</h2>
            <div class="trades-container">
"""
    
    # Dodaj wszystkie transakcje z wykresami
    for idx, trade in enumerate(trades_with_charts, 1):
        profit_class = "profit" if trade['profit_perc'] > 0 else "loss"
        badge_class = "badge-success" if trade['profit_perc'] > 0 else "badge-danger"
        sign = "+" if trade['profit_perc'] > 0 else ""
        icon = "▶"
        
        # Konwertuj dane świeczek do JSON
        candles_json = json.dumps(trade.get('candles', []))
        
        html_content += f"""
                <div class="trade-row">
                    <div class="trade-header" onclick="toggleChart({idx})">
                        <div class="expand-icon" id="icon-{idx}">{icon}</div>
                        <div class="trade-number">#{idx}</div>
                        <div><strong>{trade['symbol']}</strong></div>
                        <div>{str(trade['entry_time'])[:19]}</div>
                        <div>{str(trade['exit_time'])[:19]}</div>
                        <div>{trade['entry_price']:.4f}</div>
                        <div>{trade['exit_price']:.4f}</div>
                        <div class="{profit_class}">{sign}{trade['profit_usdt']:.2f} USDT</div>
                        <div><span class="badge {badge_class}">{sign}{trade['profit_perc']:.2f}%</span></div>
                    </div>
                    <div class="trade-chart" id="chart-{idx}">
                        <div class="chart-container" id="chart-container-{idx}"></div>
                    </div>
                    <script>
                        var chartData{idx} = {candles_json};
                        var entryPrice{idx} = {trade['entry_price']};
                        var exitPrice{idx} = {trade['exit_price']};
                        var exitReason{idx} = '{trade.get('exit_reason', trade.get('reason', 'UNKNOWN'))}';
                        // Konwertuj czasy do Unix timestamp
                        var entryTime{idx} = Math.floor(new Date('{str(trade['entry_time'])[:19]}').getTime() / 1000);
                        var exitTime{idx} = Math.floor(new Date('{str(trade['exit_time'])[:19]}').getTime() / 1000);
                    </script>
                </div>
"""
    
    html_content += """
            </div>
        </div>
        
        <!-- Footer -->
        <div class="footer">
            Raport wygenerowany: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """ | 
            Backtest Engine v2.0 | Kliknij na transakcję aby zobaczyć wykres świecowy
        </div>
    </div>
    
    <script>
        // Przechowuj wykresy
        const charts = {};
        
        function toggleChart(tradeId) {
            const chartDiv = document.getElementById(`chart-${tradeId}`);
            const icon = document.getElementById(`icon-${tradeId}`);
            const header = chartDiv.previousElementSibling;
            
            // Toggle visibility
            chartDiv.classList.toggle('active');
            icon.classList.toggle('active');
            header.classList.toggle('active');
            
            // Utwórz wykres jeśli jeszcze nie istnieje
            if (chartDiv.classList.contains('active') && !charts[tradeId]) {
                createChart(tradeId);
            }
        }
        
        function createChart(tradeId) {
            const container = document.getElementById(`chart-container-${tradeId}`);
            const candlesData = window[`chartData${tradeId}`];
            const entryPrice = window[`entryPrice${tradeId}`];
            const exitPrice = window[`exitPrice${tradeId}`];
            const entryTime = window[`entryTime${tradeId}`];
            const exitTime = window[`exitTime${tradeId}`];
            const exitReason = window[`exitReason${tradeId}`] || 'UNKNOWN';
            
            if (!candlesData || candlesData.length === 0) {
                container.innerHTML = '<p style="text-align: center; padding: 20px;">Brak danych świeczek dla tej transakcji</p>';
                return;
            }
            
            // Utwórz wykres
            const chart = LightweightCharts.createChart(container, {
                width: container.clientWidth,
                height: 400,
                layout: {
                    background: { color: '#ffffff' },
                    textColor: '#333',
                },
                grid: {
                    vertLines: { color: '#e1e1e1' },
                    horzLines: { color: '#e1e1e1' },
                },
                crosshair: {
                    mode: LightweightCharts.CrosshairMode.Normal,
                },
                rightPriceScale: {
                    borderColor: '#cccccc',
                },
                timeScale: {
                    borderColor: '#cccccc',
                    timeVisible: true,
                    secondsVisible: false,
                },
            });
            
            // Dodaj serię świecową
            const candlestickSeries = chart.addCandlestickSeries({
                upColor: '#26a69a',
                downColor: '#ef5350',
                borderVisible: false,
                wickUpColor: '#26a69a',
                wickDownColor: '#ef5350',
            });
            
            // Konwertuj dane
            const formattedData = candlesData.map(candle => ({
                time: candle.time,
                open: candle.open,
                high: candle.high,
                low: candle.low,
                close: candle.close,
            }));
            
            candlestickSeries.setData(formattedData);
            
            // Dodaj linie wejścia i wyjścia
            const entryLine = chart.addLineSeries({
                color: '#2196F3',
                lineWidth: 2,
                lineStyle: LightweightCharts.LineStyle.Solid,
                title: 'Wejście',
            });
            
            const exitLine = chart.addLineSeries({
                color: '#FF9800',
                lineWidth: 2,
                lineStyle: LightweightCharts.LineStyle.Solid,
                title: 'Wyjście',
            });
            
            // Ustaw dane dla linii
            entryLine.setData([
                { time: formattedData[0].time, value: entryPrice },
                { time: formattedData[formattedData.length - 1].time, value: entryPrice }
            ]);
            
            exitLine.setData([
                { time: formattedData[0].time, value: exitPrice },
                { time: formattedData[formattedData.length - 1].time, value: exitPrice }
            ]);
            
            // Dodaj markery dla punktów wejścia/wyjścia
            const markers = [
                {
                    time: entryTime,
                    position: 'belowBar',
                    color: '#2196F3',
                    shape: 'arrowUp',
                    text: 'KUPNO @ ' + entryPrice.toFixed(4)
                },
                {
                    time: exitTime,
                    position: 'aboveBar',
                    color: '#FF9800',
                    shape: 'arrowDown',
                    text: 'SPRZEDAŻ @ ' + exitPrice.toFixed(4) + ' (' + exitReason + ')'
                }
            ];
            
            candlestickSeries.setMarkers(markers);
            
            // Dopasuj widok
            chart.timeScale().fitContent();
            
            // Zapisz wykres
            charts[tradeId] = chart;
            
            // Obsługa zmiany rozmiaru
            window.addEventListener('resize', () => {
                chart.applyOptions({ width: container.clientWidth });
            });
        }
    </script>
</body>
</html>
"""
    
    # Zapisz do pliku
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"{datetime.now()} 🌐 Raport HTML z wykresami zapisany do: {filename}")
