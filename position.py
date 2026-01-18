class Position:
    """
    Reprezentuje aktywną pozycję tradingową.
    """
    
    def __init__(self, db_id: int, symbol: str, strategy_name: str, 
                 entry_price: float, quantity: float):
        """
        Args:
            db_id: ID rekordu w bazie danych
            symbol: Symbol waluty (np. 'BNBUSDT')
            strategy_name: Nazwa strategii (strategy_id)
            entry_price: Cena wejścia
            quantity: Ilość zakupionej waluty
        """
        self.db_id = db_id
        self.symbol = symbol
        self.strategy_name = strategy_name
        self.entry_price = entry_price
        self.quantity = quantity
        
        # Stan dla śledzenia TP
        self.tp_tracking = False
        self.red_count = 0
        
        # Indeks świecy wejścia (dla strategii ze stagnacją)
        self.entry_bar_index = 0
    
    def __str__(self):
        return (f"Position(symbol={self.symbol}, strategy={self.strategy_name}, "
                f"entry={self.entry_price}, qty={self.quantity}, "
                f"tp_tracking={self.tp_tracking})")
    
    def __repr__(self):
        return self.__str__()
