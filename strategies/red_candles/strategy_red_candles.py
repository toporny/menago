from ..falling_candles.strategy import Strategy
import pandas as pd
from datetime import datetime


class RedCandlesSequenceStrategy(Strategy):
    """
    Strategia "Red Candles Sequence (with stagnation exit)" z PineScript v6.
    
    Parametry z PineScript:
    - barsCount: 5 (liczba świeczek w sekwencji)
    - totalDropPerc: 5.0% (minimalny spadek w całej sekwencji)
    - tpPerc: 5.0% (Take Profit)
    - slPerc: 50.0% (Stop Loss)
    - stagnationBars: 60 (maksymalna liczba świec do trzymania pozycji)
    
    Logika:
    - Kupno: Wykrycie sekwencji N spadkowych świec z minimalnym spadkiem X%,
             następnie pierwsza świeca rosnąca (bodyMid(0) > bodyMid(1))
    - Sprzedaż: TP/SL lub wymuszenie po 60 świecach (stagnacja)
    
    Kluczowa różnica: Ta strategia używa "body mid" = (open + close) / 2
    zamiast samego close.
    """
    
    def __init__(self, symbol: str, params: dict, strategy_id: str = None):
        super().__init__(symbol, params, strategy_id)
        
        # Parametry strategii (zgodne z PineScript)
        self.barsCount = params.get('barsCount', 5)
        self.totalDropPerc = params.get('totalDropPerc', 5.0)
        self.tpPerc = params.get('tpPerc', 5.0)
        self.slPerc = params.get('slPerc', 50.0)
        self.stagnationBars = params.get('stagnationBars', 60)
    
    def _body_mid(self, df: pd.DataFrame, index: int) -> float:
        """
        Oblicza środek body świecy: (open + close) / 2
        
        Args:
            df: DataFrame ze świecami
            index: Indeks świecy (ujemny, od końca)
        
        Returns:
            Średnia z open i close
        """
        return (df['open'].iloc[index] + df['close'].iloc[index]) / 2
    
    def check_buy_signal(self, df: pd.DataFrame) -> bool:
        """
        Sygnał kupna:
        1. Sekwencja N spadkowych świec (bodyMid(i) < bodyMid(i+1))
        2. Całkowity spadek >= totalDropPerc%
        3. Obecna świeca rosnąca: bodyMid(0) > bodyMid(1)
        
        W PineScript:
        fallingSequence := true
        for i = 1 to barsCount
            fallingSequence := fallingSequence and (bodyMid(i) < bodyMid(i + 1))
        
        firstMid = bodyMid(barsCount)
        lastMid  = bodyMid(1)
        sequenceDrop = (firstMid - lastMid) / firstMid * 100
        dropCondition = sequenceDrop >= totalDropPerc
        
        buySignal = fallingSequence and dropCondition and bodyMid(0) > bodyMid(1)
        """
        if len(df) < self.barsCount + 2:
            return False
        
        # 1. Sprawdzenie sekwencji spadkowej
        falling_sequence = True
        for i in range(1, self.barsCount + 1):
            # bodyMid(i) < bodyMid(i + 1)
            # W Pythonie: iloc[-i] to i-ta świeca od końca
            mid_curr = self._body_mid(df, -i)
            mid_prev = self._body_mid(df, -i - 1)
            
            if not (mid_curr < mid_prev):
                falling_sequence = False
                break
        
        if not falling_sequence:
            return False
        
        # 2. Sprawdzenie całkowitego spadku
        first_mid = self._body_mid(df, -self.barsCount)  # bodyMid(barsCount)
        last_mid = self._body_mid(df, -1)  # bodyMid(1)
        
        sequence_drop = (first_mid - last_mid) / first_mid * 100
        
        if sequence_drop < self.totalDropPerc:
            return False
        
        # 3. Sprawdzenie czy obecna świeca jest rosnąca
        # bodyMid(0) > bodyMid(1)
        mid_current = self._body_mid(df, -1)  # Ostatnia zamknięta świeca (bodyMid(0) w PineScript)
        mid_previous = self._body_mid(df, -2)  # Poprzednia (bodyMid(1) w PineScript)
        
        # UWAGA: W PineScript bodyMid(0) to BIEŻĄCA świeca, ale w backtestingu
        # używamy ostatniej ZAMKNIĘTEJ świecy, więc porównujemy -1 z -2
        if mid_current <= mid_previous:
            return False
        
        return True
    
    def check_sell_signal(self, df: pd.DataFrame, position) -> tuple[bool, str]:
        """
        Sprawdza warunki sprzedaży:
        1. Take Profit (5%)
        2. Stop Loss (50%)
        3. Stagnacja (60 świec bez ruchu)
        
        W PineScript:
        strategy.exit(
            "TP/SL",
            from_entry = "LONG",
            limit = entryPrice * (1 + tpPerc / 100),
            stop  = entryPrice * (1 - slPerc / 100)
        )
        
        if bar_index - entryBarIndex >= stagnationBars
            strategy.close("LONG", comment="Stagnation exit")
        """
        current_price = df['close'].iloc[-1]
        
        # === TAKE PROFIT ===
        tp_price = self.get_take_profit(position.entry_price)
        if current_price >= tp_price:
            return True, "TAKE_PROFIT"
        
        # === STOP LOSS ===
        sl_price = self.get_stop_loss(position.entry_price)
        if current_price <= sl_price:
            return True, "STOP_LOSS"
        
        # === STAGNACJA ===
        # Sprawdzamy ile świec minęło od wejścia
        # W position przechowujemy entry_bar_index
        if hasattr(position, 'entry_bar_index'):
            current_bar_index = len(df) - 1
            bars_held = current_bar_index - position.entry_bar_index
            
            if bars_held >= self.stagnationBars:
                return True, "STAGNATION"
        
        return False, ""
    
    def get_stop_loss(self, entry_price: float) -> float:
        """
        Zwraca cenę stop loss (50%).
        W PineScript: stop = entryPrice * (1 - slPerc / 100)
        """
        return entry_price * (1 - self.slPerc / 100)
    
    def get_take_profit(self, entry_price: float) -> float:
        """
        Zwraca cenę take profit (5%).
        W PineScript: limit = entryPrice * (1 + tpPerc / 100)
        """
        return entry_price * (1 + self.tpPerc / 100)
