from abc import ABC, abstractmethod
import pandas as pd
from datetime import datetime


class Strategy(ABC):
    """
    Klasa bazowa dla wszystkich strategii tradingowych.
    Każda strategia musi implementować metody sprawdzania sygnałów kupna/sprzedaży.
    """
    
    def __init__(self, symbol: str, params: dict, strategy_id: str = None):
        """
        Args:
            symbol: Symbol waluty (np. 'BNBUSDT')
            params: Słownik z parametrami strategii
            strategy_id: Unikalny identyfikator strategii (opcjonalny)
        """
        self.symbol = symbol
        self.params = params
        self.name = self.__class__.__name__
        # Jeśli nie podano strategy_id, użyj nazwy klasy
        self.strategy_id = strategy_id if strategy_id else self.name
    
    @abstractmethod
    def check_buy_signal(self, df: pd.DataFrame) -> bool:
        """
        Sprawdza czy są spełnione warunki kupna.
        
        Args:
            df: DataFrame z danymi świec (OHLCV)
        
        Returns:
            True jeśli sygnał kupna, False w przeciwnym razie
        """
        pass
    
    @abstractmethod
    def check_sell_signal(self, df: pd.DataFrame, position) -> tuple[bool, str]:
        """
        Sprawdza czy są spełnione warunki sprzedaży.
        
        Args:
            df: DataFrame z danymi świec (OHLCV)
            position: Obiekt Position z informacjami o pozycji
        
        Returns:
            (should_sell, reason) - tuple z decyzją i powodem
        """
        pass
    
    @abstractmethod
    def get_stop_loss(self, entry_price: float) -> float:
        """Zwraca cenę stop loss dla danej ceny wejścia."""
        pass
    
    @abstractmethod
    def get_take_profit(self, entry_price: float) -> float:
        """Zwraca cenę take profit dla danej ceny wejścia."""
        pass
    
    def __str__(self):
        return f"{self.strategy_id}({self.symbol})"


class FallingCandlesStrategy(Strategy):
    """
    Strategia oparta na spadających świecach.
    Kupuje gdy wykryje N kolejnych spadających świec (z opcjonalnym zaburzeniem).
    Sprzedaje przy SL lub po osiągnięciu TP i wystąpieniu M czerwonych świec.
    """
    
    def __init__(self, symbol: str, params: dict, strategy_id: str = None):
        super().__init__(symbol, params, strategy_id)
        
        # Parametry strategii z domyślnymi wartościami
        self.num_falling = params.get('num_falling', 6)
        self.allow_one_break = params.get('allow_one_break', True)
        self.take_profit_perc = params.get('take_profit_perc', 12.0)
        self.stop_loss_perc = params.get('stop_loss_perc', 5.0)
        self.red_candles_to_sell = params.get('red_candles_to_sell', 3)
        self.loss_lookback_bars = params.get('loss_lookback_bars', 1)
    
    def check_buy_signal(self, df: pd.DataFrame) -> bool:
        """
        Sprawdza czy jest N spadających świec (z opcjonalnym zaburzeniem).
        """
        if len(df) < self.num_falling + 2:
            return False
        
        return self._check_falling(df, self.num_falling, self.allow_one_break)
    
    def _check_falling(self, df: pd.DataFrame, num: int, allow_break: bool) -> bool:
        """
        Sprawdza czy ostatnie N świec jest spadkowych.
        Spadek = średnia (open+close)/2 obecnej świecy < średnia poprzedniej.
        """
        falling_count = 0
        break_used = False
        
        # Sprawdzamy od najnowszej świecy wstecz
        for i in range(1, num + (1 if allow_break else 0) + 1):
            if i >= len(df):
                return False
            
            mid_curr = (df['open'].iloc[-i] + df['close'].iloc[-i]) / 2
            mid_prev = (df['open'].iloc[-i-1] + df['close'].iloc[-i-1]) / 2
            
            if mid_curr < mid_prev:
                falling_count += 1
            else:
                if allow_break and not break_used:
                    break_used = True
                else:
                    return False
        
        return falling_count >= num
    
    def check_sell_signal(self, df: pd.DataFrame, position) -> tuple[bool, str]:
        """
        Sprawdza warunki sprzedaży:
        1. Stop Loss - cena spadła poniżej SL
        2. Take Profit - cena osiągnęła TP i pojawiły się czerwone świece
        """
        current_price = df['close'].iloc[-1]
        
        # STOP LOSS
        sl_price = self.get_stop_loss(position.entry_price)
        if current_price <= sl_price:
            return True, "STOP_LOSS"
        
        # TAKE PROFIT - aktywacja śledzenia
        tp_price = self.get_take_profit(position.entry_price)
        if not position.tp_tracking and current_price >= tp_price:
            position.tp_tracking = True
            position.red_count = 0
            print(f"{datetime.now()} 🟡 {self.symbol} TP aktywowany przy {current_price}")
        
        # TAKE PROFIT - liczenie czerwonych świec
        if position.tp_tracking:
            last_candle = df.iloc[-1]
            if last_candle['close'] < last_candle['open']:
                position.red_count += 1
            else:
                position.red_count = 0
            
            if position.red_count >= self.red_candles_to_sell:
                return True, "TAKE_PROFIT"
        
        return False, ""
    
    def get_stop_loss(self, entry_price: float) -> float:
        """Zwraca cenę stop loss."""
        return entry_price * (1 - self.stop_loss_perc / 100)
    
    def get_take_profit(self, entry_price: float) -> float:
        """Zwraca cenę take profit."""
        return entry_price * (1 + self.take_profit_perc / 100)
