# Strategia BNB PineScript - Dokumentacja

## Przegląd

Strategia `BNBPineScriptStrategy` została stworzona na podstawie skryptu PineScript v6 specjalnie dla pary **BNBUSDT**.

## Parametry strategii

### Domyślne wartości (z PineScript):

```json
{
  "num_falling": 5,
  "allow_one_break": true,
  "take_profit_perc": 4.0,
  "stop_loss_perc": 12.0,
  "red_candles_to_sell": 6,
  "loss_lookback_bars": 6
}
```

### Opis parametrów:

| Parametr | Wartość | Opis |
|----------|---------|------|
| `num_falling` | 5 | Liczba spadkowych świeczek wymagana do kupna |
| `allow_one_break` | true | Pozwala na jedną zaburzającą świeczkę w sekwencji |
| `take_profit_perc` | 4.0% | Próg aktywacji śledzenia Take Profit |
| `stop_loss_perc` | 12.0% | Sztywny Stop Loss |
| `red_candles_to_sell` | 6 | Liczba czerwonych świec do sprzedaży po aktywacji TP |
| `loss_lookback_bars` | 6 | Liczba świec do blokady kupna po stracie |

## Logika strategii

### 🟢 Warunki KUPNA:

1. **5 spadkowych świeczek** - średnia (open+close)/2 każdej świecy musi być niższa od poprzedniej
2. **Opcjonalne zaburzenie** - jedna świeczka może nie być spadkowa (jeśli `allow_one_break=true`)
3. **Brak niedawnej straty** - w ostatnich 6 świeczkach nie było zamkniętej pozycji ze stratą

**Przykład sekwencji spadkowej:**
```
Świeca 6: mid = 920
Świeca 5: mid = 915  ✓ spadek
Świeca 4: mid = 910  ✓ spadek  
Świeca 3: mid = 912  ✗ wzrost (zaburzenie - OK jeśli allow_one_break=true)
Świeca 2: mid = 908  ✓ spadek
Świeca 1: mid = 905  ✓ spadek
→ 4 spadkowe + 1 zaburzenie = BRAK SYGNAŁU (potrzeba 5 spadkowych)
```

### 🔴 Warunki SPRZEDAŻY:

#### 1. Stop Loss (sztywny 12%)
- Aktywuje się gdy cena spadnie o 12% poniżej ceny kupna
- **Przykład:** Kupno po 900 → SL = 792

#### 2. Take Profit (śledzony)

**Faza 1: Aktywacja TP**
- TP aktywuje się gdy `high` świecy osiągnie +4% od ceny kupna
- **Przykład:** Kupno po 900 → TP aktywuje się gdy high ≥ 936

**Faza 2: Śledzenie czerwonych świec**
- Po aktywacji TP, strategia liczy czerwone świeczki (close < open)
- Jeśli świeczka zielona (close ≥ open) → licznik resetuje się do 0
- Sprzedaż następuje po 6 kolejnych czerwonych świeczkach

**Przykład:**
```
Kupno: 900
High osiąga 936 → TP AKTYWOWANY

Świeca 1: close < open → red_count = 1
Świeca 2: close < open → red_count = 2
Świeca 3: close ≥ open → red_count = 0 (reset!)
Świeca 4: close < open → red_count = 1
Świeca 5: close < open → red_count = 2
Świeca 6: close < open → red_count = 3
Świeca 7: close < open → red_count = 4
Świeca 8: close < open → red_count = 5
Świeca 9: close < open → red_count = 6 → SPRZEDAŻ!
```

### 🚫 Blokada po stracie

Jeśli ostatnia zamknięta pozycja (w ciągu ostatnich 6 świec) zakończyła się stratą, strategia **NIE** wygeneruje sygnału kupna.

**Przykład:**
```
Świeca 100: Sprzedaż ze stratą -5%
Świeca 101-106: Blokada kupna (nawet jeśli warunki spełnione)
Świeca 107: Blokada zniesiona, można kupować
```

## Różnice względem oryginalnej strategii FallingCandlesStrategy

| Parametr | FallingCandlesStrategy | BNBPineScriptStrategy |
|----------|------------------------|----------------------|
| Liczba spadkowych świec | 6 | 5 |
| Take Profit | 12% | 4% (trigger) |
| Stop Loss | 5% | 12% |
| Czerwone świece do sprzedaży | 3 | 6 |
| Blokada po stracie | 1 świeca | 6 świec |

## Konfiguracja w config.json

```json
{
  "symbol": "BNBUSDT",
  "table": "bnbusdt_1h",
  "strategy": "BNBPineScriptStrategy",
  "strategy_id": "BNB_PineScript",
  "buy_quantity": 1,
  "enabled": true,
  "params": {
    "num_falling": 5,
    "allow_one_break": true,
    "take_profit_perc": 4.0,
    "stop_loss_perc": 12.0,
    "red_candles_to_sell": 6,
    "loss_lookback_bars": 6
  }
}
```

## Przykłady użycia

### Test na danych aktualnych
```bash
python sandbox_binance_new.py --symbol BNBUSDT
```

### Test historyczny
```bash
python sandbox_binance_new.py --backtest "2025-11-20 01:00:00" --symbol BNBUSDT
```

### Tryb dry-run
```bash
python sandbox_binance_new.py --dry-run --symbol BNBUSDT
```

## Optymalizacja parametrów

Możesz dostosować parametry w `config.json`:

### Bardziej konserwatywna strategia:
```json
"params": {
  "num_falling": 6,           // Więcej spadkowych świec
  "allow_one_break": false,   // Bez zaburzeń
  "take_profit_perc": 5.0,    // Wyższy TP
  "stop_loss_perc": 10.0,     // Mniejszy SL
  "red_candles_to_sell": 4,   // Szybsza sprzedaż
  "loss_lookback_bars": 10    // Dłuższa blokada
}
```

### Bardziej agresywna strategia:
```json
"params": {
  "num_falling": 4,           // Mniej spadkowych świec
  "allow_one_break": true,    // Pozwól zaburzenie
  "take_profit_perc": 3.0,    // Niższy TP
  "stop_loss_perc": 15.0,     // Większy SL
  "red_candles_to_sell": 8,   // Wolniejsza sprzedaż
  "loss_lookback_bars": 3     // Krótsza blokada
}
```

## Wskazówki

✅ **Zalecane:**
- Testuj na danych historycznych przed użyciem na żywo
- Używaj `--dry-run` do weryfikacji sygnałów
- Monitoruj skuteczność w bazie danych

⚠️ **Uwagi:**
- Strategia wymaga minimum 50 świec w bazie danych
- Działa tylko na świecach 1h (bnbusdt_1h)
- Blokada po stracie może pominąć dobre okazje

## Analiza skuteczności

Sprawdź skuteczność strategii w bazie danych:

```sql
SELECT 
    strategy_name,
    COUNT(*) as total_trades,
    AVG(profit_loss_perc) as avg_profit,
    SUM(CASE WHEN profit_loss_perc > 0 THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN profit_loss_perc < 0 THEN 1 ELSE 0 END) as losses
FROM _binance_crypto_trades
WHERE strategy_name = 'BNB_PineScript'
  AND position_status = 'CLOSED'
GROUP BY strategy_name;
```

## Kod źródłowy

Pełna implementacja znajduje się w pliku:
`strategy_bnb_pinescript.py`

Strategia dziedziczy po klasie bazowej `Strategy` i implementuje wszystkie wymagane metody zgodnie z logiką PineScript.
