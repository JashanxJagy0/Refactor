"""
Keno Game - Number selection game
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


class KenoGame(BaseGame):
    """Keno number selection game"""
    
    def __init__(self):
        super().__init__()
        self.game_type = "keno"
        
        # Payout table (matches: multiplier)
        self.payouts = {
            1: {1: 3.5},
            2: {2: 9.0},
            3: {2: 1.5, 3: 25.0},
            4: {2: 1.0, 3: 4.0, 4: 75.0},
            5: {3: 2.5, 4: 10.0, 5: 200.0},
            6: {3: 1.5, 4: 5.0, 5: 25.0, 6: 500.0},
            7: {4: 2.5, 5: 10.0, 6: 50.0, 7: 1000.0},
            8: {5: 5.0, 6: 20.0, 7: 100.0, 8: 2000.0},
        }
    
    @check_banned
    @check_maintenance
    async def start_game(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE",
                        bet_amount: float, numbers: list):
        """
        Start keno game
        numbers: list of 1-8 numbers (1-80)
        """
        user = update.effective_user
        
        # Validate numbers
        if not numbers or len(numbers) < 1 or len(numbers) > 8:
            await update.message.reply_text("❌ Pick 1-8 numbers")
            return
        
        if not all(1 <= n <= 80 for n in numbers):
            await update.message.reply_text("❌ Numbers must be 1-80")
            return
        
        if len(numbers) != len(set(numbers)):
            await update.message.reply_text("❌ No duplicate numbers")
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
            picked_numbers=numbers
        )
        
        # Deduct bet
        if not self.deduct_bet(user.id, bet_amount):
            await update.message.reply_text("❌ Insufficient balance")
            return
        
        # Generate 10 drawn numbers
        game = self.get_game_session(game_id)
        drawn_numbers = []
        for i in range(10):
            num = get_provably_fair_result(
                game["server_seed"],
                game["client_seed"],
                game["nonce"] + i,
                80
            ) + 1
            if num not in drawn_numbers:
                drawn_numbers.append(num)
        
        # Count matches
        matches = len(set(numbers) & set(drawn_numbers))
        
        # Check payout
        num_picked = len(numbers)
        multiplier = self.payouts.get(num_picked, {}).get(matches, 0)
        
        if multiplier > 0:
            winnings = bet_amount * multiplier
            self.payout(user.id, winnings)
            
            self.complete_game(
                game_id,
                win=True,
                multiplier=multiplier,
                result_data=f"Picked: {numbers}, Drawn: {drawn_numbers}, Matches: {matches}"
            )
            
            text = (
                f"🎱 <b>Keno Win!</b> (ID: <code>{game_id}</code>)\n\n"
                f"🎯 Your Numbers: {numbers}\n"
                f"🎲 Drawn: {drawn_numbers}\n"
                f"✅ Matches: {matches}/{num_picked}\n"
                f"💸 Won: ${winnings:.2f}\n"
                f"🎯 Multiplier: {multiplier:.1f}x"
            )
        else:
            self.complete_game(
                game_id,
                win=False,
                multiplier=0.0,
                result_data=f"Picked: {numbers}, Drawn: {drawn_numbers}, Matches: {matches}"
            )
            
            text = (
                f"🎱 <b>Keno</b> (ID: <code>{game_id}</code>)\n\n"
                f"🎯 Your Numbers: {numbers}\n"
                f"🎲 Drawn: {drawn_numbers}\n"
                f"✅ Matches: {matches}/{num_picked}\n"
                f"❌ Lost: ${bet_amount:.2f}"
            )
        
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    
    async def handle_callback(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
        """Keno is instant, no callbacks"""
        pass


# Create game instance
keno_game = KenoGame()
