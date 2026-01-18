import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime


class DatabaseManager:
    """
    Zarządza połączeniem z bazą danych MySQL i operacjami na danych.
    Obsługuje pobieranie świec, zarządzanie transakcjami i sprawdzanie historii.
    """
    
    def __init__(self, config: dict):
        """
        Args:
            config: Słownik z konfiguracją MySQL (host, user, password, database, port)
        """
        self.config = config
        self.trades_table = config.get('trades_table', '_binance_crypto_trades')
        self._engine = None
    
    def get_engine(self):
        """Tworzy i zwraca silnik SQLAlchemy."""
        if self._engine is None:
            connection_string = (
                f"mysql+mysqlconnector://{self.config['user']}:{self.config['password']}"
                f"@{self.config['host']}:{self.config['port']}/{self.config['database']}"
            )
            self._engine = create_engine(connection_string)
        return self._engine
    
    def ensure_trades_table(self):
        """
        Sprawdza czy tabela transakcji istnieje i tworzy ją jeśli nie.
        """
        try:
            engine = self.get_engine()
            
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS `{self.trades_table}` (
                `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
                `symbol` varchar(20) NOT NULL,
                `strategy_name` varchar(50) DEFAULT NULL,
                `buy_time` datetime NOT NULL,
                `buy_price` float NOT NULL,
                `quantity` float DEFAULT NULL,
                `sell_time` datetime DEFAULT NULL,
                `sell_price` float DEFAULT NULL,
                `profit_loss_perc` float DEFAULT NULL,
                `position_status` enum('OPEN','CLOSED') NOT NULL DEFAULT 'OPEN',
                `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (`id`),
                KEY `idx_symbol_status` (`symbol`,`position_status`),
                KEY `idx_strategy` (`strategy_name`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
            
            with engine.begin() as conn:
                conn.execute(text(create_table_sql))
            
            print(f"{datetime.now()} ✅ Tabela {self.trades_table} gotowa")
            
        except SQLAlchemyError as e:
            print(f"{datetime.now()} ❌ Błąd tworzenia tabeli {self.trades_table}: {e}")
            raise
    
    def load_data(self, table: str, bars: int) -> pd.DataFrame:
        """
        Pobiera dane świec z określonej tabeli.
        
        Args:
            table: Nazwa tabeli ze świecami (np. 'bnbusdt_1h')
            bars: Liczba świec do pobrania
        
        Returns:
            DataFrame z danymi OHLCV posortowany od najstarszej do najnowszej
        """
        try:
            engine = self.get_engine()
            query = f"SELECT * FROM {table} ORDER BY open_time DESC LIMIT {bars}"
            df = pd.read_sql(query, engine)
            
            if df.empty:
                print(f"{datetime.now()} ⚠️ Brak danych w tabeli {table}")
                return pd.DataFrame()
            
            # Odwracamy kolejność: od najstarszej do najnowszej
            df = df[::-1].reset_index(drop=True)
            print(f"{datetime.now()} ✅ Pobrano {len(df)} świec z {table}")
            return df
            
        except SQLAlchemyError as e:
            print(f"{datetime.now()} ❌ Błąd podczas pobierania danych z {table}: {e}")
            return pd.DataFrame()
    
    def load_historical_data(self, table: str, bars: int, timestamp: datetime) -> pd.DataFrame:
        """
        Pobiera dane historyczne do określonego momentu w czasie.
        
        Args:
            table: Nazwa tabeli ze świecami
            bars: Liczba świec do pobrania
            timestamp: Znacznik czasowy - pobierz świece PRZED tym momentem
        
        Returns:
            DataFrame z danymi historycznymi
        """
        try:
            engine = self.get_engine()
            
            # Konwersja timestamp do formatu MySQL
            timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            
            query = f"""
                SELECT * FROM {table} 
                WHERE open_time <= '{timestamp_str}'
                ORDER BY open_time DESC 
                LIMIT {bars}
            """
            df = pd.read_sql(query, engine)
            
            if df.empty:
                print(f"{datetime.now()} ⚠️ Brak danych historycznych w {table} dla {timestamp_str}")
                return pd.DataFrame()
            
            # Odwracamy kolejność: od najstarszej do najnowszej
            df = df[::-1].reset_index(drop=True)
            
            last_candle_time = df['open_time'].iloc[-1]
            print(f"{datetime.now()} ✅ Pobrano {len(df)} świec historycznych z {table}")
            print(f"{datetime.now()} 📅 Ostatnia świeca: {last_candle_time}")
            
            return df
            
        except SQLAlchemyError as e:
            print(f"{datetime.now()} ❌ Błąd podczas pobierania danych historycznych z {table}: {e}")
            return pd.DataFrame()
    
    def check_open_position(self, symbol: str) -> dict:
        """
        Sprawdza czy istnieje otwarta pozycja dla danego symbolu.
        
        Args:
            symbol: Symbol waluty (np. 'BNBUSDT')
        
        Returns:
            Słownik z danymi pozycji lub None jeśli brak otwartej pozycji
        """
        try:
            engine = self.get_engine()
            query = f"""
                SELECT * FROM {self.trades_table} 
                WHERE symbol = '{symbol}' AND position_status = 'OPEN' 
                ORDER BY buy_time DESC LIMIT 1
            """
            df = pd.read_sql(query, engine)
            
            if df.empty:
                return None
            
            return df.iloc[0].to_dict()
            
        except SQLAlchemyError as e:
            print(f"{datetime.now()} ❌ Błąd sprawdzania pozycji dla {symbol}: {e}")
            return None
    
    def recent_loss(self, symbol: str, strategy_name: str, since_bars: int) -> bool:
        """
        Sprawdza czy była strata w ostatnich N zamkniętych transakcjach.
        
        Args:
            symbol: Symbol waluty
            strategy_name: Nazwa strategii
            since_bars: Liczba ostatnich transakcji do sprawdzenia
        
        Returns:
            True jeśli była strata, False w przeciwnym razie
        """
        try:
            engine = self.get_engine()
            query = f"""
                SELECT * FROM {self.trades_table} 
                WHERE symbol = '{symbol}' 
                  AND strategy_name = '{strategy_name}'
                  AND position_status = 'CLOSED'
                ORDER BY sell_time DESC LIMIT {since_bars}
            """
            df = pd.read_sql(query, engine)
            
            if df.empty:
                return False
            
            # Sprawdzamy ostatnią transakcję
            last_trade = df.iloc[0]
            return last_trade['profit_loss_perc'] < 0
            
        except SQLAlchemyError as e:
            print(f"{datetime.now()} ❌ Błąd sprawdzania strat dla {symbol}: {e}")
            return False
    
    def insert_trade(self, symbol: str, strategy_name: str, buy_price: float, 
                     buy_time: datetime, quantity: float) -> int:
        """
        Dodaje nową transakcję do bazy danych.
        
        Args:
            symbol: Symbol waluty
            strategy_name: Nazwa strategii
            buy_price: Cena kupna
            buy_time: Czas kupna
            quantity: Ilość zakupionej waluty
        
        Returns:
            ID nowo utworzonego rekordu
        """
        try:
            engine = self.get_engine()
            sql = text(f"""
                INSERT INTO {self.trades_table} 
                (symbol, strategy_name, buy_time, buy_price, quantity, position_status)
                VALUES (:symbol, :strategy_name, :buy_time, :buy_price, :quantity, 'OPEN')
            """)
            
            with engine.begin() as conn:
                result = conn.execute(sql, {
                    'symbol': symbol,
                    'strategy_name': strategy_name,
                    'buy_time': buy_time,
                    'buy_price': buy_price,
                    'quantity': quantity
                })
                trade_id = result.lastrowid
            
            print(f"{datetime.now()} ✅ Transakcja zapisana w bazie: ID={trade_id}")
            return trade_id
            
        except SQLAlchemyError as e:
            print(f"{datetime.now()} ❌ Błąd zapisu transakcji: {e}")
            return None
    
    def update_trade(self, trade_id: int, sell_price: float, 
                     sell_time: datetime, profit_perc: float):
        """
        Aktualizuje transakcję po sprzedaży.
        
        Args:
            trade_id: ID transakcji w bazie
            sell_price: Cena sprzedaży
            sell_time: Czas sprzedaży
            profit_perc: Procent zysku/straty
        """
        try:
            engine = self.get_engine()
            sql = text(f"""
                UPDATE {self.trades_table} 
                SET sell_price = :sell_price, 
                    sell_time = :sell_time, 
                    profit_loss_perc = :profit_perc, 
                    position_status = 'CLOSED'
                WHERE id = :trade_id
            """)
            
            with engine.begin() as conn:
                conn.execute(sql, {
                    'sell_price': sell_price,
                    'sell_time': sell_time,
                    'profit_perc': profit_perc,
                    'trade_id': trade_id
                })
            
            print(f"{datetime.now()} ✅ Transakcja zaktualizowana: ID={trade_id}, profit={profit_perc:.2f}%")
            
        except SQLAlchemyError as e:
            print(f"{datetime.now()} ❌ Błąd aktualizacji transakcji {trade_id}: {e}")
    
    def ensure_strategy_column(self):
        """
        Sprawdza i dodaje kolumnę strategy_name do tabeli transakcji jeśli nie istnieje.
        """
        try:
            engine = self.get_engine()
            
            # Sprawdzenie czy kolumna istnieje
            check_query = f"""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = '{self.config['database']}' 
                  AND TABLE_NAME = '{self.trades_table}' 
                  AND COLUMN_NAME = 'strategy_name'
            """
            
            with engine.connect() as conn:
                result = conn.execute(text(check_query))
                exists = result.fetchone() is not None
            
            if not exists:
                print(f"{datetime.now()} ⚠️ Kolumna strategy_name nie istnieje, dodaję...")
                alter_query = f"""
                    ALTER TABLE {self.trades_table} 
                    ADD COLUMN strategy_name VARCHAR(50) AFTER symbol
                """
                with engine.begin() as conn:
                    conn.execute(text(alter_query))
                print(f"{datetime.now()} ✅ Kolumna strategy_name dodana")
            else:
                print(f"{datetime.now()} ✅ Kolumna strategy_name już istnieje")
                
        except SQLAlchemyError as e:
            print(f"{datetime.now()} ❌ Błąd sprawdzania/dodawania kolumny strategy_name: {e}")
    
    def load_all_data_in_range(self, table: str, start_date: datetime, 
                               end_date: datetime) -> pd.DataFrame:
        """
        Pobiera wszystkie świece w zadanym zakresie dat.
        Używane do backtestingu - ładuje dane raz na początku (Sliding Window).
        
        Args:
            table: Nazwa tabeli ze świecami
            start_date: Data początkowa
            end_date: Data końcowa
        
        Returns:
            DataFrame ze wszystkimi świecami w zakresie, posortowany chronologicznie
        """
        try:
            engine = self.get_engine()
            
            # Konwersja dat do formatu MySQL
            start_str = start_date.strftime('%Y-%m-%d %H:%M:%S')
            end_str = end_date.strftime('%Y-%m-%d %H:%M:%S')
            
            query = f"""
                SELECT * FROM {table}
                WHERE open_time >= '{start_str}' 
                  AND open_time <= '{end_str}'
                ORDER BY open_time ASC
            """
            
            df = pd.read_sql(query, engine)
            
            if df.empty:
                print(f"{datetime.now()} ⚠️ Brak danych w {table} dla zakresu {start_str} → {end_str}")
                return pd.DataFrame()
            
            print(f"{datetime.now()} ✅ Załadowano {len(df)} świec z {table} ({start_date.date()} → {end_date.date()})")
            return df
            
        except SQLAlchemyError as e:
            print(f"{datetime.now()} ❌ Błąd ładowania danych z {table}: {e}")
            return pd.DataFrame()

