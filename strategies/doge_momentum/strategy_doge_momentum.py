from ..falling_candles.strategy import Strategy
import pandas as pd
import numpy as np
from datetime import datetime


class DOGEMomentumStrategy(Strategy):
    """
    ULEPSZONA Strategia DOGE Momentum Reversal v2.0
    
    Bazuje na analizie rzeczywistych danych DOGE 2025:
    - Małe świeczki (średnio 0.67%)
    - Niska volatility (std 0.995%)
    - Reversal po kapitulacji działa najlepiej
    
    ULEPSZENIA v2.0:
    - Dodano RSI oversold (< 35)
    - Lepszy R/R: 3% TP / 1.2% SL = 2.5:1
    - Wyższy próg volume (30% wzrost)
    - Cena musi być blisko lokalnego dołka
    - Silniejsze momentum reversal
    
    KUPNO:
    1. Seria 2-3 czerwonych świec (nie więcej - za dużo = trend)
    2. RSI < 35 (oversold)
    3. Cena poniżej MA20 (0.5-1%)
    4. Volume spike (30%+ wzrost)
    5. Cena blisko lokalnego dołka (5 ostatnich świec)
    6. Momentum reversal (ostatnia świeca słabsza)
    
    SPRZEDAŻ:
    - SL: 1.2% (dopasowane do volatility)
    - TP: 3% (realistyczne dla DOGE)
    - Trailing: 1.5% aktywacja, 0.8% trailing
    """
    
    def __init__(self, symbol: str, params: dict, strategy_id: str = None):
        super().__init__(symbol, params, strategy_id)
        
        # Parametry strategii (ulepszone wartości domyślne)
        self.red_candles_min = params.get('red_candles_min', 2)
        self.red_candles_max = params.get('red_candles_max', 3)  # Zmniejszone z 4 na 3
        self.price_below_ma20_pct = params.get('price_below_ma20_pct', 0.7)  # Zmniejszone z 1.0
        self.volume_increase_pct = params.get('volume_increase_pct', 30.0)  # Zwiększone z 20
        self.rsi_oversold = params.get('rsi_oversold', 35)  # NOWE
        self.stop_loss_pct = params.get('stop_loss_pct', 1.2)  # Zmniejszone z 1.5
        self.take_profit_pct = params.get('take_profit_pct', 3.0)  # Zmniejszone z 4.0
        self.trailing_activation_pct = params.get('trailing_activation_pct', 1.5)  # Zmniejszone z 2.0
        self.trailing_stop_pct = params.get('trailing_stop_pct', 0.8)  # Zmniejszone z 1.0
    
    def _calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> float:
        """Oblicza RSI (Relative Strength Index)."""
        if len(df) < period + 1:
            return 50  # Neutralny RSI
        
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
    
    def _is_red(self, df: pd.DataFrame, idx: int = -1) -> bool:
        """Sprawdza czy świeca jest czerwona."""
        return df['close'].iloc[idx] < df['open'].iloc[idx]
    
    def _count_recent_red_candles(self, df: pd.DataFrame, max_candles: int = 10) -> int:
        """Liczy ile ostatnich świec jest czerwonych (bez przerwy)."""
        count = 0
        for i in range(1, min(max_candles + 1, len(df))):
            if self._is_red(df, -i):
                count += 1
            else:
                break
        return count
    
    def _get_ma20(self, df: pd.DataFrame) -> float:
        """Pobiera MA20 z bazy lub oblicza."""
        if 'ma20' in df.columns and not pd.isna(df['ma20'].iloc[-1]):
            return df['ma20'].iloc[-1]
        return df['close'].rolling(20).mean().iloc[-1]
    
    def _get_volume_avg(self, df: pd.DataFrame, period: int = 20) -> float:
        """Oblicza średni volume."""
        if 'volume' not in df.columns:
            return 0
        return df['volume'].rolling(period).mean().iloc[-2]
    
    def _is_near_local_low(self, df: pd.DataFrame, lookback: int = 5) -> bool:
        """
        Sprawdza czy obecna cena jest blisko lokalnego dołka.
        Cena musi być w dolnych 30% zakresu ostatnich N świec.
        """
        if len(df) < lookback:
            return False
        
        recent_low = df['low'].iloc[-lookback:].min()
        recent_high = df['high'].iloc[-lookback:].max()
        current_price = df['close'].iloc[-1]
        
        range_size = recent_high - recent_low
        if range_size == 0:
            return False
        
        # Cena w dolnych 30% zakresu
        position_in_range = (current_price - recent_low) / range_size
        return position_in_range < 0.3
    
    def _check_momentum_reversal(self, df: pd.DataFrame) -> bool:
        """
        ULEPSZONE: Sprawdza czy momentum się odwraca.
        - Ostatnia świeca zielona = silny reversal
        - LUB ostatnia świeca czerwona ale znacznie słabsza (50% mniejszy spadek)
        """
        if len(df) < 3:
            return False
        
        # Ostatnia świeca zielona = silny reversal
        if not self._is_red(df, -1):
            return True
        
        # Ostatnia świeca czerwona ale słabsza
        last_drop = (df['open'].iloc[-1] - df['close'].iloc[-1]) / df['open'].iloc[-1]
        prev_drop = (df['open'].iloc[-2] - df['close'].iloc[-2]) / df['open'].iloc[-2]
        
        # Spadek musi być co najmniej 50% mniejszy
        return last_drop < prev_drop * 0.5
    
    def check_buy_signal(self, df: pd.DataFrame) -> bool:
        """
        ULEPSZONA logika kupna:
        1. Seria 2-3 czerwonych świec
        2. RSI < 35 (oversold)
        3. Cena poniżej MA20 (0.5-1%)
        4. Volume spike (30%+)
        5. Cena blisko lokalnego dołka
        6. Momentum reversal
        """
        if len(df) < 25:
            return False
        
        # 1. Seria czerwonych świec (2-3, nie więcej)
        red_count = self._count_recent_red_candles(df)
        if red_count < self.red_candles_min or red_count > self.red_candles_max:
            return False
        
        # 2. RSI oversold
        rsi = self._calculate_rsi(df)
        if rsi >= self.rsi_oversold:
            return False
        
        # 3. Cena poniżej MA20 (oversold)
        ma20 = self._get_ma20(df)
        current_price = df['close'].iloc[-1]
        price_threshold = ma20 * (1 - self.price_below_ma20_pct / 100)
        
        if current_price >= price_threshold:
            return False
        
        # 4. Volume spike (kapitulacja)
        if 'volume' in df.columns:
            current_volume = df['volume'].iloc[-1]
            avg_volume = self._get_volume_avg(df)
            
            if avg_volume > 0:
                volume_increase = ((current_volume - avg_volume) / avg_volume) * 100
                if volume_increase < self.volume_increase_pct:
                    return False
        
        # 5. Cena blisko lokalnego dołka
        if not self._is_near_local_low(df):
            return False
        
        # 6. Momentum reversal
        if not self._check_momentum_reversal(df):
            return False
        
        return True
    
    def check_sell_signal(self, df: pd.DataFrame, position) -> tuple[bool, str]:
        """
        Warunki sprzedaży:
        1. Stop Loss (1.2%)
        2. Take Profit (3%)
        3. Trailing Stop (aktywacja 1.5%, trailing 0.8%)
        """
        current_price = df['close'].iloc[-1]
        
        # === STOP LOSS ===
        sl_price = self.get_stop_loss(position.entry_price)
        if current_price <= sl_price:
            return True, "STOP_LOSS"
        
        # === TRAILING STOP ===
        if not hasattr(position, 'trailing_active'):
            position.trailing_active = False
            position.highest_price = position.entry_price
        
        if current_price > position.highest_price:
            position.highest_price = current_price
        
        trailing_activation_price = position.entry_price * (1 + self.trailing_activation_pct / 100)
        if not position.trailing_active and current_price >= trailing_activation_price:
            position.trailing_active = True
            print(f"{datetime.now()} 🟡 {self.symbol} Trailing stop aktywowany przy {current_price}")
        
        if position.trailing_active:
            trailing_stop_price = position.highest_price * (1 - self.trailing_stop_pct / 100)
            if current_price <= trailing_stop_price:
                return True, "TRAILING_STOP"
        
        # === TAKE PROFIT ===
        tp_price = self.get_take_profit(position.entry_price)
        if current_price >= tp_price:
            return True, "TAKE_PROFIT"
        
        return False, ""
    
    def get_stop_loss(self, entry_price: float) -> float:
        """Zwraca cenę stop loss."""
        return entry_price * (1 - self.stop_loss_pct / 100)
    
    def get_take_profit(self, entry_price: float) -> float:
        """Zwraca cenę take profit."""
        return entry_price * (1 + self.take_profit_pct / 100)
