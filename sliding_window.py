"""
Sliding Window - Klasa pomocnicza do zarządzania przesuwnym oknem danych.

Używana w backtestingu do efektywnego dostępu do danych historycznych
bez wielokrotnego odpytywania bazy danych.
"""

import pandas as pd
from datetime import datetime
from typing import Optional


class SlidingWindow:
    """
    Zarządza przesuwnym oknem danych dla backtestingu.
    
    Zamiast pobierać 50 świec z bazy danych dla każdego kroku czasowego,
    ładujemy wszystkie dane raz i przesuwamy okno w pamięci.
    
    Przykład:
        >>> data = db.load_all_data_in_range('bnbusdt_1h', start, end)
        >>> window = SlidingWindow(data, window_size=50)
        >>> df = window.get_window_at_time(datetime(2025, 10, 1, 12, 0))
    """
    
    def __init__(self, data: pd.DataFrame, window_size: int = 50):
        """
        Args:
            data: Pełny DataFrame z danymi świec (posortowany chronologicznie)
            window_size: Rozmiar okna (liczba świec do zwrócenia)
        """
        self.data = data
        self.window_size = window_size
        
        # Walidacja
        if data.empty:
            raise ValueError("DataFrame nie może być pusty")
        
        if 'open_time' not in data.columns:
            raise ValueError("DataFrame musi zawierać kolumnę 'open_time'")
        
        # Konwertuj open_time do datetime jeśli jeszcze nie jest
        if not pd.api.types.is_datetime64_any_dtype(data['open_time']):
            self.data['open_time'] = pd.to_datetime(data['open_time'])
    
    def get_window_at_time(self, timestamp: datetime) -> pd.DataFrame:
        """
        Zwraca okno danych do określonego czasu.
        
        Args:
            timestamp: Czas do którego pobieramy dane
        
        Returns:
            DataFrame z ostatnimi window_size świecami przed/do timestamp
            Pusta DataFrame jeśli brak danych
        """
        # Znajdź wszystkie świece <= timestamp
        mask = self.data['open_time'] <= timestamp
        
        if not mask.any():
            return pd.DataFrame()
        
        # Znajdź indeks ostatniej świecy <= timestamp
        valid_indices = self.data.index[mask]
        end_idx = valid_indices[-1]
        
        # Oblicz indeks początkowy okna
        start_idx = max(0, end_idx - self.window_size + 1)
        
        # Zwróć okno (kopia aby nie modyfikować oryginału)
        return self.data.iloc[start_idx:end_idx + 1].copy()
    
    def get_window_at_index(self, index: int) -> pd.DataFrame:
        """
        Zwraca okno danych dla określonego indeksu.
        
        Args:
            index: Indeks końcowy okna (0-based)
        
        Returns:
            DataFrame z window_size świecami kończącymi się na index
            Pusta DataFrame jeśli index < window_size
        """
        if index < self.window_size - 1:
            # Za mało danych dla pełnego okna
            return pd.DataFrame()
        
        start_idx = index - self.window_size + 1
        return self.data.iloc[start_idx:index + 1].copy()
    
    def get_all_windows(self):
        """
        Generator zwracający wszystkie możliwe okna.
        
        Yields:
            Tuple[int, pd.DataFrame]: (indeks, okno danych)
        """
        for i in range(self.window_size - 1, len(self.data)):
            yield i, self.get_window_at_index(i)
    
    def __len__(self):
        """Zwraca liczbę możliwych okien."""
        return max(0, len(self.data) - self.window_size + 1)
    
    def __repr__(self):
        return f"SlidingWindow(data_length={len(self.data)}, window_size={self.window_size}, num_windows={len(self)})"
