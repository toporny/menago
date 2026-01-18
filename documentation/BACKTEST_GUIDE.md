# Backtest - Testowanie strategii na danych historycznych

## Przegląd

Funkcja backtestingu pozwala sprawdzić czy strategia wygenerowałaby sygnał kupna w konkretnym momencie w przeszłości. To niezwykle przydatne narzędzie do:

- Testowania strategii na historycznych danych
- Weryfikacji czy strategia wykryłaby znane okazje
- Optymalizacji parametrów strategii
- Analizy skuteczności bez ryzyka

## Jak używać

### Podstawowe użycie

```bash
python sandbox_binance_new.py --backtest "2026-01-10 14:00:00"
```

Bot pobierze dane historyczne do podanego momentu i sprawdzi czy strategia wygenerowałaby sygnał kupna.

### Format daty

**Wymagany format:** `YYYY-MM-DD HH:MM:SS`

**Przykłady poprawnych dat:**
```
2026-01-10 14:00:00
2026-01-05 09:30:00
2025-12-31 23:59:59
```

**Niepoprawne formaty:**
```
2026-01-10           ❌ Brak godziny
10-01-2026 14:00     ❌ Zła kolejność
2026/01/10 14:00:00  ❌ Ukośniki zamiast myślników
```

## Przykłady użycia

### 1. Test wszystkich strategii w konkretnym momencie

```bash
python sandbox_binance_new.py --backtest "2026-01-10 14:00:00"
```

**Output:**
```
📅 TRYB BACKTEST - Testowanie na danych historycznych: 2026-01-10 14:00:00
✅ Pobrano 50 świec historycznych z bnbusdt_1h
📅 Ostatnia świeca: 2026-01-10 14:00:00
ℹ️ Aktualna cena BNBUSDT: 905.02
⚪ BNB_FallingCandles - warunki kupna nie spełnione
```

### 2. Test konkretnej strategii

```bash
python sandbox_binance_new.py --backtest "2026-01-10 14:00:00" --strategy BNB_FallingCandles
```

### 3. Test dla konkretnej waluty

```bash
python sandbox_binance_new.py --backtest "2026-01-10 14:00:00" --symbol XRPUSDT
```

### 4. Kombinacja parametrów

```bash
python sandbox_binance_new.py --backtest "2026-01-10 14:00:00" --strategy XRP_Conservative --symbol XRPUSDT
```

## Co pokazuje backtest

### Gdy NIE ma sygnału kupna:

```
📊 Przetwarzam: BNB_FallingCandles(BNBUSDT)
✅ Pobrano 50 świec historycznych z bnbusdt_1h
📅 Ostatnia świeca: 2026-01-10 14:00:00
ℹ️ Aktualna cena BNBUSDT: 905.02
⚪ BNB_FallingCandles - warunki kupna nie spełnione
```

### Gdy JEST sygnał kupna:

```
📊 Przetwarzam: BNB_FallingCandles(BNBUSDT)
✅ Pobrano 50 świec historycznych z bnbusdt_1h
📅 Ostatnia świeca: 2026-01-09 10:00:00
ℹ️ Aktualna cena BNBUSDT: 650.50
✅ SYGNAŁ KUPNA wykryty dla BNB_FallingCandles!
💡 Strategia wygenerowałaby kupno po cenie: 650.50
📈 Take Profit: 728.56 (+12.0%)
📉 Stop Loss: 617.98 (-5.0%)
```

## Jak działa backtest

1. **Pobiera dane historyczne** - świece PRZED podanym timestampem
2. **Sprawdza warunki strategii** - używa tych samych reguł co w trybie live
3. **Wyświetla wynik** - czy byłby sygnał kupna i jakie byłyby poziomy TP/SL
4. **NIE wykonuje transakcji** - to tylko analiza

## Przypadki użycia

### 🔍 Weryfikacja strategii

Sprawdź czy strategia wykryłaby znaną okazję:

```bash
# Sprawdź czy strategia wykryłaby spadek z 10 stycznia
python sandbox_binance_new.py --backtest "2026-01-10 09:00:00" --symbol BNBUSDT
```

### 📊 Optymalizacja parametrów

Testuj różne momenty aby zobaczyć kiedy strategia generuje sygnały:

```bash
python sandbox_binance_new.py --backtest "2026-01-10 08:00:00"
python sandbox_binance_new.py --backtest "2026-01-10 09:00:00"
python sandbox_binance_new.py --backtest "2026-01-10 10:00:00"
```

### 🎯 Porównanie strategii

Sprawdź która strategia lepiej wykrywa okazje:

