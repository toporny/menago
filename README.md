# System wielowalutowy - Bot tradingowy Binance

System tradingowy obsługujący wiele walut z różnymi strategiami.

## 📁 Struktura plików

```
__SANDBOX_BINANCE/
├── config.json                      # Konfiguracja walut i strategii
├── sandbox_binance_new.py           # Główny plik bota (TradingBot)
├── strategy.py                      # Klasa bazowa Strategy + FallingCandlesStrategy
├── strategy_xrp_pinescript.py       # Strategia dla XRP (konwersja z PineScript)
├── position.py                      # Klasa Position (zarządzanie pozycją)
├── database_manager.py              # DatabaseManager (operacje MySQL)
├── HOW_TO_ADD_STRATEGY.md           # Instrukcja dodawania strategii
└── sandbox_binance.py               # Stary plik (do usunięcia)
```

## 🚀 Uruchomienie

1. **Skonfiguruj klucze API** w `config.json`:
   ```json
   "binance": {
     "api_key": "TWÓJ_KLUCZ",
     "api_secret": "TWÓJ_SECRET",
     "testnet": true,
     "test_api_on_start": true
   }
   ```
   
   > **💡 Wskazówka:** Ustaw `test_api_on_start: true` aby przy każdym uruchomieniu sprawdzić połączenie z API i wyświetlić salda konta.

2. **Sprawdź konfigurację MySQL** w `config.json`:
   ```json
   "mysql": {
     "host": "localhost",
     "user": "root",
     "password": "",
     "database": "menago",
     "port": 3306
   }
   ```

3. **Uruchom bota**:
   ```bash
   python sandbox_binance_new.py
   ```

## 🎛️ Parametry wiersza poleceń

Bot obsługuje parametry pozwalające na elastyczne uruchamianie:

```bash
# Pomoc
python sandbox_binance_new.py --help

# Tryb dry-run (bez rzeczywistych transakcji)
python sandbox_binance_new.py --dry-run

# Tylko konkretna strategia
python sandbox_binance_new.py --strategy BNB_FallingCandles

# Tylko konkretny symbol
python sandbox_binance_new.py --symbol BNBUSDT

# Kombinacja parametrów
python sandbox_binance_new.py --dry-run --symbol XRPUSDT
```

**Dostępne opcje:**
- `--config` / `-c` - własny plik konfiguracyjny
- `--dry-run` / `-d` - tryb symulacji (bez transakcji)
- `--strategy` / `-s` - filtr strategii (strategy_id)
- `--symbol` / `-y` - filtr symboli (np. BNBUSDT)

Zobacz `COMMAND_LINE_PARAMS.md` dla pełnej dokumentacji.


## ⚙️ Konfiguracja walut

Edytuj `config.json` aby dodać/usunąć waluty:

```json
{
  "currencies": [
    {
      "symbol": "BNBUSDT",
      "table": "bnbusdt_1h",
      "strategy": "FallingCandlesStrategy",
      "strategy_id": "BNB_FallingCandles",
      "buy_quantity": 1,
      "enabled": true,
      "params": {
        "num_falling": 6,
        "take_profit_perc": 12.0,
        "stop_loss_perc": 5.0
      }
    }
  ]
}
```

### Parametry:
- `symbol` - para walutowa (np. BNBUSDT, XRPUSDT)
- `table` - tabela w MySQL ze świecami
- `strategy` - nazwa klasy strategii
- `strategy_id` - **unikalny identyfikator strategii** (opcjonalny, ale zalecany)
- `buy_quantity` - ilość do kupna
- `enabled` - włącz/wyłącz strategię
- `params` - parametry specyficzne dla strategii

### 🆔 Strategy ID - Unikalne identyfikatory

**Dlaczego `strategy_id` jest ważne?**

Możesz uruchomić **wiele instancji tej samej strategii** dla tej samej waluty z różnymi parametrami. `strategy_id` pozwala je rozróżnić w logach i bazie danych.

**Przykład - dwie strategie dla XRPUSDT:**

