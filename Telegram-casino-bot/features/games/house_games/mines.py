"""
Mines Game - Interactive grid-based game
Players reveal tiles to find gems while avoiding mines
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
    from telegram.ext import ContextTypes

try:
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    from telegram.constants import ParseMode
except ImportError:
    pass

from features.games.base import BaseGame
from utils.crypto import generate_mine_positions
from utils.decorators import check_banned, check_maintenance


# Mines multiplier table with 2% house edge
MINES_MULT_TABLE = {
    1: {1: 1.01, 2: 1.06, 3: 1.1, 4: 1.16, 5: 1.22, 6: 1.27, 7: 1.34, 8: 1.43, 9: 1.52, 10: 1.62, 
        11: 1.73, 12: 1.86, 13: 2.02, 14: 2.21, 15: 2.42, 16: 2.69, 17: 3.03, 18: 3.47, 19: 4.04,
        20: 4.85, 21: 6.07, 22: 8.08, 23: 12.12, 24: 24.25},
    2: {1: 1.06, 2: 1.15, 3: 1.26, 4: 1.38, 5: 1.53, 6: 1.71, 7: 1.9, 8: 2.14, 9: 2.42, 10: 2.77,
        11: 3.19, 12: 3.73, 13: 4.41, 14: 5.29, 15: 6.47, 16: 8.08, 17: 10.4, 18: 13.86, 19: 19.4,
        20: 29.11, 21: 48.51, 22: 97.02, 23: 291.06},
    3: {1: 1.12, 2: 1.29, 3: 1.5, 4: 1.78, 5: 2.14, 6: 2.61, 7: 3.26, 8: 4.17, 9: 5.46, 10: 7.33,
        11: 10.15, 12: 14.65, 13: 22.2, 14: 36.3, 15: 64.66, 16: 127.33, 17: 291.06, 18: 850.86,
        19: 3828.86, 20: 38288.57, 21: 1337099.81},
    5: {1: 1.26, 2: 1.71, 3: 2.42, 4: 3.64, 5: 5.83, 6: 10.0, 7: 18.33, 8: 36.67, 9: 80.37,
        10: 200.92, 11: 582.69, 12: 1998.46, 13: 8326.93, 14: 44945.04, 15: 359560.29,
        16: 5393404.35, 17: 269670217.43, 18: 134835108.71, 19: 134835108.71},
    10: {1: 2.14, 2: 5.46, 3: 16.49, 4: 58.72, 5: 257.17, 6: 1418.46, 7: 10012.19, 8: 100121.95,
         9: 1701472.11, 10: 85073605.53, 11: 12761040829.55, 12: 14113834476.72, 13: 14113834476.72,
         14: 14113834476.72},
    15: {1: 5.83, 2: 41.28, 3: 412.84, 4: 6041.89, 5: 150047.24, 6: 9002834.7, 7: 2701850409.48,
         8: 54036008189.61, 9: 54036008189.61},
    20: {1: 41.28, 2: 1861.72, 3: 372344.08, 4: 372344.08},
    24: {1: 24.25}
}


class MinesGame(BaseGame):
    """Mines game implementation"""
    
    def __init__(self):
        super().__init__()
        self.game_type = "mines"
        self.total_cells = 25  # 5x5 grid
    
    def get_multiplier(self, num_mines: int, safe_picks: int) -> float:
        """Get multiplier for number of mines and safe picks"""
        if safe_picks == 0:
            return 1.0
        try:
            return MINES_MULT_TABLE[num_mines][safe_picks]
        except KeyError:
            return 1.0
    
    def create_keyboard(self, game_id: str, reveal: bool = False) -> "InlineKeyboardMarkup":
        """Create the mines grid keyboard"""
        game = self.get_game_session(game_id)
        if not game:
            return InlineKeyboardMarkup([])
        
        buttons = []
        for i in range(1, self.total_cells + 1):
            if i in game["picks"]:
                emoji = "✅"
            elif reveal and i in game["mines"]:
                emoji = "💥"
            elif reveal:
                emoji = "💎"
            else:
                emoji = "❓"
            
            buttons.append(InlineKeyboardButton(
                emoji, 
                callback_data=f"mines_pick_{game_id}_{i}"
            ))
        
        # Create 5x5 grid
        keyboard = [buttons[i:i+5] for i in range(0, len(buttons), 5)]
        
        # Add cashout button if there are picks
        if game["status"] == "active" and game["picks"]:
            safe_picks = len(game["picks"])
            multiplier = self.get_multiplier(game["num_mines"], safe_picks)
            winnings = game["bet_amount"] * multiplier
            cashout_text = f"💸 Cashout (${winnings:.2f})"
            keyboard.append([
                InlineKeyboardButton(
                    cashout_text, 
                    callback_data=f"mines_cashout_{game_id}"
                )
            ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @check_banned
    @check_maintenance
    async def start_game(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE",
                        bet_amount: float, num_mines: int = 3):
        """Start a new mines game"""
        user = update.effective_user
        
        # Validate bet
        valid, error = self.validate_bet(user.id, bet_amount)
        if not valid:
            await update.message.reply_text(f"❌ {error}")
            return
        
        # Validate num_mines
        if num_mines < 1 or num_mines > 24:
            await update.message.reply_text("❌ Number of mines must be between 1 and 24")
            return
        
        # Get provably fair seeds
        from utils.crypto import get_user_seeds
        seeds = get_user_seeds(user.id)
        
        # Generate mine positions
        mine_positions = generate_mine_positions(
            seeds["server_seed"],
            seeds["client_seed"],
            seeds["nonce"],
            num_mines
        )
        
        # Create game session
        game_id = self.create_game_session(
            user.id,
            bet_amount,
            mines=mine_positions,
            picks=[],
            total_cells=self.total_cells,
            num_mines=num_mines
        )
        
        # Deduct bet
        if not self.deduct_bet(user.id, bet_amount):
            await update.message.reply_text("❌ Insufficient balance")
            return
        
        # Send game message
        text = (
            f"💣 <b>Mines Game Started!</b> (ID: <code>{game_id}</code>)\n\n"
            f"Bet: <b>${bet_amount:.2f}</b>\n"
            f"Mines: <b>{num_mines}</b>\n\n"
            "Click the buttons to reveal tiles. Find gems to increase your multiplier. "
            "Avoid the bombs!\nYou can cash out after any successful pick."
        )
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=self.create_keyboard(game_id)
        )
    
    @check_banned
    @check_maintenance
    async def handle_callback(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
        """Handle mines game callbacks"""
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
            await query.edit_message_text(
                "❌ Game not found or has ended.",
                reply_markup=None
            )
            return
        
        # Check ownership
        if not self.is_player_game(game_id, user.id):
            await query.answer("❌ This is not your game!", show_alert=True)
            return
        
        # Check if game is active
        if game["status"] != "active":
            await query.answer("❌ This game has already ended.", show_alert=True)
            return
        
        if action == "cashout":
            await self._handle_cashout(query, game_id, game)
        elif action == "pick" and len(parts) >= 4:
            cell = int(parts[3])
            await self._handle_pick(query, game_id, game, cell)
    
    async def _handle_cashout(self, query, game_id: str, game: dict):
        """Handle cashout action"""
        safe_picks = len(game["picks"])
        
        if safe_picks == 0:
            await query.answer("❌ Make at least one pick to cash out.", show_alert=True)
            return
        
        multiplier = self.get_multiplier(game["num_mines"], safe_picks)
        winnings = game["bet_amount"] * multiplier
        
        # Payout winnings
        self.payout(game["user_id"], winnings)
        
        # Complete game
        self.complete_game(
            game_id,
            win=True,
            multiplier=multiplier,
            result_data=f"Cashed out: {safe_picks} safe picks, Multiplier: {multiplier:.2f}x, Mine positions: {game['mines']}"
        )
        
        # Update message
        text = (
            f"💸 <b>Cashed Out!</b> (ID: <code>{game_id}</code>)\n\n"
            f"You won <b>${winnings:.2f}</b> with {safe_picks} correct picks!\n"
            f"Multiplier: <b>{multiplier:.2f}x</b>"
        )
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=self.create_keyboard(game_id, reveal=True)
        )
    
    async def _handle_pick(self, query, game_id: str, game: dict, cell: int):
        """Handle tile pick action"""
        # Check if already picked
        if cell in game["picks"]:
            await query.answer("❌ You already picked this tile.", show_alert=True)
            return
        
        # Check if hit mine
        if cell in game["mines"]:
            # Game over - lost
            self.complete_game(
                game_id,
                win=False,
                multiplier=0.0,
                result_data=f"Hit mine at tile {cell}, Mine positions: {game['mines']}"
            )
            
            text = (
                f"💥 <b>Boom!</b> You hit a mine at tile {cell}. (ID: <code>{game_id}</code>)\n\n"
                f"You lost your bet of <b>${game['bet_amount']:.2f}</b>."
            )
            
            await query.edit_message_text(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=self.create_keyboard(game_id, reveal=True)
            )
            return
        
        # Safe pick - add to picks
        game["picks"].append(cell)
        safe_picks = len(game["picks"])
        multiplier = self.get_multiplier(game["num_mines"], safe_picks)
        potential_winnings = game["bet_amount"] * multiplier
        
        # Check if max win (all safe tiles revealed)
        if safe_picks == (self.total_cells - game["num_mines"]):
            # Game over - max win
            self.payout(game["user_id"], potential_winnings)
            self.complete_game(
                game_id,
                win=True,
                multiplier=multiplier,
                result_data=f"Max win: {safe_picks} gems, Multiplier: {multiplier:.2f}x, Mine positions: {game['mines']}"
            )
            
            text = (
                f"🎉 <b>MAX WIN!</b> (ID: <code>{game_id}</code>)\n\n"
                f"You found all {safe_picks} gems and won <b>${potential_winnings:.2f}</b>!\n"
                f"Final Multiplier: <b>{multiplier:.2f}x</b>"
            )
            
            await query.edit_message_text(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=self.create_keyboard(game_id, reveal=True)
            )
            return
        
        # Continue game
        text = (
            f"✅ Safe! Tile {cell} was a gem. (ID: <code>{game_id}</code>)\n\n"
            f"<b>Picks:</b> {safe_picks}/{self.total_cells - game['num_mines']}\n"
            f"<b>Current Multiplier:</b> {multiplier:.2f}x\n"
            f"<b>Current Cashout:</b> ${potential_winnings:.2f}"
        )
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=self.create_keyboard(game_id)
        )
        await query.answer(f"✅ Safe! Current multiplier: {multiplier:.2f}x")


# Create game instance
mines_game = MinesGame()
