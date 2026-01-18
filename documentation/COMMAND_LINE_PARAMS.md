# Parametry wiersza poleceń - Dokumentacja

## Przegląd

Bot obsługuje parametry wiersza poleceń, które pozwalają na elastyczne uruchamianie bez modyfikacji pliku konfiguracyjnego.

## Dostępne parametry

### `--help` / `-h`
Wyświetla pomoc i wszystkie dostępne opcje.

```bash
python sandbox_binance_new.py --help
```

### `--config` / `-c`
Określa ścieżkę do pliku konfiguracyjnego.

```bash
python sandbox_binance_new.py --config my_config.json
```

**Domyślnie:** `config.json`

### `--dry-run` / `-d`
Tryb symulacji - bot **NIE wykonuje** rzeczywistych transakcji. Przydatne do:
- Testowania strategii
- Sprawdzania sygnałów kupna/sprzedaży
- Debugowania bez ryzyka

```bash
python sandbox_binance_new.py --dry-run
```

**Output:**
```
⚠️ TRYB DRY-RUN - Transakcje NIE będą wykonywane!
...
🟢 KUPNO [BNB_FallingCandles]: BNBUSDT po ~650.5
🔸 DRY-RUN: Symulacja kupna (transakcja NIE została wykonana)
```

### `--strategy` / `-s`
Uruchamia tylko określone strategie (po `strategy_id`). Można użyć wielokrotnie.

```bash
# Jedna strategia
python sandbox_binance_new.py --strategy BNB_FallingCandles

# Wiele strategii
python sandbox_binance_new.py --strategy BNB_FallingCandles --strategy XRP_Conservative
```

**Skrócona forma:**
```bash
python sandbox_binance_new.py -s BNB_FallingCandles -s XRP_Conservative
```

### `--symbol` / `-y`
Uruchamia tylko dla określonych symboli walut. Można użyć wielokrotnie.

```bash
# Jeden symbol
python sandbox_binance_new.py --symbol BNBUSDT

# Wiele symboli
python sandbox_binance_new.py --symbol BNBUSDT --symbol XRPUSDT
```

**Skrócona forma:**
```bash
python sandbox_binance_new.py -y BNBUSDT -y XRPUSDT
```

### `--backtest` / `-b`
Test historyczny - sprawdza czy strategia wygenerowałaby sygnał kupna w określonym momencie przeszłości.

```bash
python sandbox_binance_new.py --backtest "2026-01-10 14:00:00"
```

**Format:** `YYYY-MM-DD HH:MM:SS` (w cudzysłowach!)

**Przykłady:**
```bash
# Test wszystkich strategii
python sandbox_binance_new.py --backtest "2026-01-10 14:00:00"

# Test konkretnej strategii
python sandbox_binance_new.py --backtest "2026-01-10 14:00:00" --strategy BNB_FallingCandles

# Test dla konkretnej waluty
python sandbox_binance_new.py --backtest "2026-01-10 14:00:00" --symbol BNBUSDT
```

**Co pokazuje:**
- Czy byłby sygnał kupna w tym momencie
- Jaka była cena
- Jakie byłyby poziomy TP/SL

**Uwaga:** Backtest NIE symuluje pełnego cyklu transakcji, tylko sprawdza sygnały kupna.

Zobacz `BACKTEST_GUIDE.md` dla szczegółowej dokumentacji.

### `--scan-range` / `-r`
Skanuje zakres dat w poszukiwaniu WSZYSTKICH sygnałów kupna.

```bash
python sandbox_binance_new.py --scan-range "2025-11-01 00:00:00" "2025-11-30 23:00:00"
```

**Format:** Dwie daty w formacie `YYYY-MM-DD HH:MM:SS` (w cudzysłowach!)

**Przykłady:**
```bash
# Skanuj cały miesiąc
python sandbox_binance_new.py --scan-range "2025-11-01 00:00:00" "2025-11-30 23:00:00"

# Tylko konkretna strategia
python sandbox_binance_new.py --scan-range "2025-11-01 00:00:00" "2025-11-30 23:00:00" --strategy BNB_PineScript

# Tylko konkretna waluta
python sandbox_binance_new.py --scan-range "2025-11-01 00:00:00" "2025-11-30 23:00:00" --symbol BNBUSDT

# Własny interwał (co 4h zamiast co 1h)
python sandbox_binance_new.py --scan-range "2025-11-01 00:00:00" "2025-11-30 23:00:00" --interval 4
```

**Co pokazuje:**
- Listę WSZYSTKICH momentów z sygnałem kupna
- Cenę w każdym momencie
- Poziomy TP/SL
- Statystyki per strategia

**Zastosowanie:**
- Porównanie z wynikami TradingView
- Analiza skuteczności strategii
- Znajdowanie wszystkich sygnałów w okresie

Zobacz `SCAN_RANGE_GUIDE.md` dla szczegółowej dokumentacji.

### `--interval`
Określa interwał skanowania w godzinach (używane z `--scan-range`).

