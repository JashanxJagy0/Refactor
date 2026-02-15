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
    
    # More games will be registered as they're implemented
    # TODO: Register other games


# Register games on import
register_all_games()
