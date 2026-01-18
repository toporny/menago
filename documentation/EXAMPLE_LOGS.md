# Przykładowe logi z strategy_id

## Uruchomienie bota

```
2026-01-11 13:15:00 🚀 Inicjalizacja TradingBot...
2026-01-11 13:15:01 ✅ Konfiguracja wczytana z config.json
2026-01-11 13:15:02 ✅ Połączono z Binance Testnet
2026-01-11 13:15:03 ✅ Kolumna strategy_name już istnieje
2026-01-11 13:15:04 ✅ Załadowano strategię: BNB_FallingCandles(BNBUSDT)
2026-01-11 13:15:05 ✅ Załadowano strategię: XRP_Conservative(XRPUSDT)
2026-01-11 13:15:06 ⚪ Strategia XRP_Aggressive dla XRPUSDT wyłączona
2026-01-11 13:15:07 ✅ TradingBot zainicjalizowany z 2 strategiami
```

## Przetwarzanie strategii BNBUSDT

```
2026-01-11 13:15:10 📊 Przetwarzam: BNB_FallingCandles(BNBUSDT)
2026-01-11 13:15:11 ✅ Pobrano 50 świec z bnbusdt_1h
2026-01-11 13:15:12 ℹ️ Aktualna cena BNBUSDT: 650.45
2026-01-11 13:15:13 🟢 KUPNO [BNB_FallingCandles]: BNBUSDT po ~650.45
2026-01-11 13:15:14 ✅ Transakcja zapisana w bazie: ID=123
2026-01-11 13:15:15 ✅ KUPNO wykonane [BNB_FallingCandles]: BNBUSDT po 650.48, ID=123
```

## Przetwarzanie strategii XRPUSDT (Conservative)

```
2026-01-11 13:15:20 📊 Przetwarzam: XRP_Conservative(XRPUSDT)
2026-01-11 13:15:21 ✅ Pobrano 50 świec z xrpusdt_1h
2026-01-11 13:15:22 ℹ️ Aktualna cena XRPUSDT: 2.45
2026-01-11 13:15:23 ⚪ XRP_Conservative - warunki kupna nie spełnione
```

## Sprzedaż z zyskiem

```
2026-01-11 14:30:00 📊 Przetwarzam: BNB_FallingCandles(BNBUSDT)
2026-01-11 14:30:01 ℹ️ Aktywna pozycja: Position(BNBUSDT, BNB_FallingCandles, entry=650.48, qty=1, tp_tracking=True)
2026-01-11 14:30:02 🟡 BNB_FallingCandles TP aktywowany przy 728.54
2026-01-11 14:30:03 🔴 SPRZEDAŻ [BNB_FallingCandles]: BNBUSDT po ~730.2, powód: TAKE_PROFIT
2026-01-11 14:30:04 ✅ Transakcja zaktualizowana: ID=123, profit=12.25%
2026-01-11 14:30:05 🟢 SPRZEDAŻ wykonana [BNB_FallingCandles]: BNBUSDT po 730.18, zysk/strata: 12.25%
```

## Sprzedaż ze stratą (Stop Loss)

```
2026-01-11 15:45:00 📊 Przetwarzam: XRP_Conservative(XRPUSDT)
2026-01-11 15:45:01 ℹ️ Aktywna pozycja: Position(XRPUSDT, XRP_Conservative, entry=2.50, qty=10, tp_tracking=False)
2026-01-11 15:45:02 🔴 SPRZEDAŻ [XRP_Conservative]: XRPUSDT po ~2.38, powód: STOP_LOSS
2026-01-11 15:45:03 ✅ Transakcja zaktualizowana: ID=124, profit=-4.80%
2026-01-11 15:45:04 🔴 SPRZEDAŻ wykonana [XRP_Conservative]: XRPUSDT po 2.38, zysk/strata: -4.80%
```

## Blokada po stracie

```
2026-01-11 16:00:00 📊 Przetwarzam: XRP_Conservative(XRPUSDT)
2026-01-11 16:00:01 ✅ Pobrano 50 świec z xrpusdt_1h
2026-01-11 16:00:02 ℹ️ Aktualna cena XRPUSDT: 2.35
2026-01-11 16:00:03 ⚠️ XRP_Conservative - blokada kupna po niedawnej stracie
```

## Wiele strategii dla tej samej waluty

Jeśli włączysz obie strategie XRP (Conservative i Aggressive):

```
2026-01-11 17:00:00 📊 Przetwarzam: XRP_Conservative(XRPUSDT)
2026-01-11 17:00:01 ℹ️ Aktualna cena XRPUSDT: 2.40
2026-01-11 17:00:02 ⚪ XRP_Conservative - warunki kupna nie spełnione

2026-01-11 17:00:05 📊 Przetwarzam: XRP_Aggressive(XRPUSDT)
2026-01-11 17:00:06 ℹ️ Aktualna cena XRPUSDT: 2.40
2026-01-11 17:00:07 🟢 KUPNO [XRP_Aggressive]: XRPUSDT po ~2.40
2026-01-11 17:00:08 ✅ KUPNO wykonane [XRP_Aggressive]: XRPUSDT po 2.40, ID=125
```

**Zauważ:** Dzięki `strategy_id` dokładnie wiesz, która strategia wykonała akcję!

---

## Baza danych - tabela _binance_crypto_trades

```
| id  | symbol  | strategy_name     | buy_price | sell_price | profit_loss_perc | position_status |
|-----|---------|-------------------|-----------|------------|------------------|-----------------|
| 123 | BNBUSDT | BNB_FallingCandles| 650.48    | 730.18     | +12.25          | CLOSED          |
| 124 | XRPUSDT | XRP_Conservative  | 2.50      | 2.38       | -4.80           | CLOSED          |
| 125 | XRPUSDT | XRP_Aggressive    | 2.40      | NULL       | NULL            | OPEN            |
```

Możesz teraz analizować skuteczność każdej strategii osobno:

```sql
-- Średni zysk dla każdej strategii
SELECT 
    strategy_name, 
    AVG(profit_loss_perc) as avg_profit,
    COUNT(*) as total_trades
FROM _binance_crypto_trades
WHERE position_status = 'CLOSED'
GROUP BY strategy_name;
```

Wynik:
```
| strategy_name      | avg_profit | total_trades |
|--------------------|------------|--------------|
| BNB_FallingCandles | +8.5%      | 15           |
| XRP_Conservative   | +3.2%      | 8            |
| XRP_Aggressive     | +12.1%     | 5            |
```