```bash
# Konserwatywna
python sandbox_binance_new.py --backtest "2026-01-10 14:00:00" --strategy XRP_Conservative

# Agresywna
python sandbox_binance_new.py --backtest "2026-01-10 14:00:00" --strategy XRP_Aggressive
```

### 📈 Analiza wielu walut

```bash
# Sprawdź wszystkie waluty w tym samym momencie
python sandbox_binance_new.py --backtest "2026-01-10 14:00:00"
```

## Ograniczenia

⚠️ **Backtest NIE symuluje:**
- Zarządzania pozycją (TP/SL)
- Sprzedaży
- Wielokrotnych transakcji
- Slippage (różnicy między ceną oczekiwaną a rzeczywistą)

✅ **Backtest TYLKO sprawdza:**
- Czy byłby sygnał kupna w danym momencie
- Jakie byłyby poziomy TP/SL

## Wskazówki

### 💡 Wybór czasu

- Dla świec 1h: testuj pełne godziny (14:00:00, nie 14:30:00)
- Dla świec 4h: testuj co 4 godziny (00:00, 04:00, 08:00, etc.)
- Dla świec 1d: testuj o północy (00:00:00)

### 💡 Ilość danych

Bot pobiera 50 świec przed podanym timestampem. Upewnij się że:
- Masz wystarczająco dużo danych w bazie
- Timestamp nie jest zbyt blisko początku danych

### 💡 Automatyzacja testów

Możesz stworzyć skrypt do testowania wielu momentów:

**test_backtest.bat:**
```batch
@echo off
echo Testowanie strategii na różnych momentach...

python sandbox_binance_new.py --backtest "2026-01-09 10:00:00" --symbol BNBUSDT
python sandbox_binance_new.py --backtest "2026-01-09 14:00:00" --symbol BNBUSDT
python sandbox_binance_new.py --backtest "2026-01-10 10:00:00" --symbol BNBUSDT
python sandbox_binance_new.py --backtest "2026-01-10 14:00:00" --symbol BNBUSDT

pause
```

## Przykładowy workflow

### Krok 1: Znajdź interesujący moment

Przejrzyj wykresy i znajdź moment gdzie spodziewasz się sygnału.

### Krok 2: Uruchom backtest

```bash
python sandbox_binance_new.py --backtest "2026-01-10 14:00:00" --symbol BNBUSDT
```

### Krok 3: Analiza wyniku

- Jeśli **JEST sygnał** - strategia działa poprawnie ✅
- Jeśli **BRAK sygnału** - może trzeba dostosować parametry ⚙️

### Krok 4: Optymalizacja

Jeśli strategia nie wykryła okazji, możesz:
1. Zmienić parametry w `config.json`
2. Uruchomić backtest ponownie
3. Porównać wyniki

## Różnice: Backtest vs Dry-run

| Funkcja | Backtest | Dry-run |
|---------|----------|---------|
| Dane | Historyczne | Aktualne |
| Transakcje | Nie | Nie (symulacja) |
| Zarządzanie pozycją | Nie | Tak |
| Cel | Analiza przeszłości | Test bez ryzyka |
| Parametr | `--backtest` | `--dry-run` |

## Połączenie z dry-run

Możesz użyć obu jednocześnie (choć backtest sam w sobie nie wykonuje transakcji):

```bash
python sandbox_binance_new.py --backtest "2026-01-10 14:00:00" --dry-run
```

To zapewnia że nawet jeśli coś pójdzie nie tak, żadne transakcje nie zostaną wykonane.

## Błędy i rozwiązania

### Błąd: "Nieprawidłowy format daty"

```
❌ Nieprawidłowy format daty. Użyj: YYYY-MM-DD HH:MM:SS
   Przykład: 2026-01-10 14:00:00
```

**Rozwiązanie:** Użyj dokładnie formatu `YYYY-MM-DD HH:MM:SS` z cudzysłowami.

### Błąd: "Brak danych historycznych"

```
⚠️ Brak danych historycznych w bnbusdt_1h dla 2026-01-10 14:00:00
```

**Rozwiązanie:** 
- Sprawdź czy masz dane w bazie dla tego okresu
- Użyj nowszej daty
- Upewnij się że nazwa tabeli jest poprawna

## Podsumowanie

Backtest to potężne narzędzie do:
- ✅ Weryfikacji strategii na danych historycznych
- ✅ Optymalizacji parametrów
- ✅ Analizy skuteczności bez ryzyka
- ✅ Porównywania różnych strategii

**Pamiętaj:** Backtest pokazuje tylko czy byłby sygnał kupna, nie symuluje pełnego cyklu transakcji.
