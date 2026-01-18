from ..falling_candles.strategy import Strategy
import pandas as pd
from datetime import datetime


class XRPPineScriptStrategy(Strategy):
    """
    Strategia dla XRPUSDT przetłumaczona z PineScript v6.
    
    Logika:
    - Kupno: 6 spadkowych świeczek (z opcjonalnym 1 zaburzeniem)
    - Blokada kupna po stracie w ostatnich X świeczkach
    - Stop Loss: sztywny procent
    - Take Profit: śledzony - aktywuje się po osiągnięciu progu, 
      następnie czeka na N czerwonych świeczek przed sprzedażą
    
    Parametry:
    - num_falling: liczba spadkowych świeczek (domyślnie 6)
    - allow_one_break: pozwól jedną zaburzającą świeczkę (domyślnie True)
    - take_profit_perc: procent TP do aktywacji śledzenia (domyślnie 12.0)
    - stop_loss_perc: procent stop loss (domyślnie 5.0)
    - red_candles_to_sell: ilość czerwonych świeczek do sprzedaży po TP (domyślnie 3)
    - loss_lookback_bars: ilość świeczek do blokady kupna po stracie (domyślnie 1)
    """
    
    def __init__(self, symbol: str, params: dict, strategy_id: str = None):
        super().__init__(symbol, params, strategy_id)
        
        # Parametry strategii (zgodne z PineScript)
        self.num_falling = params.get('num_falling', 6)
        self.allow_one_break = params.get('allow_one_break', True)
        self.take_profit_perc = params.get('take_profit_perc', 12.0)
        self.stop_loss_perc = params.get('stop_loss_perc', 5.0)
        self.red_candles_to_sell = params.get('red_candles_to_sell', 3)
        self.loss_lookback_bars = params.get('loss_lookback_bars', 1)
    
    def check_buy_signal(self, df: pd.DataFrame) -> bool:
        """
        Sygnał kupna:
        1. Wykrycie num_falling spadkowych świeczek (z opcjonalnym zaburzeniem)
        2. Brak straty w ostatnich loss_lookback_bars świeczkach
        
        W PineScript:
        buy_signal = f_check_falling(num_falling, allow_one_break) and in_date_range and not recent_loss
        """
        if len(df) < self.num_falling + 2:
            return False
        
        # Sprawdzenie spadkowych świeczek
        falling_ok = self._f_check_falling(df, self.num_falling, self.allow_one_break)
        
        if not falling_ok:
            return False
        
        # Sprawdzenie czy nie było niedawnej straty
        # (to będzie sprawdzane w TradingBot przez DatabaseManager)
        return True
    
    def _f_check_falling(self, df: pd.DataFrame, num: int, allow_break: bool) -> bool:
        """
        Funkcja f_check_falling z PineScript.
        
        Sprawdza czy ostatnie 'num' świeczek jest spadkowych.
        Spadek = średnia (open+close)/2 obecnej świecy < średnia poprzedniej.
        
        Jeśli allow_break=True, pozwala na jedną zaburzającą świeczkę.
        """
        falling_count = 0
        break_used = False
        
        # Iterujemy od najnowszej świecy wstecz
        # W PineScript: for i = 1 to num + (allow_break ? 1 : 0)
        max_iterations = num + (1 if allow_break else 0)
        
        for i in range(1, max_iterations + 1):
            if i + 1 >= len(df):
                break
            
            # mid_curr = (open[i] + close[i]) / 2
            mid_curr = (df['open'].iloc[-i] + df['close'].iloc[-i]) / 2
            # mid_prev = (open[i + 1] + close[i + 1]) / 2
            mid_prev = (df['open'].iloc[-i-1] + df['close'].iloc[-i-1]) / 2
            
            if mid_curr < mid_prev:
                falling_count += 1
            else:
                # Nie jest spadkowa
                if allow_break and not break_used:
                    break_used = True
                else:
                    # Brak możliwości zaburzenia - resetujemy
                    falling_count = 0
                    break
        
        return falling_count >= num
    
    def check_sell_signal(self, df: pd.DataFrame, position) -> tuple[bool, str]:
        """
        Sprawdza warunki sprzedaży:
        1. Stop Loss (sztywny)
        2. Take Profit (śledzony przez czerwone świeczki)
        
        W PineScript:
        - SL: strategy.exit("SL", from_entry="Long", stop=sl_price)
        - TP: aktywacja gdy high >= tp_trigger_price, następnie liczenie czerwonych świec
        """
        current_price = df['close'].iloc[-1]
        current_high = df['high'].iloc[-1]
        
        # === STOP LOSS (sztywny) ===
        sl_price = self.get_stop_loss(position.entry_price)
        if current_price <= sl_price:
            return True, "STOP_LOSS"
        
        # === TAKE PROFIT (śledzony) ===
        tp_trigger_price = self.get_take_profit(position.entry_price)
        
        # Aktywacja TP (wystarczy dotknięcie HIGH)
        # W PineScript: if not tp_tracking and high >= tp_trigger_price
        if not position.tp_tracking and current_high >= tp_trigger_price:
            position.tp_tracking = True
            position.red_count = 0
            print(f"{datetime.now()} 🟡 {self.symbol} TP aktywowany przy high={current_high}")
        
        # Jeśli TP aktywny – liczymy czerwone świeczki
        if position.tp_tracking:
            last_candle = df.iloc[-1]
            
            # Czerwona świeczka: close < open
            if last_candle['close'] < last_candle['open']:
                position.red_count += 1
            else:
                # Zielona/doji - resetujemy licznik
                position.red_count = 0
            
            # Sprzedaż po N czerwonych świeczkach
            if position.red_count >= self.red_candles_to_sell:
                return True, "TAKE_PROFIT"
        
        return False, ""
    
    def get_stop_loss(self, entry_price: float) -> float:
        """
        Zwraca cenę stop loss.
        W PineScript: sl_price = entry_price * (1 - stop_loss_perc / 100)
        """
        return entry_price * (1 - self.stop_loss_perc / 100)
    
    def get_take_profit(self, entry_price: float) -> float:
        """
        Zwraca cenę aktywacji take profit (trigger).
        W PineScript: tp_trigger_price = entry_price * (1 + take_profit_perc / 100)
        """
        return entry_price * (1 + self.take_profit_perc / 100)
