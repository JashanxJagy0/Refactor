"""
Game command and callback handlers
Routes game-related commands and callbacks to appropriate game implementations
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes

from features.games.registry import game_registry
from utils.decorators import check_banned, check_maintenance


@check_banned
@check_maintenance
async def mines_command(update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
    """Handle /mines command"""
    from features.games.house_games.mines import mines_game
    
    # Get parameters
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "Usage: /mines <bet_amount> [num_mines]\n"
            "Example: /mines 1.50 5\n"
            "Default mines: 3"
        )
        return
    
    try:
        bet_amount = float(context.args[0])
        num_mines = int(context.args[1]) if len(context.args) > 1 else 3
    except ValueError:
        await update.message.reply_text("❌ Invalid bet amount or number of mines")
        return
    
    await mines_game.start_game(update, context, bet_amount, num_mines)


@check_banned
@check_maintenance
async def coinflip_command(update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
    """Handle /flip command"""
    from features.games.house_games.coinflip import coinflip_game
    
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "Usage: /flip <bet_amount>\n"
            "Example: /flip 1.50"
        )
        return
    
    try:
        bet_amount = float(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid bet amount")
        return
    
    await coinflip_game.start_game(update, context, bet_amount)


@check_banned
@check_maintenance
async def diceroll_command(update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
    """Handle /dice command"""
    from features.games.house_games.diceroll import diceroll_game
    
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "Usage: /dice <bet_amount> [prediction]\n"
            "Example: /dice 1.50 6\n"
            "Default prediction: 6"
        )
        return
    
    try:
        bet_amount = float(context.args[0])
        prediction = int(context.args[1]) if len(context.args) > 1 else 6
    except ValueError:
        await update.message.reply_text("❌ Invalid bet amount or prediction")
        return
    
    await diceroll_game.start_game(update, context, bet_amount, prediction)


async def game_callback_router(update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
    """Route game callbacks to appropriate game handlers"""
    query = update.callback_query
    data = query.data
    
    # Route based on callback data prefix
    if data.startswith("mines_"):
        from features.games.house_games.mines import mines_game
        await mines_game.handle_callback(update, context)
    elif data.startswith("flip_"):
        from features.games.house_games.coinflip import coinflip_game
        await coinflip_game.handle_callback(update, context)
    # Add more game routing as games are implemented
    else:
        await query.answer("Unknown game action")


# Command handlers mapping for easy registration
GAME_COMMAND_HANDLERS = {
    "mines": mines_command,
    "m": mines_command,  # Alias
    "flip": coinflip_command,
    "coinflip": coinflip_command,
    "dice": diceroll_command,
    "d": diceroll_command,  # Alias
}