```json
{
  "symbol": "XRPUSDT",
  "strategy": "XRPPineScriptStrategy",
  "strategy_id": "XRP_Conservative",  ← Konserwatywna
  "params": {
    "num_falling": 6,
    "take_profit_perc": 12.0,
    "stop_loss_perc": 5.0
  }
},
{
  "symbol": "XRPUSDT",
  "strategy": "XRPPineScriptStrategy",
  "strategy_id": "XRP_Aggressive",  ← Agresywna
  "params": {
    "num_falling": 5,
    "take_profit_perc": 10.0,
    "stop_loss_perc": 4.0
  }
}
```

**Logi będą wyglądać tak:**
```
📊 Przetwarzam: XRP_Conservative(XRPUSDT)
🟢 KUPNO [XRP_Conservative]: XRPUSDT po ~2.50
...
📊 Przetwarzam: XRP_Aggressive(XRPUSDT)
⚪ XRP_Aggressive - warunki kupna nie spełnione
```

**W bazie danych:**
```
| id | symbol  | strategy_name     | profit_loss_perc |
|----|---------|-------------------|------------------|
| 1  | XRPUSDT | XRP_Conservative  | +5.2%           |
| 2  | XRPUSDT | XRP_Aggressive    | +8.1%           |
```

## 📊 Dostępne strategie

### 1. FallingCandlesStrategy
Strategia spadających świec (oryginalna).

**Parametry:**
- `num_falling` - liczba spadkowych świec (domyślnie 6)
- `allow_one_break` - pozwól jedno zaburzenie (domyślnie true)
- `take_profit_perc` - procent TP (domyślnie 12.0)
- `stop_loss_perc` - procent SL (domyślnie 5.0)
- `red_candles_to_sell` - czerwone świece do sprzedaży (domyślnie 3)
- `loss_lookback_bars` - blokada po stracie (domyślnie 1)

### 2. XRPPineScriptStrategy
Strategia przetłumaczona z PineScript v6 dla XRPUSDT.

**Parametry:** (takie same jak FallingCandlesStrategy)

### 3. BNBPineScriptStrategy
Strategia dla BNBUSDT przetłumaczona z PineScript v6.

**Parametry domyślne:**
- `num_falling` - 5 (liczba spadkowych świec)
- `allow_one_break` - true (pozwól jedno zaburzenie)
- `take_profit_perc` - 4.0% (trigger śledzenia TP)
- `stop_loss_perc` - 12.0% (sztywny SL)
- `red_candles_to_sell` - 6 (czerwone świece do sprzedaży po TP)
- `loss_lookback_bars` - 6 (blokada po stracie)

**Szczegóły:** Zobacz `BNB_PINESCRIPT_STRATEGY.md`


## ⚙️ Konfiguracja zaawansowana

### Test połączenia API przy starcie

Dodaj do sekcji `binance` w `config.json`:

```json
"binance": {
  "api_key": "...",
  "api_secret": "...",
  "testnet": true,
  "test_api_on_start": true  ← Włącz test połączenia
}
```

Przy `test_api_on_start: true` bot wykona przy starcie:
- ✅ Test statusu serwera Binance
- ✅ Test ping
- ✅ Sprawdzenie dostępu do konta
- ✅ Wyświetlenie sald (wolne + zablokowane)
- ✅ Weryfikację uprawnień API

**Przykładowy output:**
```
🔍 Testowanie połączenia z Binance Testnet...
✅ Status serwera: OK
✅ Ping: OK
✅ Dostęp do konta: OK
💰 Salda na koncie:
   BNB: 10.50000000 (wolne: 10.50000000, zablokowane: 0.00000000)
   USDT: 1000.00000000 (wolne: 1000.00000000, zablokowane: 0.00000000)
✅ Uprawnienia API: SPOT
✅ Test połączenia zakończony pomyślnie!
```


## 🗄️ Baza danych

### Wymagana kolumna w tabeli transakcji

Bot automatycznie doda kolumnę `strategy_name` do tabeli `_binance_crypto_trades` przy pierwszym uruchomieniu.

