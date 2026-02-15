"""
Dice Roll Game - Simple dice prediction game
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


class DiceRollGame(BaseGame):
    """Simple dice roll prediction game"""
    
    def __init__(self):
        super().__init__()
        self.game_type = "dice_roll"
        # Multipliers for each dice value (1-6)
        self.multipliers = {
            1: 5.82,  # Rare (lowest)
            2: 5.82,
            3: 5.82,
            4: 5.82,
            5: 5.82,
            6: 5.82   # Equal probability
        }
    
    @check_banned
    @check_maintenance
    async def start_game(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE",
                        bet_amount: float, prediction: int = 6):
        """Start dice roll game"""
        user = update.effective_user
        
        # Validate prediction
        if prediction < 1 or prediction > 6:
            await update.message.reply_text("❌ Prediction must be between 1 and 6")
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
            prediction=prediction
        )
        
        # Deduct bet
        if not self.deduct_bet(user.id, bet_amount):
            await update.message.reply_text("❌ Insufficient balance")
            return
        
        # Generate result using provably fair
        game = self.get_game_session(game_id)
        result = get_provably_fair_result(
            game["server_seed"],
            game["client_seed"],
            game["nonce"],
            6
        ) + 1  # 1-6
        
        # Check win
        if result == prediction:
            # WIN
            multiplier = self.multipliers[result]
            winnings = bet_amount * multiplier
            self.payout(user.id, winnings)
            
            self.complete_game(
                game_id,
                win=True,
                multiplier=multiplier,
                result_data=f"Predicted {prediction}, rolled {result}"
            )
            
            text = (
                f"🎲 <b>You Won!</b> (ID: <code>{game_id}</code>)\n\n"
                f"Prediction: {prediction} | Result: {result}\n"
                f"Winnings: <b>${winnings:.2f}</b>\n"
                f"Multiplier: {multiplier:.2f}x"
            )
        else:
            # LOSS
            self.complete_game(
                game_id,
                win=False,
                multiplier=0.0,
                result_data=f"Predicted {prediction}, rolled {result}"
            )
            
            text = (
                f"🎲 <b>You Lost!</b> (ID: <code>{game_id}</code>)\n\n"
                f"Prediction: {prediction} | Result: {result}\n"
                f"Lost: ${bet_amount:.2f}"
            )
        
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    
    async def handle_callback(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
        """Dice roll is instant, no callbacks needed"""
        pass


# Create game instance
diceroll_game = DiceRollGame()
