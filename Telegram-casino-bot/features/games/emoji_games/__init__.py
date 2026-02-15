"""
Emoji games module
Contains all Telegram emoji-based games
"""

# Import single emoji games
try:
    from features.games.emoji_games.single_emoji import (
        darts_single_game, soccer_single_game, basketball_single_game,
        bowling_single_game, slot_single_game
    )
    SINGLE_EMOJI_AVAILABLE = True
except ImportError:
    SINGLE_EMOJI_AVAILABLE = False
    darts_single_game = None
    soccer_single_game = None
    basketball_single_game = None
    bowling_single_game = None
    slot_single_game = None

__all__ = [
    'darts_single_game', 'soccer_single_game', 'basketball_single_game',
    'bowling_single_game', 'slot_single_game', 'SINGLE_EMOJI_AVAILABLE'
]
