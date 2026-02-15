"""
Single Emoji Games - Simple emoji-based games with fixed multipliers
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


class SingleEmojiGame(BaseGame):
    """Base class for single emoji games"""
    
    def __init__(self, game_type: str, emoji: str, multiplier: float, win_values: list):
        super().__init__()
        self.game_type = game_type
        self.emoji = emoji
        self.multiplier = multiplier
        self.win_values = win_values
    
    @check_banned
    @check_maintenance
    async def start_game(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE",
                        bet_amount: float):
        """Start single emoji game"""
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
        
        # Send emoji (Telegram will animate)
        try:
            dice_msg = await update.message.reply_dice(emoji=self.emoji)
            
            # Wait for animation
            await asyncio.sleep(3)
            
            result_value = dice_msg.dice.value
            
            # Check win
            if result_value in self.win_values:
                winnings = bet_amount * self.multiplier
                self.payout(user.id, winnings)
                
                self.complete_game(
                    game_id,
                    win=True,
                    multiplier=self.multiplier,
                    result_data=f"Result: {result_value}"
                )
                
                await update.message.reply_text(
                    f"{self.emoji} <b>WIN!</b> (ID: <code>{game_id}</code>)\n\n"
                    f"Result: {result_value}\n"
                    f"💸 Won: ${winnings:.2f}\n"
                    f"🎯 Multiplier: {self.multiplier:.2f}x",
                    parse_mode=ParseMode.HTML
                )
            else:
                self.complete_game(
                    game_id,
                    win=False,
                    multiplier=0.0,
                    result_data=f"Result: {result_value}"
                )
                
                await update.message.reply_text(
                    f"{self.emoji} <b>Lost</b> (ID: <code>{game_id}</code>)\n\n"
                    f"Result: {result_value}\n"
                    f"❌ Lost: ${bet_amount:.2f}",
                    parse_mode=ParseMode.HTML
                )
        except Exception as e:
            # Refund on error
            self.payout(user.id, bet_amount)
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def handle_callback(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
        """Single emoji games are instant, no callbacks"""
        pass


# Create game instances for each emoji type
darts_single_game = SingleEmojiGame(
    game_type="darts_single",
    emoji="🎯",
    multiplier=1.15,
    win_values=[3, 4, 5, 6]  # Hit board
)

soccer_single_game = SingleEmojiGame(
    game_type="soccer_single",
    emoji="⚽",
    multiplier=1.53,
    win_values=[3, 4, 5]  # Goal scored
)

basketball_single_game = SingleEmojiGame(
    game_type="basketball_single",
    emoji="🏀",
    multiplier=2.25,
    win_values=[4, 5]  # Basket scored
)

bowling_single_game = SingleEmojiGame(
    game_type="bowling_single",
    emoji="🎳",
    multiplier=5.00,
    win_values=[6]  # Strike
)

slot_single_game = SingleEmojiGame(
    game_type="slot_single",
    emoji="🎰",
    multiplier=14.5,
    win_values=[1, 22, 43, 64]  # Any matching symbols
)
