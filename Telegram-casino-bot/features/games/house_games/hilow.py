"""
High-Low Card Game - Predict if next card is higher or lower
"""
from __future__ import annotations
from typing import TYPE_CHECKING
import random

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes

try:
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    from telegram.constants import ParseMode
except ImportError:
    pass

from features.games.base import BaseGame
from utils.decorators import check_banned, check_maintenance

# Card ranks
CARD_RANKS = {
    'A': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7,
    '8': 8, '9': 9, '10': 10, 'J': 11, 'Q': 12, 'K': 13
}
SUITS = ['♠', '♥', '♦', '♣']


class HighLowGame(BaseGame):
    """High-Low card prediction game"""
    
    def __init__(self):
        super().__init__()
        self.game_type = "hilow"
        self.base_multiplier = 1.35  # Base multiplier per correct guess
    
    def create_deck(self) -> list:
        """Create shuffled deck"""
        deck = [f"{rank}{suit}" for suit in SUITS for rank in CARD_RANKS.keys()]
        random.shuffle(deck)
        return deck
    
    def get_card_value(self, card: str) -> int:
        """Get numeric value of card"""
        rank = card[:-1]
        return CARD_RANKS[rank]
    
    def get_multiplier(self, streak: int) -> float:
        """Calculate multiplier based on streak"""
        return self.base_multiplier ** streak
    
    def create_game_keyboard(self, game_id: str, current_value: int) -> "InlineKeyboardMarkup":
        """Create game action keyboard"""
        buttons = []
        
        # Only show valid options based on current card
        if current_value > 1:  # Can go lower
            buttons.append(
                InlineKeyboardButton("⬇️ Lower", callback_data=f"hl_lower_{game_id}")
            )
        
        if current_value < 13:  # Can go higher
            buttons.append(
                InlineKeyboardButton("⬆️ Higher", callback_data=f"hl_higher_{game_id}")
            )
        
        # Always allow skip (safer option)
        buttons.append(
            InlineKeyboardButton("➡️ Skip", callback_data=f"hl_skip_{game_id}")
        )
        
        keyboard = [buttons]
        
        # Add cashout if streak > 0
        game = self.get_game_session(game_id)
        if game and game.get("streak", 0) > 0:
            multiplier = self.get_multiplier(game["streak"])
            potential = game["bet_amount"] * multiplier
            keyboard.append([
                InlineKeyboardButton(
                    f"💸 Cashout ${potential:.2f}",
                    callback_data=f"hl_cashout_{game_id}"
                )
            ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @check_banned
    @check_maintenance
    async def start_game(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE",
                        bet_amount: float):
        """Start high-low game"""
        user = update.effective_user
        
        # Validate bet
        valid, error = self.validate_bet(user.id, bet_amount)
        if not valid:
            await update.message.reply_text(f"❌ {error}")
            return
        
        # Create deck and draw first card
        deck = self.create_deck()
        current_card = deck.pop()
        
        # Create game session
        game_id = self.create_game_session(
            user.id,
            bet_amount,
            deck=deck,
            current_card=current_card,
            streak=0
        )
        
        # Deduct bet
        if not self.deduct_bet(user.id, bet_amount):
            await update.message.reply_text("❌ Insufficient balance")
            return
        
        current_value = self.get_card_value(current_card)
        
        text = (
            f"🎴 <b>High-Low Started!</b> (ID: <code>{game_id}</code>)\n\n"
            f"💰 Bet: ${bet_amount:.2f}\n"
            f"Current Card: {current_card} (Value: {current_value})\n"
            f"🔥 Streak: 0\n\n"
            "Will the next card be higher or lower?"
        )
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=self.create_game_keyboard(game_id, current_value)
        )
    
    @check_banned
    @check_maintenance
    async def handle_callback(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
        """Handle high-low callbacks"""
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
        
        # Check if active
        if game["status"] != "active":
            await query.answer("❌ This game has already ended.", show_alert=True)
            return
        
        if action == "cashout":
            await self._handle_cashout(query, game_id, game)
        elif action in ["higher", "lower", "skip"]:
            await self._handle_prediction(query, game_id, game, action)
    
    async def _handle_prediction(self, query, game_id: str, game: dict, prediction: str):
        """Handle card prediction"""
        # Draw next card
        if not game["deck"]:
            # Deck empty - force cashout
            await self._handle_cashout(query, game_id, game)
            return
        
        next_card = game["deck"].pop()
        current_value = self.get_card_value(game["current_card"])
        next_value = self.get_card_value(next_card)
        
        # Determine if prediction is correct
        correct = False
        if prediction == "higher" and next_value > current_value:
            correct = True
        elif prediction == "lower" and next_value < current_value:
            correct = True
        elif prediction == "skip" and next_value != current_value:
            correct = True
        elif next_value == current_value:  # Same value always loses
            correct = False
        
        if correct:
            # Correct prediction - increase streak
            game["streak"] += 1
            game["current_card"] = next_card
            
            multiplier = self.get_multiplier(game["streak"])
            potential = game["bet_amount"] * multiplier
            
            text = (
                f"✅ <b>Correct!</b> (ID: <code>{game_id}</code>)\n\n"
                f"Previous: {game['current_card'][:-1]} → New: {next_card}\n"
                f"🔥 Streak: {game['streak']}\n"
                f"💰 Current Value: ${potential:.2f}\n"
                f"🎯 Multiplier: {multiplier:.2f}x\n\n"
                "Predict next card or cash out:"
            )
            
            await query.edit_message_text(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=self.create_game_keyboard(game_id, next_value)
            )
        else:
            # Wrong prediction - lose
            self.complete_game(
                game_id,
                win=False,
                multiplier=0.0,
                result_data=f"Prediction: {prediction}, Current: {current_value}, Next: {next_value}"
            )
            
            text = (
                f"❌ <b>Wrong!</b> (ID: <code>{game_id}</code>)\n\n"
                f"Previous: {game['current_card']} ({current_value})\n"
                f"Next: {next_card} ({next_value})\n"
                f"Prediction: {prediction.upper()}\n\n"
                f"🔥 Streak: {game['streak']}\n"
                f"💔 Lost: ${game['bet_amount']:.2f}"
            )
            
            await query.edit_message_text(text, parse_mode=ParseMode.HTML)
    
    async def _handle_cashout(self, query, game_id: str, game: dict):
        """Handle cashout"""
        if game["streak"] == 0:
            await query.answer("❌ No winnings to cash out! Make at least one correct guess.", show_alert=True)
            return
        
        multiplier = self.get_multiplier(game["streak"])
        winnings = game["bet_amount"] * multiplier
        
        self.payout(game["user_id"], winnings)
        self.complete_game(
            game_id,
            win=True,
            multiplier=multiplier,
            result_data=f"Cashed out with streak {game['streak']}"
        )
        
        profit = winnings - game["bet_amount"]
        
        text = (
            f"💸 <b>Cashed Out!</b> (ID: <code>{game_id}</code>)\n\n"
            f"🔥 Streak: {game['streak']}\n"
            f"�� Profit: ${profit:.2f}\n"
            f"💸 Total Payout: ${winnings:.2f}\n"
            f"🎯 Multiplier: {multiplier:.2f}x"
        )
        
        await query.edit_message_text(text, parse_mode=ParseMode.HTML)


# Create game instance
hilow_game = HighLowGame()
