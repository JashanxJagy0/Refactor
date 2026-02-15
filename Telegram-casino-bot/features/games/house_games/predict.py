"""
Predict Game - Dice up/down prediction
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
from utils.decorators import check_banned, check_maintenance
import asyncio


class PredictGame(BaseGame):
    """Predict if dice will be up (4-6) or down (1-3)"""
    
    def __init__(self):
        super().__init__()
        self.game_type = "predict"
        self.multiplier = 2.0  # 2x on win
    
    @check_banned
    @check_maintenance
    async def start_game(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE",
                        bet_amount: float, direction: str):
        """
        Start predict game
        direction: 'up' (4-6) or 'down' (1-3)
        """
        user = update.effective_user
        
        # Validate direction
        if direction.lower() not in ['up', 'down']:
            await update.message.reply_text("❌ Direction must be 'up' or 'down'")
            return
        
        direction = direction.lower()
        
        # Validate bet
        valid, error = self.validate_bet(user.id, bet_amount)
        if not valid:
            await update.message.reply_text(f"❌ {error}")
            return
        
        # Create game session
        game_id = self.create_game_session(
            user.id,
            bet_amount,
            direction=direction
        )
        
        # Deduct bet
        if not self.deduct_bet(user.id, bet_amount):
            await update.message.reply_text("❌ Insufficient balance")
            return
        
        # Send dice
        try:
            await update.message.reply_text("Rolling the dice... 🎲")
            await asyncio.sleep(0.5)
            
            dice_msg = await update.message.reply_dice(emoji="🎲")
            
            # Wait for animation
            await asyncio.sleep(4)
            
            outcome = dice_msg.dice.value
            
            # Determine win
            win = (direction == "up" and outcome in [4, 5, 6]) or \
                  (direction == "down" and outcome in [1, 2, 3])
            
            if win:
                winnings = bet_amount * self.multiplier
                self.payout(user.id, winnings)
                
                self.complete_game(
                    game_id,
                    win=True,
                    multiplier=self.multiplier,
                    result_data=f"Direction: {direction}, Result: {outcome}"
                )
                
                text = (
                    f"🎲 <b>Predict Win!</b> (ID: <code>{game_id}</code>)\n\n"
                    f"Result: {outcome}\n"
                    f"Prediction: {direction.upper()}\n"
                    f"💸 Won: ${winnings:.2f}\n"
                    f"🎯 Multiplier: {self.multiplier:.1f}x"
                )
            else:
                self.complete_game(
                    game_id,
                    win=False,
                    multiplier=0.0,
                    result_data=f"Direction: {direction}, Result: {outcome}"
                )
                
                text = (
                    f"🎲 <b>Predict</b> (ID: <code>{game_id}</code>)\n\n"
                    f"Result: {outcome}\n"
                    f"Prediction: {direction.upper()}\n"
                    f"❌ Lost: ${bet_amount:.2f}"
                )
            
            await update.message.reply_text(text, parse_mode=ParseMode.HTML)
            
        except Exception as e:
            # Refund on error
            self.payout(user.id, bet_amount)
            await update.message.reply_text(f"❌ Error: {e}. Bet refunded.")
    
    async def handle_callback(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
        """Predict is instant, no callbacks"""
        pass


# Create game instance
predict_game = PredictGame()
