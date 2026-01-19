"""
Backtest Engine - Pełna symulacja strategii z zarządzaniem kapitałem.

Symuluje handel z początkowym kapitałem, śledzi wszystkie transakcje,
oblicza zyski/straty i generuje szczegółowy raport.
"""

# Konfiguracja UTF-8 dla Windows (emoji)
import sys
if sys.platform == 'win32':
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except:
        pass

import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from database_manager import DatabaseManager
from sliding_window import SlidingWindow
from strategies import XRPPineScriptStrategy
import json



class BacktestEngine:
    """
    Silnik backtestingu - symuluje handel z pełnym zarządzaniem kapitałem.
    """
    
    def __init__(self, db_manager: DatabaseManager, initial_capital: float = 100.0):
        """
        Args:
            db_manager: Manager bazy danych
            initial_capital: Początkowy kapitał (domyślnie 100 USDT)
        """
        self.db = db_manager
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.position = None  # Aktualna pozycja
        self.trades = []  # Historia transakcji
        self.equity_curve = []  # Krzywa kapitału
    
    def get_all_crypto_tables(self) -> List[str]:
        """
        Pobiera listę wszystkich tabel z kryptowalutami (*usdt_1h).
        
        Returns:
            Lista nazw tabel
        """
        try:
            engine = self.db.get_engine()
            from sqlalchemy import text
            
            query = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = :schema
                  AND table_name LIKE '%usdt_1h'
                ORDER BY table_name
            """)
            
            with engine.connect() as conn:
                result = conn.execute(query, {'schema': self.db.config['database']})
                tables = [row[0] for row in result]
            
            print(f"{datetime.now()} ✅ Znaleziono {len(tables)} tabel z kryptowalutami")
            for table in tables[:10]:  # Pokaż pierwsze 10
                print(f"   - {table}")
            if len(tables) > 10:
                print(f"   ... i {len(tables) - 10} więcej")
            
            return tables
            
        except Exception as e:
            print(f"{datetime.now()} ❌ Błąd pobierania tabel: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def run_backtest(self, strategy_class, strategy_params: dict, 
                     start_date: datetime, end_date: datetime,
                     tables: List[str] = None, interval_hours: int = 1) -> Dict:
        """
        Uruchamia backtest dla strategii na wielu walutach.
        
        Args:
            strategy_class: Klasa strategii do testowania
            strategy_params: Parametry strategii
            start_date: Data początkowa
            end_date: Data końcowa
            tables: Lista tabel do testowania (None = wszystkie)
            interval_hours: Interwał sprawdzania (domyślnie 1h)
        
        Returns:
            Słownik z wynikami backtestingu
        """
        print(f"\n{datetime.now()} 🚀 ROZPOCZYNAM BACKTEST")
        print(f"{'='*80}")
        print(f"💰 Kapitał początkowy: {self.initial_capital} USDT")
        print(f"📅 Okres: {start_date} → {end_date}")
        print(f"📊 Strategia: {strategy_class.__name__}")
        print(f"⏱️  Interwał: {interval_hours}h")
        print(f"{'='*80}\n")
        
        # Pobierz tabele jeśli nie podano
        if tables is None:
            tables = self.get_all_crypto_tables()
        
        if not tables:
            print(f"{datetime.now()} ❌ Brak tabel do przetestowania")
            return {}
        
        print(f"{datetime.now()} 📊 Testowanie {len(tables)} walut...\n")
        
        # Reset stanu
        self.capital = self.initial_capital
        self.position = None
        self.trades = []
        self.equity_curve = []
        
        # Iteruj przez czas
        current_time = start_date
        
        while current_time <= end_date:
            # Sprawdź czy mamy otwartą pozycję
            if self.position:
                # Zarządzaj otwartą pozycją
                self._manage_position(current_time, strategy_class, strategy_params)
            else:
                # Szukaj nowej okazji
                self._find_opportunity(current_time, tables, strategy_class, strategy_params)
            
            # Zapisz stan kapitału
            self.equity_curve.append({
                'time': current_time,
                'capital': self.capital,
                'position_value': self._get_position_value(current_time) if self.position else 0
            })
            
            # Następny interwał
            current_time += timedelta(hours=interval_hours)
        
        # Zamknij pozycję jeśli jest otwarta na koniec
        if self.position:
            self._close_position(end_date, "END_OF_BACKTEST")
        
        # Generuj raport
        return self._generate_report()
    
    def run_backtest_optimized(self, strategy_class, strategy_params: dict,
                              start_date: datetime, end_date: datetime,
                              tables: List[str] = None, interval_hours: int = 1) -> Dict:
        """
        ZOPTYMALIZOWANA wersja backtestingu używająca Sliding Window.
        
        Zamiast pobierać dane z bazy dla każdego kroku czasowego (220,000 zapytań SQL),
        ładuje wszystkie dane raz na początku i przesuw okno w pamięci.
        
        Przyspieszenie: ~90x szybciej niż run_backtest()
        
        Args:
            strategy_class: Klasa strategii do testowania
            strategy_params: Parametry strategii
            start_date: Data początkowa
            end_date: Data końcowa
            tables: Lista tabel do testowania (None = wszystkie)
            interval_hours: Interwał sprawdzania (domyślnie 1h)
        
        Returns:
            Słownik z wynikami backtestingu
        """
        print(f"\n{datetime.now()} 🚀 ROZPOCZYNAM ZOPTYMALIZOWANY BACKTEST (Sliding Window)")
        print(f"{'='*80}")
        print(f"💰 Kapitał początkowy: {self.initial_capital} USDT")
        print(f"📅 Okres: {start_date} → {end_date}")
        print(f"📊 Strategia: {strategy_class.__name__}")
        print(f"⏱️  Interwał: {interval_hours}h")
        print(f"{'='*80}\n")
        
        # Pobierz tabele jeśli nie podano
        if tables is None:
            tables = self.get_all_crypto_tables()
        
        if not tables:
            print(f"{datetime.now()} ❌ Brak tabel do przetestowania")
            return {}
        
        # === KROK 1: ZAŁADUJ WSZYSTKIE DANE RAZ (Sliding Window) ===
        print(f"{datetime.now()} 📥 Ładowanie danych do pamięci...")
        data_cache = {}
        
        for table in tables:
            df = self.db.load_all_data_in_range(table, start_date, end_date)
            if not df.empty and len(df) >= 50:
                try:
                    data_cache[table] = SlidingWindow(df, window_size=50)
                except Exception as e:
                    print(f"{datetime.now()} ⚠️ Błąd tworzenia okna dla {table}: {e}")
        
        if not data_cache:
            print(f"{datetime.now()} ❌ Brak danych do przetestowania")
            return {}
        
        print(f"{datetime.now()} ✅ Załadowano dane dla {len(data_cache)} walut do pamięci")
        print(f"{datetime.now()} 🚀 Rozpoczynam symulację...\n")
        
        # Reset stanu
        self.capital = self.initial_capital
        self.position = None
        self.trades = []
        self.equity_curve = []
        
        # === KROK 2: ITERUJ PRZEZ CZAS (bez SQL!) ===
        current_time = start_date
        iteration = 0
        total_iterations = int((end_date - start_date).total_seconds() / 3600 / interval_hours)
        
        while current_time <= end_date:
            iteration += 1
            
            # Sprawdź czy mamy otwartą pozycję
            if self.position:
                # Zarządzaj otwartą pozycją (używając cache)
                self._manage_position_optimized(current_time, data_cache, strategy_class, strategy_params)
            else:
                # Szukaj nowej okazji (używając cache)
                self._find_opportunity_optimized(current_time, data_cache, strategy_class, strategy_params)
            
            # Zapisz stan kapitału
            self.equity_curve.append({
                'time': current_time,
                'capital': self.capital,
                'position_value': self._get_position_value_optimized(current_time, data_cache) if self.position else 0
            })
            
            # Progress bar co 500 iteracji
            if iteration % 500 == 0:
                progress = (iteration / total_iterations) * 100
                print(f"⏳ Progress: {progress:.1f}% ({iteration}/{total_iterations} iteracji)")
            
            # Następny interwał
            current_time += timedelta(hours=interval_hours)
        
        # Zamknij pozycję jeśli jest otwarta na koniec
        if self.position:
            self._close_position(end_date, "END_OF_BACKTEST")
        
        print(f"\n{datetime.now()} ✅ Backtest zakończony!")
        
        # Generuj raport
        return self._generate_report()

    
    def _find_opportunity(self, current_time: datetime, tables: List[str],
                         strategy_class, strategy_params: dict):
        """
        Szuka okazji do kupna wśród wszystkich walut.
        """
        for table in tables:
            # Pobierz dane historyczne
            df = self.db.load_historical_data(table, 50, current_time)
            
            if df.empty or len(df) < 10:
                continue
            
            # Utwórz strategię
            symbol = table.replace('_1h', '').upper()
            strategy = strategy_class(symbol, strategy_params, f"Backtest_{symbol}")
            
            # Sprawdź sygnał kupna
            if strategy.check_buy_signal(df):
                current_price = df['close'].iloc[-1]
                
                # Kup za cały kapitał
                quantity = self.capital / current_price
                
                self.position = {
                    'symbol': symbol,
                    'table': table,
                    'entry_time': current_time,
                    'entry_price': current_price,
                    'quantity': quantity,
                    'strategy': strategy,
                    'tp_tracking': False,
                    'red_count': 0,
                    'entry_bar_index': len(df) - 1
                }
                
                print(f"{datetime.now()} 🟢 KUPNO: {symbol} @ {current_price:.4f} | Ilość: {quantity:.4f} | Kapitał: {self.capital:.2f}")
                
                # Kapitał = 0 (wszystko w pozycji)
                self.capital = 0
                break
    
    def _manage_position(self, current_time: datetime, strategy_class, strategy_params: dict):
        """
        Zarządza otwartą pozycją - sprawdza warunki sprzedaży.
        """
        if not self.position:
            return
        
        # Pobierz aktualne dane
        df = self.db.load_historical_data(self.position['table'], 50, current_time)
        
        if df.empty:
            return
        
        current_price = df['close'].iloc[-1]
        
        # Utwórz obiekt pozycji dla strategii
        class PositionMock:
            def __init__(self, pos_dict):
                self.entry_price = pos_dict['entry_price']
                self.tp_tracking = pos_dict['tp_tracking']
                self.red_count = pos_dict['red_count']
                self.entry_bar_index = pos_dict['entry_bar_index']
        
        pos_mock = PositionMock(self.position)
        
        # Sprawdź sygnał sprzedaży
        should_sell, reason = self.position['strategy'].check_sell_signal(df, pos_mock)
        
        # Aktualizuj stan pozycji
        self.position['tp_tracking'] = pos_mock.tp_tracking
        self.position['red_count'] = pos_mock.red_count
        
        if should_sell:
            self._close_position(current_time, reason, current_price)
    
    def _close_position(self, exit_time: datetime, reason: str, exit_price: float = None):
        """
        Zamyka pozycję i zapisuje transakcję.
        Wymusza maksymalną stratę równą Stop Loss (ochrona przed gwałtownymi spadkami).
        """
        if not self.position:
            return
        
        if exit_price is None:
            # Pobierz ostatnią cenę
            df = self.db.load_historical_data(self.position['table'], 1, exit_time)
            if not df.empty:
                exit_price = df['close'].iloc[-1]
            else:
                exit_price = self.position['entry_price']
        
        # === OCHRONA STOP LOSS ===
        # Oblicz minimalną cenę wyjścia (Stop Loss)
        sl_price = self.position['strategy'].get_stop_loss(self.position['entry_price'])
        
        # Jeśli cena spadła poniżej SL, użyj ceny SL (ochrona przed gapami)
        if exit_price < sl_price and reason == "STOP_LOSS":
            original_exit_price = exit_price
            exit_price = sl_price
            print(f"{datetime.now()} ⚠️  KOREKTA SL: Cena {original_exit_price:.4f} → {exit_price:.4f} (ochrona przed gapem)")
        
        # Oblicz zysk/stratę
        profit_perc = (exit_price - self.position['entry_price']) / self.position['entry_price'] * 100
        profit_usdt = self.position['quantity'] * (exit_price - self.position['entry_price'])
        
        # Zwróć kapitał
        self.capital = self.position['quantity'] * exit_price
        
        # Zapisz transakcję
        trade = {
            'symbol': self.position['symbol'],
            'entry_time': self.position['entry_time'],
            'entry_price': self.position['entry_price'],
            'exit_time': exit_time,
            'exit_price': exit_price,
            'quantity': self.position['quantity'],
            'profit_perc': profit_perc,
            'profit_usdt': profit_usdt,
            'capital_after': self.capital,
            'exit_reason': reason  # Dodano powód sprzedaży
        }
        
        self.trades.append(trade)
        
        emoji = "🟢" if profit_perc > 0 else "🔴"
        print(f"{datetime.now()} {emoji} SPRZEDAŻ: {self.position['symbol']} @ {exit_price:.4f} | "
              f"Zysk: {profit_perc:+.2f}% ({profit_usdt:+.2f} USDT) | "
              f"Kapitał: {self.capital:.2f} | Powód: {reason}")
        
        # Usuń pozycję
        self.position = None
    
    def _find_opportunity_optimized(self, current_time: datetime, 
                                   data_cache: Dict[str, SlidingWindow],
                                   strategy_class, strategy_params: dict):
        """
        ZOPTYMALIZOWANA wersja: Szuka okazji do kupna używając cache danych.
        Brak zapytań SQL - wszystkie dane w pamięci RAM.
        """
        for table, window in data_cache.items():
            # Pobierz okno danych z cache (bez SQL!)
            df = window.get_window_at_time(current_time)
            
            if df.empty or len(df) < 10:
                continue
            
            # Utwórz strategię
            symbol = table.replace('_1h', '').upper()
            strategy = strategy_class(symbol, strategy_params, f"Backtest_{symbol}")
            
            # Sprawdź sygnał kupna
            if strategy.check_buy_signal(df):
                current_price = df['close'].iloc[-1]
                
                # Kup za cały kapitał
                quantity = self.capital / current_price
                
                self.position = {
                    'symbol': symbol,
                    'table': table,
                    'entry_time': current_time,
                    'entry_price': current_price,
                    'quantity': quantity,
                    'strategy': strategy,
                    'tp_tracking': False,
                    'red_count': 0,
                    'entry_bar_index': len(df) - 1
                }
                
                print(f"{datetime.now()} 🟢 KUPNO: {symbol} @ {current_price:.4f} | Ilość: {quantity:.4f} | Kapitał: {self.capital:.2f}")
                
                # Kapitał = 0 (wszystko w pozycji)
                self.capital = 0
                break
    
    def _manage_position_optimized(self, current_time: datetime,
                                  data_cache: Dict[str, SlidingWindow],
                                  strategy_class, strategy_params: dict):
        """
        ZOPTYMALIZOWANA wersja: Zarządza otwartą pozycją używając cache danych.
        """
        if not self.position:
            return
        
        # Pobierz aktualne dane z cache (bez SQL!)
        window = data_cache.get(self.position['table'])
        if not window:
            return
        
        df = window.get_window_at_time(current_time)
        
        if df.empty:
            return
        
        current_price = df['close'].iloc[-1]
        
        # Utwórz obiekt pozycji dla strategii
        class PositionMock:
            def __init__(self, pos_dict):
                self.entry_price = pos_dict['entry_price']
                self.tp_tracking = pos_dict['tp_tracking']
                self.red_count = pos_dict['red_count']
                self.entry_bar_index = pos_dict['entry_bar_index']
        
        pos_mock = PositionMock(self.position)
        
        # Sprawdź sygnał sprzedaży
        should_sell, reason = self.position['strategy'].check_sell_signal(df, pos_mock)
        
        # Aktualizuj stan pozycji
        self.position['tp_tracking'] = pos_mock.tp_tracking
        self.position['red_count'] = pos_mock.red_count
        
        if should_sell:
            self._close_position(current_time, reason, current_price)
    
    def _get_position_value_optimized(self, current_time: datetime,
                                     data_cache: Dict[str, SlidingWindow]) -> float:
        """
        ZOPTYMALIZOWANA wersja: Oblicza aktualną wartość pozycji używając cache.
        """
        if not self.position:
            return 0
        
        window = data_cache.get(self.position['table'])
        if not window:
            return self.position['quantity'] * self.position['entry_price']
        
        df = window.get_window_at_time(current_time)
        if df.empty:
            return self.position['quantity'] * self.position['entry_price']
        
        current_price = df['close'].iloc[-1]
        return self.position['quantity'] * current_price

    
    def _get_position_value(self, current_time: datetime) -> float:
        """
        Oblicza aktualną wartość pozycji.
        """
        if not self.position:
            return 0
        
        df = self.db.load_historical_data(self.position['table'], 1, current_time)
        if df.empty:
            return self.position['quantity'] * self.position['entry_price']
        
        current_price = df['close'].iloc[-1]
        return self.position['quantity'] * current_price
    
    def _generate_report(self) -> Dict:
        """
        Generuje szczegółowy raport z backtestingu.
        """
        if not self.trades:
            return {
                'initial_capital': self.initial_capital,
                'final_capital': self.capital,
                'total_return_perc': 0,
                'total_trades': 0
            }
        
        # Statystyki
        total_trades = len(self.trades)
        winning_trades = [t for t in self.trades if t['profit_perc'] > 0]
        losing_trades = [t for t in self.trades if t['profit_perc'] < 0]
        
        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
        
        avg_profit = sum(t['profit_perc'] for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(t['profit_perc'] for t in losing_trades) / len(losing_trades) if losing_trades else 0
        
        total_return_perc = (self.capital - self.initial_capital) / self.initial_capital * 100
        
        # Najlepsza i najgorsza transakcja
        best_trade = max(self.trades, key=lambda t: t['profit_perc'])
        worst_trade = min(self.trades, key=lambda t: t['profit_perc'])
        
        report = {
            'initial_capital': self.initial_capital,
            'final_capital': self.capital,
            'total_return_perc': total_return_perc,
            'total_return_usdt': self.capital - self.initial_capital,
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'best_trade': best_trade,
            'worst_trade': worst_trade,
            'trades': self.trades,
            'equity_curve': self.equity_curve
        }
        
        return report
    
    def print_report(self, report: Dict):
        """
        Wyświetla raport w czytelnej formie z tabelkami.
        """
        if not report:
            print(f"\n{datetime.now()} ❌ Brak danych do raportu")
            return
        
        print(f"\n{'='*100}")
        print(f"{'RAPORT Z BACKTESTINGU':^100}")
        print(f"{'='*100}\n")
        
        # Informacje o strategii
        if 'strategy_name' in report:
            print(f"📊 STRATEGIA: {report['strategy_name']}")
            print(f"📅 OKRES TESTOWANIA: {report.get('test_period', 'N/A')}")
            print(f"⏱️  INTERWAŁ: {report.get('interval_hours', 1)}h")
            print()
            
            print(f"⚙️  PARAMETRY STRATEGII:")
            params = report.get('strategy_params', {})
            for key, value in params.items():
                print(f"   • {key}: {value}")
            print()
        
        # Wyniki finansowe
        print(f"┌{'─'*98}┐")
        print(f"│ {'WYNIKI FINANSOWE':^96} │")
        print(f"├{'─'*98}┤")
        print(f"│ {'Kapitał początkowy:':<50} {report['initial_capital']:>45.2f} USDT │")
        print(f"│ {'Kapitał końcowy:':<50} {report['final_capital']:>45.2f} USDT │")
        
        return_color = "🟢" if report['total_return_perc'] > 0 else "🔴"
        print(f"│ {'Zwrot:':<50} {return_color} {report['total_return_perc']:>42.2f}% │")
        print(f"│ {'Zysk/Strata:':<50} {report['total_return_usdt']:>45.2f} USDT │")
        print(f"└{'─'*98}┘")
        print()
        
        # Statystyki transakcji
        print(f"┌{'─'*98}┐")
        print(f"│ {'STATYSTYKI TRANSAKCJI':^96} │")
        print(f"├{'─'*98}┤")
        print(f"│ {'Wszystkie transakcje:':<50} {report['total_trades']:>46} │")
        print(f"│ {'Wygrane:':<50} {report['winning_trades']:>35} ({report['win_rate']:.1f}%) │")
        print(f"│ {'Przegrane:':<50} {report['losing_trades']:>46} │")
        print(f"│ {'Średni zysk:':<50} {report['avg_profit']:>44.2f}% │")
        print(f"│ {'Średnia strata:':<50} {report['avg_loss']:>44.2f}% │")
        
        if report['avg_loss'] != 0:
            risk_reward = abs(report['avg_profit'] / report['avg_loss'])
            print(f"│ {'Risk/Reward Ratio:':<50} {risk_reward:>46.2f} │")
        
        print(f"└{'─'*98}┘")
        print()
        
        if report['total_trades'] > 0:
            # Najlepsza i najgorsza transakcja
            print(f"┌{'─'*98}┐")
            print(f"│ {'EKSTREMALNE TRANSAKCJE':^96} │")
            print(f"├{'─'*98}┤")
            
            best = report['best_trade']
            print(f"│ 🏆 NAJLEPSZA:                                                                            │")
            print(f"│    Symbol: {best['symbol']:<20} Zysk: {best['profit_perc']:>8.2f}% ({best['profit_usdt']:>8.2f} USDT)               │")
            print(f"│    {str(best['entry_time']):<25} → {str(best['exit_time']):<45} │")
            print(f"├{'─'*98}┤")
            
            worst = report['worst_trade']
            print(f"│ 💔 NAJGORSZA:                                                                            │")
            print(f"│    Symbol: {worst['symbol']:<20} Strata: {worst['profit_perc']:>6.2f}% ({worst['profit_usdt']:>8.2f} USDT)             │")
            print(f"│    {str(worst['entry_time']):<25} → {str(worst['exit_time']):<45} │")
            print(f"└{'─'*98}┘")
            print()
        
        # Lista wszystkich transakcji
        if len(report['trades']) > 0:
            print(f"┌{'─'*98}┐")
            print(f"│ {'WSZYSTKIE TRANSAKCJE':^96} │")
            print(f"├{'─'*98}┤")
            print(f"│ {'Symbol':<12} {'Wejście':<20} {'Wyjście':<20} {'Cena wej.':<12} {'Cena wyj.':<12} {'Zysk %':<10} │")
            print(f"├{'─'*98}┤")
            
            for trade in report['trades']:  # Wszystkie transakcje
                emoji = "🟢" if trade['profit_perc'] > 0 else "🔴"
                entry_time = str(trade['entry_time'])[:19]
                exit_time = str(trade['exit_time'])[:19]
                
                print(f"│ {emoji} {trade['symbol']:\u003c10} {entry_time:\u003c20} {exit_time:\u003c20} {trade['entry_price']:\u003c12.4f} {trade['exit_price']:\u003c12.4f} {trade['profit_perc']:\u003c9.2f}% │")
            
            if len(report['trades']) > 50:
                print(f"│ {'':^96} │")
                print(f"│ {'Wyświetlono wszystkie ' + str(len(report['trades'])) + ' transakcji':^96} │")

            
            print(f"└{'─'*98}┘")
        
        print(f"\n{'='*100}\n")
    
    def save_report_to_txt(self, report: Dict, filename: str):
        """
        Zapisuje raport do pliku TXT z ładnymi tabelkami ASCII.
        Bez emoji i znaków specjalnych które mogłyby zepsuć formatowanie.
        
        Args:
            report: Słownik z raportem
            filename: Nazwa pliku do zapisu
        """
        if not report:
            print(f"\n{datetime.now()} Brak danych do zapisu")
            return
        
        with open(filename, 'w', encoding='utf-8') as f:
            # Nagłówek
            f.write("=" * 100 + "\n")
            f.write(" " * 35 + "RAPORT Z BACKTESTINGU\n")
            f.write("=" * 100 + "\n\n")
            
            # Informacje o strategii
            if 'strategy_name' in report:
                f.write(f"STRATEGIA: {report['strategy_name']}\n")
                f.write(f"OKRES TESTOWANIA: {report.get('test_period', 'N/A')}\n")
                f.write(f"INTERWAL: {report.get('interval_hours', 1)}h\n")
                f.write("\n")
                
                f.write("PARAMETRY STRATEGII:\n")
                params = report.get('strategy_params', {})
                for key, value in params.items():
                    f.write(f"   - {key}: {value}\n")
                f.write("\n")
            
            # Wyniki finansowe
            f.write("+" + "-" * 98 + "+\n")
            f.write("|" + " " * 40 + "WYNIKI FINANSOWE" + " " * 42 + "|\n")
            f.write("+" + "-" * 98 + "+\n")
            f.write(f"| {'Kapital poczatkowy:':<50} {report['initial_capital']:>45.2f} USDT |\n")
            f.write(f"| {'Kapital koncowy:':<50} {report['final_capital']:>45.2f} USDT |\n")
            
            return_sign = "+" if report['total_return_perc'] > 0 else ""
            f.write(f"| {'Zwrot:':<50} {return_sign}{report['total_return_perc']:>45.2f}% |\n")
            f.write(f"| {'Zysk/Strata:':<50} {return_sign}{report['total_return_usdt']:>45.2f} USDT |\n")
            f.write("+" + "-" * 98 + "+\n\n")
            
            # Statystyki transakcji
            f.write("+" + "-" * 98 + "+\n")
            f.write("|" + " " * 38 + "STATYSTYKI TRANSAKCJI" + " " * 39 + "|\n")
            f.write("+" + "-" * 98 + "+\n")
            f.write(f"| {'Wszystkie transakcje:':<50} {report['total_trades']:>46} |\n")
            f.write(f"| {'Wygrane:':<50} {report['winning_trades']:>35} ({report['win_rate']:.1f}%) |\n")
            f.write(f"| {'Przegrane:':<50} {report['losing_trades']:>46} |\n")
            f.write(f"| {'Sredni zysk:':<50} {report['avg_profit']:>44.2f}% |\n")
            f.write(f"| {'Srednia strata:':<50} {report['avg_loss']:>44.2f}% |\n")
            
            if report['avg_loss'] != 0:
                risk_reward = abs(report['avg_profit'] / report['avg_loss'])
                f.write(f"| {'Risk/Reward Ratio:':<50} {risk_reward:>46.2f} |\n")
            
            f.write("+" + "-" * 98 + "+\n\n")
            
            if report['total_trades'] > 0:
                # Najlepsza i najgorsza transakcja
                f.write("+" + "-" * 98 + "+\n")
                f.write("|" + " " * 38 + "EKSTREMALNE TRANSAKCJE" + " " * 38 + "|\n")
                f.write("+" + "-" * 98 + "+\n")
                
                best = report['best_trade']
                f.write(f"| NAJLEPSZA:                                                                               |\n")
                f.write(f"|    Symbol: {best['symbol']:<20} Zysk: {best['profit_perc']:>8.2f}% ({best['profit_usdt']:>8.2f} USDT)               |\n")
                f.write(f"|    {str(best['entry_time']):<25} -> {str(best['exit_time']):<45} |\n")
                f.write("+" + "-" * 98 + "+\n")
                
                worst = report['worst_trade']
                f.write(f"| NAJGORSZA:                                                                               |\n")
                f.write(f"|    Symbol: {worst['symbol']:<20} Strata: {worst['profit_perc']:>6.2f}% ({worst['profit_usdt']:>8.2f} USDT)             |\n")
                f.write(f"|    {str(worst['entry_time']):<25} -> {str(worst['exit_time']):<45} |\n")
                f.write("+" + "-" * 98 + "+\n\n")
            
            # Lista wszystkich transakcji
            if len(report['trades']) > 0:
                f.write("+" + "-" * 98 + "+\n")
                f.write("|" + " " * 40 + "WSZYSTKIE TRANSAKCJE" + " " * 38 + "|\n")
                f.write("+" + "-" * 98 + "+\n")
                f.write(f"| {'Symbol':<12} {'Wejscie':<20} {'Wyjscie':<20} {'Cena wej.':<12} {'Cena wyj.':<12} {'Zysk %':<10} |\n")
                f.write("+" + "-" * 98 + "+\n")
                
                for trade in report['trades']:  # Wszystkie transakcje
                    result_marker = "+" if trade['profit_perc'] > 0 else "-"
                    entry_time = str(trade['entry_time'])[:19]
                    exit_time = str(trade['exit_time'])[:19]
                    
                    f.write(f"| {result_marker} {trade['symbol']:<10} {entry_time:<20} {exit_time:<20} "
                           f"{trade['entry_price']:<12.4f} {trade['exit_price']:<12.4f} "
                           f"{trade['profit_perc']:>8.2f}% |\n")
                
                f.write("+" + "-" * 98 + "+\n")
            
            f.write("\n" + "=" * 100 + "\n")
        
        print(f"{datetime.now()} Raport TXT zapisany do: {filename}")


def main():
    """
    Główna funkcja uruchamiająca backtest.
    """
    import argparse
    
    # Parser argumentów
    parser = argparse.ArgumentParser(
        description='Backtest Engine - Testowanie strategii na danych historycznych',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Przykłady użycia:

  # XRP PineScript Strategy na Q4 2025
  python backtest_engine.py --strategy XRP --start "2025-10-01" --end "2025-12-31"
  
  # BNB PineScript Strategy na cały rok
  python backtest_engine.py --strategy BNB --start "2025-01-01" --end "2025-12-31"
  
  # Red Candles Strategy na miesiąc
  python backtest_engine.py --strategy RED --start "2025-11-01" --end "2025-11-30"
  
  # Własny kapitał początkowy
  python backtest_engine.py --strategy XRP --capital 500 --start "2025-10-01" --end "2025-12-31"
        """
    )
    
    parser.add_argument(
        '--strategy',
        type=str,
        choices=['XRP', 'BNB', 'RED', 'FALLING'],
        default='XRP',
        help='Strategia do przetestowania (XRP=XRPPineScript, BNB=BNBPineScript, RED=RedCandles, FALLING=FallingCandles)'
    )
    
    parser.add_argument(
        '--capital',
        type=float,
        default=100.0,
        help='Kapitał początkowy w USDT (domyślnie: 100)'
    )
    
    parser.add_argument(
        '--start',
        type=str,
        required=True,
        help='Data początkowa (format: YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--end',
        type=str,
        required=True,
        help='Data końcowa (format: YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--interval',
        type=int,
        default=1,
        dest='interval',
        help='Interwał skanowania w godzinach (domyślnie: 1)'
    )
    
    parser.add_argument(
        '--optimized', '-o',
        action='store_true',
        dest='optimized',
        help='Użyj zoptymalizowanej wersji backtestingu (Sliding Window - 90x szybciej!)'
    )

    
    parser.add_argument(
        '--symbols',
        type=str,
        nargs='*',
        help='Lista symboli do testowania (np. BTCUSDT ETHUSDT), puste = wszystkie'
    )
    
    args = parser.parse_args()
    
    # Parsowanie dat
    try:
        from datetime import datetime as dt
        start_date = dt.strptime(args.start, '%Y-%m-%d')
        end_date = dt.strptime(args.end, '%Y-%m-%d')
        end_date = end_date.replace(hour=23, minute=59, second=59)
    except ValueError:
        print(f"❌ Nieprawidłowy format daty. Użyj: YYYY-MM-DD")
        print(f"   Przykład: 2025-10-01")
        return
    
    # Wybór strategii
    strategy_configs = {
        'XRP': {
            'class': 'XRPPineScriptStrategy',
            'name': 'XRP PineScript Strategy',
            'params': {
                'num_falling': 6,
                'allow_one_break': True,
                'take_profit_perc': 12.0,
                'stop_loss_perc': 5.0,
                'red_candles_to_sell': 3,
                'loss_lookback_bars': 1
            }
        },
        'BNB': {
            'class': 'BNBPineScriptStrategy',
            'name': 'BNB PineScript Strategy',
            'params': {
                'num_falling': 5,
                'allow_one_break': True,
                'take_profit_perc': 4.0,
                'stop_loss_perc': 12.0,  # Optymalny stosunek TP:SL (4:6)
                'red_candles_to_sell': 2,
                'loss_lookback_bars': 6
            }
        },
        'RED': {
            'class': 'RedCandlesSequenceStrategy',
            'name': 'Red Candles Sequence Strategy',
            'params': {
                'barsCount': 5,
                'totalDropPerc': 5.0,
                'tpPerc': 5.0,
                'slPerc': 50.0,
                'stagnationBars': 60
            }
        },
        'FALLING': {
            'class': 'FallingCandlesStrategy',
            'name': 'Falling Candles Strategy',
            'params': {
                'num_falling': 6,
                'allow_one_break': True,
                'take_profit_perc': 12.0,
                'stop_loss_perc': 5.0,
                'red_candles_to_sell': 3,
                'loss_lookback_bars': 1
            }
        }
    }
    
    strategy_config = strategy_configs[args.strategy]
    
    # Import strategii
    from strategies import (
        XRPPineScriptStrategy,
        BNBPineScriptStrategy,
        RedCandlesSequenceStrategy,
        FallingCandlesStrategy
    )
    
    strategy_classes = {
        'XRPPineScriptStrategy': XRPPineScriptStrategy,
        'BNBPineScriptStrategy': BNBPineScriptStrategy,
        'RedCandlesSequenceStrategy': RedCandlesSequenceStrategy,
        'FallingCandlesStrategy': FallingCandlesStrategy
    }
    
    strategy_class = strategy_classes[strategy_config['class']]
    
    # Wczytaj konfigurację bazy
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Inicjalizacja
    db = DatabaseManager(config['mysql'])
    engine = BacktestEngine(db, initial_capital=args.capital)
    
    # Przygotuj tabele
    tables = None
    if args.symbols:
        tables = [f"{symbol.lower()}_1h" for symbol in args.symbols]
    
    # Wyświetl informację o trybie
    if args.optimized:
        print(f"\n{'='*80}")
        print(f"🚀 TRYB ZOPTYMALIZOWANY (Sliding Window)")
        print(f"   Przyspieszenie: ~90x szybciej niż standardowy backtest")
        print(f"   Metoda: Ładowanie danych raz + operacje w pamięci RAM")
        print(f"{'='*80}\n")
    
    # Uruchom backtest - wybierz wersję
    if args.optimized:
        # ZOPTYMALIZOWANA WERSJA - Sliding Window
        report = engine.run_backtest_optimized(
            strategy_class=strategy_class,
            strategy_params=strategy_config['params'],
            start_date=start_date,
            end_date=end_date,
            tables=tables,
            interval_hours=args.interval
        )
    else:
        # STANDARDOWA WERSJA
        report = engine.run_backtest(
            strategy_class=strategy_class,
            strategy_params=strategy_config['params'],
            start_date=start_date,
            end_date=end_date,
            tables=tables,
            interval_hours=args.interval
        )

    
    # Dodaj informacje o strategii do raportu
    report['strategy_name'] = strategy_config['name']
    report['strategy_params'] = strategy_config['params']
    report['test_period'] = f"{args.start} → {args.end}"
    report['interval_hours'] = args.interval
    
    # Wyświetl raport
    engine.print_report(report)
    
    # Upewnij się że katalog reports istnieje
    import os
    os.makedirs('reports', exist_ok=True)
    
    # Zapisz raport do pliku JSON
    report_file_json = f"reports/backtest_{args.strategy}_{args.start}_{args.end}.json"
    
    # Konwersja datetime do string dla JSON
    report_json = report.copy()
    for trade in report_json.get('trades', []):
        trade['entry_time'] = str(trade['entry_time'])
        trade['exit_time'] = str(trade['exit_time'])
    
    for point in report_json.get('equity_curve', []):
        point['time'] = str(point['time'])
    
    with open(report_file_json, 'w', encoding='utf-8') as f:
        json.dump(report_json, f, indent=2, ensure_ascii=False)
    
    print(f"{datetime.now()} 💾 Raport JSON zapisany do: {report_file_json}")
    
    # Zapisz raport do pliku TXT
    report_file_txt = f"reports/backtest_{args.strategy}_{args.start}_{args.end}.txt"
    engine.save_report_to_txt(report, report_file_txt)
    
    # Zapisz raport do pliku HTML z wykresami
    from html_report_generator import generate_html_report_with_charts
    report_file_html = f"reports/backtest_{args.strategy}_{args.start}_{args.end}.html"
    generate_html_report_with_charts(report, report_file_html, db_manager=db)


if __name__ == "__main__":
    main()

