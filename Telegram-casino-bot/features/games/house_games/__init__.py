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

try:
    from features.games.house_games.tower import tower_game
    TOWER_AVAILABLE = True
except ImportError:
    TOWER_AVAILABLE = False
    tower_game = None

try:
    from features.games.house_games.roulette import roulette_game
    ROULETTE_AVAILABLE = True
except ImportError:
    ROULETTE_AVAILABLE = False
    roulette_game = None

try:
    from features.games.house_games.slots import slots_game
    SLOTS_AVAILABLE = True
except ImportError:
    SLOTS_AVAILABLE = False
    slots_game = None

try:
    from features.games.house_games.keno import keno_game
    KENO_AVAILABLE = True
except ImportError:
    KENO_AVAILABLE = False
    keno_game = None

__all__ = [
    'mines_game', 'MINES_AVAILABLE',
    'coinflip_game', 'COINFLIP_AVAILABLE',
    'diceroll_game', 'DICEROLL_AVAILABLE',
    'tower_game', 'TOWER_AVAILABLE',
    'roulette_game', 'ROULETTE_AVAILABLE',
    'slots_game', 'SLOTS_AVAILABLE',
    'keno_game', 'KENO_AVAILABLE',
]
