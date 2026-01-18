import json
import sys
import os
from binance.client import Client
from binance.exceptions import BinanceAPIException
from datetime import datetime
from typing import Dict, List

# Konfiguracja kodowania UTF-8 dla Windows
if sys.platform == 'win32':
    try:
        # Próba ustawienia UTF-8 dla konsoli Windows
        os.system('chcp 65001 > nul')
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass  # Jeśli się nie uda, kontynuuj bez emoji


from database_manager import DatabaseManager
from position import Position
from strategies import (
    FallingCandlesStrategy,
    XRPPineScriptStrategy,
    BNBPineScriptStrategy,
    RedCandlesSequenceStrategy
)


class TradingBot:
    """
    Główna klasa bota tradingowego obsługująca wiele walut i strategii.
    Wczytuje konfigurację, zarządza pozycjami i wykonuje zlecenia.
    """
    
    def __init__(self, config_path: str = "config.json", dry_run: bool = False, 
                 filter_strategies: list = None, filter_symbols: list = None,
                 backtest_timestamp: datetime = None):
        """
        Args:
            config_path: Ścieżka do pliku konfiguracyjnego JSON
            dry_run: Jeśli True, nie wykonuje rzeczywistych transakcji (tylko symulacja)
            filter_strategies: Lista strategy_id do uruchomienia (None = wszystkie)
            filter_symbols: Lista symboli do uruchomienia (None = wszystkie)
            backtest_timestamp: Znacznik czasowy dla testowania historycznego (None = dane aktualne)
        """
        print(f"{datetime.now()} 🚀 Inicjalizacja TradingBot...")
        
        if dry_run:
            print(f"{datetime.now()} ⚠️ TRYB DRY-RUN - Transakcje NIE będą wykonywane!")
        
        if backtest_timestamp:
            print(f"{datetime.now()} 📅 TRYB BACKTEST - Testowanie na danych historycznych: {backtest_timestamp}")
        
        self.dry_run = dry_run
        self.filter_strategies = filter_strategies
        self.filter_symbols = filter_symbols
        self.backtest_timestamp = backtest_timestamp
        
        # Wczytanie konfiguracji
        self.config = self._load_config(config_path)
        
        # Inicjalizacja Binance Client
        self.client = self._init_binance_client()
        
        # Inicjalizacja DatabaseManager
        self.db = DatabaseManager(self.config['mysql'])
        self.db.trades_table = self.config['trades_table']
        
        # Sprawdzenie i utworzenie tabeli transakcji
        self.db.ensure_trades_table()
        
        # Sprawdzenie i dodanie kolumny strategy_name
        self.db.ensure_strategy_column()
        
        # Wczytanie strategii dla każdej waluty
        self.strategies = self._load_strategies()
        
        # Słownik aktywnych pozycji: {symbol: Position}
        self.positions: Dict[str, Position] = {}
        
        print(f"{datetime.now()} ✅ TradingBot zainicjalizowany z {len(self.strategies)} strategiami")
    
    def _load_config(self, config_path: str) -> dict:
        """Wczytuje konfigurację z pliku JSON."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            print(f"{datetime.now()} ✅ Konfiguracja wczytana z {config_path}")
            return config
        except Exception as e:
            print(f"{datetime.now()} ❌ Błąd wczytywania konfiguracji: {e}")
            raise
    
    def _init_binance_client(self) -> Client:
        """Inicjalizuje klienta Binance API."""
        try:
            binance_config = self.config['binance']
            client = Client(
                binance_config['api_key'],
                binance_config['api_secret'],
                testnet=binance_config.get('testnet', True)
            )
            
            # Synchronizacja czasu z serwerem Binance
            self._sync_time_with_binance(client)
            
            # Test połączenia jeśli włączony w konfiguracji
            if binance_config.get('test_api_on_start', False):
                self._test_binance_connection(client, binance_config.get('testnet', True))
            else:
                print(f"{datetime.now()} ✅ Połączono z Binance {'Testnet' if binance_config.get('testnet') else 'Mainnet'}")
            
            return client
        except BinanceAPIException as e:
            print(f"{datetime.now()} ❌ Błąd połączenia z Binance: {e}")
            raise
    
    def _sync_time_with_binance(self, client: Client):
        """
        Synchronizuje czas lokalny z serwerem Binance.
        Oblicza różnicę czasu i ustawia offset w kliencie.
        """
        try:
            # Pobierz czas serwera Binance
            server_time = client.get_server_time()
            server_timestamp = server_time['serverTime']
            
            # Oblicz różnicę między czasem lokalnym a serwerem
            import time
            local_timestamp = int(time.time() * 1000)
            time_offset = server_timestamp - local_timestamp
            
            # Ustaw offset w kliencie
            client.timestamp_offset = time_offset
            
            if abs(time_offset) > 1000:  # Jeśli różnica > 1 sekunda
                print(f"{datetime.now()} ⏰ Synchronizacja czasu: offset = {time_offset}ms")
            
        except Exception as e:
            print(f"{datetime.now()} ⚠️ Nie udało się zsynchronizować czasu: {e}")
            # Kontynuuj bez synchronizacji - może zadziałać
    
    def _test_binance_connection(self, client: Client, is_testnet: bool):
        """
        Testuje połączenie z Binance API.
        Sprawdza status serwera, ping i dostęp do konta.
        
        Args:
            client: Klient Binance
            is_testnet: Czy to testnet
        """
        try:
            print(f"{datetime.now()} 🔍 Testowanie połączenia z Binance {'Testnet' if is_testnet else 'Mainnet'}...")
            
            # Test 1: Status serwera
            status = client.get_system_status()
            if status['status'] == 0:
                print(f"{datetime.now()} ✅ Status serwera: OK")
            else:
                print(f"{datetime.now()} ⚠️ Status serwera: {status}")
            
            # Test 2: Ping
            client.ping()
            print(f"{datetime.now()} ✅ Ping: OK")
            
            # Test 3: Informacje o koncie
            account = client.get_account()
            print(f"{datetime.now()} ✅ Dostęp do konta: OK")
            
            # Wyświetlenie sald (tylko te > 0)
            balances = [b for b in account['balances'] if float(b['free']) > 0 or float(b['locked']) > 0]
            if balances:
                print(f"{datetime.now()} 💰 Salda na koncie:")
                for balance in balances[:5]:  # Pokaż max 5 pierwszych
                    free = float(balance['free'])
                    locked = float(balance['locked'])
                    total = free + locked
                    print(f"   {balance['asset']}: {total:.8f} (wolne: {free:.8f}, zablokowane: {locked:.8f})")
                if len(balances) > 5:
                    print(f"   ... i {len(balances) - 5} więcej")
            else:
                print(f"{datetime.now()} ℹ️ Brak środków na koncie testowym")
            
            # Test 4: Sprawdzenie uprawnień API
            permissions = account.get('permissions', [])
            print(f"{datetime.now()} ✅ Uprawnienia API: {', '.join(permissions)}")
            
            print(f"{datetime.now()} ✅ Test połączenia zakończony pomyślnie!")
            
        except BinanceAPIException as e:
            print(f"{datetime.now()} ❌ Błąd podczas testu połączenia: {e}")
            print(f"{datetime.now()} ⚠️ Sprawdź czy klucze API są poprawne i mają odpowiednie uprawnienia")
            raise
        except Exception as e:
            print(f"{datetime.now()} ❌ Nieoczekiwany błąd podczas testu: {e}")
            raise
    
    def _load_strategies(self) -> List:
        """
        Wczytuje strategie z konfiguracji.
        Tworzy instancje klas strategii dla każdej włączonej waluty.
        """
        strategies = []
        
        # Mapowanie nazw strategii na klasy
        strategy_classes = {
            'FallingCandlesStrategy': FallingCandlesStrategy,
            'XRPPineScriptStrategy': XRPPineScriptStrategy,
            'BNBPineScriptStrategy': BNBPineScriptStrategy,
            'RedCandlesSequenceStrategy': RedCandlesSequenceStrategy,
        }
        
        for currency_config in self.config['currencies']:
            # Filtrowanie po symbolu
            if self.filter_symbols and currency_config['symbol'] not in self.filter_symbols:
                print(f"{datetime.now()} ⏭️ Pomijam {currency_config['symbol']} (nie w filtrze symboli)")
                continue
            
            # Filtrowanie po strategy_id
            strategy_id = currency_config.get('strategy_id')
            if self.filter_strategies and strategy_id not in self.filter_strategies:
                print(f"{datetime.now()} ⏭️ Pomijam {strategy_id} (nie w filtrze strategii)")
                continue
            
            if not currency_config.get('enabled', True):
                print(f"{datetime.now()} ⚪ Strategia {currency_config.get('strategy_id', currency_config['strategy'])} dla {currency_config['symbol']} wyłączona")
                continue
            
            strategy_name = currency_config['strategy']
            
            if strategy_name not in strategy_classes:
                print(f"{datetime.now()} ⚠️ Nieznana strategia: {strategy_name}, pomijam")
                continue
            
            # Tworzenie instancji strategii
            strategy_class = strategy_classes[strategy_name]
            strategy = strategy_class(
                symbol=currency_config['symbol'],
                params=currency_config.get('params', {}),
                strategy_id=currency_config.get('strategy_id')  # Przekazanie strategy_id
            )
            
            # Dodanie dodatkowych informacji z konfiguracji
            strategy.table = currency_config['table']
            strategy.buy_quantity = currency_config['buy_quantity']
            
            strategies.append(strategy)
            print(f"{datetime.now()} ✅ Załadowano strategię: {strategy}")
        
        return strategies
    
    def _load_open_positions(self):
        """Wczytuje otwarte pozycje z bazy danych."""
        for strategy in self.strategies:
            open_trade = self.db.check_open_position(strategy.symbol)
            
            if open_trade:
                position = Position(
                    db_id=open_trade['id'],
                    symbol=open_trade['symbol'],
                    strategy_name=open_trade['strategy_name'],
                    entry_price=open_trade['buy_price'],
                    quantity=open_trade.get('quantity', strategy.buy_quantity)
                )
                
                # Klucz pozycji: symbol + strategy_id (unikalny dla każdej instancji strategii)
                position_key = f"{position.symbol}_{strategy.strategy_id}"
                self.positions[position_key] = position
                
                print(f"{datetime.now()} ℹ️ Znaleziono otwartą pozycję: {position}")
    
    def run(self):
        """
        Główna pętla bota.
        Sprawdza wszystkie strategie i wykonuje odpowiednie akcje.
        """
        print(f"{datetime.now()} 🔄 Rozpoczynam analizę strategii...")
        
        # Wczytanie otwartych pozycji z bazy
        self._load_open_positions()
        
        # Przetwarzanie każdej strategii
        for strategy in self.strategies:
            try:
                self._process_strategy(strategy)
            except Exception as e:
                print(f"{datetime.now()} ❌ Błąd przetwarzania strategii {strategy}: {e}")
                continue
        
        print(f"{datetime.now()} 🏁 Zakończono analizę strategii")
    
    def scan_date_range(self, start_date: datetime, end_date: datetime, interval_hours: int = 1):
        """
        Skanuje zakres dat w poszukiwaniu sygnałów kupna.
        
        Args:
            start_date: Data początkowa
            end_date: Data końcowa
            interval_hours: Interwał między sprawdzeniami (domyślnie 1h dla świec 1h)
        
        Returns:
            Lista słowników z wynikami
        """
        from datetime import timedelta
        
        print(f"\n{datetime.now()} 🔍 SKANOWANIE ZAKRESU DAT")
        print(f"{'='*80}")
        print(f"📅 Od: {start_date}")
        print(f"📅 Do: {end_date}")
        print(f"⏱️  Interwał: {interval_hours}h")
        print(f"📊 Strategie: {len(self.strategies)}")
        print(f"{'='*80}\n")
        
        results = []
        current_date = start_date
        total_checks = 0
        
        while current_date <= end_date:
            for strategy in self.strategies:
                try:
                    # Pobierz dane historyczne do tego momentu
                    df = self.db.load_historical_data(
                        strategy.table, 
                        self.config['history_bars'], 
                        current_date
                    )
                    
                    if df.empty:
                        continue
                    
                    # Sprawdź sygnał kupna
                    if strategy.check_buy_signal(df):
                        current_price = df['close'].iloc[-1]
                        tp_price = strategy.get_take_profit(current_price)
                        sl_price = strategy.get_stop_loss(current_price)
                        
                        result = {
                            'timestamp': current_date,
                            'strategy_id': strategy.strategy_id,
                            'symbol': strategy.symbol,
                            'price': current_price,
                            'tp': tp_price,
                            'sl': sl_price,
                            'tp_perc': strategy.params.get('take_profit_perc', 0),
                            'sl_perc': strategy.params.get('stop_loss_perc', 0)
                        }
                        results.append(result)
                        
                        print(f"✅ {current_date} | {strategy.strategy_id} | {strategy.symbol}")
                        print(f"   💰 Cena: {current_price:.2f}")
                        print(f"   📈 TP: {tp_price:.2f} (+{result['tp_perc']:.1f}%)")
                        print(f"   📉 SL: {sl_price:.2f} (-{result['sl_perc']:.1f}%)")
                        print()
                    
                    total_checks += 1
                    
                except Exception as e:
                    print(f"⚠️ Błąd dla {strategy.strategy_id} w {current_date}: {e}")
                    continue
            
            # Przejdź do następnego interwału
            current_date += timedelta(hours=interval_hours)
        
        # Podsumowanie
        print(f"\n{datetime.now()} 📊 PODSUMOWANIE SKANOWANIA")
        print(f"{'='*80}")
        print(f"🔍 Sprawdzono punktów: {total_checks}")
        print(f"✅ Znaleziono sygnałów kupna: {len(results)}")
        
        if results:
            print(f"\n📋 LISTA WSZYSTKICH SYGNAŁÓW:")
            print(f"{'-'*80}")
            print(f"{'Data':<20} {'Strategia':<20} {'Symbol':<10} {'Cena':<10} {'TP%':<8} {'SL%':<8}")
            print(f"{'-'*80}")
            
            for r in results:
                print(f"{str(r['timestamp']):<20} {r['strategy_id']:<20} {r['symbol']:<10} "
                      f"{r['price']:<10.2f} +{r['tp_perc']:<7.1f} -{r['sl_perc']:<7.1f}")
            
            print(f"{'-'*80}")
            
            # Statystyki per strategia
            print(f"\n📈 STATYSTYKI PER STRATEGIA:")
            strategy_counts = {}
            for r in results:
                sid = r['strategy_id']
                strategy_counts[sid] = strategy_counts.get(sid, 0) + 1
            
            for sid, count in strategy_counts.items():
                print(f"   {sid}: {count} sygnałów")
        
        print(f"{'='*80}\n")
        
        return results
    
    def _process_strategy(self, strategy):
        """
        Przetwarza pojedynczą strategię.
        Sprawdza sygnały kupna/sprzedaży i wykonuje odpowiednie akcje.
        """
        print(f"\n{datetime.now()} 📊 Przetwarzam: {strategy}")
        
        # Pobranie danych świec - historyczne lub aktualne
        if self.backtest_timestamp:
            df = self.db.load_historical_data(strategy.table, self.config['history_bars'], self.backtest_timestamp)
        else:
            df = self.db.load_data(strategy.table, self.config['history_bars'])
        
        if df.empty:
            print(f"{datetime.now()} ⚠️ Brak danych dla {strategy.symbol}, pomijam")
            return
        
        current_price = df['close'].iloc[-1]
        print(f"{datetime.now()} ℹ️ Aktualna cena {strategy.symbol}: {current_price}")
        
        # W trybie backtest pomijamy zarządzanie pozycjami - tylko sprawdzamy sygnały
        if self.backtest_timestamp:
            # Sprawdzenie sygnału kupna
            if strategy.check_buy_signal(df):
                print(f"{datetime.now()} ✅ SYGNAŁ KUPNA wykryty dla {strategy.strategy_id}!")
                print(f"{datetime.now()} 💡 Strategia wygenerowałaby kupno po cenie: {current_price}")
                
                # Dodatkowe informacje o strategii
                tp_price = strategy.get_take_profit(current_price)
                sl_price = strategy.get_stop_loss(current_price)
                print(f"{datetime.now()} 📈 Take Profit: {tp_price:.2f} (+{strategy.params.get('take_profit_perc', 0):.1f}%)")
                print(f"{datetime.now()} 📉 Stop Loss: {sl_price:.2f} (-{strategy.params.get('stop_loss_perc', 0):.1f}%)")
            else:
                print(f"{datetime.now()} ⚪ {strategy.strategy_id} - warunki kupna nie spełnione")
            return
        
        # Klucz pozycji - używamy strategy_id
        position_key = f"{strategy.symbol}_{strategy.strategy_id}"
        position = self.positions.get(position_key)
        
        # === ZARZĄDZANIE POZYCJĄ (jeśli istnieje) ===
        if position:
            print(f"{datetime.now()} ℹ️ Aktywna pozycja: {position}")
            
            # Sprawdzenie sygnału sprzedaży
            should_sell, reason = strategy.check_sell_signal(df, position)
            
            if should_sell:
                self._execute_sell(strategy, position, current_price, reason)
                return
        
        # === SPRAWDZENIE SYGNAŁU KUPNA (jeśli brak pozycji) ===
        else:
            # Sprawdzenie czy nie było niedawnej straty - używamy strategy_id
            if self.db.recent_loss(strategy.symbol, strategy.strategy_id, 
                                   strategy.params.get('loss_lookback_bars', 1)):
                print(f"{datetime.now()} ⚠️ {strategy.strategy_id} - blokada kupna po niedawnej stracie")
                return
            
            # Sprawdzenie sygnału kupna
            if strategy.check_buy_signal(df):
                self._execute_buy(strategy, current_price)
            else:
                print(f"{datetime.now()} ⚪ {strategy.strategy_id} - warunki kupna nie spełnione")
    
    def _execute_buy(self, strategy, current_price: float):
        """
        Wykonuje zlecenie kupna.
        
        Args:
            strategy: Strategia generująca sygnał
            current_price: Aktualna cena (informacyjna)
        """
        try:
            print(f"{datetime.now()} 🟢 KUPNO [{strategy.strategy_id}]: {strategy.symbol} po ~{current_price}")
            
            if self.dry_run:
                print(f"{datetime.now()} 🔸 DRY-RUN: Symulacja kupna (transakcja NIE została wykonana)")
                return
            
            # Wykonanie zlecenia rynkowego
            order = self.client.order_market_buy(
                symbol=strategy.symbol,
                quantity=strategy.buy_quantity
            )
            
            # Pobranie rzeczywistej ceny z wypełnienia
            buy_price = float(order['fills'][0]['price'])
            buy_time = datetime.now()
            
            # Zapis do bazy danych - używamy strategy_id
            trade_id = self.db.insert_trade(
                symbol=strategy.symbol,
                strategy_name=strategy.strategy_id,
                buy_price=buy_price,
                buy_time=buy_time,
                quantity=strategy.buy_quantity
            )
            
            # Utworzenie obiektu Position
            position = Position(
                db_id=trade_id,
                symbol=strategy.symbol,
                strategy_name=strategy.strategy_id,
                entry_price=buy_price,
                quantity=strategy.buy_quantity
            )
            
            # Zapamiętaj indeks świecy wejścia (dla strategii ze stagnacją)
            position.entry_bar_index = len(df) - 1
            
            # Dodanie do słownika pozycji - używamy strategy_id
            position_key = f"{strategy.symbol}_{strategy.strategy_id}"
            self.positions[position_key] = position
            
            print(f"{datetime.now()} ✅ KUPNO wykonane [{strategy.strategy_id}]: {strategy.symbol} po {buy_price}, ID={trade_id}")
            
        except BinanceAPIException as e:
            print(f"{datetime.now()} ❌ Błąd przy kupnie [{strategy.strategy_id}] {strategy.symbol}: {e}")
    
    def _execute_sell(self, strategy, position: Position, current_price: float, reason: str):
        """
        Wykonuje zlecenie sprzedaży.
        
        Args:
            strategy: Strategia zarządzająca pozycją
            position: Pozycja do zamknięcia
            current_price: Aktualna cena (informacyjna)
            reason: Powód sprzedaży (STOP_LOSS, TAKE_PROFIT)
        """
        try:
            print(f"{datetime.now()} 🔴 SPRZEDAŻ [{strategy.strategy_id}]: {strategy.symbol} po ~{current_price}, powód: {reason}")
            
            if self.dry_run:
                print(f"{datetime.now()} 🔸 DRY-RUN: Symulacja sprzedaży (transakcja NIE została wykonana)")
                return
            
            # Wykonanie zlecenia rynkowego
            order = self.client.order_market_sell(
                symbol=strategy.symbol,
                quantity=position.quantity
            )
            
            # Pobranie rzeczywistej ceny z wypełnienia
            sell_price = float(order['fills'][0]['price'])
            sell_time = datetime.now()
            
            # Obliczenie zysku/straty
            profit_perc = (sell_price - position.entry_price) / position.entry_price * 100
            
            # Aktualizacja w bazie danych
            self.db.update_trade(
                trade_id=position.db_id,
                sell_price=sell_price,
                sell_time=sell_time,
                profit_perc=profit_perc
            )
            
            # Usunięcie pozycji - używamy strategy_id
            position_key = f"{strategy.symbol}_{strategy.strategy_id}"
            if position_key in self.positions:
                del self.positions[position_key]
            
            emoji = "🟢" if profit_perc > 0 else "🔴"
            print(f"{datetime.now()} {emoji} SPRZEDAŻ wykonana [{strategy.strategy_id}]: {strategy.symbol} po {sell_price}, "
                  f"zysk/strata: {profit_perc:.2f}%")
            
        except BinanceAPIException as e:
            print(f"{datetime.now()} ❌ Błąd przy sprzedaży {strategy.symbol}: {e}")


# =========================
# URUCHOMIENIE
# =========================
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Bot tradingowy Binance - system wielowalutowy',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Przykłady użycia:

  # Uruchomienie standardowe
  python sandbox_binance_new.py

  # Tryb dry-run (bez rzeczywistych transakcji)
  python sandbox_binance_new.py --dry-run

  # Tylko konkretna strategia
  python sandbox_binance_new.py --strategy BNB_FallingCandles

  # Tylko konkretny symbol
  python sandbox_binance_new.py --symbol BNBUSDT

  # Test historyczny - sprawdź sygnały w przeszłości
  python sandbox_binance_new.py --backtest "2026-01-10 14:00:00"

  # Backtest dla konkretnej strategii
  python sandbox_binance_new.py --backtest "2026-01-10 14:00:00" --strategy BNB_FallingCandles

  # Skanowanie zakresu dat w poszukiwaniu sygnałów kupna
  python sandbox_binance_new.py --scan-range "2025-11-01 00:00:00" "2025-11-30 23:00:00"

  # Skanowanie z konkretną strategią
  python sandbox_binance_new.py --scan-range "2025-11-01 00:00:00" "2025-11-30 23:00:00" --strategy BNB_PineScript

  # Skanowanie z własnym interwałem (co 4h)
  python sandbox_binance_new.py --scan-range "2025-11-01 00:00:00" "2025-11-30 23:00:00" --interval 4

  # Wiele strategii
  python sandbox_binance_new.py --strategy BNB_FallingCandles --strategy XRP_Conservative

  # Własny plik konfiguracyjny
  python sandbox_binance_new.py --config my_config.json

  # Kombinacja parametrów
  python sandbox_binance_new.py --dry-run --symbol XRPUSDT
        '''
    )
    
    parser.add_argument(
        '--config', '-c',
        default='config.json',
        help='Ścieżka do pliku konfiguracyjnego (domyślnie: config.json)'
    )
    
    parser.add_argument(
        '--dry-run', '-d',
        action='store_true',
        help='Tryb symulacji - nie wykonuje rzeczywistych transakcji'
    )
    
    parser.add_argument(
        '--strategy', '-s',
        action='append',
        dest='strategies',
        help='Uruchom tylko określoną strategię (strategy_id). Można użyć wielokrotnie.'
    )
    
    parser.add_argument(
        '--symbol', '-y',
        action='append',
        dest='symbols',
        help='Uruchom tylko dla określonego symbolu (np. BNBUSDT). Można użyć wielokrotnie.'
    )
    
    parser.add_argument(
        '--backtest', '-b',
        type=str,
        dest='backtest',
        help='Test historyczny - podaj znacznik czasowy (format: YYYY-MM-DD HH:MM:SS)'
    )
    
    parser.add_argument(
        '--scan-range', '-r',
        type=str,
        nargs=2,
        metavar=('START', 'END'),
        dest='scan_range',
        help='Skanuj zakres dat w poszukiwaniu sygnałów kupna (format: YYYY-MM-DD HH:MM:SS)'
    )
    
    parser.add_argument(
        '--interval',
        type=int,
        default=1,
        dest='interval',
        help='Interwał skanowania w godzinach (domyślnie: 1)'
    )
    
    args = parser.parse_args()
    
    # Parsowanie backtest timestamp
    backtest_timestamp = None
    if args.backtest:
        try:
            from datetime import datetime as dt
            backtest_timestamp = dt.strptime(args.backtest, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            print(f"❌ Nieprawidłowy format daty. Użyj: YYYY-MM-DD HH:MM:SS")
            print(f"   Przykład: 2026-01-10 14:00:00")
            exit(1)
    
    # Parsowanie scan range
    scan_start = None
    scan_end = None
    if args.scan_range:
        try:
            from datetime import datetime as dt
            scan_start = dt.strptime(args.scan_range[0], '%Y-%m-%d %H:%M:%S')
            scan_end = dt.strptime(args.scan_range[1], '%Y-%m-%d %H:%M:%S')
            
            if scan_start >= scan_end:
                print(f"❌ Data początkowa musi być wcześniejsza niż końcowa")
                exit(1)
        except ValueError:
            print(f"❌ Nieprawidłowy format daty. Użyj: YYYY-MM-DD HH:MM:SS")
            print(f"   Przykład: --scan-range \"2025-11-01 00:00:00\" \"2025-11-30 23:00:00\"")
            exit(1)
    
    # Wyświetlenie parametrów
    if args.dry_run or args.strategies or args.symbols or args.backtest or args.scan_range:
        print(f"{datetime.now()} 📋 Parametry uruchomienia:")
        if args.dry_run:
            print(f"   - Tryb: DRY-RUN (symulacja)")
        if args.backtest:
            print(f"   - Backtest: {backtest_timestamp}")
        if args.scan_range:
            print(f"   - Skanowanie zakresu: {scan_start} → {scan_end}")
            print(f"   - Interwał: {args.interval}h")
        if args.strategies:
            print(f"   - Strategie: {', '.join(args.strategies)}")
        if args.symbols:
            print(f"   - Symbole: {', '.join(args.symbols)}")
        print()
    
    # Uruchomienie bota
    bot = TradingBot(
        config_path=args.config,
        dry_run=args.dry_run,
        filter_strategies=args.strategies,
        filter_symbols=args.symbols,
        backtest_timestamp=backtest_timestamp
    )
    
    # Tryb skanowania zakresu dat
    if args.scan_range:
        bot.scan_date_range(scan_start, scan_end, args.interval)
    else:
        bot.run()
