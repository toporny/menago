# Jak Działa Sprawdzanie Strategii

## Spis treści
1. [Przegląd systemu](#przegląd-systemu)
2. [Architektura strategii](#architektura-strategii)
3. [Proces sprawdzania](#proces-sprawdzania)
4. [Przykłady strategii](#przykłady-strategii)
5. [Przepływ danych](#przepływ-danych)

---

## Przegląd systemu

System tradingowy działa w cyklu sprawdzania strategii dla różnych kryptowalut. Każda strategia analizuje dane świec (candlestick) i podejmuje decyzje o kupnie lub sprzedaży.

### Główne komponenty:
- **TradingBot** - główny silnik zarządzający strategiami
- **Strategy (klasa bazowa)** - abstrakcyjna klasa definiująca interfejs strategii
- **Konkretne strategie** - implementacje różnych algorytmów tradingowych
- **DatabaseManager** - dostęp do danych historycznych świec

---

## Architektura strategii

### Klasa bazowa `Strategy`

Każda strategia dziedziczy po klasie `Strategy` i musi zaimplementować 4 metody abstrakcyjne:

```python
class Strategy(ABC):
    @abstractmethod
    def check_buy_signal(self, df: pd.DataFrame) -> bool:
        """Sprawdza czy są spełnione warunki kupna"""
        pass
    
    @abstractmethod
    def check_sell_signal(self, df: pd.DataFrame, position) -> tuple[bool, str]:
        """Sprawdza czy są spełnione warunki sprzedaży"""
        pass
    
    @abstractmethod
    def get_stop_loss(self, entry_price: float) -> float:
        """Zwraca cenę stop loss"""
        pass
    
    @abstractmethod
    def get_take_profit(self, entry_price: float) -> float:
        """Zwraca cenę take profit"""
        pass
```

### Parametry strategii

Każda strategia otrzymuje przy inicjalizacji:
- **symbol** - symbol waluty (np. "BNBUSDT")
- **params** - słownik z parametrami (z config.json)
- **strategy_id** - unikalny identyfikator strategii

---

## Proces sprawdzania

### 1. Główna pętla (`TradingBot.run()`)

```python
def run(self):
    # 1. Wczytaj otwarte pozycje z bazy danych
    self._load_open_positions()
    
    # 2. Przetwórz każdą strategię
    for strategy in self.strategies:
        self._process_strategy(strategy)
```

### 2. Przetwarzanie strategii (`_process_strategy()`)

```
┌─────────────────────────────────────────────────────────────┐
│                  PRZETWARZANIE STRATEGII                    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────┐
        │  Pobierz dane świec z bazy        │
        │  (ostatnie N świec, np. 50)       │
        └───────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────┐
        │  Czy mamy otwartą pozycję?        │
        └───────────────────────────────────┘
                    │               │
                TAK │               │ NIE
                    ▼               ▼
        ┌─────────────────┐   ┌─────────────────────┐
        │ ZARZĄDZANIE     │   │ SZUKANIE SYGNAŁU    │
        │ POZYCJĄ         │   │ KUPNA               │
        └─────────────────┘   └─────────────────────┘
                    │                       │
                    ▼                       ▼
        ┌─────────────────┐   ┌─────────────────────┐
        │ check_sell_     │   │ Sprawdź blokadę     │
        │ signal()        │   │ po stracie          │
        └─────────────────┘   └─────────────────────┘
                    │                       │
                    ▼                       ▼
        ┌─────────────────┐   ┌─────────────────────┐
        │ Sprzedaj jeśli  │   │ check_buy_signal()  │
        │ warunki OK      │   │                     │
        └─────────────────┘   └─────────────────────┘
                                            │
                                            ▼
                                ┌─────────────────────┐
                                │ Kup jeśli warunki   │
                                │ spełnione           │
                                └─────────────────────┘
```

### 3. Sprawdzanie sygnału kupna

Przykład dla strategii **Red Candles Sequence**:

```python
def check_buy_signal(self, df: pd.DataFrame) -> bool:
    # KROK 1: Sprawdź czy mamy wystarczająco danych
    if len(df) < self.barsCount + 2:
        return False
    
    # KROK 2: Sprawdź sekwencję spadkowych świec
    # Przykład: 5 świec gdzie każda ma niższy "body mid" niż poprzednia
    falling_sequence = True
    for i in range(1, self.barsCount + 1):
        mid_curr = (df['open'].iloc[-i] + df['close'].iloc[-i]) / 2
        mid_prev = (df['open'].iloc[-i-1] + df['close'].iloc[-i-1]) / 2
        
        if not (mid_curr < mid_prev):
            falling_sequence = False
            break
    
    # KROK 3: Sprawdź całkowity spadek w sekwencji
    first_mid = (df['open'].iloc[-5] + df['close'].iloc[-5]) / 2
    last_mid = (df['open'].iloc[-1] + df['close'].iloc[-1]) / 2
    sequence_drop = (first_mid - last_mid) / first_mid * 100
    
    if sequence_drop < self.totalDropPerc:  # np. 5%
        return False
    
    # KROK 4: Sprawdź czy obecna świeca jest rosnąca
    mid_current = (df['open'].iloc[-1] + df['close'].iloc[-1]) / 2
    mid_previous = (df['open'].iloc[-2] + df['close'].iloc[-2]) / 2
    
    if mid_current <= mid_previous:
        return False
    
    # Wszystkie warunki spełnione!
    return True
```

**Wizualizacja:**
```
Świece (od lewej do prawej):
    
    ┌─┐         
    │ │ ← Świeca 5 (najstarsza)
    └─┘ mid = 100
      
      ┌─┐       
      │ │ ← Świeca 4
      └─┘ mid = 98
      
        ┌─┐     
        │ │ ← Świeca 3
        └─┘ mid = 96
        
          ┌─┐   
          │ │ ← Świeca 2
          └─┘ mid = 94
          
            ┌─┐ 
            │ │ ← Świeca 1 (najnowsza)
            └─┘ mid = 92
            
Spadek: (100 - 92) / 100 = 8% ✓ (> 5%)
Sekwencja spadkowa: ✓
Obecna świeca rosnąca: sprawdzamy czy mid(-1) > mid(-2)
```

### 4. Sprawdzanie sygnału sprzedaży

```python
def check_sell_signal(self, df: pd.DataFrame, position) -> tuple[bool, str]:
    current_price = df['close'].iloc[-1]
    
    # WARUNEK 1: STOP LOSS
    sl_price = self.get_stop_loss(position.entry_price)
    if current_price <= sl_price:
        return True, "STOP_LOSS"
    
    # WARUNEK 2: TAKE PROFIT (dwuetapowy)
    tp_price = self.get_take_profit(position.entry_price)
    
    # Etap 1: Aktywacja śledzenia TP
    if not position.tp_tracking and current_price >= tp_price:
        position.tp_tracking = True
        position.red_count = 0
        print("TP aktywowany - czekam na czerwone świece")
    
    # Etap 2: Liczenie czerwonych świec po aktywacji TP
    if position.tp_tracking:
        last_candle = df.iloc[-1]
        
        # Czerwona świeca: close < open
        if last_candle['close'] < last_candle['open']:
            position.red_count += 1
        else:
            position.red_count = 0  # Reset przy zielonej świecy
        
        # Sprzedaj po N czerwonych świecach
        if position.red_count >= self.red_candles_to_sell:
            return True, "TAKE_PROFIT"
    
    return False, ""
```

**Przykład działania TP:**
```
Cena wejścia: 100 USDT
TP trigger: 104 USDT (4%)

Świeca 1: 103 → TP nieaktywny
Świeca 2: 105 → TP AKTYWOWANY! (cena >= 104)
Świeca 3: 106 (zielona) → red_count = 0
Świeca 4: 105 (czerwona) → red_count = 1
Świeca 5: 104 (czerwona) → red_count = 2
Świeca 6: 103 (czerwona) → red_count = 3
...
Świeca N: gdy red_count >= 6 → SPRZEDAJ!
```

---

## Przykłady strategii

### Strategia 1: Falling Candles

**Warunki kupna:**
- N spadkowych świec (domyślnie 6)
- Opcjonalnie: 1 zaburzenie dozwolone
- Średnia (open+close)/2 każdej świecy < poprzedniej

**Warunki sprzedaży:**
- SL: -5% od ceny wejścia
- TP: +12% od ceny wejścia + 3 czerwone świece

### Strategia 2: Red Candles Sequence

**Warunki kupna:**
- 5 spadkowych świec
- Całkowity spadek >= 5%
- Obecna świeca rosnąca (odwrócenie trendu)

**Warunki sprzedaży:**
- SL: -50% (bardzo szeroki)
- TP: +5%
- Stagnacja: wymuszenie sprzedaży po 60 świecach

### Strategia 3: BNB PineScript

**Warunki kupna:**
- 5 spadkowych świec (1 zaburzenie OK)
- Brak straty w ostatnich 6 świecach

**Warunki sprzedaży:**
- SL: -12%
- TP: +4% + 6 czerwonych świec

---

## Przepływ danych

### 1. Dane wejściowe (DataFrame)

```python
df = pd.DataFrame({
    'timestamp': [...],
    'open': [100.5, 101.2, 99.8, ...],
    'high': [102.0, 103.5, 100.5, ...],
    'low': [99.0, 100.0, 98.5, ...],
    'close': [101.0, 100.0, 99.0, ...],
    'volume': [...]
})
```

### 2. Indeksowanie świec

```python
# W Pythonie używamy ujemnych indeksów:
df.iloc[-1]   # Ostatnia (najnowsza) świeca
df.iloc[-2]   # Przedostatnia świeca
df.iloc[-5]   # 5-ta świeca od końca

# W PineScript:
# [0] = bieżąca świeca
# [1] = poprzednia świeca
# [5] = 5-ta świeca wstecz
```

### 3. Obliczenia

```python
# Body Mid (środek korpusu świecy)
body_mid = (open + close) / 2

# Czy świeca czerwona?
is_red = close < open

# Czy świeca zielona?
is_green = close > open

# Procent zmiany
change_perc = (current_price - entry_price) / entry_price * 100
```

---

## Blokady i zabezpieczenia

### 1. Blokada po stracie

```python
# Sprawdź czy była strata w ostatnich N świecach
if self.db.recent_loss(symbol, strategy_id, lookback_bars):
    print("Blokada kupna po niedawnej stracie")
    return  # Nie kupuj
```

### 2. Minimalna ilość danych

```python
if len(df) < self.barsCount + 2:
    return False  # Za mało danych do analizy
```

### 3. Walidacja pozycji

```python
# Sprawdź czy nie mamy już otwartej pozycji
position_key = f"{symbol}_{strategy_id}"
if position_key in self.positions:
    # Zarządzaj istniejącą pozycją
else:
    # Szukaj nowego sygnału kupna
```

---

## Podsumowanie

**Kluczowe punkty:**

1. ✅ Każda strategia implementuje 4 metody: `check_buy_signal`, `check_sell_signal`, `get_stop_loss`, `get_take_profit`

2. ✅ Sprawdzanie odbywa się w pętli dla każdej strategii osobno

3. ✅ Dane świec pobierane są z bazy danych (ostatnie N świec)

4. ✅ Sygnały kupna sprawdzane tylko gdy brak otwartej pozycji

5. ✅ Sygnały sprzedaży sprawdzane tylko gdy pozycja jest otwarta

6. ✅ Zabezpieczenia: blokada po stracie, minimalna ilość danych, walidacja pozycji

7. ✅ Take Profit może być dwuetapowy: aktywacja + czekanie na potwierdzenie (czerwone świece)
