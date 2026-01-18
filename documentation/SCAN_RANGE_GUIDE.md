# Skanowanie zakresu dat - Dokumentacja

## Przegląd

Funkcja skanowania zakresu dat pozwala znaleźć wszystkie punkty kupna w określonym okresie czasu. To idealne narzędzie do:

- Porównania wyników z TradingView
- Analizy skuteczności strategii w przeszłości
- Znajdowania wszystkich sygnałów w danym okresie
- Weryfikacji poprawności implementacji strategii

## Jak używać

### Podstawowe użycie

```bash
python sandbox_binance_new.py --scan-range "2025-11-01 00:00:00" "2025-11-30 23:00:00"
```

### Format

```bash
--scan-range "DATA_START" "DATA_END"
```

- **DATA_START**: Data początkowa (YYYY-MM-DD HH:MM:SS)
- **DATA_END**: Data końcowa (YYYY-MM-DD HH:MM:SS)

## Parametry

### `--scan-range` / `-r`
Określa zakres dat do przeskanowania.

```bash
python sandbox_binance_new.py --scan-range "2025-11-15 00:00:00" "2025-11-20 23:00:00"
```

### `--interval`
Określa interwał skanowania w godzinach (domyślnie: 1h).

```bash
# Skanuj co 4 godziny
python sandbox_binance_new.py --scan-range "2025-11-01 00:00:00" "2025-11-30 23:00:00" --interval 4

# Skanuj co 24 godziny (raz dziennie)
python sandbox_binance_new.py --scan-range "2025-11-01 00:00:00" "2025-11-30 23:00:00" --interval 24
```

## Przykłady użycia

### 1. Skanowanie miesiąca dla wszystkich strategii

```bash
python sandbox_binance_new.py --scan-range "2025-11-01 00:00:00" "2025-11-30 23:00:00"
```

### 2. Skanowanie dla konkretnej strategii

```bash
python sandbox_binance_new.py --scan-range "2025-11-01 00:00:00" "2025-11-30 23:00:00" --strategy BNB_PineScript
```

### 3. Skanowanie dla konkretnej waluty

```bash
python sandbox_binance_new.py --scan-range "2025-11-01 00:00:00" "2025-11-30 23:00:00" --symbol BNBUSDT
```

### 4. Skanowanie tygodnia z interwałem 4h

```bash
python sandbox_binance_new.py --scan-range "2025-11-15 00:00:00" "2025-11-22 00:00:00" --interval 4
```

### 5. Porównanie dwóch strategii

```bash
# Strategia 1
python sandbox_binance_new.py --scan-range "2025-11-01 00:00:00" "2025-11-30 23:00:00" --strategy XRP_Conservative

# Strategia 2
python sandbox_binance_new.py --scan-range "2025-11-01 00:00:00" "2025-11-30 23:00:00" --strategy XRP_Aggressive
```

## Przykładowy output

```
🔍 SKANOWANIE ZAKRESU DAT
================================================================================
📅 Od: 2025-11-15 00:00:00
📅 Do: 2025-11-20 23:00:00
⏱️  Interwał: 1h
📊 Strategie: 1
================================================================================

✅ 2025-11-16 01:00:00 | BNB_PineScript | BNBUSDT
   💰 Cena: 928.19
   📈 TP: 965.31 (+4.0%)
   📉 SL: 816.81 (-12.0%)

✅ 2025-11-16 16:00:00 | BNB_PineScript | BNBUSDT
   💰 Cena: 914.51
   📈 TP: 951.09 (+4.0%)
   📉 SL: 804.77 (-12.0%)

...

📊 PODSUMOWANIE SKANOWANIA
================================================================================
🔍 Sprawdzono punktów: 144
✅ Znaleziono sygnałów kupna: 16

📋 LISTA WSZYSTKICH SYGNAŁÓW:
--------------------------------------------------------------------------------
Data                 Strategia            Symbol     Cena       TP%      SL%     
--------------------------------------------------------------------------------
2025-11-16 01:00:00  BNB_PineScript       BNBUSDT    928.19     +4.0     -12.0   
2025-11-16 16:00:00  BNB_PineScript       BNBUSDT    914.51     +4.0     -12.0   
2025-11-16 17:00:00  BNB_PineScript       BNBUSDT    915.68     +4.0     -12.0   
...
--------------------------------------------------------------------------------

📈 STATYSTYKI PER STRATEGIA:
   BNB_PineScript: 16 sygnałów
================================================================================
```

## Interpretacja wyników

### Liczba sprawdzonych punktów
```
🔍 Sprawdzono punktów: 144
```
To liczba wszystkich momentów czasowych, które zostały przeskanowane (zakres dat × liczba strategii).

### Znalezione sygnały
```
✅ Znaleziono sygnałów kupna: 16
```
Liczba momentów, w których strategia wygenerowałaby sygnał kupna.

### Lista sygnałów
Każdy sygnał zawiera:
- **Data** - dokładny moment sygnału
- **Strategia** - strategy_id
- **Symbol** - para walutowa
- **Cena** - cena w momencie sygnału
- **TP%** - procent Take Profit
- **SL%** - procent Stop Loss

### Statystyki per strategia
Pokazuje ile sygnałów wygenerowała każda strategia.

## Porównanie z TradingView

### Krok 1: Uruchom skanowanie w Pythonie

```bash
python sandbox_binance_new.py --scan-range "2025-11-01 00:00:00" "2025-11-30 23:00:00" --strategy BNB_PineScript
```

### Krok 2: Sprawdź wyniki w TradingView

