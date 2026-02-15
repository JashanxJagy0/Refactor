"""
Slots Game - Telegram slot machine
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


class SlotsGame(BaseGame):
    """Telegram slot machine game"""
    
    def __init__(self):
        super().__init__()
        self.game_type = "slots"
        
        # Slot values and multipliers
        self.multipliers = {
            64: 14.5,  # Triple 7s (jackpot)
            1: 5.82,   # Bar
            22: 5.82,  # Grape
            43: 5.82,  # Lemon
        }
    
    @check_banned
    @check_maintenance
    async def start_game(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE",
                        bet_amount: float):
        """Start slots game"""
        user = update.effective_user
        
        # Validate bet
        valid, error = self.validate_bet(user.id, bet_amount)
        if not valid:
            await update.message.reply_text(f"❌ {error}")
            return
        
        # Create game session
        game_id = self.create_game_session(user.id, bet_amount)
        
        # Deduct bet
        if not self.deduct_bet(user.id, bet_amount):
            await update.message.reply_text("❌ Insufficient balance")
            return
        
        # Send slot machine (Telegram will animate)
        try:
            dice_msg = await update.message.reply_dice(emoji="🎰")
            
            # Store for later processing
            import asyncio
            await asyncio.sleep(3)  # Wait for animation
            
            result_value = dice_msg.dice.value
            
            # Check win
            if result_value in self.multipliers:
                multiplier = self.multipliers[result_value]
                winnings = bet_amount * multiplier
                self.payout(user.id, winnings)
                
                self.complete_game(
                    game_id,
                    win=True,
                    multiplier=multiplier,
                    result_data=f"Slot value: {result_value}"
                )
                
                await update.message.reply_text(
                    f"🎰 <b>JACKPOT!</b> (ID: <code>{game_id}</code>)\n\n"
                    f"💸 Won: ${winnings:.2f}\n"
                    f"🎯 Multiplier: {multiplier:.2f}x",
                    parse_mode=ParseMode.HTML
                )
            else:
                self.complete_game(
                    game_id,
                    win=False,
                    multiplier=0.0,
                    result_data=f"Slot value: {result_value}"
                )
                
                await update.message.reply_text(
                    f"🎰 <b>Slots</b> (ID: <code>{game_id}</code>)\n\n"
                    f"❌ Lost: ${bet_amount:.2f}",
                    parse_mode=ParseMode.HTML
                )
        except Exception as e:
            # Refund on error
            self.payout(user.id, bet_amount)
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def handle_callback(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
        """Slots is instant, no callbacks"""
        pass


# Create game instance
slots_game = SlotsGame()
