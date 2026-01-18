# Strategia Red Candles Sequence - Dokumentacja

## Przegląd

Strategia `RedCandlesSequenceStrategy` została stworzona na podstawie skryptu PineScript v6 "Red Candles Sequence (with stagnation exit)".

## Parametry strategii

### Domyślne wartości (z PineScript):

```json
{
  "barsCount": 5,
  "totalDropPerc": 5.0,
  "tpPerc": 5.0,
  "slPerc": 50.0,
  "stagnationBars": 60
}
```

### Opis parametrów:

| Parametr | Wartość | Opis |
|----------|---------|------|
| `barsCount` | 5 | Liczba świec w sekwencji spadkowej |
| `totalDropPerc` | 5.0% | Minimalny całkowity spadek w sekwencji |
| `tpPerc` | 5.0% | Take Profit |
| `slPerc` | 50.0% | Stop Loss |
| `stagnationBars` | 60 | Maksymalna liczba świec do trzymania pozycji |

## Logika strategii

### 🟢 Warunki KUPNA:

Wszystkie 3 warunki muszą być spełnione:

#### 1. Sekwencja N spadkowych świec

Strategia sprawdza czy ostatnie N świec tworzy sekwencję spadkową.

**Kluczowa różnica:** Używa "body mid" zamiast close:
```
body_mid = (open + close) / 2
```

Świeca jest spadkowa gdy:
```
body_mid(i) < body_mid(i+1)
```

**Przykład sekwencji dla barsCount=5:**
```
Świeca 6: body_mid = 920
Świeca 5: body_mid = 915  ✓ spadek
Świeca 4: body_mid = 910  ✓ spadek
Świeca 3: body_mid = 905  ✓ spadek
Świeca 2: body_mid = 900  ✓ spadek
Świeca 1: body_mid = 895  ✓ spadek
→ 5 spadkowych świec ✅
```

#### 2. Minimalny całkowity spadek

Całkowity spadek w sekwencji musi być >= totalDropPerc%.

```
firstMid = body_mid(świeca najstarsza w sekwencji)
lastMid = body_mid(świeca najnowsza w sekwencji)
sequenceDrop = (firstMid - lastMid) / firstMid * 100
```

**Przykład:**
```
firstMid = 920 (świeca 5)
lastMid = 895 (świeca 1)
sequenceDrop = (920 - 895) / 920 * 100 = 2.72%

2.72% < 5.0% → BRAK SYGNAŁU ❌
```

**Przykład z sygnałem:**
```
firstMid = 1000
lastMid = 940
sequenceDrop = (1000 - 940) / 1000 * 100 = 6.0%

6.0% >= 5.0% → WARUNEK SPEŁNIONY ✅
```

#### 3. Obecna świeca rosnąca

Ostatnia świeca musi być rosnąca (odwrócenie trendu):
```
body_mid(0) > body_mid(1)
```

**Przykład:**
```
Świeca 1: body_mid = 895
Świeca 0: body_mid = 900

900 > 895 → ROSNĄCA ✅
```

**Jeśli WSZYSTKIE 3 warunki spełnione → KUPNO!**

### 🔴 Warunki SPRZEDAŻY:

#### 1. Take Profit (5%)

Sprzedaż gdy cena osiągnie +5% od ceny kupna.

**Przykład:**
```
Cena kupna: 900
TP: 945 (900 × 1.05)

Gdy cena >= 945 → SPRZEDAŻ ✅
```

#### 2. Stop Loss (50%)

Sprzedaż gdy cena spadnie o 50% poniżej ceny kupna.

**Przykład:**
```
Cena kupna: 900
SL: 450 (900 × 0.50)

Gdy cena <= 450 → SPRZEDAŻ ✅
```

⚠️ **UWAGA:** SL 50% to bardzo duży spadek! Może oznaczać ogromną stratę.

#### 3. Stagnacja (60 świec)

Jeśli po 60 świecach (60 godzin dla 1h) pozycja nadal jest otwarta, następuje wymuszona sprzedaż.

**Przykład:**
```
Kupno: Świeca 100
Świeca 101-159: Pozycja otwarta
Świeca 160: 60 świec minęło → WYMUSZENIE SPRZEDAŻY ✅
```

## Konfiguracja w config.json

