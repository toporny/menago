# Jak dodać nową strategię z TradingView (PineScript)

Ten dokument wyjaśnia jak przekonwertować strategię z TradingView (PineScript v6) na Python i zintegrować ją z botem tradingowym.

## Krok 1: Przygotowanie pliku strategii

Utwórz nowy plik w katalogu projektu, np. `strategy_moja_strategia.py`.

## Krok 2: Import i dziedziczenie

Zaimportuj klasę bazową `Strategy` i utwórz nową klasę dziedziczącą po niej:

```python
from strategy import Strategy
import pandas as pd
from datetime import datetime


class MojaStrategia(Strategy):
    """
    Opis strategii - co robi, jakie sygnały generuje.
    
    Parametry:
    - parametr1: opis (domyślnie wartość)
    - parametr2: opis (domyślnie wartość)
    """
    
    def __init__(self, symbol: str, params: dict):
        super().__init__(symbol, params)
        
        # Wczytanie parametrów z domyślnymi wartościami
        self.parametr1 = params.get('parametr1', wartość_domyślna)
        self.parametr2 = params.get('parametr2', wartość_domyślna)
```

## Krok 3: Konwersja logiki PineScript

### 3.1 Sygnał kupna - `check_buy_signal()`

W PineScript sygnał kupna to zazwyczaj warunek logiczny:

```pinescript
buy_signal = warunek1 and warunek2 and warunek3
if buy_signal
    strategy.entry("Long", strategy.long)
```

W Pythonie:

```python
def check_buy_signal(self, df: pd.DataFrame) -> bool:
    """Sprawdza warunki kupna."""
    if len(df) < minimalna_liczba_świec:
        return False
    
    # Konwersja warunków z PineScript
    warunek1 = ...  # np. df['close'].iloc[-1] > df['sma_20'].iloc[-1]
    warunek2 = ...
    warunek3 = ...
    
    return warunek1 and warunek2 and warunek3
```

### 3.2 Sygnał sprzedaży - `check_sell_signal()`

W PineScript:

```pinescript
if strategy.position_size > 0
    if warunek_sprzedaży
        strategy.close("Long")
```

W Pythonie:

```python
def check_sell_signal(self, df: pd.DataFrame, position) -> tuple[bool, str]:
    """Sprawdza warunki sprzedaży."""
    current_price = df['close'].iloc[-1]
    
    # Stop Loss
    sl_price = self.get_stop_loss(position.entry_price)
    if current_price <= sl_price:
        return True, "STOP_LOSS"
    
    # Take Profit lub inne warunki
    if warunek_sprzedaży:
        return True, "TAKE_PROFIT"
    
    return False, ""
```

### 3.3 Stop Loss i Take Profit

```python
def get_stop_loss(self, entry_price: float) -> float:
    """Zwraca cenę stop loss."""
    return entry_price * (1 - self.stop_loss_perc / 100)

def get_take_profit(self, entry_price: float) -> float:
    """Zwraca cenę take profit."""
    return entry_price * (1 + self.take_profit_perc / 100)
```

## Krok 4: Mapowanie typowych konstrukcji PineScript -> Python

### Dostęp do danych świec

| PineScript | Python (pandas) |
|------------|-----------------|
| `close` | `df['close'].iloc[-1]` |
| `close[1]` | `df['close'].iloc[-2]` |
| `open` | `df['open'].iloc[-1]` |
| `high` | `df['high'].iloc[-1]` |
| `low` | `df['low'].iloc[-1]` |
| `volume` | `df['volume'].iloc[-1]` |

### Pętle

PineScript:
```pinescript
for i = 1 to 10
    wartość = close[i]
```

Python:
```python
for i in range(1, 11):
    wartość = df['close'].iloc[-i]
```

### Zmienne stanu (var)

PineScript:
```pinescript
var int licznik = 0
licznik += 1
```

Python - używamy atrybutów obiektu `position`:
```python
# W check_sell_signal():
if not hasattr(position, 'licznik'):
    position.licznik = 0
position.licznik += 1
```

### Wskaźniki techniczne

Jeśli używasz wskaźników (SMA, RSI, MACD), musisz je obliczyć w Pythonie:

```python
# Przykład: SMA
df['sma_20'] = df['close'].rolling(window=20).mean()

# Przykład: RSI (wymaga biblioteki ta-lib lub pandas_ta)
import pandas_ta as ta
df['rsi'] = ta.rsi(df['close'], length=14)
```

## Krok 5: Dodanie strategii do config.json

```json
{
  "currencies": [
    {
      "symbol": "BTCUSDT",
      "table": "btcusdt_1h",
      "strategy": "MojaStrategia",
      "buy_quantity": 0.001,
      "enabled": true,
      "params": {
        "parametr1": wartość,
        "parametr2": wartość
      }
    }
  ]
}
```

## Krok 6: Rejestracja strategii w TradingBot

W pliku `sandbox_binance_new.py`, w metodzie `_load_strategies()`, dodaj swoją strategię do słownika:

```python
from strategy_moja_strategia import MojaStrategia

# W metodzie _load_strategies():
strategy_classes = {
    'FallingCandlesStrategy': FallingCandlesStrategy,
    'XRPPineScriptStrategy': XRPPineScriptStrategy,
    'MojaStrategia': MojaStrategia,  # <-- DODAJ TU
}
```

## Przykład kompletnej konwersji

Zobacz plik `strategy_xrp_pinescript.py` jako przykład pełnej konwersji strategii z PineScript v6 do Pythona.

Strategia ta zawiera:
- ✅ Wykrywanie spadkowych świec z opcjonalnym zaburzeniem
- ✅ Blokadę kupna po stracie
- ✅ Sztywny Stop Loss
- ✅ Śledzony Take Profit z liczeniem czerwonych świec

## Testowanie strategii

1. Ustaw `enabled: false` dla innych strategii w `config.json`
2. Uruchom bota: `python sandbox_binance_new.py`
3. Sprawdź logi czy strategia działa poprawnie
4. Zweryfikuj transakcje w bazie danych

## Wskazówki

- **Zachowaj komentarze** - dodaj komentarze z oryginalnym kodem PineScript dla łatwiejszego debugowania
- **Testuj na małych kwotach** - zawsze najpierw testuj na Binance Testnet
- **Loguj decyzje** - dodaj `print()` w kluczowych momentach strategii
- **Sprawdź dane** - upewnij się że tabela w MySQL ma wystarczająco dużo świec
