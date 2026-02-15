"""
Tower Game - Climb 9 floors avoiding snakes
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
from utils.crypto import generate_tower_positions
from utils.decorators import check_banned, check_maintenance

# Tower configuration
TOWER_CONFIG = {
    'easy': {'name': 'Easy', 'tiles': 4},
    'medium': {'name': 'Medium', 'tiles': 3},
    'hard': {'name': 'Hard', 'tiles': 2}
}

TOWER_MULTIPLIERS = {
    'easy': {1: 1.1, 2: 1.2, 3: 1.4, 4: 1.8, 5: 2.2, 6: 2.8, 7: 3.5, 8: 4.5, 9: 6.0},
    'medium': {1: 1.2, 2: 1.5, 3: 2.0, 4: 2.8, 5: 4.0, 6: 5.5, 7: 7.5, 8: 10.0, 9: 14.0},
    'hard': {1: 1.5, 2: 2.5, 3: 4.5, 4: 8.0, 5: 14.0, 6: 24.0, 7: 40.0, 8: 70.0, 9: 125.0}
}


class TowerGame(BaseGame):
    """Tower climbing game with difficulty levels"""
    
    def __init__(self):
        super().__init__()
        self.game_type = "tower"
        self.num_floors = 9
    
    def get_multiplier(self, difficulty: str, floor: int) -> float:
        """Get multiplier for difficulty and floor"""
        return TOWER_MULTIPLIERS.get(difficulty, {}).get(floor, 1.0)
    
    def create_floor_keyboard(self, game_id: str, game: dict) -> "InlineKeyboardMarkup":
        """Create keyboard for current floor"""
        difficulty = game["difficulty"]
        tiles = TOWER_CONFIG[difficulty]['tiles']
        current_floor = game["current_floor"]
        
        # Create tile buttons
        buttons = []
        for i in range(1, tiles + 1):
            buttons.append(
                InlineKeyboardButton(f"🟩 {i}", callback_data=f"tower_pick_{game_id}_{i}")
            )
        
        keyboard = [buttons]
        
        # Add cashout button if past first floor
        if current_floor > 1:
            multiplier = self.get_multiplier(difficulty, current_floor - 1)
            potential = game["bet_amount"] * multiplier
            keyboard.append([
                InlineKeyboardButton(
                    f"💸 Cashout ${potential:.2f}",
                    callback_data=f"tower_cashout_{game_id}"
                )
            ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @check_banned
    @check_maintenance
    async def start_game(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE",
                        bet_amount: float, difficulty: str = 'medium'):
        """Start tower game"""
        user = update.effective_user
        
        # Validate difficulty
        if difficulty not in TOWER_CONFIG:
            await update.message.reply_text("❌ Invalid difficulty. Use: easy, medium, or hard")
            return
        
        # Validate bet
        valid, error = self.validate_bet(user.id, bet_amount)
        if not valid:
            await update.message.reply_text(f"❌ {error}")
            return
        
        # Generate snake positions
        from utils.crypto import get_user_seeds
        seeds = get_user_seeds(user.id)
        snake_positions = generate_tower_positions(
            seeds["server_seed"],
            seeds["client_seed"],
            seeds["nonce"],
            difficulty,
            self.num_floors
        )
        
        # Create game session
        game_id = self.create_game_session(
            user.id,
            bet_amount,
            difficulty=difficulty,
            current_floor=1,
            snake_positions=snake_positions
        )
        
        # Deduct bet
        if not self.deduct_bet(user.id, bet_amount):
            await update.message.reply_text("❌ Insufficient balance")
            return
        
        game = self.get_game_session(game_id)
        
        # Send game message
        text = (
            f"🗼 <b>Tower Game Started!</b> (ID: <code>{game_id}</code>)\n\n"
            f"💰 Bet: ${bet_amount:.2f}\n"
            f"🎚️ Difficulty: {TOWER_CONFIG[difficulty]['name']}\n"
            f"📈 Max Multiplier: {TOWER_MULTIPLIERS[difficulty][9]:.1f}x\n\n"
            f"🏁 Floor 1/{self.num_floors}\n"
            "Choose a tile to climb!"
        )
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=self.create_floor_keyboard(game_id, game)
        )
    
    @check_banned
    @check_maintenance
    async def handle_callback(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
        """Handle tower callbacks"""
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
        
        if action == "pick" and len(parts) >= 4:
            tile = int(parts[3])
            await self._handle_pick(query, game_id, game, tile)
        elif action == "cashout":
            await self._handle_cashout(query, game_id, game)
    
    async def _handle_pick(self, query, game_id: str, game: dict, tile: int):
        """Handle tile selection"""
        difficulty = game["difficulty"]
        current_floor = game["current_floor"]
        snake_positions = game["snake_positions"]
        
        # Check if hit snake (positions are 0-indexed in list but 1-indexed for tiles)
        if tile == snake_positions[current_floor - 1]:
            # Hit snake - lose
            self.complete_game(
                game_id,
                win=False,
                multiplier=0.0,
                result_data=f"Hit snake on floor {current_floor}, tile {tile}"
            )
            
            text = (
                f"💥 <b>Snake Hit!</b> (ID: <code>{game_id}</code>)\n\n"
                f"🐍 You hit a snake on floor {current_floor}!\n"
                f"💸 Lost: ${game['bet_amount']:.2f}"
            )
            
            await query.edit_message_text(text, parse_mode=ParseMode.HTML)
        else:
            # Safe - advance floor
            game["current_floor"] += 1
            
            if game["current_floor"] > self.num_floors:
                # Max win!
                multiplier = TOWER_MULTIPLIERS[difficulty][self.num_floors]
                winnings = game["bet_amount"] * multiplier
                
                self.payout(game["user_id"], winnings)
                self.complete_game(
                    game_id,
                    win=True,
                    multiplier=multiplier,
                    result_data=f"Completed all {self.num_floors} floors"
                )
                
                text = (
                    f"🎉 <b>MAX WIN!</b> (ID: <code>{game_id}</code>)\n\n"
                    f"You completed all {self.num_floors} floors!\n"
                    f"💸 Won: ${winnings:.2f}\n"
                    f"🎯 Multiplier: {multiplier:.1f}x"
                )
                
                await query.edit_message_text(text, parse_mode=ParseMode.HTML)
            else:
                # Continue climbing
                multiplier = self.get_multiplier(difficulty, game["current_floor"] - 1)
                potential = game["bet_amount"] * multiplier
                
                text = (
                    f"✅ <b>Safe!</b> (ID: <code>{game_id}</code>)\n\n"
                    f"🏁 Floor {game['current_floor']}/{self.num_floors}\n"
                    f"💰 Current Value: ${potential:.2f}\n"
                    f"🎯 Multiplier: {multiplier:.2f}x\n\n"
                    "Choose next tile:"
                )
                
                await query.edit_message_text(
                    text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=self.create_floor_keyboard(game_id, game)
                )
    
    async def _handle_cashout(self, query, game_id: str, game: dict):
        """Handle cashout"""
        difficulty = game["difficulty"]
        current_floor = game["current_floor"] - 1  # Last completed floor
        
        if current_floor < 1:
            await query.answer("❌ Complete at least one floor to cash out!", show_alert=True)
            return
        
        multiplier = self.get_multiplier(difficulty, current_floor)
        winnings = game["bet_amount"] * multiplier
        
        self.payout(game["user_id"], winnings)
        self.complete_game(
            game_id,
            win=True,
            multiplier=multiplier,
            result_data=f"Cashed out at floor {current_floor}"
        )
        
        profit = winnings - game["bet_amount"]
        
        text = (
            f"💸 <b>Cashed Out!</b> (ID: <code>{game_id}</code>)\n\n"
            f"🏁 Floor Reached: {current_floor}/{self.num_floors}\n"
            f"💰 Profit: ${profit:.2f}\n"
            f"💸 Total Payout: ${winnings:.2f}\n"
            f"🎯 Multiplier: {multiplier:.2f}x"
        )
        
        await query.edit_message_text(text, parse_mode=ParseMode.HTML)


# Create game instance
tower_game = TowerGame()
