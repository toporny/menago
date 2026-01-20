from ..falling_candles.strategy import Strategy
import pandas as pd
from datetime import datetime


class DOGEPineScriptStrategy(Strategy):
    """
    Strategia dla DOGEUSDT przetłumaczona z PineScript v6.
    
    Logika:
    - Kupno: Sekwencja opadających świeczek + silna czerwona świeczka + trend MA spadkowy
             + cena poniżej MA20 + dynamiczny stop loss
    - Dynamiczny Stop Loss: obliczany na podstawie spadku w sekwencji świeczek
    - Take Profit: tryb obserwacji po osiągnięciu progu zysku
    - Szybka sprzedaż w trybie obserwacji:
      * N czerwonych świeczek powyżej MA20
      * Środek korpusu poniżej ceny wejścia
      * MA10 przecina MA50 w dół
    
    Parametry:
    - candle_count: liczba opadających świeczek (domyślnie 6)
    - price_below_ma20_pct: procent poniżej MA20 dla ceny (domyślnie 2.0)
    - min_red_body_pct: minimalny spadek czerwonej świecy (domyślnie 2.0)
    - profit_trigger_pct: procent zysku do aktywacji trybu obserwacji (domyślnie 2.0)
    - stop_loss_multiplier: mnożnik stop lossa (domyślnie 1.0)
    - red_candle_count_trigger: czerwone świece do szybkiej sprzedaży (domyślnie 2)
    - red_candle_above_ma20_pct: pierwsza czerwona > MA20 (%) (domyślnie 1.0)
    """
    
    def __init__(self, symbol: str, params: dict, strategy_id: str = None):
        super().__init__(symbol, params, strategy_id)
        
        # Parametry strategii (zgodne z PineScript)
        self.candle_count = params.get('candle_count', 6)
        self.price_below_ma20_pct = params.get('price_below_ma20_pct', 2.0)
        self.min_red_body_pct = params.get('min_red_body_pct', 2.0)
        self.profit_trigger_pct = params.get('profit_trigger_pct', 2.0)
        self.stop_loss_multiplier = params.get('stop_loss_multiplier', 1.0)
        self.red_candle_count_trigger = params.get('red_candle_count_trigger', 2)
        self.red_candle_above_ma20_pct = params.get('red_candle_above_ma20_pct', 1.0)
        self.require_ma_trend = params.get('require_ma_trend', True)  # Czy wymagać trendu MA
        
        # Zmienne stanu dla pozycji (będą przechowywane w obiekcie position)
        # - observer_active: czy tryb obserwacji jest aktywny
        # - red_candle_streak: licznik czerwonych świeczek
        # - first_red_candle_mid: środek korpusu pierwszej czerwonej świeczki
        # - trade_stop_loss_pct: procent stop lossa dla danej transakcji
    
    def _calculate_ma(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Oblicza prostą średnią kroczącą (SMA)."""
        return df['close'].rolling(window=period).mean()
    
    def _body_mid(self, df: pd.DataFrame, bar: int = 0) -> float:
        """
        Zwraca środek korpusu świecy.
        bar=0 to ostatnia świeca, bar=1 to przedostatnia, itd.
        """
        idx = -(bar + 1)
        return (df['open'].iloc[idx] + df['close'].iloc[idx]) / 2
    
    def _is_red(self, df: pd.DataFrame, bar: int = 0) -> bool:
        """Sprawdza czy świeca jest czerwona (close < open)."""
        idx = -(bar + 1)
        return df['close'].iloc[idx] < df['open'].iloc[idx]
    
    def _is_strong_red(self, df: pd.DataFrame, bar: int = 0) -> bool:
        """
        Sprawdza czy świeca jest silnie czerwona.
        Silnie czerwona = czerwona + spadek >= min_red_body_pct
        """
        idx = -(bar + 1)
        if not self._is_red(df, bar):
            return False
        
        open_price = df['open'].iloc[idx]
        close_price = df['close'].iloc[idx]
        drop_pct = (open_price - close_price) / open_price
        
        return drop_pct >= (self.min_red_body_pct / 100)
    
    def _check_falling_sequence(self, df: pd.DataFrame) -> bool:
        """
        Sprawdza czy ostatnie candle_count świeczek tworzy opadającą sekwencję.
        Opadająca = body_mid(i) < body_mid(i+1) dla wszystkich i
        """
        for i in range(self.candle_count - 1):
            if self._body_mid(df, i) >= self._body_mid(df, i + 1):
                return False
        return True
    
    def _check_strong_red_exists(self, df: pd.DataFrame) -> bool:
        """
        Sprawdza czy w ostatnich candle_count świeczkach jest przynajmniej jedna silnie czerwona.
        """
        for i in range(self.candle_count):
            if self._is_strong_red(df, i):
                return True
        return False
    
    def _check_ma_trend_down(self, df: pd.DataFrame) -> bool:
        """
        Sprawdza czy trend MA jest spadkowy: MA20 < MA50 < MA100 < MA200
        """
        if len(df) < 200:
            return False
        
        ma20 = self._calculate_ma(df, 20).iloc[-1]
        ma50 = self._calculate_ma(df, 50).iloc[-1]
        ma100 = self._calculate_ma(df, 100).iloc[-1]
        ma200 = self._calculate_ma(df, 200).iloc[-1]
        
        return ma20 < ma50 < ma100 < ma200
    
    def _calculate_dynamic_stop_loss_pct(self, df: pd.DataFrame) -> float:
        """
        Oblicza dynamiczny procent stop lossa na podstawie spadku w sekwencji.
        
        Returns:
            Procent stop lossa (np. 0.05 dla 5%) lub None jeśli nieprawidłowy
        """
        mid_start = self._body_mid(df, self.candle_count - 1)  # pierwsza świeca sekwencji
        mid_end = self._body_mid(df, 0)  # ostatnia świeca sekwencji
        
        fall_drop_pct = (mid_start - mid_end) / mid_start
        stop_loss_pct = fall_drop_pct * self.stop_loss_multiplier
        
        # Walidacja: stop loss musi być > 0 i < 50%
        if stop_loss_pct > 0 and stop_loss_pct < 0.5:
            return stop_loss_pct
        
        return None
    
    def check_buy_signal(self, df: pd.DataFrame) -> bool:
        """
        Sygnał kupna:
        1. Opadająca sekwencja świeczek
        2. Przynajmniej jedna silnie czerwona świeczka w sekwencji
        3. Trend MA spadkowy (MA20 < MA50 < MA100 < MA200)
        4. Cena poniżej MA20 o price_below_ma20_pct
        5. Prawidłowy dynamiczny stop loss
        
        W PineScript:
        buyCondition = inDateRange and fallingSequence and strongRedExists and 
                       maTrendDown and priceCondition and validStopLoss and 
                       strategy.position_size == 0
        """
        # Sprawdzenie czy mamy wystarczająco danych
        if len(df) < max(200, self.candle_count + 2):
            return False
        
        # 1. Opadająca sekwencja
        if not self._check_falling_sequence(df):
            return False
        
        # 2. Silna czerwona świeczka
        if not self._check_strong_red_exists(df):
            return False
        
        # 3. Trend MA spadkowy (opcjonalny)
        if self.require_ma_trend and not self._check_ma_trend_down(df):
            return False
        
        # 4. Cena poniżej MA20
        ma20 = self._calculate_ma(df, 20).iloc[-1]
        current_close = df['close'].iloc[-1]
        price_threshold = ma20 * (1 - self.price_below_ma20_pct / 100)
        
        if current_close >= price_threshold:
            return False
        
        # 5. Prawidłowy dynamiczny stop loss
        stop_loss_pct = self._calculate_dynamic_stop_loss_pct(df)
        if stop_loss_pct is None:
            return False
        
        # Zapisujemy stop loss dla tej transakcji (będzie użyty w get_stop_loss)
        # To będzie przechowywane w position.trade_stop_loss_pct
        self._current_stop_loss_pct = stop_loss_pct
        
        return True
    
    def check_sell_signal(self, df: pd.DataFrame, position) -> tuple[bool, str]:
        """
        Sprawdza warunki sprzedaży:
        1. Stop Loss (dynamiczny)
        2. Tryb obserwacji po osiągnięciu profit_trigger_pct
        3. Szybka sprzedaż w trybie obserwacji:
           - N czerwonych świeczek powyżej MA20
           - Środek korpusu poniżej ceny wejścia
           - MA10 przecina MA50 w dół
        
        W PineScript:
        - SL: strategy.exit("SL", from_entry="BUY", stop=entryPrice * (1 - tradeStopLossPct))
        - Observer: aktywacja gdy close >= entryPrice * (1 + profitTriggerPct)
        - Szybka sprzedaż: różne warunki w trybie obserwacji
        """
        current_price = df['close'].iloc[-1]
        
        # === STOP LOSS (dynamiczny) ===
        sl_price = self.get_stop_loss(position.entry_price)
        if current_price <= sl_price:
            return True, "STOP_LOSS"
        
        # === TRYB OBSERWACJI ===
        # Inicjalizacja atrybutów jeśli nie istnieją
        if not hasattr(position, 'observer_active'):
            position.observer_active = False
            position.red_candle_streak = 0
            position.first_red_candle_mid = None
        
        # Aktywacja trybu obserwacji
        profit_trigger_price = position.entry_price * (1 + self.profit_trigger_pct / 100)
        if not position.observer_active and current_price >= profit_trigger_price:
            position.observer_active = True
            position.red_candle_streak = 0
            position.first_red_candle_mid = None
            print(f"{datetime.now()} 🟡 {self.symbol} Tryb obserwacji aktywowany przy {current_price}")
        
        # === SZYBKA SPRZEDAŻ W TRYBIE OBSERWACJI ===
        if position.observer_active:
            # Liczenie czerwonych świeczek
            if self._is_red(df, 0):
                position.red_candle_streak += 1
                if position.first_red_candle_mid is None:
                    position.first_red_candle_mid = self._body_mid(df, 0)
            else:
                # Zielona świeczka - reset
                position.red_candle_streak = 0
                position.first_red_candle_mid = None
            
            # Warunek 1: N czerwonych świeczek + pierwsza powyżej MA20
            if position.red_candle_streak >= self.red_candle_count_trigger:
                ma20 = self._calculate_ma(df, 20).iloc[-1]
                ma20_threshold = ma20 * (1 + self.red_candle_above_ma20_pct / 100)
                
                if position.first_red_candle_mid is not None and position.first_red_candle_mid > ma20_threshold:
                    return True, "OBSERVER_RED_STREAK"
            
            # Warunek 2: Środek korpusu poniżej ceny wejścia
            if self._body_mid(df, 0) < position.entry_price:
                return True, "OBSERVER_BODY_BELOW_ENTRY"
            
            # Warunek 3: MA10 przecina MA50 w dół
            if len(df) >= 50:
                ma10_curr = self._calculate_ma(df, 10).iloc[-1]
                ma50_curr = self._calculate_ma(df, 50).iloc[-1]
                ma10_prev = self._calculate_ma(df, 10).iloc[-2]
                ma50_prev = self._calculate_ma(df, 50).iloc[-2]
                
                # Przecięcie w dół: poprzednio MA10 > MA50, teraz MA10 < MA50
                if ma10_prev > ma50_prev and ma10_curr < ma50_curr:
                    return True, "OBSERVER_MA_CROSS"
        
        return False, ""
    
    def get_stop_loss(self, entry_price: float) -> float:
        """
        Zwraca cenę stop loss.
        Używa dynamicznego stop lossa obliczonego podczas sygnału kupna.
        
        W PineScript: stop = entryPrice * (1 - tradeStopLossPct)
        """
        # Pobieramy stop loss z pozycji (jeśli istnieje)
        # W przeciwnym razie używamy ostatnio obliczonego
        if hasattr(self, '_current_stop_loss_pct'):
            stop_loss_pct = self._current_stop_loss_pct
        else:
            # Fallback - domyślny 5%
            stop_loss_pct = 0.05
        
        return entry_price * (1 - stop_loss_pct)
    
    def get_take_profit(self, entry_price: float) -> float:
        """
        Zwraca cenę aktywacji trybu obserwacji.
        
        W PineScript: entryPrice * (1 + profitTriggerPct)
        """
        return entry_price * (1 + self.profit_trigger_pct / 100)
