"""
Blackjack Game - Classic card game
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

# Card definitions
SUITS = ['♠', '♥', '♦', '♣']
RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']


class BlackjackGame(BaseGame):
    """Blackjack card game"""
    
    def __init__(self):
        super().__init__()
        self.game_type = "blackjack"
        self.regular_multiplier = 1.94  # 3% house edge
        self.blackjack_multiplier = 2.425  # Natural blackjack payout
    
    def create_deck(self) -> list:
        """Create and shuffle a deck"""
        deck = [f"{rank}{suit}" for suit in SUITS for rank in RANKS]
        random.shuffle(deck)
        return deck
    
    def calculate_hand_value(self, hand: list) -> int:
        """Calculate hand value with proper ace handling"""
        value = 0
        aces = 0
        
        for card in hand:
            rank = card[:-1]  # Remove suit
            if rank == 'A':
                aces += 1
                value += 11
            elif rank in ['J', 'Q', 'K']:
                value += 10
            else:
                value += int(rank)
        
        # Adjust for aces if busting
        while value > 21 and aces > 0:
            value -= 10
            aces -= 1
        
        return value
    
    def hand_to_string(self, hand: list) -> str:
        """Convert hand to readable string"""
        return " ".join(hand)
    
    def create_game_keyboard(self, game_id: str, can_double: bool = False) -> "InlineKeyboardMarkup":
        """Create game action keyboard"""
        buttons = [
            [
                InlineKeyboardButton("🃏 Hit", callback_data=f"bj_hit_{game_id}"),
                InlineKeyboardButton("✋ Stand", callback_data=f"bj_stand_{game_id}")
            ]
        ]
        
        if can_double:
            buttons.append([
                InlineKeyboardButton("💰 Double Down", callback_data=f"bj_double_{game_id}")
            ])
        
        return InlineKeyboardMarkup(buttons)
    
    @check_banned
    @check_maintenance
    async def start_game(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE",
                        bet_amount: float):
        """Start blackjack game"""
        user = update.effective_user
        
        # Validate bet
        valid, error = self.validate_bet(user.id, bet_amount)
        if not valid:
            await update.message.reply_text(f"❌ {error}")
            return
        
        # Create deck and deal cards
        deck = self.create_deck()
        player_hand = [deck.pop(), deck.pop()]
        dealer_hand = [deck.pop(), deck.pop()]
        
        # Create game session
        game_id = self.create_game_session(
            user.id,
            bet_amount,
            deck=deck,
            player_hand=player_hand,
            dealer_hand=dealer_hand,
            doubled=False
        )
        
        # Deduct bet
        if not self.deduct_bet(user.id, bet_amount):
            await update.message.reply_text("❌ Insufficient balance")
            return
        
        # Check for natural blackjack
        player_value = self.calculate_hand_value(player_hand)
        dealer_value = self.calculate_hand_value(dealer_hand)
        
        if player_value == 21:
            # Player has blackjack
            if dealer_value == 21:
                # Push
                self.payout(user.id, bet_amount)
                self.complete_game(game_id, win=False, multiplier=0, result_data="Push - both blackjack")
                
                text = (
                    f"🃏 <b>Blackjack!</b> (ID: <code>{game_id}</code>)\n\n"
                    f"Your Hand: {self.hand_to_string(player_hand)} = 21\n"
                    f"Dealer: {self.hand_to_string(dealer_hand)} = 21\n\n"
                    "🤝 Push! Both have blackjack. Bet returned."
                )
            else:
                # Natural blackjack wins
                winnings = bet_amount * self.blackjack_multiplier
                self.payout(user.id, winnings)
                self.complete_game(game_id, win=True, multiplier=self.blackjack_multiplier, 
                                 result_data="Natural blackjack")
                
                text = (
                    f"🃏 <b>BLACKJACK!</b> (ID: <code>{game_id}</code>)\n\n"
                    f"Your Hand: {self.hand_to_string(player_hand)} = 21\n"
                    f"Dealer: {self.hand_to_string([dealer_hand[0], '🂠'])}\n\n"
                    f"💸 Won: ${winnings:.2f}\n"
                    f"🎯 Multiplier: {self.blackjack_multiplier:.2f}x"
                )
            
            await update.message.reply_text(text, parse_mode=ParseMode.HTML)
            return
        
        # Regular game - show initial state
        text = (
            f"🃏 <b>Blackjack Started!</b> (ID: <code>{game_id}</code>)\n\n"
            f"💰 Bet: ${bet_amount:.2f}\n\n"
            f"Your Hand: {self.hand_to_string(player_hand)} = {player_value}\n"
            f"Dealer: {self.hand_to_string([dealer_hand[0], '🂠'])}\n\n"
            "Choose your action:"
        )
        
        # Can only double on first turn
        can_double = True
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=self.create_game_keyboard(game_id, can_double)
        )
    
    @check_banned
    @check_maintenance
    async def handle_callback(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
        """Handle blackjack callbacks"""
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
        
        if action == "hit":
            await self._handle_hit(query, game_id, game)
        elif action == "stand":
            await self._handle_stand(query, game_id, game)
        elif action == "double":
            await self._handle_double(query, game_id, game)
    
    async def _handle_hit(self, query, game_id: str, game: dict):
        """Handle hit action"""
        # Deal card
        card = game["deck"].pop()
        game["player_hand"].append(card)
        
        player_value = self.calculate_hand_value(game["player_hand"])
        
        if player_value > 21:
            # Bust
            self.complete_game(game_id, win=False, multiplier=0, result_data="Player bust")
            
            text = (
                f"🃏 <b>Bust!</b> (ID: <code>{game_id}</code>)\n\n"
                f"Your Hand: {self.hand_to_string(game['player_hand'])} = {player_value}\n\n"
                f"💔 You busted! Lost: ${game['bet_amount']:.2f}"
            )
            
            await query.edit_message_text(text, parse_mode=ParseMode.HTML)
        else:
            # Continue playing
            text = (
                f"🃏 <b>Blackjack</b> (ID: <code>{game_id}</code>)\n\n"
                f"Your Hand: {self.hand_to_string(game['player_hand'])} = {player_value}\n"
                f"Dealer: {self.hand_to_string([game['dealer_hand'][0], '🂠'])}\n\n"
                "Choose your action:"
            )
            
            # Can't double after first hit
            await query.edit_message_text(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=self.create_game_keyboard(game_id, can_double=False)
            )
    
    async def _handle_stand(self, query, game_id: str, game: dict):
        """Handle stand action - dealer plays"""
        # Dealer plays (hits to 17)
        while self.calculate_hand_value(game["dealer_hand"]) < 17:
            game["dealer_hand"].append(game["deck"].pop())
        
        player_value = self.calculate_hand_value(game["player_hand"])
        dealer_value = self.calculate_hand_value(game["dealer_hand"])
        
        # Determine winner
        if dealer_value > 21:
            # Dealer bust
            winnings = game["bet_amount"] * self.regular_multiplier
            self.payout(game["user_id"], winnings)
            self.complete_game(game_id, win=True, multiplier=self.regular_multiplier, 
                             result_data="Dealer bust")
            
            result = f"🎉 Dealer busts! Won: ${winnings:.2f}"
        elif dealer_value > player_value:
            # Dealer wins
            self.complete_game(game_id, win=False, multiplier=0, result_data="Dealer wins")
            result = f"😢 Dealer wins. Lost: ${game['bet_amount']:.2f}"
        elif player_value > dealer_value:
            # Player wins
            winnings = game["bet_amount"] * self.regular_multiplier
            self.payout(game["user_id"], winnings)
            self.complete_game(game_id, win=True, multiplier=self.regular_multiplier, 
                             result_data="Player wins")
            result = f"🎉 You win! Won: ${winnings:.2f}"
        else:
            # Push
            self.payout(game["user_id"], game["bet_amount"])
            self.complete_game(game_id, win=False, multiplier=0, result_data="Push")
            result = "🤝 Push! Bet returned."
        
        text = (
            f"🃏 <b>Game Over!</b> (ID: <code>{game_id}</code>)\n\n"
            f"Your Hand: {self.hand_to_string(game['player_hand'])} = {player_value}\n"
            f"Dealer: {self.hand_to_string(game['dealer_hand'])} = {dealer_value}\n\n"
            f"{result}"
        )
        
        await query.edit_message_text(text, parse_mode=ParseMode.HTML)
    
    async def _handle_double(self, query, game_id: str, game: dict):
        """Handle double down - double bet, one card, then stand"""
        # Check balance for double
        from core.state import user_wallets
        if user_wallets.get(game["user_id"], 0) < game["bet_amount"]:
            await query.answer("❌ Insufficient balance to double!", show_alert=True)
            return
        
        # Deduct additional bet
        self.deduct_bet(game["user_id"], game["bet_amount"])
        game["bet_amount"] *= 2
        game["doubled"] = True
        
        # Deal one card
        card = game["deck"].pop()
        game["player_hand"].append(card)
        
        player_value = self.calculate_hand_value(game["player_hand"])
        
        if player_value > 21:
            # Bust
            self.complete_game(game_id, win=False, multiplier=0, result_data="Doubled and bust")
            
            text = (
                f"🃏 <b>Doubled & Bust!</b> (ID: <code>{game_id}</code>)\n\n"
                f"Your Hand: {self.hand_to_string(game['player_hand'])} = {player_value}\n\n"
                f"💔 You busted! Lost: ${game['bet_amount']:.2f}"
            )
            
            await query.edit_message_text(text, parse_mode=ParseMode.HTML)
        else:
            # Automatically stand after double
            await self._handle_stand(query, game_id, game)


# Create game instance
blackjack_game = BlackjackGame()
