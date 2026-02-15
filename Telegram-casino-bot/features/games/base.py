"""
Base class for all casino games
Provides common functionality for game implementation
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Dict, Optional, Any
from abc import ABC, abstractmethod
import secrets
from datetime import datetime, timezone

if TYPE_CHECKING:
    from telegram import Update, InlineKeyboardMarkup
    from telegram.ext import ContextTypes

from core import user_wallets, user_stats, game_sessions, save_user_data
from utils.crypto import get_user_seeds, increment_user_nonce, store_provably_fair_record


class BaseGame(ABC):
    """Base class for all casino games"""
    
    def __init__(self):
        self.game_type = "base"  # Override in subclass
        self.min_bet = 0.1
        self.max_bet = 10000.0
    
    def generate_game_id(self, prefix: str = "GM") -> str:
        """Generate unique game ID"""
        return f"{prefix}-{secrets.token_hex(8)}"
    
    def create_game_session(self, user_id: int, bet_amount: float, **kwargs) -> str:
        """
        Create a new game session
        
        Args:
            user_id: Player's user ID
            bet_amount: Bet amount in USD
            **kwargs: Additional game-specific data
            
        Returns:
            game_id: Unique game identifier
        """
        game_id = self.generate_game_id(self.game_type.upper()[:2])
        seeds = get_user_seeds(user_id)
        
        game_sessions[game_id] = {
            "id": game_id,
            "game_type": self.game_type,
            "user_id": user_id,
            "bet_amount": bet_amount,
            "status": "active",
            "timestamp": str(datetime.now(timezone.utc)),
            "server_seed": seeds["server_seed"],
            "client_seed": seeds["client_seed"],
            "nonce": seeds["nonce"],
            **kwargs
        }
        
        # Track in user stats
        if user_id in user_stats:
            if 'game_sessions' not in user_stats[user_id]:
                user_stats[user_id]['game_sessions'] = []
            user_stats[user_id]['game_sessions'].append(game_id)
        
        return game_id
    
    def deduct_bet(self, user_id: int, amount: float) -> bool:
        """
        Deduct bet amount from user's balance
        
        Returns:
            True if successful, False if insufficient balance
        """
        if user_wallets.get(user_id, 0.0) < amount:
            return False
        
        user_wallets[user_id] -= amount
        save_user_data(user_id)
        return True
    
    def payout(self, user_id: int, amount: float):
        """Add winnings to user's balance"""
        user_wallets[user_id] = user_wallets.get(user_id, 0.0) + amount
        save_user_data(user_id)
    
    def complete_game(self, game_id: str, win: bool, multiplier: float = 0.0, 
                     result_data: str = ""):
        """
        Complete a game and update stats
        
        Args:
            game_id: Game identifier
            win: Whether player won
            multiplier: Win multiplier
            result_data: Additional result information for provably fair
        """
        game = game_sessions.get(game_id)
        if not game:
            return
        
        game["status"] = "completed"
        game["win"] = win
        game["multiplier"] = multiplier
        
        user_id = game["user_id"]
        
        # Increment nonce for provably fair
        increment_user_nonce(user_id)
        
        # Store provably fair record
        store_provably_fair_record(
            game_id, 
            game["game_type"],
            game["server_seed"],
            game["client_seed"],
            game["nonce"],
            result_data
        )
        
        # Update user stats
        self.update_stats(user_id, game_id, game["bet_amount"], win, multiplier)
        save_user_data(user_id)
    
    def update_stats(self, user_id: int, game_id: str, bet_amount: float, 
                    win: bool, multiplier: float):
        """Update user statistics after game"""
        if user_id not in user_stats:
            return
        
        stats = user_stats[user_id]
        
        # Update general stats
        if "bets" not in stats:
            stats["bets"] = {"count": 0, "amount": 0.0}
        stats["bets"]["count"] += 1
        stats["bets"]["amount"] += bet_amount
        
        if win:
            if "wins" not in stats:
                stats["wins"] = 0
            stats["wins"] += 1
            
            winnings = bet_amount * multiplier
            if "total_won" not in stats:
                stats["total_won"] = 0.0
            stats["total_won"] += winnings
        else:
            if "losses" not in stats:
                stats["losses"] = 0
            stats["losses"] += 1
            
            if "total_lost" not in stats:
                stats["total_lost"] = 0.0
            stats["total_lost"] += bet_amount
        
        # Update game-specific stats
        game_stats_key = f"{self.game_type}_stats"
        if game_stats_key not in stats:
            stats[game_stats_key] = {"played": 0, "won": 0, "lost": 0}
        
        stats[game_stats_key]["played"] += 1
        if win:
            stats[game_stats_key]["won"] += 1
        else:
            stats[game_stats_key]["lost"] += 1
    
    def validate_bet(self, user_id: int, bet_amount: float) -> tuple[bool, Optional[str]]:
        """
        Validate bet amount
        
        Returns:
            (valid, error_message) tuple
        """
        if bet_amount < self.min_bet:
            return False, f"Minimum bet is ${self.min_bet:.2f}"
        
        if bet_amount > self.max_bet:
            return False, f"Maximum bet is ${self.max_bet:.2f}"
        
        if user_wallets.get(user_id, 0.0) < bet_amount:
            return False, "Insufficient balance"
        
        return True, None
    
    @abstractmethod
    async def start_game(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE", 
                        bet_amount: float, **kwargs):
        """Start the game (implement in subclass)"""
        pass
    
    @abstractmethod
    async def handle_callback(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
        """Handle game callbacks (implement in subclass)"""
        pass
    
    def get_game_session(self, game_id: str) -> Optional[Dict[str, Any]]:
        """Get game session by ID"""
        return game_sessions.get(game_id)
    
    def is_player_game(self, game_id: str, user_id: int) -> bool:
        """Check if game belongs to user"""
        game = self.get_game_session(game_id)
        return game is not None and game.get("user_id") == user_id
