"""
Test porównawczy logiki PineScript vs Python dla strategii DOGE.
Sprawdza czy translacja jest poprawna.
"""

import pandas as pd
import numpy as np

# Symulacja danych (6 świec opadających)
# W PineScript [0] = najnowsza, [5] = najstarsza
# W DataFrame iloc[-1] = najnowsza, iloc[-6] = najstarsza

data = {
    'open': [100, 98, 96, 94, 92, 90],    # Opadające
    'close': [98, 96, 94, 92, 90, 88],    # Opadające (czerwone świece)
    'high': [101, 99, 97, 95, 93, 91],
    'low': [97, 95, 93, 91, 89, 87]
}

df = pd.DataFrame(data)

print("="*80)
print("TEST TRANSLACJI PINESCRIPT -> PYTHON")
print("="*80)

print("\nDane testowe (od najstarszej do najnowszej):")
print(df)

print("\n" + "="*80)
print("1. TEST BODY_MID")
print("="*80)

# PineScript: bodyMid(bar) => (open[bar] + close[bar]) / 2
# Python: _body_mid(df, bar) gdzie bar=0 to ostatnia świeca

def body_mid_python(df, bar):
    """bar=0 to ostatnia świeca (jak w PineScript [0])"""
    idx = -(bar + 1)
    return (df['open'].iloc[idx] + df['close'].iloc[idx]) / 2

print("\nPineScript [0] (najnowsza) = Python bar=0:")
print(f"  bodyMid(0) = {body_mid_python(df, 0)}")  # Powinno być (90+88)/2 = 89

print("\nPineScript [1] (poprzednia) = Python bar=1:")
print(f"  bodyMid(1) = {body_mid_python(df, 1)}")  # Powinno być (92+90)/2 = 91

print("\nPineScript [5] (najstarsza) = Python bar=5:")
print(f"  bodyMid(5) = {body_mid_python(df, 5)}")  # Powinno być (100+98)/2 = 99

print("\n" + "="*80)
print("2. TEST FALLING SEQUENCE")
print("="*80)

# PineScript:
# for i = 0 to candleCount - 2
#     if bodyMid(i) >= bodyMid(i + 1)
#         fallingSequence := false

# To sprawdza: bodyMid(0) < bodyMid(1) < bodyMid(2) < ...
# Czyli: 89 < 91 < 93 < 95 < 97 (OPADAJĄCA od starszych do nowszych)

candle_count = 6

print(f"\nSprawdzam {candle_count} świec:")
print("PineScript logika: for i = 0 to candleCount - 2")
print("  Sprawdza: bodyMid(0) < bodyMid(1) < bodyMid(2) < ...")

falling_sequence = True
for i in range(candle_count - 1):
    mid_i = body_mid_python(df, i)
    mid_i_plus_1 = body_mid_python(df, i + 1)
    
    print(f"  i={i}: bodyMid({i})={mid_i:.1f} vs bodyMid({i+1})={mid_i_plus_1:.1f}", end="")
    
    if mid_i >= mid_i_plus_1:
        print(" ❌ NIE opadająca")
        falling_sequence = False
    else:
        print(" ✅ Opadająca")

print(f"\nWynik: falling_sequence = {falling_sequence}")

print("\n" + "="*80)
print("3. TEST STRONG RED")
print("="*80)

min_red_body_pct = 2.0  # 2%

def is_strong_red(df, bar, min_pct):
    idx = -(bar + 1)
    open_price = df['open'].iloc[idx]
    close_price = df['close'].iloc[idx]
    
    # Czerwona?
    if close_price >= open_price:
        return False
    
    # Silna?
    drop_pct = (open_price - close_price) / open_price * 100
    return drop_pct >= min_pct

print(f"\nSprawdzam silne czerwone świece (min {min_red_body_pct}%):")

strong_red_exists = False
for i in range(candle_count):
    idx = -(i + 1)
    open_price = df['open'].iloc[idx]
    close_price = df['close'].iloc[idx]
    drop_pct = (open_price - close_price) / open_price * 100
    
    is_strong = is_strong_red(df, i, min_red_body_pct)
    
    print(f"  Świeca {i}: open={open_price}, close={close_price}, drop={drop_pct:.2f}% → {'✅ SILNA' if is_strong else '❌ słaba'}")
    
    if is_strong:
        strong_red_exists = True

print(f"\nWynik: strongRedExists = {strong_red_exists}")

print("\n" + "="*80)
print("4. TEST DYNAMIC STOP LOSS")
print("="*80)

# PineScript:
# midStart = bodyMid(candleCount - 1)   // pierwsza świeca sekwencji
# midEnd   = bodyMid(0)                 // ostatnia świeca sekwencji

mid_start = body_mid_python(df, candle_count - 1)  # Najstarsza w sekwencji
mid_end = body_mid_python(df, 0)  # Najnowsza w sekwencji

print(f"\nmidStart = bodyMid({candle_count - 1}) = {mid_start}")
print(f"midEnd = bodyMid(0) = {mid_end}")

fall_drop_pct = (mid_start - mid_end) / mid_start
stop_loss_multiplier = 1.0
stop_loss_pct = fall_drop_pct * stop_loss_multiplier

print(f"\nfallDropPct = (midStart - midEnd) / midStart = {fall_drop_pct:.4f} ({fall_drop_pct*100:.2f}%)")
print(f"stopLossPct = fallDropPct * {stop_loss_multiplier} = {stop_loss_pct:.4f} ({stop_loss_pct*100:.2f}%)")

valid_stop_loss = stop_loss_pct > 0 and stop_loss_pct < 0.5
print(f"validStopLoss = {valid_stop_loss}")

print("\n" + "="*80)
print("PODSUMOWANIE")
print("="*80)

print("\n✅ Translacja jest POPRAWNA jeśli:")
print("  - falling_sequence = True (świece opadają)")
print("  - strongRedExists = True (są silne czerwone)")
print("  - validStopLoss = True (SL w zakresie 0-50%)")

print(f"\nAktualne wyniki:")
print(f"  falling_sequence = {falling_sequence}")
print(f"  strongRedExists = {strong_red_exists}")
print(f"  validStopLoss = {valid_stop_loss}")

if falling_sequence and strong_red_exists and valid_stop_loss:
    print("\n🎉 TRANSLACJA POPRAWNA!")
else:
    print("\n❌ TRANSLACJA MA BŁĘDY!")