Jeśli chcesz dodać ręcznie:
```sql
ALTER TABLE _binance_crypto_trades 
ADD COLUMN strategy_name VARCHAR(50) AFTER symbol;
```

### Struktura tabeli (przykład):
```sql
CREATE TABLE _binance_crypto_trades (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20),
    strategy_name VARCHAR(50),
    buy_time DATETIME,
    buy_price DECIMAL(20,8),
    quantity DECIMAL(20,8),
    sell_time DATETIME,
    sell_price DECIMAL(20,8),
    profit_loss_perc DECIMAL(10,2),
    position_status VARCHAR(10)
);
```

## ➕ Dodawanie nowych strategii

Zobacz plik `HOW_TO_ADD_STRATEGY.md` dla szczegółowej instrukcji konwersji strategii z TradingView/PineScript.

### Szybki start:

1. Utwórz plik `strategy_nazwa.py`
2. Dziedzicz po klasie `Strategy`
3. Zaimplementuj metody:
   - `check_buy_signal(df)` - warunki kupna
   - `check_sell_signal(df, position)` - warunki sprzedaży
   - `get_stop_loss(entry_price)` - poziom SL
   - `get_take_profit(entry_price)` - poziom TP
4. Dodaj do `config.json`
5. Zarejestruj w `sandbox_binance_new.py`

## 🔄 Jak działa bot

1. **Wczytuje konfigurację** z `config.json`
2. **Łączy się z Binance** (testnet/mainnet)
3. **Inicjalizuje strategie** dla każdej włączonej waluty
4. **Sprawdza otwarte pozycje** w bazie danych
5. **Dla każdej strategii:**
   - Pobiera świece z MySQL
   - Sprawdza sygnały kupna/sprzedaży
   - Wykonuje zlecenia przez Binance API
   - Zapisuje transakcje do bazy

## ⚠️ Ważne uwagi

- Bot działa **jednorazowo** - musisz go uruchamiać cyklicznie (np. cron co godzinę dla świec 1h)
- Zawsze testuj na **Binance Testnet** (`testnet: true`)
- Upewnij się że tabele MySQL mają wystarczająco dużo danych (min. 50 świec)
- Każda strategia może mieć tylko **jedną aktywną pozycję** na raz dla danego symbolu

## 📝 Przykładowe uruchomienie cykliczne (Windows)

Utwórz plik `run_bot.bat`:
```batch
@echo off
cd c:\xampp\htdocs\menago\__SANDBOX_BINANCE
python sandbox_binance_new.py
```

Dodaj do Harmonogramu zadań Windows (Task Scheduler) aby uruchamiać co godzinę.

## 🐛 Debugowanie

Logi są wyświetlane w konsoli z timestampami i emoji:
- 🚀 Inicjalizacja
- ✅ Sukces
- ❌ Błąd
- ⚠️ Ostrzeżenie
- 🟢 Kupno (z `[strategy_id]`)
- 🔴 Sprzedaż (z `[strategy_id]`)
- 🟡 Aktywacja TP
- ℹ️ Informacja

**Przykładowe logi:**
```
2026-01-11 13:15:00 🚀 Inicjalizacja TradingBot...
2026-01-11 13:15:01 ✅ Załadowano strategię: BNB_FallingCandles(BNBUSDT)
2026-01-11 13:15:02 ✅ Załadowano strategię: XRP_Conservative(XRPUSDT)
2026-01-11 13:15:03 📊 Przetwarzam: BNB_FallingCandles(BNBUSDT)
2026-01-11 13:15:04 🟢 KUPNO [BNB_FallingCandles]: BNBUSDT po ~650.5
2026-01-11 13:15:05 ✅ KUPNO wykonane [BNB_FallingCandles]: BNBUSDT po 650.48, ID=123
```

## 📞 Wsparcie

W razie problemów sprawdź:
1. Czy klucze API są poprawne
2. Czy tabele w MySQL istnieją i mają dane
3. Czy kolumna `strategy_name` została dodana
4. Logi w konsoli
