"""
Game registry system
Manages all available games and their handlers
"""
from typing import Dict, Optional
from features.games.base import BaseGame


class GameRegistry:
    """Central registry for all casino games"""
    
    def __init__(self):
        self._games: Dict[str, BaseGame] = {}
    
    def register(self, game: BaseGame):
        """Register a game"""
        self._games[game.game_type] = game
    
    def get(self, game_type: str) -> Optional[BaseGame]:
        """Get a game by type"""
        return self._games.get(game_type)
    
    def get_all(self) -> Dict[str, BaseGame]:
        """Get all registered games"""
        return self._games.copy()
    
    def is_registered(self, game_type: str) -> bool:
        """Check if a game is registered"""
        return game_type in self._games


# Global registry instance
game_registry = GameRegistry()


def register_all_games():
    """Register all available games"""
    # Import and register house games
    try:
        from features.games.house_games.mines import mines_game
        game_registry.register(mines_game)
    except ImportError:
        pass
    
    try:
        from features.games.house_games.coinflip import coinflip_game
        game_registry.register(coinflip_game)
    except ImportError:
        pass
    
    try:
        from features.games.house_games.diceroll import diceroll_game
        game_registry.register(diceroll_game)
    except ImportError:
        pass
    
    try:
        from features.games.house_games.tower import tower_game
        game_registry.register(tower_game)
    except ImportError:
        pass
    
    try:
        from features.games.house_games.roulette import roulette_game
        game_registry.register(roulette_game)
    except ImportError:
        pass
    
    try:
        from features.games.house_games.slots import slots_game
        game_registry.register(slots_game)
    except ImportError:
        pass
    
    try:
        from features.games.house_games.keno import keno_game
        game_registry.register(keno_game)
    except ImportError:
        pass
    
    # Import and register single emoji games
    try:
        from features.games.emoji_games.single_emoji import (
            darts_single_game, soccer_single_game, basketball_single_game,
            bowling_single_game, slot_single_game
        )
        game_registry.register(darts_single_game)
        game_registry.register(soccer_single_game)
        game_registry.register(basketball_single_game)
        game_registry.register(bowling_single_game)
        game_registry.register(slot_single_game)
    except ImportError:
        pass


# Register games on import
register_all_games()