```bash
# Skanuj co 4 godziny
python sandbox_binance_new.py --scan-range "2025-11-01 00:00:00" "2025-11-30 23:00:00" --interval 4
```

**Domyślnie:** 1 (co 1 godzinę)


## Przykłady użycia

### 1. Uruchomienie standardowe
Wszystkie włączone strategie z `config.json`:
```bash
python sandbox_binance_new.py
```

### 2. Test strategii bez transakcji
```bash
python sandbox_binance_new.py --dry-run
```

### 3. Tylko strategia BNB
```bash
python sandbox_binance_new.py --strategy BNB_FallingCandles
```

### 4. Tylko waluta XRPUSDT
```bash
python sandbox_binance_new.py --symbol XRPUSDT
```

### 5. Test konkretnej strategii
```bash
python sandbox_binance_new.py --dry-run --strategy XRP_Conservative
```

### 6. Wiele strategii w trybie dry-run
```bash
python sandbox_binance_new.py --dry-run --strategy BNB_FallingCandles --strategy XRP_Conservative
```

### 7. Własny plik konfiguracyjny
```bash
python sandbox_binance_new.py --config production_config.json
```

### 8. Kombinacja wszystkich parametrów
```bash
python sandbox_binance_new.py --config test_config.json --dry-run --symbol BNBUSDT
```

## Logi z parametrami

Gdy używasz parametrów, bot wyświetla podsumowanie:

```
📋 Parametry uruchomienia:
   - Tryb: DRY-RUN (symulacja)
   - Strategie: BNB_FallingCandles, XRP_Conservative
   - Symbole: BNBUSDT

🚀 Inicjalizacja TradingBot...
⚠️ TRYB DRY-RUN - Transakcje NIE będą wykonywane!
```

## Filtrowanie strategii

### Jak działa filtrowanie?

1. **Bez parametrów** - uruchamia wszystkie `enabled: true` z config.json
2. **Z `--strategy`** - uruchamia TYLKO wymienione strategie (ignoruje `enabled`)
3. **Z `--symbol`** - uruchamia TYLKO strategie dla wymienionych symboli
4. **Kombinacja** - uruchamia strategie spełniające OBA warunki

### Przykład filtrowania

**Config.json:**
```json
{
  "currencies": [
    {"symbol": "BNBUSDT", "strategy_id": "BNB_FallingCandles", "enabled": true},
    {"symbol": "XRPUSDT", "strategy_id": "XRP_Conservative", "enabled": true},
    {"symbol": "XRPUSDT", "strategy_id": "XRP_Aggressive", "enabled": false}
  ]
}
```

**Uruchomienie:**
```bash
python sandbox_binance_new.py --symbol XRPUSDT
```

**Wynik:**
```
✅ Załadowano strategię: XRP_Conservative(XRPUSDT)
⏭️ Pomijam BNBUSDT (nie w filtrze symboli)
⚪ Strategia XRP_Aggressive dla XRPUSDT wyłączona
```

## Przypadki użycia

### 🧪 Testowanie nowej strategii
```bash
python sandbox_binance_new.py --dry-run --strategy NowaStrategia
```

### 📊 Analiza konkretnej waluty
```bash
python sandbox_binance_new.py --symbol BTCUSDT
```

### 🔍 Debugowanie problemu
```bash
python sandbox_binance_new.py --dry-run --strategy ProblematycznaStrategia
```

### 🚀 Produkcja - tylko sprawdzone strategie
```bash
python sandbox_binance_new.py --strategy BNB_FallingCandles --strategy XRP_Conservative
```

### ⏰ Cron - różne strategie o różnych porach
```bash
# Rano - konserwatywne
0 9 * * * python sandbox_binance_new.py --strategy XRP_Conservative

# Wieczorem - agresywne
0 21 * * * python sandbox_binance_new.py --strategy XRP_Aggressive
```

## Wskazówki

✅ **Używaj `--dry-run`** przy testowaniu nowych strategii  
✅ **Filtruj po `--symbol`** gdy chcesz skupić się na jednej walucie  
✅ **Filtruj po `--strategy`** gdy testujesz różne warianty parametrów  
✅ **Kombinuj parametry** dla maksymalnej kontroli  

❌ **Nie używaj** `--dry-run` w produkcji (chyba że celowo)  
❌ **Nie mieszaj** wielu plików config bez potrzeby  

## Skrypty pomocnicze

### test_all.bat (Windows)
```batch
@echo off
echo Testowanie wszystkich strategii...
python sandbox_binance_new.py --dry-run
pause
```

### test_bnb.bat
```batch
@echo off
echo Testowanie strategii BNB...
python sandbox_binance_new.py --dry-run --symbol BNBUSDT
pause
```

### run_production.bat
```batch
@echo off
echo Uruchamianie produkcyjne...
python sandbox_binance_new.py --strategy BNB_FallingCandles --strategy XRP_Conservative
```
