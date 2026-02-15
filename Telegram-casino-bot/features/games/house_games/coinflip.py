"""
Coin Flip Game - Simple heads/tails prediction with streak multipliers
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes

try:
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    from telegram.constants import ParseMode
except ImportError:
    pass

from features.games.base import BaseGame
from utils.crypto import get_provably_fair_result
from utils.decorators import check_banned, check_maintenance


class CoinFlipGame(BaseGame):
    """Coin flip game with progressive multipliers"""
    
    def __init__(self):
        super().__init__()
        self.game_type = "coin_flip"
        self.base_multiplier = 1.94  # 3% house edge
    
    def get_multiplier(self, streak: int) -> float:
        """Calculate multiplier based on streak (2x per win)"""
        if streak == 0:
            return self.base_multiplier
        return self.base_multiplier * (2 ** (streak - 1))
    
    @check_banned
    @check_maintenance
    async def start_game(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE",
                        bet_amount: float):
        """Start a new coin flip game"""
        user = update.effective_user
        
        # Validate bet
        valid, error = self.validate_bet(user.id, bet_amount)
        if not valid:
            await update.message.reply_text(f"❌ {error}")
            return
        
        # Create game session
        game_id = self.create_game_session(
            user.id,
            bet_amount,
            streak=0
        )
        
        # Deduct bet
        if not self.deduct_bet(user.id, bet_amount):
            await update.message.reply_text("❌ Insufficient balance")
            return
        
        # Create choice buttons
        keyboard = [
            [
                InlineKeyboardButton("🪙 Heads", callback_data=f"flip_pick_{game_id}_Heads"),
                InlineKeyboardButton("🪙 Tails", callback_data=f"flip_pick_{game_id}_Tails")
            ]
        ]
        
        text = (
            f"🪙 <b>Coin Flip Started!</b> (ID: <code>{game_id}</code>)\n\n"
            f"💰 Bet: ${bet_amount:.2f}\n"
            "Choose Heads or Tails!\n\n"
            f"🎯 Current Multiplier: {self.base_multiplier:.2f}x"
        )
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    @check_banned
    @check_maintenance
    async def handle_callback(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
        """Handle coin flip callbacks"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        parts = query.data.split("_")
        
        if len(parts) < 3:
            return
        
        action = parts[1]
        game_id = parts[2]
        
        game = self.get_game_session(game_id)
        if not game:
            await query.edit_message_text("❌ Game not found or has ended.")
            return
        
        # Check ownership
        if not self.is_player_game(game_id, user.id):
            await query.answer("❌ This is not your game!", show_alert=True)
            return
        
        # Check if game is active
        if game["status"] != "active":
            await query.answer("❌ This game has already ended.", show_alert=True)
            return
        
        if action == "pick" and len(parts) >= 4:
            pick = parts[3]
            await self._handle_pick(query, game_id, game, pick)
        elif action == "cashout":
            await self._handle_cashout(query, game_id, game)
    
    async def _handle_pick(self, query, game_id: str, game: dict, pick: str):
        """Handle player's pick"""
        # Increment nonce for provably fair
        game["nonce"] += 1
        
        # Generate result (0=Heads, 1=Tails)
        result_num = get_provably_fair_result(
            game["server_seed"],
            game["client_seed"],
            game["nonce"],
            2
        )
        bot_choice = "Heads" if result_num == 0 else "Tails"
        
        if pick == bot_choice:
            # WIN - increase streak
            game["streak"] += 1
            multiplier = self.get_multiplier(game["streak"])
            win_amount = game["bet_amount"] * multiplier
            next_multiplier = self.get_multiplier(game["streak"] + 1)
            
            # Create continue/cashout buttons
            keyboard = [
                [
                    InlineKeyboardButton("🪙 Heads", callback_data=f"flip_pick_{game_id}_Heads"),
                    InlineKeyboardButton("🪙 Tails", callback_data=f"flip_pick_{game_id}_Tails")
                ],
                [
                    InlineKeyboardButton(f"💸 Cash Out ${win_amount:.2f}", 
                                       callback_data=f"flip_cashout_{game_id}")
                ]
            ]
            
            text = (
                f"🎉 <b>Correct!</b> The coin landed on {pick}!\n\n"
                f"💰 Current Win: <b>${win_amount:.2f}</b>\n"
                f"🔥 Streak: {game['streak']}\n"
                f"🎯 Next Multiplier: {next_multiplier:.2f}x\n\n"
                "Continue playing or cash out?"
            )
            
            await query.edit_message_text(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            # LOSS - game over
            self.complete_game(
                game_id,
                win=False,
                multiplier=0.0,
                result_data=f"Picked {pick}, landed on {bot_choice}. Streak: {game['streak']}"
            )
            
            text = (
                f"❌ <b>Wrong!</b> You picked {pick}, but the coin landed on {bot_choice}.\n\n"
                f"💔 You lost your bet of ${game['bet_amount']:.2f}\n"
                f"🎯 Your streak was: {game['streak']}"
            )
            
            await query.edit_message_text(text, parse_mode=ParseMode.HTML)
    
    async def _handle_cashout(self, query, game_id: str, game: dict):
        """Handle cash out"""
        if game["streak"] == 0:
            await query.answer("❌ No winnings to cash out!", show_alert=True)
            return
        
        multiplier = self.get_multiplier(game["streak"])
        win_amount = game["bet_amount"] * multiplier
        
        # Payout
        self.payout(game["user_id"], win_amount)
        
        # Complete game
        self.complete_game(
            game_id,
            win=True,
            multiplier=multiplier,
            result_data=f"Cashed out with streak {game['streak']}, Multiplier: {multiplier:.2f}x"
        )
        
        text = (
            f"💸 <b>Cashed Out!</b> (ID: <code>{game_id}</code>)\n\n"
            f"You won <b>${win_amount:.2f}</b> with a {game['streak']} win streak!\n"
            f"Final Multiplier: <b>{multiplier:.2f}x</b>"
        )
        
        await query.edit_message_text(text, parse_mode=ParseMode.HTML)


# Create game instance
coinflip_game = CoinFlipGame()