1. Otwórz wykres BNBUSDT 1h w TradingView
2. Zastosuj swoją strategię PineScript
3. Sprawdź listę transakcji (Strategy Tester)

### Krok 3: Porównaj daty

Porównaj daty sygnałów z Pythona z datami z TradingView:

**Python:**
```
2025-11-16 01:00:00  BNB_PineScript  BNBUSDT  928.19
2025-11-16 16:00:00  BNB_PineScript  BNBUSDT  914.51
```

**TradingView:**
```
Nov 16, 2025 01:00  Long  928.19
Nov 16, 2025 16:00  Long  914.51
```

✅ Jeśli daty i ceny się zgadzają - implementacja jest poprawna!  
⚠️ Jeśli są różnice - sprawdź parametry strategii

## Optymalizacja skanowania

### Duże zakresy dat

Dla dużych zakresów użyj większego interwału:

```bash
# Cały rok, co 24h
python sandbox_binance_new.py --scan-range "2025-01-01 00:00:00" "2025-12-31 23:00:00" --interval 24
```

### Tylko konkretne godziny

Jeśli wiesz że sygnały występują o konkretnych godzinach:

```bash
# Tylko godziny 00:00, 04:00, 08:00, 12:00, 16:00, 20:00
python sandbox_binance_new.py --scan-range "2025-11-01 00:00:00" "2025-11-30 20:00:00" --interval 4
```

## Eksport wyników

### Do pliku tekstowego

```bash
python sandbox_binance_new.py --scan-range "2025-11-01 00:00:00" "2025-11-30 23:00:00" > wyniki_skanowania.txt
```

### Do CSV (ręcznie)

Możesz skopiować tabelę z wyników i wkleić do Excel/Google Sheets:

```
Data                 Strategia            Symbol     Cena       TP%      SL%     
2025-11-16 01:00:00  BNB_PineScript       BNBUSDT    928.19     +4.0     -12.0   
```

## Przypadki użycia

### 🔍 Weryfikacja strategii

Sprawdź czy strategia wykrywa znane okazje:

```bash
python sandbox_binance_new.py --scan-range "2025-11-15 00:00:00" "2025-11-20 23:00:00" --strategy BNB_PineScript
```

### 📊 Analiza częstotliwości sygnałów

Ile sygnałów generuje strategia w miesiącu?

```bash
python sandbox_binance_new.py --scan-range "2025-11-01 00:00:00" "2025-11-30 23:00:00"
```

### 🎯 Porównanie strategii

Która strategia generuje więcej sygnałów?

```bash
# Konserwatywna
python sandbox_binance_new.py --scan-range "2025-11-01 00:00:00" "2025-11-30 23:00:00" --strategy XRP_Conservative

# Agresywna
python sandbox_binance_new.py --scan-range "2025-11-01 00:00:00" "2025-11-30 23:00:00" --strategy XRP_Aggressive
```

### 📈 Optymalizacja parametrów

1. Zmień parametry w `config.json`
2. Uruchom skanowanie
3. Porównaj liczbę sygnałów
4. Wybierz najlepsze ustawienia

## Ograniczenia

⚠️ **Skanowanie NIE symuluje:**
- Zarządzania pozycją
- Sprzedaży (TP/SL)
- Wielokrotnych transakcji
- Rzeczywistych zysków/strat

✅ **Skanowanie TYLKO znajduje:**
- Momenty sygnałów kupna
- Ceny w tych momentach
- Poziomy TP/SL

## Wskazówki

### 💡 Wybór zakresu

- **Krótki zakres (tydzień)**: Szczegółowa analiza
- **Średni zakres (miesiąc)**: Ogólna skuteczność
- **Długi zakres (rok)**: Statystyki długoterminowe

### 💡 Interwał

- **1h**: Dla świec 1h (domyślnie)
- **4h**: Dla świec 4h lub szybszego skanowania
- **24h**: Dla świec 1d lub bardzo długich zakresów

### 💡 Wydajność

Skanowanie 1 miesiąca (720 godzin) zajmuje ok. 1-2 minuty.

## Różnice: Scan vs Backtest

| Funkcja | Scan Range | Backtest |
|---------|------------|----------|
| Zakres | Wiele dat | Jedna data |
| Output | Lista sygnałów | Tak/Nie |
| Cel | Znajdź wszystkie | Sprawdź jeden moment |
| Czas | Dłuższy | Szybki |
| Parametr | `--scan-range` | `--backtest` |

## Przykładowy workflow

### Krok 1: Skanuj miesiąc

```bash
python sandbox_binance_new.py --scan-range "2025-11-01 00:00:00" "2025-11-30 23:00:00" --strategy BNB_PineScript
```

### Krok 2: Sprawdź w TradingView

Otwórz TradingView i porównaj daty.

### Krok 3: Jeśli są różnice

- Sprawdź parametry strategii
- Zweryfikuj logikę w `strategy_bnb_pinescript.py`
- Uruchom backtest dla konkretnej daty:

```bash
python sandbox_binance_new.py --backtest "2025-11-16 01:00:00" --strategy BNB_PineScript
```

### Krok 4: Optymalizuj

Jeśli strategia działa poprawnie, możesz:
- Dostosować parametry
- Przetestować na innych okresach
- Uruchomić na żywo

## Podsumowanie

Skanowanie zakresu dat to potężne narzędzie do:
- ✅ Weryfikacji strategii
- ✅ Porównania z TradingView
- ✅ Analizy skuteczności
- ✅ Optymalizacji parametrów

**Użyj tego przed uruchomieniem strategii na żywo!**
