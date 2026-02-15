"""
House games module
Contains all casino-style games where players play against the house
"""
from features.games.base import BaseGame

# Import individual games
try:
    from features.games.house_games.mines import mines_game
    MINES_AVAILABLE = True
except ImportError:
    MINES_AVAILABLE = False
    mines_game = None

try:
    from features.games.house_games.coinflip import coinflip_game
    COINFLIP_AVAILABLE = True
except ImportError:
    COINFLIP_AVAILABLE = False
    coinflip_game = None

try:
    from features.games.house_games.diceroll import diceroll_game
    DICEROLL_AVAILABLE = True
except ImportError:
    DICEROLL_AVAILABLE = False
    diceroll_game = None

__all__ = [
    'mines_game', 'MINES_AVAILABLE',
    'coinflip_game', 'COINFLIP_AVAILABLE',
    'diceroll_game', 'DICEROLL_AVAILABLE'
]
