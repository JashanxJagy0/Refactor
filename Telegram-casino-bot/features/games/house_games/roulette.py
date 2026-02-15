"""
Roulette Game - Classic casino roulette
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes

try:
    from telegram.constants import ParseMode
except ImportError:
    pass

from features.games.base import BaseGame
from utils.crypto import get_provably_fair_result
from utils.decorators import check_banned, check_maintenance


class RouletteGame(BaseGame):
    """Classic roulette game (0-36)"""
    
    def __init__(self):
        super().__init__()
        self.game_type = "roulette"
        
        # Multipliers
        self.multipliers = {
            'single': 35.0,    # Single number
            'red': 2.0,        # Red/Black
            'black': 2.0,
            'even': 2.0,       # Even/Odd
            'odd': 2.0,
            'low': 2.0,        # 1-18/19-36
            'high': 2.0,
        }
        
        # Red numbers
        self.red_numbers = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
    
    @check_banned
    @check_maintenance
    async def start_game(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE",
                        bet_amount: float, bet_type: str, bet_value: int = None):
        """
        Start roulette game
        bet_type: 'single', 'red', 'black', 'even', 'odd', 'low', 'high'
        bet_value: number (0-36) for single bets
        """
        user = update.effective_user
        
        # Validate bet type
        if bet_type not in self.multipliers:
            await update.message.reply_text("❌ Invalid bet type")
            return
        
        # Validate single number
        if bet_type == 'single':
            if bet_value is None or bet_value < 0 or bet_value > 36:
                await update.message.reply_text("❌ Number must be 0-36")
                return
        
        # Validate bet
        valid, error = self.validate_bet(user.id, bet_amount)
        if not valid:
            await update.message.reply_text(f"❌ {error}")
            return
        
        # Create game session
        game_id = self.create_game_session(
            user.id,
            bet_amount,
            bet_type=bet_type,
            bet_value=bet_value
        )
        
        # Deduct bet
        if not self.deduct_bet(user.id, bet_amount):
            await update.message.reply_text("❌ Insufficient balance")
            return
        
        # Generate result
        game = self.get_game_session(game_id)
        result = get_provably_fair_result(
            game["server_seed"],
            game["client_seed"],
            game["nonce"],
            37  # 0-36
        )
        
        # Check win
        win = self._check_win(result, bet_type, bet_value)
        
        if win:
            multiplier = self.multipliers[bet_type]
            winnings = bet_amount * multiplier
            self.payout(user.id, winnings)
            
            self.complete_game(
                game_id,
                win=True,
                multiplier=multiplier,
                result_data=f"Result: {result}, Bet: {bet_type} {bet_value or ''}"
            )
            
            text = (
                f"🎰 <b>Roulette Win!</b> (ID: <code>{game_id}</code>)\n\n"
                f"🎲 Result: <b>{result}</b> {self._get_color_emoji(result)}\n"
                f"🎯 Your Bet: {bet_type} {bet_value or ''}\n"
                f"💸 Winnings: ${winnings:.2f}\n"
                f"🎯 Multiplier: {multiplier:.1f}x"
            )
        else:
            self.complete_game(
                game_id,
                win=False,
                multiplier=0.0,
                result_data=f"Result: {result}, Bet: {bet_type} {bet_value or ''}"
            )
            
            text = (
                f"🎰 <b>Roulette</b> (ID: <code>{game_id}</code>)\n\n"
                f"🎲 Result: <b>{result}</b> {self._get_color_emoji(result)}\n"
                f"🎯 Your Bet: {bet_type} {bet_value or ''}\n"
                f"❌ Lost: ${bet_amount:.2f}"
            )
        
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    
    def _check_win(self, result: int, bet_type: str, bet_value: int = None) -> bool:
        """Check if bet wins"""
        if bet_type == 'single':
            return result == bet_value
        elif bet_type == 'red':
            return result in self.red_numbers
        elif bet_type == 'black':
            return result not in self.red_numbers and result != 0
        elif bet_type == 'even':
            return result % 2 == 0 and result != 0
        elif bet_type == 'odd':
            return result % 2 == 1
        elif bet_type == 'low':
            return 1 <= result <= 18
        elif bet_type == 'high':
            return 19 <= result <= 36
        return False
    
    def _get_color_emoji(self, number: int) -> str:
        """Get color emoji for number"""
        if number == 0:
            return "🟢"
        elif number in self.red_numbers:
            return "🔴"
        else:
            return "⚫"
    
    async def handle_callback(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
        """Roulette is instant, no callbacks"""
        pass


# Create game instance
roulette_game = RouletteGame()
