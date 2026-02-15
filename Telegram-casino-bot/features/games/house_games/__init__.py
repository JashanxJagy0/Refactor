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

__all__ = ['mines_game', 'MINES_AVAILABLE']