```json
{
  "symbol": "BNBUSDT",
  "table": "bnbusdt_1h",
  "strategy": "RedCandlesSequenceStrategy",
  "strategy_id": "RedCandles_BNB",
  "buy_quantity": 1,
  "enabled": true,
  "params": {
    "barsCount": 5,
    "totalDropPerc": 5.0,
    "tpPerc": 5.0,
    "slPerc": 50.0,
    "stagnationBars": 60
  }
}
```

## Przykłady użycia

### Test na danych aktualnych
```bash
python sandbox_binance_new.py --symbol BNBUSDT --strategy RedCandles_BNB
```

### Test historyczny
```bash
python sandbox_binance_new.py --backtest "2025-11-20 14:00:00" --strategy RedCandles_BNB
```

### Skanowanie zakresu dat
```bash
python sandbox_binance_new.py --scan-range "2025-11-01 00:00:00" "2025-11-30 23:00:00" --strategy RedCandles_BNB
```

## Optymalizacja parametrów

### Bardziej konserwatywna strategia:
```json
"params": {
  "barsCount": 7,           // Więcej świec w sekwencji
  "totalDropPerc": 8.0,     // Większy wymagany spadek
  "tpPerc": 3.0,            // Niższy TP (szybsza realizacja)
  "slPerc": 30.0,           // Mniejszy SL (mniejsze ryzyko)
  "stagnationBars": 40      // Krótsza stagnacja
}
```

### Bardziej agresywna strategia:
```json
"params": {
  "barsCount": 3,           // Mniej świec
  "totalDropPerc": 3.0,     // Mniejszy wymagany spadek
  "tpPerc": 10.0,           // Wyższy TP (większy zysk)
  "slPerc": 60.0,           // Większy SL (więcej przestrzeni)
  "stagnationBars": 100     // Dłuższa stagnacja
}
```

## Różnice względem innych strategii

| Cecha | BNBPineScriptStrategy | RedCandlesSequenceStrategy |
|-------|----------------------|----------------------------|
| Wykrywanie | 5 spadkowych (mid) | 5 spadkowych (mid) + min. spadek |
| Zaburzenie | Tak (1 świeca) | Nie |
| Warunek dodatkowy | Brak | Całkowity spadek >= 5% |
| Sygnał kupna | Po 5 spadkowych | Po 5 spadkowych + świeca rosnąca |
| Take Profit | 4% (śledzony) | 5% (sztywny) |
| Stop Loss | 12% | 50% (!!) |
| Dodatkowe wyjście | 6 czerwonych świec | Stagnacja (60 świec) |

## Kluczowe cechy

### ✅ Zalety:
- **Wymaga potwierdzenia** - świeca rosnąca po spadkach
- **Minimalny spadek** - filtruje małe ruchy
- **Stagnacja** - automatyczne zamknięcie po 60h
- **Duży SL** - daje dużo przestrzeni

### ⚠️ Uwagi:
- **Bardzo duży SL (50%)** - może oznaczać ogromną stratę!
- **Brak zaburzenia** - wszystkie świece muszą być spadkowe
- **Długa stagnacja (60h)** - może trzymać pozycję bardzo długo
- **Sztywny TP** - sprzedaje od razu po osiągnięciu 5%

## Wskazówki

### 💡 Stop Loss 50%

To bardzo duży SL! Rozważ zmniejszenie do 10-20%:
```json
"slPerc": 15.0
```

### 💡 Stagnacja

60 świec (60h dla 1h) to 2.5 dnia. Możesz skrócić:
```json
"stagnationBars": 24  // 1 dzień
```

### 💡 Minimalny spadek

5% to dość dużo. Dla mniejszych ruchów możesz zmniejszyć:
```json
"totalDropPerc": 3.0
```

## Analiza skuteczności

Sprawdź skuteczność w bazie danych:

```sql
SELECT 
    strategy_name,
    COUNT(*) as total_trades,
    AVG(profit_loss_perc) as avg_profit,
    MAX(profit_loss_perc) as max_profit,
    MIN(profit_loss_perc) as max_loss,
    SUM(CASE WHEN profit_loss_perc > 0 THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN profit_loss_perc < 0 THEN 1 ELSE 0 END) as losses
FROM _binance_crypto_trades
WHERE strategy_name = 'RedCandles_BNB'
  AND position_status = 'CLOSED'
GROUP BY strategy_name;
```

## Kod źródłowy

Pełna implementacja znajduje się w pliku:
`strategy_red_candles.py`

Strategia dziedziczy po klasie bazowej `Strategy` i implementuje wszystkie wymagane metody zgodnie z logiką PineScript.
