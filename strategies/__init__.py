# Strategies package
from .falling_candles.strategy import FallingCandlesStrategy
from .xrp_pinescript.strategy_xrp_pinescript import XRPPineScriptStrategy
from .bnb_pinescript.strategy_bnb_pinescript import BNBPineScriptStrategy
from .red_candles.strategy_red_candles import RedCandlesSequenceStrategy

__all__ = [
    'FallingCandlesStrategy',
    'XRPPineScriptStrategy',
    'BNBPineScriptStrategy',
    'RedCandlesSequenceStrategy',
]
