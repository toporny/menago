# Test połączenia API - Podsumowanie

## Zaimplementowana funkcja

Dodano funkcję `test_api_on_start` która testuje połączenie z Binance API podczas inicjalizacji bota.

## Jak używać

W pliku `config.json` ustaw:

```json
"binance": {
  "api_key": "TWÓJ_KLUCZ",
  "api_secret": "TWÓJ_SECRET",
  "testnet": true,
  "test_api_on_start": true  ← Włącz test
}
```

## Co testuje

Gdy `test_api_on_start: true`, bot wykonuje przy starcie:

1. ✅ **Test statusu serwera** - sprawdza czy serwer Binance działa
2. ✅ **Test ping** - weryfikuje połączenie sieciowe
3. ✅ **Dostęp do konta** - sprawdza czy klucze API są poprawne
4. ✅ **Wyświetlenie sald** - pokazuje dostępne środki (wolne + zablokowane)
5. ✅ **Uprawnienia API** - weryfikuje jakie operacje są dozwolone

## Przykładowy output

```
2026-01-11 13:31:09 🔍 Testowanie połączenia z Binance Testnet...
2026-01-11 13:31:10 ✅ Status serwera: OK
2026-01-11 13:31:10 ✅ Ping: OK
2026-01-11 13:31:10 ✅ Dostęp do konta: OK
2026-01-11 13:31:10 💰 Salda na koncie:
   BNB: 1.00000000 (wolne: 1.00000000, zablokowane: 0.00000000)
   BTC: 1.00000000 (wolne: 1.00000000, zablokowane: 0.00000000)
   USDT: 10000.00000000 (wolne: 10000.00000000, zablokowane: 0.00000000)
   ... i 451 więcej
2026-01-11 13:31:10 ✅ Uprawnienia API: SPOT
2026-01-11 13:31:10 ✅ Test połączenia zakończony pomyślnie!
```

## Obsługa błędów

Jeśli klucze API są niepoprawne lub brak uprawnień:

```
❌ Błąd podczas testu połączenia: API-key format invalid
⚠️ Sprawdź czy klucze API są poprawne i mają odpowiednie uprawnienia
```

Bot zakończy działanie i nie będzie próbował wykonywać transakcji.

## Korzyści

- ✅ Natychmiastowa weryfikacja konfiguracji
- ✅ Widoczność sald przed rozpoczęciem tradingu
- ✅ Wykrycie problemów z API przed wykonaniem zleceń
- ✅ Potwierdzenie uprawnień (SPOT trading)

## Wyłączenie testu

Jeśli nie chcesz testować przy każdym uruchomieniu:

```json
"test_api_on_start": false
```

Lub usuń tę linię z konfiguracji (domyślnie wyłączone).

## Implementacja techniczna

### Metoda `_test_binance_connection()`

Znajduje się w `sandbox_binance_new.py` (linie 79-132).

Wykonuje:
- `client.get_system_status()` - status serwera
- `client.ping()` - test połączenia
- `client.get_account()` - informacje o koncie
- Wyświetla max 5 pierwszych walut z saldem > 0
- Pokazuje uprawnienia API z konta

### Obsługa emoji w Windows

Dodano konfigurację UTF-8 dla konsoli Windows (linie 7-15):

```python
if sys.platform == 'win32':
    try:
        os.system('chcp 65001 > nul')
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass
```

Dzięki temu emoji (🚀, ✅, ❌, 💰 itp.) wyświetlają się poprawnie w PowerShell/CMD.
